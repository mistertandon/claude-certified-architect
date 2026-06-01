# Task 04-02: Dismissal Pattern Tracker

Core idea: The detected_pattern fields aggregate per-pattern dismissal data. When missing-null-check gets dismissed 6 out of 7 times with varied reasons, that's a systematic signal — either the rule is too    
  noisy or the codebase has a real gap that reviewers keep working around. The LLM analyzes these fields and recommends: suppress the rule, fix the root cause, or escalate.   

---

Demonstrates **`detected_pattern` fields** — tracking how often reviewers dismiss
specific findings to surface systematic issues in validation/review workflows.

## Concept

When a code-review bot flags issues, reviewers can dismiss them. Individual dismissals
are normal. But when the *same pattern* is dismissed repeatedly, it signals either:

- **A noisy rule** that should be tuned or suppressed
- **A deeper codebase problem** that reviewers are working around

The `detected_pattern` fields aggregate this dismissal data so an LLM can analyze
trends and recommend action.

## Key Fields Tracked

| Field               | Purpose                                      |
|---------------------|----------------------------------------------|
| `dismissal_count`   | Total times this pattern was dismissed        |
| `dismissal_rate`    | Ratio of dismissed vs total occurrences       |
| `dismissal_reasons` | Raw reviewer reasons — LLM judges quality     |
| `flagged_as_systematic` | True when count ≥ 3 (threshold-based flag) |

## Setup

```bash
cd domain-04/task-04-02

python -m venv .venv
source .venv/bin/activate

pip install anthropic python-dotenv
```

## Configure

Edit `.env` and set your API key:

```
ANTHROPIC_API_KEY=sk-ant-...
```

## Run

```bash
python dismissal_pattern_tracker.py
```

## Expected Output

1. **Detected Patterns** — aggregated dismissal stats per pattern, with systematic flags
2. **Claude Analysis** — LLM interpretation of whether dismissals are justified or hiding risk
3. **Summary** — counts of total patterns, systematic flags, and dismissals
