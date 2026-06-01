# Context Degradation POC

Demonstrates how response quality degrades in extended Claude sessions as the context window fills up.

## What This Proves

In a multi-turn conversation, early information gets "buried" under newer messages. This POC:

1. Plants a unique fact at the start of a conversation
2. Stuffs the context with unrelated filler turns
3. Periodically asks the model to recall the planted fact
4. Tracks **recall accuracy** and **response latency** at each checkpoint

As context grows, you'll observe:
- Exact recall degrades to partial or failed recall
- Response latency increases (more tokens to process)

## Project Structure

```
task-03-01/
├── .env                         # API key configuration
├── requirements.txt             # Python dependencies
├── context_degradation_poc.py   # Main POC script
└── README.md
```

## Step-by-Step Guide

### 1. Prerequisites

- Python 3.10+
- An Anthropic API key

### 2. Configure Environment

```bash
cd domain-05/task-03-01
cp .env .env.local   # optional: keep a local copy
```

Edit `.env` and set your API key:

```
ANTHROPIC_API_KEY=sk-ant-...your-key...
```

### 3. Create Virtual Environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

### 5. Run the POC

```bash
python context_degradation_poc.py
```

### 6. Read the Output

The script prints a checkpoint table like:

```
[Checkpoint 1] msgs= 14  input_tokens=  1842  recall=EXACT    latency=1.23s
[Checkpoint 2] msgs= 26  input_tokens=  3901  recall=EXACT    latency=1.87s
[Checkpoint 3] msgs= 38  input_tokens=  5934  recall=PARTIAL  latency=2.41s
...
```

And a summary:

```
CONTEXT DEGRADATION SUMMARY
 CP | Filler |  Msgs | Tokens |   Recall |  Latency
  1 |      5 |   14  |   1842 |    EXACT |    1.23s
  2 |     10 |   26  |   3901 |    EXACT |    1.87s
  3 |     15 |   38  |   5934 |  PARTIAL |    2.41s
```

Results are also saved as `degradation_results_<timestamp>.json`.

## Tuning Parameters

| Variable | Default | Purpose |
|---|---|---|
| `FILLER_ROUNDS_PER_CHECK` | 5 | Filler turns between each recall test |
| `NUM_CHECKPOINTS` | 6 | Total recall probes |
| `MODEL_NAME` (in .env) | `claude-sonnet-4-20250514` | Model to test |

To observe degradation more aggressively, increase `FILLER_ROUNDS_PER_CHECK` to 10-15.

## Key Takeaway for the Architect Exam

Context degradation is the primary reason production systems need:
- **Summarization / compaction** — periodically condense older messages
- **RAG retrieval** — pull relevant context on-demand instead of keeping everything in the window
- **Conversation pruning** — drop low-value turns to preserve token budget for high-value content
- **System prompt anchoring** — place critical instructions in the system prompt (always at the top of attention)
