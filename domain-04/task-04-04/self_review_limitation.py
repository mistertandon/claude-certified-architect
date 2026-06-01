"""
Self-Review Limitation Demo:
Shows why asking the SAME session to review its own output is weak —
the model retains its reasoning context and is biased toward confirming
its prior answer. Contrasts with a FRESH session review.
"""

import os
import json
from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()

client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
MODEL = "claude-sonnet-4-6"

# Deliberately tricky prompt where the model might produce a subtly wrong answer
CODING_TASK = """Write a Python function `merge_sorted(a, b)` that merges two sorted lists
into one sorted list. Do NOT use built-in sort. Return the result.
Important: handle duplicates by keeping all copies.
Also write a brief explanation of the time complexity."""

REVIEW_PROMPT = """Review the code you just wrote for correctness.
Look for:
- Off-by-one errors
- Missing edge cases (empty lists, single element, all duplicates)
- Incorrect complexity analysis
Be brutally honest. Rate confidence 1-10 that the code is bug-free.
Return JSON: {"issues_found": [...], "confidence": <int>, "verdict": "pass"|"fail"}"""


def step1_generate_code() -> tuple[list[dict], str]:
    """Generate code in a fresh session, return messages history + response."""
    messages = [{"role": "user", "content": CODING_TASK}]

    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        messages=messages,
    )

    assistant_text = response.content[0].text

    # Keep full conversation history — this is what causes the bias
    messages.append({"role": "assistant", "content": assistant_text})

    return messages, assistant_text


def step2_same_session_review(messages: list[dict]) -> dict:
    """Ask the SAME conversation to review its own code.
    The model still holds its original reasoning, making it
    predisposed to defend rather than critique its own output."""

    # Appending review request to existing conversation preserves context
    messages.append({"role": "user", "content": REVIEW_PROMPT})

    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        messages=messages,
    )

    return response.content[0].text


def step3_fresh_session_review(code_text: str) -> str:
    """Send the code to a BRAND NEW session with zero prior context.
    No reasoning history means no anchoring bias — the reviewer
    evaluates the code purely on its merits."""

    # Fresh messages list = fresh session = no shared reasoning context
    review_messages = [
        {
            "role": "user",
            "content": f"""Review this code for correctness. You did NOT write it.
Look for:
- Off-by-one errors
- Missing edge cases (empty lists, single element, all duplicates)
- Incorrect complexity analysis
Be brutally honest. Rate confidence 1-10 that the code is bug-free.
Return JSON: {{"issues_found": [...], "confidence": <int>, "verdict": "pass"|"fail"}}

Code to review:
```python
{code_text}
```""",
        }
    ]

    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        # No system prompt linking this to the author session
        messages=review_messages,
    )

    return response.content[0].text


def extract_json(text: str) -> dict | None:
    """Best-effort JSON extraction from model output."""
    try:
        start = text.index("{")
        end = text.rindex("}") + 1
        return json.loads(text[start:end])
    except (ValueError, json.JSONDecodeError):
        return None


def main():
    print("=" * 70)
    print("SELF-REVIEW LIMITATION DEMO")
    print("=" * 70)

    # --- Step 1: Generate code ---
    print("\n[Step 1] Generating code in Session A...\n")
    messages, code_output = step1_generate_code()
    print(code_output[:500] + ("..." if len(code_output) > 500 else ""))

    # --- Step 2: Same-session review (biased) ---
    print("\n" + "-" * 70)
    print("[Step 2] SAME-SESSION review (Session A reviews its own code)...\n")
    same_review_raw = step2_same_session_review(messages)
    print(same_review_raw[:500] + ("..." if len(same_review_raw) > 500 else ""))
    same_review = extract_json(same_review_raw)

    # --- Step 3: Fresh-session review (independent) ---
    print("\n" + "-" * 70)
    print("[Step 3] FRESH-SESSION review (Session B reviews Session A's code)...\n")
    fresh_review_raw = step3_fresh_session_review(code_output)
    print(fresh_review_raw[:500] + ("..." if len(fresh_review_raw) > 500 else ""))
    fresh_review = extract_json(fresh_review_raw)

    # --- Comparison ---
    print("\n" + "=" * 70)
    print("COMPARISON")
    print("=" * 70)

    if same_review and fresh_review:
        print(f"\n  Same-session confidence : {same_review.get('confidence', '?')}/10")
        print(f"  Fresh-session confidence: {fresh_review.get('confidence', '?')}/10")
        print(f"  Same-session issues     : {len(same_review.get('issues_found', []))}")
        print(f"  Fresh-session issues    : {len(fresh_review.get('issues_found', []))}")
        print(f"  Same-session verdict    : {same_review.get('verdict', '?')}")
        print(f"  Fresh-session verdict   : {fresh_review.get('verdict', '?')}")

        # The key insight for the exam
        conf_same = same_review.get("confidence", 0)
        conf_fresh = fresh_review.get("confidence", 0)
        if conf_same >= conf_fresh:
            print("\n  >> Same-session was equally or MORE confident — demonstrates")
            print("     anchoring bias: the model defends its own prior reasoning.")
        else:
            print("\n  >> Unusual: fresh session was more confident.")
            print("     This can happen but is the exception, not the rule.")
    else:
        print("\n  Could not parse one or both reviews as JSON.")
        print("  Raw same-session review:")
        print(f"    {same_review_raw[:200]}")
        print("  Raw fresh-session review:")
        print(f"    {fresh_review_raw[:200]}")

    print("\n" + "=" * 70)
    print("KEY TAKEAWAY FOR ARCHITECT EXAM:")
    print("  Same-session self-review retains reasoning context,")
    print("  causing anchoring bias. For effective validation,")
    print("  use a SEPARATE session (or a separate model) as reviewer.")
    print("=" * 70)


if __name__ == "__main__":
    main()
