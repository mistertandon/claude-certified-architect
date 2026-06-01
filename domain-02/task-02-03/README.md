# Task 02-03: `isRetryable` Error Response Design Pattern

## What this demonstrates

When an agentic tool call fails, the error response includes an `isRetryable` flag that tells the agent:

| `isRetryable` | Meaning | Agent action |
|---|---|---|
| `true` | Transient failure (timeout, rate-limit, blip) | Retry the same call |
| `false` | Permanent failure (bad input, not found) | Stop retrying, inform user |

This prevents wasted retries on permanent errors and enables automatic recovery from transient ones.

## Setup

```bash
cd domain-02/task-02-03

# 1. Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# 2. Install dependency
pip install anthropic python-dotenv

# 3. Configure API key
cp .env .env.local
# Edit .env.local and replace 'your-api-key-here' with your actual key
export ANTHROPIC_API_KEY=<your-key>
```

## Run

```bash
python is_retryable_poc.py
```

## Expected output

The backend randomly simulates three scenarios. Run multiple times to see each:

1. **Success** -- agent gets order status, responds to user
2. **Transient error** (`isRetryable: true`) -- agent retries, may succeed on next attempt
3. **Permanent error** (`isRetryable: false`) -- agent stops retrying, tells user the order wasn't found

## Key pattern (exam focus)

```
Tool error response shape:
{
  "error": "human-readable message",
  "isRetryable": true | false    <-- drives agent retry logic
}
```

- The **system prompt** teaches the agent the retry policy
- The **tool result** carries `is_error: true` so the model knows it failed
- The **isRetryable flag** inside the content lets the agent distinguish transient vs permanent
