import json
import os
from anthropic import Anthropic

# tool_use forces Claude to respond ONLY via tool calls, guaranteeing JSON schema compliance
client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# The tool definition IS the schema contract — Claude must conform to this structure
extract_person_tool = {
    "name": "extract_person",
    "description": "Extract structured person information from unstructured text.",
    "input_schema": {
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": "Full name of the person"
            },
            "age": {
                "type": "integer",
                "description": "Age in years"
            },
            "occupation": {
                "type": "string",
                "description": "Current job title or role"
            },
            "skills": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of professional skills"
            }
        },
        # required fields ensure Claude never omits critical data
        "required": ["name", "age", "occupation", "skills"]
    }
}

unstructured_text = (
    "Meet Sarah Chen, a 34-year-old machine learning engineer. "
    "She excels at Python, TensorFlow, and distributed systems."
)

response = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=1024,
    # tool_choice="any" forces a tool call — prevents free-text responses entirely
    tool_choice={"type": "any"},
    tools=[extract_person_tool],
    messages=[
        {
            "role": "user",
            "content": f"Extract person details from: {unstructured_text}"
        }
    ]
)

# tool_use content blocks contain the schema-compliant JSON — no parsing guesswork
for block in response.content:
    if block.type == "tool_use":
        structured_data = block.input
        print("Structured Output (guaranteed schema-compliant):")
        print(json.dumps(structured_data, indent=2))
        print(f"\nTool called: {block.name}")
        print(f"Tool use ID: {block.id}")
