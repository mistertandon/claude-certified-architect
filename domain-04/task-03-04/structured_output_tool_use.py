"""
POC: Structured Output via tool_use — Schema Design Patterns
Demonstrates: required vs optional fields, enums with 'other' + detail, nullable fields
"""

import os
import json
from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()

client = Anthropic()

# The tool schema IS the structured output contract — Claude must conform to it
classify_incident_tool = {
    "name": "classify_incident",
    "description": "Classify a customer support incident into structured fields.",
    "input_schema": {
        "type": "object",
        "properties": {
            # REQUIRED field — always present, model must extract or infer
            "summary": {
                "type": "string",
                "description": "One-line summary of the incident"
            },
            # ENUM field — constrains model output to known categories
            "severity": {
                "type": "string",
                "enum": ["low", "medium", "high", "critical"],
                "description": "Impact severity level"
            },
            # ENUM WITH 'other' + detail pattern — allows escape hatch without losing structure
            "category": {
                "type": "string",
                "enum": ["billing", "authentication", "performance", "data_loss", "other"],
                "description": "Primary incident category. Use 'other' only if none fit."
            },
            # Companion field for 'other' — only meaningful when category=other
            "category_detail": {
                "type": "string",
                "description": "Required explanation when category is 'other'. Null otherwise."
            },
            # NULLABLE field — explicitly allows null to represent absence of data
            "resolved_at": {
                "type": ["string", "null"],  # JSON Schema nullable pattern
                "description": "ISO timestamp when resolved, or null if still open"
            },
            # OPTIONAL field — omitted from 'required' so model can skip if info unavailable
            "affected_user_count": {
                "type": "integer",
                "description": "Number of users affected, if known"
            },
            # Boolean required field — forces a yes/no decision from the model
            "requires_followup": {
                "type": "boolean",
                "description": "Whether this incident needs a follow-up action"
            }
        },
        # Only list fields the model MUST always produce — optional fields excluded
        "required": ["summary", "severity", "category", "requires_followup", "resolved_at"]
    }
}

def extract_structured_incident(description: str) -> dict:
    """Force Claude to produce structured output by making tool_use the only option."""

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        # tool_choice="any" forces tool call — no free-text escape route
        tool_choice={"type": "any"},
        tools=[classify_incident_tool],
        messages=[
            {
                "role": "user",
                "content": f"Classify this incident:\n\n{description}"
            }
        ]
    )

    # With tool_choice="any", first content block is guaranteed to be tool_use
    tool_block = next(b for b in response.content if b.type == "tool_use")
    return tool_block.input


if __name__ == "__main__":
    # Test case 1: Standard category — exercises required + enum fields
    incident_1 = """
    Customer reports they've been double-charged for their Pro subscription
    for the last 3 months. 47 other users reported similar issues.
    Issue was fixed today at 2024-03-15T14:30:00Z.
    """

    # Test case 2: 'other' category — exercises the enum escape hatch + detail field
    incident_2 = """
    Our office WiFi router caught fire during a firmware update.
    No users are affected yet but the entire dev team lost internet access.
    Still ongoing.
    """

    print("=" * 60)
    print("INCIDENT 1 — Standard category (billing)")
    print("=" * 60)
    result_1 = extract_structured_incident(incident_1)
    print(json.dumps(result_1, indent=2))

    print("\n" + "=" * 60)
    print("INCIDENT 2 — 'Other' category with detail")
    print("=" * 60)
    result_2 = extract_structured_incident(incident_2)
    print(json.dumps(result_2, indent=2))

    # Validate schema contract adherence
    print("\n" + "=" * 60)
    print("SCHEMA VALIDATION")
    print("=" * 60)
    required_fields = ["summary", "severity", "category", "requires_followup", "resolved_at"]
    for field in required_fields:
        present = field in result_1
        print(f"  {field}: {'PRESENT' if present else 'MISSING'}")

    # Show nullable field behavior
    print(f"\n  resolved_at in incident_2 is None: {result_2.get('resolved_at') is None}")
    # Show optional field behavior
    print(f"  affected_user_count in incident_2 omitted: {'affected_user_count' not in result_2}")
