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

## Why Hub-and-Spoke?

- **Separation of concerns** — each spoke has one job, making prompts focused and outputs predictable
- **Scalability** — add new spokes without modifying existing ones
- **Quality** — the hub can weigh and reconcile conflicting spoke outputs
- **Tradeoff** — higher latency and token cost vs. single-agent (each spoke = separate API call)
