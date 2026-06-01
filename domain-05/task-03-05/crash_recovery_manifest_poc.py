"""
POC: Crash Recovery Manifests — Persistent State for Session Recovery
=====================================================================
Demonstrates the core exam concept: an agentic loop writes a manifest file
to disk BEFORE each step, capturing enough state to resume if the process
crashes mid-execution.

Scenario (multi-step research agent):
  1. Agent receives a multi-step research plan (analyze N topics).
  2. BEFORE each API call, it writes a manifest to disk recording:
     - conversation history so far
     - which step it's about to attempt
     - partial results already collected
  3. If the process crashes, the next run detects the manifest, skips
     completed steps, and resumes from the last incomplete one.

Why this matters:
  - Long-running agentic loops are vulnerable to crashes (network, OOM, timeout).
  - Without persistence, a crash at step 8/10 loses ALL prior work.
  - Manifests turn a catastrophic failure into a resumable checkpoint.
  - Write-ahead (persist BEFORE the call) ensures no ambiguous half-states.
"""

import os
import json
import time
import signal
import sys
from datetime import datetime, timezone

from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

client = Anthropic()

MODEL = os.getenv("MODEL_NAME", "claude-sonnet-4-20250514")

# Manifest lives alongside the script so it survives process restarts
MANIFEST_PATH = os.getenv(
    "MANIFEST_PATH",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "recovery_manifest.json"),
)

# ── Research topics — the multi-step workload ──────────────────────────

RESEARCH_TOPICS = [
    "Explain how prompt caching reduces latency in multi-turn conversations",
    "Describe the role of stop_reason in controlling an agentic loop",
    "How does token budgeting prevent context window overflow",
    "What are the tradeoffs of extended thinking for complex reasoning tasks",
    "Explain why system prompts should be static for cache efficiency",
]


# ── Manifest operations ───────────────────────────────────────────────

def create_fresh_manifest() -> dict:
    """Initialize a new manifest with no progress."""
    return {
        "session_id": datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S"),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        # "pending" → "in_progress" → "completed" lifecycle
        "status": "pending",
        # Index of the step ABOUT TO be attempted (not yet completed)
        "current_step": 0,
        "total_steps": len(RESEARCH_TOPICS),
        # Accumulates results as steps complete — survives crashes
        "completed_results": [],
        # Full conversation history for the coordinator
        "conversation_history": [],
        # Tracks each step's lifecycle for auditability
        "step_log": [],
    }


def write_manifest(manifest: dict) -> None:
    """Atomically persist the manifest to disk.

    Write-to-temp-then-rename prevents partial writes from corrupting
    the manifest if the process is killed mid-write."""
    manifest["updated_at"] = datetime.now(timezone.utc).isoformat()
    tmp_path = MANIFEST_PATH + ".tmp"
    with open(tmp_path, "w") as f:
        json.dump(manifest, f, indent=2)
    # Atomic rename — OS guarantees this won't produce a half-written file
    os.replace(tmp_path, MANIFEST_PATH)


def load_manifest() -> dict | None:
    """Load an existing manifest if one exists from a prior crash."""
    if not os.path.exists(MANIFEST_PATH):
        return None
    with open(MANIFEST_PATH, "r") as f:
        return json.load(f)


def clear_manifest() -> None:
    """Remove the manifest after successful completion — no recovery needed."""
    if os.path.exists(MANIFEST_PATH):
        os.remove(MANIFEST_PATH)
    tmp = MANIFEST_PATH + ".tmp"
    if os.path.exists(tmp):
        os.remove(tmp)


# ── Simulated crash mechanism ─────────────────────────────────────────

# Which step to crash on (0-indexed); None = no crash
CRASH_AT_STEP = int(os.getenv("CRASH_AT_STEP", "-1"))


def maybe_crash(step: int) -> None:
    """Simulate a process crash at a specific step for demonstration.

    In production, crashes come from network errors, OOM kills, or timeouts.
    This simulates that by raising a hard exit."""
    if step == CRASH_AT_STEP:
        print(f"\n  ** SIMULATED CRASH at step {step}! **")
        print(f"  ** Process dying — manifest on disk preserves state **\n")
        # os._exit bypasses cleanup — mimics a real crash (SIGKILL, OOM, etc.)
        os._exit(1)


# ── Agent loop with manifest checkpointing ────────────────────────────

def run_research_agent() -> dict:
    """Execute the multi-step research loop with crash recovery.

    On each iteration:
      1. Write manifest with status "in_progress" for current step (WRITE-AHEAD)
      2. Make the API call
      3. Write manifest with the result appended (COMMIT)
    If the process crashes between 1 and 3, the next run sees the
    in_progress step and re-attempts it — no work is duplicated or lost."""

    # ── Phase 1: Check for existing manifest (crash recovery) ──────
    manifest = load_manifest()

    if manifest and manifest["status"] != "completed":
        completed = len(manifest["completed_results"])
        print(f"  [RECOVERY] Found manifest from session {manifest['session_id']}")
        print(f"  [RECOVERY] {completed}/{manifest['total_steps']} steps completed")
        print(f"  [RECOVERY] Resuming from step {manifest['current_step']}\n")
    else:
        manifest = create_fresh_manifest()
        print(f"  [FRESH] Starting new session {manifest['session_id']}\n")
        write_manifest(manifest)

    # ── Phase 2: Execute steps, checkpointing after each ───────────
    start_step = manifest["current_step"]

    for step_idx in range(start_step, len(RESEARCH_TOPICS)):
        topic = RESEARCH_TOPICS[step_idx]
        print(f"  Step {step_idx + 1}/{len(RESEARCH_TOPICS)}: {topic[:60]}...")

        # ── WRITE-AHEAD: persist intent BEFORE the API call ────────
        # If we crash during the API call, next run knows which step
        # was in-flight and can re-attempt it safely
        manifest["current_step"] = step_idx
        manifest["status"] = "in_progress"
        manifest["step_log"].append({
            "step": step_idx,
            "topic": topic,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "status": "in_progress",
        })
        write_manifest(manifest)

        # ── Simulate crash BEFORE the API call completes ───────────
        maybe_crash(step_idx)

        # ── API call — the potentially-failing operation ───────────
        user_msg = {
            "role": "user",
            "content": (
                f"Research topic {step_idx + 1}/{len(RESEARCH_TOPICS)}: {topic}\n"
                f"Provide a concise 2-3 sentence explanation suitable for "
                f"an architecture exam study guide."
            ),
        }
        manifest["conversation_history"].append(user_msg)

        resp = client.messages.create(
            model=MODEL,
            max_tokens=512,
            system=(
                "You are a concise technical writer creating study notes for "
                "the Claude Architect exam. Keep each answer to 2-3 sentences."
            ),
            messages=manifest["conversation_history"],
        )

        assistant_msg = {"role": "assistant", "content": resp.content[0].text}
        manifest["conversation_history"].append(assistant_msg)

        # ── COMMIT: persist the completed result ───────────────────
        result = {
            "step": step_idx,
            "topic": topic,
            "response": resp.content[0].text,
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "input_tokens": resp.usage.input_tokens,
            "output_tokens": resp.usage.output_tokens,
        }
        manifest["completed_results"].append(result)
        # Advance pointer PAST the completed step so recovery skips it
        manifest["current_step"] = step_idx + 1
        manifest["step_log"][-1]["status"] = "completed"
        manifest["step_log"][-1]["completed_at"] = result["completed_at"]
        write_manifest(manifest)

        print(f"    -> Done ({resp.usage.input_tokens}+{resp.usage.output_tokens} tokens)")

    # ── Phase 3: Mark session complete ─────────────────────────────
    manifest["status"] = "completed"
    write_manifest(manifest)

    return manifest


# ── Display results ───────────────────────────────────────────────────

def display_results(manifest: dict) -> None:
    """Print the research results and manifest metadata."""
    print("\n" + "=" * 64)
    print("RESEARCH RESULTS")
    print("=" * 64)

    for result in manifest["completed_results"]:
        print(f"\n--- Topic {result['step'] + 1}: {result['topic']} ---")
        print(result["response"])

    print("\n" + "=" * 64)
    print("MANIFEST METADATA")
    print("=" * 64)
    print(f"  Session ID:    {manifest['session_id']}")
    print(f"  Created:       {manifest['created_at']}")
    print(f"  Last updated:  {manifest['updated_at']}")
    print(f"  Status:        {manifest['status']}")
    print(f"  Steps:         {len(manifest['completed_results'])}/{manifest['total_steps']}")

    total_input = sum(r.get("input_tokens", 0) for r in manifest["completed_results"])
    total_output = sum(r.get("output_tokens", 0) for r in manifest["completed_results"])
    print(f"  Total tokens:  {total_input} input + {total_output} output")

    # Show step lifecycle timeline
    print("\n  Step log:")
    for entry in manifest["step_log"]:
        status_icon = "+" if entry["status"] == "completed" else "~"
        print(f"    [{status_icon}] Step {entry['step']}: {entry['status']}")


# ── Main ──────────────────────────────────────────────────────────────

def main():
    print("=" * 64)
    print("CRASH RECOVERY MANIFEST — Multi-Step Research Agent")
    print("=" * 64)
    print(f"  Manifest path: {MANIFEST_PATH}")
    print(f"  Crash at step: {'None (clean run)' if CRASH_AT_STEP < 0 else CRASH_AT_STEP}")
    print()

    manifest = run_research_agent()
    display_results(manifest)

    # Clean up manifest — session completed successfully
    clear_manifest()

    print("\n" + "=" * 64)
    print("SESSION COMPLETE — manifest cleared (no recovery needed)")
    print("=" * 64)

    print("\n  Exam-relevant takeaways:")
    print("  1. WRITE-AHEAD: persist state BEFORE the risky operation")
    print("  2. ATOMIC WRITES: temp-file + rename prevents corrupt manifests")
    print("  3. IDEMPOTENT RESUME: re-running a step produces the same effect")
    print("  4. STEP POINTER: current_step tracks what to attempt next, not what succeeded")
    print("  5. CLEANUP: remove manifest on success so stale state doesn't confuse future runs")


if __name__ == "__main__":
    main()
