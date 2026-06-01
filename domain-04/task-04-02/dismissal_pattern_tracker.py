"""
Dismissal Pattern Tracker — demonstrates how detected_pattern fields
track repeated review dismissals to surface systematic issues.

Use case: A code-review bot flags issues. Reviewers can dismiss findings.
When the same pattern is dismissed repeatedly across reviews, the system
escalates it — the dismissals themselves become a signal worth investigating.
"""

import os
import json
from datetime import datetime, timezone
from collections import Counter
from dotenv import load_dotenv
import anthropic

load_dotenv()

client = anthropic.Anthropic()

# ── Simulated review history ───────────────────────────────────────────
# Each entry represents a reviewer's reaction to a bot-flagged issue.
# "dismissed" entries are the ones we mine for systematic patterns.
REVIEW_HISTORY = [
    {"review_id": "PR-101", "pattern": "missing-null-check",     "action": "dismissed", "reason": "not applicable here"},
    {"review_id": "PR-102", "pattern": "missing-null-check",     "action": "dismissed", "reason": "handled upstream"},
    {"review_id": "PR-103", "pattern": "missing-null-check",     "action": "fixed"},
    {"review_id": "PR-104", "pattern": "sql-injection-risk",     "action": "dismissed", "reason": "parameterized already"},
    {"review_id": "PR-105", "pattern": "missing-null-check",     "action": "dismissed", "reason": "legacy code, won't fix"},
    {"review_id": "PR-106", "pattern": "unused-import",          "action": "dismissed", "reason": "auto-generated file"},
    {"review_id": "PR-107", "pattern": "missing-null-check",     "action": "dismissed", "reason": "checked in wrapper"},
    {"review_id": "PR-108", "pattern": "sql-injection-risk",     "action": "dismissed", "reason": "ORM handles it"},
    {"review_id": "PR-109", "pattern": "unused-import",          "action": "dismissed", "reason": "will clean up later"},
    {"review_id": "PR-110", "pattern": "missing-error-handling",  "action": "fixed"},
    {"review_id": "PR-111", "pattern": "missing-null-check",     "action": "dismissed", "reason": "test file only"},
    {"review_id": "PR-112", "pattern": "sql-injection-risk",     "action": "dismissed", "reason": "internal-only endpoint"},
    {"review_id": "PR-113", "pattern": "hardcoded-secret",       "action": "fixed"},
    {"review_id": "PR-114", "pattern": "missing-null-check",     "action": "dismissed", "reason": "optional field"},
    {"review_id": "PR-115", "pattern": "unused-import",          "action": "dismissed", "reason": "needed for type hints"},
]


def build_detected_patterns(history: list[dict]) -> dict:
    """Aggregate dismissal data into detected_pattern fields.

    The structure mirrors what a real CI/review system would persist
    so that downstream consumers (dashboards, LLM reviewers) can
    reason about dismissal trends without re-scanning raw logs.
    """
    dismissed = [e for e in history if e["action"] == "dismissed"]

    # Counter gives us frequency — the core signal for "systematic".
    pattern_counts = Counter(e["pattern"] for e in dismissed)

    detected_patterns = {}
    for pattern, count in pattern_counts.items():
        reasons = [
            e["reason"] for e in dismissed if e["pattern"] == pattern
        ]
        detected_patterns[pattern] = {
            # Total dismissals — high counts warrant investigation.
            "dismissal_count": count,
            # Raw reasons let an LLM judge whether dismissals are justified.
            "dismissal_reasons": reasons,
            # Ratio of dismissed vs total occurrences for this pattern.
            "dismissal_rate": round(
                count / sum(1 for e in history if e["pattern"] == pattern), 2
            ),
            # Threshold flag — simple heuristic; real systems tune this.
            "flagged_as_systematic": count >= 3,
        }

    return detected_patterns


def analyze_with_claude(detected_patterns: dict) -> str:
    """Ask Claude to interpret the dismissal patterns and recommend actions."""

    # System prompt scopes Claude's role: pattern analyst, not code reviewer.
    system_prompt = (
        "You are a code-review process analyst. You receive detected_pattern "
        "fields that track how often reviewers dismiss specific findings. "
        "Identify systematic issues — patterns dismissed so frequently that "
        "the rule itself may need tuning, or the codebase has a deeper problem. "
        "Be concise and actionable."
    )

    # Structured payload lets Claude parse fields reliably.
    user_payload = {
        "task": "Analyze these dismissal patterns from our code review system",
        "detected_patterns": detected_patterns,
        "instructions": [
            "Identify which patterns are systematically dismissed",
            "Assess whether dismissals are justified or hiding real risk",
            "Recommend: suppress the rule, fix the root cause, or escalate",
        ],
    }

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=system_prompt,
        messages=[
            {"role": "user", "content": json.dumps(user_payload, indent=2)}
        ],
    )

    return response.content[0].text


def main():
    print("=" * 64)
    print("  Dismissal Pattern Tracker — Validation & Review Patterns")
    print("=" * 64)

    # ── Step 1: Build detected_pattern fields from history ──────────
    detected_patterns = build_detected_patterns(REVIEW_HISTORY)

    print("\n── Detected Patterns (detected_pattern fields) ──\n")
    for pattern, data in detected_patterns.items():
        flag = " ** SYSTEMATIC **" if data["flagged_as_systematic"] else ""
        print(f"  {pattern}:{flag}")
        print(f"    dismissal_count : {data['dismissal_count']}")
        print(f"    dismissal_rate  : {data['dismissal_rate']}")
        print(f"    reasons         : {data['dismissal_reasons']}")
        print()

    # ── Step 2: Let Claude analyze the patterns ─────────────────────
    print("── Claude Analysis ──\n")
    analysis = analyze_with_claude(detected_patterns)
    print(analysis)

    # ── Step 3: Summary stats ───────────────────────────────────────
    systematic = [p for p, d in detected_patterns.items() if d["flagged_as_systematic"]]
    print(f"\n── Summary ──")
    print(f"  Total patterns tracked     : {len(detected_patterns)}")
    print(f"  Flagged as systematic (≥3) : {len(systematic)}  {systematic}")
    print(f"  Total review entries        : {len(REVIEW_HISTORY)}")
    print(f"  Total dismissals            : {sum(1 for e in REVIEW_HISTORY if e['action'] == 'dismissed')}")


if __name__ == "__main__":
    main()
