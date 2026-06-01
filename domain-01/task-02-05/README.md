# Task 01-02-05: Fork Session — Branched Parallel Exploration

## Concept

`fork_session` creates **branched sessions** from a shared conversation trunk. Each fork inherits the same base context but diverges independently — no fork can see or pollute a sibling's responses.

```
  [User] → [Assistant]          ← shared trunk (2 messages)
        ├── Fork A: token_bucket_deep_dive
        ├── Fork B: sliding_window_deep_dive
        └── Fork C: tradeoff_analysis
```

## How It Maps to Claude Code

| Claude Code Internals | This POC |
|---|---|
| `fork_session` creates a branched context | `copy.deepcopy(BASE_MESSAGES)` per fork |
| Parent context is preserved, not mutated | Deep copy ensures trunk stays read-only |
| Sibling forks are isolated | Each `run_fork()` has its own message list |
| Parallel execution | `asyncio.gather()` fires all forks concurrently |

## Setup

```bash
cd domain-01/task-01-02-05

# 1. Create & activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 2. Install dependencies
pip install anthropic python-dotenv

# 3. Configure API key
#    Edit the .env file and replace 'your-api-key-here' with your actual key
nano .env
```

## Run

```bash
python fork_session.py
```

## Expected Output

```
================================================================
  Fork Session Complete — 3 branches, ~1.5s wall time
================================================================

  Shared Trunk (2 messages):
    [user] We need to build a rate limiter for our API. What approaches...
    [assistant] Common approaches: (1) Token Bucket, (2) Sliding Window...

────────────────────────────────────────────────────────────────

  Fork: token_bucket_deep_dive (context depth: 3 messages)
  ────────────────────────────────────────
    <token bucket implementation>

  Fork: sliding_window_deep_dive (context depth: 3 messages)
  ────────────────────────────────────────
    <sliding window implementation>

  Fork: tradeoff_analysis (context depth: 3 messages)
  ────────────────────────────────────────
    <comparison analysis>

================================================================
  Key point: each fork saw the shared trunk but NOT sibling responses.
================================================================
```

## Key Takeaway

Fork session enables **parallel exploration without context pollution**. The shared trunk provides common ground; each fork adds its own direction. This is how Claude Code lets you explore multiple solution paths simultaneously — each branch reasons independently from the same starting point.
