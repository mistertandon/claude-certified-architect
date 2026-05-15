"""
POC: Context Isolation in Subagents
Each subagent maintains its own message history — no shared state leaks between them.
"""

import os
from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()

# Single client instance — but each "subagent" gets its own message list
client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
MODEL = os.getenv("MODEL", "claude-sonnet-4-6")


def create_subagent(agent_name: str) -> list:
    """Each call returns a fresh message list — this IS the isolation boundary."""
    return []


def send_to_subagent(agent_name: str, messages: list, user_input: str) -> str:
    """Appends to the agent's own history, keeping context private to that agent."""

    # Only this agent's history is sent — other agents' turns are invisible
    messages.append({"role": "user", "content": user_input})

    response = client.messages.create(
        model=MODEL,
        max_tokens=256,
        # System prompt scopes the agent's identity — reinforces isolation
        system=f"You are subagent '{agent_name}'. Answer concisely. "
               f"You have NO knowledge of other agents or their conversations.",
        messages=messages,
    )

    assistant_text = response.content[0].text
    # Persist response only in THIS agent's context
    messages.append({"role": "assistant", "content": assistant_text})
    return assistant_text


def main():
    # --- Two independent subagents, each with isolated context ---
    agent_a_messages = create_subagent("Alpha")
    agent_b_messages = create_subagent("Beta")

    # Step 1: Tell Agent Alpha a secret
    print("=" * 60)
    print("[Parent] Sending secret to Agent Alpha only")
    reply = send_to_subagent(
        "Alpha", agent_a_messages,
        "Remember this secret code: FALCON-42. Confirm you stored it."
    )
    print(f"[Alpha] {reply}\n")

    # Step 2: Ask Agent Beta about the secret — it should have NO knowledge
    print("=" * 60)
    print("[Parent] Asking Agent Beta about the secret (it was never told)")
    reply = send_to_subagent(
        "Beta", agent_b_messages,
        "What is the secret code? Do you know any secret code?"
    )
    print(f"[Beta] {reply}\n")

    # Step 3: Verify Alpha still remembers — its context is intact
    print("=" * 60)
    print("[Parent] Verifying Agent Alpha retains its own context")
    reply = send_to_subagent(
        "Alpha", agent_a_messages,
        "What was the secret code I told you earlier?"
    )
    print(f"[Alpha] {reply}\n")

    # Step 4: Prove Beta's context is separate — ask about Alpha
    print("=" * 60)
    print("[Parent] Asking Beta about Alpha's existence")
    reply = send_to_subagent(
        "Beta", agent_b_messages,
        "Have you spoken with any other agent named Alpha?"
    )
    print(f"[Beta] {reply}\n")

    print("=" * 60)
    print("RESULT: Beta never learns Alpha's secret — contexts are isolated.")


if __name__ == "__main__":
    main()
