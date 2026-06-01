# Validation-Retry Loop Pattern

Demonstrates how to append specific validation errors back into the conversation so Claude can self-correct across retries.

## Core Concept

```
User prompt → Model responds → Validate → FAIL?
    → Append error to messages → Retry (model sees what broke)
    → Model self-corrects → Validate → PASS
```

## Setup

```bash
cd domain-04/task-04-01
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
python validation_retry_loop.py
```

## Expected Output

```
--- Attempt 1/3 ---
Model output:
{"name": "Elena Torres", "age": 28, "hobbies": ["painting", "hiking", "chess"]}
Validation passed on attempt 1.

Final validated result:
{
  "name": "Elena Torres",
  "age": 28,
  "hobbies": ["painting", "hiking", "chess"]
}
```

If the model returns malformed output (e.g., markdown fences around JSON), you'll see retry attempts where the error is fed back and the model corrects itself.
