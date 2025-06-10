# Agent

A modular prototype **coding-assistant agent** that turns natural-language prompts into fully-scaffolded software projects.  
The project’s goal is to explore an *LLM-first* workflow in which the agent plans, writes, and iteratively updates code until a working deliverable is ready for the user to test.

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
- **Prompt Understanding** – Parses the user’s description to identify project type, essential features, and technologies.  
- **Autonomous Planning** – Produces a development plan in ≤ 10 actionable steps and saves it to `development_plan.md`.  
- **Step-wise Execution** – For each TODO the agent independently:
  1. Re-plans the specific task with the LLM  
  2. Decides which files to create / update  
  3. Generates or edits code via the LLM  
  4. Marks the step as **DONE** in the plan  
- **File System Safety** – All file operations are routed through `ProjectExecutor`, providing backups and basic command-sanitisation.  
- **Pluggable LLM Layer** – `LLMInterface` is an adapter; swap in any provider by replacing a single class.  

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
