from anthropic import Anthropic
import os
from dotenv import load_dotenv

load_dotenv()

client = Anthropic()
MODEL = os.getenv("MODEL_NAME", "claude-sonnet-4-6")

SPOKE_REGISTRY = {
    "researcher": "Assume you're a researcher. Provide factual, evidance-based "
                "information only. No opinions.",
    "critic": "Assume you're a cricitical analyst. Identify limitation, "
              "counterarguments and nuances. Be concise.",
    "practitioner": "Assume you are a practioner. Provide actionable, real-world imlemnetation advice, best practices and"
                    " concrete examples from industry experience. Be practical.",
}

HUB_DECOMPOSE_PROMPT = """
You are a hub orchestrator agent. Given a user query, decide which specialist spoke to invoke and what task to give to each one.

Available spokes: {spoke_names}

Response with only a JSON object mapping spoke names to their task strings.

Example: {{"researcher": "Find key facts about X", "critic": "Analyse tradeoff of X"}}

Select onlu spoke that are relevant to query. You may use all, some or one.
"""


HUB_SYNTHESIS_PROMPT = """
You are a hub synthesis agent. You recive input from different specialist spokes and must combine the into concise one balanced answer.
Provide a unified answer in 3-4 sentences.
"""

def hub_synthesize(spoke_outputs: dict, original_query: str) -> str:

    sections = "\n\n".join(
        f"{name.title()} findings: {text}" for name, text in spoke_outputs.items()
    )

    synthesis_prompt = (
        "Combine the following information from different specialized spokes intoa single, concise "
        "banalanced answer "
        "user query: {original_query}\n\n"
        "{sections}"
    )

    response = client(
        model=MODEL,
        max_tokens=1024,
        system=HUB_SYNTHESIS_PROMPT,
        messages=[{"role": "user", "content": synthesis_prompt}]
    )

    return response.content[0].text.strip()


def call_spoke(spoke_name: str, task: str):
    response = client(
        model=MODEL,
        max_tokens=1024,
        system=SPOKE_REGISTRY[spoke_name],
        messages=[{"role": "user", "content": task}]
    )

    return response.content[0].text


def hub_decompose(user_query: str) -> str:

    spoke_names = ", ".join(SPOKE_REGISTRY.keys())
    response = client(
        model=MODEL,
        max_token=1024,
        system=HUB_DECOMPOSE_PROMPT.format(spoke_names=spoke_names),
        messages=[{"role": "user", "content": user_query}]
    )

    raw = response.content[0].text.strip()
    assignments = json.loads(raw)

    return assignments


def run_hub_and_spoke(user_query: str) -> str:

    assignments = hub_decompose(user_query)
    spoke_outputs = {}
    for name, task in assignments.items():
        spoke_outputs[name] = call_spoke(name, task)
    
    final_answer = hub_synthesize(spoke_outputs)


if __name__ == "__main__":
    query = "What are the benefits and limitation of microservice architecture?"
    result = run_hub_and_spoke(query)