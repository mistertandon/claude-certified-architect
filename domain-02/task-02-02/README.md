# Error Response Design Patterns — POC

Demonstrates classifying Anthropic SDK errors into semantic categories (`validation`, `auth`, `not_found`, `rate_limit`, `overload`, `internal`, `timeout`) so consumers get structured, actionable error responses.

## Architecture

```
SDK Exception (AuthenticationError, BadRequestError, …)
        │
        ▼
┌──────────────────┐     ┌─────────────────────┐
│ classify_api_error│ ──▶ │  ErrorResponse       │
│ (single mapper)  │     │  • error_category    │
└──────────────────┘     │  • message           │
                         │  • retryable (bool)  │
                         │  • retry_after_seconds│
                         │  • details{}         │
                         └─────────────────────┘
                                  │
                                  ▼
                         call_with_retry()
                         (retries only if retryable=True)
```

## Setup

### 1. Create and activate a virtual environment

```bash
cd domain-02/task-02-02
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Install dependencies

```bash
pip install anthropic python-dotenv
```

### 3. Configure your API key

```bash
cp .env .env.local
# Edit .env.local and replace 'your-api-key-here' with your real key
```

Or export directly:

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

### 4. Run the demo

```bash
python error_response_patterns.py
```

## What the demo runs

| # | Scenario            | Trigger                       | Expected Category |
|---|---------------------|-------------------------------|-------------------|
| 1 | Validation Error    | Empty `messages=[]`           | `validation`      |
| 2 | Auth Error          | Bogus API key                 | `auth`            |
| 3 | Not Found Error     | Non-existent model name       | `not_found`       |
| 4 | Successful Request  | Valid call                    | *(success)*       |

## Key Design Decisions

1. **Single classification point** — all SDK exceptions map through `classify_api_error()`, so category logic never leaks into business code.
2. **`retryable` flag on the envelope** — callers decide retry behavior without understanding HTTP status codes.
3. **`retry_after_seconds`** — parsed from the `retry-after` header when available; callers don't hardcode backoff.
4. **Finite `ErrorCategory` enum** — consumers can `switch`/`match` on a known set instead of parsing strings.
