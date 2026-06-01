# Multi-Pass Code Review POC

Key pattern demonstrated: Fan-out/fan-in — each file is reviewed in isolation with a scoped system prompt (Pass 1), then all findings plus full source are assembled into a single integration review that       
  catches cross-cutting concerns like unsanitized data flows and inconsistent auth checks (Pass 2).

---

Demonstrates the **multi-pass review pattern**: per-file local analysis followed by a cross-file integration pass — a validation pattern tested in the Claude Architect exam.

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                  Sample Codebase                     │
│  auth/login.py  auth/permissions.py  api/endpoints   │
│  data/store.py                                       │
└──────────┬──────────────────────────────┬────────────┘
           │                              │
     ┌─────▼──────┐                ┌──────▼─────┐
     │  Pass 1a   │                │  Pass 1d   │
     │ Local      │  ... (×4)      │ Local      │
     │ Review     │                │ Review     │
     └─────┬──────┘                └──────┬─────┘
           │    Per-file JSON findings    │
           └──────────┬───────────────────┘
                      │
                ┌─────▼──────┐
                │  Pass 2    │
                │ Integration│  All findings + full source
                │ Review     │
                └─────┬──────┘
                      │
                ┌─────▼──────┐
                │  Unified   │
                │  Report    │
                └────────────┘
```

**Pass 1 (Fan-out):** Each file reviewed independently — catches local bugs, security issues, code quality.

**Pass 2 (Fan-in):** All per-file findings + full source fed into one integration review — catches cross-file data flows, contract mismatches, systemic patterns.

## Setup

### 1. Create virtual environment

```bash
cd domain-04/task-04-03
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Install dependencies

```bash
pip install anthropic python-dotenv
```

### 3. Configure API key

```bash
cp .env .env.local
# Edit .env and replace 'your-api-key-here' with your actual key
nano .env
```

### 4. Run

```bash
python multi_pass_review.py
```

## Expected Output

The script prints a structured report with two sections:

1. **Pass 1 results** — per-file issues (SQL injection in `data/store.py`, weak hashing in `auth/login.py`, etc.)
2. **Pass 2 results** — cross-file issues (unsanitized user input flowing from `api/endpoints.py` → `data/store.py`, missing auth checks on certain endpoints, etc.)

## Key Exam Concepts

| Concept | Where in code |
|---|---|
| Fan-out / fan-in pattern | `run_local_pass()` → `run_integration_pass()` |
| Scoped system prompts | `LOCAL_REVIEW_SYSTEM` limits model to single-file scope |
| Structured JSON output | Both passes return parseable JSON |
| Context assembly for integration | Pass 2 receives per-file findings + full source |
| Graceful JSON parsing fallback | Handles markdown-fenced JSON responses |
