"""
Prompt Design Principle: Explicit Criteria vs Vague Instructions

Demonstrates why 'flag functions over 50 lines' produces reliable,
consistent output while 'flag long functions' yields subjective,
unpredictable results.
"""

import os
from pathlib import Path

import anthropic
from dotenv import load_dotenv

load_dotenv()


def load_sample_code() -> str:
    return Path(__file__).with_name("sample_code.py").read_text()


# ── Prompt A: Vague instruction ─────────────────────────────────────────
# "long" is subjective — the model must guess a threshold, leading to
# inconsistent results across runs and models.
VAGUE_PROMPT = """Review this Python code and flag any long functions.

```python
{code}
```"""

# ── Prompt B: Explicit criteria ─────────────────────────────────────────
# Measurable thresholds (50 lines, 5 params) eliminate ambiguity, making
# output deterministic and auditable regardless of model version.
EXPLICIT_PROMPT = """Review this Python code. Flag any function that meets
ONE OR MORE of these criteria:

1. Body exceeds 50 lines (count from `def` to last statement)
2. Has more than 5 parameters
3. Contains nested conditionals deeper than 2 levels

For each flagged function, report:
- Function name
- Which criteria it violates (cite the number)
- The measured value (e.g., "62 lines", "8 parameters")

Output ONLY the flagged functions. If none qualify, respond "No issues found."

```python
{code}
```"""


def run_review(prompt_template: str, label: str, code: str) -> str:
    # Single client instance — reused connection avoids TCP/TLS overhead.
    client = anthropic.Anthropic()

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        messages=[
            {
                "role": "user",
                "content": prompt_template.format(code=code),
            }
        ],
    )

    result = response.content[0].text
    print(f"\n{'='*60}")
    print(f"  {label}")
    print(f"{'='*60}")
    print(result)
    return result


def main():
    code = load_sample_code()

    # Run both prompts against identical code so the ONLY variable is
    # prompt specificity — isolates the design principle under test.
    run_review(VAGUE_PROMPT, "VAGUE: 'flag long functions'", code)
    run_review(EXPLICIT_PROMPT, "EXPLICIT: 'flag functions over 50 lines'", code)

    print(f"\n{'='*60}")
    print("  KEY TAKEAWAY")
    print(f"{'='*60}")
    print(
        "The vague prompt leaves 'long' to the model's judgment — results\n"
        "vary across runs. The explicit prompt sets measurable thresholds\n"
        "(50 lines, 5 params, nesting depth 2), producing consistent,\n"
        "auditable output every time."
    )


if __name__ == "__main__":
    main()
