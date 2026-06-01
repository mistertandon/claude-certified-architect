"""
POC: Trimming Verbose Tool Outputs
===================================
Demonstrates how trimming noisy tool results before injecting them back
into the conversation preserves essential data while cutting token waste.
"""

import os
import json
from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()

# Reuse a single client for connection pooling across all API calls.
client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

MODEL = "claude-sonnet-4-20250514"

# --- Simulated tool: a customer-lookup API that returns far more data than
# the model actually needs to answer user questions. Real-world APIs
# (Salesforce, Stripe, internal CRMs) routinely return 50+ fields. ---

VERBOSE_TOOL_OUTPUT = {
    "status": 200,
    "request_id": "req_8f3a2b1c-9d4e-4f5a-b6c7-d8e9f0a1b2c3",
    "timestamp": "2025-04-22T14:33:07.442Z",
    "rate_limit_remaining": 847,
    "rate_limit_reset": "2025-04-22T15:00:00Z",
    "server": "api-prod-us-east-2b",
    "version": "v3.14.2",
    "cache_hit": False,
    "response_time_ms": 142,
    "data": {
        "customer": {
            "id": "cust_90X2kL",
            "created_at": "2023-06-14T09:22:11Z",
            "updated_at": "2025-04-20T11:05:33Z",
            "name": "Priya Sharma",
            "email": "priya.sharma@example.com",
            "phone": "+1-503-555-0182",
            "status": "active",
            "tier": "enterprise",
            "account_manager": "David Kim",
            "region": "us-west",
            "timezone": "America/Los_Angeles",
            "locale": "en-US",
            "avatar_url": "https://cdn.example.com/avatars/90X2kL.jpg",
            "two_factor_enabled": True,
            "last_login": "2025-04-21T08:12:44Z",
            "login_count": 342,
            "ip_address": "203.0.113.42",
            "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
            "subscription": {
                "plan": "Enterprise Annual",
                "price_cents": 499900,
                "currency": "USD",
                "billing_cycle": "annual",
                "started_at": "2024-01-15",
                "renews_at": "2026-01-15",
                "payment_method": "card_ending_4242",
                "last_payment_date": "2025-01-15",
                "last_payment_amount_cents": 499900,
                "auto_renew": True,
                "discount_code": None,
                "tax_id": "US-EIN-12-3456789",
                "invoice_email": "billing@sharma-consulting.com",
            },
            "usage": {
                "api_calls_this_month": 48210,
                "api_calls_limit": 100000,
                "storage_used_gb": 23.7,
                "storage_limit_gb": 100,
                "seats_used": 8,
                "seats_limit": 15,
                "bandwidth_used_gb": 156.3,
                "bandwidth_limit_gb": 500,
                "last_api_call": "2025-04-22T14:30:12Z",
            },
            "feature_flags": {
                "beta_dashboard_v2": True,
                "new_billing_ui": False,
                "advanced_analytics": True,
                "custom_domains": True,
                "sso_enabled": True,
            },
            "internal_notes": [
                {"date": "2024-03-10", "author": "support-bot", "note": "Auto-upgraded from Pro tier"},
                {"date": "2024-11-22", "author": "d.kim", "note": "Discussed custom SLA terms"},
                {"date": "2025-02-14", "author": "d.kim", "note": "Renewal confirmed, happy with service"},
            ],
            "audit_log_url": "https://admin.internal/audit/cust_90X2kL",
        }
    },
    "_links": {
        "self": "/v3/customers/cust_90X2kL",
        "invoices": "/v3/customers/cust_90X2kL/invoices",
        "tickets": "/v3/customers/cust_90X2kL/tickets",
        "usage_history": "/v3/customers/cust_90X2kL/usage",
    },
}

# Only the fields the model needs to answer user-facing questions.
# Everything else — request metadata, internal URLs, feature flags,
# audit logs — is noise that burns tokens and dilutes attention.
TRIMMED_FIELDS = {
    "customer": ["name", "email", "phone", "status", "tier", "account_manager"],
    "subscription": ["plan", "price_cents", "currency", "renews_at", "auto_renew"],
    "usage": [
        "api_calls_this_month", "api_calls_limit",
        "storage_used_gb", "storage_limit_gb",
        "seats_used", "seats_limit",
    ],
}


def trim_tool_output(raw: dict, field_spec: dict) -> dict:
    """Strip a verbose API response down to the fields the model needs.

    Operates on a whitelist basis — unlisted fields are dropped, not
    selectively removed. Whitelisting is safer than blacklisting because
    new fields added upstream are excluded by default.
    """
    cust = raw["data"]["customer"]

    trimmed = {}

    for section, keys in field_spec.items():
        # Each section maps to either the top-level customer dict or a
        # nested sub-object (subscription, usage). The fallback to cust
        # handles the top-level "customer" section itself.
        source = cust.get(section, cust)
        trimmed[section] = {k: source[k] for k in keys if k in source}

    return trimmed


def ask_with_tool_result(tool_output: dict, label: str) -> dict:
    """Send a customer question to Claude, injecting the tool output
    as if a tool call had returned it.

    Returns the response text and token usage so we can compare the
    cost of verbose vs trimmed approaches side by side.
    """
    # Simulate the agentic loop: model called a tool, we're injecting
    # the result back. In production this would be inside the tool-use
    # message cycle; here we inline it for clarity.
    tool_result_json = json.dumps(tool_output, indent=2)

    response = client.messages.create(
        model=MODEL,
        max_tokens=300,
        system=(
            "You are a customer support assistant. A tool has returned "
            "customer data below. Answer the user's question using ONLY "
            "this data. Be concise."
        ),
        messages=[
            {
                "role": "user",
                "content": (
                    f"Tool result:\n```json\n{tool_result_json}\n```\n\n"
                    "Question: What plan is Priya on, when does it renew, "
                    "and how much of her API quota has she used?"
                ),
            }
        ],
    )

    return {
        "label": label,
        "answer": response.content[0].text,
        "input_tokens": response.usage.input_tokens,
        "output_tokens": response.usage.output_tokens,
        "tool_result_chars": len(tool_result_json),
    }


def run_comparison():
    """Run the same question with verbose vs trimmed tool output and
    compare token cost and answer quality."""

    print("=" * 72)
    print("  TRIMMING VERBOSE TOOL OUTPUTS — COST & QUALITY COMPARISON")
    print("=" * 72)

    raw_json = json.dumps(VERBOSE_TOOL_OUTPUT, indent=2)
    trimmed = trim_tool_output(VERBOSE_TOOL_OUTPUT, TRIMMED_FIELDS)
    trimmed_json = json.dumps(trimmed, indent=2)

    print(f"\n  Verbose tool output : {len(raw_json):>6} chars")
    print(f"  Trimmed tool output : {len(trimmed_json):>6} chars")
    print(f"  Reduction           : {(1 - len(trimmed_json)/len(raw_json))*100:.0f}%")

    # --- Phase 1: Verbose (raw API response passed straight through) ---
    print("\n" + "-" * 72)
    print("PHASE 1: Verbose tool output (full API response)")
    print("-" * 72)

    verbose_result = ask_with_tool_result(VERBOSE_TOOL_OUTPUT, "verbose")

    print(f"\n  Input tokens : {verbose_result['input_tokens']}")
    print(f"  Output tokens: {verbose_result['output_tokens']}")
    print(f"\n  Answer:\n  {verbose_result['answer']}")

    # --- Phase 2: Trimmed (only whitelisted fields) ---
    print("\n" + "-" * 72)
    print("PHASE 2: Trimmed tool output (whitelisted fields only)")
    print("-" * 72)

    trimmed_result = ask_with_tool_result(trimmed, "trimmed")

    print(f"\n  Input tokens : {trimmed_result['input_tokens']}")
    print(f"  Output tokens: {trimmed_result['output_tokens']}")
    print(f"\n  Answer:\n  {trimmed_result['answer']}")

    # --- Comparison ---
    print("\n" + "=" * 72)
    print("  RESULTS SUMMARY")
    print("=" * 72)

    token_saved = verbose_result["input_tokens"] - trimmed_result["input_tokens"]
    token_pct = (token_saved / verbose_result["input_tokens"]) * 100

    print(f"""
  Metric                Verbose     Trimmed     Saved
  ───────────────────   ─────────   ─────────   ─────────
  Tool output chars     {verbose_result['tool_result_chars']:>9}   {trimmed_result['tool_result_chars']:>9}   {verbose_result['tool_result_chars'] - trimmed_result['tool_result_chars']:>9}
  Input tokens          {verbose_result['input_tokens']:>9}   {trimmed_result['input_tokens']:>9}   {token_saved:>9}
  Token reduction                               {token_pct:>8.1f}%
""")

    # --- Takeaways ---
    print("=" * 72)
    print("  WHY TRIMMING TOOL OUTPUTS MATTERS")
    print("=" * 72)
    print("""
  1. TOKEN COST — Verbose API responses pad every turn with metadata
     (request IDs, rate limits, HATEOAS links) that the model never
     uses. Trimming cuts input tokens proportionally.

  2. ATTENTION DILUTION — The model's attention is finite. Irrelevant
     fields compete with relevant ones for weight in the attention
     mechanism, potentially degrading answer quality.

  3. CONTEXT WINDOW BUDGET — In agentic loops with many tool calls,
     untrimmed outputs accumulate fast. Trimming extends the number
     of tool-call rounds before hitting the context limit.

  4. SECURITY — Stripping internal fields (audit_log_url, ip_address,
     internal_notes) prevents accidental leakage to end users through
     the model's response.

  EXAM TIP: Trim tool outputs via a whitelist (keep only what's needed)
  rather than a blacklist (remove what's not needed). Whitelists are
  safer because new fields added to the upstream API are excluded by
  default, preventing both token waste and data leakage.
""")


if __name__ == "__main__":
    run_comparison()
