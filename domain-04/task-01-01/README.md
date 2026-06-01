# Prompt Design: Explicit Criteria vs Vague Instructions
  Core principle demonstrated: The vague prompt ("flag long functions") leaves the threshold to the model's judgment, producing inconsistent results. The explicit prompt ("flag functions over 50 lines, >5       
  params, nesting >2") sets measurable criteria, making output deterministic and auditable — critical for production systems.

## Concept

This POC contrasts two prompt styles for the same code review task:

| Style | Prompt | Problem |
|-------|--------|---------|
| **Vague** | *"flag long functions"* | "Long" is subjective — model guesses a threshold |
| **Explicit** | *"flag functions over 50 lines, >5 params, nesting >2"* | Measurable criteria → consistent, auditable output |

## Setup

```bash
cd domain-04/task-01-01

# 1. Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 2. Install dependencies
pip install anthropic python-dotenv

# 3. Configure API key
cp .env .env.local
# Edit .env.local and set your actual ANTHROPIC_API_KEY
```

## Run

```bash
python main.py
```

## Expected Output

Two reviews of the same `sample_code.py`:

1. **Vague prompt** — inconsistent; may or may not flag functions, with varying reasoning
2. **Explicit prompt** — deterministic; flags `process_order` citing exact violations:
   - Body exceeds 50 lines
   - More than 5 parameters (has 20)
   - Nested conditionals deeper than 2 levels

## Exam Takeaway

> When designing prompts for production systems, replace subjective adjectives
> ("long", "complex", "clean") with **measurable thresholds** — this makes
> outputs reproducible, testable, and auditable.
