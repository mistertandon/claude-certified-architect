# Task 01-04: Measurable Criteria Enable Automated Validation

## Principle

Embedding quantifiable constraints (word counts, field counts, format rules, value ranges) into a prompt turns subjective "is this good?" into objective pass/fail checks that code can run — enabling CI-style quality gates with no human in the loop.

## Setup

```bash
cd domain-04/task-01-04

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

1. **Unmeasurable prompt** — produces free-form text. You can read it, but no code can decide if it's "good enough."
2. **Measurable prompt** — produces structured JSON. Every constraint in the prompt maps to a validator that returns pass/fail.
3. **Scorecard** — prints a per-check breakdown plus an overall PASS/FAIL verdict, exactly like a test suite.

The contrast shows that measurable criteria are the bridge between prompt engineering and automated quality assurance.
