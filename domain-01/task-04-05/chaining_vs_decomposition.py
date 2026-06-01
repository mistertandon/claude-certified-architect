"""
POC: Prompt Chaining vs Dynamic Adaptive Decomposition — choose based on task predictability.

Prompt Chaining: a fixed sequence of LLM calls where each step's output feeds the next.
  Best for PREDICTABLE tasks with known steps (e.g., translate → summarize → format).

Dynamic Adaptive Decomposition: the LLM itself decides what subtasks to spawn at runtime.
  Best for UNPREDICTABLE tasks where the steps depend on intermediate results.

Key exam insight: chaining is cheaper/faster but brittle when the task shape varies;
decomposition is flexible but costs more tokens and adds latency.
"""

import json
import os

from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

client = Anthropic()
MODEL = "claude-sonnet-4-6"


# ──────────────────────────────────────────────────────────────────────
# APPROACH 1: PROMPT CHAINING (fixed pipeline, predictable tasks)
# ──────────────────────────────────────────────────────────────────────

def prompt_chain(topic: str) -> dict:
    """
    Fixed 3-step chain: Research → Outline → Draft.
    Steps are hardcoded because content-writing always follows this shape.
    """

    # Step 1 — each step is isolated so earlier hallucinations don't compound.
    research = _call(
        f"List 3 key facts about: {topic}. Return ONLY a JSON array of strings.",
        "You are a research assistant. Return valid JSON only."
    )

    # Step 2 — output of step 1 becomes input to step 2; this is the "chain".
    outline = _call(
        f"Given these facts:\n{research}\n\nCreate a 3-section blog outline. "
        "Return JSON: {{\"sections\": [{{\"title\": str, \"key_point\": str}}]}}",
        "You are a content strategist. Return valid JSON only."
    )

    # Step 3 — final step consumes all prior context for the finished artifact.
    draft = _call(
        f"Write a short blog post following this outline:\n{outline}\n\n"
        "Keep it under 150 words.",
        "You are a blog writer. Write concise, engaging content."
    )

    return {"research": research, "outline": outline, "draft": draft}


# ──────────────────────────────────────────────────────────────────────
# APPROACH 2: DYNAMIC ADAPTIVE DECOMPOSITION (runtime decisions)
# ──────────────────────────────────────────────────────────────────────

# The LLM receives a tool to spawn subtasks — it decides WHAT to decompose into.
SUBTASK_TOOL = {
    "name": "create_subtask",
    "description": "Break the current task into a subtask that should be executed next.",
    "input_schema": {
        "type": "object",
        "properties": {
            "subtask_name": {
                "type": "string",
                "description": "Short label for this subtask"
            },
            "subtask_prompt": {
                "type": "string",
                "description": "The full prompt to execute for this subtask"
            },
            "is_final": {
                "type": "boolean",
                "description": "True if this subtask produces the final answer"
            }
        },
        "required": ["subtask_name", "subtask_prompt", "is_final"]
    }
}


def adaptive_decomposition(task: str, max_steps: int = 5) -> dict:
    """
    The model itself decides what steps are needed — no hardcoded pipeline.
    Crucial for tasks like 'debug this error' where the path depends on findings.
    """
    results = {}
    context = ""
    step = 0

    # Outer loop keeps running until the model signals completion or we hit the cap.
    # This is the "adaptive" part — step count isn't predetermined.
    while step < max_steps:
        step += 1

        # Feed all prior subtask results back so the model can adapt its plan.
        # Without this accumulation, each step would be blind to earlier findings.
        planning_prompt = (
            f"Task: {task}\n\n"
            f"Completed so far:\n{context if context else 'Nothing yet.'}\n\n"
            "Decide the next subtask needed. Use the create_subtask tool. "
            "Set is_final=true when the task can be completed in this step."
        )

        response = client.messages.create(
            model=MODEL,
            max_tokens=1024,
            system="You are a task planner. Analyze what's needed and decompose dynamically. "
                   "Use the create_subtask tool to define each next step.",
            messages=[{"role": "user", "content": planning_prompt}],
            tools=[SUBTASK_TOOL]
        )

        # Extract the tool call — this tells us what the model chose to do next.
        tool_use = next(
            (b for b in response.content if b.type == "tool_use"), None
        )

        if not tool_use:
            # Model responded with text instead of a tool call — it's done planning.
            final_text = next(
                (b.text for b in response.content if b.type == "text"), ""
            )
            results["final_answer"] = final_text
            break

        subtask = tool_use.input
        print(f"  Step {step}: {subtask['subtask_name']}")

        # Execute the subtask the model just defined — this is the actual work.
        subtask_result = _call(
            subtask["subtask_prompt"],
            "You are a helpful assistant. Complete the assigned subtask thoroughly."
        )

        results[f"step_{step}_{subtask['subtask_name']}"] = subtask_result
        context += f"\n- {subtask['subtask_name']}: {subtask_result}"

        # The model itself decides when it's done, not the caller.
        if subtask.get("is_final", False):
            results["final_answer"] = subtask_result
            break

    return results


# ──────────────────────────────────────────────────────────────────────
# STRATEGY SELECTOR — the exam-relevant decision point
# ──────────────────────────────────────────────────────────────────────

# Predictable tasks have a known shape; unpredictable ones don't.
# This classification drives the architectural choice.
PREDICTABLE_KEYWORDS = {"write", "translate", "summarize", "format", "convert"}


def choose_strategy(task: str) -> str:
    """
    Heuristic: if the task verb maps to a known pipeline, chain it.
    Otherwise, let the model decompose dynamically.
    Real systems might use a classifier or the LLM itself to decide.
    """
    first_word = task.strip().lower().split()[0]
    # Chain when steps are foreseeable; decompose when they aren't.
    if first_word in PREDICTABLE_KEYWORDS:
        return "chain"
    return "decompose"


# ──────────────────────────────────────────────────────────────────────
# SHARED HELPER
# ──────────────────────────────────────────────────────────────────────

def _call(prompt: str, system: str) -> str:
    """Single LLM call — isolated so each pipeline step has clean context."""
    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=system,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.content[0].text


# ──────────────────────────────────────────────────────────────────────
# DEMO
# ──────────────────────────────────────────────────────────────────────

def main():
    tasks = [
        # Predictable → chaining (steps are always: research → outline → draft)
        "Write a blog post about quantum computing",
        # Unpredictable → decomposition (model must figure out what analysis is needed)
        "Analyze why our API latency spiked last week and suggest fixes",
    ]

    for task in tasks:
        strategy = choose_strategy(task)
        print(f"\n{'='*60}")
        print(f"Task: {task}")
        print(f"Strategy chosen: {strategy.upper()}")
        print(f"{'='*60}")

        if strategy == "chain":
            result = prompt_chain(task.split("about ")[-1])
            print(f"\n--- Research ---\n{result['research']}")
            print(f"\n--- Outline ---\n{result['outline']}")
            print(f"\n--- Draft ---\n{result['draft']}")
        else:
            result = adaptive_decomposition(task)
            for key, value in result.items():
                print(f"\n--- {key} ---\n{value}")


if __name__ == "__main__":
    main()
