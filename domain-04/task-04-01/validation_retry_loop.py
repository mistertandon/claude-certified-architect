"""
Validation-Retry Loop Pattern:
When Claude's output fails validation, append the specific error
back into the conversation so the model can self-correct.
"""

import json
import os
from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()

client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
MODEL = "claude-sonnet-4-6"
MAX_RETRIES = 3


def validate_response(text: str) -> tuple[bool, str]:
    """Validate that the model returned well-formed JSON with required fields."""
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        # Return the exact parse error so the model knows what to fix
        return False, f"Invalid JSON: {e}"

    required_fields = ["name", "age", "hobbies"]
    missing = [f for f in required_fields if f not in data]
    if missing:
        return False, f"Missing required fields: {missing}"

    if not isinstance(data["hobbies"], list):
        return False, "Field 'hobbies' must be a JSON array, not a string."

    if not isinstance(data["age"], int):
        return False, "Field 'age' must be an integer."

    return True, ""


def run_validation_retry_loop():
    # Seed the conversation with the task instruction
    messages = [
        {
            "role": "user",
            "content": (
                "Generate a JSON object for a fictional person with fields: "
                "name (string), age (integer), hobbies (array of strings). "
                "Return ONLY raw JSON, no markdown fences."
            ),
        }
    ]

    for attempt in range(1, MAX_RETRIES + 1):
        print(f"\n--- Attempt {attempt}/{MAX_RETRIES} ---")

        response = client.messages.create(
            model=MODEL,
            max_tokens=300,
            messages=messages,
        )

        assistant_text = response.content[0].text
        print(f"Model output:\n{assistant_text}")

        is_valid, error_msg = validate_response(assistant_text)

        if is_valid:
            print(f"\nValidation passed on attempt {attempt}.")
            return json.loads(assistant_text)

        print(f"Validation failed: {error_msg}")

        # Append assistant reply so context stays coherent for multi-turn
        messages.append({"role": "assistant", "content": assistant_text})

        # Append the SPECIFIC error — this is the core of the pattern:
        # the model sees exactly what went wrong and can self-correct
        messages.append(
            {
                "role": "user",
                "content": (
                    f"Your previous response failed validation:\n"
                    f"ERROR: {error_msg}\n\n"
                    f"Please fix the issue and return ONLY valid raw JSON."
                ),
            }
        )

    print("\nAll retries exhausted. Validation never passed.")
    return None


if __name__ == "__main__":
    result = run_validation_retry_loop()
    if result:
        print(f"\nFinal validated result:\n{json.dumps(result, indent=2)}")
