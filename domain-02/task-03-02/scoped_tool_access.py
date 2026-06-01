"""
POC: Scoped Tool Access — each agent only gets tools relevant to its task
(Claude Architect Exam — Domain 02, Tool Distribution Strategies)

Scenario:
  A user asks "Get the current price of ACME stock and calculate my profit."
  A coordinator delegates to:
    1. Research Agent  → only has `lookup_stock_price` (no math tools)
    2. Finance Agent   → only has `calculate_profit`   (no lookup tools)

Key insight: restricting each agent's tool set prevents hallucinated calls
to irrelevant tools and enforces least-privilege at the API level.
"""

import os
import json
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

client = Anthropic()
MODEL = "claude-sonnet-4-6"

# ── Tool Catalogue ──────────────────────────────────────────────────────────
# All tools live in one catalogue; agents receive only a SUBSET.
# This mirrors real systems where a registry exists but access is scoped.

TOOL_CATALOGUE = {
    "lookup_stock_price": {
        "name": "lookup_stock_price",
        "description": (
            "Return the current stock price for a given ticker symbol. "
            "Accepts uppercase NYSE/NASDAQ tickers (e.g. 'ACME', 'TSLA'). "
            "Returns price in USD as a float."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "Uppercase ticker symbol, e.g. 'ACME'"
                }
            },
            "required": ["ticker"]
        },
    },
    "search_news": {
        "name": "search_news",
        "description": (
            "Search recent financial news headlines for a company. "
            "Returns up to 3 headline strings."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "company": {
                    "type": "string",
                    "description": "Company name or ticker to search for"
                }
            },
            "required": ["company"]
        },
    },
    "calculate_profit": {
        "name": "calculate_profit",
        "description": (
            "Calculate profit/loss given buy price, current price, and shares held. "
            "Returns an object with total_profit and percent_change."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "buy_price": {
                    "type": "number",
                    "description": "Original purchase price per share in USD"
                },
                "current_price": {
                    "type": "number",
                    "description": "Current price per share in USD"
                },
                "shares": {
                    "type": "integer",
                    "description": "Number of shares held"
                }
            },
            "required": ["buy_price", "current_price", "shares"]
        },
    },
    "format_report": {
        "name": "format_report",
        "description": (
            "Format structured data into a human-readable markdown report. "
            "Accepts a title and a list of key-value sections."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Report title"
                },
                "sections": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "heading": {"type": "string"},
                            "content": {"type": "string"}
                        }
                    },
                    "description": "List of {heading, content} sections"
                }
            },
            "required": ["title", "sections"]
        },
    },
}

# ── Scoped Role Definitions ─────────────────────────────────────────────────
# THIS IS THE CORE PATTERN: each role maps to a subset of tool names.
# The agent literally cannot call tools outside its scope — the API
# never receives them, so the model never "sees" them in context.

ROLE_TOOL_SCOPES = {
    "research_agent": ["lookup_stock_price", "search_news"],
    "finance_agent": ["calculate_profit"],
    "reporting_agent": ["format_report"],
}

ROLE_INSTRUCTIONS = {
    "research_agent": (
        "You are a research agent. Your ONLY job is to look up factual data "
        "using the tools provided. Do NOT attempt calculations or formatting."
    ),
    "finance_agent": (
        "You are a finance agent. Your ONLY job is to perform financial "
        "calculations using the tools provided. Do NOT look up prices or format reports."
    ),
    "reporting_agent": (
        "You are a reporting agent. Your ONLY job is to format provided data "
        "into a readable report. Do NOT look up data or run calculations."
    ),
}


def get_scoped_tools(role: str) -> list[dict]:
    """Return only the tool definitions this role is allowed to use."""
    # Filtering at call-time means the model's context window never
    # contains tools it shouldn't invoke — strongest possible guardrail.
    allowed = ROLE_TOOL_SCOPES[role]
    return [TOOL_CATALOGUE[name] for name in allowed]


# ── Simulated Tool Execution ────────────────────────────────────────────────
# Stubs return deterministic data so the POC runs without real services.

def execute_tool(name: str, input_data: dict) -> str:
    if name == "lookup_stock_price":
        prices = {"ACME": 142.50, "TSLA": 248.00, "GOOG": 172.30}
        ticker = input_data["ticker"]
        price = prices.get(ticker, 0.0)
        return json.dumps({"ticker": ticker, "price": price, "currency": "USD"})

    if name == "search_news":
        return json.dumps({"headlines": [
            f"{input_data['company']} beats Q3 earnings expectations",
            f"{input_data['company']} announces new product line",
            f"Analysts upgrade {input_data['company']} to 'Buy'",
        ]})

    if name == "calculate_profit":
        profit = (input_data["current_price"] - input_data["buy_price"]) * input_data["shares"]
        pct = ((input_data["current_price"] - input_data["buy_price"]) / input_data["buy_price"]) * 100
        return json.dumps({"total_profit": round(profit, 2), "percent_change": round(pct, 2)})

    if name == "format_report":
        md = f"# {input_data['title']}\n\n"
        for sec in input_data.get("sections", []):
            md += f"## {sec['heading']}\n{sec['content']}\n\n"
        return md

    return json.dumps({"error": f"Unknown tool: {name}"})


# ── Agent Runner ────────────────────────────────────────────────────────────
# Each agent runs its own agentic loop with ONLY its scoped tools.

def run_scoped_agent(role: str, task: str) -> str:
    """Run an agent with tools restricted to its role scope."""
    scoped_tools = get_scoped_tools(role)
    tool_names = [t["name"] for t in scoped_tools]
    print(f"\n{'='*60}")
    print(f"  Agent: {role}")
    print(f"  Scoped tools: {tool_names}")
    # Showing what the agent CANNOT see is the proof of isolation.
    all_tools = set(TOOL_CATALOGUE.keys())
    blocked = all_tools - set(tool_names)
    print(f"  Blocked tools: {sorted(blocked)}")
    print(f"{'='*60}")

    messages = [{"role": "user", "content": task}]

    # Standard agentic loop — but tools param is the scoped subset.
    while True:
        response = client.messages.create(
            model=MODEL,
            max_tokens=1024,
            system=ROLE_INSTRUCTIONS[role],
            tools=scoped_tools,  # SCOPED — not the full catalogue
            messages=messages,
        )

        # Collect text and tool calls from this turn
        result_text = ""
        tool_results = []

        for block in response.content:
            if block.type == "text":
                result_text += block.text
            elif block.type == "tool_use":
                print(f"  -> {role} calls: {block.name}({json.dumps(block.input)})")

                # DEFENSE IN DEPTH: even if the model somehow hallucinates
                # a tool name outside its scope, we reject it here.
                if block.name not in tool_names:
                    print(f"  !! BLOCKED: {block.name} is outside {role}'s scope")
                    tool_result = json.dumps({"error": "Tool not in your scope"})
                else:
                    tool_result = execute_tool(block.name, block.input)

                print(f"  <- result: {tool_result[:120]}")
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": tool_result,
                })

        # If model made tool calls, feed results back and loop.
        if response.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": tool_results})
            continue

        # end_turn → agent is done; return its final text.
        print(f"  Agent {role} finished.")
        return result_text


# ── Coordinator ─────────────────────────────────────────────────────────────
# The coordinator itself has NO tools — it only delegates and synthesizes.
# This separation ensures the coordinator can't accidentally call data tools.

def run_coordinator(user_request: str):
    """Orchestrate scoped agents to fulfill a user request."""
    print(f"\nUser request: {user_request}")
    print("Coordinator has 0 tools — it only delegates.\n")

    # Step 1: Research agent fetches the stock price
    price_data = run_scoped_agent(
        "research_agent",
        f"Look up the current stock price for ACME. User context: {user_request}",
    )

    # Step 2: Finance agent calculates profit using the looked-up price
    profit_data = run_scoped_agent(
        "finance_agent",
        (
            f"The current ACME price is $142.50. The user bought 100 shares at $120 each. "
            f"Calculate their profit. User context: {user_request}"
        ),
    )

    # Step 3: Reporting agent formats everything
    report = run_scoped_agent(
        "reporting_agent",
        (
            f"Create a portfolio report with these findings:\n"
            f"- Research: {price_data}\n"
            f"- Profit analysis: {profit_data}\n"
        ),
    )

    # Final synthesis by coordinator (no tools, just text)
    print(f"\n{'='*60}")
    print("  COORDINATOR SYNTHESIS (no tools)")
    print(f"{'='*60}")

    synthesis = client.messages.create(
        model=MODEL,
        max_tokens=512,
        system=(
            "You are a coordinator. Summarize the agents' outputs for the user. "
            "You have NO tools — you only synthesize."
        ),
        # No `tools` param at all — coordinator is toolless by design.
        messages=[{
            "role": "user",
            "content": (
                f"Original request: {user_request}\n\n"
                f"Research output:\n{price_data}\n\n"
                f"Finance output:\n{profit_data}\n\n"
                f"Report output:\n{report}"
            ),
        }],
    )

    final = synthesis.content[0].text
    print(f"\nFinal answer:\n{final}")
    return final


# ── Main ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    run_coordinator(
        "I bought 100 shares of ACME at $120 each. "
        "What's the current price and how much profit have I made?"
    )
