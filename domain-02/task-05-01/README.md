# Domain 02 / Task 05-01 — Built-in Read Tool (read_file)

## What This Demonstrates

The `read_file` built-in tool in a single-tool agentic loop. The agent reads file contents to understand code and data, then synthesizes findings into a human-readable summary.

```
   User Question
        |
   +-----------+
   | READ AGENT|  (1 tool: read_file)
   +-----------+
        |
   Agentic Loop:
     tool_use  → read_file(path) → result → reasoning
        ↓
     end_turn  → final answer
```

## Key Exam Concepts

| Concept | Where in Code |
|---------|---------------|
| Tool definition (JSON schema) | `READ_TOOL` dict — name, description, input_schema |
| Tool handler (execution) | `handle_read_file()` — runs the actual file read |
| Agentic loop | `while True` loop in `run_read_agent()` |
| Loop continuation signal | `stop_reason == "tool_use"` → model wants to read more files |
| Loop exit signal | `stop_reason == "end_turn"` → model has enough info to answer |
| Single-tool constraint | `tools=[READ_TOOL]` — agent can only read, never write or edit |
| Multi-turn reasoning | Demo 2 shows the agent reading multiple files across turns |

## Setup

```bash
cd domain-02/task-05-01

# 1. Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 2. Install dependencies
pip install anthropic python-dotenv

# 3. Set your API key
#    Edit .env and replace your-api-key-here with a real key
nano .env
```

## Run

```bash
python read_file_tool.py
```

## What to Observe

1. **Demo 1 — Single file read**: The agent reads `config.json` in one turn and reports the database host/port and debug flag status. Expect `stop_reason: tool_use` (turn 1) → `stop_reason: end_turn` (turn 2).

2. **Demo 2 — Multi-file read**: The agent reads `src/models.py` and `src/service.py` across multiple turns to build a cross-file understanding. Watch how `stop_reason` stays `tool_use` until the agent has read enough files, then flips to `end_turn`.

3. **Tool isolation**: The agent cannot write, edit, or execute — it can only read. The system prompt and tool list enforce this boundary.

4. **Sandbox scoping**: All reads resolve against a `sandbox/` directory, preventing accidental access to files outside the demo.
