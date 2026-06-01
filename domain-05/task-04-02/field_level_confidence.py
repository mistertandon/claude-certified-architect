"""
Field-Level Confidence Indicators — Structured Extraction POC

When extracting structured data from messy real-world text, not every field
is equally trustworthy. This POC asks Claude to self-assess confidence per
field — so downstream systems can auto-accept high-confidence values and
route low-confidence ones to human review.
"""

import os
import json

import anthropic
from dotenv import load_dotenv

# .env lives next to this script, not in the caller's cwd
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

client = anthropic.Anthropic()

# --- Model returns structured JSON via tool use, eliminating brittle text parsing ---
EXTRACTION_TOOL = {
    "name": "submit_extraction",
    "description": (
        "Submit extracted fields from the document. "
        "For EVERY field, include a confidence score (0.0–1.0) and a brief reason."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "fields": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Field name (e.g. 'company_name', 'total_amount')"
                        },
                        "value": {
                            "type": "string",
                            "description": "Extracted value"
                        },
                        "confidence": {
                            "type": "number",
                            "description": "0.0 = pure guess, 1.0 = explicitly stated in text"
                        },
                        "reason": {
                            "type": "string",
                            "description": "Why this confidence level — what evidence supports or undermines it"
                        }
                    },
                    "required": ["name", "value", "confidence", "reason"]
                }
            }
        },
        "required": ["fields"]
    }
}

# Deliberately messy input — some fields are clear, others ambiguous or missing
SAMPLE_DOCUMENT = """
From: j.martinez@acmecorp.com
Date: Jan 15 2025

Hi,

Attached is the invoice. Total comes to around $12,400 — though we're still
waiting on the final shipping costs from the warehouse, so that might change
by a couple hundred bucks. PO number is #PO-2025-0042.

Payment terms are the usual net-30 unless your finance team needs net-60
again like last quarter.

Thanks,
Jorge
"""

SYSTEM_PROMPT = """You are a document extraction specialist. Extract structured
fields from the provided document. For each field, honestly assess your
confidence based on how explicitly the information appears in the text.

Confidence scale:
- 0.9–1.0: Value is explicitly and unambiguously stated
- 0.7–0.8: Value is clearly implied or stated with minor ambiguity
- 0.4–0.6: Value requires inference or is stated as approximate/uncertain
- 0.0–0.3: Value is a guess based on weak signals or convention

Extract these fields: sender_name, sender_email, company_name, invoice_total,
po_number, payment_terms, invoice_date, shipping_cost."""


def extract_with_confidence(document: str) -> list[dict]:
    # tool_choice="any" forces Claude to respond via the tool, not free text
    response = client.messages.create(
        model="claude-sonnet-4-6-20250514",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        tools=[EXTRACTION_TOOL],
        # "any" guarantees structured output — no fallback to prose
        tool_choice={"type": "any"},
        messages=[{"role": "user", "content": document}]
    )

    # With tool_choice="any", first content block is always a tool_use
    tool_block = next(b for b in response.content if b.type == "tool_use")
    return tool_block.input["fields"]


def classify_confidence(score: float) -> str:
    """Map numeric score to action — the thresholds drive a human-in-the-loop workflow."""
    if score >= 0.8:
        return "AUTO_ACCEPT"
    elif score >= 0.5:
        return "FLAG_FOR_REVIEW"
    else:
        return "REJECT / MANUAL_ENTRY"


def display_results(fields: list[dict]) -> None:
    print("\n" + "=" * 72)
    print("FIELD-LEVEL CONFIDENCE REPORT")
    print("=" * 72)

    # Sort descending so reviewer sees most-trusted fields first
    for f in sorted(fields, key=lambda x: x["confidence"], reverse=True):
        action = classify_confidence(f["confidence"])
        bar = render_confidence_bar(f["confidence"])

        print(f"\n  {f['name']}")
        print(f"    Value      : {f['value']}")
        print(f"    Confidence : {f['confidence']:.1f}  {bar}  [{action}]")
        print(f"    Reason     : {f['reason']}")

    print("\n" + "-" * 72)
    print_summary(fields)


def render_confidence_bar(score: float, width: int = 20) -> str:
    filled = round(score * width)
    return f"[{'█' * filled}{'░' * (width - filled)}]"


def print_summary(fields: list[dict]) -> None:
    """Show counts per action bucket — gives a quick triage overview."""
    buckets = {"AUTO_ACCEPT": 0, "FLAG_FOR_REVIEW": 0, "REJECT / MANUAL_ENTRY": 0}
    for f in fields:
        buckets[classify_confidence(f["confidence"])] += 1

    print("\nSUMMARY:")
    for action, count in buckets.items():
        print(f"  {action:25s}: {count}")
    print()


if __name__ == "__main__":
    print("Extracting fields from document with confidence indicators...")
    fields = extract_with_confidence(SAMPLE_DOCUMENT)
    display_results(fields)

    # Dump raw JSON for programmatic consumers
    print("Raw JSON output:")
    print(json.dumps(fields, indent=2))
