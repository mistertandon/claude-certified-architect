# Context Compaction POC

Demonstrates how `/compact` works: compress conversation history into a dense summary to reclaim context window space, then continue the conversation from the compacted state.

## Core Concept

As a conversation grows, every new API call sends the **entire history** — consuming more tokens and approaching the context limit. **Compaction** asks the model to summarize the history into a structured recap, then replaces the full transcript with that single summary.

```
BEFORE compaction                    AFTER compaction
┌─────────────────────┐              ┌─────────────────────┐
│ user: review auth.py│              │ user: [COMPACTED]    │
│ asst: found SQLi... │              │  - auth.py: SQLi     │
│ user: review pay.py │              │  - pay.py: PII log   │
│ asst: PII logged... │   ──────►   │  - upload.py: path   │
│ user: review upload │              │  - config.py: creds  │
│ asst: path traversal│              │  - session.py: RCE   │
│ user: review config │              │ asst: context loaded  │
│ asst: hardcoded key │              └─────────────────────┘
│ user: review session│                 2 messages (~30%)
│ asst: pickle RCE... │
└─────────────────────┘
   10 messages (100%)
```

## What This Proves

| Aspect | Before Compaction | After Compaction |
|---|---|---|
| **Messages** | 10 (full transcript) | 2 (summary + ack) |
| **Tokens** | ~100% | ~30% (varies) |
| **Fact recall** | Perfect | High — structured facts survive |
| **Nuance** | Full conversational detail | Lost — this is the tradeoff |

## Project Structure

```
task-03-03/
├── .env                # API key + model configuration
├── requirements.txt    # Python dependencies
├── compact_poc.py      # Main POC script
└── README.md
```

## Step-by-Step Guide

### 1. Prerequisites

- Python 3.10+
- An Anthropic API key

### 2. Configure Environment

```bash
cd domain-05/task-03-03
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
python compact_poc.py
```

### 6. Read the Output

The script runs 4 phases:

```
================================================================
PHASE 1: Building conversation history (5 review rounds)
================================================================
  Round 1 (auth.py):     ~180 tokens in history | 2 messages
  Round 2 (payments.py): ~420 tokens in history | 4 messages
  Round 3 (upload.py):   ~710 tokens in history | 6 messages
  Round 4 (config.py):   ~980 tokens in history | 8 messages
  Round 5 (session.py):  ~1250 tokens in history | 10 messages

================================================================
PHASE 2: Compacting conversation history
================================================================
  Compacted: 2 messages, ~370 tokens
  Savings:   ~70% token reduction (1250 -> 370)

================================================================
PHASE 3: Verifying recall after compaction
================================================================
  [Both full and compacted histories answer recall questions]

================================================================
PHASE 4: Continuing conversation from compacted state
================================================================
  [Model produces severity ranking using compacted context]
```

Results are also saved as `compact_results_<timestamp>.json`.

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| `ANTHROPIC_API_KEY` | — | Your Anthropic API key (required) |
| `MODEL_NAME` | `claude-sonnet-4-20250514` | Model to use |

## Key Takeaway for the Architect Exam

Compaction solves the **context window exhaustion** problem in long conversations:

- **Lossy compression** — conversational filler is discarded, structured facts are preserved
- **Token reclamation** — frees 50-80% of context space for future turns
- **Continuation** — the compacted state is a valid conversation the model can build on
- **Tradeoff** — nuance and exact phrasing are lost; only the "what" survives, not the "how it was said"

In Claude Code, `/compact` triggers this exact pattern: the full message history is summarized and replaced, letting the user continue working without hitting context limits.
