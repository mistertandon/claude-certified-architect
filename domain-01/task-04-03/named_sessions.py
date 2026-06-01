"""
Named Sessions POC: Organize parallel workstreams into isolated, named conversations.

Claude Code's `--session-id <name>` flag routes each invocation to a distinct
conversation history. This lets you maintain separate sessions for different
concerns (e.g., "frontend", "backend", "debugging") without cross-contamination.
This script simulates that mechanism using the Anthropic SDK.
"""

import json
import os
from pathlib import Path

from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

# Directory mirrors Claude Code's per-project session storage —
# each named session gets its own file, enabling parallel workstreams.
SESSIONS_DIR = Path("sessions")
SESSIONS_DIR.mkdir(exist_ok=True)

client = Anthropic()
MODEL = os.getenv("MODEL_NAME", "claude-sonnet-4-6")


def session_path(name: str) -> Path:
    # Deterministic filename from session name so the same --session-id
    # always resolves to the same history file.
    return SESSIONS_DIR / f"{name}.json"


def load_session(name: str) -> list[dict]:
    """Load a named session's history — empty list if it doesn't exist yet."""
    path = session_path(name)
    if path.exists():
        return json.loads(path.read_text())
    return []


def save_session(name: str, messages: list[dict]) -> None:
    """Persist after every turn so session state survives process exit."""
    session_path(name).write_text(json.dumps(messages, indent=2))


def list_sessions() -> list[str]:
    """Enumerate available sessions — equivalent to browsing Claude Code's session picker."""
    return sorted(p.stem for p in SESSIONS_DIR.glob("*.json"))


def delete_session(name: str) -> bool:
    path = session_path(name)
    if path.exists():
        path.unlink()
        return True
    return False


def chat(session_name: str, user_msg: str) -> str:
    messages = load_session(session_name)
    messages.append({"role": "user", "content": user_msg})

    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        # System prompt scopes the assistant's role per session —
        # in practice, Claude Code injects project-specific context here.
        system=(
            f"You are assisting in the '{session_name}' workstream. "
            "Stay focused on this workstream's topic. Reference earlier messages when relevant."
        ),
        messages=messages,
    )

    assistant_text = response.content[0].text
    messages.append({"role": "assistant", "content": assistant_text})

    # Write-after-every-turn guarantees no context loss on unexpected exit.
    save_session(session_name, messages)
    return assistant_text


def run_demo():
    """Scripted demo showing why named sessions matter for multi-workstream projects."""

    print("=" * 64)
    print("STEP 1: Create two named sessions for separate concerns")
    print("=" * 64)

    # Two sessions simulate parallel workstreams — like having one terminal
    # for frontend and another for backend, each with its own Claude context.
    r1 = chat(
        "backend",
        "I'm designing a REST API for an e-commerce platform. "
        "What are the essential resource endpoints I need?",
    )
    print(f"[backend] Claude:\n{r1}\n")

    r2 = chat(
        "frontend",
        "I'm building a React storefront. What component hierarchy "
        "would you recommend for the product listing page?",
    )
    print(f"[frontend] Claude:\n{r2}\n")

    print("=" * 64)
    print("STEP 2: Continue each session — context is isolated")
    print("=" * 64)

    # Second turn in 'backend' — Claude remembers the API discussion
    # but knows nothing about the React component hierarchy.
    r3 = chat(
        "backend",
        "Good. Now focus on the /orders endpoint specifically. "
        "What status transitions should an order support?",
    )
    print(f"[backend] Claude:\n{r3}\n")

    # Second turn in 'frontend' — Claude remembers the React discussion
    # but knows nothing about order status transitions.
    r4 = chat(
        "frontend",
        "How should we handle loading and error states in the "
        "product listing component you suggested?",
    )
    print(f"[frontend] Claude:\n{r4}\n")

    print("=" * 64)
    print("STEP 3: List and inspect sessions")
    print("=" * 64)

    sessions = list_sessions()
    print(f"Active sessions: {sessions}")
    for s in sessions:
        msgs = load_session(s)
        print(f"  '{s}' — {len(msgs)} messages")

    print()
    print("=" * 64)
    print("STEP 4: Cross-session context isolation proof")
    print("=" * 64)

    # Ask each session to recall what it discussed — proves no context leak.
    r5 = chat("backend", "Summarize what we've discussed so far in one sentence.")
    print(f"[backend] recalls: {r5}\n")

    r6 = chat("frontend", "Summarize what we've discussed so far in one sentence.")
    print(f"[frontend] recalls: {r6}\n")


def run_interactive():
    """Interactive mode: switch between named sessions like Claude Code's --session-id."""
    print("\nCommands:")
    print("  /new <name>      — create or switch to a named session")
    print("  /switch <name>   — switch to an existing session")
    print("  /list            — show all sessions")
    print("  /delete <name>   — remove a session")
    print("  /quit            — exit\n")

    current_session = None

    while True:
        if current_session:
            prompt = f"[{current_session}] You: "
        else:
            prompt = "(no session) > "

        user_input = input(prompt).strip()
        if not user_input:
            continue

        if user_input.startswith("/new "):
            current_session = user_input[5:].strip()
            msgs = load_session(current_session)
            if msgs:
                print(f"  Switched to existing session '{current_session}' ({len(msgs)} messages)")
            else:
                print(f"  Created new session '{current_session}'")

        elif user_input.startswith("/switch "):
            name = user_input[8:].strip()
            if session_path(name).exists():
                current_session = name
                msgs = load_session(name)
                print(f"  Switched to '{name}' ({len(msgs)} messages)")
            else:
                print(f"  Session '{name}' not found. Use /new to create it.")

        elif user_input == "/list":
            sessions = list_sessions()
            if sessions:
                for s in sessions:
                    marker = " <—" if s == current_session else ""
                    msgs = load_session(s)
                    print(f"  {s} ({len(msgs)} messages){marker}")
            else:
                print("  No sessions yet. Use /new <name> to create one.")

        elif user_input.startswith("/delete "):
            name = user_input[8:].strip()
            if delete_session(name):
                print(f"  Deleted session '{name}'")
                if current_session == name:
                    current_session = None
            else:
                print(f"  Session '{name}' not found.")

        elif user_input == "/quit":
            break

        elif user_input.startswith("/"):
            print("  Unknown command. Type /list, /new, /switch, /delete, or /quit.")

        else:
            if not current_session:
                print("  No active session. Use /new <name> first.")
                continue
            reply = chat(current_session, user_input)
            print(f"\n  Claude: {reply}\n")


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Named sessions POC — organize multi-workstream conversations"
    )
    parser.add_argument(
        "--demo", action="store_true",
        help="Run the scripted demo instead of interactive mode.",
    )
    args = parser.parse_args()

    if args.demo:
        run_demo()
    else:
        run_interactive()


if __name__ == "__main__":
    main()
