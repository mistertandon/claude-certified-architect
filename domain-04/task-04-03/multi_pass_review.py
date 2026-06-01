"""
Multi-pass code review: per-file local analysis + cross-file integration pass.

Architecture pattern demonstrated:
  Pass 1 (Fan-out)  — Each file is reviewed independently for local issues.
  Pass 2 (Fan-in)   — All per-file findings are fed into one integration
                       review that catches cross-file concerns (dependency
                       chains, inconsistent contracts, systemic patterns).

This two-pass split mirrors how senior engineers review PRs: skim each file
first, then reason about how the pieces interact.
"""

import json
import os
import sys

import anthropic
from dotenv import load_dotenv

from sample_files import SAMPLE_FILES

# .env lives next to this script; load before reading keys
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

# Single client instance — reuses connection pool across all API calls
client = anthropic.Anthropic()

# Haiku keeps per-file pass fast and cheap; integration pass uses the same
# model for consistency, but could be upgraded to Sonnet for deeper reasoning.
MODEL = "claude-haiku-4-5-20251001"


# ── Pass 1: Per-file local analysis ──────────────────────────────────────────

# System prompt scopes the model to single-file concerns only — prevents it
# from speculating about cross-file issues it can't verify in isolation.
LOCAL_REVIEW_SYSTEM = """You are a senior code reviewer performing a LOCAL per-file analysis.
Focus ONLY on issues visible within this single file:
- Security vulnerabilities (injection, hardcoded secrets, weak crypto)
- Bug risks (unhandled errors, race conditions, logic flaws)
- Code quality (naming, complexity, missing validation)

Output valid JSON with this structure:
{
  "file": "<filename>",
  "issues": [
    {
      "severity": "critical|high|medium|low",
      "category": "security|bug|quality",
      "line_hint": "<approximate line or code snippet>",
      "description": "<concise issue description>",
      "suggestion": "<fix recommendation>"
    }
  ],
  "summary": "<one-line summary of file health>"
}

Do NOT speculate about how this file interacts with others — that is handled in a separate pass."""


def review_single_file(filename: str, content: str) -> dict:
    """Pass 1 unit: review one file in isolation and return structured findings."""
    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        # System prompt enforces local-only scope so the model doesn't
        # hallucinate cross-file dependencies it hasn't seen.
        system=LOCAL_REVIEW_SYSTEM,
        messages=[
            {
                "role": "user",
                "content": f"Review this file:\n\n**{filename}**\n```python\n{content}\n```",
            }
        ],
    )

    raw = response.content[0].text
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # Fallback: model occasionally wraps JSON in markdown fences
        import re
        match = re.search(r"```(?:json)?\s*(.*?)```", raw, re.DOTALL)
        if match:
            return json.loads(match.group(1))
        # Graceful degradation — surface the raw text so the integration
        # pass can still reason about it rather than losing the review.
        return {"file": filename, "issues": [], "summary": raw}


def run_local_pass(files: dict[str, str]) -> list[dict]:
    """Fan-out: review every file independently, collect all findings."""
    results = []
    for filename, content in files.items():
        print(f"  [Pass 1] Reviewing {filename} ...")
        result = review_single_file(filename, content)
        results.append(result)
        issue_count = len(result.get("issues", []))
        print(f"           Found {issue_count} issue(s)")
    return results


# ── Pass 2: Cross-file integration analysis ──────────────────────────────────

# This prompt sees ALL per-file results plus full source — it can now reason
# about interaction patterns that no single-file review could catch.
INTEGRATION_REVIEW_SYSTEM = """You are a senior architect performing a CROSS-FILE integration review.
You receive per-file review results AND the full source code of all files.

Your job is to find issues that span multiple files:
- Data flow vulnerabilities (unsanitized input crossing module boundaries)
- Inconsistent security patterns (auth checked in some paths, not others)
- Architectural concerns (circular dependencies, tight coupling, missing layers)
- Contract mismatches (caller assumptions vs callee guarantees)
- Systemic patterns (same anti-pattern repeated across files)

Output valid JSON:
{
  "cross_file_issues": [
    {
      "severity": "critical|high|medium|low",
      "category": "security-flow|architecture|contract-mismatch|systemic",
      "files_involved": ["file1", "file2"],
      "description": "<issue spanning multiple files>",
      "attack_scenario_or_impact": "<concrete example of how this fails>",
      "suggestion": "<fix recommendation>"
    }
  ],
  "systemic_patterns": ["<pattern seen across multiple files>"],
  "architecture_summary": "<overall assessment of the codebase health>"
}"""


def run_integration_pass(
    files: dict[str, str], local_results: list[dict]
) -> dict:
    """Fan-in: feed all per-file findings + full source into one integration review."""

    # Build context: both the raw source AND the per-file findings.
    # Providing both lets the model verify per-file claims and spot gaps.
    all_source = "\n\n".join(
        f"### {fname}\n```python\n{content}\n```"
        for fname, content in files.items()
    )

    local_summary = json.dumps(local_results, indent=2)

    # Single large prompt — the model needs holistic view to find cross-cutting
    # concerns, so splitting this further would defeat the purpose.
    user_msg = (
        "## Per-file review results (from Pass 1)\n"
        f"```json\n{local_summary}\n```\n\n"
        "## Full source code\n"
        f"{all_source}\n\n"
        "Now perform the cross-file integration review."
    )

    response = client.messages.create(
        model=MODEL,
        max_tokens=2048,
        system=INTEGRATION_REVIEW_SYSTEM,
        messages=[{"role": "user", "content": user_msg}],
    )

    raw = response.content[0].text
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        import re
        match = re.search(r"```(?:json)?\s*(.*?)```", raw, re.DOTALL)
        if match:
            return json.loads(match.group(1))
        return {"cross_file_issues": [], "architecture_summary": raw}


# ── Report formatting ────────────────────────────────────────────────────────


def print_report(local_results: list[dict], integration_result: dict) -> None:
    """Human-readable console report combining both passes."""

    print("\n" + "=" * 70)
    print("  MULTI-PASS CODE REVIEW REPORT")
    print("=" * 70)

    # ── Per-file findings ──
    print("\n── PASS 1: Per-File Local Analysis ──\n")
    for file_result in local_results:
        fname = file_result.get("file", "unknown")
        issues = file_result.get("issues", [])
        summary = file_result.get("summary", "")
        print(f"  File: {fname}")
        print(f"  Summary: {summary}")
        if issues:
            for i, issue in enumerate(issues, 1):
                sev = issue.get("severity", "?").upper()
                cat = issue.get("category", "?")
                desc = issue.get("description", "")
                hint = issue.get("line_hint", "")
                fix = issue.get("suggestion", "")
                print(f"    [{sev}] ({cat}) {desc}")
                if hint:
                    print(f"           Line/code: {hint}")
                if fix:
                    print(f"           Fix: {fix}")
        else:
            print("    No issues found.")
        print()

    # ── Cross-file findings ──
    print("── PASS 2: Cross-File Integration Analysis ──\n")
    cross_issues = integration_result.get("cross_file_issues", [])
    if cross_issues:
        for i, issue in enumerate(cross_issues, 1):
            sev = issue.get("severity", "?").upper()
            cat = issue.get("category", "?")
            files = ", ".join(issue.get("files_involved", []))
            desc = issue.get("description", "")
            impact = issue.get("attack_scenario_or_impact", "")
            fix = issue.get("suggestion", "")
            print(f"  {i}. [{sev}] ({cat})")
            print(f"     Files: {files}")
            print(f"     Issue: {desc}")
            if impact:
                print(f"     Impact: {impact}")
            if fix:
                print(f"     Fix: {fix}")
            print()
    else:
        print("  No cross-file issues found.\n")

    # ── Systemic patterns ──
    patterns = integration_result.get("systemic_patterns", [])
    if patterns:
        print("  Systemic patterns:")
        for p in patterns:
            print(f"    - {p}")
        print()

    # ── Architecture summary ──
    arch = integration_result.get("architecture_summary", "")
    if arch:
        print(f"  Architecture assessment: {arch}")

    print("\n" + "=" * 70)


# ── Main ─────────────────────────────────────────────────────────────────────


def main():
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ERROR: Set ANTHROPIC_API_KEY in .env file")
        sys.exit(1)

    print("Multi-Pass Code Review")
    print("-" * 40)
    print(f"Files to review: {len(SAMPLE_FILES)}")
    print(f"Model: {MODEL}\n")

    # Pass 1: independent per-file reviews (fan-out)
    print("[Pass 1] Running per-file local analysis...")
    local_results = run_local_pass(SAMPLE_FILES)

    # Pass 2: holistic cross-file review (fan-in)
    # Depends on Pass 1 output — must run sequentially.
    print("\n[Pass 2] Running cross-file integration analysis...")
    integration_result = run_integration_pass(SAMPLE_FILES, local_results)

    # Combine both passes into a unified report
    print_report(local_results, integration_result)

    return {
        "local_results": local_results,
        "integration_result": integration_result,
    }


if __name__ == "__main__":
    main()
