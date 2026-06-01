"""
POC: Measurable criteria enable automated validation of output quality.

Demonstrates how embedding quantifiable constraints (word count, format,
required fields) into a prompt lets you programmatically verify that the
model's output meets a quality bar — no human review needed.
"""

import json
import os
from dotenv import load_dotenv
from anthropic import Anthropic

# Credentials stay in .env, never in source
load_dotenv()

client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
MODEL = "claude-sonnet-4-6"

# --- Prompt WITHOUT measurable criteria: quality is subjective, can't auto-validate ---
unmeasurable_prompt = "Write a product review for wireless headphones."

# --- Prompt WITH measurable criteria: every constraint maps to a programmatic check ---
measurable_prompt = (
    "Write a product review for wireless headphones as valid JSON with these exact keys:\n"
    '- "product_name": string, 2-5 words\n'
    '- "rating": integer from 1 to 5\n'
    '- "pros": array of exactly 3 strings, each under 15 words\n'
    '- "cons": array of exactly 2 strings, each under 15 words\n'
    '- "summary": string, exactly 1 sentence, 20-40 words\n\n'
    "Return ONLY the JSON object, no markdown fences or extra text."
)


# Each validator returns (pass/fail, reason) — mirrors how CI pipelines gate on assertions
VALIDATORS = {
    "valid_json": lambda output: validate_json(output),
    "has_required_keys": lambda parsed: validate_keys(parsed),
    "product_name_length": lambda parsed: validate_word_range(parsed.get("product_name", ""), 2, 5, "product_name"),
    "rating_range": lambda parsed: validate_rating(parsed),
    "pros_count": lambda parsed: validate_array_len(parsed.get("pros", []), 3, "pros"),
    "cons_count": lambda parsed: validate_array_len(parsed.get("cons", []), 2, "cons"),
    "pros_word_limit": lambda parsed: validate_items_word_limit(parsed.get("pros", []), 15, "pros"),
    "cons_word_limit": lambda parsed: validate_items_word_limit(parsed.get("cons", []), 15, "cons"),
    "summary_word_range": lambda parsed: validate_word_range(parsed.get("summary", ""), 20, 40, "summary"),
}

REQUIRED_KEYS = {"product_name", "rating", "pros", "cons", "summary"}


def validate_json(raw: str):
    try:
        json.loads(raw)
        return True, "Valid JSON"
    except json.JSONDecodeError as e:
        return False, f"Invalid JSON: {e}"


def validate_keys(parsed: dict):
    missing = REQUIRED_KEYS - set(parsed.keys())
    if missing:
        return False, f"Missing keys: {missing}"
    return True, "All required keys present"


def validate_word_range(text: str, lo: int, hi: int, field: str):
    # Word count is unambiguous — machines count the same way every time
    count = len(text.split())
    if lo <= count <= hi:
        return True, f"{field}: {count} words (range {lo}-{hi})"
    return False, f"{field}: {count} words, expected {lo}-{hi}"


def validate_rating(parsed: dict):
    r = parsed.get("rating")
    # Type + range check: catches strings, floats, out-of-bounds ints
    if isinstance(r, int) and 1 <= r <= 5:
        return True, f"Rating {r} in range 1-5"
    return False, f"Rating '{r}' not an int in 1-5"


def validate_array_len(arr, expected: int, field: str):
    if not isinstance(arr, list):
        return False, f"{field}: not an array"
    if len(arr) == expected:
        return True, f"{field}: exactly {expected} items"
    return False, f"{field}: {len(arr)} items, expected {expected}"


def validate_items_word_limit(items: list, max_words: int, field: str):
    # Per-item word cap prevents verbose, low-signal bullets
    for i, item in enumerate(items):
        count = len(str(item).split())
        if count > max_words:
            return False, f"{field}[{i}]: {count} words, max {max_words}"
    return True, f"{field}: all items under {max_words} words"


def call_model(prompt: str) -> str:
    response = client.messages.create(
        model=MODEL,
        max_tokens=512,
        # temperature=0 isolates prompt design from sampling randomness
        temperature=0,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text


def run_validation(output: str) -> dict:
    """Run every validator against the output, return a scorecard."""
    results = {}

    # JSON validity must pass first — all other checks depend on parsed data
    is_valid, reason = validate_json(output)
    results["valid_json"] = {"pass": is_valid, "reason": reason}

    if not is_valid:
        # Short-circuit: no point running structural checks on unparseable text
        for name in VALIDATORS:
            if name != "valid_json":
                results[name] = {"pass": False, "reason": "Skipped — invalid JSON"}
        return results

    parsed = json.loads(output)

    for name, validator in VALIDATORS.items():
        if name == "valid_json":
            continue
        passed, reason = validator(parsed)
        results[name] = {"pass": passed, "reason": reason}

    return results


def print_scorecard(results: dict):
    total = len(results)
    passed = sum(1 for r in results.values() if r["pass"])
    print(f"\n{'─'*55}")
    print(f"  VALIDATION SCORECARD: {passed}/{total} checks passed")
    print(f"{'─'*55}")
    for name, result in results.items():
        icon = "PASS" if result["pass"] else "FAIL"
        print(f"  [{icon}] {name}: {result['reason']}")
    print(f"{'─'*55}")
    # Single pass/fail verdict — suitable for CI exit codes
    print(f"  OVERALL: {'PASS' if passed == total else 'FAIL'}")
    print()


def main():
    # --- Part 1: Unmeasurable prompt — output can't be auto-validated ---
    print("=" * 55)
    print("PROMPT WITHOUT MEASURABLE CRITERIA")
    print("=" * 55)
    unmeasurable_output = call_model(unmeasurable_prompt)
    print(unmeasurable_output)
    print("\n[No automated validation possible — quality is subjective]")

    # --- Part 2: Measurable prompt — every constraint has a matching validator ---
    print("\n" + "=" * 55)
    print("PROMPT WITH MEASURABLE CRITERIA")
    print("=" * 55)
    measurable_output = call_model(measurable_prompt)
    print(measurable_output)

    results = run_validation(measurable_output)
    print_scorecard(results)


if __name__ == "__main__":
    main()
