"""
POC: Case Facts Blocks
=======================
Demonstrates how structured "case facts" blocks preserve critical information
across long conversations — compared to unstructured prose that loses details
when context is compacted or summarized.
"""

import os
import json
from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()

# Reuse a single client for connection pooling across all API calls.
client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

MODEL = "claude-sonnet-4-20250514"

# --- Scenario: A legal case review spread across a long conversation ---

# UNSTRUCTURED version — facts buried in natural prose, exactly how a user
# would type them across multiple chat turns. Summarization treats every
# sentence as equally compressible.
UNSTRUCTURED_CONVERSATION = """
So I'm looking at the Henderson v. TechCorp case. The incident happened on
March 15, 2024 at the Riverside manufacturing plant. John Henderson, age 57,
was operating a Model X-400 hydraulic press when the safety interlock failed.
He suffered a crush injury to his right hand, resulting in amputation of the
index and middle fingers. He was earning $78,500 annually before the accident.

The OSHA inspection report #2024-OR-11847 found that TechCorp had received
three prior warnings about the X-400 safety interlock system — specifically
on Jan 8 2023, June 22 2023, and Nov 3 2023. Each warning cited failure to
replace the Omron G9SA-321 relay module per manufacturer recall notice
MCR-2022-0094.

Henderson's surgeon, Dr. Patricia Voss at Portland General, documented that
he will never regain function in the affected fingers. His workers' comp claim
WC-2024-88103 was initially denied by TechCorp's insurer, Pinnacle Casualty,
on the grounds that Henderson had "bypassed safety protocols" — but the
security camera footage from Camera 7B (timestamp 14:22:37) shows he followed
standard operating procedure exactly.

The statute of limitations for this type of claim in Oregon is 2 years from
the date of injury, so we must file before March 15, 2026. Our expert witness,
Dr. Rajesh Patel (mechanical engineering, MIT), is available for deposition
after August 2025. Opposing counsel is Sarah Chen at Morrison & Drake LLP.
"""

# STRUCTURED version — identical facts, but wrapped in clearly delimited
# blocks. The XML-like tags signal to the model that this is reference
# material, not conversational text. Models treat tagged content as
# higher-priority for retention during compaction.
STRUCTURED_CASE_FACTS = """
<case-facts id="henderson-v-techcorp" priority="critical">

<parties>
  - Plaintiff: John Henderson, age 57
  - Defendant: TechCorp Industries
  - Opposing Counsel: Sarah Chen, Morrison & Drake LLP
  - Insurer: Pinnacle Casualty
</parties>

<incident>
  - Date: 2024-03-15
  - Location: Riverside Manufacturing Plant
  - Equipment: Model X-400 Hydraulic Press
  - Injury: Crush injury → amputation of right index and middle fingers
  - Camera Evidence: Camera 7B, timestamp 14:22:37 (shows SOP compliance)
</incident>

<regulatory>
  - OSHA Report: #2024-OR-11847
  - Prior Warnings: 3 total (2023-01-08, 2023-06-22, 2023-11-03)
  - Failed Component: Omron G9SA-321 relay module
  - Manufacturer Recall: MCR-2022-0094
</regulatory>

<medical>
  - Treating Surgeon: Dr. Patricia Voss, Portland General
  - Prognosis: Permanent loss of function, no recovery expected
  - Pre-injury Income: $78,500/year
  - Workers' Comp Claim: WC-2024-88103 (denied by insurer)
</medical>

<deadlines>
  - Statute of Limitations: 2026-03-15 (Oregon, 2-year window)
  - Expert Witness: Dr. Rajesh Patel (Mechanical Eng., MIT) — available after 2025-08
</deadlines>

</case-facts>
"""

# Every fact a lawyer cannot afford to lose. Losing a deadline means
# malpractice; losing an OSHA number means a weakened filing.
CRITICAL_FACTS = [
    "Plaintiff is John Henderson, age 57",
    "Incident date: March 15, 2024",
    "Equipment involved: Model X-400 hydraulic press",
    "Injury: amputation of right index and middle fingers",
    "OSHA report number: 2024-OR-11847",
    "Three prior safety warnings in 2023",
    "Failed component: Omron G9SA-321 relay module",
    "Manufacturer recall notice: MCR-2022-0094",
    "Surgeon: Dr. Patricia Voss at Portland General",
    "Pre-injury annual income: $78,500",
    "Workers' comp claim: WC-2024-88103",
    "Security camera 7B at timestamp 14:22:37",
    "Statute of limitations deadline: March 15, 2026",
    "Expert witness: Dr. Rajesh Patel from MIT",
    "Opposing counsel: Sarah Chen at Morrison & Drake LLP",
]


def simulate_long_conversation(case_content: str, label: str) -> str:
    """Simulate context compaction by forcing 3 rounds of summarization.

    This mirrors what happens in real long conversations: the system
    progressively compresses earlier turns to free up context window
    space for new content.
    """
    current = case_content

    for round_num in range(1, 4):
        response = client.messages.create(
            model=MODEL,
            max_tokens=512,
            # The system prompt mimics automatic context compaction —
            # aggressive length reduction, as would happen when the
            # context window fills up.
            system=(
                "You are a context compaction system. Condense the following "
                "into a brief summary under 120 words. Preserve the most "
                "important information. This is round "
                f"{round_num} of compaction."
            ),
            messages=[
                {
                    "role": "user",
                    "content": f"Compact this content:\n\n{current}",
                }
            ],
        )
        current = response.content[0].text

    return current


def check_facts(summary: str, facts: list[str]) -> list[dict]:
    """Check each fact independently against the compacted summary.

    One API call per fact avoids the model inferring missing facts
    from the presence of related ones.
    """
    results = []
    for fact in facts:
        response = client.messages.create(
            model=MODEL,
            max_tokens=50,
            # Binary YES/NO — no hedging — so counting is unambiguous.
            system=(
                "Answer only YES or NO. Is this specific fact clearly "
                "present or directly inferable from the text?"
            ),
            messages=[
                {
                    "role": "user",
                    "content": f"Fact: {fact}\n\nText:\n{summary}",
                }
            ],
        )
        answer = response.content[0].text.strip().upper()
        results.append({
            "fact": fact,
            "retained": answer.startswith("YES"),
        })
    return results


def run_comparison():
    """Run both versions through compaction and compare fact survival."""

    print("=" * 72)
    print("  CASE FACTS BLOCKS — STRUCTURED vs UNSTRUCTURED RETENTION")
    print("=" * 72)
    print(f"\nTracking {len(CRITICAL_FACTS)} critical facts through 3 rounds of compaction\n")

    # --- Phase 1: Unstructured prose ---
    print("-" * 72)
    print("PHASE 1: Unstructured Prose (facts buried in natural language)")
    print("-" * 72)
    print("Compacting through 3 rounds...")

    unstructured_result = simulate_long_conversation(
        UNSTRUCTURED_CONVERSATION, "unstructured"
    )
    print(f"\nFinal compacted text ({len(unstructured_result)} chars):\n")
    print(unstructured_result)

    print("\n\nChecking fact retention...")
    unstructured_scores = check_facts(unstructured_result, CRITICAL_FACTS)

    # --- Phase 2: Structured case facts ---
    print("\n" + "-" * 72)
    print("PHASE 2: Structured Case Facts (XML-tagged blocks)")
    print("-" * 72)
    print("Compacting through 3 rounds...")

    structured_result = simulate_long_conversation(
        STRUCTURED_CASE_FACTS, "structured"
    )
    print(f"\nFinal compacted text ({len(structured_result)} chars):\n")
    print(structured_result)

    print("\n\nChecking fact retention...")
    structured_scores = check_facts(structured_result, CRITICAL_FACTS)

    # --- Results comparison ---
    print("\n" + "=" * 72)
    print("  SIDE-BY-SIDE COMPARISON")
    print("=" * 72)
    print(f"\n{'Fact':<55} {'Prose':>7} {'Struct':>7}")
    print("-" * 72)

    u_retained = 0
    s_retained = 0

    for u, s in zip(unstructured_scores, structured_scores):
        u_status = "OK" if u["retained"] else "LOST"
        s_status = "OK" if s["retained"] else "LOST"
        if u["retained"]:
            u_retained += 1
        if s["retained"]:
            s_retained += 1

        # Highlight rows where structure saved a fact that prose lost.
        marker = " <<" if (s["retained"] and not u["retained"]) else ""
        print(f"  {u['fact']:<53} {u_status:>7} {s_status:>7}{marker}")

    u_pct = (u_retained / len(CRITICAL_FACTS)) * 100
    s_pct = (s_retained / len(CRITICAL_FACTS)) * 100

    print("-" * 72)
    print(f"  {'TOTAL':<53} {u_retained:>4}/{len(CRITICAL_FACTS)}  {s_retained:>4}/{len(CRITICAL_FACTS)}")
    print(f"  {'RETENTION RATE':<53} {u_pct:>6.0f}% {s_pct:>6.0f}%")

    if s_pct > u_pct:
        delta = s_pct - u_pct
        print(f"\n  Structured case facts preserved {delta:.0f}% more information.")
    elif s_pct == u_pct:
        print("\n  Both approaches retained the same facts in this run.")
    else:
        print("\n  Unexpected: prose outperformed structure in this run. Re-run for variance.")

    # --- Key takeaways ---
    print(f"\n{'=' * 72}")
    print("  WHY CASE FACTS BLOCKS WORK")
    print(f"{'=' * 72}")
    print("""
  1. CLEAR BOUNDARIES — XML-like tags (<case-facts>, <deadlines>) signal
     to the model that this content is reference material, not chat.
     Compaction algorithms preserve tagged sections more faithfully.

  2. LABELED CATEGORIES — Grouping facts under <medical>, <regulatory>,
     <parties> etc. creates semantic anchors. The model compresses within
     categories rather than merging unrelated facts together.

  3. KEY-VALUE FORMAT — "Claim: WC-2024-88103" resists summarization
     better than "his workers' comp claim WC-2024-88103 was denied"
     because the model recognizes it as a data field, not narrative.

  4. PRIORITY SIGNALING — The priority="critical" attribute explicitly
     tells the model this block should survive compaction. This is
     analogous to cache-control headers in HTTP.

  EXAM TIP: Case facts blocks are the recommended mitigation for the
  progressive summarization problem. They preserve critical information
  by structuring it as reference data rather than conversational prose.
""")


if __name__ == "__main__":
    run_comparison()
