"""
Conflict Annotation POC

When multiple sources disagree, a naive system silently picks one answer —
the consumer never learns a conflict existed. This POC forces conflicts into
the open: the model is instructed to surface contradictions, and a post-
processing layer independently detects and annotates conflicting claims
so no disagreement is swept under the rug.
"""

import os
import json
from datetime import datetime, timezone

import anthropic
from dotenv import load_dotenv

# .env lives next to this script, not in the caller's cwd
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

client = anthropic.Anthropic()

# --- Conflicting knowledge sources ---
# Deliberately contradictory so the model must choose — or flag.
# Each source is authoritative in its own domain, but they disagree
# on overlapping facts. Real-world analogy: two departments publish
# different numbers for the same metric.
KNOWLEDGE_SOURCES = [
    {
        "source_id": "finance-q1-report",
        "department": "Finance",
        "title": "Q1 2025 Financial Summary",
        "published": "2025-04-01",
        "data": (
            "Q1 2025 revenue: $48.2M (up 18% YoY). "
            "Customer churn rate: 4.1%. "
            "Average contract value (ACV): $86,000. "
            "Total active customers: 560. "
            "Largest deal closed: Meridian Corp at $1.2M ARR."
        ),
    },
    {
        "source_id": "sales-q1-report",
        "department": "Sales",
        "title": "Q1 2025 Sales Performance Review",
        "published": "2025-04-03",
        # Revenue and ACV conflict with Finance's numbers — this is
        # the scenario the POC exists to catch.
        "data": (
            "Q1 2025 bookings: $52.7M (up 23% YoY). "
            "Customer churn rate: 3.8%. "
            "Average deal size: $91,500. "
            "Total accounts: 580. "
            "Top deal: Meridian Corp at $1.4M ARR."
        ),
    },
    {
        "source_id": "cs-health-report",
        "department": "Customer Success",
        "title": "Q1 2025 Customer Health Dashboard",
        "published": "2025-03-31",
        # Churn and customer count conflict with both Finance and Sales
        "data": (
            "Active customers (end of Q1): 572. "
            "Customer churn rate: 5.3% (up from 4.0% in Q4). "
            "NPS score: 42 (down from 48). "
            "At-risk accounts: 38 (6.6% of base). "
            "Meridian Corp health score: GREEN — renewed at $1.2M ARR."
        ),
    },
    {
        "source_id": "product-roadmap",
        "department": "Product",
        "title": "2025 Product Roadmap — Public",
        "published": "2025-03-15",
        # Non-conflicting source — included to show that the system
        # does NOT flag agreement as conflict (avoids false positives).
        "data": (
            "H1 2025: SSO/SAML launch (April), API v3 GA (May). "
            "H2 2025: Mobile app beta (August), AI assistant GA (October). "
            "Pricing unchanged until Q3 review. "
            "Target NPS: 55 by year-end."
        ),
    },
]

# Metrics we expect to conflict across sources — used by the
# post-processing detector. Keys are semantic labels, values are
# regex-free search terms that identify mentions of each metric.
TRACKED_METRICS = {
    "revenue_or_bookings": ["revenue", "bookings"],
    "churn_rate": ["churn rate", "churn"],
    "customer_count": ["active customers", "total active", "total accounts"],
    "acv_or_deal_size": ["average contract value", "ACV", "average deal size"],
    "meridian_deal": ["meridian corp", "meridian"],
}

QUERIES = [
    "What was our Q1 2025 revenue and how did it compare year-over-year?",
    "What is our current customer churn rate?",
    "Summarize the Meridian Corp deal — contract value and status.",
]


def build_source_document(source: dict) -> dict:
    """Wrap a knowledge source as a citable document block.

    The department and publication date are embedded in the document
    text — not just in code — so the model can attribute and compare.
    """
    # Provenance header lets the model (and the consumer) know which
    # department produced this data, critical for conflict attribution.
    header = (
        f"[SOURCE PROVENANCE]\n"
        f"  Department : {source['department']}\n"
        f"  Document   : {source['title']}\n"
        f"  Published  : {source['published']}\n"
        f"  Source ID  : {source['source_id']}\n"
        f"[/SOURCE PROVENANCE]\n\n"
    )

    return {
        "type": "document",
        "source": {
            "type": "text",
            "media_type": "text/plain",
            "data": header + source["data"],
        },
        "title": f"{source['title']} ({source['department']})",
        # Citations let us trace each claim back to its originating
        # document — without this, conflict detection is guesswork.
        "citations": {"enabled": True},
    }


# The system prompt is the first line of defense: it tells the model
# to surface conflicts rather than resolve them. Without this, models
# default to synthesizing a single coherent answer — hiding the very
# disagreements the consumer needs to see.
SYSTEM_PROMPT = (
    "You are a cross-departmental data analyst.\n\n"
    "CONFLICT RULES (non-negotiable):\n"
    "1. When two or more sources report DIFFERENT values for the same "
    "metric, you MUST flag the conflict explicitly using this format:\n"
    "   [CONFLICT] <metric>: Source A says X, Source B says Y.\n"
    "2. Do NOT silently pick one value. Present ALL conflicting values "
    "with their source attribution.\n"
    "3. After listing the conflict, suggest which source is likely "
    "authoritative and why, but frame it as a recommendation, not a fact.\n"
    "4. For non-conflicting data, cite the source normally.\n"
    "5. Use ONLY the provided documents. Do not invent data.\n"
    "6. End your response with a CONFLICT SUMMARY listing all "
    "conflicts found (or 'No conflicts detected')."
)


def query_with_conflict_detection(query: str) -> anthropic.types.Message:
    """Send query with all source documents for conflict-aware answering."""
    content = [build_source_document(s) for s in KNOWLEDGE_SOURCES]
    content.append({"type": "text", "text": query})

    return client.messages.create(
        model="claude-sonnet-4-6-20250514",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": content}],
    )


def extract_cited_claims(response: anthropic.types.Message) -> list[dict]:
    """Parse response into claims, each linked to its source document(s).

    A claim citing multiple sources is a candidate for conflict — the
    model reached across documents, which means it either found
    agreement or disagreement.
    """
    claims = []

    for block in response.content:
        if block.type != "text":
            continue

        sources_cited = []
        if hasattr(block, "citations") and block.citations:
            for cite in block.citations:
                source_record = KNOWLEDGE_SOURCES[cite.document_index]
                sources_cited.append({
                    "document_title": cite.document_title,
                    "department": source_record["department"],
                    "source_id": source_record["source_id"],
                    "cited_text": cite.cited_text[:150],
                })

        claims.append({
            "text": block.text,
            "sources": sources_cited,
            # Multiple departments cited = potential cross-source conflict
            "departments_involved": list({s["department"] for s in sources_cited}),
        })

    return claims


def detect_conflicts(claims: list[dict]) -> list[dict]:
    """Independent conflict detection — does NOT trust the model's own flags.

    The model is prompted to flag conflicts, but prompting is best-effort.
    This function catches conflicts the model missed by checking whether
    the same metric appears in claims from different departments.
    """
    conflicts = []

    for metric_name, search_terms in TRACKED_METRICS.items():
        # Collect every claim that mentions this metric
        matching_claims = []
        for claim in claims:
            claim_lower = claim["text"].lower()
            if any(term.lower() in claim_lower for term in search_terms):
                matching_claims.append(claim)

        if len(matching_claims) < 2:
            continue

        # Conflict exists when different departments report on the same metric
        all_depts = set()
        for c in matching_claims:
            all_depts.update(c["departments_involved"])

        if len(all_depts) > 1:
            conflicts.append({
                "metric": metric_name,
                "departments": sorted(all_depts),
                "claim_count": len(matching_claims),
                # Model-flagged = model used [CONFLICT] tag itself
                "model_flagged": any(
                    "[conflict]" in c["text"].lower() for c in matching_claims
                ),
            })

    return conflicts


def render_conflict_report(query: str, claims: list[dict], conflicts: list[dict]) -> None:
    """Display the annotated conflict report for a single query."""
    print(f"\n{'=' * 72}")
    print(f"  QUERY: {query}")
    print(f"{'=' * 72}")

    total_claims = len(claims)
    multi_source = sum(1 for c in claims if len(c["departments_involved"]) > 1)
    model_flagged = sum(1 for c in conflicts if c["model_flagged"])

    print(f"\n  CLAIMS          : {total_claims}")
    print(f"  MULTI-SOURCE    : {multi_source} claim(s) cite >1 department")
    print(f"  CONFLICTS FOUND : {len(conflicts)} (model flagged {model_flagged})")
    print(f"  {'─' * 50}\n")

    # Render each claim with conflict annotation
    for i, claim in enumerate(claims):
        preview = claim["text"][:140].replace("\n", " ")
        if len(claim["text"]) > 140:
            preview += "..."

        is_conflict_claim = "[conflict]" in claim["text"].lower()
        if is_conflict_claim:
            icon, tag = "!!", "CONFLICT"
        elif len(claim["departments_involved"]) > 1:
            icon, tag = "?", "CROSS-SOURCE"
        else:
            icon, tag = "+", "SINGLE-SOURCE"

        print(f"  [{icon}] Claim {i + 1} ({tag}):")
        print(f"      \"{preview}\"")

        for s in claim["sources"]:
            print(f"        <- [{s['department']}] {s['document_title']}")
        print()

    # Conflict summary — the payoff of the entire POC
    if conflicts:
        print(f"  {'=' * 50}")
        print("  CONFLICT ANNOTATIONS")
        print(f"  {'=' * 50}\n")

        for c in conflicts:
            flag = "MODEL+CODE" if c["model_flagged"] else "CODE-ONLY"
            print(f"    [{flag}] {c['metric']}")
            print(f"      Departments   : {', '.join(c['departments'])}")
            print(f"      Claim matches : {c['claim_count']}")
            if not c["model_flagged"]:
                # The model missed this conflict — exactly the scenario
                # that makes code-level detection essential.
                print("      ** Model did NOT flag this — caught by post-processing **")
            print()
    else:
        print("  No conflicts detected.\n")


def render_source_overview() -> None:
    """Show all sources and their departments before querying."""
    print(f"\n{'=' * 72}")
    print("  KNOWLEDGE BASE — SOURCE OVERVIEW")
    print(f"{'=' * 72}\n")

    for source in KNOWLEDGE_SOURCES:
        print(f"    [{source['department'][:3].upper()}] {source['title']}")
        print(f"        Published  : {source['published']}")
        print(f"        Source ID  : {source['source_id']}")
        print()


def main():
    print("Conflict Annotation POC")
    print(f"Demonstrates: explicit conflict marking vs. silent source selection")
    print("=" * 72)

    # Step 1: Show source inventory so the reader knows what can conflict
    render_source_overview()

    # Step 2: Query and detect conflicts
    print("Sending queries across conflicting sources...\n")

    for query in QUERIES:
        print(f"  -> Querying: \"{query[:60]}...\"")
        response = query_with_conflict_detection(query)
        claims = extract_cited_claims(response)
        # Two-layer conflict detection: model's own flags + code-level check
        conflicts = detect_conflicts(claims)
        render_conflict_report(query, claims, conflicts)

    # Step 3: Show raw model response for the first query (for inspection)
    print(f"\n{'=' * 72}")
    print("  RAW MODEL RESPONSE (first query)")
    print(f"{'=' * 72}")
    first_response = query_with_conflict_detection(QUERIES[0])
    for block in first_response.content:
        if block.type == "text":
            print(block.text)


if __name__ == "__main__":
    main()
