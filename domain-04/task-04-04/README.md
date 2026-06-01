# Self-Review Limitations

  Key exam takeaway: Same-session self-review is ineffective because the model's prior reasoning stays in the conversation context, biasing it toward defending its own output. The fix is to use a separate       
  session (fresh messages list) or a different model as the reviewer.

---

Demonstrates why same-session self-review is weak — the model retains its reasoning context (anchoring bias) and tends to confirm rather than critique its own output.

## Core Concept

```
Session A: Generate code → Self-review → Biased (high confidence, few issues)
Session B: Review same code cold → Independent (lower confidence, more issues)
```

The same model, same prompt — but splitting into separate sessions removes the anchoring effect.

## Setup

```bash
cd domain-04/task-04-04
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
python self_review_limitation.py
```

## What to Expect

| Metric | Same-Session Review | Fresh-Session Review |
|--------|-------------------|---------------------|
| Confidence | Higher (7-9/10) | Lower (5-7/10) |
| Issues found | Fewer | More |
| Verdict | Usually "pass" | More likely "fail" |

## Why This Matters for the Architect Exam

- **Same session** = model has its original reasoning in context, anchoring it to defend its output
- **Fresh session** = no prior context, evaluates code on its own merits
- **Mitigation**: use separate API calls (fresh `messages` list) or a different model for review
- This is a fundamental limitation of single-agent validation loops
