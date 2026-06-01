# Scratchpad Files POC

Demonstrates how external "scratchpad" files persist critical state across context window resets — a key pattern for production agentic systems.

## Core Concept

When a context window fills up and gets compacted (or a new conversation starts), all in-context state is lost. A **scratchpad file** is an external file the agent reads at the start of each window and writes to at the end, creating durable memory that outlives any single context.

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  Window 1    │     │  Window 2    │     │  Window 3    │
│              │     │              │     │              │
│ Research     │     │ Research     │     │ Read all     │
│ Tokyo        │     │ Lisbon       │     │ findings     │
│      │       │     │      │       │     │      │       │
│      ▼       │     │      ▼       │     │      ▼       │
│ WRITE to     │     │ READ then    │     │ READ then    │
│ scratchpad   │     │ WRITE        │     │ produce plan │
└──────┬───────┘     └──────┬───────┘     └──────────────┘
       │   ┌────────────────┘
       ▼   ▼
   ┌──────────┐
   │scratchpad│  ← survives all resets
   │  .json   │
   └──────────┘
```

## What This Proves

The POC runs two modes side-by-side:

| Mode | Behavior | Result |
|---|---|---|
| **WITH scratchpad** | Each phase writes findings to `scratchpad.json`, next phase reads it | Final plan uses specific research from all 3 cities |
| **WITHOUT scratchpad** | Each phase runs in isolation, results are discarded | Final plan falls back to generic training knowledge |

## Project Structure

```
task-03-02/
├── .env                  # API key + model configuration
├── requirements.txt      # Python dependencies
├── scratchpad_poc.py     # Main POC script
└── README.md
```

## Step-by-Step Guide

### 1. Prerequisites

- Python 3.10+
- An Anthropic API key

### 2. Configure Environment

```bash
cd domain-05/task-03-02
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
python scratchpad_poc.py
```

### 6. Read the Output

The script runs 3 phases per mode. Watch for:

```
============================================================
RUN 1: WITH SCRATCHPAD (state persists across resets)
============================================================

--- Phase 1: Researching Tokyo (fresh context window) ---
  Cities accumulated in scratchpad: ['Tokyo']

--- Phase 2: Researching Lisbon (fresh context window) ---
  Cities accumulated in scratchpad: ['Tokyo', 'Lisbon']

--- Phase 3: Researching Cape Town (fresh context window) ---
  Cities accumulated in scratchpad: ['Tokyo', 'Lisbon', 'Cape Town']

--- Final Plan (informed by scratchpad) ---
  [Detailed plan using specific findings from each phase]

============================================================
RUN 2: WITHOUT SCRATCHPAD (no persistence across resets)
============================================================
  (research done but NOT persisted anywhere)
  ...
--- Final Plan (no prior research available) ---
  [Generic plan with no phase-specific research]
```

Results are also saved as `scratchpad_results_<timestamp>.json`.

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| `ANTHROPIC_API_KEY` | — | Your Anthropic API key (required) |
| `MODEL_NAME` | `claude-sonnet-4-20250514` | Model to use |
| `SCRATCHPAD_PATH` | `scratchpad.json` | Where the scratchpad file is stored |

## Key Takeaway for the Architect Exam

Scratchpad files solve the **state loss problem** in long-running agentic workflows:

- **Context compaction** discards older messages — scratchpad survives
- **New conversation windows** start empty — scratchpad carries forward
- **Crash recovery** — agent can resume from last scratchpad state
- **Auditability** — scratchpad on disk is inspectable / debuggable

Production systems (including Claude Code itself) use this pattern via `CLAUDE.md`, memory files, and task lists that persist across context resets.
