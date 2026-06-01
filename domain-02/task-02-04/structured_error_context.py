"""
Structured Error Context Pattern — surfaces WHAT was attempted and WHY it failed,
so callers get actionable diagnostics instead of opaque tracebacks.
"""

import json
import time
import anthropic
from dataclasses import dataclass, field, asdict
from dotenv import load_dotenv

load_dotenv()


# --- 1. Structured error envelope ---

@dataclass
class ErrorContext:
    """Carries machine-readable context alongside every failure."""
    operation: str          # what the caller asked for ("summarize_text")
    phase: str              # where it broke ("api_call", "response_parse", "validation")
    error_type: str         # classify without coupling to Python exception names
    message: str            # human sentence explaining the failure
    attempted_input: dict = field(default_factory=dict)   # redacted snapshot of what was sent
    retry_eligible: bool = False  # lets callers decide without inspecting internals
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        # JSON serialization keeps the error portable across service boundaries
        return json.dumps(self.to_dict(), indent=2, default=str)


# --- 2. Classifiers that map raw exceptions to structured context ---

def _classify_api_error(err: anthropic.APIError, operation: str, attempted_input: dict) -> ErrorContext:
    """Single place to decide retry eligibility — keeps policy out of business logic."""

    # Status-based classification mirrors Anthropic's documented retry guidance
    status = getattr(err, "status_code", None)

    if status == 401:
        return ErrorContext(
            operation=operation,
            phase="api_call",
            error_type="authentication_error",
            message="API key is invalid or missing. Check ANTHROPIC_API_KEY.",
            attempted_input=attempted_input,
            retry_eligible=False,  # retrying won't fix a bad key
        )

    if status == 429:
        return ErrorContext(
            operation=operation,
            phase="api_call",
            error_type="rate_limit_error",
            message="Rate limit hit. Back off and retry.",
            attempted_input=attempted_input,
            retry_eligible=True,  # transient by nature
        )

    if status == 529:
        return ErrorContext(
            operation=operation,
            phase="api_call",
            error_type="overloaded_error",
            message="Anthropic API is temporarily overloaded.",
            attempted_input=attempted_input,
            retry_eligible=True,
        )

    # Catch-all for unexpected status codes
    return ErrorContext(
        operation=operation,
        phase="api_call",
        error_type="api_error",
        message=str(err),
        attempted_input=attempted_input,
        retry_eligible=(status is not None and status >= 500),  # 5xx are usually transient
    )


# --- 3. Application-level operation that returns structured results OR errors ---

def summarize_text(text: str, max_tokens: int = 256) -> dict:
    """
    Returns a dict with either {"result": ...} or {"error": ErrorContext}.
    Callers never need to catch exceptions — the contract is always a dict.
    """
    operation = "summarize_text"
    # Redact long inputs so error logs stay readable
    attempted_input = {"text_length": len(text), "max_tokens": max_tokens}

    # Phase: input validation — fail fast before spending an API call
    if not text or not text.strip():
        return {
            "error": ErrorContext(
                operation=operation,
                phase="validation",
                error_type="invalid_input",
                message="Input text is empty. Nothing to summarize.",
                attempted_input=attempted_input,
                retry_eligible=False,  # same input will always fail
            ).to_dict()
        }

    client = anthropic.Anthropic()

    # Phase: API call — network and auth failures surface here
    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": f"Summarize in one paragraph:\n\n{text}"}],
        )
    except anthropic.APIError as err:
        ctx = _classify_api_error(err, operation, attempted_input)
        return {"error": ctx.to_dict()}
    except Exception as err:
        # Non-API failures (DNS, TLS, timeout) get their own phase
        return {
            "error": ErrorContext(
                operation=operation,
                phase="api_call",
                error_type="connection_error",
                message=f"Could not reach the API: {err}",
                attempted_input=attempted_input,
                retry_eligible=True,  # network issues are usually transient
            ).to_dict()
        }

    # Phase: response parsing — guard against unexpected shapes
    try:
        content_block = response.content[0]
        summary = content_block.text
    except (IndexError, AttributeError) as err:
        return {
            "error": ErrorContext(
                operation=operation,
                phase="response_parse",
                error_type="malformed_response",
                message=f"Response had unexpected structure: {err}",
                attempted_input=attempted_input,
                retry_eligible=True,  # might succeed on a second call
            ).to_dict()
        }

    return {"result": summary}


# --- 4. Demo runner ---

def main():
    scenarios = [
        ("empty_input", ""),
        ("valid_input", "Artificial intelligence is transforming industries worldwide."),
    ]

    for label, text in scenarios:
        print(f"\n{'='*60}")
        print(f"Scenario: {label}")
        print(f"{'='*60}")

        outcome = summarize_text(text)

        if "error" in outcome:
            print("[ERROR] Structured error context:")
            print(json.dumps(outcome["error"], indent=2, default=str))
        else:
            print(f"[OK] Summary: {outcome['result']}")


if __name__ == "__main__":
    main()
