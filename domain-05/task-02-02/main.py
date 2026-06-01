"""
POC: Structured Error Context vs Generic Errors
Principle: Always include WHAT was attempted when raising/handling errors.
"""

import os
from dataclasses import dataclass, field
from dotenv import load_dotenv
from anthropic import Anthropic, APIError, AuthenticationError

load_dotenv()


# --- ANTI-PATTERN: Generic error handling ---

def generic_error_approach(prompt: str) -> str:
    """Loses all context about what was being attempted."""
    client = Anthropic()
    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=100,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text
    except Exception as e:
        # BAD: caller has no idea what operation failed or what inputs caused it
        raise Exception(f"Something went wrong: {e}")


# --- PATTERN: Structured error context ---

@dataclass
class OperationContext:
    """Captures the full context of what was attempted — enables debugging without reproducing."""
    operation: str
    model: str
    prompt_preview: str
    max_tokens: int
    metadata: dict = field(default_factory=dict)


class StructuredAPIError(Exception):
    """Wraps the original error with the operation context that produced it."""

    def __init__(self, message: str, context: OperationContext, cause: Exception):
        # Preserves the chain so root cause is never lost
        super().__init__(message)
        self.context = context
        self.cause = cause

    def __str__(self):
        return (
            f"[{self.context.operation}] {self.__cause__}\n"
            f"  model: {self.context.model}\n"
            f"  prompt: \"{self.context.prompt_preview}...\"\n"
            f"  max_tokens: {self.context.max_tokens}\n"
            f"  metadata: {self.context.metadata}"
        )


def structured_error_approach(prompt: str, user_id: str = "anonymous") -> str:
    """Attaches full operation context so any failure is immediately actionable."""
    client = Anthropic()
    model = "claude-sonnet-4-20250514"
    max_tokens = 100

    # Build context BEFORE the call — if it fails, we already have the evidence
    context = OperationContext(
        operation="message_create",
        model=model,
        prompt_preview=prompt[:50],
        max_tokens=max_tokens,
        metadata={"user_id": user_id},
    )

    try:
        response = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text

    except AuthenticationError as e:
        # Specific exception type lets callers handle auth vs rate-limit differently
        raise StructuredAPIError(
            "Authentication failed — check API key", context, cause=e
        ) from e

    except APIError as e:
        # SDK errors carry status_code; we attach our context on top
        raise StructuredAPIError(
            f"API returned {e.status_code}", context, cause=e
        ) from e

    except Exception as e:
        # Catch-all still preserves context — never swallow the "what"
        raise StructuredAPIError(
            "Unexpected failure during API call", context, cause=e
        ) from e


# --- Demo ---

if __name__ == "__main__":
    test_prompt = "Explain structured error handling in one sentence."

    print("=" * 60)
    print("1) GENERIC ERROR (anti-pattern)")
    print("=" * 60)
    try:
        generic_error_approach(test_prompt)
    except Exception as e:
        # Notice: no way to know what model, prompt, or operation failed
        print(f"  Caught: {e}\n")

    print("=" * 60)
    print("2) STRUCTURED ERROR (recommended)")
    print("=" * 60)
    try:
        structured_error_approach(test_prompt, user_id="user-42")
    except StructuredAPIError as e:
        # Full context: operation, model, prompt snippet, metadata — all in one place
        print(f"  Caught:\n  {e}\n")
        print(f"  Root cause type: {type(e.cause).__name__}")
