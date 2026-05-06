"""
Hub-and-Spoke Architecture POC

Architecture:
  [User] → [Hub Agent] → [Spoke: Researcher]
                       → [Spoke: Critic]
                       ← [Synthesized Response]

The hub orchestrates by decomposing a task and delegating to
specialized spoke agents, then merging their outputs.
"""

import os
from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()

# Single client instance shared across all agents — spokes don't need
# their own credentials or connections.
client = Anthropic()
MODEL = os.getenv("MODEL_NAME", "claude-sonnet-4-6")


def call_spoke(role_prompt: str, task: str) -> str:
    """Invoke one spoke agent with a focused role and task."""
    # Each spoke gets an isolated conversation — no cross-contamination
    # between specialist perspectives.
    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        # System prompt defines the spoke's specialization boundary.
        system=role_prompt,
        messages=[{"role": "user", "content": task}],
    )
    return response.content[0].text


def hub_synthesize(spoke_outputs: dict[str, str], original_query: str) -> str:
    """Hub merges spoke results into a single coherent answer."""
    # The hub sees ALL spoke outputs — this is the architectural advantage:
    # spokes are independent, but the hub has the full picture.
    synthesis_prompt = f"""You are a synthesis agent. Combine these specialist outputs
into one concise, balanced answer for the user's query: "{original_query}"

Research findings:
{spoke_outputs['researcher']}

Critical analysis:
{spoke_outputs['critic']}

Provide a unified answer in 3-4 sentences."""

    response = client.messages.create(
        model=MODEL,
        max_tokens=512,
        messages=[{"role": "user", "content": synthesis_prompt}],
    )
    return response.content[0].text


def run_hub_and_spoke(user_query: str) -> str:
    """
    Main orchestration loop:
    1. Hub decomposes → 2. Spokes execute in isolation → 3. Hub merges
    """

    # --- Spoke definitions ---
    # Each spoke has a narrow mandate — this prevents scope creep
    # and makes outputs predictable for the hub to merge.
    spokes = {
        "researcher": {
            "role": "You are a research specialist. Provide factual, "
                    "evidence-based information only. No opinions.",
            "task": f"Research this topic and provide key facts: {user_query}",
        },
        "critic": {
            "role": "You are a critical analyst. Identify limitations, "
                    "counterarguments, and nuances. Be concise.",
            "task": f"Critically analyze this topic — what are the tradeoffs "
                    f"and limitations? Topic: {user_query}",
        },
    }

    # --- Fan-out: dispatch to spokes ---
    # Sequential here for simplicity; production would use asyncio
    # to call spokes in parallel (they're independent).
    spoke_outputs = {}
    for name, config in spokes.items():
        print(f"  [Hub] Dispatching to spoke: {name}")
        spoke_outputs[name] = call_spoke(config["role"], config["task"])
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
