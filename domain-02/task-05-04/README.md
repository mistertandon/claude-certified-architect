# Domain 02 / Task 05-04 — Built-in Tool: Bash

## What This Demonstrates

The **Bash** built-in tool in an agentic loop — the model executes shell commands for building, testing, and system inspection. This is the same mechanism Claude Code uses when it runs commands on your behalf.

```
   User Task
       |
   +────────────────+
   | BASH AGENT     |  (single tool: bash)
   +────────────────+
       |
   Agentic Loop:
     tool_use  → subprocess.run(command) → stdout/stderr/exit_code → reasoning
       ↓
     end_turn  → final summary
```

### Why Bash Matters

| Use Case | Example Commands |
|----------|-----------------|
| **System inspection** | `ls`, `find`, `cat`, `wc -l` |
| **Building** | `make build`, `pip install`, `npm run build` |
| **Testing** | `make test`, `pytest`, `npm test` |
| **Linting / validation** | `py_compile`, `flake8`, `eslint` |
| **Multi-step operations** | Chaining commands to answer complex questions |

Bash is the **escape hatch** — when no specialized tool exists, the model falls back to shell commands.

## Key Exam Concepts

| Concept | Where in Code |
|---------|---------------|
| Tool schema | `BASH_TOOL` dict — defines `command` as the single input |
| Handler boundary | `handle_bash()` — where model reasoning meets real-world execution |
| `subprocess.run` | Executes the command, captures stdout/stderr/exit_code |
| Sandbox isolation | `cwd=SANDBOX` pins all commands to a safe directory |
| Timeout guard | `timeout=30` prevents runaway commands from blocking |
| Agentic loop | `stop_reason == "tool_use"` → run more commands |
| Loop termination | `stop_reason == "end_turn"` → model has enough info |
| Result feedback | Full stdout/stderr fed back so model can reason over output |

## Setup

```bash
cd domain-02/task-05-04

# 1. Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 2. Install dependencies
pip install anthropic python-dotenv pytest

# 3. Configure API key
#    Open .env and replace your-api-key-here with a real Anthropic API key
nano .env
```

## Run

```bash
python bash_tool_poc.py
```

## What to Observe

### Demo 1 — System Inspection
- Agent runs `ls`, `find`, `cat` to discover and read the project
- Multiple turns: each command yields information that guides the next
- **Use case:** understanding an unfamiliar codebase

### Demo 2 — Testing
- Agent executes `make test` (which runs `pytest -v`)
- Parses test output to report pass/fail status
- **Use case:** CI/CD validation, automated test runner

### Demo 3 — Build Validation
- Agent runs `make lint` and `py_compile` to check for syntax errors
- Reports whether the code is clean or has issues
- **Use case:** pre-commit checks, catching errors before they ship

### Demo 4 — Multi-step Operations
- Agent chains `wc -l`, `find`, `cat` across multiple turns
- Combines results to produce a project health summary
- **Use case:** complex queries that require multiple data points

## Architecture vs Other Tasks

| Aspect | Task 05-01 (Read) | Task 05-02 (Multi-tool) | Task 05-04 (Bash) |
|--------|-------------------|-------------------------|-------------------|
| Tools | 1 (read_file) | 5 (write/edit/bash/grep/glob) | 1 (bash) |
| Scope | File contents only | Full CRUD + search | Any shell command |
| Side effects | None (read-only) | Creates/modifies files | Depends on command |
| Key insight | Simplest agentic loop | Tool dispatch routing | Escape hatch for arbitrary ops |
