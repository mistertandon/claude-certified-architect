import anthropic
import json
import os
from dotenv import load_dotenv

load_dotenv()

# Structured output forces Claude to classify into discrete buckets
# rather than returning freeform sentiment text we'd have to parse again.
ESCALATION_SCHEMA = {
    "name": "classify_escalation",
    "description": "Classify a customer message for escalation triggers",
    "input_schema": {
        "type": "object",
        "properties": {
            "triggers_found": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "type": {
                            "type": "string",
                            # These categories map to real support workflows —
                            # sentiment alone can't distinguish "angry but handled"
                            # from "needs manager approval."
                            "enum": [
                                "legal_threat",
                                "regulatory_complaint",
                                "refund_beyond_policy",
                                "manager_demand",
                                "policy_gap",
                                "repeated_contact",
                                "churn_threat"
                            ]
                        },
                        "evidence": {
                            "type": "string",
                            "description": "Exact quote from the message"
                        },
                        "severity": {
                            "type": "string",
                            "enum": ["low", "medium", "high", "critical"]
                        }
                    },
                    "required": ["type", "evidence", "severity"]
                }
            },
            "should_escalate": {"type": "boolean"},
            "escalation_reason": {"type": "string"},
            "recommended_team": {
                "type": "string",
                # Routing to a team is the actionable output —
                # without it, "should_escalate=True" leaves agents guessing.
                "enum": ["tier1", "tier2_billing", "legal", "retention", "policy_review"]
            }
        },
        "required": ["triggers_found", "should_escalate", "escalation_reason", "recommended_team"]
    }
}

# System prompt encodes institutional knowledge about what actually
# requires escalation vs what a frontline agent can handle.
SYSTEM_PROMPT = """You are a support escalation classifier. Analyze customer messages
for triggers that require escalation BEYOND what a frontline agent can handle.

Focus on these trigger categories — not raw sentiment:

1. **Legal threats**: Mentions of lawyers, lawsuits, regulatory bodies, or formal complaints
2. **Regulatory complaints**: References to consumer protection, GDPR, FTC, or similar bodies
3. **Refund beyond policy**: Requests exceeding standard refund window or amount limits
4. **Manager demand**: Explicit requests to speak with supervisor/manager
5. **Policy gap**: Customer describes a scenario our policies don't cover
6. **Repeated contact**: Customer indicates they've contacted multiple times without resolution
7. **Churn threat**: Customer threatens to cancel or switch to a competitor

IMPORTANT: An angry customer is NOT automatically an escalation.
A calm customer requesting something outside policy IS an escalation.
Classify based on what ACTION is needed, not how the customer FEELS."""


# Each scenario tests a distinct trigger type so we can verify
# the classifier doesn't collapse everything into "angry customer."
TEST_MESSAGES = [
    {
        "id": "msg_001",
        "label": "Legal threat + regulatory",
        "message": "I've been waiting 3 weeks for my refund. If this isn't resolved by Friday, "
                   "I'm filing a complaint with the FTC and my attorney will be in touch. "
                   "This is a clear violation of consumer protection laws."
    },
    {
        "id": "msg_002",
        "label": "Policy gap (calm tone)",
        # This message is deliberately calm — proves we're not keying off sentiment.
        "message": "Hi, I purchased a gift subscription for my mother, but she passed away "
                   "last month. I'd like to transfer the remaining 8 months to my account "
                   "instead. I couldn't find any information about this in your FAQ."
    },
    {
        "id": "msg_003",
        "label": "Refund beyond policy + repeated contact",
        "message": "This is my FOURTH time contacting you about order #8821. I bought this "
                   "6 months ago and it broke after 2 uses. I know your return window is 30 days "
                   "but this is clearly a defective product. I need a full refund."
    },
    {
        "id": "msg_004",
        "label": "Angry but no escalation needed",
        # Control case: high emotion but entirely within frontline authority.
        "message": "This is ridiculous! I ordered the blue one and got red instead. "
                   "I want the correct item shipped to me ASAP. This is so frustrating!"
    },
    {
        "id": "msg_005",
        "label": "Manager demand + churn threat",
        "message": "I've been a customer for 7 years and I'm being charged more than new "
                   "customers. Let me speak to a manager. If you can't match the $9.99 promo "
                   "rate, I'm switching to CompetitorX today."
    }
]


def classify_message(client: anthropic.Anthropic, message: str) -> dict:
    # force_tool_use ensures we always get structured JSON back,
    # never a conversational reply we'd have to parse.
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        tools=[ESCALATION_SCHEMA],
        tool_choice={"type": "tool", "name": "classify_escalation"},
        messages=[{"role": "user", "content": message}]
    )

    for block in response.content:
        if block.type == "tool_use":
            return block.input
    return {}


def print_result(test_case: dict, result: dict):
    print(f"\n{'='*70}")
    print(f"Test: {test_case['label']} ({test_case['id']})")
    print(f"Message: {test_case['message'][:100]}...")
    print(f"-"*70)
    print(f"Should escalate: {result.get('should_escalate', 'N/A')}")
    print(f"Route to: {result.get('recommended_team', 'N/A')}")
    print(f"Reason: {result.get('escalation_reason', 'N/A')}")

    triggers = result.get("triggers_found", [])
    if triggers:
        print(f"\nTriggers detected ({len(triggers)}):")
        for t in triggers:
            print(f"  [{t['severity'].upper()}] {t['type']}: \"{t['evidence']}\"")
    else:
        print("\nNo escalation triggers detected.")


def main():
    client = anthropic.Anthropic()

    print("ESCALATION TRIGGER CLASSIFIER")
    print("Demonstrates: demand-based & policy-gap triggers, NOT sentiment-based")

    for test_case in TEST_MESSAGES:
        result = classify_message(client, test_case["message"])
        print_result(test_case, result)

    # Summary: proves the classifier distinguishes actionable triggers from emotion.
    print(f"\n{'='*70}")
    print("KEY INSIGHT: msg_004 (angry but simple) should NOT escalate,")
    print("while msg_002 (calm but policy gap) SHOULD escalate.")
    print("This proves trigger-based > sentiment-based classification.")


if __name__ == "__main__":
    main()
