"""
POC: Specificity reduces ambiguity and improves consistency across runs.

Demonstrates how a vague prompt yields varied/unpredictable outputs,
while a specific prompt produces consistent, structured results.
"""

import os
from dotenv import load_dotenv
from anthropic import Anthropic

# Load API key from .env so credentials stay out of source control
load_dotenv()

client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
MODEL = "claude-sonnet-4-6"

# --- Vague prompt: lacks constraints, so the model improvises format/length/focus each run ---
vague_prompt = "Tell me about Python."

# --- Specific prompt: constraints pin down format, scope, audience, and length ---
specific_prompt = (
    "List exactly 3 advantages of Python for backend web development. "
    "Format each as a single bullet point (hyphen prefix). "
    "Each bullet must be one sentence, max 20 words. "
    "Target audience: senior engineers evaluating language choices."
)


def call_model(prompt: str, label: str) -> str:
    """Send a single-turn message and return the text response."""
    response = client.messages.create(
        model=MODEL,
        max_tokens=256,
        # temperature=0 maximizes determinism — isolates the effect of prompt specificity
        temperature=0,
        messages=[{"role": "user", "content": prompt}],
    )
    text = response.content[0].text
    print(f"\n{'='*60}")
    print(f"[{label}]")
    print(f"Prompt: {prompt[:80]}...")
    print(f"{'='*60}")
    print(text)
    return text


def main():
    # Run each prompt 3 times to show consistency (or lack thereof)
    print("\n>>> VAGUE PROMPT — expect varied structure/length across runs <<<")
    for i in range(3):
        call_model(vague_prompt, f"Vague Run {i+1}")

    print("\n\n>>> SPECIFIC PROMPT — expect near-identical output across runs <<<")
    for i in range(3):
        call_model(specific_prompt, f"Specific Run {i+1}")


if __name__ == "__main__":
    main()
