# Access Failures vs Empty Results — POC

Demonstrates the critical architectural distinction between:
- **Access failure** → "could not check" (error state — must not assume absence)
- **Empty result** → "checked and found nothing" (safe to act on absence)

## Why This Matters

Conflating these two states is a common source of silent bugs:
```
results = search(query)      # returns [] on BOTH failure and no-match
if not results:
    delete_all_cached_data() # DANGEROUS if search actually failed
```

## Setup

```bash
cd domain-05/task-02-03

# 1. Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment (optional — demo works without a real key)
cp .env .env.local
# Edit .env and replace 'your-api-key-here' with a valid Anthropic API key
```

## Run

```bash
python main.py
```

## Expected Output

```
==================================================
ACCESS FAILURES vs EMPTY RESULTS
==================================================

──────────────────────────────────────────────────
Context: Bad API key → access failure
⚠ ACCESS FAILURE: AUTH_FAILED
  → Cannot assert 'nothing exists' — search never completed
  → Action: retry, escalate, or degrade gracefully

──────────────────────────────────────────────────
Context: Valid credentials, query matched nothing
✓ EMPTY RESULT: search completed, zero matches
  → Safe to proceed assuming absence

──────────────────────────────────────────────────
Context: Valid credentials, query matched items
✓ FOUND: ['Python', 'JavaScript', 'Go']
```

## Key Concept for Exam

| Scenario | `items` | `searched_successfully` | Safe to assume absence? |
|----------|---------|------------------------|------------------------|
| Auth failure | `[]` | `False` | **NO** |
| Network timeout | `[]` | `False` | **NO** |
| Search OK, no match | `[]` | `True` | YES |
| Search OK, matched | `[...]` | `True` | N/A |

The `SearchResult` dataclass encodes this distinction at the type level — downstream code **must** check `searched_successfully` before interpreting an empty `items` list.
