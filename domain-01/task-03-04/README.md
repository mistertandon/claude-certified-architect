# Task 03-04: Hook-Based Blocking for Refund Escalation

## Concept

Pre-execution **hooks** intercept tool calls before they run, enforcing hard constraints in code rather than in prompts. This makes guardrails immune to prompt injection and social engineering — Claude literally cannot bypass a code-level block.

## Key Architectural Insight

| Approach | Where | Bypassable? | Use Case |
|---|---|---|---|
| Prompt instruction | System prompt | Yes (jailbreak) | Soft preferences, tone |
| Hook-based blocking | Application code | No | Safety-critical limits |

```
User request
    |
    v
Claude selects tool ──> HOOK intercepts ──> Allowed? ──> Execute tool
                                               |
                                               No
                                               |
                                          Block + Redirect
                                               |
                                          escalate_to_manager
```

## Setup

```bash
cd domain-01/task-03-04

# 1. Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 2. Install dependencies
pip install anthropic python-dotenv

# 3. Configure API key
cp .env .env.local
# Edit .env.local and replace 'your-api-key-here' with your actual key
```

## Run

```bash
python hook_based_blocking.py
```

## Expected Output

**Case 1 — $150 refund (under $500 limit):**
```
Customer: Hi, I'm customer C-1234. I'd like a $150 refund for a defective product.
-> Tool call: process_refund({"customer_id": "C-1234", "amount": 150, ...})
   ALLOWED -> {"status": "approved", "refund_id": "RF-20260506", "amount": 150}
Agent: Your $150 refund has been processed successfully...
```

**Case 2 — $750 refund (over $500 limit):**
```
Customer: Hello, customer C-5678 here. Please refund $750 for my cancelled subscription.
-> Tool call: process_refund({"customer_id": "C-5678", "amount": 750, ...})
   BLOCKED -> Refund $750.00 exceeds $500.00 limit.
   REDIRECTED to escalate_to_manager -> {"status": "escalated", "ticket_id": "ESC-7891", ...}
Agent: Your refund request has been escalated to a manager for review...
```

## Exam-Relevant Takeaways

1. **Hooks live in code, not prompts** — they execute deterministically regardless of what Claude "wants" to do
2. **Block + redirect > block + error** — giving Claude a structured alternative (escalation tool) produces better UX than a raw denial
3. **Policy thresholds belong in application logic** — putting "$500 limit" in the system prompt is a suggestion; putting it in a hook is an enforcement
4. **The agentic loop continues after redirection** — Claude sees the escalation result and explains it to the user naturally
