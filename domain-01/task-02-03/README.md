# Task Tool for Spawning Subagents — POC

## Core Concept

The `Task` tool enables a parent agent to delegate discrete subtasks to independent subagents. **The critical requirement**: `allowedTools` must include `'Task'` in the tools list — without it, the model cannot spawn subagents.

## Architecture

```
Parent Agent (orchestrator)
    │
    ├── tools=[task_tool]  ← Task MUST be listed here
    │
    ├── Subagent A (microservices summary)
    └── Subagent B (monolith summary)
```

## Setup

```bash
cd domain-01/task-01-02-03

# 1. Create virtual environment
python -m venv venv
source venv/bin/activate

# 2. Install dependencies
pip install anthropic python-dotenv

# 3. Configure API key
cp .env .env.local
# Edit .env and set your ANTHROPIC_API_KEY

# 4. Run
python task_subagent_poc.py
```

## Key Exam Takeaway

| Requirement | Why |
|---|---|
| `tools=[task_tool]` in API call | Model can only use tools explicitly provided |
| Task tool in `allowedTools` | Gate mechanism — without it, subagent spawning is blocked |
| Tool result fed back to parent | Completes the agentic loop; parent synthesizes subagent outputs |
