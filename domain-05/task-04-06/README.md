# Conflict Annotation POC

Core technique: When multiple sources disagree on the same metric, the system explicitly marks the conflict rather than silently choosing one value. A two-layer detection strategy — model-level prompting + code-level post-processing — ensures no disagreement is hidden from the consumer.

## Why conflict annotation matters

| Approach | Problem |
|---|---|
| Silent selection | Model picks one source; consumer never learns a conflict existed |
| Averaging / merging | Produces a number no source actually reported — untraceable |
| **Explicit annotation** | Consumer sees all values, their sources, and a recommendation — then decides |

## How it works

```
Conflicting sources (4 documents, 3 departments)
  │
  ▼
┌─────────────────────────────────────┐
│  Source document builder             │  ← Embeds department + provenance
│  Wraps each source with attribution  │     in document text so model can
│                                      │     attribute each claim to a dept
└─────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────┐
│  Claude (citations enabled)          │  ← System prompt enforces rules:
│  Instructed to flag [CONFLICT] tags  │     never silently pick one value,
│  for disagreeing sources             │     list all values with sources
└─────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────┐
│  Claim extractor                     │  ← Maps each citation to its
│  Links claims to source departments  │     originating department for
│                                      │     cross-source comparison
└─────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────┐
│  Code-level conflict detector        │  ← Catches conflicts the model
│  Scans for same metric across depts  │     missed — prompting is best-
│  Tags: MODEL+CODE or CODE-ONLY       │     effort, code is deterministic
└─────────────────────────────────────┘
```

## The conflicting data

| Metric | Finance | Sales | Customer Success |
|---|---|---|---|
| Revenue / Bookings | $48.2M | $52.7M | — |
| Churn rate | 4.1% | 3.8% | 5.3% |
| Customer count | 560 | 580 | 572 |
| ACV / Deal size | $86,000 | $91,500 | — |
| Meridian deal | $1.2M ARR | $1.4M ARR | $1.2M ARR |

## Setup

```bash
cd domain-05/task-04-06

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
python conflict_annotation.py
```

## Expected output

```
Conflict Annotation POC
Demonstrates: explicit conflict marking vs. silent source selection
========================================================================

========================================================================
  KNOWLEDGE BASE — SOURCE OVERVIEW
========================================================================

    [FIN] Q1 2025 Financial Summary
        Published  : 2025-04-01
        Source ID  : finance-q1-report

    [SAL] Q1 2025 Sales Performance Review
        Published  : 2025-04-03
        Source ID  : sales-q1-report

    [CUS] Q1 2025 Customer Health Dashboard
        Published  : 2025-03-31
        Source ID  : cs-health-report

    [PRO] 2025 Product Roadmap — Public
        Published  : 2025-03-15
        Source ID  : product-roadmap

Sending queries across conflicting sources...

  -> Querying: "What was our Q1 2025 revenue and how did it compare..."

========================================================================
  QUERY: What was our Q1 2025 revenue and how did it compare year-over-year?
========================================================================

  CLAIMS          : 3
  MULTI-SOURCE    : 1 claim(s) cite >1 department
  CONFLICTS FOUND : 1 (model flagged 1)
  ──────────────────────────────────────────────────

  [!!] Claim 1 (CONFLICT):
      "[CONFLICT] Revenue/Bookings: Finance reports Q1 2025 revenue of $48.2M..."
        <- [Finance] Q1 2025 Financial Summary (Finance)
        <- [Sales] Q1 2025 Sales Performance Review (Sales)

  [+] Claim 2 (SINGLE-SOURCE):
      "The Finance report shows 18% YoY growth while Sales reports 23% YoY..."
        <- [Finance] Q1 2025 Financial Summary (Finance)

  ==================================================
  CONFLICT ANNOTATIONS
  ==================================================

    [MODEL+CODE] revenue_or_bookings
      Departments   : Finance, Sales
      Claim matches : 2

  -> Querying: "What is our current customer churn rate?..."

========================================================================
  QUERY: What is our current customer churn rate?
========================================================================

  CLAIMS          : 4
  MULTI-SOURCE    : 1 claim(s) cite >1 department
  CONFLICTS FOUND : 1 (model flagged 1)
  ──────────────────────────────────────────────────

  [!!] Claim 1 (CONFLICT):
      "[CONFLICT] Churn rate: Finance says 4.1%, Sales says 3.8%, Customer..."
        <- [Finance] Q1 2025 Financial Summary (Finance)
        <- [Sales] Q1 2025 Sales Performance Review (Sales)
        <- [Customer Success] Q1 2025 Customer Health Dashboard (Customer Success)

  ==================================================
  CONFLICT ANNOTATIONS
  ==================================================

    [MODEL+CODE] churn_rate
      Departments   : Customer Success, Finance, Sales
      Claim matches : 2
```

## Key concepts for the exam

1. **Prompting alone is not enough for conflict detection** — The system prompt tells the model to flag `[CONFLICT]`, but models can still silently pick one source. The code-level detector (`detect_conflicts`) catches what the model misses — tagged as `CODE-ONLY` in the output
2. **Two-layer detection is the pattern** — Layer 1 (model prompting) catches obvious conflicts cheaply; Layer 2 (code post-processing) is deterministic and catches what Layer 1 misses. Neither layer alone is sufficient
3. **Provenance must be in the document text** — Embedding department name and source ID inside the document (not just in code variables) lets the model attribute conflicting values to specific departments in its response
4. **Citations enable conflict tracing** — Without the Citations API, you cannot programmatically determine which claims came from which documents. Citations turn "the model said X" into "the model said X, citing document Y from department Z"
5. **Silent selection is the default failure mode** — Without explicit conflict rules in the system prompt, models synthesize a single coherent answer. This is helpful for general Q&A but dangerous when accuracy requires surfacing disagreements
6. **Conflict annotation preserves consumer autonomy** — Instead of the model deciding which source is right, the consumer sees all values and makes the call. The model can recommend, but the recommendation is clearly labeled as such
7. **Non-conflicting sources should NOT be flagged** — The Product Roadmap source agrees with others or covers different topics. A good conflict detector has low false positives — flagging everything as a conflict is as useless as flagging nothing
