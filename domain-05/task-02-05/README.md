# Partial Results + What Was Attempted — POC

Demonstrates the resilience pattern where a multi-step pipeline **always reports progress**, even when steps fail mid-execution.

## Why This Matters

When a 4-step pipeline fails on step 2, you have two choices:

```
BAD:   raise Exception("step 2 failed")          → steps 1, 3, 4 results lost
GOOD:  return PipelineReport(partial_results=...) → steps 1, 3, 4 results preserved
```

Returning partial results means:
- **No wasted work** — completed steps are immediately usable
- **Debuggable failures** — the report shows exactly which step failed and why
- **Informed retries** — callers know what to retry without re-running the whole pipeline

## Setup

```bash
cd domain-05/task-02-05

# 1. Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
# Edit .env and replace 'your-api-key-here' with a valid Anthropic API key
nano .env
```

## Run

```bash
python main.py
```

## Expected Output

```
=======================================================
PARTIAL RESULTS + WHAT WAS ATTEMPTED
Always report progress — even on failure
=======================================================

#######################################################
SCENARIO: All steps succeed (baseline)
#######################################################

  [define] running...
  [define] SUCCESS
  [history] running...
  [history] SUCCESS
  [application] running...
  [application] SUCCESS
  [future] running...
  [future] SUCCESS

  ──────────────────────────────────────────────────────
  PIPELINE REPORT
  ──────────────────────────────────────────────────────
  Task:            Research: machine learning
  Overall:         success
  Steps attempted: 4
  Steps succeeded: 4
  Steps failed:    0

  PARTIAL RESULTS (usable even though pipeline succeeded):
    [define] Machine learning is ...
    [history] The most important milestone ...
    [application] One real-world application ...
    [future] One future development ...
  ──────────────────────────────────────────────────────

#######################################################
SCENARIO: Mid-pipeline failure (partial results preserved)
#######################################################

  [define] running...
  [define] SUCCESS
  [history] running...
  [history] FAILED (sabotaged)
  [application] running...
  [application] SUCCESS               ← pipeline continued past failure
  [future] running...
  [future] SUCCESS                    ← this result would be lost without partial reporting

  ──────────────────────────────────────────────────────
  PIPELINE REPORT
  ──────────────────────────────────────────────────────
  Task:            Research: machine learning
  Overall:         partial_failure
  Steps attempted: 4
  Steps succeeded: 3                  ← 3 out of 4 results preserved
  Steps failed:    1

  PARTIAL RESULTS (usable even though pipeline failed):
    [define] Machine learning is ...
    [application] One real-world application ...
    [future] One future development ...

  FAILURES (what went wrong and where):
    [history] simulated_failure: step deliberately sabotaged for demo
  ──────────────────────────────────────────────────────
```

## Key Concept for Exam

| Principle | What It Means |
|-----------|---------------|
| **Never return None on failure** | Always return a structured report — callers need data, not silence |
| **Catch per step, not per pipeline** | Wrapping the whole pipeline in try/except loses partial results |
| **Continue past failures** | Steps after a failure may still succeed — don't short-circuit |
| **Report what was attempted** | `steps_attempted`, `steps_succeeded`, `steps_failed` tell the full story |

### Anti-pattern (what NOT to do)

```python
# BAD: one try/except around the entire pipeline — all-or-nothing
def pipeline(topic):
    try:
        r1 = step_define(topic)
        r2 = step_history(topic)     # if this throws...
        r3 = step_application(topic) # ...r3 and r4 never run
        r4 = step_future(topic)
        return {"results": [r1, r2, r3, r4]}
    except Exception:
        return None                  # r1 is lost, no failure details
```

### Correct pattern

```python
# GOOD: catch per step, accumulate into a report
def pipeline(topic):
    report = PipelineReport(task=topic)
    for step in steps:
        try:
            result = step.run(topic)
            report.add(StepOutcome(step.name, "success", result))
        except Exception as e:
            report.add(StepOutcome(step.name, "failed", error=str(e)))
            # continue — don't break
    return report  # always returned, always has data
```
