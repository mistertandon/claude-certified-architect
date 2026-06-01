# Task 02-02: Structured Error Context vs Generic Errors

## Principle

> Always include **what was attempted** when raising or handling errors.

Generic errors like `"Something went wrong"` force developers to reproduce failures to debug them. Structured errors carry the full operation context (model, prompt, parameters, metadata) so any failure is immediately actionable.

## Project Structure

```
task-02-02/
├── .env          # API key configuration
├── main.py       # POC comparing both approaches
└── README.md
```

## Setup

### 1. Create and activate virtual environment

```bash
python3 -m venv venv
source venv/bin/activate
```

### 2. Install dependencies

```bash
pip install anthropic python-dotenv
```

### 3. Configure environment

```bash
cp .env .env.local
# Edit .env and replace 'your-api-key-here' with your actual Anthropic API key
```

### 4. Run the POC

```bash
python main.py
```

## Expected Output

With an invalid/missing API key, you'll see the contrast:

```
============================================================
1) GENERIC ERROR (anti-pattern)
============================================================
  Caught: Something went wrong: ...

============================================================
2) STRUCTURED ERROR (recommended)
============================================================
  Caught:
  [message_create] ...
    model: claude-sonnet-4-20250514
    prompt: "Explain structured error handling in one sentence..."
    max_tokens: 100
    metadata: {'user_id': 'user-42'}

  Root cause type: AuthenticationError
```

## Key Takeaways

| Aspect | Generic | Structured |
|--------|---------|-----------|
| What failed? | Unknown | `operation` field |
| What input caused it? | Lost | `prompt_preview` + `metadata` |
| Which model? | Unknown | `model` field |
| Root cause? | Swallowed | Chained via `from e` |
| Actionable? | No | Yes |
