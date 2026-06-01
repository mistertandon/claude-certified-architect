# Accuracy by Document Type — Per-Category Performance Tracking POC

Core technique: Runs Claude extraction against a labeled evaluation dataset spanning multiple document categories (invoice, receipt, contract, memo), then computes per-category accuracy alongside aggregate accuracy. Surfaces blind spots where overall metrics look healthy but specific categories underperform.

## Why per-category accuracy?

| Approach | Problem |
|---|---|
| Aggregate accuracy only | 90% overall can hide 50% accuracy on contracts if invoices dominate the dataset |
| Manual spot-checks | Biased toward easy/common document types — rare categories get missed |
| **Per-category tracking** | Every document type gets its own accuracy score — weak spots surface immediately |

## How it works

```
Labeled evaluation dataset
(8 documents across 4 categories)
        │
        ▼
┌──────────────────────────────┐
│  Claude (tool_use mode)       │  ← Extracts vendor, amount, date, category
│  per-document extraction      │     via tool_choice="any"
└──────────────────────────────┘
        │
        ▼
┌──────────────────────────────┐
│  Scoring engine               │  ← Fuzzy-match predictions against ground truth
│  per-field, per-category      │
└──────────────────────────────┘
        │
        ▼
┌──────────────────────────────┐
│  Report generator             │  ← Overall accuracy + per-category breakdown
│  flags weak categories        │     with delta from aggregate + threshold alerts
└──────────────────────────────┘
```

## Setup

```bash
cd domain-05/task-04-03

# 1. Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 2. Install dependencies
pip install anthropic python-dotenv

# 3. Configure API key
cp .env .env.local
# Edit .env and replace 'your-api-key-here' with your actual key
# OR export directly:
export ANTHROPIC_API_KEY="sk-ant-..."
```

## Run

```bash
python accuracy_by_doc_type.py
```

## Expected output

```
Evaluating extraction accuracy across document types...

  Processing [invoice] document 1/8...
  Processing [invoice] document 2/8...
  Processing [receipt] document 3/8...
  ...

========================================================================
ACCURACY BY DOCUMENT TYPE — EVALUATION REPORT
========================================================================

  OVERALL ACCURACY: 84.4%  (27/32 fields correct)
  ──────────────────────────────────────────────────

  PER-CATEGORY BREAKDOWN:

    CONTRACT       62.5%  [████████████░░░░░░░░]  (-21.9pp vs aggregate)
      ✓ category        : 100%
      ✗ vendor          : 50%
      ✗ total_amount    : 50%
      ✗ date            : 50%

    INVOICE       100.0%  [████████████████████]  (+15.6pp vs aggregate)
      ✓ vendor          : 100%
      ✓ total_amount    : 100%
      ✓ date            : 100%
      ✓ category        : 100%

    MEMO           75.0%  [███████████████░░░░░]  (-9.4pp vs aggregate)
      ✓ vendor          : 100%
      ✗ total_amount    : 50%
      ✓ date            : 100%
      ✓ category        : 50%

    RECEIPT       100.0%  [████████████████████]  (+15.6pp vs aggregate)
      ✓ vendor          : 100%
      ✓ total_amount    : 100%
      ✓ date            : 100%
      ✓ category        : 100%

  ⚠ CATEGORIES BELOW 75% THRESHOLD:
    → contract: 62.5% — needs targeted prompt tuning or more training examples

========================================================================
```

## Key concepts for the exam

1. **Aggregate accuracy is deceptive** — A single overall number hides per-category performance gaps; always stratify evaluation by document type
2. **Deliberate ambiguity in test data** — Contracts and memos include vague amounts, multiple dates, and informal language to stress-test extraction
3. **Fuzzy matching with normalization** — `$4,620.00` vs `$4620` shouldn't count as a miss; normalize before comparison to reduce false negatives
4. **Threshold-based alerting** — Automatically flag categories below a quality threshold (75%) so teams know where to invest in prompt tuning
5. **Per-field granularity within categories** — Knowing that contracts fail on `date` (multiple dates present) vs `vendor` (multiple parties) guides targeted improvements
