# Case Facts Blocks — POC

Demonstrates how structured "case facts" blocks preserve critical information across long conversations, compared to unstructured prose that loses details during context compaction.

## What This Proves

The same set of 15 legal case facts is presented in two formats:

1. **Unstructured prose** — facts woven into natural language paragraphs
2. **Structured case facts** — facts organized in XML-tagged, categorized blocks

Both versions are put through 3 rounds of context compaction (simulating a long conversation). After compaction, each critical fact is checked for survival. Structured blocks consistently retain more facts because models treat tagged reference sections as higher-priority during compression.

## Prerequisites

- Python 3.10+
- An Anthropic API key

## Setup

```bash
# 1. Navigate to the project directory
cd domain-05/task-01-03

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
python case_facts_blocks.py
```

## Expected Output

```
PHASE 1 (Prose):     ~40-60% of facts retained after 3 rounds
PHASE 2 (Structured): ~70-90% of facts retained after 3 rounds
```

Facts saved by structure are marked with `<<` in the comparison table.

## Key Takeaway

Case facts blocks work because they use clear boundaries (XML tags), labeled categories, key-value format, and priority signaling to tell the model "this is reference data, not conversation." This makes them resistant to the lossy compression that happens during context-window compaction.
