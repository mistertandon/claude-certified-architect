"""
POC: PostToolUse Hooks — Intercept and modify tool outputs for data normalization.

In Claude Code, PostToolUse hooks fire after a tool executes, letting you
transform raw outputs before the model sees them. This POC replicates that
pattern programmatically with the Anthropic SDK.
"""

import os
import json
from dotenv import load_dotenv
from anthropic import Anthropic

# Load from .env so secrets never live in source control
load_dotenv()

client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# --- Tool Definitions ---

# Simulates a tool that returns messy, inconsistent data (like a real API would)
tools = [
    {
        "name": "get_customer_record",
        "description": "Fetch a customer record by ID from the legacy CRM system.",
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_id": {
                    "type": "string",
                    "description": "The customer identifier"
                }
            },
            "required": ["customer_id"]
        }
    }
]


# --- Simulated Tool Execution ---

def execute_tool(tool_name: str, tool_input: dict) -> str:
    """Simulates a legacy API returning inconsistently formatted data."""
    if tool_name == "get_customer_record":
        # Intentionally messy: mixed case, extra whitespace, inconsistent date format
        return json.dumps({
            "Name": "  john DOE  ",
            "EMAIL": "John.Doe@Example.COM",
            "phone": "(555) 123-4567",
            "signup_date": "03/15/2023",
            "account_balance": "$1,234.56",
            "status": "ACTIVE",
            "address": "  123 main ST, apt 4B, new york, NY  10001  "
        })
    return json.dumps({"error": "Unknown tool"})


# --- PostToolUse Hook ---

def post_tool_use_hook(tool_name: str, raw_output: str) -> str:
    """
    PostToolUse hook: normalizes tool output BEFORE the model processes it.

    WHY: Raw tool outputs from legacy systems are inconsistent. Normalizing
    here means the model always sees clean data — reducing hallucination risk
    and ensuring downstream responses use consistent formatting.
    """
    data = json.loads(raw_output)

    if tool_name == "get_customer_record":
        normalized = {}
        for key, value in data.items():
            # Standardize keys to snake_case — model works better with consistent schema
            norm_key = key.lower().strip()

            if isinstance(value, str):
                value = value.strip()

                # Normalize email to lowercase — prevents duplicate identity issues
                if "email" in norm_key:
                    value = value.lower()

                # Title-case names — consistent display format for end users
                elif "name" in norm_key:
                    value = value.title()

                # Strip currency symbols — model can do math on clean numbers
                elif "balance" in norm_key:
                    value = value.replace("$", "").replace(",", "")

                # ISO 8601 dates — eliminates ambiguity (MM/DD vs DD/MM)
                elif "date" in norm_key:
                    parts = value.split("/")
                    if len(parts) == 3:
                        value = f"{parts[2]}-{parts[0].zfill(2)}-{parts[1].zfill(2)}"

                # Normalize address whitespace — cleaner for geocoding downstream
                elif "address" in norm_key:
                    value = " ".join(value.split()).title()

            normalized[norm_key] = value

        # Inject metadata so the model knows this data was cleaned
        normalized["_normalized"] = True
        normalized["_hook"] = "post_tool_use"

        print(f"\n{'='*60}")
        print("POST_TOOL_USE HOOK FIRED")
        print(f"{'='*60}")
        print(f"Tool: {tool_name}")
        print(f"\nRaw output:\n{json.dumps(data, indent=2)}")
        print(f"\nNormalized output:\n{json.dumps(normalized, indent=2)}")
        print(f"{'='*60}\n")

        return json.dumps(normalized)

    return raw_output


# --- Agentic Loop ---

def run_agent():
    """
    Standard agentic loop with PostToolUse hook injected between
    tool execution and result submission.
    """
    messages = [
        {
            "role": "user",
            "content": "Look up customer record for ID 'cust-42' and summarize their info."
        }
    ]

    print("Starting agent with PostToolUse hook...\n")

    # Outer loop: keeps running until model stops requesting tools
    while True:
        response = client.messages.create(
            model=os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514"),
            max_tokens=1024,
            tools=tools,
            messages=messages
        )

        # Check if model wants to use a tool
        if response.stop_reason == "tool_use":
            # Process each content block in the response
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    print(f"Model requested tool: {block.name}")
                    print(f"Input: {json.dumps(block.input, indent=2)}")

                    # Step 1: Execute the tool (raw output)
                    raw_output = execute_tool(block.name, block.input)

                    # Step 2: PostToolUse hook — normalize BEFORE model sees it
                    # WHY here and not in the tool itself: separation of concerns.
                    # The hook is reusable across tools; tool logic stays pure.
                    normalized_output = post_tool_use_hook(block.name, raw_output)

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        # Model receives normalized data, not raw mess
                        "content": normalized_output
                    })

            # Append assistant response + tool results for next iteration
            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": tool_results})

        else:
            # Model finished — extract final text response
            for block in response.content:
                if hasattr(block, "text"):
                    print(f"\nAgent Response:\n{block.text}")
            break


if __name__ == "__main__":
    run_agent()
