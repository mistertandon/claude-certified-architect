# Lost in the Middle Effect — POC

Demonstrates that LLMs recall information placed at the **beginning** or **end** of a long context more reliably than information buried in the **middle**.

## Setup

```bash
cd domain-05/task-01-01-02

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install anthropic python-dotenv
```

## Configure

Edit `.env` and set your API key:

```
ANTHROPIC_API_KEY=sk-ant-...
MODEL_NAME=claude-sonnet-4-6
```

## Run

```bash
python lost_in_middle.py
```

## Expected Output

```
[Position: BEGINNING]
  Response: The secret project code name is AURORA-7749.
  Recalled correctly: YES

[Position: MIDDLE]
  Response: I could not find a specific project code name...
  Recalled correctly: NO

[Position: END]
  Response: The secret project code name is AURORA-7749.
  Recalled correctly: YES
```

## How It Works

1. A target fact (`AURORA-7749`) is embedded at three positions within a ~20-paragraph filler document
2. The model is asked to recall that fact for each position
3. Middle placement shows degraded recall — the "lost in the middle" effect

## Exam Relevance

- **Mitigation strategies**: place critical information at the start/end of prompts, use structured delimiters, or break long contexts into retrievable chunks (RAG).
- **Architecture implication**: when designing systems with large context windows, position-aware prompt engineering matters.
