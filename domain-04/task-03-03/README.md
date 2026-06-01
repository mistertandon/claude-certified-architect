# Structured Output via `tool_use` — `tool_choice` Options
  The key exam insight: forcing a specific tool ({"type": "tool", "name": "X"}) guarantees the response contains structured JSON matching that tool's schema — this is the canonical pattern for structured output 
  in the Anthropic SDK.   
## What this demonstrates

The `tool_choice` parameter controls whether and which tool the model must invoke:

| `tool_choice` | Behavior | `stop_reason` |
|---|---|---|
| `{"type": "auto"}` | Model decides — may or may not call a tool | `end_turn` or `tool_use` |
| `{"type": "any"}` | Model **must** call a tool, picks which one | `tool_use` |
| `{"type": "tool", "name": "X"}` | Model **must** call tool X — guarantees schema | `tool_use` |

## Setup

```bash
cd domain-04/task-03-03

# 1. Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 2. Install dependencies
pip install anthropic python-dotenv

# 3. Configure your API key
cp .env .env.local
# Edit .env.local and replace "your-api-key-here" with your actual key
# OR export directly:
export ANTHROPIC_API_KEY=sk-ant-...
```

## Run

```bash
python tool_choice_poc.py
```

## Expected output

The script runs 5 API calls, one per `tool_choice` variant:

1. **auto + general question** → no tool used, plain text answer (`stop_reason=end_turn`)
2. **auto + extraction prompt** → model voluntarily picks `extract_contact` (`stop_reason=tool_use`)
3. **any + sentiment text** → model must pick a tool, chooses `extract_sentiment`
4. **forced `extract_contact`** → guaranteed structured JSON matching the contact schema
5. **forced `extract_sentiment`** on contact text → model still returns sentiment schema (proves forced tool always wins)

## Key exam takeaway

Forcing a specific tool (`{"type": "tool", "name": "..."}`) is the canonical pattern for **guaranteed structured output** — the response always contains a `tool_use` block whose `input` conforms to the tool's `input_schema`.
