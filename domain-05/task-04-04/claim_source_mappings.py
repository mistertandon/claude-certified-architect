"""
Claim-Source Mappings — Traceability POC

Every claim in an LLM's output should trace back to a specific passage in a
source document. Without this, users cannot verify whether the model invented
a fact or grounded it in evidence. The Anthropic Citations API solves this by
returning char-level pointers from each output sentence back to its source.
"""

import os
import json

import anthropic
from dotenv import load_dotenv

# .env lives next to this script, not in the caller's cwd
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

client = anthropic.Anthropic()

# --- Source documents: the ground truth that claims must trace back to ---
# Multiple docs test that citations correctly distinguish between sources.
SOURCE_DOCUMENTS = [
    {
        "title": "Q1 2025 Revenue Report",
        "text": (
            "Total revenue for Q1 2025 reached $14.2 million, a 23% increase "
            "over Q1 2024. The growth was driven primarily by enterprise contracts, "
            "which accounted for 68% of total revenue. Self-serve revenue declined "
            "by 4% due to churn in the SMB segment. Gross margin improved to 72%, "
            "up from 65% in the prior year, reflecting lower infrastructure costs "
            "after the cloud migration completed in November 2024."
        ),
    },
    {
        "title": "Product Roadmap — H1 2025",
        "text": (
            "The team will ship three major features in H1 2025: real-time "
            "collaboration (target: February), an AI-powered search upgrade "
            "(target: April), and a self-serve analytics dashboard (target: June). "
            "Real-time collaboration depends on the WebSocket infrastructure that "
            "the platform team is building in January. The AI search upgrade will "
            "use retrieval-augmented generation with citation support to ensure "
            "every result links back to its source document."
        ),
    },
    {
        "title": "Incident Postmortem — 2025-02-18",
        "text": (
            "On February 18, 2025, the payment processing service experienced "
            "a 47-minute outage starting at 14:03 UTC. Root cause: a database "
            "connection pool exhaustion triggered by a spike in retry storms "
            "after a failed deployment at 13:58 UTC. 1,247 transactions were "
            "delayed but none were lost. Mitigation: the on-call engineer rolled "
            "back the deployment at 14:22 UTC and manually drained the connection "
            "pool. Preventive measures include adding circuit breakers to the "
            "retry logic and enforcing deployment canary gates."
        ),
    },
]

# --- Questions designed to force claims from specific (and multiple) sources ---
QUERIES = [
    "Summarize the company's financial performance in Q1 2025.",
    "What are the key product launches planned, and do any of them relate to traceability?",
    "Describe the recent outage: what happened, how long did it last, and what was the fix?",
    "What connections exist between the cloud migration and financial results?",
]


def build_message_content(query: str) -> list[dict]:
    """Assemble documents + query into a single user message.

    Documents are passed as typed content blocks so the Citations API
    can map output sentences back to exact character ranges in each source.
    A plain string concatenation would lose document boundaries.
    """
    content = []

    for doc in SOURCE_DOCUMENTS:
        content.append({
            "type": "document",
            "source": {
                "type": "text",
                "media_type": "text/plain",
                "data": doc["text"],
            },
            "title": doc["title"],
            # Per-document flag — the API requires all docs to agree on this
            "citations": {"enabled": True},
        })

    content.append({"type": "text", "text": query})
    return content


def query_with_citations(query: str) -> anthropic.types.Message:
    """Send query + source documents to Claude with citations enabled."""
    return client.messages.create(
        model="claude-sonnet-4-6-20250514",
        max_tokens=1024,
        system=(
            "Answer questions using ONLY the provided documents. "
            "Every factual claim must be grounded in a source passage. "
            "Do not add information beyond what the documents contain."
        ),
        messages=[{"role": "user", "content": build_message_content(query)}],
    )


def extract_claim_source_map(response: anthropic.types.Message) -> list[dict]:
    """Parse response into a list of {claim, citations} mappings.

    Each text block in the response may carry zero or more citations.
    A block with no citations is an unsupported claim — a red flag for
    traceability-sensitive use cases like compliance or legal review.
    """
    mappings = []

    for block in response.content:
        if block.type != "text":
            continue

        citations_for_block = []
        if hasattr(block, "citations") and block.citations:
            for cite in block.citations:
                citation_entry = {
                    "cited_text": cite.cited_text,
                    "source_title": cite.document_title,
                    "document_index": cite.document_index,
                }
                # char_location gives exact offsets for substring verification
                if cite.type == "char_location":
                    citation_entry["char_range"] = (
                        cite.start_char_index,
                        cite.end_char_index,
                    )
                citations_for_block.append(citation_entry)

        mappings.append({
            "claim": block.text,
            "citation_count": len(citations_for_block),
            "citations": citations_for_block,
        })

    return mappings


def render_traceability_report(query: str, mappings: list[dict]) -> None:
    """Print a human-readable claim-to-source map for auditing."""
    print(f"\n{'=' * 72}")
    print(f"  QUERY: {query}")
    print(f"{'=' * 72}")

    total_claims = len(mappings)
    grounded_claims = sum(1 for m in mappings if m["citation_count"] > 0)

    print(f"\n  TRACEABILITY: {grounded_claims}/{total_claims} text blocks have citations")
    print(f"  {'─' * 50}\n")

    for i, mapping in enumerate(mappings):
        claim_preview = mapping["claim"][:120].replace("\n", " ")
        if len(mapping["claim"]) > 120:
            claim_preview += "..."

        status = "GROUNDED" if mapping["citation_count"] > 0 else "UNSUPPORTED"
        icon = "+" if mapping["citation_count"] > 0 else "!"

        print(f"  [{icon}] Claim {i + 1} ({status}):")
        print(f"      \"{claim_preview}\"")

        if mapping["citations"]:
            print(f"      Sources ({mapping['citation_count']}):")
            for c in mapping["citations"]:
                source_preview = c["cited_text"][:90].replace("\n", " ")
                if len(c["cited_text"]) > 90:
                    source_preview += "..."
                char_info = ""
                if "char_range" in c:
                    char_info = f" [chars {c['char_range'][0]}–{c['char_range'][1]}]"
                print(f"        <- [{c['source_title']}]{char_info}")
                print(f"           \"{source_preview}\"")
        else:
            # Unsupported claims are the ones that need human review
            print(f"      ** No source citation — verify manually **")
        print()


def render_source_coverage(all_mappings: list[list[dict]]) -> None:
    """Show which source documents were cited and how often.

    Unused sources may signal that the query set is too narrow,
    or that one document is irrelevant to the task at hand.
    """
    doc_citation_counts = {}
    for doc in SOURCE_DOCUMENTS:
        doc_citation_counts[doc["title"]] = 0

    for mappings in all_mappings:
        for m in mappings:
            for c in m["citations"]:
                title = c["source_title"]
                if title in doc_citation_counts:
                    doc_citation_counts[title] += 1

    print(f"\n{'=' * 72}")
    print("  SOURCE COVERAGE SUMMARY")
    print(f"{'=' * 72}\n")

    for title, count in doc_citation_counts.items():
        bar_len = min(count, 30)
        bar = "█" * bar_len + "░" * (30 - bar_len)
        status = "CITED" if count > 0 else "UNUSED"
        print(f"    [{status:6s}] {title}")
        print(f"             {bar}  {count} citation(s)\n")


def main():
    print("Claim-Source Mapping — Traceability POC")
    print("Sending queries with citations enabled...\n")

    all_mappings = []

    for query in QUERIES:
        print(f"  -> Querying: \"{query[:60]}...\"")
        response = query_with_citations(query)
        mappings = extract_claim_source_map(response)
        all_mappings.append(mappings)
        render_traceability_report(query, mappings)

    render_source_coverage(all_mappings)

    # Dump structured output for programmatic consumers
    print("\n" + "=" * 72)
    print("  RAW JSON (first query only, for inspection)")
    print("=" * 72)
    print(json.dumps(all_mappings[0], indent=2, default=str))


if __name__ == "__main__":
    main()
