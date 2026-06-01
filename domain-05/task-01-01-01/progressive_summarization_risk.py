"""
POC: Progressive Summarization Risks
=====================================
Demonstrates how critical details erode when content is repeatedly summarized —
the core risk behind context-window compaction strategies in long conversations.
"""

import os
from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()

# Single client instance — reused across all API calls to leverage connection pooling.
client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

MODEL = "claude-sonnet-4-20250514"

# A detail-rich source text where every fact matters.
# The mix of names, numbers, allergies, and temporal constraints
# is intentional — these are the details most likely to vanish
# during progressive summarization.
ORIGINAL_DOCUMENT = """
PATIENT CASE FILE — CONFIDENTIAL

Patient: Maria Santos, 42, Female
MRN: 2024-JS-8847
Admission: 2024-11-15 03:42 AM (Emergency)

Chief Complaint: Severe chest pain radiating to left arm, onset 2 hours prior.

Critical Allergies:
- Penicillin (anaphylaxis — confirmed 2018)
- Latex (contact dermatitis)
- Iodine contrast dye (bronchospasm — near-fatal, 2021)

Current Medications:
- Metformin 1000mg BID (Type 2 Diabetes, diagnosed 2019)
- Lisinopril 20mg daily (Hypertension)
- Atorvastatin 40mg daily (Hyperlipidemia)
- Aspirin 81mg daily

Vitals on Admission:
- BP: 178/102 mmHg
- HR: 112 bpm
- SpO2: 94% on room air
- Temp: 37.1°C
- RR: 22/min

Lab Results:
- Troponin I: 2.8 ng/mL (CRITICAL HIGH — normal <0.04)
- BNP: 890 pg/mL (elevated)
- Creatinine: 1.9 mg/dL (elevated — possible renal compromise)
- HbA1c: 8.2% (poor diabetic control)
- Potassium: 5.3 mEq/L (borderline high)

ECG: ST-elevation in leads II, III, aVF — consistent with inferior STEMI.

Treatment Plan:
- IMMEDIATE cardiac catheterization (avoid iodine contrast — use CO2 angiography)
- Heparin drip per STEMI protocol
- DO NOT administer any beta-lactam antibiotics
- Nephrology consult for elevated creatinine before any contrast procedure
- Monitor potassium — hold ACE inhibitor if K+ rises above 5.5
- Target glucose 140-180 mg/dL with insulin sliding scale
- Family contact: Daughter Ana Santos, phone 555-0147 (healthcare proxy)

Special Notes:
- Patient is primary caregiver for elderly mother with dementia — social work consult needed
- Patient expressed wish for NO intubation unless absolutely necessary (verbal, not yet documented as formal advance directive)
- Previous cardiac history: Father died of MI at age 48
"""

# These facts are safety-critical — losing any of them in a summary
# could lead to real clinical harm (wrong drug, wrong procedure, wrong contact).
CRITICAL_FACTS = [
    "Penicillin allergy causing anaphylaxis",
    "Iodine contrast dye allergy (near-fatal bronchospasm)",
    "Troponin I level of 2.8 ng/mL",
    "Creatinine 1.9 mg/dL indicating renal compromise",
    "Must use CO2 angiography instead of iodine contrast",
    "Do NOT administer beta-lactam antibiotics",
    "Potassium 5.3 — hold ACE inhibitor if above 5.5",
    "Healthcare proxy: daughter Ana Santos, 555-0147",
    "Patient wishes NO intubation unless absolutely necessary",
    "Patient is primary caregiver for elderly mother with dementia",
]


def summarize(text: str, iteration: int) -> str:
    """Ask the model to compress text into a shorter summary.

    Each call simulates one round of context-window compaction —
    the same operation that happens automatically in long conversations.
    """
    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        # system prompt forces aggressive compression, mimicking
        # what happens when a context window nears its limit.
        system="You are a summarizer. Condense the following into a brief summary. "
               "Keep it under 150 words. Focus on the most important points.",
        messages=[
            {
                "role": "user",
                "content": f"Please summarize this text concisely:\n\n{text}",
            }
        ],
    )
    return response.content[0].text


def check_fact_retention(summary: str, facts: list[str]) -> list[dict]:
    """Use the model itself to judge whether each critical fact survived.

    A separate API call per fact avoids cross-contamination between checks —
    the model can't "infer" one fact from another's presence.
    """
    results = []
    for fact in facts:
        response = client.messages.create(
            model=MODEL,
            max_tokens=100,
            # Strict binary prompt — no hedging allowed — so we get
            # a clean PRESENT/ABSENT signal for downstream counting.
            system="You are a fact-checker. Answer only YES or NO. "
                   "Is the following specific fact clearly present in the summary?",
            messages=[
                {
                    "role": "user",
                    "content": f"Fact to check: {fact}\n\nSummary:\n{summary}",
                }
            ],
        )
        answer = response.content[0].text.strip().upper()
        results.append({
            "fact": fact,
            # Startswith handles "YES, ..." or "YES." responses gracefully.
            "retained": answer.startswith("YES"),
        })
    return results


def run_progressive_summarization(rounds: int = 3):
    """Run N rounds of summarize-then-check to show detail erosion over time."""

    print("=" * 70)
    print("PROGRESSIVE SUMMARIZATION RISK DEMONSTRATION")
    print("=" * 70)
    print(f"\nOriginal document length: {len(ORIGINAL_DOCUMENT)} characters")
    print(f"Tracking {len(CRITICAL_FACTS)} critical facts across {rounds} summarization rounds\n")

    current_text = ORIGINAL_DOCUMENT

    for round_num in range(1, rounds + 1):
        print(f"\n{'—' * 70}")
        print(f"ROUND {round_num}: Summarizing...")
        print(f"{'—' * 70}")

        summary = summarize(current_text, round_num)

        print(f"\nSummary ({len(summary)} chars):\n")
        print(summary)

        print(f"\n--- Fact Retention Check (Round {round_num}) ---\n")
        results = check_fact_retention(summary, CRITICAL_FACTS)

        retained = 0
        lost = 0
        for r in results:
            status = "RETAINED" if r["retained"] else "!! LOST"
            icon = "  " if r["retained"] else ">>"
            print(f"  {icon} [{status}] {r['fact']}")
            if r["retained"]:
                retained += 1
            else:
                lost += 1

        pct = (retained / len(CRITICAL_FACTS)) * 100
        print(f"\n  Score: {retained}/{len(CRITICAL_FACTS)} facts retained ({pct:.0f}%)")

        if lost > 0:
            print(f"  WARNING: {lost} critical fact(s) lost in this round!")

        # Feed the summary back as input — each round compounds the loss,
        # exactly like repeated context compaction in a long conversation.
        current_text = summary

    print(f"\n{'=' * 70}")
    print("CONCLUSION")
    print(f"{'=' * 70}")
    print("""
Progressive summarization is a lossy compression. Each round:
  1. Drops details the model deems "less important"
  2. Merges distinct facts into vaguer statements
  3. Loses numerical precision (lab values, dosages, phone numbers)

In agentic / long-context systems, this means:
  - Safety-critical details (allergies, contraindications) can vanish
  - Specific identifiers (names, numbers) are replaced by generics
  - Nuanced instructions ("use CO2 angiography") collapse into generalities

Mitigation strategies:
  - Pin critical facts outside the summarized context (structured metadata)
  - Use retrieval (RAG) instead of summarization for detail-sensitive data
  - Implement fact-preservation checks after each compaction cycle
  - Maintain a "never-summarize" zone for safety-critical information
""")


if __name__ == "__main__":
    run_progressive_summarization(rounds=3)
