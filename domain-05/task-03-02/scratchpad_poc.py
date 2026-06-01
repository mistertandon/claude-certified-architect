"""
POC: Scratchpad Files — Persisting State Across Context Resets
==============================================================
Demonstrates how external "scratchpad" files let an agent survive context
compaction / window resets without losing critical state.

Scenario (3-city travel planner):
  Phase 1 — Agent researches city 1, writes findings to scratchpad, context resets.
  Phase 2 — Agent reads scratchpad, researches city 2, appends findings, context resets.
  Phase 3 — Agent reads scratchpad, researches city 3, produces final plan.

  Contrast run: same task with NO scratchpad — after each reset the agent
  starts blind and the final plan is incomplete.

The scratchpad acts as durable external memory that outlives any single
context window, which is the core exam concept.
"""

import os
import json
from datetime import datetime

from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

client = Anthropic()

MODEL = os.getenv("MODEL_NAME", "claude-sonnet-4-20250514")
SCRATCHPAD_PATH = os.getenv("SCRATCHPAD_PATH", "scratchpad.json")

CITIES = ["Tokyo", "Lisbon", "Cape Town"]

# ── system prompt instructs the agent HOW to use the scratchpad ──────────
SYSTEM_WITH_SCRATCHPAD = """\
You are a travel-planning assistant.

SCRATCHPAD RULES (critical):
- Before answering, ALWAYS read the scratchpad to recover prior state.
- After completing research for a city, ALWAYS update the scratchpad with
  your findings in this JSON format:
  {"cities_done": ["CityName"], "findings": {"CityName": "..."}}
- The scratchpad is your ONLY memory across sessions — treat it as ground truth.

Respond with ONLY valid JSON when asked to write scratchpad content.
When asked to produce a final plan, output a readable travel plan (not JSON).
"""

SYSTEM_WITHOUT_SCRATCHPAD = """\
You are a travel-planning assistant.
When asked to produce a final plan, output a readable travel plan.
"""


def read_scratchpad() -> dict:
    """Load scratchpad from disk; return empty state if missing."""
    if os.path.exists(SCRATCHPAD_PATH):
        with open(SCRATCHPAD_PATH, "r") as f:
            return json.load(f)
    # First run — no prior state exists yet
    return {"cities_done": [], "findings": {}}


def write_scratchpad(state: dict) -> None:
    with open(SCRATCHPAD_PATH, "w") as f:
        json.dump(state, f, indent=2)


def call_model(system: str, messages: list[dict]) -> str:
    resp = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=system,
        messages=messages,
    )
    return resp.content[0].text


# ── Phase runner — each phase simulates a FRESH context window ───────────
def run_phase_with_scratchpad(city: str, phase_num: int) -> str:
    """Each call starts a brand-new conversation (empty messages list)
    to simulate a context reset.  The scratchpad bridges the gap."""

    prior_state = read_scratchpad()

    # Inject scratchpad content so the model knows what happened before this window
    scratchpad_context = json.dumps(prior_state, indent=2)

    research_prompt = (
        f"Current scratchpad state:\n```json\n{scratchpad_context}\n```\n\n"
        f"Research the top 2 must-see attractions and 1 local food recommendation "
        f"for {city}.  Then output ONLY the updated scratchpad JSON "
        f"(merge your new findings with the existing ones)."
    )

    # Fresh conversation — no prior turns carried over
    messages = [{"role": "user", "content": research_prompt}]

    raw = call_model(SYSTEM_WITH_SCRATCHPAD, messages)

    # Persist the model's updated state to disk so the NEXT phase can read it
    try:
        updated = json.loads(raw.strip().strip("```json").strip("```"))
        write_scratchpad(updated)
    except json.JSONDecodeError:
        print(f"  [warn] Phase {phase_num} returned non-JSON, saving raw text")
        prior_state["findings"][city] = raw
        prior_state["cities_done"].append(city)
        write_scratchpad(prior_state)

    return raw


def run_phase_without_scratchpad(city: str) -> str:
    """Same task but NO scratchpad — each phase is truly amnesic."""
    messages = [
        {
            "role": "user",
            "content": (
                f"Research the top 2 must-see attractions and 1 local food "
                f"recommendation for {city}. Be concise."
            ),
        }
    ]
    return call_model(SYSTEM_WITHOUT_SCRATCHPAD, messages)


def generate_final_plan(use_scratchpad: bool) -> str:
    if use_scratchpad:
        state = read_scratchpad()
        prompt = (
            f"Scratchpad state:\n```json\n{json.dumps(state, indent=2)}\n```\n\n"
            f"Using ALL the research above, write a cohesive 3-city travel plan "
            f"covering {', '.join(CITIES)}."
        )
        return call_model(SYSTEM_WITH_SCRATCHPAD, [{"role": "user", "content": prompt}])
    else:
        # Without scratchpad the model has ZERO prior context — it must guess
        prompt = (
            f"Write a 3-city travel plan for {', '.join(CITIES)}. "
            f"Include top attractions and food for each city."
        )
        return call_model(SYSTEM_WITHOUT_SCRATCHPAD, [{"role": "user", "content": prompt}])


def main():
    # ── Run WITH scratchpad ──────────────────────────────────────────────
    print("=" * 64)
    print("RUN 1: WITH SCRATCHPAD (state persists across resets)")
    print("=" * 64)

    # Clean slate
    if os.path.exists(SCRATCHPAD_PATH):
        os.remove(SCRATCHPAD_PATH)

    for i, city in enumerate(CITIES, 1):
        print(f"\n--- Phase {i}: Researching {city} (fresh context window) ---")
        raw = run_phase_with_scratchpad(city, i)
        state = read_scratchpad()
        print(f"  Cities accumulated in scratchpad: {state.get('cities_done', [])}")

    print(f"\n--- Final Plan (informed by scratchpad) ---")
    plan_with = generate_final_plan(use_scratchpad=True)
    print(plan_with)

    # ── Run WITHOUT scratchpad ───────────────────────────────────────────
    print("\n" + "=" * 64)
    print("RUN 2: WITHOUT SCRATCHPAD (no persistence across resets)")
    print("=" * 64)

    for i, city in enumerate(CITIES, 1):
        print(f"\n--- Phase {i}: Researching {city} (fresh context, no memory) ---")
        raw = run_phase_without_scratchpad(city)
        # Results vanish — nothing is saved
        print(f"  (research done but NOT persisted anywhere)")

    print(f"\n--- Final Plan (no prior research available) ---")
    plan_without = generate_final_plan(use_scratchpad=False)
    print(plan_without)

    # ── Comparison ───────────────────────────────────────────────────────
    print("\n" + "=" * 64)
    print("COMPARISON")
    print("=" * 64)
    print(f"  WITH scratchpad    — plan length: {len(plan_with):>5} chars "
          f"(uses accumulated research)")
    print(f"  WITHOUT scratchpad — plan length: {len(plan_without):>5} chars "
          f"(generic, no prior context)")
    print()
    print("Key insight: The scratchpad-backed plan references SPECIFIC findings")
    print("from each phase, while the no-scratchpad plan relies on generic training")
    print("knowledge because all per-phase research was lost at each context reset.")

    # ── Save results ─────────────────────────────────────────────────────
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    results = {
        "plan_with_scratchpad": plan_with,
        "plan_without_scratchpad": plan_without,
        "scratchpad_final_state": read_scratchpad(),
    }
    out_file = f"scratchpad_results_{ts}.json"
    with open(out_file, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to {out_file}")


if __name__ == "__main__":
    main()
