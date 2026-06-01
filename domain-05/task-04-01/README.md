# Stratified Sampling — AI-Powered Review POC

Demonstrates **stratified sampling** for review: instead of random selection
(which can miss minority categories entirely), items are sampled proportionally
from every category — ensuring full coverage.

## Why stratified over random?

| Aspect | Random | Stratified |
|---|---|---|
| Minority categories | May get 0 samples | Guaranteed ≥1 sample |
| Reproducibility | Varies wildly | Proportionally stable |
| Blind spots | Likely at small N | Eliminated by design |

## Setup

```bash
cd domain-05/task-04-01

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
python stratified_sampling.py
```

## Expected Output

1. **Category distribution** — shows the skew in the full dataset
2. **Stratified sample** — proportional picks from each category (min 1 per category)
3. **Random sample** — contrast showing categories that random misses
4. **Claude review** — cross-category analysis of the stratified sample

## Key Concept

```
Total: 17 items across 4 categories
  billing:  8 items (47%)  →  stratified picks ~4
  security: 3 items (18%)  →  stratified picks ~1
  feature:  4 items (24%)  →  stratified picks ~2
  outage:   2 items (12%)  →  stratified picks  1 (minimum guarantee)
```

Random sampling of 8 from this set often yields 0 outage or 0 security tickets —
exactly the categories where missed issues are most costly.
