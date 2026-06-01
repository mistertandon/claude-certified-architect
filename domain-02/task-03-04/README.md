# Task 03-04: Tool Grouping — Assign Related Tools to Specialized Agents

## Concept

Instead of giving **all tools** to a single monolithic agent, organize them into **domain-specific groups** and assign each group to a **specialist agent**. A lightweight **router** (with zero tools) classifies incoming requests and delegates to the right specialist.

```
                    ┌─────────────┐
   User Query ────▶ │   Router    │  (no tools — classification only)
                    └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
        ┌───────────┐ ┌──────────┐ ┌──────────┐
        │  Order    │ │ Billing  │ │ Product  │
        │  Agent    │ │ Agent    │ │ Agent    │
        ├───────────┤ ├──────────┤ ├──────────┤
        │track_order│ │get_invoice│ │search    │
        │cancel_order││process   │ │ _products│
        │           │ │ _refund  │ │check     │
        │           │ │          │ │_inventory│
        └───────────┘ └──────────┘ └──────────┘
```

### Why Tool Grouping Matters

| Concern | Monolithic (all 6 tools) | Grouped (2 tools each) |
|---|---|---|
| **Hallucination** | Model may pick wrong tool from 6 | Only 2 relevant choices |
| **Cost** | All 6 tool schemas in every prompt | Only 2 schemas per call |
| **Security** | Any tool callable anytime | Billing can't cancel orders |
| **Maintainability** | One giant prompt | Add new agent without touching others |

## Prerequisites

- Python 3.10+
- Anthropic API key

## Setup

```bash
# 1. Navigate to task directory
cd domain-02/task-03-04

# 2. Create virtual environment
python -m venv .venv
source .venv/bin/activate

# 3. Install dependencies
pip install anthropic python-dotenv

# 4. Configure API key
cp .env .env.local
# Edit .env.local and set your ANTHROPIC_API_KEY
```

## Run

```bash
python tool_grouping.py
```

## Expected Output

For each test query you will see:

1. **Routing decision** — which specialist was chosen
2. **Scoped tools** — only 2 tools available to that specialist
3. **Hidden tools** — the 4 tools the specialist cannot access
4. **Tool call + result** — the specialist using its grouped tools
5. **Final answer** — natural language response

```
Customer: "Where is my order ORD-1234?"
  → Routed to: order_agent
  → Tools available: [track_order, cancel_order]
  → Tools hidden:    [get_invoice, process_refund, search_products, check_inventory]
    [tool_call] track_order({"order_id": "ORD-1234"})
  Assistant: Your order ORD-1234 has shipped via FedEx, ETA May 9.
```

## Key Exam Concepts

- **Router has no tools** — enforces separation between classification and execution
- **Each specialist sees only its tool group** — the `tools` parameter in the API call contains a subset
- **Tool grouping is orthogonal to tool_choice** — grouping controls *which* tools are visible; `tool_choice` controls *whether* the model must use them
- **Scales horizontally** — add a `shipping_agent` by registering it in the registry; no changes to existing agents
