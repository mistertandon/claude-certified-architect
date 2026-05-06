"""
Error Response Design Patterns — classifying API errors into semantic categories
so callers get structured, actionable feedback instead of raw HTTP codes.
"""

import os
import time
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Optional
import json

import anthropic
from dotenv import load_dotenv

load_dotenv()


# ── Error Category Taxonomy ──────────────────────────────────────────────────

class ErrorCategory(str, Enum):
    """Finite set of categories so consumers can switch on a known enum
    instead of parsing free-text messages."""
    VALIDATION = "validation"
    AUTH = "auth"
    NOT_FOUND = "not_found"
    RATE_LIMIT = "rate_limit"
    OVERLOAD = "overload"
    INTERNAL = "internal"
    TIMEOUT = "timeout"


# ── Structured Error Response ────────────────────────────────────────────────

@dataclass
class ErrorResponse:
    """Uniform envelope — every error surfaces the same shape regardless of
    origin, so downstream handlers never need to guess the schema."""
    error_category: ErrorCategory
    message: str
    status_code: Optional[int] = None
    # retryable flag lets callers decide retry logic without knowing HTTP semantics
    retryable: bool = False
    retry_after_seconds: Optional[float] = None
    details: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        result = asdict(self)
        result["error_category"] = self.error_category.value
        return result

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)


# ── Classifier: maps SDK exceptions → ErrorCategory ─────────────────────────

def classify_api_error(error: anthropic.APIError) -> ErrorResponse:
    """Single mapping point — all Anthropic SDK errors funnel through here,
    so category logic never leaks into business code."""

    status = getattr(error, "status_code", None)

    # 401 = bad/missing key; separated from 403 because remediation differs
    if isinstance(error, anthropic.AuthenticationError):
        return ErrorResponse(
            error_category=ErrorCategory.AUTH,
            message="Invalid or missing API key.",
            status_code=status,
            retryable=False,
            details={"hint": "Check ANTHROPIC_API_KEY in your .env file."},
        )

    # 403 = key is valid but lacks scope for this operation
    if isinstance(error, anthropic.PermissionDeniedError):
        return ErrorResponse(
            error_category=ErrorCategory.AUTH,
            message="API key lacks required permissions.",
            status_code=status,
            retryable=False,
            details={"hint": "Verify key scopes in the Anthropic console."},
        )

    # 400 = malformed request; surface the API's own validation message
    if isinstance(error, anthropic.BadRequestError):
        return ErrorResponse(
            error_category=ErrorCategory.VALIDATION,
            message=str(error),
            status_code=status,
            retryable=False,
            details={"raw_error": str(error)},
        )

    # 404 = wrong model name, deprecated endpoint, etc.
    if isinstance(error, anthropic.NotFoundError):
        return ErrorResponse(
            error_category=ErrorCategory.NOT_FOUND,
            message="Requested resource or model not found.",
            status_code=status,
            retryable=False,
        )

    # 429 = back off; retry-after header tells us how long
    if isinstance(error, anthropic.RateLimitError):
        retry_after = _extract_retry_after(error)
        return ErrorResponse(
            error_category=ErrorCategory.RATE_LIMIT,
            message="Rate limit exceeded.",
            status_code=status,
            retryable=True,
            retry_after_seconds=retry_after,
        )

    # 529 = Anthropic's servers are temporarily overloaded
    if isinstance(error, anthropic.APIStatusError) and status == 529:
        return ErrorResponse(
            error_category=ErrorCategory.OVERLOAD,
            message="Anthropic API is temporarily overloaded.",
            status_code=status,
            retryable=True,
            retry_after_seconds=30.0,
        )

    # 5xx catch-all — assume transient
    if isinstance(error, anthropic.InternalServerError):
        return ErrorResponse(
            error_category=ErrorCategory.INTERNAL,
            message="Anthropic internal server error.",
            status_code=status,
            retryable=True,
            retry_after_seconds=5.0,
        )

    # Fallback for any future exception subclass the SDK might add
    return ErrorResponse(
        error_category=ErrorCategory.INTERNAL,
        message=f"Unexpected API error: {error}",
        status_code=status,
        retryable=False,
    )


def _extract_retry_after(error: anthropic.APIError) -> Optional[float]:
    """Parse the retry-after header when present — callers shouldn't
    hardcode backoff if the server already told us when to come back."""
    headers = getattr(error, "response", None)
    if headers is not None:
        raw = getattr(headers, "headers", {}).get("retry-after")
        if raw:
            try:
                return float(raw)
            except ValueError:
                pass
    return 30.0  # safe default when header is absent


# ── Retry wrapper with category awareness ────────────────────────────────────

def call_with_retry(
    client: anthropic.Anthropic,
    max_retries: int = 3,
    **create_kwargs,
) -> dict:
    """Retries only when the classifier says the error is retryable —
    avoids wasting quota on 400s/401s that will never succeed."""

    for attempt in range(1, max_retries + 1):
        try:
            response = client.messages.create(**create_kwargs)
            return {
                "success": True,
                "content": response.content[0].text,
                "model": response.model,
                "usage": {
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens,
                },
            }

        except anthropic.APIError as exc:
            classified = classify_api_error(exc)
            print(f"  [attempt {attempt}/{max_retries}] {classified.error_category.value}: {classified.message}")

            # Non-retryable → fail fast; no point burning attempts
            if not classified.retryable or attempt == max_retries:
                return {"success": False, "error": classified.to_dict()}

            wait = classified.retry_after_seconds or (2 ** attempt)
            print(f"  Retrying in {wait}s ...")
            time.sleep(wait)

    # Unreachable but keeps the type checker happy
    return {"success": False, "error": {"message": "Exhausted retries"}}


# ── Demo scenarios ───────────────────────────────────────────────────────────

def demo_validation_error(client: anthropic.Anthropic) -> dict:
    """Triggers a 400 by sending an empty messages list —
    the API rejects it before any model invocation."""
    return call_with_retry(
        client,
        model="claude-sonnet-4-20250514",
        max_tokens=100,
        messages=[],  # intentionally invalid
    )


def demo_auth_error() -> dict:
    """Uses a bogus key so the API returns 401 immediately."""
    bad_client = anthropic.Anthropic(api_key="sk-ant-INVALID-KEY")
    return call_with_retry(
        bad_client,
        model="claude-sonnet-4-20250514",
        max_tokens=100,
        messages=[{"role": "user", "content": "Hello"}],
    )


def demo_not_found_error(client: anthropic.Anthropic) -> dict:
    """Requests a non-existent model to provoke a 404."""
    return call_with_retry(
        client,
        model="claude-nonexistent-model",
        max_tokens=100,
        messages=[{"role": "user", "content": "Hello"}],
    )


def demo_success(client: anthropic.Anthropic) -> dict:
    """Happy path — proves the same call_with_retry works for both
    success and failure without branching at the call site."""
    return call_with_retry(
        client,
        model="claude-sonnet-4-20250514",
        max_tokens=50,
        messages=[{"role": "user", "content": "Say 'Error handling works!' in one sentence."}],
    )


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    client = anthropic.Anthropic()

    scenarios = [
        ("1. Validation Error (empty messages)", lambda: demo_validation_error(client)),
        ("2. Auth Error (bad API key)",          lambda: demo_auth_error()),
        ("3. Not Found Error (bad model name)",  lambda: demo_not_found_error(client)),
        ("4. Successful Request",                lambda: demo_success(client)),
    ]

    for title, scenario_fn in scenarios:
        print(f"\n{'='*60}")
        print(f"  {title}")
        print(f"{'='*60}")
        result = scenario_fn()
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
