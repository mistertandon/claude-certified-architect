# Task 03-04: Subagent Delegation — Keeping Coordinator Context Clean

## Concept

A **coordinator** agent delegates verbose exploratory work to **disposable subagents** (each a separate API call with its own context). Only structured summaries flow back — the coordinator never sees the raw analysis, keeping its context window small and focused on synthesis.

```
Coordinator ← summary ← Subagent(file1)   # each subagent is isolated
Coordinator ← summary ← Subagent(file2)   # coordinator context = O(summaries)
Coordinator ← summary ← Subagent(fileN)   # NOT O(N × verbose_analysis)
```

## Architecture

| Component | Context | Role |
|-----------|---------|------|
| **Coordinator** | Sees only summaries | Delegates, synthesizes final report |
| **Subagent (per file)** | Fresh context per file | Deep verbose analysis, returns JSON only |

## Contrast: Delegated vs Monolithic

The POC runs both approaches and compares:

- **Delegated**: Coordinator context stays lean (summaries only)
- **Monolithic**: Single agent accumulates ALL verbose analysis — context balloons

## Setup & Run

### 1. Create virtual environment

```bash
cd domain-05/task-03-04
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment

Edit `.env` and set your API key:

```
ANTHROPIC_API_KEY=sk-ant-...your-key...
MODEL_NAME=claude-sonnet-4-20250514
```

### 4. Run the POC

```bash
python subagent_delegation_poc.py
```

## Expected Output

```
================================================================
RUN 1: DELEGATED AUDIT (subagent per file)
================================================================
Spawning subagents for each file...

  Subagent [auth.py]: returned 3 findings
  Subagent [upload.py]: returned 3 findings
  Subagent [session.py]: returned 1 findings
  Subagent [config.py]: returned 4 findings

Coordinator context: 2 messages, ~XXX tokens
Coordinator NEVER saw raw code or verbose analysis

--- Coordinator's synthesized report ---
[Executive summary synthesized from subagent findings]

================================================================
RUN 2: MONOLITHIC AUDIT (everything in one context)
================================================================
  Monolithic [auth.py]: ~XXX tokens in context | 2 messages
  Monolithic [upload.py]: ~XXX tokens in context | 4 messages
  ...

================================================================
COMPARISON: DELEGATED vs MONOLITHIC
================================================================
  Delegated coordinator:    2 messages | ~  XXX tokens
  Monolithic single-agent: 10 messages | ~ XXXX tokens
  Coordinator savings:     ~XX%
```

## Exam-Relevant Takeaways

1. **Subagents are disposable** — their verbose reasoning is discarded after summary extraction
2. **Coordinator context = O(summaries)** — scales independently of analysis depth
3. **Each subagent gets a clean slate** — no cross-file noise polluting analysis
4. **Structured output at boundaries** — JSON schema enforced via system prompt controls what crosses the subagent→coordinator boundary
5. **Tradeoff**: more API calls (one per subagent) but dramatically cleaner coordinator context
