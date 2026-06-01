# Domain 02 / Task 02-01 — `is_error` Flag: Signalling Tool Failure to the Agent

## Concept

When returning a `tool_result` to Claude, the `is_error` field explicitly tells the model
whether the tool call **succeeded** or **failed**. Without it, the model must guess from
free-text output — leading to hallucinations where error messages are treated as real data.

## Key Distinction

| Scenario | `is_error` | Model Behavior |
|---|---|---|
| Valid result (including "not found") | `false` (default) | Presents data to the user normally |
| Bad input / validation failure | `true` | Self-corrects input and retries |
| Transient service failure | `true` | Retries the same call |
| Permanent failure | `true` | Informs user about the failure gracefully |

## Scenarios Demonstrated

| # | Scenario | Expected Behavior |
|---|----------|-------------------|
| 1 | Happy path — `alice92` exists | Model returns profile data directly |
| 2 | Validation error — `@invalid!` username | `is_error=True` → model recognizes bad input, informs user |
| 3 | Transient failure — `bob` (first call times out) | `is_error=True` + retry hint → model retries → second call succeeds |
| 4 | Not found — `unknownuser99` | `is_error=False` → model says "user not found" (no retry) |

## Setup

```bash
cd domain-02/task-02-01

# 1. Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 2. Install dependencies
pip install anthropic python-dotenv

# 3. Set your API key
#    Open .env and replace your-api-key-here with your actual Anthropic API key
nano .env
```

## Run

```bash
python is_error_flag.py
```

## What to Observe

1. **Scenario 1** — Straightforward success; `is_error` is `False` (default), model presents data.
2. **Scenario 2** — Model receives `is_error=True` for invalid input; it does **not** parrot the error JSON as a profile.
3. **Scenario 3** — First call returns `is_error=True` with a "retry" hint. Watch the model make a **second tool call** for the same username — this retry behavior is driven by the error signal.
4. **Scenario 4** — "Not found" returns `is_error=False` because it's a valid outcome, not a failure. The model composes a polite response instead of retrying.

## Exam Takeaway

> The `is_error` flag is a **structured signal** in the `tool_result` message.
> It removes ambiguity: the model no longer has to parse free-text to decide
> if something went wrong. This single boolean controls whether the agent
> retries, self-corrects, or reports the failure — making the agentic loop
> more predictable and reliable.
