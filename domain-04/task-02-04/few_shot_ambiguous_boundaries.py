import anthropic
import os
from dotenv import load_dotenv

load_dotenv()

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# --- WHY few-shot matters for ambiguous boundaries ---
#
# Task: classify workplace messages as "direct", "passive-aggressive", or "diplomatic".
# These categories overlap — a message can read as either diplomatic or passive-aggressive
# depending on context. There is no objective ground truth, so a system prompt alone
# can't convey where YOUR organization draws the line. Few-shot examples anchor
# the model to YOUR interpretation of these fuzzy boundaries.

# Each pair encodes a boundary decision that a system prompt alone cannot capture.
few_shot_examples = [
    # Clear case: establishes the "direct" anchor point.
    {
        "role": "user",
        "content": "Classify tone: 'The deploy broke staging. Roll it back now.'"
    },
    {
        "role": "assistant",
        "content": "tone: direct\nreasoning: explicit demand, no hedging or indirection"
    },

    # AMBIGUOUS BOUNDARY #1: diplomatic vs passive-aggressive.
    # "As per my last email" is textbook passive-aggressive in popular culture,
    # but here we classify it as diplomatic — because it cites prior communication
    # without personal attack. This example teaches the model OUR boundary.
    {
        "role": "user",
        "content": "Classify tone: 'As per my last email, the deadline was Friday. Could we revisit the timeline?'"
    },
    {
        "role": "assistant",
        "content": "tone: diplomatic\nreasoning: references prior context but offers collaborative path forward"
    },

    # AMBIGUOUS BOUNDARY #2: passive-aggressive vs direct.
    # Superficially polite ("Thanks for finally"), but the sarcasm signals
    # passive-aggression. Without this example, the model might call it diplomatic
    # because it contains "thanks".
    {
        "role": "user",
        "content": "Classify tone: 'Thanks for finally getting to this. Appreciate it.'"
    },
    {
        "role": "assistant",
        "content": "tone: passive-aggressive\nreasoning: 'finally' implies blame disguised as gratitude"
    },

    # AMBIGUOUS BOUNDARY #3: direct vs passive-aggressive.
    # Blunt but factual — no sarcasm or disguised blame. Models often
    # confuse bluntness with hostility; this example corrects that tendency.
    {
        "role": "user",
        "content": "Classify tone: 'This approach won't scale. We need to rethink it before the demo.'"
    },
    {
        "role": "assistant",
        "content": "tone: direct\nreasoning: states problem and urgency without personal attribution or sarcasm"
    },
]

# --- Test with messages that sit right on the boundaries ---
test_messages = [
    "I'm sure you did your best with the time you had.",
    "Let's align on expectations so we don't run into this again.",
    "Just flagging — this is the third time the tests failed on this module.",
]

# Minimal system prompt — the few-shot examples do the heavy lifting
# because they encode subjective boundary decisions no instruction can.
system_prompt = (
    "Classify workplace message tone as: direct, passive-aggressive, or diplomatic. "
    "Follow the output format from prior examples."
)

for msg in test_messages:
    query = f"Classify tone: '{msg}'"

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=100,
        system=system_prompt,
        # Few-shot examples prepended so the model sees boundary decisions before the query.
        messages=few_shot_examples + [{"role": "user", "content": query}],
    )

    print(f"Input: {msg}")
    print(f"{response.content[0].text}")
    print("-" * 50)
