# Agent Toolkit

**Agent Toolkit** is a configuration-driven, *multi-agent* orchestration system.  
Instead of a single monolithic assistant, the Toolkit spins-up specialised
Builder, Verifier and Operator agents that collaborate to:

* generate code or infrastructure from a high-level spec,
* automatically verify the result with tests / static analysis, and
* run or monitor the artefacts in an operational loop.

Everything is controlled through a single YAML/JSON/TOML configuration file
(see `examples/config.yaml`). A CLI (`agentctl`) then reads the config, launches
the requested agents and streams **structured JSON logs** so you can follow the
process in real-time or pipe it to your observability stack.

---

## Table of Contents
1. [Key Capabilities](#key-capabilities)  
2. [How It Works](#how-it-works)  
3. [Project Structure & Core Modules](#project-structure--core-modules)  
4. [Development Workflow](#development-workflow)  
5. [Getting Started](#getting-started)  
6. [Configuration](#configuration)  
7. [Usage Examples](#usage-examples)  
8. [Contributing](#contributing)  
9. [License](#license)

---

## Key Capabilities
- **Config-Driven Orchestration** – One declarative file defines how many agents
  to launch, which LLM models to use, budget / time caps, verification strategy,
  deployment runtime, log sinks, and more.  
- **Specialised Agent Pools**
  - **Builder Agents** – synthesise code, infra or data assets  
  - **Verifier Agents** – run unit / integration / performance / security tests  
  - **Operator Agents** – deploy or run the artefacts and watch health metrics  
- **Resource Governance** – central tracker enforces token/cost/time budgets and
  raises structured `resource.limit.*` events when thresholds are hit.  
- **Structured Logging** – every significant event is emitted as NDJSON
  (timestamp, level, module, message, payload) so it can be shipped straight to
  ELK/Grafana/Datadog.  
- **Pluggable LLM Backend** – the `LLMInterface` adapter lets you swap
  OpenRouter, Azure OpenAI, Vertex AI, etc., without touching agent logic.  
- **Extensible** – add new agent types, verification stages or log sinks via a
  clean plugin interface.

---

## Agent Types

| Type | Responsibility | Typical Skills |
|------|----------------|----------------|
| **Builder** | Generate code / infra from spec | Code synthesis, templating, doc-gen |
| **Verifier** | Validate artefacts meet quality & policy | Test-gen, static analysis, perf / sec scanners |
| **Operator** | Run, monitor and heal the system | CLI / API automation, schedulers, alerting |

All inherit from a common `BaseAgent` that provides:
* async inbox/outbox on an internal event-bus  
* cost / token accounting hooks  
* structured logger instance  
* graceful-shutdown handler  

---

## How It Works
```text
┌────────────┐   1. Prompt         ┌────────────┐
│    User    │ ───────────────▶ │   Agent   │
└────────────┘                  └────────────┘
                                      │
         2. Understand request        │
         3. Create plan (≤10 steps)   ▼
                                 development_plan.md
                                      │
         4. Iterate over steps        │
         ─────────────────────────────┘
For each step:
    a. Query LLM → implementation plan
    b. File ops via ProjectExecutor
    c. Update development_plan.md
```

---

## Project Structure & Core Modules
| Path | Purpose |
|------|---------|
| `main.py` | CLI entry-point – parses args, instantiates `Agent`, kicks off a run |
| `agent.py` | Orchestrator – high-level logic for understanding, planning, executing, updating |
| `llm_interface.py` | Thin wrapper around the Language-Model API (currently stubs) |
| `project_executor.py` | Safe file-system / shell-command helper |
| `config.py` | Typed configuration model powered by **pydantic** |
| `requirements.txt` | Dependency pinning |
| `agent_config.json` | Example runtime configuration |

---

## Development Workflow
1. **Understand** – `Agent.understand_request()` calls `LLMInterface` to extract project metadata.  
2. **Plan** – `Agent.create_plan()` asks the LLM for ≤ 10 steps and writes them to *development_plan.md*.  
3. **Execute** – For each step:  
   - Files in the project directory are listed.  
   - `LLMInterface.plan_implementation_step()` returns a mini-spec.  
   - `ProjectExecutor` creates / modifies files with code produced by `LLMInterface.generate_code()`.  
   - Step is flagged as `[DONE]` in the plan.  
4. **Completion** – After all steps are done the agent prompts the user to test the project.  

---

## Getting Started

### Prerequisites
```bash
python 3.10+
pip install -r requirements.txt
# Optional: Configure an API key for your LLM provider
export OPENAI_API_KEY="..."
```

### Installation
Clone the repo (or your fork) and install dependencies:

```bash
git clone git@github.com:YOUR_USERNAME/Agent.git
cd Agent
pip install -r requirements.txt
```

---

## Configuration
Most settings live in **`agent_config.json`** (you can also supply `ini` or env vars):

```json
{
  "agent":    { "project_dir": "./project", "max_steps": 10 },
  "llm":      { "model_name": "gpt-4", "temperature": 0.7 },
  "executor": { "command_timeout": 30, "safe_mode": true }
}
```

Load a custom file with `--config /path/to/config.json` (feature coming soon).

---

## Usage Examples

### Quick Start
```bash
python main.py \
  --prompt "Build a simple CLI timer application in Python that supports start, stop, and reset commands."
```

Flags:
- `-d / --directory` – target project folder (default `./project`)
- `--plan-file`      – name of the Markdown file storing the plan
- `-v / --verbose`   – enable debug logging

### Iterative Development
Run once to generate the scaffold, inspect `project/`, tweak the plan if needed, then re-run to continue.

---

## Contributing
Pull requests and issues are welcome! For major changes, start a discussion to describe what you’d like to add or change.

**Local dev helpers**

```bash
# formatting, imports, linting, tests
make format lint test
```

---

## License
This project is released under the MIT License – see `LICENSE` for details.
