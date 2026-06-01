# Domain 02 / Task 03-02 — Scoped Tool Access (Tool Distribution Strategy)

## Concept Demonstrated

**Each agent only receives tools relevant to its task** — the strongest form of tool isolation.

| Agent | Scoped Tools | Blocked Tools |
|-------|-------------|---------------|
| `research_agent` | `lookup_stock_price`, `search_news` | `calculate_profit`, `format_report` |
| `finance_agent` | `calculate_profit` | `lookup_stock_price`, `search_news`, `format_report` |
| `reporting_agent` | `format_report` | `lookup_stock_price`, `search_news`, `calculate_profit` |
| **coordinator** | **none** | all four tools |

### Why This Matters

1. **Least privilege** — the model can't hallucinate calls to tools it never sees in context
2. **Defense in depth** — even if a model somehow names a blocked tool, the runner rejects it
3. **Reduced confusion** — fewer tools in context means fewer wrong-tool selections

### Architecture

```
User Request
     │
     ▼
┌────────────────┐   0 tools
│  Coordinator   │◄──────────── delegates only, never calls tools
└──┬─────┬─────┬─┘
   │     │     │
   ▼     ▼     ▼
┌─────┐┌─────┐┌─────┐
│Rsrch││Fin. ││Rpt. │  each agent gets its OWN tool subset
│Agent││Agent││Agent│
└─────┘└─────┘└─────┘
 2 tools 1 tool 1 tool
```

## Setup

```bash
cd domain-02/task-03-02

# 1. Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 2. Install dependencies
pip install anthropic python-dotenv

# 3. Set your API key
#    Edit .env and replace "your-api-key-here" with your real Anthropic API key
nano .env
```

## Run

```bash
python scoped_tool_access.py
```

## Expected Output

```
User request: I bought 100 shares of ACME at $120 each. ...
Coordinator has 0 tools — it only delegates.

============================================================
  Agent: research_agent
  Scoped tools: ['lookup_stock_price', 'search_news']
  Blocked tools: ['calculate_profit', 'format_report']
============================================================
  -> research_agent calls: lookup_stock_price({"ticker": "ACME"})
  <- result: {"ticker": "ACME", "price": 142.5, "currency": "USD"}
  Agent research_agent finished.

============================================================
  Agent: finance_agent
  Scoped tools: ['calculate_profit']
  Blocked tools: ['format_report', 'lookup_stock_price', 'search_news']
============================================================
  -> finance_agent calls: calculate_profit({"buy_price": 120, "current_price": 142.5, "shares": 100})
  <- result: {"total_profit": 2250.0, "percent_change": 18.75}
  Agent finance_agent finished.

...
Final answer: <synthesized summary>
```

## Key Exam Takeaways

| Principle | How This POC Shows It |
|-----------|----------------------|
| Scope tools per role | `ROLE_TOOL_SCOPES` dict maps each role → allowed tool names |
| Filter at call time | `get_scoped_tools()` builds the subset before each API call |
| Defense in depth | Runner checks `block.name not in tool_names` even after scoping |
| Toolless coordinator | Coordinator's `messages.create()` has **no `tools` param** at all |
