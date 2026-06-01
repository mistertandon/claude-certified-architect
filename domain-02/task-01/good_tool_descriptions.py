"""
POC: What makes a good tool description (Claude Architect Exam - Domain 02)

Demonstrates four best practices:
  1. Input format specifications with examples
  2. Edge cases and boundary conditions
  3. Clear parameter descriptions with types, ranges, constraints
  4. Tool descriptions as rich documentation for the model
"""

import os
import json
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

client = Anthropic()

# ── Tool Definitions ─────────────────────────────────────────────────────────
# The QUALITY of these descriptions directly controls how well the model
# selects and parameterizes tools. Vague descriptions cause hallucinated
# arguments; detailed ones yield correct calls on the first attempt.

tools = [
    {
        "name": "convert_temperature",
        "description": (
            # [BEST PRACTICE 1] Input format specs with examples
            # The model has no prior knowledge of our API contract —
            # examples in the description are the only way it learns the expected shape.
            "Convert a temperature value between Celsius, Fahrenheit, and Kelvin scales.\n\n"
            "INPUT FORMAT EXAMPLES:\n"
            '  - convert_temperature(value=100, from_scale="C", to_scale="F")  => 212.0\n'
            '  - convert_temperature(value=32, from_scale="F", to_scale="C")   => 0.0\n'
            '  - convert_temperature(value=0, from_scale="C", to_scale="K")    => 273.15\n\n'
            # [BEST PRACTICE 2] Edge cases and boundary conditions
            # Without these, the model may pass physically impossible values
            # (e.g., -300 Kelvin) and expect a valid result.
            "EDGE CASES & BOUNDARY CONDITIONS:\n"
            "  - Absolute zero is the minimum: 0 K, -273.15 C, -459.67 F.\n"
            "    Values below absolute zero are physically impossible — return an error.\n"
            "  - Identical from_scale and to_scale is valid; returns the input value unchanged.\n"
            "  - Floating-point results are rounded to 2 decimal places.\n"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "value": {
                    # [BEST PRACTICE 3] Type, range, and constraint in the description
                    # JSON Schema 'type' alone isn't enough — the model needs
                    # human-readable guidance to pick sensible values.
                    "type": "number",
                    "description": (
                        "Numeric temperature value to convert. "
                        "Range: must be >= absolute zero for the given from_scale "
                        "(-273.15 for C, -459.67 for F, 0 for K). "
                        "Accepts integers or floats. Example: 100, -40, 273.15"
                    ),
                },
                "from_scale": {
                    "type": "string",
                    "enum": ["C", "F", "K"],
                    "description": (
                        "Source temperature scale. "
                        "Exactly one of: 'C' (Celsius), 'F' (Fahrenheit), 'K' (Kelvin). "
                        "Case-sensitive single uppercase letter."
                    ),
                },
                "to_scale": {
                    "type": "string",
                    "enum": ["C", "F", "K"],
                    "description": (
                        "Target temperature scale. "
                        "Exactly one of: 'C' (Celsius), 'F' (Fahrenheit), 'K' (Kelvin). "
                        "Case-sensitive single uppercase letter."
                    ),
                },
            },
            "required": ["value", "from_scale", "to_scale"],
        },
    },
    {
        "name": "lookup_product",
        # [BEST PRACTICE 4] Description as documentation
        # More detail is better — the model treats this as its sole reference
        # manual. Skimpy descriptions force the model to guess.
        "description": (
            "Look up product information by SKU code from the inventory catalog.\n\n"
            "WHAT THIS TOOL DOES:\n"
            "  Returns name, price (USD), and stock count for a single product.\n\n"
            "WHAT THIS TOOL DOES NOT DO:\n"
            "  - Does NOT search by product name (use search_products instead).\n"
            "  - Does NOT support bulk lookups; call once per SKU.\n"
            "  - Does NOT return historical pricing.\n\n"
            "INPUT FORMAT:\n"
            '  - SKU pattern: uppercase letters + digits, 6-10 chars. Example: "WIDGET001", "AB1234CDEF"\n'
            "  - An invalid SKU format returns a validation error before hitting the database.\n\n"
            "EDGE CASES:\n"
            "  - Unknown but validly-formatted SKU: returns {found: false} (not an error).\n"
            "  - Stock count of 0 means out-of-stock but the product exists.\n"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "sku": {
                    "type": "string",
                    "description": (
                        "Product SKU code. Must be 6-10 uppercase alphanumeric characters "
                        "matching the pattern [A-Z0-9]{6,10}. "
                        'Examples: "WIDGET001", "BOLT99X", "AB1234CDEF". '
                        "Lowercase input will be rejected."
                    ),
                }
            },
            "required": ["sku"],
        },
    },
]


# ── Simulated Tool Handlers ──────────────────────────────────────────────────

ABSOLUTE_ZERO = {"C": -273.15, "F": -459.67, "K": 0}


def handle_convert_temperature(value, from_scale, to_scale):
    if value < ABSOLUTE_ZERO[from_scale]:
        return {"error": f"Below absolute zero for {from_scale} scale"}

    if from_scale == to_scale:
        return {"result": value, "unit": to_scale}

    # Normalize to Celsius first — single pivot avoids a 3x3 conversion matrix
    if from_scale == "F":
        celsius = (value - 32) * 5 / 9
    elif from_scale == "K":
        celsius = value - 273.15
    else:
        celsius = value

    if to_scale == "F":
        result = celsius * 9 / 5 + 32
    elif to_scale == "K":
        result = celsius + 273.15
    else:
        result = celsius

    return {"result": round(result, 2), "unit": to_scale}


MOCK_CATALOG = {
    "WIDGET001": {"name": "Standard Widget", "price_usd": 9.99, "stock": 142},
    "BOLT99X": {"name": "Hex Bolt 99X", "price_usd": 0.50, "stock": 0},
}


def handle_lookup_product(sku):
    import re

    if not re.match(r"^[A-Z0-9]{6,10}$", sku):
        return {"error": f"Invalid SKU format: '{sku}'. Must be 6-10 uppercase alphanumeric chars."}

    product = MOCK_CATALOG.get(sku)
    if not product:
        return {"found": False, "sku": sku}

    return {"found": True, "sku": sku, **product}


def dispatch_tool(name, input_args):
    if name == "convert_temperature":
        return handle_convert_temperature(**input_args)
    elif name == "lookup_product":
        return handle_lookup_product(**input_args)
    return {"error": f"Unknown tool: {name}"}


# ── Agentic Loop ─────────────────────────────────────────────────────────────

def run_conversation(user_message: str):
    print(f"\n{'='*60}")
    print(f"USER: {user_message}")
    print(f"{'='*60}")

    messages = [{"role": "user", "content": user_message}]

    # Loop until the model stops requesting tools (stop_reason == "end_turn")
    while True:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            tools=tools,
            messages=messages,
        )

        # Collect any text the model emits alongside tool calls
        for block in response.content:
            if block.type == "text":
                print(f"\nASSISTANT: {block.text}")

        if response.stop_reason == "end_turn":
            break

        # Process every tool_use block in a single turn
        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                print(f"\n>> TOOL CALL: {block.name}({json.dumps(block.input)})")
                result = dispatch_tool(block.name, block.input)
                print(f"<< TOOL RESULT: {json.dumps(result)}")
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps(result),
                    }
                )

        # Feed both the assistant turn and tool results back — required by the API contract
        messages.append({"role": "assistant", "content": response.content})
        messages.append({"role": "user", "content": tool_results})


# ── Demo Prompts ─────────────────────────────────────────────────────────────
# Each prompt targets a different aspect of the tool descriptions
# so the examiner can observe how description quality shapes behavior.

if __name__ == "__main__":
    # 1. Basic conversion — model should use the examples from the description
    run_conversation("What is 100 degrees Celsius in Fahrenheit?")

    # 2. Edge case — absolute zero boundary; model should handle gracefully
    #    because the description explicitly documents this constraint
    run_conversation("Convert -500 Fahrenheit to Celsius.")

    # 3. Product lookup with valid SKU
    run_conversation("Look up the product with SKU WIDGET001.")

    # 4. Product lookup with invalid format — model should recognize the
    #    constraint from the description and either reject or let the tool validate
    run_conversation("Find product info for sku widget-001.")

    # 5. Edge case — out-of-stock product (stock == 0 is valid, not an error)
    run_conversation("Is BOLT99X in stock?")
