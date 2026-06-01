# Progressive Summarization Risks — POC

Demonstrates how critical details erode when content is repeatedly summarized, the core risk behind context-window compaction in long conversations.

## What This Proves

A detail-rich medical case file is summarized 3 times in succession. After each round, 10 safety-critical facts (allergies, lab values, contraindications) are checked for survival. By round 3, several facts are typically lost — showing that progressive summarization is **lossy compression** that can silently drop important information.

## Prerequisites

- Python 3.10+
- An Anthropic API key

## Setup

```bash
# 1. Navigate to the project directory
cd domain-05/task-01-01-01

# 2. Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 3. Install dependencies
pip install anthropic python-dotenv

# 4. Configure your API key
#    Open .env and replace "your-api-key-here" with your actual key
nano .env
```

## Run

```bash
python progressive_summarization_risk.py
```

## Expected Output

```
ROUND 1: ~60-80% of facts retained (summary still fairly detailed)
ROUND 2: ~40-60% retained (numbers, names start disappearing)
ROUND 3: ~20-40% retained (only the broadest facts survive)
```

Each lost fact is flagged with `>> [!! LOST]` in the output.

## Key Takeaway

In agentic or long-context systems, never rely on summarization alone for safety-critical data. Pin important facts in structured metadata, use RAG, or maintain a "never-summarize" zone.
