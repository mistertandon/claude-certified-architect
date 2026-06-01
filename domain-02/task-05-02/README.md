# Domain 02 / Task 05-02 — Built-in Tools: Write, Edit, Bash, Grep, Glob

## What This Demonstrates

Five built-in tools working together in a single multi-tool agentic loop. The agent scaffolds a project, modifies it, searches it, and validates it — all through tool calls orchestrated by the model.

```
   User Task
       |
   +────────────────+
   | MULTI-TOOL     |  (5 tools: write, edit, bash, grep, glob)
   | AGENT          |
   +────────────────+
       |
   Agentic Loop:
     tool_use  → dispatch to handler → result → reasoning
       ↓
     end_turn  → final answer
```

### Tool-by-Tool Breakdown

| # | Tool | Purpose | Real-World Analogy |
|---|------|---------|--------------------|
| 1 | **write_file** | Create new files from scratch | Scaffolding new modules, configs, tests |
| 2 | **edit_file** | Targeted old→new string replacement | Surgical bug fixes without rewriting whole files |
| 3 | **bash** | Execute shell commands | Building, testing, linting, system inspection |
| 4 | **grep** | Regex search across files | Finding TODOs, symbols, patterns in a codebase |
| 5 | **glob** | Find files by pattern | Discovering project structure, locating configs |

## Key Exam Concepts

| Concept | Where in Code |
|---------|---------------|
| Multi-tool schema | `ALL_TOOLS` list — five tool dicts with JSON schemas |
| Dispatch routing | `HANDLERS` dict — maps tool name → handler function |
| Agentic loop | `while turn < max_turns` in `run_agent()` |
| Loop continuation | `stop_reason == "tool_use"` → model needs more tool calls |
| Loop exit | `stop_reason == "end_turn"` → task complete |
| Sandbox isolation | `_resolve()` anchors all paths to `sandbox/` |
| Edit uniqueness | `handle_edit_file()` rejects ambiguous multi-match edits |
| Tool selection | Model chooses which tool(s) per turn based on task context |

## Setup

```bash
cd domain-02/task-05-02

# 1. Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 2. Install dependencies
pip install anthropic python-dotenv

# 3. Set your API key
#    Open .env and replace your-api-key-here with a real Anthropic API key
nano .env
```

## Run

```bash
python builtin_tools_poc.py
```

## What to Observe

### Demo 1 — Write (create new files)
- Agent reads `src/utils.py` via `bash` (cat) to understand the functions
- Agent calls `write_file` to create `tests/test_utils.py` with proper test cases
- Demonstrates **file creation from scratch**

### Demo 2 — Edit (targeted modifications)
- Agent uses `edit_file` with exact `old_string` / `new_string` to patch `src/app.py`
- The `/users` endpoint changes from returning `[]` to returning sample data
- Demonstrates **surgical edits** — only the changed lines are specified

### Demo 3 — Bash (shell commands)
- Agent runs `find`, `wc -l`, and `grep` via shell to inspect the sandbox
- Shows how bash is the escape hatch for arbitrary system operations
- Demonstrates **build/test/validate workflows**

### Demo 4 — Grep (pattern search)
- Agent searches for `TODO` comments across all files
- Returns file paths, line numbers, and matching lines
- Demonstrates **codebase-wide pattern discovery**

### Demo 5 — Glob (file discovery)
- Agent uses `**/*.py` and `**/*.json` patterns to discover project structure
- Demonstrates **navigating unfamiliar codebases** by finding files first

## Architecture vs Task 05-01

| Aspect | Task 05-01 (Read) | Task 05-02 (Write/Edit/Bash/Grep/Glob) |
|--------|-------------------|----------------------------------------|
| Tools | 1 (read_file) | 5 (write, edit, bash, grep, glob) |
| Dispatch | Direct call | `HANDLERS` dispatch table |
| Agent role | Read-only observer | Active modifier + inspector |
| Turns | 1–3 per demo | 2–6+ per demo (more complex tasks) |
| Loop guard | None (simple tasks) | `max_turns` prevents runaway loops |
