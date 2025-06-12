# Agent Toolkit – High-Level Architecture

> Version 0.1 – DRAFT  
> Last updated: 2025-06-10

## 1  Overview

The **Agent Toolkit** is a configuration-driven platform that spins up *Builder*, *Verifier*, and *Operator* agents, coordinates their work, and logs every significant event in a structured format.  
A single CLI command (`agentctl run path/to/config.yaml`) reads the user-supplied configuration file, provisions the requested agents, enforces resource constraints, and streams progress to a log sink (stdout, file, or external collector).

```
╭────────────────────────╮
│   User config (YAML)   │◀───┐
╰────────────────────────╯    │
          │                    │
          ▼                    │
╭──────────────────────────────┴─────────────╮
│         Orchestration Engine               │
│ ─────────────────────────────────────────── │
│  • Config parser & validator               │
│  • Agent factory & lifecycle manager       │
│  • Message bus (in-proc)                   │
│  • Resource & budget monitor               │
│  • Structured logging                      │
╰──────────┬────────────────────────┬────────╯
           │                        │
┌──────────┴──────────┐   ┌─────────┴─────────┐
│   Builder Agents    │   │  Verifier Agents  │
│  (N configurable)   │   │  (M configurable) │
└──────────┬──────────┘   └─────────┬─────────┘
           │                        │
           ▼                        ▼
                 ┌──────────────────────┐
                 │  Operator Agents     │
                 │   (running loop)     │
                 └──────────────────────┘
```

## 2  Agent Types

| Type        | Responsibility | Typical Skills | Key Outputs |
|-------------|----------------|----------------|-------------|
| **Builder** | Generate code, data assets, infra templates | LLM prompting, code synthesis, formatting | Source files, migration scripts |
| **Verifier** | Evaluate artifacts for correctness, policy compliance, performance | Unit & property testing, static analysis, benchmark harnesses | Test reports, quality scores |
| **Operator** | Deploy/run built system, monitor health, enact feedback loops | CLI / API automation, schedulers, alerting | Runtime logs, metrics, remediation actions |

All agents inherit from a common `BaseAgent` (async) that provides:
* inbox/outbox channels (in-proc event bus)
* cost/time accounting helpers
* structured logger instance
* graceful cancellation hook

## 3  Configuration File

YAML is the canonical format; JSON/TOML accepted interchangeably.  
The configuration is validated against an [OpenAPI-like JSON Schema] stored in `schemas/agent_config.schema.json`.

### 3.1  Top-Level Sections

```yaml
# config.example.yaml
project:
  name: retail-price-optimizer
  description: Build a CLI + API that suggests optimal prices.
build:
  agents:                # Builder pool
    count: 3
    model: openai/gpt-4o
    max_cost_usd: 5.00
    max_runtime_min: 30
verify:
  strategy: sequential   # sequential | parallel | gated
  agents:
    count: 2
    model: anthropic/claude-3-sonnet
  tests:
    - type: unit
      path: tests/unit/
    - type: performance
      target_rps: 200
operate:
  runtime: docker
  operator_agents:
    count: 1
    model: openai/gpt-4o-mini
logging:
  level: info
  format: json           # json | pretty
  sink:
    type: file
    path: logs/agent-run.ndjson
```

### 3.2  Important Fields

| Path | Description |
|------|-------------|
| `build.agents.count` | How many Builder agents to launch. |
| `build.max_cost_usd` | Hard cap on combined OpenRouter token spend. |
| `verify.strategy` | *sequential* ‑ run verifiers after all builders, *parallel* ‑ interleave, *gated* ‑ block promotion until tests pass. |
| `operate.runtime` | Target runtime for Operator agents (`docker`, `k8s`, `local`). |
| `logging.format` | `json` enforces machine-readable NDJSON lines; `pretty` adds color & indentation. |

## 4  Orchestration Engine

### 4.1  Lifecycle

1. **Load & validate config** – abort early on schema errors.  
2. **Instantiate agents** via `AgentFactory`:
   * allocate budget slice per agent
   * pass shared context (repo path, message bus, logger)
3. **Execution loop**  
   ```
   while active_agents:
       event = bus.next()
       route event to subscribed agents
       update budget/time trackers
   ```
4. **Shutdown hooks** – flush pending logs, close OpenRouter sessions.

### 4.2  Communication Model

* **Event Bus** – in-process async queue (can be swapped for Redis/NATS).  
* Events are small JSON dicts with mandatory fields:
  ```json
  { "ts":"2025-06-10T16:55:07Z", "type":"build.step.completed",
    "agent":"builder-2", "payload":{ "file":"price.py" } }
  ```

## 5  Logging & Observability

* All toolkit components emit **structured log events** (`ndjson` lines).  
* **Common envelope**:
  ```json
  {
    "ts": "2025-06-10T16:58:23.123Z",
    "lvl": "INFO",
    "module": "builder-1.codegen",
    "msg": "Generated file",
    "data": { "file": "price_optimizer.py", "tokens": 356, "cost_usd": 0.0041 }
  }
  ```
* **Sinks**: `stdout`, rotating file, or HTTP POST to external collector.
* **Correlation IDs** (`run_id`, `agent_id`, optional `trace_id`) propagate across events for end-to-end auditing.
* A lightweight CLI subcommand `agentctl logs path/to/log.ndjson --pretty` pretty-prints filtered views.

## 6  Extensibility Points

| Concern | Extension Mechanism |
|---------|--------------------|
| New LLM provider | Implement `LLMBackend` interface; register in factory. |
| Custom verifier | Subclass `VerifierAgent` and register entry-point. |
| Cost policy | Replace `CostMeter` strategy in orchestration engine. |
| Log sink | Implement `LogSink` protocol (write, flush) and configure via `logging.sink`. |

## 7  Future Work

* Multi-run experiment tracking (compare different build/verify configs).  
* UI dashboard streaming live logs & budget usage.  
* Pluggable memory/knowledge base shared between agents.  
* Fine-grained rollback & resume checkpoints.

---

**© 2025 Agent Toolkit** – MIT License. Contributions welcome!  
