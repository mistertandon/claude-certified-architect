"""
Temporal Data Currency POC

Data without timestamps is data without trust. When an LLM answers "the
price is $142," the consumer has no way to know if that was true five
minutes ago or five months ago. This POC attaches ISO-8601 timestamps and
version tags to every data record, instructs Claude to surface them, and
then validates whether the response honors temporal freshness boundaries.
"""

import os
import json
from datetime import datetime, timezone, timedelta

import anthropic
from dotenv import load_dotenv

# .env lives next to this script, not in the caller's cwd
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

client = anthropic.Anthropic()

# --- Temporal records: each carries its own "born-on" metadata ---
# Real systems pull these from databases/APIs; here they are inline
# so the POC is self-contained and reproducible.
NOW = datetime.now(timezone.utc)

VERSIONED_RECORDS = [
    {
        "record_id": "pricing-enterprise",
        "title": "Enterprise Pricing Schedule",
        "version": "3.1.0",
        # Fresh — updated 2 days ago
        "recorded_at": (NOW - timedelta(days=2)).isoformat(),
        "valid_until": (NOW + timedelta(days=28)).isoformat(),
        "data": (
            "Enterprise plan: $142/seat/month (annual commitment). "
            "Volume discount: 15% for 500+ seats, 25% for 1000+ seats. "
            "Premium support add-on: $30/seat/month. "
            "This schedule supersedes version 3.0.0 dated 2025-01-15."
        ),
    },
    {
        "record_id": "pricing-startup",
        "title": "Startup Pricing Schedule",
        "version": "2.0.0",
        # Stale — recorded 200 days ago, expired 110 days ago
        "recorded_at": (NOW - timedelta(days=200)).isoformat(),
        "valid_until": (NOW - timedelta(days=110)).isoformat(),
        "data": (
            "Startup plan: $49/seat/month (monthly billing). "
            "Free tier: up to 5 seats. "
            "No volume discounts available on this plan."
        ),
    },
    {
        "record_id": "sla-uptime",
        "title": "Platform SLA — Uptime Guarantees",
        "version": "1.4.2",
        # Moderately fresh — updated 30 days ago
        "recorded_at": (NOW - timedelta(days=30)).isoformat(),
        "valid_until": (NOW + timedelta(days=335)).isoformat(),
        "data": (
            "Guaranteed uptime: 99.95% monthly. "
            "Credit schedule: 10% credit for <99.95%, 25% for <99.0%, "
            "50% for <95.0%. Measurement excludes scheduled maintenance "
            "windows (Sundays 02:00-04:00 UTC). "
            "Effective date: 2025-04-01. Replaces SLA v1.4.1."
        ),
    },
    {
        "record_id": "incident-report",
        "title": "Incident Report — API Gateway",
        "version": "1.0.0",
        # Very stale — 400 days old, long expired
        "recorded_at": (NOW - timedelta(days=400)).isoformat(),
        "valid_until": (NOW - timedelta(days=370)).isoformat(),
        "data": (
            "On 2024-03-28, the API gateway experienced 12 minutes of "
            "elevated error rates (peak 8.3% 5xx). Root cause: TLS "
            "certificate rotation script failed silently. Resolved by "
            "manual certificate deployment. Post-incident action: "
            "automated cert-rotation monitoring added."
        ),
    },
]

# Staleness threshold — records expired beyond this are flagged
STALENESS_THRESHOLD_DAYS = 90

QUERIES = [
    "What is the current enterprise pricing, and when was it last updated?",
    "Compare the startup and enterprise pricing plans.",
    "Summarize the platform uptime SLA and the most recent incident.",
]


def classify_freshness(record: dict) -> str:
    """Label each record as CURRENT, EXPIRING_SOON, or STALE.

    Downstream consumers use this label to decide whether to trust,
    caveat, or reject information — the model alone cannot know the
    caller's freshness tolerance.
    """
    valid_until = datetime.fromisoformat(record["valid_until"])
    if valid_until < NOW:
        return "STALE"
    if (valid_until - NOW).days < 14:
        return "EXPIRING_SOON"
    return "CURRENT"


def build_temporal_document(record: dict) -> dict:
    """Wrap a data record in a document content block with temporal metadata.

    Embedding timestamps inside the document text (not just in code) is
    critical — the model can only reason about freshness if it can SEE
    the dates in its context window.
    """
    freshness = classify_freshness(record)

    # Temporal metadata is prepended to the document body so the model
    # encounters it before the data itself — priming temporal awareness.
    temporal_header = (
        f"[METADATA]\n"
        f"  Record ID   : {record['record_id']}\n"
        f"  Version     : {record['version']}\n"
        f"  Recorded at : {record['recorded_at']}\n"
        f"  Valid until : {record['valid_until']}\n"
        f"  Freshness   : {freshness}\n"
        f"  Current time: {NOW.isoformat()}\n"
        f"[/METADATA]\n\n"
    )

    return {
        "type": "document",
        "source": {
            "type": "text",
            "media_type": "text/plain",
            "data": temporal_header + record["data"],
        },
        "title": f"{record['title']} (v{record['version']})",
        # Citations enabled so we can trace claims back to specific records
        "citations": {"enabled": True},
    }


def build_message_content(query: str) -> list[dict]:
    """Assemble all versioned records + query into a single user message."""
    content = [build_temporal_document(r) for r in VERSIONED_RECORDS]
    content.append({"type": "text", "text": query})
    return content


# System prompt forces the model to surface temporal metadata rather than
# silently using stale data — the whole point of this POC.
SYSTEM_PROMPT = (
    "You are a data analyst that is rigorous about temporal accuracy.\n\n"
    "Rules:\n"
    "1. For every fact you state, include the version and recorded_at date.\n"
    "2. If a record's freshness is STALE, explicitly warn that the data may "
    "be outdated and should be re-verified before any decision.\n"
    "3. If a record is EXPIRING_SOON, note the upcoming expiration.\n"
    "4. Never present stale data as if it were current.\n"
    "5. When comparing records, note any version or date discrepancies.\n"
    "6. Use ONLY the provided documents. Do not invent data."
)


def query_with_temporal_context(query: str) -> anthropic.types.Message:
    """Send query to Claude with temporally-annotated documents."""
    return client.messages.create(
        model="claude-sonnet-4-6-20250514",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": build_message_content(query)}],
    )


def extract_temporal_claims(response: anthropic.types.Message) -> list[dict]:
    """Parse response into claims, each with citation + freshness metadata.

    This mirrors the claim-source mapping pattern but adds a temporal
    dimension: every cited source is annotated with its freshness class
    so the consumer knows which claims rest on stale foundations.
    """
    claims = []

    for block in response.content:
        if block.type != "text":
            continue

        cited_sources = []
        if hasattr(block, "citations") and block.citations:
            for cite in block.citations:
                # Map citation back to the original record to recover
                # temporal metadata that the citation object doesn't carry.
                source_record = VERSIONED_RECORDS[cite.document_index]
                cited_sources.append({
                    "source_title": cite.document_title,
                    "cited_text": cite.cited_text[:100],
                    "version": source_record["version"],
                    "recorded_at": source_record["recorded_at"],
                    "freshness": classify_freshness(source_record),
                })

        claims.append({
            "text": block.text,
            "citation_count": len(cited_sources),
            "sources": cited_sources,
        })

    return claims


def render_temporal_report(query: str, claims: list[dict]) -> None:
    """Print a report that highlights temporal currency of each claim."""
    print(f"\n{'=' * 72}")
    print(f"  QUERY: {query}")
    print(f"{'=' * 72}")

    total = len(claims)
    grounded = sum(1 for c in claims if c["citation_count"] > 0)
    stale_sourced = sum(
        1 for c in claims
        if any(s["freshness"] == "STALE" for s in c["sources"])
    )

    print(f"\n  TRACEABILITY : {grounded}/{total} claims have citations")
    print(f"  STALE CLAIMS : {stale_sourced} claim(s) cite expired data")
    print(f"  {'─' * 50}\n")

    for i, claim in enumerate(claims):
        preview = claim["text"][:120].replace("\n", " ")
        if len(claim["text"]) > 120:
            preview += "..."

        if claim["citation_count"] == 0:
            tag = "UNSUPPORTED"
            icon = "!"
        elif any(s["freshness"] == "STALE" for s in claim["sources"]):
            tag = "STALE SOURCE"
            icon = "~"
        else:
            tag = "CURRENT"
            icon = "+"

        print(f"  [{icon}] Claim {i + 1} ({tag}):")
        print(f"      \"{preview}\"")

        for s in claim["sources"]:
            freshness_marker = (
                " !! STALE" if s["freshness"] == "STALE"
                else " * EXPIRING" if s["freshness"] == "EXPIRING_SOON"
                else ""
            )
            print(
                f"        <- [{s['source_title']}] "
                f"v{s['version']} | recorded {s['recorded_at'][:10]}"
                f"{freshness_marker}"
            )
        print()


def render_freshness_summary() -> None:
    """Show the temporal status of every record in the knowledge base.

    This is the pre-flight check: operators should review this before
    trusting any answers, because a knowledge base full of stale records
    produces stale answers regardless of model quality.
    """
    print(f"\n{'=' * 72}")
    print("  KNOWLEDGE BASE — TEMPORAL CURRENCY SUMMARY")
    print(f"{'=' * 72}\n")

    status_icon = {"CURRENT": "+", "EXPIRING_SOON": "~", "STALE": "!"}

    for record in VERSIONED_RECORDS:
        freshness = classify_freshness(record)
        age_days = (NOW - datetime.fromisoformat(record["recorded_at"])).days
        icon = status_icon[freshness]

        print(f"    [{icon}] {record['title']}")
        print(f"        Version    : {record['version']}")
        print(f"        Recorded   : {record['recorded_at'][:10]} ({age_days}d ago)")
        print(f"        Valid until: {record['valid_until'][:10]}")
        print(f"        Freshness  : {freshness}")
        print()


def main():
    print("Temporal Data Currency POC")
    print(f"Reference time: {NOW.isoformat()}")
    print("=" * 72)

    # Step 1: Show temporal status of all records before querying
    render_freshness_summary()

    # Step 2: Query with temporal context and analyze responses
    print("\nSending queries with temporal metadata...")

    all_claims = []
    for query in QUERIES:
        print(f"\n  -> Querying: \"{query[:60]}...\"")
        response = query_with_temporal_context(query)
        claims = extract_temporal_claims(response)
        all_claims.append((query, claims))
        render_temporal_report(query, claims)

    # Step 3: Dump structured output for programmatic consumers
    print(f"\n{'=' * 72}")
    print("  RAW JSON (first query, for inspection)")
    print(f"{'=' * 72}")
    print(json.dumps(all_claims[0][1], indent=2, default=str))


if __name__ == "__main__":
    main()
