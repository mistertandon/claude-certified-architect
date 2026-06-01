# Task 04-05: Prompt Chaining vs Dynamic Adaptive Decomposition

## Concept

Two orchestration patterns for multi-step LLM workflows, chosen based on **task predictability**:

| Pattern | When to Use | Trade-off |
|---|---|---|
| **Prompt Chaining** | Steps are known upfront (translate → summarize → format) | Cheaper, faster, but brittle if task shape varies |
| **Dynamic Decomposition** | Steps depend on intermediate results (debug, analyze) | Flexible, but more tokens and latency |

## Architecture

```
PROMPT CHAINING (fixed pipeline)        DYNAMIC DECOMPOSITION (runtime decisions)
┌──────────┐                            ┌──────────────┐
│ Step 1:  │──output──▶┌──────────┐     │   Planner    │◀─── accumulated context
│ Research │           │ Step 2:  │     │  (LLM + tool)│───▶ create_subtask()
└──────────┘           │ Outline  │     └──────┬───────┘
                       └────┬─────┘            │ subtask prompt
                            │            ┌─────▼───────┐
                       ┌────▼─────┐      │  Executor   │──result──▶ back to Planner
                       │ Step 3:  │      │  (LLM call) │           (loop until is_final)
                       │  Draft   │      └─────────────┘
                       └──────────┘
```

## Setup

### 1. Install dependencies

```bash
cd domain-01/task-04-05
pip install anthropic python-dotenv
```

### 2. Configure environment

```bash
cp .env .env.local
# Edit .env and set your actual API key:
# ANTHROPIC_API_KEY=sk-ant-...
```

### 3. Run

```bash
python chaining_vs_decomposition.py
```

## Expected Output

The script runs two tasks:

1. **"Write a blog post about quantum computing"** → detected as **predictable** → uses **Prompt Chaining** (3 fixed steps: research → outline → draft)
2. **"Analyze why our API latency spiked..."** → detected as **unpredictable** → uses **Dynamic Decomposition** (model decides steps at runtime via tool use)

## Exam Key Points

- **Chaining** = deterministic pipeline, each step's output feeds the next
- **Decomposition** = the LLM uses a tool (`create_subtask`) to decide what to do next
- **Selection heuristic**: predictable verb → chain; open-ended task → decompose
- Real systems may use a **classifier or the LLM itself** to pick the strategy
