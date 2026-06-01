# Task 04-04: Stale Context Detection & Mitigation in Long-Running Sessions

## Concept

In long-running Claude Code sessions (hours or days), earlier messages can become **stale** — the files, configs, or decisions they reference may no longer exist or may have been superseded. Claude keeps treating the entire context window as equally trustworthy, which leads to:

- Hallucinated references to deleted files or old variable names
- Contradictory advice when early assumptions conflict with later corrections
- Wasted token budget on outdated detail that no longer matters

```
Turn 1 (3 hours ago):  "Our DB is PostgreSQL 14 on db-prod-1"
Turn 47 (2 min ago):   "We migrated to PostgreSQL 16 on db-prod-2"
Turn 48 (now):         "What DB are we using?"

Without mitigation → Claude may cite PG 14 (stale) alongside PG 16 (current)
With mitigation    → Stale turns are compacted; Claude cites only PG 16
```

## Three Mitigation Strategies Demonstrated

| Strategy | How it works | Cost |
|---|---|---|
| **Timestamp tagging** | Every turn is prefixed with its age (`[180s ago]`). System prompt instructs Claude to prefer newer information on conflicts. | Zero — just string formatting |
| **Staleness audit** | Score each turn by age against a configurable threshold. Report freshness ratio and flag turns needing attention. | Zero — local computation only |
| **Context compaction** | Ask Claude to summarize stale turns into one recap message, then replace them. Frees token budget while preserving key decisions. | One extra API call per compaction |

## Setup

```bash
cd domain-01/task-04-04
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Configure

Edit `.env` and set your API key:

```
ANTHROPIC_API_KEY=sk-ant-...
MODEL_NAME=claude-sonnet-4-6
STALENESS_THRESHOLD_SECS=300
MAX_TURNS_BEFORE_COMPACTION=10
```

| Variable | Purpose | Default |
|---|---|---|
| `ANTHROPIC_API_KEY` | Anthropic API key | (required) |
| `MODEL_NAME` | Model to use | `claude-sonnet-4-6` |
| `STALENESS_THRESHOLD_SECS` | Seconds before a turn is considered stale | `300` |
| `MAX_TURNS_BEFORE_COMPACTION` | Turn count that triggers compaction | `10` |

## Run

### Scripted Demo (no interaction needed)

```bash
python stale_context.py --demo
```

Walks through 6 phases automatically:

1. **Establish context** — two turns set initial facts (PG 14, 100 req/s)
2. **Simulate staleness** — artificially age those turns past the threshold
3. **Introduce contradictions** — new turn updates the facts (PG 16, 500 req/s)
4. **Audit** — inspect freshness ratio and stale turn count
5. **Compact** — summarize stale turns into one recap, discard originals
6. **Verify** — ask Claude about current state; confirm it cites only fresh facts

### Interactive Mode

```bash
python stale_context.py
```

Chat freely and use these commands to observe staleness in real time:

| Command | Description |
|---|---|
| `/audit` | Show staleness report (total turns, stale count, freshness ratio) |
| `/compact` | Summarize and remove stale turns |
| `/history` | Show all turns with ages and stale markers |
| `/reset` | Clear the session |
| `/quit` | Exit |

### Example Interactive Workflow

```
You: Our API uses Flask with SQLAlchemy
  Claude: ...

You: The main model is in models/user.py
  Claude: ...

  (... time passes, you refactor the codebase ...)

You: Actually we moved to FastAPI and the model is now in app/schemas/user.py

You: /audit
  total_turns: 6
  stale_turns: 4
  freshness_ratio: 0.33
  needs_compaction: True

You: /compact
  Compacted: The project initially used Flask/SQLAlchemy but has migrated
  to FastAPI with models in app/schemas/user.py.

You: Where is the user model?
  Claude: Based on your recent update, the user model is in app/schemas/user.py.
```

## Expected Demo Output

1. **Phase 1** — Claude acknowledges PG 14 on db-prod-1, rate limit 100 req/s
2. **Phase 2** — Messages aged; new facts introduced (PG 16, db-prod-2, 500 req/s)
3. **Phase 3** — Audit shows stale turns and low freshness ratio
4. **Phase 4** — Compaction produces a short summary of outdated turns
5. **Phase 5** — Claude correctly cites PG 16 / db-prod-2 / 500 req/s (not the stale values)
6. **Phase 6** — Final stats show improved freshness ratio after compaction
