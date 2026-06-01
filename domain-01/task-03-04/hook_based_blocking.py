"""
Hook-Based Blocking: Refund Escalation Guard

Architectural pattern: Pre-execution hooks intercept tool calls BEFORE they reach
the business logic, enforcing hard constraints that Claude cannot bypass — even if
the user asks it to. This is the recommended approach for safety-critical guardrails
because prompt-level instructions can be jailbroken, but code-level hooks cannot.

Flow:
  User request -> Claude selects tool -> HOOK intercepts -> allow / block+redirect
"""

import json
import anthropic
from dotenv import load_dotenv

load_dotenv()

# --- Hook: the guardrail layer that sits between Claude and execution ---

# Threshold lives in code, not in the prompt, so it can't be socially-engineered away.
REFUND_LIMIT = 500.0


def refund_hook(tool_name: str, tool_input: dict) -> dict:
    """
    Pre-execution hook that enforces the refund ceiling.
    Returns a dict with 'allowed' bool and either the original input or a redirect.
    """
    if tool_name != "process_refund":
        # Non-refund tools pass through unchecked.
        return {"allowed": True, "tool_input": tool_input}

    amount = tool_input.get("amount", 0)

    if amount > REFUND_LIMIT:
        # Block and redirect — the tool never fires; Claude gets a structured
        # denial it can relay to the user.
        return {
            "allowed": False,
            "reason": f"Refund ${amount:.2f} exceeds ${REFUND_LIMIT:.2f} limit.",
            "redirect": "escalate_to_manager",
            "escalation_payload": {
                "customer_id": tool_input.get("customer_id"),
                "requested_amount": amount,
                "reason": tool_input.get("reason", ""),
            },
        }

    return {"allowed": True, "tool_input": tool_input}


# --- Tool definitions: what Claude sees and can choose from ---

# Defined as a list so it's easy to extend; Claude picks the right tool via intent.
tools = [
    {
        "name": "process_refund",
        "description": "Process a customer refund. Use this when the customer requests money back.",
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_id": {
                    "type": "string",
                    "description": "The customer's account ID.",
                },
                "amount": {
                    "type": "number",
                    "description": "Refund amount in USD.",
                },
                "reason": {
                    "type": "string",
                    "description": "Reason for the refund.",
                },
            },
            "required": ["customer_id", "amount", "reason"],
        },
    },
    {
        "name": "escalate_to_manager",
        "description": "Escalate a case to a human manager for review.",
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_id": {"type": "string"},
                "requested_amount": {"type": "number"},
                "reason": {"type": "string"},
            },
            "required": ["customer_id", "requested_amount", "reason"],
        },
    },
]

# --- Simulated tool execution ---


def execute_tool(tool_name: str, tool_input: dict) -> str:
    if tool_name == "process_refund":
        return json.dumps(
            {
                "status": "approved",
                "refund_id": "RF-20260506",
                "amount": tool_input["amount"],
            }
        )
    if tool_name == "escalate_to_manager":
        return json.dumps(
            {
                "status": "escalated",
                "ticket_id": "ESC-7891",
                "message": f"Manager review requested for ${tool_input['requested_amount']:.2f} refund.",
            }
        )
    return json.dumps({"error": "Unknown tool"})


# --- Agentic loop with hook interception ---


def run_agent(user_message: str):
    client = anthropic.Anthropic()

    # System prompt tells Claude its role but does NOT encode the $500 rule —
    # the hook enforces that, keeping policy out of the prompt attack surface.
    system = (
        "You are a customer-support agent. "
        "Use the provided tools to handle refund requests. "
        "If a refund is blocked, explain the escalation to the customer politely."
    )

    messages = [{"role": "user", "content": user_message}]

    print(f"\n{'='*60}")
    print(f"Customer: {user_message}")
    print(f"{'='*60}")

    # Agentic loop: keeps running until Claude produces a final text response.
    while True:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            system=system,
            tools=tools,
            messages=messages,
        )

        # Collect all tool uses from this turn — Claude may call multiple tools.
        tool_uses = [b for b in response.content if b.type == "tool_use"]

        if response.stop_reason == "end_turn" or not tool_uses:
            # Claude is done — extract and print its final answer.
            text_parts = [b.text for b in response.content if hasattr(b, "text")]
            print(f"\nAgent: {''.join(text_parts)}")
            break

        # Process each tool call through the hook before execution.
        tool_results = []
        for tool_use in tool_uses:
            print(f"\n-> Tool call: {tool_use.name}({json.dumps(tool_use.input)})")

            # === HOOK FIRES HERE — before any business logic runs ===
            hook_result = refund_hook(tool_use.name, tool_use.input)

            if hook_result["allowed"]:
                result = execute_tool(tool_use.name, tool_use.input)
                print(f"   ALLOWED -> {result}")
            else:
                # Hook blocked the call; run the redirect tool instead so
                # Claude sees a structured escalation, not a raw error.
                print(f"   BLOCKED -> {hook_result['reason']}")
                result = execute_tool(
                    hook_result["redirect"], hook_result["escalation_payload"]
                )
                print(f"   REDIRECTED to {hook_result['redirect']} -> {result}")

            tool_results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": tool_use.id,
                    "content": result,
                }
            )

        # Feed tool results back so Claude can formulate its response.
        messages.append({"role": "assistant", "content": response.content})
        messages.append({"role": "user", "content": tool_results})


# --- Demo: one request below and one above the limit ---

if __name__ == "__main__":
    # Case 1: $150 refund — under limit, hook allows it.
    run_agent(
        "Hi, I'm customer C-1234. I'd like a $150 refund for a defective product."
    )

    # Case 2: $750 refund — over limit, hook blocks and redirects to escalation.
    run_agent(
        "Hello, customer C-5678 here. Please refund $750 for my cancelled subscription."
    )
