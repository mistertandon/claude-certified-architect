"""
POC: Local Recovery Before Coordinator Escalation
──────────────────────────────────────────────────
Demonstrates the multi-agent pattern where a worker agent:
  1. Encounters a failure while processing a task
  2. Attempts local recovery (retry, simplify, fallback)
  3. Only escalates to the coordinator after local options are exhausted

Escalating every failure to a coordinator wastes tokens and adds latency.
Local-first recovery keeps the system fast and cost-efficient.
"""

import os
import json
from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()

client = Anthropic()

# Tracks what each agent attempted — makes the recovery chain auditable
recovery_log: list[str] = []


def log_step(agent: str, action: str, outcome: str):
    entry = f"[{agent}] {action} -> {outcome}"
    recovery_log.append(entry)
    print(f"  {entry}")


def worker_agent(task: str, poison: bool = False) -> dict:
    """
    Worker that processes a task with built-in local recovery.
    Returns structured result so coordinator knows exactly what was tried.
    """
    print(f"\n{'─' * 55}")
    print(f"WORKER received task: {task}")
    print(f"{'─' * 55}")

    # --- Attempt 1: Process normally ---
    attempt_1_input = task if not poison else task + " %%%CORRUPT_DATA%%% [[INVALID]]"
    result = _try_process(attempt_1_input, attempt=1)

    if result["success"]:
        return result

    # --- Local Recovery 1: Sanitize input and retry ---
    # Why sanitize before retry: bad input is the most common transient cause;
    # fixing it locally avoids a round-trip to the coordinator
    log_step("worker", "LOCAL RECOVERY 1", "sanitizing input and retrying")
    sanitized = _sanitize_input(attempt_1_input)
    result = _try_process(sanitized, attempt=2)

    if result["success"]:
        return result

    # --- Local Recovery 2: Simplify the request ---
    # Why simplify: if the task is too complex, breaking it down often succeeds
    # without needing coordinator intervention
    log_step("worker", "LOCAL RECOVERY 2", "simplifying request")
    result = _try_simplify(task)

    if result["success"]:
        return result

    # --- All local recovery exhausted → escalate ---
    # Why return structured failure: coordinator needs to know WHAT was tried
    # to avoid repeating the same failed strategies
    log_step("worker", "ESCALATING", "all local recovery exhausted")
    return {
        "success": False,
        "original_task": task,
        "attempts_made": 3,
        "strategies_tried": ["direct_process", "sanitize_retry", "simplify"],
        "last_error": result.get("error", "unknown"),
    }


def _try_process(text: str, attempt: int) -> dict:
    """Single processing attempt via Claude."""
    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=200,
            messages=[{
                "role": "user",
                "content": (
                    f"Summarize this in one sentence. "
                    f"If the input contains corrupted markers like %%%CORRUPT_DATA%%% "
                    f"or [[INVALID]], respond ONLY with: PROCESSING_ERROR\n\n{text}"
                ),
            }],
        )
        text_out = response.content[0].text.strip()

        if "PROCESSING_ERROR" in text_out:
            log_step("worker", f"attempt {attempt}", "FAILED (corrupt input detected)")
            return {"success": False, "error": "corrupt_input"}

        log_step("worker", f"attempt {attempt}", "SUCCESS")
        return {"success": True, "result": text_out, "recovered_locally": attempt > 1}

    except Exception as e:
        log_step("worker", f"attempt {attempt}", f"FAILED ({type(e).__name__})")
        return {"success": False, "error": str(e)}


def _sanitize_input(text: str) -> str:
    """Strip known corruption markers — cheapest local fix."""
    for marker in ["%%%CORRUPT_DATA%%%", "[[INVALID]]"]:
        text = text.replace(marker, "")
    return text.strip()


def _try_simplify(task: str) -> dict:
    """Ask Claude to extract just the core request — reduces complexity."""
    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=150,
            messages=[{
                "role": "user",
                "content": f"Extract the core question from this task in under 10 words: {task}",
            }],
        )
        simplified = response.content[0].text.strip()
        log_step("worker", "simplified to", f'"{simplified}"')
        return _try_process(simplified, attempt=3)

    except Exception as e:
        log_step("worker", "simplify", f"FAILED ({type(e).__name__})")
        return {"success": False, "error": str(e)}


def coordinator_agent(failure_report: dict) -> dict:
    """
    Coordinator only activates AFTER worker exhausted local recovery.
    Has broader context to pick an alternative strategy the worker cannot.
    """
    print(f"\n{'=' * 55}")
    print("COORDINATOR activated (worker escalated)")
    print(f"{'=' * 55}")

    log_step("coordinator", "received escalation", f"{failure_report['attempts_made']} worker attempts failed")

    # Why pass strategies_tried: coordinator must not repeat what already failed —
    # it needs to pick a genuinely different approach
    strategies_tried = failure_report.get("strategies_tried", [])
    original_task = failure_report["original_task"]

    print(f"  Strategies already tried by worker: {strategies_tried}")

    # Coordinator strategy: rephrase the task entirely
    # Why rephrase vs retry: worker already retried — same input won't help;
    # rephrasing changes the problem framing
    log_step("coordinator", "STRATEGY", "rephrasing task from scratch")

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=200,
            messages=[{
                "role": "user",
                "content": (
                    f"A worker agent failed to process this task after 3 attempts. "
                    f"Strategies tried: {strategies_tried}. "
                    f"Rephrase and answer this task yourself in one sentence:\n\n{original_task}"
                ),
            }],
        )
        result_text = response.content[0].text.strip()
        log_step("coordinator", "rephrase+solve", "SUCCESS")
        return {
            "success": True,
            "result": result_text,
            "resolved_by": "coordinator",
            "worker_attempts": failure_report["attempts_made"],
        }

    except Exception as e:
        log_step("coordinator", "rephrase+solve", f"FAILED ({type(e).__name__})")
        return {
            "success": False,
            "result": None,
            "resolved_by": None,
            "error": str(e),
            "total_attempts": failure_report["attempts_made"] + 1,
        }


def run_scenario(label: str, task: str, poison: bool = False):
    """Run one end-to-end scenario through the worker → coordinator pipeline."""
    global recovery_log
    recovery_log = []

    print(f"\n{'#' * 55}")
    print(f"SCENARIO: {label}")
    print(f"{'#' * 55}")

    # Worker tries first — coordinator stays idle unless needed
    result = worker_agent(task, poison=poison)

    if not result["success"]:
        # Only now does the coordinator get involved
        result = coordinator_agent(result)

    print(f"\n  FINAL OUTCOME: {'SUCCESS' if result['success'] else 'FAILURE'}")
    resolved_by = result.get("resolved_by", "worker")
    if result["success"]:
        print(f"  Resolved by: {resolved_by}")
        print(f"  Result: {result['result'][:100]}")

    print(f"\n  Recovery chain ({len(recovery_log)} steps):")
    for entry in recovery_log:
        print(f"    {entry}")

    return result


if __name__ == "__main__":
    print("=" * 55)
    print("LOCAL RECOVERY BEFORE COORDINATOR ESCALATION")
    print("=" * 55)

    # Scenario 1: Clean input — worker handles it on first try, coordinator never activates
    run_scenario(
        label="Clean input (no escalation needed)",
        task="Explain what photosynthesis is",
        poison=False,
    )

    # Scenario 2: Corrupted input — worker fails, recovers locally via sanitization
    run_scenario(
        label="Corrupt input (worker self-heals)",
        task="Explain what photosynthesis is",
        poison=True,
    )

    # Scenario 3: Forced escalation — simulate exhausted local recovery
    print(f"\n{'#' * 55}")
    print("SCENARIO: Forced escalation to coordinator")
    print(f"{'#' * 55}")

    # Directly invoke coordinator with a synthetic failure report
    # Why synthetic: demonstrates coordinator behavior in isolation
    forced_failure = {
        "success": False,
        "original_task": "Explain quantum entanglement in simple terms",
        "attempts_made": 3,
        "strategies_tried": ["direct_process", "sanitize_retry", "simplify"],
        "last_error": "all_strategies_exhausted",
    }
    coord_result = coordinator_agent(forced_failure)

    print(f"\n  FINAL OUTCOME: {'SUCCESS' if coord_result['success'] else 'FAILURE'}")
    if coord_result["success"]:
        print(f"  Result: {coord_result['result'][:100]}")

    print(f"\n{'=' * 55}")
    print("KEY TAKEAWAY:")
    print("  Worker handles transient failures locally (fast, cheap)")
    print("  Coordinator only activates when local recovery is exhausted")
    print("  Escalation carries WHAT was tried so coordinator doesn't repeat")
    print(f"{'=' * 55}")
