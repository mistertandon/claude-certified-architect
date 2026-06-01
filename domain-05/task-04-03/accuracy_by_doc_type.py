"""
Accuracy by Document Type — Per-Category Performance Tracking POC

Aggregate accuracy (e.g., 90% overall) can mask catastrophic failure on
specific document types. A system that nails invoices but botches contracts
looks great on average — until a contract error causes a legal dispute.
This POC tracks extraction accuracy per document category so weak spots
surface before they reach production.
"""

import os
import json
from collections import defaultdict

import anthropic
from dotenv import load_dotenv

# .env lives next to this script, not in the caller's cwd
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

client = anthropic.Anthropic()

# --- Tool schema forces Claude into structured JSON — no regex parsing needed ---
EXTRACTION_TOOL = {
    "name": "submit_extraction",
    "description": (
        "Submit extracted fields from the document. "
        "Return vendor, total_amount, date, and category for every document."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "vendor": {
                "type": "string",
                "description": "Company or person who issued the document"
            },
            "total_amount": {
                "type": "string",
                "description": "Total monetary amount (include currency symbol)"
            },
            "date": {
                "type": "string",
                "description": "Document date in YYYY-MM-DD format"
            },
            "category": {
                "type": "string",
                "description": "Document type: invoice, receipt, contract, or memo"
            }
        },
        "required": ["vendor", "total_amount", "date", "category"]
    }
}

SYSTEM_PROMPT = """You are a document extraction specialist. Extract these fields
from the provided document: vendor, total_amount, date, category.

Rules:
- date must be YYYY-MM-DD format
- total_amount must include currency symbol (e.g., $1,200.00)
- category must be exactly one of: invoice, receipt, contract, memo
- If a field is ambiguous, use your best judgment from context clues"""


# --- Ground-truth dataset: each doc has known correct answers for scoring ---
# Deliberately varied quality — invoices are clean, contracts are ambiguous,
# so per-category accuracy will diverge from aggregate.
EVAL_DATASET = [
    # INVOICES — explicit, structured, easy to extract
    {
        "doc_type": "invoice",
        "text": """
            INVOICE #2025-0331
            From: Acme Cloud Services
            Date: March 15, 2025

            Cloud hosting (March 2025)    $4,500.00
            SSL certificates (annual)       $120.00
            ─────────────────────────────────────────
            Total Due:                    $4,620.00
            Payment Terms: Net-30
        """,
        "ground_truth": {
            "vendor": "Acme Cloud Services",
            "total_amount": "$4,620.00",
            "date": "2025-03-15",
            "category": "invoice"
        }
    },
    {
        "doc_type": "invoice",
        "text": """
            Invoice from DataPipe Inc.
            Invoice Date: 2025-01-10

            Data pipeline maintenance (Q1)     $8,000.00
            Overage charges (Dec 2024)         $1,250.00
            ─────────────────────────────────────────
            Total:                             $9,250.00
        """,
        "ground_truth": {
            "vendor": "DataPipe Inc.",
            "total_amount": "$9,250.00",
            "date": "2025-01-10",
            "category": "invoice"
        }
    },
    # RECEIPTS — informal, abbreviated, missing some structure
    {
        "doc_type": "receipt",
        "text": """
            QuickMart Express
            04/02/2025  3:47 PM

            Office supplies      $34.99
            Printer paper x3     $29.97
            Tax                   $5.20
            TOTAL                $70.16

            VISA ending 4421
            Thank you!
        """,
        "ground_truth": {
            "vendor": "QuickMart Express",
            "total_amount": "$70.16",
            "date": "2025-04-02",
            "category": "receipt"
        }
    },
    {
        "doc_type": "receipt",
        "text": """
            CoffeeBean Roasters — Downtown
            Feb 28, 2025

            Team lunch catering
            12 sandwiches, 12 drinks
            Subtotal: $156.00
            Tip: $23.40
            Total charged: $179.40
        """,
        "ground_truth": {
            "vendor": "CoffeeBean Roasters",
            "total_amount": "$179.40",
            "date": "2025-02-28",
            "category": "receipt"
        }
    },
    # CONTRACTS — deliberately ambiguous: multiple dates, multiple parties,
    # amounts buried in legalese. This is where accuracy should drop.
    {
        "doc_type": "contract",
        "text": """
            SERVICE AGREEMENT

            This agreement is entered into on January 5, 2025, between
            NexGen Solutions LLC ("Provider") and GlobalTech Corp ("Client").

            The Provider shall deliver consulting services for a period of
            12 months commencing February 1, 2025. Total contract value
            shall not exceed $150,000, payable in quarterly installments
            of $37,500 each, with the first payment due upon execution
            of this agreement dated January 5, 2025.

            Amendment date: March 20, 2025
        """,
        "ground_truth": {
            # Ambiguity: is vendor the Provider or the Client?
            "vendor": "NexGen Solutions LLC",
            "total_amount": "$150,000",
            "date": "2025-01-05",
            "category": "contract"
        }
    },
    {
        "doc_type": "contract",
        "text": """
            LICENSING AGREEMENT — DRAFT v3

            Between: FreshData Analytics and our partner Meridian Corp
            Effective: TBD (targeting Q2 2025)

            FreshData grants Meridian a non-exclusive license to the
            DataStream platform. Annual license fee: approx $85K-$95K
            depending on final seat count. Initial term: 24 months.

            Last revised: April 10, 2025
        """,
        "ground_truth": {
            "vendor": "FreshData Analytics",
            # Ambiguous amount — a range, not a precise figure
            "total_amount": "$85,000",
            "date": "2025-04-10",
            "category": "contract"
        }
    },
    # MEMOS — internal, conversational tone, amounts and dates embedded in prose
    {
        "doc_type": "memo",
        "text": """
            Hey team,

            Quick update on the offsite budget. Sarah from Pinnacle Events
            quoted us $6,800 for the venue + catering for May 22nd.
            That's within our $7K cap so I went ahead and confirmed.

            Let me know if you have dietary restrictions by Friday.
            — Dana
        """,
        "ground_truth": {
            "vendor": "Pinnacle Events",
            "total_amount": "$6,800",
            "date": "2025-05-22",
            "category": "memo"
        }
    },
    {
        "doc_type": "memo",
        "text": """
            From: ops-team@internal
            Subject: Server migration costs
            Date sent: March 3, 2025

            FYI — RackSpace quoted the migration at somewhere between
            $22K and $28K. We'll know the final number once they scope
            the legacy DB. Budget meeting is March 15 to decide.
        """,
        "ground_truth": {
            "vendor": "RackSpace",
            # Another ambiguous range — tests whether model picks a point estimate
            "total_amount": "$22,000",
            "date": "2025-03-03",
            "category": "memo"
        }
    },
]


def extract_fields(document_text: str) -> dict:
    """Send one document to Claude and get structured extraction back."""
    response = client.messages.create(
        model="claude-sonnet-4-6-20250514",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        tools=[EXTRACTION_TOOL],
        # "any" guarantees structured output — no free-text fallback
        tool_choice={"type": "any"},
        messages=[{"role": "user", "content": document_text}]
    )

    # With tool_choice="any", first content block is always tool_use
    tool_block = next(b for b in response.content if b.type == "tool_use")
    return tool_block.input


def normalize(value: str) -> str:
    """Lowercase and strip whitespace/punctuation for fuzzy matching.

    Without normalization, '$4,620.00' != '$4620' would count as a miss
    even though both are correct — inflating false negatives.
    """
    return value.lower().strip().replace(",", "").replace(".", "").replace("$", "")


def score_extraction(predicted: dict, ground_truth: dict) -> dict[str, bool]:
    """Compare each extracted field against ground truth, return per-field pass/fail."""
    results = {}
    for field in ["vendor", "total_amount", "date", "category"]:
        pred_val = normalize(predicted.get(field, ""))
        true_val = normalize(ground_truth.get(field, ""))
        # Substring match catches partial-but-correct extractions
        # e.g., "CoffeeBean Roasters" vs "CoffeeBean Roasters — Downtown"
        results[field] = pred_val in true_val or true_val in pred_val
    return results


def compute_metrics(all_results: list[dict]) -> dict:
    """Aggregate per-category and overall accuracy from scored results."""
    by_category = defaultdict(lambda: {"correct": 0, "total": 0, "field_scores": defaultdict(lambda: {"correct": 0, "total": 0})})
    overall = {"correct": 0, "total": 0}

    for result in all_results:
        cat = result["doc_type"]
        field_results = result["field_results"]

        for field, is_correct in field_results.items():
            by_category[cat]["total"] += 1
            by_category[cat]["field_scores"][field]["total"] += 1
            overall["total"] += 1

            if is_correct:
                by_category[cat]["correct"] += 1
                by_category[cat]["field_scores"][field]["correct"] += 1
                overall["correct"] += 1

    return {
        "overall": overall,
        "by_category": dict(by_category)
    }


def render_report(metrics: dict, all_results: list[dict]) -> None:
    """Print a formatted accuracy report — the whole point of this POC."""
    overall = metrics["overall"]
    overall_acc = overall["correct"] / overall["total"] * 100

    print("\n" + "=" * 72)
    print("ACCURACY BY DOCUMENT TYPE — EVALUATION REPORT")
    print("=" * 72)

    # --- Aggregate number that looks good but hides problems ---
    print(f"\n  OVERALL ACCURACY: {overall_acc:.1f}%  "
          f"({overall['correct']}/{overall['total']} fields correct)")
    print("  " + "─" * 50)

    # --- Per-category breakdown reveals where the model struggles ---
    print("\n  PER-CATEGORY BREAKDOWN:\n")
    for cat, data in sorted(metrics["by_category"].items()):
        cat_acc = data["correct"] / data["total"] * 100
        # Visual delta from aggregate — negative means this category drags down quality
        delta = cat_acc - overall_acc
        delta_str = f"{'+'if delta >= 0 else ''}{delta:.1f}pp vs aggregate"
        bar = render_bar(cat_acc)

        print(f"    {cat.upper():12s}  {cat_acc:5.1f}%  {bar}  ({delta_str})")

        # Per-field detail within each category
        for field, fdata in data["field_scores"].items():
            field_acc = fdata["correct"] / fdata["total"] * 100
            status = "✓" if field_acc == 100 else "✗"
            print(f"      {status} {field:16s}: {field_acc:.0f}%")
        print()

    # --- Flag categories performing below threshold ---
    THRESHOLD = 75.0
    weak = [
        (cat, data["correct"] / data["total"] * 100)
        for cat, data in metrics["by_category"].items()
        if data["correct"] / data["total"] * 100 < THRESHOLD
    ]

    if weak:
        print("  ⚠ CATEGORIES BELOW 75% THRESHOLD:")
        for cat, acc in sorted(weak, key=lambda x: x[1]):
            print(f"    → {cat}: {acc:.1f}% — needs targeted prompt tuning or more training examples")
    else:
        print("  ✓ All categories above 75% threshold")

    print("\n" + "=" * 72)

    # --- Detailed per-document results for debugging specific failures ---
    print("\n  DETAILED RESULTS:\n")
    for r in all_results:
        all_correct = all(r["field_results"].values())
        icon = "✓" if all_correct else "✗"
        print(f"    {icon} [{r['doc_type']:10s}] vendor={r['predicted'].get('vendor', 'N/A')}")
        for field, is_correct in r["field_results"].items():
            if not is_correct:
                print(f"        MISS on '{field}': "
                      f"predicted='{r['predicted'].get(field, '')}' "
                      f"expected='{r['ground_truth'].get(field, '')}'")
    print()


def render_bar(pct: float, width: int = 20) -> str:
    filled = round(pct / 100 * width)
    return f"[{'█' * filled}{'░' * (width - filled)}]"


def main():
    print("Evaluating extraction accuracy across document types...\n")

    all_results = []

    for i, sample in enumerate(EVAL_DATASET):
        print(f"  Processing [{sample['doc_type']}] document {i + 1}/{len(EVAL_DATASET)}...")

        predicted = extract_fields(sample["text"])
        field_results = score_extraction(predicted, sample["ground_truth"])

        all_results.append({
            "doc_type": sample["doc_type"],
            "predicted": predicted,
            "ground_truth": sample["ground_truth"],
            "field_results": field_results
        })

    metrics = compute_metrics(all_results)
    render_report(metrics, all_results)

    # Dump raw results for programmatic consumers
    print("Raw JSON results:")
    print(json.dumps(
        [{"doc_type": r["doc_type"], "predicted": r["predicted"],
          "ground_truth": r["ground_truth"],
          "field_results": r["field_results"]} for r in all_results],
        indent=2
    ))


if __name__ == "__main__":
    main()
