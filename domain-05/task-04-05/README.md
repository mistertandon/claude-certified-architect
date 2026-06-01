# Temporal Data Currency POC

Core technique: Every data record carries ISO-8601 timestamps (`recorded_at`, `valid_until`) and a semantic version tag. These are embedded directly in the document text so the model can reason about freshness. A classification layer (`CURRENT` / `EXPIRING_SOON` / `STALE`) lets both the model and downstream consumers decide whether to trust, caveat, or reject information.

## Why temporal currency matters

| Approach | Problem |
|---|---|
| Undated data | Consumer cannot tell if "$142/seat" was true yesterday or last year |
| Timestamps in code only | Model never sees the dates — it cannot warn about staleness |
| **Timestamps in document text** | Model can surface version + date per fact; consumer can enforce freshness policies |

## How it works

```
Versioned records (4 records, mixed freshness)
  │
  ▼
┌─────────────────────────────────────┐
│  Freshness classifier               │  ← Compares valid_until against NOW
│  Labels: CURRENT / EXPIRING / STALE │     to pre-classify each record
└─────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────┐
│  Temporal document builder           │  ← Prepends [METADATA] header with
│  Embeds timestamps + version in text │     timestamps, version, freshness
│                                      │     so model sees dates in context
└─────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────┐
│  Claude (citations enabled)          │  ← System prompt enforces rules:
│  Answers with version + date per     │     cite version/date per fact,
│  fact; warns on stale sources        │     warn on STALE records
└─────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────┐
│  Temporal claim analyzer             │  ← Maps each citation back to its
│  Tags claims as CURRENT / STALE      │     source record to recover temporal
│                                      │     metadata and flag stale claims
└─────────────────────────────────────┘
```

## Setup

```bash
cd domain-05/task-04-05

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
python temporal_data_currency.py
```

## Expected output

```
Temporal Data Currency POC
Reference time: 2025-05-06T12:00:00+00:00
========================================================================

========================================================================
  KNOWLEDGE BASE — TEMPORAL CURRENCY SUMMARY
========================================================================

    [+] Enterprise Pricing Schedule
        Version    : 3.1.0
        Recorded   : 2025-05-04 (2d ago)
        Valid until: 2025-06-03
        Freshness  : CURRENT

    [!] Startup Pricing Schedule
        Version    : 2.0.0
        Recorded   : 2024-10-18 (200d ago)
        Valid until: 2025-01-16
        Freshness  : STALE

    [+] Platform SLA — Uptime Guarantees
        Version    : 1.4.2
        Recorded   : 2025-04-06 (30d ago)
        Valid until: 2026-04-06
        Freshness  : CURRENT

    [!] Incident Report — API Gateway
        Version    : 1.0.0
        Recorded   : 2024-04-01 (400d ago)
        Valid until: 2024-05-01
        Freshness  : STALE

Sending queries with temporal metadata...

  -> Querying: "What is the current enterprise pricing, and when was it..."

========================================================================
  QUERY: What is the current enterprise pricing, and when was it last updated?
========================================================================

  TRACEABILITY : 2/2 claims have citations
  STALE CLAIMS : 0 claim(s) cite expired data
  ──────────────────────────────────────────────────

  [+] Claim 1 (CURRENT):
      "The current enterprise plan is priced at $142/seat/month with an annual..."
        <- [Enterprise Pricing Schedule (v3.1.0)] v3.1.0 | recorded 2025-05-04

  ...

========================================================================
  QUERY: Compare the startup and enterprise pricing plans.
========================================================================

  TRACEABILITY : 3/3 claims have citations
  STALE CLAIMS : 2 claim(s) cite expired data
  ──────────────────────────────────────────────────

  [~] Claim 1 (STALE SOURCE):
      "The startup plan is $49/seat/month, however this data is from version..."
        <- [Startup Pricing Schedule (v2.0.0)] v2.0.0 | recorded 2024-10-18 !! STALE

  [+] Claim 2 (CURRENT):
      "The enterprise plan is $142/seat/month with volume discounts..."
        <- [Enterprise Pricing Schedule (v3.1.0)] v3.1.0 | recorded 2025-05-04
```

## Key concepts for the exam

1. **Timestamps must be in the document text, not just in code** — The model can only reason about temporal currency if it sees the dates in its context window; metadata stored only in application variables is invisible to the model
2. **Version + date together prevent silent regression** — A version tag alone doesn't tell you when it was recorded; a date alone doesn't tell you which revision of the data you're looking at; together they form a unique temporal identity
3. **Pre-classify freshness before sending to the model** — Computing `CURRENT` / `EXPIRING_SOON` / `STALE` in code (not asking the model to do it) keeps freshness logic deterministic and auditable
4. **System prompt enforces temporal discipline** — Without explicit instructions to surface dates and warn about staleness, the model will cheerfully present expired data as current
5. **Post-response validation catches what the model misses** — Even with a good system prompt, mapping citations back to source records lets application code independently verify that no stale data slipped through uncaveated
6. **`valid_until` is the consumer's contract** — It shifts responsibility from "the model should know" to "the data says when it expires," making staleness a data-quality problem rather than a model-behavior problem
7. **Temporal metadata composes with citations** — Combining `recorded_at` / `version` with the Citations API means every claim is traceable to both a source passage AND a point in time
