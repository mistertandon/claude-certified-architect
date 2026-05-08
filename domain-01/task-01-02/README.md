# Tool Result Appending POC

What the POC demonstrates: A 3-step account review pipeline (fetch record → validate email → check status) where each tool result is appended to the messages list before the next API call. The model sees all  
  prior results accumulate, enabling it to make informed decisions at each step — e.g., it validates the specific email returned by the fetch, then checks the status of the specific user it already knows is
  blocklisted.                                                                                                                                                                                                     
                                                            
  The conversation snapshot at the end prints the full message structure so you can see exactly how [user, asst(tool_use), user(tool_result), ...] grows across iterations. 

---

Demonstrates how tool results are appended to the conversation after each tool call, giving the model cumulative context for validation and review decisions.

## Core Concept

```
Iteration 1                          Iteration 2                          Iteration 3
─────────────                        ─────────────                        ─────────────
messages = [                         messages = [                         messages = [
  user: "Review u-102"                 user: "Review u-102",                user: "Review u-102",
]                                      asst: tool_use(fetch_user),          asst: tool_use(fetch_user),
                                       user: tool_result({...}),            user: tool_result({...}),
                                     ]                                      asst: tool_use(validate_email),
                                                                            user: tool_result({...}),
                                                                          ]

Model sees 1 message                 Model sees 3 messages                Model sees 5 messages
→ Calls fetch_user_record            → Sees fetch result, now             → Sees all prior results,
                                       calls validate_email                 calls check_account_status
```

Each iteration appends two messages (assistant tool_use + user tool_result), so the model accumulates full context to make informed decisions at every step.

## Setup

```bash
# 1. Create virtual environment
python -m venv .venv
source .venv/bin/activate

# 2. Install dependencies
pip install anthropic python-dotenv

# 3. Configure API key
# Edit .env and replace 'your-api-key-here' with your actual Anthropic API key
```

## Run

```bash
python tool_result_appending.py
```

## Expected Output

```
============================================================
User: Review user u-102 and give me a verdict on their account.
============================================================

--- Iteration 1 ---
stop_reason: tool_use
  messages in context: 1
  Tool call: fetch_user_record({"user_id": "u-102"})
  Tool result: {"found": true, "name": "Bob", "email": "bob@spam-domain.xyz", "signup": "2025-03-20"}

--- Iteration 2 ---
stop_reason: tool_use
  messages in context: 3
  Tool call: validate_email({"email": "bob@spam-domain.xyz"})
  Tool result: {"email": "bob@spam-domain.xyz", "valid_format": true, "blocklisted": true}

--- Iteration 3 ---
stop_reason: tool_use
  messages in context: 5
  Tool call: check_account_status({"user_id": "u-102"})
  Tool result: {"user_id": "u-102", "status": "flagged"}

--- Iteration 4 ---
stop_reason: end_turn
  messages in context: 7

Assistant (final review):
  ... verdict referencing ALL prior tool results ...

============================================================
Conversation structure (role / content-type per message):
============================================================
  [0] user: text
  [1] assistant: text, tool_use
  [2] user: tool_result
  [3] assistant: text, tool_use
  [4] user: tool_result
  [5] assistant: text, tool_use
  [6] user: tool_result
```

## Key Exam Takeaways

1. **Messages list grows**: Each tool call adds two messages (assistant tool_use + user tool_result)
2. **ID linkage**: Every `tool_result` must reference the `tool_use_id` from the corresponding `tool_use` block
3. **Role alternation**: Tool results are sent as `user` role messages — the API enforces user/assistant alternation
4. **Cumulative context**: The model sees ALL prior results on each iteration, enabling multi-step validation
5. **stop_reason drives the loop**: `tool_use` → continue iterating, `end_turn` → exit with final answer
