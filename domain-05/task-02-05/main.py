"""
POC: Partial Results + What Was Attempted
─────────────────────────────────────────
Demonstrates the resilience pattern where a multi-step pipeline:
  1. Collects results from each step as it completes
  2. On failure, returns ALL partial results gathered so far
  3. Always reports what was attempted, what succeeded, and what failed

Silently swallowing failures or returning empty results on error
makes debugging impossible and wastes the work already completed.
"""

import os
import json
from dataclasses import dataclass, field
from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()

client = Anthropic()


@dataclass
class StepOutcome:
    """One step's result — success or failure, always captured."""
    name: str
    status: str  # "success" | "failed" | "skipped"
    result: str | None = None
    error: str | None = None


@dataclass
class PipelineReport:
    """
    Accumulates outcomes across steps so nothing is lost.
    Even a fully failed pipeline returns this — never None, never empty.
    """
    task: str
    steps: list[StepOutcome] = field(default_factory=list)

    def add(self, outcome: StepOutcome):
        self.steps.append(outcome)

    @property
    def succeeded(self) -> list[StepOutcome]:
        return [s for s in self.steps if s.status == "success"]

    @property
    def failed(self) -> list[StepOutcome]:
        return [s for s in self.steps if s.status == "failed"]

    @property
    def overall_success(self) -> bool:
        # Pipeline succeeds only if zero steps failed
        return len(self.failed) == 0 and len(self.succeeded) > 0

    def summary(self) -> dict:
        """Structured summary — always returned regardless of outcome."""
        return {
            "task": self.task,
            "overall": "success" if self.overall_success else "partial_failure",
            "steps_attempted": len(self.steps),
            "steps_succeeded": len(self.succeeded),
            "steps_failed": len(self.failed),
            # Partial results are the key value: work done before failure is preserved
            "partial_results": {
                s.name: s.result for s in self.succeeded
            },
            "failures": {
                s.name: s.error for s in self.failed
            },
        }


def call_claude(prompt: str, max_tokens: int = 200) -> str:
    """Single Claude call — thin wrapper to keep step functions focused on logic."""
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text.strip()


def run_step(report: PipelineReport, step_name: str, prompt: str, *, sabotage: bool = False) -> StepOutcome:
    """
    Execute one step and record its outcome into the report.
    Catches exceptions so a single step failure never kills the pipeline.
    """
    print(f"  [{step_name}] running...")

    if sabotage:
        # Simulates a mid-pipeline failure (timeout, bad input, quota hit)
        outcome = StepOutcome(
            name=step_name,
            status="failed",
            error="simulated_failure: step deliberately sabotaged for demo",
        )
        report.add(outcome)
        print(f"  [{step_name}] FAILED (sabotaged)")
        return outcome

    try:
        result = call_claude(prompt)
        outcome = StepOutcome(name=step_name, status="success", result=result)
        report.add(outcome)
        print(f"  [{step_name}] SUCCESS")
        return outcome

    except Exception as e:
        # Capture the failure but keep the pipeline running —
        # subsequent steps may still produce useful partial results
        outcome = StepOutcome(
            name=step_name,
            status="failed",
            error=f"{type(e).__name__}: {e}",
        )
        report.add(outcome)
        print(f"  [{step_name}] FAILED ({type(e).__name__})")
        return outcome


def research_pipeline(topic: str, sabotage_step: str | None = None) -> PipelineReport:
    """
    Multi-step research pipeline. Each step adds to the report.
    If any step fails, the report still contains everything that succeeded.
    """
    report = PipelineReport(task=f"Research: {topic}")

    steps = [
        ("define", f"Define '{topic}' in exactly one sentence."),
        ("history", f"State the single most important historical milestone for '{topic}' in one sentence."),
        ("application", f"Name one real-world application of '{topic}' in one sentence."),
        ("future", f"Predict one future development for '{topic}' in one sentence."),
    ]

    for step_name, prompt in steps:
        # sabotage_step lets us inject failure at any point in the pipeline
        should_sabotage = (step_name == sabotage_step)
        run_step(report, step_name, prompt, sabotage=should_sabotage)

    return report


def print_report(report: PipelineReport):
    """Display the full report — partial results are always visible."""
    summary = report.summary()

    print(f"\n  {'─' * 50}")
    print(f"  PIPELINE REPORT")
    print(f"  {'─' * 50}")
    print(f"  Task:            {summary['task']}")
    print(f"  Overall:         {summary['overall']}")
    print(f"  Steps attempted: {summary['steps_attempted']}")
    print(f"  Steps succeeded: {summary['steps_succeeded']}")
    print(f"  Steps failed:    {summary['steps_failed']}")

    if summary["partial_results"]:
        print(f"\n  PARTIAL RESULTS (usable even though pipeline {'succeeded' if report.overall_success else 'failed'}):")
        for name, result in summary["partial_results"].items():
            print(f"    [{name}] {result[:90]}")

    if summary["failures"]:
        print(f"\n  FAILURES (what went wrong and where):")
        for name, error in summary["failures"].items():
            print(f"    [{name}] {error}")

    print(f"  {'─' * 50}")


def run_scenario(label: str, topic: str, sabotage_step: str | None = None):
    """Run one pipeline scenario and display results."""
    print(f"\n{'#' * 55}")
    print(f"SCENARIO: {label}")
    print(f"{'#' * 55}\n")

    report = research_pipeline(topic, sabotage_step=sabotage_step)
    print_report(report)
    return report


if __name__ == "__main__":
    print("=" * 55)
    print("PARTIAL RESULTS + WHAT WAS ATTEMPTED")
    print("Always report progress — even on failure")
    print("=" * 55)

    # Scenario 1: All steps succeed — baseline happy path
    run_scenario(
        label="All steps succeed (baseline)",
        topic="machine learning",
    )

    # Scenario 2: Middle step fails — steps before AND after still produce results
    # This is the core insight: step 1 and steps 3-4 are not wasted
    run_scenario(
        label="Mid-pipeline failure (partial results preserved)",
        topic="machine learning",
        sabotage_step="history",
    )

    # Scenario 3: First step fails — even total early failure reports what was attempted
    run_scenario(
        label="First step fails (still reports attempts)",
        topic="machine learning",
        sabotage_step="define",
    )

    print(f"\n{'=' * 55}")
    print("KEY TAKEAWAY:")
    print("  Never return None or raise on pipeline failure")
    print("  Always return: what succeeded + what failed + what was attempted")
    print("  Partial results are valuable — don't throw them away")
    print(f"{'=' * 55}")
