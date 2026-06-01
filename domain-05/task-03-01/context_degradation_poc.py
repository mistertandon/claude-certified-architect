"""
POC: Context Degradation in Extended Sessions
==============================================
Demonstrates how response quality degrades as conversation context fills up.

Strategy:
  1. Plant a specific "seed fact" early in the conversation.
  2. Progressively stuff the context with filler messages.
  3. Periodically ask the model to recall the seed fact.
  4. Measure recall accuracy + latency at each checkpoint.

When the seed fact gets pushed far back in context, the model struggles
to retrieve it — this IS context degradation.
"""

import os
import time
import json
from datetime import datetime

from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

client = Anthropic()

MODEL = os.getenv("MODEL_NAME", "claude-sonnet-4-20250514")

# Deliberately obscure fact so the model can't rely on training data
SEED_FACT = "The secret project codename is GOLDEN-PARROT-7742."

# Filler that is topically unrelated so it competes for attention
FILLER_TOPIC = (
    "Explain one interesting fact about the history of "
    "cartography in the {era} era. Keep it under 80 words."
)

ERAS = [
    "ancient Egyptian", "Roman", "medieval European", "Song Dynasty Chinese",
    "Ottoman", "Renaissance Italian", "colonial Spanish", "Enlightenment French",
    "Victorian British", "early American", "Meiji Japanese", "Soviet",
    "post-WWII", "Cold War", "digital age", "modern satellite",
    "deep-sea mapping", "Arctic exploration", "Polynesian navigation",
    "Aboriginal Australian", "Inuit", "Phoenician", "Greek classical",
    "Mughal Indian", "Ming Dynasty", "Portuguese Age of Discovery",
    "Dutch Golden Age", "Napoleonic", "Antarctic expedition", "space-age",
]

# How many filler rounds between each recall test
FILLER_ROUNDS_PER_CHECK = 5

# Total recall checkpoints to run
NUM_CHECKPOINTS = 6

RECALL_QUESTION = (
    "What is the exact secret project codename I told you at the start? "
    "Reply with ONLY the codename, nothing else."
)


def run_degradation_test():
    """Drive the multi-turn conversation and collect degradation metrics."""

    # conversation_history accumulates every message — this is the mechanism
    # that causes context to fill up, mirroring real extended sessions
    conversation_history = []

    results = []

    # -- Step 1: Plant the seed fact ------------------------------------------
    conversation_history.append({
        "role": "user",
        "content": (
            f"Remember this exactly: {SEED_FACT} "
            "I will ask you to recall it later."
        ),
    })

    seed_response = client.messages.create(
        model=MODEL,
        max_tokens=128,
        # system prompt kept minimal so it doesn't help with recall
        system="You are a helpful assistant.",
        messages=conversation_history,
    )

    conversation_history.append({
        "role": "assistant",
        "content": seed_response.content[0].text,
    })

    print(f"[Seed planted] Tokens used so far: {seed_response.usage.input_tokens}")
    print(f"  Model acknowledged: {seed_response.content[0].text[:80]}...")
    print("-" * 72)

    # -- Step 2: Stuff context + periodic recall checks -----------------------
    era_idx = 0

    for checkpoint in range(1, NUM_CHECKPOINTS + 1):

        # --- Filler rounds: push the seed fact further from attention ---
        for _ in range(FILLER_ROUNDS_PER_CHECK):
            era = ERAS[era_idx % len(ERAS)]
            era_idx += 1

            conversation_history.append({
                "role": "user",
                "content": FILLER_TOPIC.format(era=era),
            })

            filler_resp = client.messages.create(
                model=MODEL,
                max_tokens=200,
                system="You are a helpful assistant.",
                messages=conversation_history,
            )

            conversation_history.append({
                "role": "assistant",
                "content": filler_resp.content[0].text,
            })

        # --- Recall probe: can the model still retrieve the seed fact? ---
        conversation_history.append({
            "role": "user",
            "content": RECALL_QUESTION,
        })

        t0 = time.time()
        recall_resp = client.messages.create(
            model=MODEL,
            max_tokens=100,
            system="You are a helpful assistant.",
            messages=conversation_history,
        )
        latency = time.time() - t0

        recall_text = recall_resp.content[0].text.strip()

        conversation_history.append({
            "role": "assistant",
            "content": recall_text,
        })

        # Exact-match check: strict because we asked for ONLY the codename
        exact_match = "GOLDEN-PARROT-7742" in recall_text
        # Partial check: model remembers fragments but not the full codename
        partial_match = (
            ("GOLDEN" in recall_text or "PARROT" in recall_text or "7742" in recall_text)
            and not exact_match
        )

        input_tokens = recall_resp.usage.input_tokens
        total_messages = len(conversation_history)

        result = {
            "checkpoint": checkpoint,
            "filler_rounds_so_far": checkpoint * FILLER_ROUNDS_PER_CHECK,
            "total_messages": total_messages,
            "input_tokens": input_tokens,
            "recall_text": recall_text,
            "exact_match": exact_match,
            "partial_match": partial_match,
            "latency_sec": round(latency, 2),
        }
        results.append(result)

        status = (
            "EXACT" if exact_match
            else "PARTIAL" if partial_match
            else "FAILED"
        )
        print(
            f"[Checkpoint {checkpoint}] "
            f"msgs={total_messages:>3}  "
            f"input_tokens={input_tokens:>6}  "
            f"recall={status:<8} "
            f"latency={latency:.2f}s"
        )
        print(f"  Model said: {recall_text[:100]}")
        print("-" * 72)

    return results


def print_summary(results):
    """Print a human-readable degradation summary."""

    print("\n" + "=" * 72)
    print("CONTEXT DEGRADATION SUMMARY")
    print("=" * 72)
    print(
        f"{'CP':>3} | {'Filler':>6} | {'Msgs':>4} | {'Tokens':>7} | "
        f"{'Recall':>8} | {'Latency':>8}"
    )
    print("-" * 72)

    for r in results:
        status = (
            "EXACT" if r["exact_match"]
            else "PARTIAL" if r["partial_match"]
            else "FAILED"
        )
        print(
            f"{r['checkpoint']:>3} | "
            f"{r['filler_rounds_so_far']:>6} | "
            f"{r['total_messages']:>4} | "
            f"{r['input_tokens']:>7} | "
            f"{status:>8} | "
            f"{r['latency_sec']:>7.2f}s"
        )

    # Degradation verdict
    exact_count = sum(1 for r in results if r["exact_match"])
    total = len(results)
    first_fail = next(
        (r["checkpoint"] for r in results if not r["exact_match"]), None
    )

    print("-" * 72)
    print(f"Exact recalls: {exact_count}/{total}")

    if first_fail:
        print(f"First degradation observed at checkpoint {first_fail}")
    else:
        print("No degradation observed (try increasing FILLER_ROUNDS_PER_CHECK)")

    # Latency trend
    if len(results) >= 2:
        first_latency = results[0]["latency_sec"]
        last_latency = results[-1]["latency_sec"]
        pct_change = ((last_latency - first_latency) / first_latency) * 100
        print(
            f"Latency trend: {first_latency:.2f}s -> {last_latency:.2f}s "
            f"({pct_change:+.1f}%)"
        )

    print("=" * 72)


def save_results(results):
    """Persist raw results for later analysis."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"degradation_results_{timestamp}.json"
    filepath = os.path.join(os.path.dirname(__file__), filename)

    with open(filepath, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\nResults saved to {filepath}")


if __name__ == "__main__":
    print("Context Degradation POC")
    print(f"Model: {MODEL}")
    print(f"Seed fact: {SEED_FACT}")
    print(f"Filler rounds per checkpoint: {FILLER_ROUNDS_PER_CHECK}")
    print(f"Total checkpoints: {NUM_CHECKPOINTS}")
    print("=" * 72)

    results = run_degradation_test()
    print_summary(results)
    save_results(results)
