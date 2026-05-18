# Recursive Subagent Delegation via Task Tool — POC

## Core Concept

Extends `task-02-03` by enabling **multi-level delegation**: subagents that themselves hold the `Task` tool can spawn their own sub-subagents. A `max_depth` cap prevents unbounded recursion.

## Architecture

```
Parent Agent (depth=0)
    ├── tools = [Task(enum=all types)]
    │
    ├─► market_researcher (depth=1)
    │       ├── tools = [web_search, read_doc, extract_data, Task(enum=[data_summarizer])]
    │       │
    │       └─► data_summarizer (depth=2)    ← leaf, no Task tool
    │               └── tools = [summarize]
    │
    └─► tech_analyst (depth=1)
            ├── tools = [read_doc, analyze_deps, Task(enum=[data_summarizer])]
            │
            └─► data_summarizer (depth=2)    ← leaf, no Task tool
                    └── tools = [summarize]
```

## What Changed vs task-02-03

| Area | task-02-03 | task-02-03-ver-02 |
|---|---|---|
| Delegation depth | Single level only | Multi-level with `MAX_DEPTH` cap |
| Subagent Task tool | Never granted | Granted when `can_delegate=True` AND `depth < MAX_DEPTH` |
| Task tool enum | Fixed list of all types | Scoped per agent via `delegatable_types` |
| Agent registry | Dict of tool lists | Dict with `tools`, `can_delegate`, `delegatable_types` |
| Leaf enforcement | Implicit (Task never in subagent tools) | Explicit (`depth >= MAX_DEPTH` strips Task tool) |

## Key Design Decisions

1. **`can_delegate` flag** — not every agent type should be allowed to delegate further. `data_summarizer` is a leaf by design.
2. **`delegatable_types`** — each agent declares which child types it may spawn, preventing a `data_summarizer` from spawning a `tech_analyst`.
3. **`MAX_DEPTH` guard** — even if `can_delegate=True`, the Task tool is withheld once depth reaches the limit.
4. **`build_task_tool()`** — generates a Task tool definition with `enum` scoped to the allowed child types, so the model cannot hallucinate an invalid agent type.

## Setup

```bash
cd domain-01/task-02-03-ver-02

# 1. Create virtual environment
python -m venv venv
source venv/bin/activate

# 2. Install dependencies
pip install anthropic python-dotenv

# 3. Configure API key — create a .env with ANTHROPIC_API_KEY=sk-...

# 4. Run
python task_subagent_recursive_poc.py
```

## Key Exam Takeaway

| Requirement | Why |
|---|---|
| `Task` in parent's `tools` | Gate mechanism — without it, subagent spawning is blocked |
| `Task` in subagent's `tools` | Enables recursive delegation (multi-level) |
| `depth < MAX_DEPTH` check | Prevents unbounded recursion |
| Scoped `enum` per agent type | Least-privilege — each agent can only delegate to declared child types |
