# Few-Shot Prompting for Ambiguous Boundaries

Demonstrates why few-shot prompting is most valuable when task categories overlap and no single "correct" answer exists. The POC classifies workplace message tone — a task where "diplomatic" vs "passive-aggressive" vs "direct" have genuinely fuzzy boundaries that only examples (not instructions) can disambiguate.

## Setup

```bash
cd domain-04/task-02-04

python -m venv venv
source venv/bin/activate

pip install anthropic python-dotenv
```

## Configure

Edit `.env` and add your API key:

```
ANTHROPIC_API_KEY=sk-ant-...
```

## Run

```bash
python few_shot_ambiguous_boundaries.py
```

## Expected Output

```
Input: I'm sure you did your best with the time you had.
tone: passive-aggressive
reasoning: surface-level praise undercut by implied inadequacy
--------------------------------------------------
Input: Let's align on expectations so we don't run into this again.
tone: diplomatic
reasoning: collaborative framing with forward-looking solution
--------------------------------------------------
Input: Just flagging — this is the third time the tests failed on this module.
tone: direct
reasoning: factual observation with repetition count, no sarcasm or blame
--------------------------------------------------
```

## Key Concept — Why Ambiguous Boundaries Need Few-Shot

| Aspect | Explanation |
|--------|-------------|
| The problem | Categories like "diplomatic" and "passive-aggressive" overlap — reasonable people disagree |
| Why instructions fail | You can't write a system prompt rule that cleanly separates "As per my last email" from "Thanks for finally..." |
| Why few-shot works | Each example pair encodes a **boundary decision** — it shows the model where *you* draw the line |
| Exam takeaway | Few-shot is most valuable when the task has ambiguous boundaries that no instruction can fully specify |
