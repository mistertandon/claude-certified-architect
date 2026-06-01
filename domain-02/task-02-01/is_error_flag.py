"""
POC: is_error flag — explicitly signalling tool failure to the agent
(Claude Architect Exam — Domain 02)

Demonstrates:
  1. Returning is_error=True so the model treats output as a failure, not data
  2. Returning is_error=False (default) for successful tool results
  3. How the model changes behavior (retries / asks for help) when it
     receives an explicit error signal vs. ambiguous error text
"""

import os
import json
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

client = Anthropic()

# ── Tool Definition ─────────────────────────────────────────────────────────

tools = [
    {
        "name": "get_user_profile",
        "description": (
            "Fetch a user profile by username from the user database.\n\n"
            "INPUT:\n"
            '  - username: alphanumeric string, 3-20 chars. Example: "alice92"\n\n'
            "POSSIBLE OUTCOMES:\n"
            "  - Valid username found: returns {name, email, plan}.\n"
            "  - Valid username not found: returns a not-found message.\n"
            "  - Invalid username format: returns a validation error.\n"
            "  - Database unreachable: returns a service error.\n"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "username": {
                    "type": "string",
                    "description": (
                        "The username to look up. Must be 3-20 alphanumeric characters. "
                        'Examples: "alice92", "bob", "charlie2024".'
                    ),
                }
            },
            "required": ["username"],
        },
    }
]

# ── Mock Data & Simulated Failures ──────────────────────────────────────────

MOCK_DB = {
    "alice92": {"name": "Alice Morgan", "email": "alice@example.com", "plan": "pro"},
    "bob":     {"name": "Bob Lee",      "email": "bob@example.com",   "plan": "free"},
}

# Tracks consecutive failures — lets us demo a retry succeeding on the 2nd attempt
_failure_counter = {}


def handle_get_user_profile(username: str) -> tuple[str, bool]:
    """
    Returns (result_json, is_error_flag).
    The two-value return makes the error signal an explicit, first-class decision
    rather than something the caller infers from the result text.
    """
    import re

    # --- Case 1: validation error (bad input → is_error=True) ---------------
    # is_error tells the model "your input was wrong" so it can self-correct
    # rather than presenting the error string to the user as if it were data.
    if not re.match(r"^[a-zA-Z0-9]{3,20}$", username):
        return (
            json.dumps({
                "error": "VALIDATION_ERROR",
                "message": f"Invalid username '{username}'. Must be 3-20 alphanumeric chars.",
            }),
            True,  # is_error=True → model knows to fix its input and retry
        )

    # --- Case 2: transient service failure (is_error=True) -------------------
    # Simulates a flaky DB: first call for "bob" fails, second succeeds.
    # is_error signals "retry might help" — without it the model would
    # treat the timeout text as the final answer and report it to the user.
    if username == "bob":
        _failure_counter.setdefault(username, 0)
        _failure_counter[username] += 1
        if _failure_counter[username] <= 1:
            return (
                json.dumps({
                    "error": "SERVICE_UNAVAILABLE",
                    "message": "Database connection timed out. Please retry.",
                }),
                True,  # is_error=True → nudges the model to retry the same call
            )

    # --- Case 3: user not found (is_error=False) ----------------------------
    # "Not found" is a valid, expected outcome — not an error.
    # Returning is_error=False (the default) lets the model treat this as
    # normal data and compose a helpful "user doesn't exist" response.
    if username not in MOCK_DB:
        return (
            json.dumps({"found": False, "username": username}),
            False,  # is_error=False → valid result, just empty
        )

    # --- Case 4: success (is_error=False) ------------------------------------
    profile = MOCK_DB[username]
    return (
        json.dumps({"found": True, "username": username, **profile}),
        False,
    )


# ── Agentic Loop ────────────────────────────────────────────────────────────

def run_conversation(user_message: str):
    print(f"\n{'='*70}")
    print(f"USER: {user_message}")
    print(f"{'='*70}")

    messages = [{"role": "user", "content": user_message}]

    while True:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            tools=tools,
            # System prompt primes the model to respect is_error and retry
            system=(
                "You are a helpful assistant with access to a user database tool. "
                "When a tool call returns is_error=true, treat the result as a failure: "
                "fix your input or retry if the error is transient. "
                "Never present error payloads to the user as if they were real data."
            ),
            messages=messages,
        )

        for block in response.content:
            if block.type == "text":
                print(f"\nASSISTANT: {block.text}")

        if response.stop_reason == "end_turn":
            break

        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                print(f"\n>> TOOL CALL: {block.name}({json.dumps(block.input)})")

                result_json, is_error = handle_get_user_profile(**block.input)
                print(f"<< TOOL RESULT (is_error={is_error}): {result_json}")

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result_json,
                    # KEY LINE: is_error is part of the API contract for tool_result.
                    # Without it the model has to guess whether the text represents
                    # success or failure — an ambiguity that causes hallucinations.
                    "is_error": is_error,
                })

        messages.append({"role": "assistant", "content": response.content})
        messages.append({"role": "user", "content": tool_results})


# ── Demo Scenarios ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Scenario 1 — Happy path: valid user, no error
    run_conversation("Look up the profile for alice92.")

    # Scenario 2 — Validation error: bad input triggers is_error=True
    #   Expect: model receives the error signal, corrects input or informs user
    run_conversation("Get me the profile for user @invalid!")

    # Scenario 3 — Transient failure then retry: first call fails, second succeeds
    #   Expect: model sees is_error=True + "retry" hint, calls the tool again
    run_conversation("What plan is bob on?")

    # Scenario 4 — Not found: valid result, is_error stays False
    #   Expect: model composes a polite "user not found" message (no retry)
    run_conversation("Look up the profile for unknownuser99.")
