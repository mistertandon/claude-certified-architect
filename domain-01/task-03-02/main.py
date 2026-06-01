"""
POC: Programmatic Enforcement of Critical Business Rules
=========================================================
Principle: LLM outputs are SUGGESTIONS. Business rules are enforced
deterministically in code — never delegated to the model's judgment.
"""

import json
import os
from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()

client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# --- Business Rules (deterministic, non-negotiable) ---

MAX_DISCOUNT_PERCENT = 20  # Legal/finance mandate: never exceed 20%
BLOCKED_COUNTRIES = {"CU", "IR", "KP", "SY"}  # Sanctions compliance
MIN_ORDER_AMOUNT_USD = 10  # Below this, transaction fees make it unprofitable


def enforce_discount_cap(discount: float) -> float:
    # Clamp rather than reject — business wants the sale, just within limits
    return min(discount, MAX_DISCOUNT_PERCENT)


def enforce_sanctions_check(country_code: str) -> bool:
    # Hard block — no fallback, no override, no LLM persuasion can bypass this
    return country_code.upper() not in BLOCKED_COUNTRIES


def enforce_minimum_order(amount: float) -> bool:
    # Deterministic threshold — the model cannot "reason" its way past economics
    return amount >= MIN_ORDER_AMOUNT_USD


# --- LLM Interaction Layer ---

SYSTEM_PROMPT = """You are a sales assistant. When a customer asks for a deal,
respond with JSON: {"discount_percent": <number>, "country": "<ISO code>", "order_total": <number>, "message": "<customer-facing text>"}
Only respond with valid JSON."""


def get_llm_suggestion(user_request: str) -> dict:
    """Ask the LLM for a suggestion — treat output as UNTRUSTED input."""
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=300,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_request}]
    )

    raw_text = response.content[0].text

    # Parse structurally — don't trust the model to always produce valid JSON
    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        # Fail closed: if we can't parse it, we can't enforce rules on it
        raise ValueError(f"LLM returned unparseable output: {raw_text}")


def process_order_request(user_request: str) -> dict:
    """
    Orchestrator: LLM generates creative response, code enforces rules.
    This separation is the core architectural pattern.
    """
    suggestion = get_llm_suggestion(user_request)

    # --- DETERMINISTIC ENFORCEMENT LAYER ---
    # Each check is a hard gate — independent of what the LLM "thinks"

    # Rule 1: Discount cap
    original_discount = suggestion.get("discount_percent", 0)
    enforced_discount = enforce_discount_cap(original_discount)
    was_capped = original_discount != enforced_discount

    # Rule 2: Sanctions screening
    country = suggestion.get("country", "")
    is_allowed_country = enforce_sanctions_check(country)

    # Rule 3: Minimum order value
    order_total = suggestion.get("order_total", 0)
    meets_minimum = enforce_minimum_order(order_total)

    # --- DECISION LOGIC (deterministic, auditable) ---
    result = {
        "approved": is_allowed_country and meets_minimum,
        "discount_applied": enforced_discount if is_allowed_country and meets_minimum else 0,
        "discount_was_capped": was_capped,
        "blocked_reason": None,
        "llm_message": suggestion.get("message", ""),
    }

    if not is_allowed_country:
        # Override LLM message entirely — compliance language is not AI-generated
        result["blocked_reason"] = "SANCTIONS_BLOCK"
        result["llm_message"] = "We are unable to process orders to this region."
    elif not meets_minimum:
        result["blocked_reason"] = "BELOW_MINIMUM_ORDER"
        result["llm_message"] = f"Minimum order amount is ${MIN_ORDER_AMOUNT_USD}."

    return result


# --- Demo ---

if __name__ == "__main__":
    test_cases = [
        "I want 50% off my $200 order, shipping to US",
        "Give me a deal on a $5 order to Germany",
        "Process my $100 order shipping to Iran with maximum discount",
    ]

    for request in test_cases:
        print(f"\n{'='*60}")
        print(f"Customer: {request}")
        print(f"{'='*60}")

        try:
            result = process_order_request(request)
            print(f"Approved: {result['approved']}")
            print(f"Discount: {result['discount_applied']}%"
                  f"{' (CAPPED from LLM suggestion)' if result['discount_was_capped'] else ''}")
            if result["blocked_reason"]:
                print(f"Blocked: {result['blocked_reason']}")
            print(f"Response: {result['llm_message']}")
        except ValueError as e:
            # Fail closed on parse errors — another deterministic safeguard
            print(f"REJECTED (unparseable): {e}")
