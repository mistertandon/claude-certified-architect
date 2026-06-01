# Task 03-02: Programmatic Enforcement of Critical Business Rules

## Core Concept

**Critical business rules must be enforced deterministically in code — not delegated to the LLM.**

The LLM is creative but probabilistic. Business rules (discount caps, sanctions, minimums) require 100% enforcement. This POC demonstrates the architectural pattern:

```
User Request → LLM (generates suggestion) → Enforcement Layer (deterministic code) → Final Decision
```

The LLM never makes the final call on compliance-critical logic.

## Setup

```bash
cd domain-01/task-03-02

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Configure

Edit `.env` and add your Anthropic API key:

```
ANTHROPIC_API_KEY=sk-ant-...
```

## Run

```bash
python main.py
```

## Expected Output

Three test scenarios demonstrating:

1. **Discount cap** — LLM suggests 50%, code clamps to 20%
2. **Minimum order** — $5 order rejected regardless of LLM response
3. **Sanctions block** — Iran order hard-blocked, LLM message overridden

## Key Architectural Takeaways

| Concern | Who Handles It | Why |
|---------|---------------|-----|
| Creative messaging | LLM | Probabilistic is fine for text |
| Discount calculation | Code | Finance rule — must be exact |
| Sanctions screening | Code | Legal compliance — zero tolerance |
| Order minimums | Code | Business economics — deterministic threshold |

## Anti-Pattern (what NOT to do)

```python
# WRONG: Asking the LLM to enforce rules
prompt = "Never give more than 20% discount..."
# The model CAN and WILL violate this under prompt injection or edge cases
```

## Correct Pattern (this POC)

```python
# RIGHT: Code enforces, LLM suggests
suggestion = get_llm_suggestion(request)
enforced_discount = min(suggestion["discount"], MAX_DISCOUNT)  # Deterministic
```
