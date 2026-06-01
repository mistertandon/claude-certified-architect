"""
POC: isRetryable error response design pattern for agentic tool use.

When a tool call fails, the error result must tell the agent WHETHER retrying
the same call could succeed (transient failure) or would always fail (permanent).
This lets the agent decide: retry vs. adapt vs. give up.
"""

import anthropic
import json
import random

client = anthropic.Anthropic()
MODEL = "claude-sonnet-4-6"

# ---------------------------------------------------------------------------
# 1. Tool definition — the agent can look up order status
# ---------------------------------------------------------------------------
tools = [
    {
        "name": "get_order_status",
        "description": "Look up the current status of a customer order by order ID.",
        "input_schema": {
            "type": "object",
            "properties": {
                "order_id": {
                    "type": "string",
                    "description": "The order identifier, e.g. ORD-1234"
                }
            },
            "required": ["order_id"]
        }
    }
]

# ---------------------------------------------------------------------------
# 2. Simulated backend — randomly produces transient or permanent failures
# ---------------------------------------------------------------------------
def simulate_order_lookup(order_id: str) -> dict:
    """Simulates a backend that can fail in retryable or non-retryable ways."""

    roll = random.random()

    # ~30 % chance: transient failure (timeout, rate-limit, service blip)
    if roll < 0.3:
        return {
            "error": "Service temporarily unavailable — upstream timeout.",
            # Transient failures CAN succeed on retry; agent should try again.
            "isRetryable": True
        }

    # ~20 % chance: permanent failure (bad input, resource doesn't exist)
    if roll < 0.5:
        return {
            "error": f"Order '{order_id}' not found in the system.",
            # Permanent failures will NEVER succeed with the same input;
            # retrying wastes tokens and time.
            "isRetryable": False
        }

    # ~50 % chance: success
    return {
        "order_id": order_id,
        "status": "shipped",
        "estimated_delivery": "2026-05-10"
    }


# ---------------------------------------------------------------------------
# 3. Build the tool_result content based on success / retryable / permanent
# ---------------------------------------------------------------------------
def build_tool_result(tool_use_id: str, result: dict) -> dict:
    """Translate backend result into the tool_result message the agent sees."""

    if "error" in result:
        # The agent receives BOTH the error text AND the retryability flag
        # so it can make an informed decision without hard-coded retry logic.
        return {
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": tool_use_id,
                    # is_error tells the model this tool call failed
                    "is_error": True,
                    "content": json.dumps({
                        "error": result["error"],
                        # KEY PATTERN: isRetryable drives agent retry decisions
                        "isRetryable": result["isRetryable"]
                    })
                }
            ]
        }

    # Happy path — just return the data
    return {
        "role": "user",
        "content": [
            {
                "type": "tool_result",
                "tool_use_id": tool_use_id,
                "content": json.dumps(result)
            }
        ]
    }


# ---------------------------------------------------------------------------
# 4. Agentic loop with retry awareness
# ---------------------------------------------------------------------------
def run_agent():
    # System prompt teaches the agent HOW to interpret isRetryable.
    # Without this, the model would guess; with it, behavior is deterministic.
    system = """You are a helpful order-tracking assistant with access to tools.

IMPORTANT — error handling rules:
- When a tool returns an error with "isRetryable": true,
  you MUST retry the SAME call (up to 2 retries). Transient failures often
  resolve on the next attempt.
- When a tool returns an error with "isRetryable": false,
  do NOT retry. The call will always fail with the same input.
  Instead, inform the user and suggest alternatives.
"""

    messages = [
        {"role": "user", "content": "What's the status of order ORD-5678?"}
    ]

    MAX_ITERATIONS = 6  # safety cap to avoid infinite loops
    iteration = 0

    print("=" * 60)
    print("USER: What's the status of order ORD-5678?")
    print("=" * 60)

    while iteration < MAX_ITERATIONS:
        iteration += 1
        print(f"\n--- Iteration {iteration} ---")

        response = client.messages.create(
            model=MODEL,
            max_tokens=1024,
            system=system,
            tools=tools,
            messages=messages
        )

        # If the model is done talking (no more tool calls), print and exit
        if response.stop_reason == "end_turn":
            for block in response.content:
                if hasattr(block, "text"):
                    print(f"\nASSISTANT: {block.text}")
            break

        # Process each content block — could be text + tool_use
        for block in response.content:
            if hasattr(block, "text"):
                print(f"  [thinking] {block.text}")

            if block.type == "tool_use":
                print(f"  -> Tool call: {block.name}({json.dumps(block.input)})")

                # Simulate the backend
                result = simulate_order_lookup(block.input["order_id"])
                print(f"  <- Result: {json.dumps(result)}")

                # Append the assistant's message, then the tool result
                messages.append({"role": "assistant", "content": response.content})
                messages.append(build_tool_result(block.id, result))

    else:
        print("\n[Loop hit MAX_ITERATIONS — stopping.]")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    run_agent()
