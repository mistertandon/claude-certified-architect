"""
POC: Context Compaction — Compressing Conversation History to Reclaim Space
===========================================================================
Demonstrates how /compact works: summarize accumulated conversation history
into a condensed form, then continue from the summary instead of the full
transcript.  This reclaims context window space while preserving essential
knowledge.

Scenario (iterative code reviewer):
  Phase 1 — Build up a long multi-turn conversation (5 review rounds).
  Phase 2 — Compact the history into a single summary message.
  Phase 3 — Continue the conversation from the compacted state and verify
             the model still recalls key facts from before compaction.

  Contrast run: same task WITHOUT compaction — history keeps growing
  unboundedly, consuming more tokens every turn.

The compaction acts as a lossy-but-efficient compression of context,
which is the core exam concept.
"""

import os
import json
from datetime import datetime

from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

client = Anthropic()

MODEL = os.getenv("MODEL_NAME", "claude-sonnet-4-20250514")

SYSTEM_PROMPT = """\
You are a senior code reviewer. You review code snippets the user submits,
track issues found across rounds, and provide a cumulative summary when asked.
Always reference specific variable names and line numbers from earlier rounds.
"""

# Simulated code snippets — each round adds a new "file" for review
REVIEW_ROUNDS = [
    {
        "file": "auth.py",
        "code": (
            "def login(user, pwd):\n"
            "    query = f\"SELECT * FROM users WHERE name='{user}' AND pass='{pwd}'\"\n"
            "    return db.execute(query)\n"
        ),
    },
    {
        "file": "payments.py",
        "code": (
            "def charge(card_num, amount):\n"
            "    print(f'Charging {card_num} for ${amount}')\n"
            "    return stripe.charge(card=card_num, amount=amount)\n"
        ),
    },
    {
        "file": "upload.py",
        "code": (
            "def save_file(filename, data):\n"
            "    path = '/uploads/' + filename\n"
            "    open(path, 'wb').write(data)\n"
            "    return path\n"
        ),
    },
    {
        "file": "config.py",
        "code": (
            "API_KEY = 'sk-live-abc123def456'\n"
            "DB_URL = 'postgres://admin:password@prod-db:5432/app'\n"
            "DEBUG = True\n"
        ),
    },
    {
        "file": "session.py",
        "code": (
            "import pickle\n"
            "def load_session(data):\n"
            "    return pickle.loads(data)\n"
        ),
    },
]


def count_message_tokens(messages: list[dict]) -> int:
    """Approximate token count via character length.
    Real systems use client.messages.count_tokens() — we approximate here
    to avoid an extra API call per measurement."""
    total_chars = sum(len(m["content"]) for m in messages)
    # ~4 chars per token is a rough English approximation
    return total_chars // 4


def build_conversation(rounds: list[dict]) -> list[dict]:
    """Simulate a multi-turn review session, accumulating full history.
    Each round: user submits code -> assistant reviews it -> history grows."""

    messages = []

    for i, review_round in enumerate(rounds, 1):
        user_msg = (
            f"Round {i}: Please review this file `{review_round['file']}`:\n"
            f"```python\n{review_round['code']}```"
        )
        messages.append({"role": "user", "content": user_msg})

        # Model sees ALL prior messages — history grows every round
        resp = client.messages.create(
            model=MODEL,
            max_tokens=512,
            system=SYSTEM_PROMPT,
            messages=messages,
        )
        assistant_reply = resp.content[0].text
        messages.append({"role": "assistant", "content": assistant_reply})

        token_est = count_message_tokens(messages)
        print(f"  Round {i} ({review_round['file']}): "
              f"~{token_est} tokens in history | "
              f"{len(messages)} messages")

    return messages


def compact_history(messages: list[dict]) -> list[dict]:
    """Core compaction logic — mirrors what /compact does:
    ask the model to summarize the entire conversation into a dense recap,
    then replace the full history with that single summary."""

    # The compaction prompt tells the model to preserve actionable details
    # while discarding conversational filler — this is the key tradeoff
    compaction_request = (
        "Summarize our ENTIRE conversation so far into a dense, structured recap. "
        "Preserve: every file name, every specific vulnerability found, variable names, "
        "and line numbers. Drop: conversational pleasantries, repeated context, "
        "formatting boilerplate. This summary will REPLACE the full history, "
        "so nothing omitted can be recovered."
    )

    # Append the compaction request as a new user turn
    messages_for_summary = messages + [
        {"role": "user", "content": compaction_request}
    ]

    resp = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=messages_for_summary,
    )
    summary = resp.content[0].text

    # Replace the ENTIRE history with one user message containing the summary.
    # This is the compaction — we go from N messages down to 1.
    compacted = [
        {
            "role": "user",
            "content": (
                f"[COMPACTED CONTEXT — this replaces {len(messages)} prior messages]\n\n"
                f"{summary}"
            ),
        },
        # Need an assistant ack so the next user message is valid
        {
            "role": "assistant",
            "content": "Understood. I have the full context from our prior review session.",
        },
    ]

    return compacted


def verify_recall(messages: list[dict], label: str) -> str:
    """Ask the model to recall specific details from earlier rounds.
    This proves whether compaction preserved the important information."""

    recall_prompt = (
        "Based on our conversation, answer these specific questions:\n"
        "1. What SQL vulnerability did you find and in which file?\n"
        "2. What sensitive data was logged in payments.py?\n"
        "3. What deserialization risk exists in session.py?\n"
        "4. How many total files did we review?\n"
        "Be specific — cite variable names and file names."
    )

    messages_with_query = messages + [
        {"role": "user", "content": recall_prompt}
    ]

    resp = client.messages.create(
        model=MODEL,
        max_tokens=512,
        system=SYSTEM_PROMPT,
        messages=messages_with_query,
    )
    return resp.content[0].text


def main():
    # ── Phase 1: Build up conversation history ──────────────────────────
    print("=" * 64)
    print("PHASE 1: Building conversation history (5 review rounds)")
    print("=" * 64)

    full_messages = build_conversation(REVIEW_ROUNDS)
    full_token_count = count_message_tokens(full_messages)

    print(f"\nFull history: {len(full_messages)} messages, ~{full_token_count} tokens")

    # ── Phase 2: Compact the history ────────────────────────────────────
    print("\n" + "=" * 64)
    print("PHASE 2: Compacting conversation history")
    print("=" * 64)

    compacted_messages = compact_history(full_messages)
    compacted_token_count = count_message_tokens(compacted_messages)

    savings_pct = (1 - compacted_token_count / full_token_count) * 100
    print(f"Compacted: {len(compacted_messages)} messages, ~{compacted_token_count} tokens")
    print(f"Savings:   ~{savings_pct:.0f}% token reduction "
          f"({full_token_count} -> {compacted_token_count})")

    # ── Phase 3: Verify recall ──────────────────────────────────────────
    print("\n" + "=" * 64)
    print("PHASE 3: Verifying recall after compaction")
    print("=" * 64)

    print("\n--- Recall from FULL history ---")
    recall_full = verify_recall(full_messages, "full")
    print(recall_full)

    print("\n--- Recall from COMPACTED history ---")
    recall_compacted = verify_recall(compacted_messages, "compacted")
    print(recall_compacted)

    # ── Phase 4: Continue from compacted state ──────────────────────────
    print("\n" + "=" * 64)
    print("PHASE 4: Continuing conversation from compacted state")
    print("=" * 64)

    # Prove the compacted conversation is a valid continuation point
    continuation_prompt = (
        "Given all the vulnerabilities found, rank them by severity "
        "(critical / high / medium) and suggest a remediation order. "
        "Reference the specific files."
    )
    continuation_messages = compacted_messages + [
        {"role": "user", "content": continuation_prompt}
    ]

    resp = client.messages.create(
        model=MODEL,
        max_tokens=512,
        system=SYSTEM_PROMPT,
        messages=continuation_messages,
    )
    print(f"\nContinuation response (from {len(compacted_messages)} msgs, not {len(full_messages)}):")
    print(resp.content[0].text)

    final_tokens = count_message_tokens(continuation_messages)
    hypothetical_tokens = count_message_tokens(full_messages) + len(continuation_prompt) // 4
    print(f"\nTokens used for continuation:  ~{final_tokens}")
    print(f"Tokens WITHOUT compaction:     ~{hypothetical_tokens}")
    print(f"Context space reclaimed:       ~{hypothetical_tokens - final_tokens} tokens")

    # ── Comparison summary ──────────────────────────────────────────────
    print("\n" + "=" * 64)
    print("COMPARISON SUMMARY")
    print("=" * 64)
    print(f"  Full history:     {len(full_messages):>3} messages | ~{full_token_count:>5} tokens")
    print(f"  After compaction: {len(compacted_messages):>3} messages | ~{compacted_token_count:>5} tokens")
    print(f"  Token savings:    ~{savings_pct:.0f}%")
    print()
    print("Key insight: Compaction is LOSSY — conversational nuance is discarded,")
    print("but structured facts (file names, vulnerabilities, variable names) survive.")
    print("This mirrors /compact in Claude Code: trade detail for runway.")

    # ── Save results ────────────────────────────────────────────────────
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    results = {
        "full_history_messages": len(full_messages),
        "full_history_tokens_approx": full_token_count,
        "compacted_messages": len(compacted_messages),
        "compacted_tokens_approx": compacted_token_count,
        "savings_pct": round(savings_pct, 1),
        "recall_full": recall_full,
        "recall_compacted": recall_compacted,
        "compacted_context": compacted_messages[0]["content"],
    }
    out_file = f"compact_results_{ts}.json"
    with open(out_file, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to {out_file}")


if __name__ == "__main__":
    main()
