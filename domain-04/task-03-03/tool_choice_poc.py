"""
POC: Structured output via tool_use — demonstrating tool_choice options.

tool_choice controls WHETHER and WHICH tool the model must call:
  - "auto"  → model decides if a tool is needed (default behavior)
  - "any"   → model MUST call a tool, but picks which one
  - {"type": "tool", "name": "X"} → model MUST call tool X (guaranteed schema)
"""

import os
import json
from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()

client = Anthropic()

# --- Tool definitions (the "schema" that guarantees structured output) ---

# Each tool acts as a JSON schema contract — the model's response MUST conform to it
tools = [
    {
        "name": "extract_contact",
        "description": "Extract structured contact information from text.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name":  {"type": "string", "description": "Full name"},
                "email": {"type": "string", "description": "Email address"},
                "phone": {"type": "string", "description": "Phone number"},
            },
            # "required" is what makes the output truly structured — no optional fields
            "required": ["name", "email", "phone"],
        },
    },
    {
        "name": "extract_sentiment",
        "description": "Classify sentiment of the given text.",
        "input_schema": {
            "type": "object",
            "properties": {
                "sentiment":   {"type": "string", "enum": ["positive", "negative", "neutral"]},
                "confidence":  {"type": "number", "description": "0.0 to 1.0"},
                "explanation": {"type": "string", "description": "Brief reason"},
            },
            "required": ["sentiment", "confidence", "explanation"],
        },
    },
]


def call_with_tool_choice(tool_choice, user_message, label):
    """Single helper to demonstrate each tool_choice variant."""
    print(f"\n{'='*60}")
    print(f"  tool_choice = {json.dumps(tool_choice)}")
    print(f"  Label: {label}")
    print(f"{'='*60}")

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        tools=tools,
        # tool_choice is the ONLY parameter that changes across demos
        tool_choice=tool_choice,
        messages=[{"role": "user", "content": user_message}],
    )

    # stop_reason reveals what happened: "tool_use" vs "end_turn"
    print(f"  stop_reason: {response.stop_reason}")

    for block in response.content:
        if block.type == "text":
            print(f"  [text]: {block.text}")
        elif block.type == "tool_use":
            # tool_use blocks contain the structured JSON — this IS the structured output
            print(f"  [tool_use] tool: {block.name}")
            print(f"  [tool_use] input: {json.dumps(block.input, indent=2)}")


# ---------------------------------------------------------------------------
# Demo 1: tool_choice = {"type": "auto"} (default)
# Model DECIDES whether to use a tool. For non-tool-worthy prompts, it won't.
# ---------------------------------------------------------------------------
call_with_tool_choice(
    tool_choice={"type": "auto"},
    user_message="What is the capital of France?",
    label="AUTO — no tool needed, model answers directly (stop_reason=end_turn)",
)

# Same "auto" but with a prompt that naturally fits a tool
call_with_tool_choice(
    tool_choice={"type": "auto"},
    user_message="Extract contact: John Doe, john@example.com, 555-1234",
    label="AUTO — model chooses a tool because the prompt fits (stop_reason=tool_use)",
)

# ---------------------------------------------------------------------------
# Demo 2: tool_choice = {"type": "any"}
# Model MUST call a tool, but it picks which one. Useful when you always want
# structured output but multiple schemas are valid.
# ---------------------------------------------------------------------------
call_with_tool_choice(
    tool_choice={"type": "any"},
    user_message="I absolutely love this product, it changed my life!",
    label="ANY — model must pick a tool; it should choose extract_sentiment",
)

# ---------------------------------------------------------------------------
# Demo 3: tool_choice = {"type": "tool", "name": "extract_contact"}
# Forces a SPECIFIC tool. This is how you guarantee a particular JSON schema
# in the response — the core pattern for structured output.
# ---------------------------------------------------------------------------
call_with_tool_choice(
    tool_choice={"type": "tool", "name": "extract_contact"},
    user_message="Reach me at jane.smith@corp.io or call 415-999-0000. — Jane Smith",
    label="FORCED TOOL — guarantees extract_contact schema in response",
)

# Force the OTHER tool on the same input to show schema is always honoured
call_with_tool_choice(
    tool_choice={"type": "tool", "name": "extract_sentiment"},
    user_message="Reach me at jane.smith@corp.io or call 415-999-0000. — Jane Smith",
    label="FORCED TOOL — same input, but extract_sentiment schema is forced",
)
