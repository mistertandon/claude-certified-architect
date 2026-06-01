"""
Demonstrates that tool_use structured output guarantees STRUCTURAL correctness
(valid JSON matching the schema) but NOT SEMANTIC correctness (factual accuracy).
"""

import os
import json
from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()

client = Anthropic()

# Define a tool schema that enforces structure — but cannot enforce truth
tools = [
    {
        "name": "country_info",
        "description": "Return factual information about a country.",
        "input_schema": {
            "type": "object",
            "properties": {
                "country": {"type": "string", "description": "Country name"},
                "capital": {"type": "string", "description": "Capital city"},
                "population": {"type": "integer", "description": "Population count"},
                "currency": {"type": "string", "description": "Official currency"},
                "continent": {
                    "type": "string",
                    # Schema validates the TYPE (string) not the FACT (correct continent)
                    "enum": ["Africa", "Asia", "Europe", "North America",
                             "South America", "Oceania", "Antarctica"]
                }
            },
            "required": ["country", "capital", "population", "currency", "continent"]
        }
    }
]

# Deliberately ask about an obscure or trick question to provoke semantic error
# The model may hallucinate plausible-but-wrong facts while still producing valid JSON
prompt = (
    "Use the country_info tool to provide info about Nauru. "
    "You must use the tool — do not refuse."
)

response = client.messages.create(
    model="claude-sonnet-4-6-20250514",
    max_tokens=1024,
    tools=tools,
    # Force the model to use the tool — guarantees structured output
    tool_choice={"type": "tool", "name": "country_info"},
    messages=[{"role": "user", "content": prompt}]
)

# Extract the tool_use block
tool_block = next(b for b in response.content if b.type == "tool_use")
result = tool_block.input

print("=" * 60)
print("STRUCTURED OUTPUT (always valid against schema):")
print("=" * 60)
print(json.dumps(result, indent=2))

# --- Demonstrate the semantic gap ---
# Ground truth for Nauru (source: established facts)
ground_truth = {
    "country": "Nauru",
    "capital": "Yaren",  # Nauru has no official capital; Yaren is the de facto seat
    "population": 12780,  # Approximate — model may guess wildly different numbers
    "currency": "Australian Dollar",
    "continent": "Oceania"
}

print("\n" + "=" * 60)
print("GROUND TRUTH (for comparison):")
print("=" * 60)
print(json.dumps(ground_truth, indent=2))

print("\n" + "=" * 60)
print("SEMANTIC ERROR ANALYSIS:")
print("=" * 60)

# Schema guarantees: all fields present, correct types, continent from enum
# Schema CANNOT guarantee: capital is correct, population is accurate, etc.
errors_found = False
for key in ground_truth:
    model_val = result.get(key)
    truth_val = ground_truth[key]

    if key == "population":
        # Population is approximate — flag if off by more than 50%
        if abs(model_val - truth_val) / truth_val > 0.5:
            print(f"  [SEMANTIC ERROR] {key}: model={model_val}, truth≈{truth_val}")
            errors_found = True
    elif str(model_val).lower() != str(truth_val).lower():
        print(f"  [SEMANTIC ERROR] {key}: model='{model_val}', truth='{truth_val}'")
        errors_found = True

if not errors_found:
    print("  No semantic errors detected in this run (model got lucky).")
    print("  Re-run with a more obscure country to trigger semantic errors.")

print("\n" + "=" * 60)
print("KEY TAKEAWAY:")
print("=" * 60)
print("""
  tool_use guarantees:
    ✓ Valid JSON
    ✓ All required fields present
    ✓ Correct types (string, integer, enum values)

  tool_use does NOT guarantee:
    ✗ Factual accuracy of values
    ✗ Logical consistency between fields
    ✗ Real-world correctness

  → Structure ≠ Semantics. Always validate MEANING, not just SHAPE.
""")
