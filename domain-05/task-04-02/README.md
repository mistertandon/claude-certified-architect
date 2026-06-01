# Field-Level Confidence Indicators — Structured Extraction POC

Core technique: Uses tool_choice={"type": "any"} to force Claude into structured JSON output via a tool schema that requires confidence (0.0–1.0) and reason per field. A calibrated confidence scale in the     
  system prompt prevents scores from clustering, and threshold-based classification turns scores into actionable routing decisions.
  
Demonstrates how to make Claude **self-assess confidence per extracted field**,
enabling downstream systems to auto-accept trusted values and flag uncertain
ones for human review.

## Why field-level confidence?

| Approach | Problem |
|---|---|
| Extract without confidence | All fields look equally trustworthy — silent errors reach production |
| Single document-level score | One low-confidence field drags the whole extraction to manual review |
| **Per-field confidence** | Only uncertain fields get routed to humans — 80% less manual work |

## How it works

```
Messy document
      │
      ▼
┌─────────────────────────┐
│  Claude (tool_use mode)  │  ← Forced structured output via tool_choice="any"
│  Extracts fields +       │
│  confidence + reasoning  │
└─────────────────────────┘
      │
      ▼
┌─────────────────────────┐
│  Confidence classifier   │  ← Thresholds: ≥0.8 auto-accept, ≥0.5 review, <0.5 reject
└─────────────────────────┘
      │
      ▼
  AUTO_ACCEPT / FLAG_FOR_REVIEW / REJECT
```


## Setup

```bash
cd domain-05/task-04-02

# 1. Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 2. Install dependencies
pip install anthropic python-dotenv

# 3. Configure API key
cp .env .env.local
# Edit .env.local and replace 'your-api-key-here' with your actual key
# OR export directly:
export ANTHROPIC_API_KEY="sk-ant-..."
```

## Run

```bash
python field_level_confidence.py
```

## Expected output

```
Extracting fields from document with confidence indicators...

========================================================================
FIELD-LEVEL CONFIDENCE REPORT
========================================================================

  sender_email
    Value      : j.martinez@acmecorp.com
    Confidence : 1.0  [████████████████████]  [AUTO_ACCEPT]
    Reason     : Email explicitly stated in the From header

  po_number
    Value      : PO-2025-0042
    Confidence : 0.9  [██████████████████░░]  [AUTO_ACCEPT]
    Reason     : PO number explicitly stated in the email body

  invoice_total
    Value      : $12,400
    Confidence : 0.5  [██████████░░░░░░░░░░]  [FLAG_FOR_REVIEW]
    Reason     : Stated as approximate ("around") and subject to change

  shipping_cost
    Value      : unknown
    Confidence : 0.1  [██░░░░░░░░░░░░░░░░░░]  [REJECT / MANUAL_ENTRY]
    Reason     : Explicitly stated as not yet determined
```

## Key concepts for the exam

1. **`tool_choice={"type": "any"}`** — Forces structured JSON output; Claude must respond through the tool, not free text
2. **Confidence scale in the system prompt** — Giving Claude explicit anchors (0.9 = explicit, 0.5 = approximate) produces calibrated scores rather than everything clustering at 0.8
3. **Action thresholds** — Numeric confidence becomes actionable routing: auto-accept, flag, or reject
4. **Per-field reasoning** — The `reason` field creates an audit trail explaining *why* a score is low, not just *that* it is
