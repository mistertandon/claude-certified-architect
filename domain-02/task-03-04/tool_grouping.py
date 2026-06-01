"""
POC: Tool Grouping — Organize Related Tools into Specialized Agents
(Claude Architect Exam — Domain 02, Tool Distribution Strategies)

Scenario:
  An e-commerce support system has 6 tools spanning 3 domains:
    • Order Agent   → track_order, cancel_order
    • Billing Agent → get_invoice, process_refund
    • Product Agent → search_products, check_inventory

  A coordinator (router) receives the user query, decides which
  specialist to delegate to, then the specialist runs with ONLY
  its own tool group.

Key insight: Tool grouping reduces hallucination risk and cost.
  - Fewer tools per call → smaller prompt, lower latency, cheaper.
  - Each agent sees only relevant tools → can't misuse unrelated ones.
  - Mirrors real org boundaries (teams own their toolsets).
"""

import os
import json
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

client = Anthropic()
MODEL = "claude-sonnet-4-6"

# ── Tool Definitions by Domain ────────────────────────────────────────────
# Tools are defined once but GROUPED by specialty. Each specialist agent
# receives only its own group — never the full set.

ORDER_TOOLS = [
    {
        "name": "track_order",
        "description": "Look up current status and tracking info for an order by ID.",
        "input_schema": {
            "type": "object",
            "properties": {
                "order_id": {"type": "string", "description": "Order ID, e.g. 'ORD-1234'"}
            },
            "required": ["order_id"],
        },
    },
    {
        "name": "cancel_order",
        "description": "Cancel a pending order. Only works if order has not shipped yet.",
        "input_schema": {
            "type": "object",
            "properties": {
                "order_id": {"type": "string", "description": "Order ID to cancel"},
                "reason": {"type": "string", "description": "Cancellation reason"},
            },
            "required": ["order_id"],
        },
    },
]

BILLING_TOOLS = [
    {
        "name": "get_invoice",
        "description": "Retrieve invoice details for an order.",
        "input_schema": {
            "type": "object",
            "properties": {
                "order_id": {"type": "string", "description": "Order ID for the invoice"}
            },
            "required": ["order_id"],
        },
    },
    {
        "name": "process_refund",
        "description": "Initiate a refund for a completed order.",
        "input_schema": {
            "type": "object",
            "properties": {
                "order_id": {"type": "string", "description": "Order ID to refund"},
                "amount": {"type": "number", "description": "Refund amount in USD"},
            },
            "required": ["order_id", "amount"],
        },
    },
]

PRODUCT_TOOLS = [
    {
        "name": "search_products",
        "description": "Search the product catalog by keyword.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search keyword"},
                "category": {"type": "string", "description": "Optional category filter"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "check_inventory",
        "description": "Check stock availability for a specific product SKU.",
        "input_schema": {
            "type": "object",
            "properties": {
                "sku": {"type": "string", "description": "Product SKU, e.g. 'SKU-5678'"}
            },
            "required": ["sku"],
        },
    },
]

# ── Registry: maps agent name → its tool group ───────────────────────────
# The router picks an agent name; we look up its tools here.
# This indirection is what makes tool grouping work — the specialist
# never sees tools outside its domain.

AGENT_REGISTRY = {
    "order_agent": {
        "tools": ORDER_TOOLS,
        "system": (
            "You are an Order Specialist. You handle order tracking and cancellations. "
            "Use your tools to help the customer. Be concise."
        ),
    },
    "billing_agent": {
        "tools": BILLING_TOOLS,
        "system": (
            "You are a Billing Specialist. You handle invoices and refunds. "
            "Use your tools to help the customer. Be concise."
        ),
    },
    "product_agent": {
        "tools": PRODUCT_TOOLS,
        "system": (
            "You are a Product Specialist. You handle product search and inventory checks. "
            "Use your tools to help the customer. Be concise."
        ),
    },
}


# ── Simulated Tool Execution ─────────────────────────────────────────────

def execute_tool(name: str, inputs: dict) -> str:
    """Stub responses — in production these hit real backends."""
    responses = {
        "track_order": lambda: {"order_id": inputs["order_id"], "status": "shipped", "eta": "2026-05-09", "carrier": "FedEx"},
        "cancel_order": lambda: {"order_id": inputs["order_id"], "cancelled": True, "reason": inputs.get("reason", "customer request")},
        "get_invoice": lambda: {"order_id": inputs["order_id"], "total": 149.99, "tax": 12.50, "issued": "2026-05-01"},
        "process_refund": lambda: {"order_id": inputs["order_id"], "refunded": inputs["amount"], "status": "processing"},
        "search_products": lambda: {"results": [{"name": "Wireless Headphones", "sku": "SKU-5678", "price": 79.99}, {"name": "Bluetooth Speaker", "sku": "SKU-9012", "price": 49.99}]},
        "check_inventory": lambda: {"sku": inputs["sku"], "in_stock": True, "quantity": 42},
    }
    return json.dumps(responses.get(name, lambda: {"error": f"Unknown tool: {name}"})())


# ── Step 1: Router — classify which specialist handles the query ──────────
# The router sees NO tools at all. Its only job is to output a JSON
# classification. This separation is critical: giving the router tools
# would let it bypass specialist boundaries.

ROUTER_SYSTEM = """You are a request router for an e-commerce support system.
Classify the user's request into exactly ONE specialist agent.

Available agents:
- order_agent: order tracking, order status, cancellations
- billing_agent: invoices, payments, refunds
- product_agent: product search, inventory, availability

Respond with ONLY a JSON object: {"agent": "<agent_name>", "reason": "<one-line reason>"}
No other text."""


def route_request(user_message: str) -> str:
    """Ask the router model which specialist should handle this query."""
    response = client.messages.create(
        model=MODEL,
        max_tokens=150,
        system=ROUTER_SYSTEM,
        # No tools parameter — router must NOT have tool access.
        # This enforces the separation: routing logic ≠ tool execution.
        messages=[{"role": "user", "content": user_message}],
    )
    raw = response.content[0].text.strip()
    routing = json.loads(raw)
    return routing["agent"]


# ── Step 2: Specialist — runs with only its own grouped tools ─────────────

def run_specialist(agent_name: str, user_message: str) -> str:
    """
    Dispatch to the specialist, which sees ONLY its own tool group.
    This is the core of tool grouping: the API call's `tools` parameter
    contains a subset, not the full catalog.
    """
    agent_config = AGENT_REGISTRY[agent_name]

    # KEY LINE: pass only this agent's tools, not all 6.
    # Fewer tools → less confusion, lower cost, tighter access control.
    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=agent_config["system"],
        tools=agent_config["tools"],
        messages=[{"role": "user", "content": user_message}],
    )

    # ── Agentic loop: process tool calls until the model stops ────────
    messages = [
        {"role": "user", "content": user_message},
        {"role": "assistant", "content": response.content},
    ]

    while response.stop_reason == "tool_use":
        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                print(f"    [tool_call] {block.name}({json.dumps(block.input)})")
                result = execute_tool(block.name, block.input)
                print(f"    [tool_result] {result}")
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result,
                })

        messages.append({"role": "user", "content": tool_results})

        # Continue with the SAME scoped tools — the agent never gains access
        # to tools outside its group, even across loop iterations.
        response = client.messages.create(
            model=MODEL,
            max_tokens=1024,
            system=agent_config["system"],
            tools=agent_config["tools"],
            messages=messages,
        )
        messages.append({"role": "assistant", "content": response.content})

    final_text = "".join(b.text for b in response.content if b.type == "text")
    return final_text


# ── Orchestrator: ties router + specialist together ───────────────────────

def handle_query(user_message: str):
    """Full pipeline: route → specialist → answer."""
    print(f"\n{'='*64}")
    print(f"  Customer: \"{user_message}\"")
    print(f"{'='*64}")

    # Step 1: classify
    agent_name = route_request(user_message)
    agent_tools = [t["name"] for t in AGENT_REGISTRY[agent_name]["tools"]]
    print(f"  → Routed to: {agent_name}")
    print(f"  → Tools available to this agent: {agent_tools}")

    # Compare: a monolithic agent would see all 6 tools here.
    all_tools = [t["name"] for group in AGENT_REGISTRY.values() for t in group["tools"]]
    print(f"  → Tools hidden from this agent: {[t for t in all_tools if t not in agent_tools]}")

    # Step 2: specialist handles it with scoped tools
    answer = run_specialist(agent_name, user_message)
    print(f"\n  Assistant: {answer}")
    return answer


# ── Demo ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("╔════════════════════════════════════════════════════════════════╗")
    print("║  POC: Tool Grouping — Specialized Agents with Scoped Tools   ║")
    print("╚════════════════════════════════════════════════════════════════╝")

    # Each query hits a different specialist — observe which tools are
    # available vs hidden for each one.

    test_queries = [
        "Where is my order ORD-1234? Has it shipped yet?",
        "I need a refund of $50 for order ORD-5678",
        "Do you have wireless headphones in stock?",
    ]

    for query in test_queries:
        handle_query(query)

    # ── Summary ───────────────────────────────────────────────────────
    print(f"\n\n{'='*64}")
    print("KEY TAKEAWAYS — Tool Grouping Strategy:")
    print("-"*64)
    print("1. SEPARATION: Router has zero tools; specialists have only theirs")
    print("2. SCOPING:    Each agent sees 2 tools, not all 6 — reduces noise")
    print("3. SECURITY:   Billing agent can't cancel orders; Order agent can't refund")
    print("4. COST:       Fewer tool definitions per call → smaller prompt → cheaper")
    print("5. SCALING:    Add a new domain (e.g. shipping_agent) without touching others")
    print("="*64)
