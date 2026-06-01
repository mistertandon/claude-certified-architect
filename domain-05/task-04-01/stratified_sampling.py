"""
Stratified Sampling for AI-Powered Review

Instead of random selection (which can over-represent majority categories),
stratified sampling ensures every category gets proportional representation
in the review set — catching issues that hide in minority segments.
"""

import os
import math
import random
from collections import defaultdict

import anthropic
from dotenv import load_dotenv

load_dotenv()


# --- Synthetic dataset: simulates real-world skewed distributions ---
ITEMS = [
    {"id": 1,  "category": "billing",  "text": "Charged twice for monthly subscription"},
    {"id": 2,  "category": "billing",  "text": "Refund not processed after 30 days"},
    {"id": 3,  "category": "billing",  "text": "Invoice amount doesn't match quote"},
    {"id": 4,  "category": "billing",  "text": "Tax calculation seems incorrect"},
    {"id": 5,  "category": "billing",  "text": "Promo code discount not applied"},
    {"id": 6,  "category": "billing",  "text": "Currency conversion fee unexpected"},
    {"id": 7,  "category": "billing",  "text": "Auto-renewal charged after cancellation"},
    {"id": 8,  "category": "billing",  "text": "Payment method declined without reason"},
    {"id": 9,  "category": "security", "text": "Suspicious login from unknown IP"},
    {"id": 10, "category": "security", "text": "Password reset email not received"},
    {"id": 11, "category": "security", "text": "Account locked after single failed attempt"},
    {"id": 12, "category": "feature",  "text": "Dark mode not saving preference"},
    {"id": 13, "category": "feature",  "text": "Export to CSV missing columns"},
    {"id": 14, "category": "feature",  "text": "Search filter ignores date range"},
    {"id": 15, "category": "feature",  "text": "Keyboard shortcuts don't work on Firefox"},
    {"id": 16, "category": "outage",   "text": "API returning 503 for all endpoints"},
    {"id": 17, "category": "outage",   "text": "Dashboard blank after deploy"},
]


def group_by_category(items: list[dict]) -> dict[str, list[dict]]:
    groups = defaultdict(list)
    for item in items:
        groups[item["category"]].append(item)
    return dict(groups)


def stratified_sample(items: list[dict], sample_size: int) -> list[dict]:
    """Pick items proportionally from each category, guaranteeing minimum 1 per stratum."""

    groups = group_by_category(items)
    total = len(items)
    sampled = []

    for category, members in groups.items():
        # Proportional allocation, but floor to at least 1 so no category is invisible
        proportion = len(members) / total
        k = max(1, math.floor(sample_size * proportion))
        # Cap at available items — can't sample more than the stratum holds
        k = min(k, len(members))
        sampled.extend(random.sample(members, k))

    return sampled


def review_with_claude(client: anthropic.Anthropic, samples: list[dict]) -> str:
    """Send stratified samples to Claude for cross-category review."""

    formatted = "\n".join(
        f"- [{item['category'].upper()}] (id={item['id']}): {item['text']}"
        for item in samples
    )

    # System prompt scopes Claude to a reviewer role — prevents off-topic generation
    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        system=(
            "You are a support ticket reviewer. "
            "Analyze the stratified sample below. For each category present, "
            "identify: (1) severity, (2) common pattern, (3) recommended action. "
            "Flag any category that appears under-represented in the sample."
        ),
        messages=[
            {
                "role": "user",
                "content": (
                    f"Here is a stratified sample of {len(samples)} tickets "
                    f"drawn proportionally from all categories:\n\n{formatted}"
                ),
            }
        ],
    )

    return message.content[0].text


def main():
    client = anthropic.Anthropic()

    sample_size = 8
    print(f"Total items: {len(ITEMS)}")
    print(f"Target sample size: {sample_size}\n")

    # --- Show category distribution so the sampling rationale is visible ---
    groups = group_by_category(ITEMS)
    print("Category distribution:")
    for cat, members in groups.items():
        pct = len(members) / len(ITEMS) * 100
        print(f"  {cat}: {len(members)} items ({pct:.0f}%)")

    # --- Stratified sampling preserves category ratios unlike random.sample ---
    samples = stratified_sample(ITEMS, sample_size)

    print(f"\nStratified sample ({len(samples)} items):")
    sampled_groups = group_by_category(samples)
    for cat, members in sampled_groups.items():
        ids = [m["id"] for m in members]
        print(f"  {cat}: {len(members)} selected — ids {ids}")

    # --- Contrast with pure random to show why stratification matters ---
    random_sample = random.sample(ITEMS, sample_size)
    random_groups = group_by_category(random_sample)
    print(f"\nRandom sample ({sample_size} items) for comparison:")
    for cat in groups:
        count = len(random_groups.get(cat, []))
        # Categories with 0 here are exactly the blind spots stratification prevents
        print(f"  {cat}: {count} selected")

    print("\n--- Claude Review of Stratified Sample ---\n")
    review = review_with_claude(client, samples)
    print(review)


if __name__ == "__main__":
    main()
