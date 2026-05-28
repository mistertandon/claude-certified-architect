# Task 01-02-04: Parallel Subagent Execution

## Concept

In Claude Code, when an assistant issues **multiple Task/Agent tool calls in a single response**, the runtime executes them **in parallel** — not sequentially. This POC reproduces that pattern using `asyncio.gather` with the Anthropic SDK.

## How It Maps to Claude Code

| Claude Code Internals | This POC |
|---|---|
| Multiple `Agent` tool blocks in one response | `asyncio.gather(*coroutines)` |
| Each agent runs independently | Each `run_subagent()` call has its own context |
| Results return when all finish | `gather()` awaits all concurrently |

## Setup

```bash
cd domain-01/task-01-02-04

# 1. Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 2. Install dependency
pip install anthropic python-dotenv

# 3. Configure API key
cp .env .env.local
# Edit .env.local and replace 'your-api-key-here' with your actual key
export ANTHROPIC_API_KEY="your-actual-key"
```

## Run

```bash
python parallel_tasks.py
```

## Expected Output

```
============================================================
  Parallel Execution Complete — ~1.2s total
  (Sequential would take ~3.6s)
============================================================

  [code_reviewer]
  → The function has a bug: it subtracts instead of adding.

  [doc_writer]
  → """Fetch a user's profile data by ID."""

  [test_generator]
  → test_login_with_valid_credentials
```

## Key Takeaway

Parallel execution reduces wall-clock time from `N × latency` to `~1 × latency`. In Claude Code, this is triggered automatically when the assistant emits multiple independent tool calls in a single turn.
