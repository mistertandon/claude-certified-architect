"""
POC: Access Failures vs Empty Results
─────────────────────────────────────
Demonstrates the critical distinction between:
  - "Could not check" (access failure → raise/propagate error)
  - "Checked and found nothing" (empty result → return empty collection)

Conflating these two states causes silent data loss in production systems.
"""

import os
from dataclasses import dataclass
from dotenv import load_dotenv
from anthropic import Anthropic, APIConnectionError, AuthenticationError, APIStatusError

load_dotenv()


@dataclass
class SearchResult:
    """Wraps results to distinguish 'nothing found' from 'could not search'."""
    items: list[str]
    searched_successfully: bool
    error_reason: str | None = None


def search_with_claude(client: Anthropic, query: str) -> SearchResult:
    """Ask Claude to search — returns structured result preserving failure semantics."""
    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=300,
            messages=[{"role": "user", "content": f"List items matching: '{query}'. If none match, reply ONLY with: EMPTY_RESULT"}],
        )

        text = response.content[0].text.strip()

        if text == "EMPTY_RESULT":
            # Signal: search executed successfully, zero matches found
            return SearchResult(items=[], searched_successfully=True)

        return SearchResult(items=[text], searched_successfully=True)

    except AuthenticationError:
        # Access failure: credentials invalid — we never reached the search
        return SearchResult(items=[], searched_successfully=False, error_reason="AUTH_FAILED")

    except APIConnectionError:
        # Access failure: network issue — we cannot confirm absence of results
        return SearchResult(items=[], searched_successfully=False, error_reason="CONNECTION_FAILED")

    except APIStatusError as e:
        # Access failure: API-level rejection (rate limit, server error, etc.)
        return SearchResult(items=[], searched_successfully=False, error_reason=f"API_ERROR_{e.status_code}")


def handle_result(result: SearchResult, context: str) -> None:
    """
    Downstream consumer MUST branch on searched_successfully first.
    Treating both states as 'empty' silently drops error signals.
    """
    print(f"\n{'─' * 50}")
    print(f"Context: {context}")

    if not result.searched_successfully:
        # CRITICAL: propagate failure — caller must retry or alert
        print(f"⚠ ACCESS FAILURE: {result.error_reason}")
        print("  → Cannot assert 'nothing exists' — search never completed")
        print("  → Action: retry, escalate, or degrade gracefully")
    elif not result.items:
        # Safe: we checked and confirmed nothing matches
        print("✓ EMPTY RESULT: search completed, zero matches")
        print("  → Safe to proceed assuming absence")
    else:
        print(f"✓ FOUND: {result.items}")


def demo_access_failure():
    """Simulate access failure using intentionally bad credentials."""
    # Bad key guarantees AuthenticationError — proves we detect 'could not check'
    bad_client = Anthropic(api_key="sk-ant-invalid-key-00000000")

    result = search_with_claude(bad_client, "test query")
    handle_result(result, "Bad API key → access failure")


def demo_empty_result():
    """Demonstrate legitimate empty result with valid credentials."""
    api_key = os.getenv("ANTHROPIC_API_KEY")

    if not api_key or api_key == "your-api-key-here":
        # Simulate what a successful-but-empty response looks like
        print("\n[Simulated] Using mock for empty-result demo (no valid key)")
        result = SearchResult(items=[], searched_successfully=True)
        handle_result(result, "Valid credentials, query matched nothing")
        return

    client = Anthropic(api_key=api_key)
    # Absurd query ensures Claude returns EMPTY_RESULT
    result = search_with_claude(client, "purple elephants dancing on Mars in 1742")
    handle_result(result, "Valid credentials, query matched nothing")


def demo_successful_result():
    """Demonstrate a query that returns actual results."""
    api_key = os.getenv("ANTHROPIC_API_KEY")

    if not api_key or api_key == "your-api-key-here":
        print("\n[Simulated] Using mock for success demo (no valid key)")
        result = SearchResult(items=["Python", "JavaScript", "Go"], searched_successfully=True)
        handle_result(result, "Valid credentials, query matched items")
        return

    client = Anthropic(api_key=api_key)
    result = search_with_claude(client, "Name 3 popular programming languages")
    handle_result(result, "Valid credentials, query matched items")


if __name__ == "__main__":
    print("=" * 50)
    print("ACCESS FAILURES vs EMPTY RESULTS")
    print("=" * 50)

    # Case 1: Access failure — we CANNOT conclude 'nothing exists'
    demo_access_failure()

    # Case 2: Empty result — we CAN safely conclude 'nothing exists'
    demo_empty_result()

    # Case 3: Successful result — baseline for comparison
    demo_successful_result()

    print(f"\n{'─' * 50}")
    print("\nKEY TAKEAWAY:")
    print("  [] empty after failure ≠ [] empty after success")
    print("  The SAME data structure (empty list) has DIFFERENT semantics")
    print("  depending on whether the lookup itself succeeded.")
