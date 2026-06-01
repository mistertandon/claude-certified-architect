# Few-Shot Prompting — Sentiment Classifier

Demonstrates **2-4 example few-shot prompting** to establish output format and reasoning patterns for an ambiguous classification task.

## Why few-shot?

- **0-shot** works for clear-cut tasks but struggles with ambiguous/mixed sentiments.
- **2-4 examples** (the sweet spot) lock down the JSON schema, confidence calibration, and how to handle edge cases — without wasting tokens on redundant demonstrations.
- Examples are placed in the **system prompt** so they apply to every request without being resent per turn.

## Setup

```bash
cd domain-04/task-02-01

# 1. Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate

# 2. Install dependency
pip install anthropic python-dotenv

# 3. Configure your API key
cp .env .env.local
# Edit .env.local and replace `your-api-key-here` with your actual key
export ANTHROPIC_API_KEY="your-actual-key"
```

## Run

```bash
python few_shot_prompting.py
```

## Expected Output

```
Input : This product changed my life! I recommend it to everyone.
Output: {"sentiment": "POSITIVE", "confidence": 0.95, "reasoning": "..."}

Input : Decent build quality but the software is buggy and crashes often.
Output: {"sentiment": "MIXED", "confidence": 0.85, "reasoning": "..."}

Input : I returned it the same day. Complete waste of money.
Output: {"sentiment": "NEGATIVE", "confidence": 0.95, "reasoning": "..."}

Input : Not bad, not great. It exists.
Output: {"sentiment": "MIXED", "confidence": 0.75, "reasoning": "..."}
```

## Key Design Decisions

| Decision | Rationale |
|---|---|
| 4 examples (not 2, not 10) | Covers all 3 labels + extra MIXED case; ambiguous inputs benefit most from examples |
| Examples in system prompt | Cached across turns; avoids re-sending per request |
| JSON-only output | Structured format makes downstream parsing reliable |
| Confidence score included | Lets callers threshold on certainty for escalation workflows |
