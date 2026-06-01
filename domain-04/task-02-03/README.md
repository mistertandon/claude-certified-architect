# Few-Shot Prompting with Edge Case Coverage

Demonstrates few-shot prompting via the Anthropic SDK — a sentiment classifier that handles standard inputs and edge cases (empty input, mixed sentiment).

## Setup

```bash
cd domain-04/task-02-03

python -m venv venv
source venv/bin/activate

pip install anthropic python-dotenv
```

## Configure

Edit `.env` and replace the placeholder with your actual API key:

```
ANTHROPIC_API_KEY=sk-ant-...
```

## Run

```bash
python few_shot_edge_case.py
```

## Expected Output

```
Input: Classify sentiment: 'It works I guess, nothing special.'

Response:
sentiment: neutral
confidence: 0.75
reason: lukewarm acknowledgment without strong emotion
```

## Key Concepts

| Concept | How it's applied |
|---------|-----------------|
| Few-shot prompting | 4 user/assistant example pairs precede the real query |
| Edge case: empty input | Example shows model returning `unclassifiable` instead of guessing |
| Edge case: mixed sentiment | Example shows model acknowledging ambiguity with `mixed` label |
| Consistent format | Examples enforce `sentiment/confidence/reason` structure |
