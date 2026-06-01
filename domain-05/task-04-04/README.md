# Claim-Source Mappings — Traceability POC

Core technique: Uses the Anthropic Citations API to link every output claim back to the exact passage in its source document. Each text block in Claude's response carries zero or more citations with char-level offsets, so reviewers can verify whether a claim is grounded or invented.

## Why claim-source mappings?

| Approach | Problem |
|---|---|
| Trust the model | No way to distinguish grounded facts from hallucinations |
| Manual fact-checking | Doesn't scale — reviewers must re-read all sources per claim |
| **Citation-based traceability** | Each claim links to its source passage — verification is O(1) per claim |

## How it works

```
Source documents (3 docs)
  │
  ▼
┌─────────────────────────────────────┐
│  Claude (citations enabled)          │  ← Each document passed as a typed
│  answers query from docs only        │     content block with citations: true
└─────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────┐
│  Citation parser                     │  ← Each text block in the response
│  extracts claim → source mappings    │     carries citation objects with
│                                      │     char offsets into source docs
└─────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────┐
│  Traceability report                 │  ← Per-claim: GROUNDED vs UNSUPPORTED
│  + source coverage summary           │     Per-source: cited vs unused
└─────────────────────────────────────┘
```

## Setup

```bash
cd domain-05/task-04-04

# 1. Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 2. Install dependencies
pip install anthropic python-dotenv

# 3. Configure API key
# Edit .env and replace 'your-api-key-here' with your actual key
# OR export directly:
export ANTHROPIC_API_KEY="sk-ant-..."
```

## Run

```bash
python claim_source_mappings.py
```

## Expected output

```
Claim-Source Mapping — Traceability POC
Sending queries with citations enabled...

  -> Querying: "Summarize the company's financial performance in Q1 2025..."

========================================================================
  QUERY: Summarize the company's financial performance in Q1 2025.
========================================================================

  TRACEABILITY: 3/3 text blocks have citations
  ──────────────────────────────────────────────────

  [+] Claim 1 (GROUNDED):
      "Total revenue for Q1 2025 was $14.2 million, representing a 23% year-over..."
      Sources (2):
        <- [Q1 2025 Revenue Report] [chars 0–85]
           "Total revenue for Q1 2025 reached $14.2 million, a 23% increase over..."
        <- [Q1 2025 Revenue Report] [chars 86–165]
           "The growth was driven primarily by enterprise contracts, which account..."

  [+] Claim 2 (GROUNDED):
      "Gross margin improved to 72%, up from 65% the prior year..."
      Sources (1):
        <- [Q1 2025 Revenue Report] [chars 248–370]
           "Gross margin improved to 72%, up from 65% in the prior year, reflecti..."

  ...

========================================================================
  SOURCE COVERAGE SUMMARY
========================================================================

    [CITED ] Q1 2025 Revenue Report
             ██████████████████████████████  12 citation(s)

    [CITED ] Product Roadmap — H1 2025
             █████████████░░░░░░░░░░░░░░░░░  6 citation(s)

    [CITED ] Incident Postmortem — 2025-02-18
             ████████████████░░░░░░░░░░░░░░  8 citation(s)
```

## Key concepts for the exam

1. **Citations are per-document, not per-request** — Enable `"citations": {"enabled": True}` on each document content block; all documents in a request must agree on this setting
2. **Text blocks carry citation arrays** — Each `text` block in the response has a `citations` list; a block with zero citations is an unsupported claim that needs manual review
3. **Three citation location types** — `char_location` (plain text, char offsets), `page_location` (PDFs, page numbers), `content_block_location` (custom content, block indices)
4. **`cited_text` is free** — The exact quoted passage is returned in the citation object but is NOT counted toward output tokens
5. **Incompatible with Structured Outputs** — Cannot combine `citations` with `output_config.format`; use tool_use with citations separately if structured extraction is needed
6. **Source coverage reveals gaps** — Tracking which documents are cited (and which are not) surfaces whether your document set is relevant to the queries being asked
7. **Grounded vs unsupported classification** — Text blocks with zero citations are the traceability red flags; in compliance or legal workflows, these should be flagged for human review
