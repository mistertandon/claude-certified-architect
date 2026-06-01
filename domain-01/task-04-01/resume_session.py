"""
POC: --resume flag behavior — continue previous sessions with preserved context.

Claude Code's `--resume` flag restores a prior conversation by replaying its
message history, so the model retains full context without re-prompting.
This script simulates that mechanism using the Anthropic SDK.
"""

import json
import os
from pathlib import Path

from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

# Persist conversation to disk so it survives process termination —
# mirrors how Claude Code serializes sessions for later resumption.
SESSION_FILE = Path("session_history.json")

client = Anthropic()  # Reads ANTHROPIC_API_KEY from environment automatically.


def load_session() -> list[dict]:
    """Load prior message history from disk — the core of --resume."""
    if SESSION_FILE.exists():
        return json.loads(SESSION_FILE.read_text())
    return []


def save_session(messages: list[dict]) -> None:
    """Persist after every turn so a crash doesn't lose context."""
    SESSION_FILE.write_text(json.dumps(messages, indent=2))


def chat(user_input: str, messages: list[dict]) -> str:
    # Append new user turn to the existing history — order matters
    # because the API reconstructs context from the full sequence.
    messages.append({"role": "user", "content": user_input})

    response = client.messages.create(
        model="claude-sonnet-4-6-20250514",
        max_tokens=1024,
        # System prompt is stateless; all statefulness comes from `messages`.
        system="You are a helpful assistant. Refer to earlier messages when relevant.",
        messages=messages,
    )

    assistant_text = response.content[0].text

    # Store assistant reply so the next invocation (--resume) sees it.
    messages.append({"role": "assistant", "content": assistant_text})
    save_session(messages)

    return assistant_text


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Claude session with --resume support")
    # --resume mirrors the Claude Code CLI flag: when present, the process
    # loads prior history instead of starting fresh.
    parser.add_argument(
        "--resume", action="store_true",
        help="Continue from the last saved session instead of starting fresh."
    )
    args = parser.parse_args()

    if args.resume:
        messages = load_session()
        if messages:
            print(f"[Resumed session with {len(messages)} prior messages]\n")
        else:
            print("[No prior session found — starting fresh]\n")
    else:
        # Wipe stale history so the model doesn't inherit unrelated context.
        messages = []
        if SESSION_FILE.exists():
            SESSION_FILE.unlink()
        print("[New session started]\n")

    print("Type 'quit' to exit. Re-run with --resume to continue this session.\n")

    while True:
        user_input = input("You: ").strip()
        if user_input.lower() in ("quit", "exit"):
            break

        reply = chat(user_input, messages)
        print(f"\nClaude: {reply}\n")


if __name__ == "__main__":
    main()
