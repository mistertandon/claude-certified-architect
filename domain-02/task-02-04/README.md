# Task 02-04 — Structured Error Context Pattern

Demonstrates how to wrap every failure with **what was attempted** and **what failed**, so callers get actionable diagnostics instead of raw tracebacks.

## Key Concepts

| Concept | Where in code |
|---|---|
| `ErrorContext` dataclass | Single structured envelope carrying operation, phase, error type, message, and retry eligibility |
| Status-code classifier | `_classify_api_error()` — maps Anthropic HTTP status codes to structured context |
| Phase tagging | Each failure is labelled with the phase it occurred in: `validation`, `api_call`, or `response_parse` |
| Result-or-error dict | `summarize_text()` always returns `{"result": ...}` or `{"error": ...}` — no exceptions leak to callers |

## Setup

```bash
cd domain-02/task-02-04

# 1. Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 2. Install dependencies
pip install anthropic python-dotenv

# 3. Configure your API key
cp .env .env.local
# Edit .env.local and replace your-api-key-here with a real key
export $(cat .env.local | xargs)
```

## Run

```bash
python structured_error_context.py
```

### Expected output

```
============================================================
Scenario: empty_input
============================================================
[ERROR] Structured error context:
{
  "operation": "summarize_text",
  "phase": "validation",
  "error_type": "invalid_input",
  "message": "Input text is empty. Nothing to summarize.",
  ...
}

============================================================
Scenario: valid_input
============================================================
[OK] Summary: <one-paragraph summary>
```

## Error response shape

Every error follows this structure:

```json
{
  "operation": "summarize_text",
  "phase": "api_call",
  "error_type": "rate_limit_error",
  "message": "Rate limit hit. Back off and retry.",
  "attempted_input": { "text_length": 42, "max_tokens": 256 },
  "retry_eligible": true,
  "timestamp": 1717689600.123
}
```

Fields:
- **operation** — what the caller asked for
- **phase** — where it broke (`validation` | `api_call` | `response_parse`)
- **error_type** — machine-readable category
- **message** — human-readable explanation
- **attempted_input** — redacted snapshot of the request
- **retry_eligible** — whether retrying could succeed
