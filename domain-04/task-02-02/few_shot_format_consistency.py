"""
Few-shot prompting POC: Format Consistency
All examples follow an identical output structure so the model learns the schema.
"""

import os
from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()

client = Anthropic()

# Few-shot examples enforce a rigid JSON-like structure the model must replicate
FEW_SHOT_EXAMPLES = [
    {
        "role": "user",
        "content": "Classify: 'The battery lasts all day and the screen is gorgeous.'"
    },
    {
        # Every assistant example uses the EXACT same keys/format — this is the consistency anchor
        "role": "assistant",
        "content": (
            "Category: Product Review\n"
            "Sentiment: Positive\n"
            "Confidence: 0.95\n"
            "Key Phrases: battery lasts all day, screen is gorgeous"
        )
    },
    {
        "role": "user",
        "content": "Classify: 'Waited 45 minutes for cold food. Never coming back.'"
    },
    {
        # Negative example ensures the model doesn't just default to positive
        "role": "assistant",
        "content": (
            "Category: Restaurant Review\n"
            "Sentiment: Negative\n"
            "Confidence: 0.92\n"
            "Key Phrases: waited 45 minutes, cold food, never coming back"
        )
    },
    {
        "role": "user",
        "content": "Classify: 'The new policy takes effect Monday but details are still unclear.'"
    },
    {
        # Neutral example prevents binary bias — model sees the full sentiment range
        "role": "assistant",
        "content": (
            "Category: News Report\n"
            "Sentiment: Neutral\n"
            "Confidence: 0.88\n"
            "Key Phrases: new policy, takes effect Monday, details unclear"
        )
    },
]

# System prompt reinforces the structure without re-explaining it — examples do the heavy lifting
SYSTEM_PROMPT = (
    "You are a text classifier. Respond ONLY in the exact format shown in the examples. "
    "Do not add explanations or extra fields."
)


def classify_text(text: str) -> str:
    """Send a new input with few-shot context so the model mirrors the learned format."""
    messages = FEW_SHOT_EXAMPLES + [
        {"role": "user", "content": f"Classify: '{text}'"}
    ]

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=150,
        # Low temperature reduces creative drift from the established format
        temperature=0.0,
        system=SYSTEM_PROMPT,
        messages=messages,
    )

    return response.content[0].text


if __name__ == "__main__":
    test_inputs = [
        "This framework makes async programming surprisingly intuitive.",
        "My flight was canceled twice and nobody offered help.",
        "The quarterly earnings report will be published next Tuesday.",
    ]

    for text in test_inputs:
        print(f"Input: {text}")
        print(f"Output:\n{classify_text(text)}")
        print("-" * 60)
