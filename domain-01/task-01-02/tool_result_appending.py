"""
Tool Result Appending POC
=========================
Demonstrates how tool results are appended to the conversation after each
tool call, giving the model cumulative context for validation and review.

Key insight: the messages list grows with each iteration —
assistant (tool_use) → user (tool_result) → assistant (next decision).
The model sees ALL prior results when deciding what to do next,
enabling multi-step validation workflows.
"""

import json
import os

import anthropic
from dotenv import load_dotenv

load_dotenv()

client = anthropic.Anthropic()

# --- Tool definitions: a mini validation pipeline ---

tools = [
    {
        "name": "fetch_user_record",
        "description": "Fetch a user record by ID. Returns name, email, and signup date.",
        "input_schema": {
            "type": "object",
            "properties": {
                "user_id": {"type": "string", "description": "The user ID to look up"}
            },
            "required": ["user_id"],
        },
    },
    {
        "name": "validate_email",
        "description": "Check whether an email address is valid and not on a blocklist.",
        "input_schema": {
            "type": "object",
            "properties": {
                "email": {"type": "string", "description": "Email to validate"}
            },
            "required": ["email"],
        },
    },
    {
        "name": "check_account_status",
        "description": "Check if a user account is active, suspended, or flagged.",
        "input_schema": {
            "type": "object",
            "properties": {
                "user_id": {"type": "string", "description": "The user ID to check"}
            },
            "required": ["user_id"],
        },
    },
]

# --- Stub tool executor ---

FAKE_DB = {
    "u-101": {"name": "Alice", "email": "alice@example.com", "signup": "2024-01-15"},
    "u-102": {"name": "Bob", "email": "bob@spam-domain.xyz", "signup": "2025-03-20"},
}


def execute_tool(name: str, input_data: dict) -> str:
    if name == "fetch_user_record":
        uid = input_data["user_id"]
        record = FAKE_DB.get(uid)
        if record:
            return json.dumps({"found": True, **record})
        return json.dumps({"found": False, "error": "User not found"})

    if name == "validate_email":
        email = input_data["email"]
        # Simulate blocklist check
        blocked = email.endswith("@spam-domain.xyz")
        return json.dumps({
            "email": email,
            "valid_format": "@" in email,
            "blocklisted": blocked,
        })

    if name == "check_account_status":
        uid = input_data["user_id"]
        # u-102 is flagged to show multi-step review
        status = "flagged" if uid == "u-102" else "active"
        return json.dumps({"user_id": uid, "status": status})

    return json.dumps({"error": f"Unknown tool: {name}"})


# --- Agentic loop with explicit conversation tracking ---

def run_validation_loop(user_message: str) -> None:
    print(f"\n{'='*60}")
    print(f"User: {user_message}")
    print(f"{'='*60}\n")

    # The messages list IS the conversation history — it accumulates every
    # assistant response and tool result across iterations.
    messages = [{"role": "user", "content": user_message}]
    iteration = 0

    while True:
        iteration += 1
        print(f"--- Iteration {iteration} ---")

        # On each call, the model receives the FULL messages list,
        # including all prior tool_use + tool_result pairs.
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            tools=tools,
            messages=messages,
            system="You are a user-account reviewer. When asked to review a user, "
                   "fetch their record first, then validate their email, then check "
                   "account status. Finally, summarize your findings as a review verdict.",
        )
        print("Model response :: ", response)
        print(f"stop_reason: {response.stop_reason}")

        # --- Snapshot: show how the conversation has grown ---
        print(f"  messages in context: {len(messages)}")

        if response.stop_reason == "end_turn":
            for block in response.content:
                if hasattr(block, "text"):
                    print(f"\nAssistant (final review):\n{block.text}")
            break

        if response.stop_reason == "tool_use":
            # STEP A: Append the assistant's full response (contains tool_use blocks).
            # This preserves the model's reasoning + tool call IDs in the conversation.
            messages.append({"role": "assistant", "content": response.content})

            # STEP B: Execute each tool and collect results.
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    print(f"  Tool call: {block.name}({json.dumps(block.input)})")
                    result = execute_tool(block.name, block.input)
                    print(f"  Tool result: {result}")
                    tool_results.append({
                        "type": "tool_result",
                        # tool_use_id links this result back to the specific tool_use
                        # block — the API rejects mismatched or missing IDs.
                        "tool_use_id": block.id,
                        "content": result,
                    })

            # STEP C: Append tool results as a user message.
            # API requires user/assistant alternation; tool_result is a special
            # user-role message type that completes the tool_use handshake.
            messages.append({"role": "user", "content": tool_results})
            print(f"Messages after iteration {iteration}: ", messages)

            # The loop now repeats. On the next API call the model will see:
            #   [original user msg, asst(tool_use), user(tool_result), ...]
            # growing with each iteration — this is tool result appending.

        print()

    # --- Final conversation snapshot ---
    print(f"\n{'='*60}")
    print("Conversation structure (role / content-type per message):")
    print(f"{'='*60}")
    for i, msg in enumerate(messages):
        role = msg["role"]
        if isinstance(msg["content"], str):
            kind = "text"
        elif isinstance(msg["content"], list):
            types = [getattr(b, "type", b.get("type", "?")) if isinstance(b, dict)
                     else getattr(b, "type", "?") for b in msg["content"]]
            kind = ", ".join(types)
        else:
            kind = "unknown"
        print(f"  [{i}] {role}: {kind}")


if __name__ == "__main__":
    # Review u-102 — forces multi-step: fetch → validate (blocklisted!) → status check (flagged!)
    run_validation_loop("Review user u-102 and give me a verdict on their account.")
