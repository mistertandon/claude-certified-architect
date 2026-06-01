# Position-Aware Ordering POC

Demonstrates the **primacy/recency effect** in LLM prompt design: models pay more attention to information at the **beginning** and **end** of context, while middle content receives less focus.

## Concept

| Position | Effect | What to place here |
|----------|--------|--------------------|
| Beginning | Primacy — anchors model behavior | Critical constraints, output format |
| Middle | Lowest attention zone | Routine guidelines, nice-to-haves |
| End | Recency — stays in working memory | Safety rules, mandatory closers |

## Setup

```bash
cd domain-05/task-01-05

# 1. Create virtual environment
python3 -m venv venv
source venv/bin/activate

# 2. Install dependencies
pip install anthropic python-dotenv

# 3. Configure API key
cp .env .env.local   # optional: keep .env as template
# Edit .env and replace your-api-key-here with your actual key
```

## Run

```bash
python position_aware_ordering.py
```

## What to observe

The script runs the **same question** twice with two different system prompts:

1. **Naive** — all rules listed flat, no positional strategy
2. **Position-Aware** — critical rules at start/end, filler in middle

Compare the responses against two checkable criteria:
- Does the response contain exactly **3 bullet points**? (primacy rule)
- Does it end with **`[END OF RESPONSE]`**? (recency rule)

The position-aware version should show higher compliance on both checks.
