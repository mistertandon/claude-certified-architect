# Task 01-03: Specificity Reduces Ambiguity

## Principle

A specific prompt constrains the model's output space — pinning format, scope, length, and audience — so results stay consistent across repeated runs. A vague prompt leaves these dimensions open, producing varied outputs each time.

## Setup

```bash
cd domain-04/task-01-03

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install anthropic python-dotenv
```

## Configure

Edit `.env` and replace the placeholder with your actual API key:

```
ANTHROPIC_API_KEY=sk-ant-...
```

## Run

```bash
python main.py
```

## What to Observe

1. **Vague prompt runs** — output varies in length, structure, and focus each time.
2. **Specific prompt runs** — output is nearly identical across all three runs (same bullets, same format).

This contrast demonstrates that specificity is the primary lever for consistency.
