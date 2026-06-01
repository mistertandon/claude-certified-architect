# Local Recovery Before Coordinator Escalation — POC

Demonstrates the multi-agent pattern where a worker agent **tries to fix failures locally** before escalating to a coordinator agent.

## Why This Matters

Escalating every failure to a coordinator is expensive (extra API calls) and slow (round-trip latency). The local-first recovery pattern ensures:

- **Fast resolution** — transient issues (corrupt input, rate limits) are fixed in-place
- **Cost efficiency** — coordinator only activates when genuinely needed
- **Auditability** — escalation carries what was already tried, so the coordinator doesn't repeat failed strategies

```
Worker fails → retry locally → sanitize → simplify → STILL failing? → escalate to coordinator
                ─────────── local recovery ───────────               ──── coordinator ────
```

## Setup

```bash
cd domain-05/task-02-04

# 1. Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env .env.local
# Edit .env and replace 'your-api-key-here' with a valid Anthropic API key
```

## Run

```bash
python main.py
```

## Expected Output

```
=======================================================
LOCAL RECOVERY BEFORE COORDINATOR ESCALATION
=======================================================

#######################################################
SCENARIO: Clean input (no escalation needed)
#######################################################

───────────────────────────────────────────────────────
WORKER received task: Explain what photosynthesis is
───────────────────────────────────────────────────────
  [worker] attempt 1 -> SUCCESS

  FINAL OUTCOME: SUCCESS
  Resolved by: worker

#######################################################
SCENARIO: Corrupt input (worker self-heals)
#######################################################

───────────────────────────────────────────────────────
WORKER received task: Explain what photosynthesis is
───────────────────────────────────────────────────────
  [worker] attempt 1 -> FAILED (corrupt input detected)
  [worker] LOCAL RECOVERY 1 -> sanitizing input and retrying
  [worker] attempt 2 -> SUCCESS

  FINAL OUTCOME: SUCCESS
  Resolved by: worker                    ← recovered locally, no escalation

#######################################################
SCENARIO: Forced escalation to coordinator
#######################################################

=======================================================
COORDINATOR activated (worker escalated)
=======================================================
  [coordinator] received escalation -> 3 worker attempts failed
  Strategies already tried by worker: ['direct_process', 'sanitize_retry', 'simplify']
  [coordinator] STRATEGY -> rephrasing task from scratch
  [coordinator] rephrase+solve -> SUCCESS

  FINAL OUTCOME: SUCCESS
  Result: Quantum entanglement is ...     ← coordinator resolved it
```

## Key Concept for Exam

| Phase | Who Acts | Strategy | When |
|-------|----------|----------|------|
| Attempt 1 | Worker | Process directly | Always |
| Recovery 1 | Worker | Sanitize + retry | After first failure |
| Recovery 2 | Worker | Simplify request | After sanitize fails |
| Escalation | Coordinator | Rephrase from scratch | After ALL local recovery fails |

**The escalation payload carries `strategies_tried`** — this prevents the coordinator from wasting tokens repeating what already failed.

### Anti-pattern (what NOT to do)

```python
# BAD: escalate immediately on first failure
def worker(task):
    result = process(task)
    if not result.success:
        return escalate(task)  # expensive, slow, unnecessary for transient issues
```

### Correct pattern

```python
# GOOD: exhaust local recovery, then escalate with context
def worker(task):
    result = process(task)
    if not result.success:
        result = retry_with_sanitized(task)    # local fix 1
    if not result.success:
        result = retry_simplified(task)         # local fix 2
    if not result.success:
        return escalate(task, tried=["sanitize", "simplify"])  # carry context
```
