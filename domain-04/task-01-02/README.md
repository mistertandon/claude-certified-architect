# False Positive Impact on Developer Trust — POC

## Concept

Too many false positives erode developer trust in automated systems. When a tool flags everything as dangerous, developers learn to dismiss **all** alerts — including the real ones.

This POC compares two prompt strategies for a code-security reviewer:

| Strategy | Behaviour | Effect on Trust |
|----------|-----------|-----------------|
| **NAIVE** | Flags any code touching I/O, crypto, config, logging | High false-positive rate → alert fatigue → developers ignore the tool |
| **TUNED** | Flags only concretely exploitable vulnerabilities | Low false-positive rate → alerts stay credible → developers act on them |

Both prompts review the same six code snippets (3 safe, 3 risky). The output shows precision and false-positive rate side by side.

## Prerequisites

- Python 3.10+
- An Anthropic API key

## Setup

```bash
# 1. Navigate to the project directory
cd domain-04/task-01-02

# 2. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate        # Linux / macOS
# .venv\Scripts\activate         # Windows

# 3. Install dependencies
pip install anthropic python-dotenv

# 4. Configure your API key
cp .env .env.local
# Edit .env (or .env.local) and replace `your-api-key-here` with your real key
```

## Run

```bash
python main.py
```

## Expected Output

```
Strategy: NAIVE  (flag everything)
  → Most snippets flagged as HIGH risk, including safe ones (FP)

Strategy: TUNED  (flag real risks)
  → Only genuinely vulnerable snippets flagged (TP), safe ones pass (TN)

COMPARISON
                     NAIVE       TUNED
  False Positives :  ~3           ~0
  Precision       :  ~0.50        ~1.00
  FP Rate (safe)  :  ~1.00        ~0.00
```

## Key Exam Takeaway

- **Precision matters more than recall** for developer-facing tools.
- A system that cries wolf loses its audience — real vulnerabilities get ignored.
- Prompt design directly controls the false-positive / false-negative tradeoff.
