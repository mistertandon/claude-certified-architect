"""
POC: Fork Session — Branched Sessions for Parallel Exploration

Demonstrates how a single conversation can be forked into independent
branches that explore different directions in parallel, without any
branch polluting another's context.
"""

import asyncio
import copy
import os
import time

from anthropic import AsyncAnthropic
from dotenv import load_dotenv

load_dotenv()

client = AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

MODEL = "claude-sonnet-4-6-20250514"

# Shared base conversation — the "trunk" all forks branch from
BASE_MESSAGES = [
    {
        "role": "user",
        "content": "We need to build a rate limiter for our API. What approaches exist?",
    },
    {
        "role": "assistant",
        "content": (
            "Common approaches: (1) Token Bucket, (2) Sliding Window Log, "
            "(3) Fixed Window Counter. Each has different trade-offs around "
            "burst tolerance, memory usage, and precision."
        ),
    },
]

# Each fork explores ONE direction from the shared trunk — no cross-talk
FORK_PROMPTS = {
    "token_bucket_deep_dive": (
        "Let's explore Token Bucket in detail. "
        "Give a minimal Python implementation in under 15 lines."
    ),
    "sliding_window_deep_dive": (
        "Let's explore Sliding Window Log in detail. "
        "Give a minimal Python implementation in under 15 lines."
    ),
    "tradeoff_analysis": (
        "Compare Token Bucket vs Sliding Window Log. "
        "Which is better for bursty traffic? Answer in 2 sentences."
    ),
}


async def run_fork(fork_name: str, fork_prompt: str) -> dict:
    """Run one forked session branch independently."""

    # deep-copy prevents any fork from mutating the shared base
    forked_messages = copy.deepcopy(BASE_MESSAGES)

    # append the fork-specific follow-up — this is where branches diverge
    forked_messages.append({"role": "user", "content": fork_prompt})

    response = await client.messages.create(
        model=MODEL,
        max_tokens=400,
        # system prompt reinforces isolation — each fork thinks it's the only path
        system=f"You are exploring the '{fork_name}' branch of a design discussion. Be concise.",
        messages=forked_messages,
    )

    return {
        "fork": fork_name,
        # message count proves each fork carries the shared trunk + its own addition
        "context_depth": len(forked_messages),
        "result": response.content[0].text,
    }


async def run_forked_exploration():
    """
    Core pattern: fork a shared conversation into parallel branches.

    Each branch gets a deep copy of the base context plus its own
    divergent prompt. asyncio.gather fires all forks concurrently —
    mirroring how Claude Code's fork_session creates branched contexts
    without cross-polluting the parent or sibling sessions.
    """
    start = time.perf_counter()

    # all forks launch from the same snapshot — no ordering dependency
    results = await asyncio.gather(
        *[run_fork(name, prompt) for name, prompt in FORK_PROMPTS.items()]
    )

    elapsed = time.perf_counter() - start

    print(f"\n{'=' * 64}")
    print(f"  Fork Session Complete — {len(results)} branches, {elapsed:.2f}s wall time")
    print(f"{'=' * 64}")

    print(f"\n  Shared Trunk ({len(BASE_MESSAGES)} messages):")
    for msg in BASE_MESSAGES:
        preview = msg["content"][:70] + "..." if len(msg["content"]) > 70 else msg["content"]
        print(f"    [{msg['role']}] {preview}")

    print(f"\n{'─' * 64}")

    for r in results:
        print(f"\n  Fork: {r['fork']} (context depth: {r['context_depth']} messages)")
        print(f"  {'─' * 40}")
        # each result is independent — no bleed-through from sibling forks
        for line in r["result"].split("\n"):
            print(f"    {line}")

    print(f"\n{'=' * 64}")
    print("  Key point: each fork saw the shared trunk but NOT sibling responses.")
    print(f"{'=' * 64}\n")


if __name__ == "__main__":
    asyncio.run(run_forked_exploration())
