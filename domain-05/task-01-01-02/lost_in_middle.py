"""
POC: 'Lost in the Middle' Effect
Demonstrates that information buried in the middle of long contexts
is less likely to be recalled compared to information at the start or end.
"""

import os
from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()

client = Anthropic()
MODEL = os.getenv("MODEL_NAME", "claude-sonnet-4-6")

# The target fact the model must recall — intentionally obscure so retrieval
# depends on position, not prior knowledge.
TARGET_FACT = "The secret project code name is AURORA-7749."

# Filler paragraphs simulate a long document where the target fact gets buried.
FILLER_PARAGRAPH = (
    "The quarterly budget review meeting covered multiple departmental updates. "
    "Marketing reported a 12% increase in engagement metrics across social channels. "
    "The engineering team discussed infrastructure upgrades planned for next quarter. "
    "HR announced new wellness initiatives and updated remote work policies. "
    "Finance highlighted cost optimization efforts yielding 8% savings year over year."
)


def build_context(target_position: str, num_fillers: int = 20) -> str:
    """Place the target fact at beginning, middle, or end of a long document."""
    fillers = [f"[Section {i+1}] {FILLER_PARAGRAPH}" for i in range(num_fillers)]

    if target_position == "beginning":
        # Fact at position 0 — highest recall expected (primacy effect)
        return TARGET_FACT + "\n\n" + "\n\n".join(fillers)
    elif target_position == "middle":
        # Fact buried at midpoint — lowest recall expected (the effect we're demonstrating)
        mid = num_fillers // 2
        return "\n\n".join(fillers[:mid]) + "\n\n" + TARGET_FACT + "\n\n" + "\n\n".join(fillers[mid:])
    else:
        # Fact at the end — strong recall due to recency effect
        return "\n\n".join(fillers) + "\n\n" + TARGET_FACT


QUESTION = "What is the secret project code name mentioned in the document?"


def test_recall(position: str) -> str:
    """Query the model about the target fact placed at a specific position."""
    context = build_context(position)

    # System prompt forces the model to rely ONLY on the provided document,
    # preventing it from hedging or refusing to answer.
    response = client.messages.create(
        model=MODEL,
        max_tokens=150,
        # Low temperature reduces randomness — makes recall differences
        # attributable to position, not sampling variance.
        temperature=0.0,
        system="You are a document analyst. Answer ONLY from the provided document. Be concise.",
        messages=[
            {
                "role": "user",
                "content": f"Document:\n\n{context}\n\n---\nQuestion: {QUESTION}",
            }
        ],
    )
    return response.content[0].text


def main():
    positions = ["beginning", "middle", "end"]

    print("=" * 60)
    print("  'LOST IN THE MIDDLE' EFFECT DEMONSTRATION")
    print("=" * 60)
    print(f"\nTarget fact: {TARGET_FACT}")
    print(f"Model: {MODEL}")
    print(f"Question: {QUESTION}\n")
    print("-" * 60)

    for pos in positions:
        print(f"\n[Position: {pos.upper()}]")
        answer = test_recall(pos)
        print(f"  Response: {answer}")

        # Simple heuristic: check if the model recalled the key identifier
        recalled = "AURORA-7749" in answer
        print(f"  Recalled correctly: {'YES' if recalled else 'NO'}")

    print("\n" + "-" * 60)
    print("\nExpected pattern: beginning=YES, middle=WEAK/NO, end=YES")
    print("This demonstrates the 'lost in the middle' effect where models")
    print("attend less to information in the center of long contexts.\n")


if __name__ == "__main__":
    main()
