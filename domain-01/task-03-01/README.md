# PostToolUse Hooks — Data Normalization POC

Demonstrates the **PostToolUse hook** pattern: intercepting and normalizing raw tool outputs before the model processes them.

## Concept

```
Tool executes → Raw output → [PostToolUse Hook] → Normalized output → Model
```

The hook sits between tool execution and model consumption, ensuring the model always receives clean, consistently formatted data regardless of upstream source quality.

## Why This Matters

| Without Hook | With Hook |
|---|---|
| Model sees `"  john DOE  "` | Model sees `"John Doe"` |
| Model sees `"03/15/2023"` | Model sees `"2023-03-15"` |
| Model sees `"$1,234.56"` | Model sees `"1234.56"` |
| Inconsistent responses | Predictable, clean responses |

## Setup

### 1. Create virtual environment

```bash
python -m venv venv
source venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment

```bash
cp .env .env.local
# Edit .env.local and set your ANTHROPIC_API_KEY
```

Or export directly:

```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

### 4. Run

```bash
python post_tool_use_hook.py
```

## Expected Output

```
Starting agent with PostToolUse hook...

Model requested tool: get_customer_record
Input: { "customer_id": "cust-42" }

============================================================
POST_TOOL_USE HOOK FIRED
============================================================
Tool: get_customer_record

Raw output:
{
  "Name": "  john DOE  ",
  "EMAIL": "John.Doe@Example.COM",
  ...
}

Normalized output:
{
  "name": "John Doe",
  "email": "john.doe@example.com",
  ...
}
============================================================

Agent Response:
Here's the customer summary for cust-42...
```

## Key Architecture Decisions

1. **Hook is separate from tool logic** — tools stay pure; normalization is reusable across tools
2. **Normalization happens before model sees data** — reduces hallucination from messy input
3. **Metadata injected (`_normalized: true`)** — model can reference that data was cleaned
4. **ISO 8601 dates** — eliminates MM/DD vs DD/MM ambiguity globally

## Relation to Claude Code Hooks

In Claude Code's `settings.json`, this maps to:

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "get_customer_record",
        "command": "python normalize_output.py"
      }
    ]
  }
}
```

This POC implements the same pattern programmatically within an SDK-based agent.
