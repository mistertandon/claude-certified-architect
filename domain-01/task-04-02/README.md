# Task 04-02: fork_session — Branch Sessions for Exploration

## Concept

`fork_session` copies the current conversation history so Claude can explore a tangent (compare options, debug a theory, brainstorm) **without adding noise to the main context**. Only the distilled insight is merged back.

```
Main Session ──► [Q1] ──► [A1] ──────────────────────► [Insight + Q3] ──► [A3]
                              \                        ▲
                               ├── Fork ──► [Q2a] ──► [A2a] ──► [Q2b] ──► [A2b]
                               (exploration happens here, main never sees it)
```

## Why This Matters

| Problem | How fork_session solves it |
|---|---|
| Exploratory turns consume token budget | Fork absorbs them; main stays lean |
| Context window fills with tangents | Main only sees the final conclusion |
| Backtracking is expensive | Discard the fork — zero cost to main |

## Setup

```bash
cd domain-01/task-04-02
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Configure

Edit `.env` and set your API key:

```
ANTHROPIC_API_KEY=sk-ant-...
MODEL_NAME=claude-sonnet-4-6
```

## Run

```bash
python fork_session.py
```

## Expected Output

1. **Step 1** — Main session establishes context (bookstore API design)
2. **Step 2** — Forked session explores pagination strategies across 2 turns
3. **Step 3** — Only the final recommendation is merged back into main
4. **Comparison** — Main has fewer messages than the fork, proving context isolation
