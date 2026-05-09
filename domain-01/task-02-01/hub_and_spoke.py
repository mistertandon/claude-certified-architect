"""
Hub-and-Spoke Architecture POC

Architecture:
  [User] → [Hub Agent] → [Spoke: Researcher]
                       → [Spoke: Critic]
                       ← [Synthesized Response]

The hub orchestrates by decomposing a task and delegating to
specialized spoke agents, then merging their outputs.
"""

import json
import os
from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()

client = Anthropic()
MODEL = os.getenv("MODEL_NAME", "claude-sonnet-4-6")

SPOKE_REGISTRY = {
    "researcher": "You are a research specialist. Provide factual, "
                  "evidence-based information only. No opinions.",
    "critic": "You are a critical analyst. Identify limitations, "
              "counterarguments, and nuances. Be concise.",
}

HUB_DECOMPOSITION_PROMPT = """You are a hub orchestrator agent. Given a user query, decide which specialist spokes to invoke and what task to give each one.

Available spokes: {spoke_names}

Respond with ONLY a JSON object mapping spoke names to their task strings.
Example: {{"researcher": "Find key facts about X", "critic": "Analyze tradeoffs of X"}}

Select only the spokes that are relevant to the query. You may use one, some, or all."""

HUB_SYNTHESIS_PROMPT = (
    "You are a hub synthesis agent. You receive outputs from specialist spokes "
    "and must combine them into one concise, balanced answer. "
    "Provide a unified answer in 3-4 sentences."
)


def hub_decompose(user_query: str) -> dict[str, str]:
    """Hub agent decides which spokes to call and with what tasks."""
    spoke_names = ", ".join(SPOKE_REGISTRY.keys())
    response = client.messages.create(
        model=MODEL,
        max_tokens=512,
        system=HUB_DECOMPOSITION_PROMPT.format(spoke_names=spoke_names),
        messages=[{"role": "user", "content": user_query}],
    )
    raw = response.content[0].text.strip()
    assignments = json.loads(raw)

    unknown = set(assignments) - set(SPOKE_REGISTRY)
    if unknown:
        raise ValueError(f"Hub requested unknown spokes: {unknown}")

    return assignments


def call_spoke(spoke_name: str, task: str) -> str:
    """Invoke one spoke agent with a focused role and task."""
    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=SPOKE_REGISTRY[spoke_name],
        messages=[{"role": "user", "content": task}],
    )
    return response.content[0].text


def hub_synthesize(spoke_outputs: dict[str, str], original_query: str) -> str:
    """Hub merges spoke results into a single coherent answer."""
    sections = "\n\n".join(
        f"{name.title()} findings:\n{text}" for name, text in spoke_outputs.items()
    )
    synthesis_prompt = (
        f'Combine these specialist outputs into one concise, balanced answer '
        f'for the user\'s query: "{original_query}"\n\n{sections}'
    )
    response = client.messages.create(
        model=MODEL,
        max_tokens=512,
        system=HUB_SYNTHESIS_PROMPT,
        messages=[{"role": "user", "content": synthesis_prompt}],
    )
    return response.content[0].text


def run_hub_and_spoke(user_query: str) -> str:
    """
    Main orchestration loop:
    1. Hub decomposes the query into spoke assignments
    2. Spokes execute in isolation
    3. Hub synthesizes spoke outputs
    """

    # --- Hub decomposes: LLM decides which spokes to call ---
    print("  [Hub] Analyzing query and selecting spokes...")
    assignments = hub_decompose(user_query)
    print(f"  [Hub] Assigned spokes: {list(assignments.keys())}")

    # --- Fan-out: dispatch to spokes ---
    spoke_outputs = {}
    for name, task in assignments.items():
        print(f"  [Hub] Dispatching to spoke: {name}")
        spoke_outputs[name] = call_spoke(name, task)
        print(f"  [Hub] Received from spoke: {name}")

    # --- Fan-in: hub synthesizes ---
    print("  [Hub] Synthesizing spoke outputs...")
    final_answer = hub_synthesize(spoke_outputs, user_query)

    return final_answer


if __name__ == "__main__":
    query = "What are the benefits and risks of microservices architecture?"
    print(f"\n[User Query]: {query}\n")
    print("[Hub-and-Spoke Processing]")

    result = run_hub_and_spoke(query)

    print(f"\n[Final Synthesized Answer]:\n{result}")
