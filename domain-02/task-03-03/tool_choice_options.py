"""
POC: tool_choice Options — 'auto', 'any', and forced specific tool
(Claude Architect Exam — Domain 02, Tool Distribution Strategies)

Scenario:
  A weather assistant has two tools: get_weather and get_forecast.
  We demonstrate how tool_choice controls whether/which tools are invoked:
    1. auto  → model decides freely (may skip tools entirely)
    2. any   → model MUST call at least one tool (but picks which)
    3. tool  → model MUST call the exact tool we specify

Key insight: tool_choice shifts control from the model to the developer,
enabling deterministic pipelines where specific tool calls are guaranteed.
"""

import os
import json
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

client = Anthropic()
MODEL = "claude-sonnet-4-6"

# ── Tool Definitions ───────────────────────────────────────────────────────
# Two tools so we can observe which one the model picks under each strategy.

TOOLS = [
    {
        "name": "get_weather",
        "description": (
            "Get current weather conditions for a city. "
            "Returns temperature, humidity, and description."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": "City name, e.g. 'Paris'"
                }
            },
            "required": ["city"]
        },
    },
    {
        "name": "get_forecast",
        "description": (
            "Get a 3-day weather forecast for a city. "
            "Returns daily high/low temperatures and conditions."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": "City name, e.g. 'Paris'"
                },
                "days": {
                    "type": "integer",
                    "description": "Number of forecast days (1-5)",
                    "default": 3
                }
            },
            "required": ["city"]
        },
    },
]


# ── Simulated Tool Execution ──────────────────────────────────────────────

def execute_tool(name: str, input_data: dict) -> str:
    if name == "get_weather":
        return json.dumps({
            "city": input_data["city"],
            "temp_celsius": 22,
            "humidity": 65,
            "description": "Partly cloudy",
        })
    if name == "get_forecast":
        days = input_data.get("days", 3)
        forecast = [
            {"day": i + 1, "high": 24 - i, "low": 14 - i, "conditions": "Sunny"}
            for i in range(days)
        ]
        return json.dumps({"city": input_data["city"], "forecast": forecast})
    return json.dumps({"error": f"Unknown tool: {name}"})


# ── Single-turn Runner ─────────────────────────────────────────────────────
# Runs one API call with a given tool_choice, processes any tool calls,
# then makes a follow-up call so the model produces a final text response.

def run_with_tool_choice(label: str, tool_choice: dict | str, user_message: str):
    """Execute a single demo with the specified tool_choice setting."""
    print(f"\n{'='*64}")
    print(f"  Strategy: {label}")
    print(f"  tool_choice = {json.dumps(tool_choice)}")
    print(f"  User: \"{user_message}\"")
    print(f"{'='*64}")

    # First call — tool_choice controls model behavior here.
    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system="You are a helpful weather assistant. Use your tools when appropriate.",
        tools=TOOLS,
        # THIS IS THE KEY PARAMETER — everything else stays identical
        # across all three demos, isolating tool_choice as the only variable.
        tool_choice=tool_choice,
        messages=[{"role": "user", "content": user_message}],
    )

    print(f"  stop_reason: {response.stop_reason}")

    # Inspect what the model did
    text_parts = []
    tool_results = []

    for block in response.content:
        if block.type == "text":
            text_parts.append(block.text)
            print(f"  [text]: {block.text[:120]}")
        elif block.type == "tool_use":
            print(f"  [tool_call]: {block.name}({json.dumps(block.input)})")
            result = execute_tool(block.name, block.input)
            print(f"  [tool_result]: {result[:120]}")
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": result,
            })

    # If tools were called, feed results back for a final text answer.
    if response.stop_reason == "tool_use":
        follow_up = client.messages.create(
            model=MODEL,
            max_tokens=1024,
            system="You are a helpful weather assistant.",
            tools=TOOLS,
            messages=[
                {"role": "user", "content": user_message},
                {"role": "assistant", "content": response.content},
                {"role": "user", "content": tool_results},
            ],
        )
        final_text = "".join(
            b.text for b in follow_up.content if b.type == "text"
        )
        print(f"  [final answer]: {final_text[:200]}")
    else:
        # Model answered directly without tools (possible with 'auto').
        print(f"  [final answer]: {''.join(text_parts)[:200]}")


# ── Demo 1: tool_choice = "auto" ──────────────────────────────────────────
# Model freely decides whether to use tools, and which ones.
# Best for: open-ended assistants where tool use is optional.

def demo_auto():
    # Greeting doesn't need tools — model should skip them entirely.
    run_with_tool_choice(
        label="AUTO — model decides (greeting, expects NO tool call)",
        tool_choice={"type": "auto"},
        user_message="Hello! How are you?",
    )

    # Weather question — model should choose get_weather on its own.
    run_with_tool_choice(
        label="AUTO — model decides (weather query, expects tool call)",
        tool_choice={"type": "auto"},
        user_message="What's the weather like in Tokyo?",
    )


# ── Demo 2: tool_choice = "any" ───────────────────────────────────────────
# Model MUST call at least one tool, but picks which one.
# Best for: pipelines where every turn must produce structured data,
# but the specific tool depends on the input.

def demo_any():
    # Even a greeting gets forced into a tool call — demonstrating
    # that "any" overrides the model's natural inclination to skip tools.
    run_with_tool_choice(
        label="ANY — must use a tool (even for a greeting)",
        tool_choice={"type": "any"},
        user_message="Hello! How are you?",
    )

    run_with_tool_choice(
        label="ANY — must use a tool (weather query)",
        tool_choice={"type": "any"},
        user_message="What's the weather like in London?",
    )


# ── Demo 3: tool_choice = specific tool ───────────────────────────────────
# Model MUST call the exact named tool — no choice at all.
# Best for: deterministic pipelines, form-filling, guaranteed data extraction.

def demo_forced_tool():
    # Force get_forecast even though the user asked about current weather.
    # This proves the developer controls which tool fires, not the model.
    run_with_tool_choice(
        label="FORCED — must call get_forecast (overrides model's natural pick)",
        tool_choice={"type": "tool", "name": "get_forecast"},
        user_message="What's the weather like in Berlin right now?",
    )

    # Force get_weather even though user asked about forecast.
    # The mismatch is intentional — it shows developer override.
    run_with_tool_choice(
        label="FORCED — must call get_weather (user asked forecast, forced current)",
        tool_choice={"type": "tool", "name": "get_weather"},
        user_message="What's the 3-day forecast for Sydney?",
    )


# ── Main ───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("╔════════════════════════════════════════════════════════════════╗")
    print("║   POC: tool_choice Options — auto / any / forced tool        ║")
    print("╚════════════════════════════════════════════════════════════════╝")

    print("\n\n▶ DEMO 1: tool_choice = 'auto' (model decides)")
    print("  The model freely chooses whether and which tool to call.")
    demo_auto()

    print("\n\n▶ DEMO 2: tool_choice = 'any' (must use a tool)")
    print("  The model MUST call at least one tool, but picks which.")
    demo_any()

    print("\n\n▶ DEMO 3: tool_choice = {type: 'tool', name: '...'} (forced)")
    print("  The model MUST call the exact tool we specify.")
    demo_forced_tool()

    print("\n\n" + "="*64)
    print("KEY TAKEAWAY:")
    print("  auto  → model decides  (flexible, best for general assistants)")
    print("  any   → must use tool  (guaranteed structured output)")
    print("  tool  → forced tool    (deterministic, developer-controlled)")
    print("="*64)
