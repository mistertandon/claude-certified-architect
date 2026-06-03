# Hub-and-Spoke Architecture POC

## Architecture Diagram

```
                    ┌──────────────┐
                    │   User Query │
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
                    │   Hub Agent  │  ← orchestrates & synthesizes
                    └──┬───────┬───┘
                       │       │
              ┌────────▼──┐ ┌──▼────────┐
              │ Researcher│ │  Critic   │  ← specialized spokes
              └────────┬──┘ └──┬────────┘
                       │       │
                    ┌──▼───────▼───┐
                    │  Hub Merges  │
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
                    │ Final Answer │
                    └──────────────┘
```

## Key Concepts

| Concept | Role |
|---------|------|
| **Hub** | Central coordinator — decomposes tasks, dispatches to spokes, merges results |
| **Spoke** | Specialized agent with a narrow mandate (researcher, critic, etc.) |
| **Fan-out** | Hub sends sub-tasks to multiple spokes |
| **Fan-in** | Hub collects and synthesizes spoke outputs |

## Setup & Run

### 1. Create virtual environment

```bash
cd domain-01/task-01-02-01
python -m venv venv
source venv/bin/activate
```

### 2. Install dependencies

```bash
pip install anthropic python-dotenv
```

### 3. Configure environment

```bash
cp .env .env.local
# Edit .env.local and set your actual API key:
# ANTHROPIC_API_KEY=sk-ant-...
```

Or export directly:

```bash
export ANTHROPIC_API_KEY=sk-ant-your-key-here
```

### 4. Run the POC

```bash
python hub_and_spoke.py
```

### Expected Output

```
[User Query]: What are the benefits and risks of microservices architecture?

[Hub-and-Spoke Processing]
  [Hub] Dispatching to spoke: researcher
  [Hub] Received from spoke: researcher
  [Hub] Dispatching to spoke: critic
  [Hub] Received from spoke: critic
  [Hub] Synthesizing spoke outputs...

[Final Synthesized Answer]:
<synthesized response combining research facts and critical analysis>
```
---

## Architect-Level Analysis

### What This POC Demonstrates

The code implements a clean, minimal hub-and-spoke pattern using the Anthropic SDK. The flow is:

```
User Query
    │
    ▼
Hub (Decomposition)    ← LLM decides WHICH spokes to invoke and WHAT to ask each
    │
    ├──► Spoke: Researcher     (stateless, single-turn)
    ├──► Spoke: Critic         (stateless, single-turn)
    └──► Spoke: Practitioner   (stateless, single-turn)
    │
    ▼
Hub (Synthesis)        ← LLM merges spoke outputs into one coherent answer
    │
    ▼
Final Response
```

Three functions map 1:1 to the architectural phases: `hub_decompose` (line 50), `call_spoke` (line 70), `hub_synthesize` (line 82). The hub is "smart" — it uses LLM reasoning to decide spoke selection and task formulation, rather than hardcoded routing.

---

### Significance of Hub-and-Spoke for Agentic Systems

Hub-and-spoke is the **orchestrator-worker** pattern applied to agents. Its core value proposition:

**1. Controlled delegation with centralized authority.**
The hub retains full control over task decomposition and output synthesis. No spoke can autonomously trigger another spoke or escalate beyond its mandate. This makes the system **predictable and auditable** — you always know the execution topology at design time (star graph, depth 1).

**2. Spoke isolation eliminates cross-contamination.**
Each spoke gets a clean context window — its own system prompt and only the sub-task assigned by the hub (line 72-78). Spokes never see each other's outputs during execution. This prevents the "opinion drift" problem where a critic's framing would bias the researcher's facts, or vice versa.

**3. The hub acts as an information bottleneck by design.**
All information flows through the hub. This is both the pattern's greatest strength (central point of control, quality gating, conflict resolution) and its fundamental constraint.

---

### When to Use Hub-and-Spoke

| Scenario | Why It Fits |
|----------|-------------|
| **Multi-perspective analysis** (exactly this POC) | Need independent, unbiased viewpoints that are merged post-hoc |
| **Embarrassingly parallel sub-tasks** | Tasks that decompose cleanly with no inter-task dependencies |
| **Compliance/audit-sensitive workflows** | Every delegation decision is logged at the hub; full traceability |
| **Fixed, well-understood spoke capabilities** | When you know your specialist roles upfront (researcher, coder, reviewer) |
| **Cost-controlled pipelines** | Hub can selectively invoke only relevant spokes (line 41: "You may use one, some, or all") |

---

### When NOT to Use It

| Scenario | Why It Fails |
|----------|-------------|
| **Iterative refinement loops** | Spokes can't talk to each other. If the critic finds a flaw in the researcher's output, there's no mechanism for the researcher to revise — the hub would need to manually re-dispatch, which this pattern doesn't model |
| **Tasks requiring shared state** | Spokes are stateless single-turn calls. No conversation memory, no shared scratchpad. A coding agent that needs to read file A, then modify file B based on A, then test — this requires sequential state passing, not fan-out |
| **Deep reasoning chains** | Hub-and-spoke is depth-1. For problems requiring multi-step decomposition (break task into sub-tasks, then sub-sub-tasks), you need a **hierarchical** or **recursive** orchestrator |
| **Dynamic, emergent workflows** | The spoke registry is static (line 24-32). You can't discover or spin up new specialist capabilities at runtime. Compare with agent frameworks that support tool-use and self-directed exploration |
| **Latency-sensitive applications** | Sequential spoke dispatch (lines 116-119) means total latency = sum of all spoke calls. Even with parallelization, synthesis still waits for the slowest spoke |

---

### Limitations in This Implementation

**1. Sequential fan-out (lines 116-119).**
Spokes are called in a `for` loop. Since spokes are independent and share no state, these should be parallel. With `asyncio.gather` or `concurrent.futures.ThreadPoolExecutor`, you'd cut latency from `sum(spoke_times)` to `max(spoke_times)`. For 3 spokes at ~2s each, that's 6s vs 2s.

**2. Fragile JSON parsing of hub decomposition (line 61).**
`json.loads(raw)` on raw LLM output. No retry, no fallback, no structured output. The LLM could return markdown-wrapped JSON, trailing text, or malformed output. Production code should use Anthropic's tool-use / function-calling to get guaranteed structured output rather than hoping for clean JSON.

**3. No spoke output validation.**
The hub synthesis blindly trusts spoke outputs (line 84-85). A spoke could hallucinate, return an error, or produce empty output. There's no quality gate between spoke execution and synthesis.

**4. No conversation memory.**
Each call is a single-turn `messages` call. The hub can't refine based on user follow-ups. For a real agent, the hub would maintain a conversation history and decide when to re-dispatch vs. answer from prior context.

**5. Token budget is unconstrained at the system level.**
Each spoke gets `max_tokens=1024`, but there's no global budget. Three verbose spokes produce ~3K tokens that get stuffed into the synthesis prompt, potentially blowing the synthesis context or producing a watered-down summary.

**6. Spoke registry is hardcoded and flat.**
No metadata about spoke capabilities, cost, latency, or reliability. A production hub would need this to make intelligent routing decisions — e.g., skip the expensive "practitioner" spoke for simple factual queries.

---

### Architectural Violations / Anti-Patterns to Watch For

**1. Hub becoming a "God Agent."**
If decomposition logic grows complex (conditional routing, multi-step planning, state tracking), the hub becomes a monolithic orchestrator that's hard to test and reason about. At that point, you've outgrown hub-and-spoke and need a **planner-executor** or **DAG-based** architecture.

**2. Spokes developing implicit coupling.**
The moment spoke B's prompt says "consider what a researcher might find" or the synthesis prompt assumes all three spokes always run, you've introduced coupling that defeats the isolation guarantee. In this POC, line 41 ("You may use one, some, or all") correctly avoids this.

**3. Synthesis as lossy compression.**
The hub synthesis (line 82-98) compresses potentially rich, nuanced spoke outputs into "3-4 sentences." For exploratory analysis this is fine, but for decision-support systems, losing spoke-level detail is a design flaw. Consider returning structured output that preserves the spoke-level breakdown alongside the synthesis.

**4. Missing error boundaries.**
If one spoke fails (API error, timeout, content filter), the entire pipeline fails. A resilient hub-and-spoke should degrade gracefully — synthesize from available spoke outputs and note which perspectives are missing.

---

### Comparison with Alternative Agentic Architectures

| Pattern | vs. Hub-and-Spoke |
|---------|-------------------|
| **Chain / Pipeline** | Sequential, each step feeds the next. Better for dependent transformations. Worse for independent parallel analysis |
| **Debate / Adversarial** | Spokes directly challenge each other in rounds. Better for stress-testing ideas. More tokens, harder to converge |
| **Hierarchical (tree)** | Hub can delegate to sub-hubs. Better for deep decomposition. More complex orchestration |
| **Blackboard / Shared State** | All agents read/write a shared workspace. Better for collaborative problem-solving. Harder to control and audit |
| **ReAct / Tool-Use Loop** | Single agent with tools, iterating until done. Better for open-ended exploration. Less structured, harder to parallelize |

---

### Bottom Line

Hub-and-spoke is the **right first architecture** when you need multi-perspective, parallel analysis with centralized control. It's simple, auditable, and maps cleanly to team-of-experts mental models. But it hits a ceiling fast: no spoke-to-spoke communication, no iterative refinement, no dynamic capability discovery. The moment your workflow needs any of those, you should graduate to a DAG-based orchestrator or a planner-executor pattern rather than stretching hub-and-spoke beyond its design intent.

This POC is a solid teaching example. For production, add parallel dispatch, structured output for hub decomposition, spoke-level error handling, and output validation before synthesis.
