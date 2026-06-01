"""
fork_session POC: Branch conversations for exploration without polluting the main context.

Pattern: Maintain a "main" message history. When exploration is needed,
fork a copy, let Claude explore freely, then extract only the final insight
back into the main session.
"""

import os
import copy
from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()

client = Anthropic()
MODEL = os.getenv("MODEL_NAME", "claude-sonnet-4-6")


def chat(messages: list[dict], user_msg: str) -> str:
    """Send a message and return assistant response."""
    messages.append({"role": "user", "content": user_msg})
    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        messages=messages,
    )
    assistant_text = response.content[0].text
    messages.append({"role": "assistant", "content": assistant_text})
    return assistant_text


def fork_session(messages: list[dict]) -> list[dict]:
    # Deep copy ensures mutations in the fork never alter the parent session
    return copy.deepcopy(messages)


def extract_insight(forked_messages: list[dict]) -> str:
    # Only the final assistant reply carries the distilled exploration result
    for msg in reversed(forked_messages):
        if msg["role"] == "assistant":
            return msg["content"]
    return ""


def main():
    # Main session: the "clean" conversation that stays focused
    main_session = []

    print("=" * 60)
    print("STEP 1: Establish main session context")
    print("=" * 60)
    response = chat(
        main_session,
        "I'm building a REST API for a bookstore. We need to design the /books endpoint. "
        "What HTTP methods should we support?",
    )
    print(f"Main session response:\n{response}\n")

    print("=" * 60)
    print("STEP 2: Fork session to explore a tangent (pagination strategies)")
    print("=" * 60)

    # Fork BEFORE the exploratory question so main stays uncontaminated
    exploration_session = fork_session(main_session)

    # Explore freely in the fork — multiple turns won't bloat the main context
    explore_response_1 = chat(
        exploration_session,
        "Let's explore pagination strategies for the GET /books endpoint. "
        "Compare cursor-based vs offset-based pagination with pros and cons.",
    )
    print(f"Fork exploration (turn 1):\n{explore_response_1}\n")

    explore_response_2 = chat(
        exploration_session,
        "Now consider our bookstore has 1M+ books. Which strategy handles "
        "real-time insertions better? Give me a final one-line recommendation.",
    )
    print(f"Fork exploration (turn 2):\n{explore_response_2}\n")

    print("=" * 60)
    print("STEP 3: Extract insight back into main session")
    print("=" * 60)

    # Merge only the conclusion, not the entire exploration history
    insight = extract_insight(exploration_session)
    merge_msg = (
        f"After exploring pagination options, here's the conclusion: {insight}. "
        f"Now, let's continue designing the /books endpoint with this in mind. "
        f"What should the response schema look like?"
    )
    response = chat(main_session, merge_msg)
    print(f"Main session continues:\n{response}\n")

    print("=" * 60)
    print("SESSION COMPARISON")
    print("=" * 60)
    # Main stays lean; fork absorbed the exploratory noise
    print(f"Main session message count: {len(main_session)}")
    print(f"Forked session message count: {len(exploration_session)}")
    print(
        f"Messages saved from main context: "
        f"{len(exploration_session) - len(main_session)}"
    )


if __name__ == "__main__":
    main()
