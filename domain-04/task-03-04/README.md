# Structured Output via tool_use — Schema Design Patterns

## Concept

Using `tool_use` with `tool_choice: "any"` forces Claude to return structured JSON conforming to a defined schema — no free-text output possible.

## Schema Patterns Demonstrated

| Pattern | How | Why |
|---------|-----|-----|
| Required fields | Listed in `"required"` array | Model MUST always produce these |
| Optional fields | Omitted from `"required"` | Model skips when info unavailable |
| Enum | `"enum": ["a", "b", "c"]` | Constrains output to known values |
| Enum + other + detail | `enum` includes `"other"` + companion `_detail` field | Escape hatch without losing structure |
| Nullable | `"type": ["string", "null"]` | Explicitly represents absence vs omission |

## Setup

```bash
cd domain-04/task-03-04

python -m venv .venv
source .venv/bin/activate

pip install anthropic python-dotenv
```

## Configure

Edit `.env` and set your API key:

```
ANTHROPIC_API_KEY=sk-ant-...
```

## Run

```bash
python structured_output_tool_use.py
```

## Expected Output

```json
{
  "summary": "Customer double-charged for Pro subscription over 3 months",
  "severity": "medium",
  "category": "billing",
  "category_detail": null,
  "resolved_at": "2024-03-15T14:30:00Z",
  "affected_user_count": 47,
  "requires_followup": true
}
```

## Key Exam Points

1. `tool_choice: "any"` — guarantees structured output (no text fallback)
2. `required` array — controls which fields model MUST produce
3. Nullable (`["type", "null"]`) vs Optional (not in `required`) — different semantics
4. Enum with `"other"` + companion detail field — extensible without losing structure
