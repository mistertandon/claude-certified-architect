"""
Agentic Loop Lifecycle POC
==========================
Demonstrates how `stop_reason` values drive the agent loop:
  - "tool_use"  → model wants to call a tool, so we execute it and loop back
  - "end_turn"  → model is done, so we exit the loop
"""

import json
import os

import anthropic
from dotenv import load_dotenv

load_dotenv()

client = anthropic.Anthropic()

# --- Tool definitions (minimal: one tool so the model has something to call) ---

tools = [
    {
        "name": "get_weather",
        "description": "Get the current weather for a given city.",
        "input_schema": {
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": "City name, e.g. 'Paris'",
                }
            },
            "required": ["city"],
        },
    }
]


def execute_tool(name: str, input_data: dict) -> str:
    """Stub tool executor — returns fake data so the loop can complete without external deps."""
    if name == "get_weather":
        return json.dumps({"city": input_data["city"], "temp_c": 22, "condition": "Sunny"})
    return json.dumps({"error": f"Unknown tool: {name}"})


# --- Agentic loop ---

def run_agentic_loop(user_message: str) -> None:
    print(f"\n{'='*60}")
    print(f"User: {user_message}")
    print(f"{'='*60}\n")

    # Seed the conversation with the user's message
    messages = [{"role": "user", "content": user_message}]
    iteration = 0

    # The loop runs until the model decides it has nothing left to do
    while True:
        iteration += 1
        print(f"--- Iteration {iteration} ---")

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            tools=tools,
            messages=messages,
        )

        print(f"stop_reason: {response.stop_reason}")

        # ---------------------------------------------------------------
        # THIS IS THE CORE DECISION POINT OF THE AGENTIC LOOP:
        # stop_reason tells us whether the model wants to act or is done.
        # ---------------------------------------------------------------

        if response.stop_reason == "end_turn":
            # Model has finished — extract and display its final text answer
            for block in response.content:
                if hasattr(block, "text"):
                    print(f"\nAssistant: {block.text}")
            break  # Exit the loop — the agent's work is complete

        if response.stop_reason == "tool_use":
            # Model is requesting tool calls — we must execute them and feed results back
            # Append the full assistant message so the API sees the tool_use blocks it emitted
            messages.append({"role": "assistant", "content": response.content})

            # Build a single user message containing one tool_result per tool_use block
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    print(f"  Tool call: {block.name}({json.dumps(block.input)})")
                    result = execute_tool(block.name, block.input)
                    print(f"  Tool result: {result}")
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,  # Must match the id from the tool_use block
                            "content": result,
                        }
                    )

            # Feed results back as a user message — the API requires this role alternation
            messages.append({"role": "user", "content": tool_results})
            # Loop continues: the model will see its tool calls + our results and decide next step


# --- Entry point ---

if __name__ == "__main__":
    # A prompt that forces at least one tool call before the final answer
    run_agentic_loop("What's the weather in Tokyo and Paris? Compare them briefly.")
