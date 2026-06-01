import os
from anthropic import Anthropic

# Single client instance — reuses connection pool across calls
client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

# Few-shot examples live in the system prompt so they apply to EVERY user turn
# without consuming per-turn tokens repeatedly.
SYSTEM_PROMPT = """You are a sentiment classifier. Classify the sentiment of the given text as POSITIVE, NEGATIVE, or MIXED.

Respond with ONLY a JSON object in this exact format:
{"sentiment": "<label>", "confidence": <0.0-1.0>, "reasoning": "<one sentence>"}

Here are examples:

Text: "The food was absolutely divine but we waited 45 minutes for a table."
{"sentiment": "MIXED", "confidence": 0.9, "reasoning": "Strong praise for food quality contrasted with complaint about wait time."}

Text: "I can't believe how terrible the customer service was. Never coming back."
{"sentiment": "NEGATIVE", "confidence": 0.95, "reasoning": "Explicit dissatisfaction with a vow to not return indicates strong negative sentiment."}

Text: "Best purchase I've made all year. Works exactly as advertised."
{"sentiment": "POSITIVE", "confidence": 0.95, "reasoning": "Superlative praise combined with met expectations signals clear satisfaction."}

Text: "It's fine, I guess. Does what it's supposed to do, nothing more."
{"sentiment": "MIXED", "confidence": 0.7, "reasoning": "Lukewarm acknowledgment without enthusiasm suggests ambivalence rather than satisfaction."}"""
# 4 examples chosen to cover each label + the ambiguous "MIXED" case twice,
# because ambiguous inputs are where few-shot examples pay off the most.


def classify_sentiment(text: str) -> str:
    """Send a single text for sentiment classification."""
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=256,  # JSON response is short; cap tokens to save cost
        system=SYSTEM_PROMPT,
        messages=[
            {"role": "user", "content": f'Text: "{text}"'}
            # No assistant prefill — the few-shot examples already lock the format
        ],
    )
    return response.content[0].text


def main():
    # Test inputs deliberately span easy, hard, and edge cases
    test_inputs = [
        "This product changed my life! I recommend it to everyone.",
        "Decent build quality but the software is buggy and crashes often.",
        "I returned it the same day. Complete waste of money.",
        "Not bad, not great. It exists.",
    ]

    for text in test_inputs:
        print(f"\nInput : {text}")
        result = classify_sentiment(text)
        print(f"Output: {result}")


if __name__ == "__main__":
    main()
