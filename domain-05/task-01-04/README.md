# Trimming Verbose Tool Outputs — POC

Demonstrates how trimming noisy tool results before injecting them back into the conversation preserves essential data while cutting token cost, reducing attention dilution, and preventing accidental leakage of internal fields.

## What This Proves

A simulated customer-lookup API returns a 70+ field JSON response (request metadata, feature flags, audit logs, HATEOAS links). The same user question is answered twice:

1. **Verbose** — the full API response is passed as the tool result
2. **Trimmed** — only whitelisted business-relevant fields are kept

Both produce correct answers, but the trimmed version uses significantly fewer input tokens and removes internal data (IP addresses, audit URLs) that should never reach the end user.

## Prerequisites

- Python 3.10+
- An Anthropic API key

## Setup

```bash
# 1. Navigate to the project directory
cd domain-05/task-01-04

# 2. Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 3. Install dependencies
pip install anthropic python-dotenv

# 4. Configure your API key
#    Open .env and replace "your-api-key-here" with your actual key
nano .env
```

## Run

```bash
python trim_tool_output.py
```

## Expected Output

```
Verbose tool output :  ~3200 chars
Trimmed tool output :   ~500 chars
Reduction           :   ~85%

Input token savings :   ~40-60% fewer input tokens with trimmed output
```

Both versions answer the question correctly. The trimmed version costs less and avoids exposing internal metadata.

## Key Takeaway

Trim tool outputs using a **whitelist** (keep only needed fields) rather than a blacklist (remove unwanted fields). Whitelists are safer because new fields added upstream are excluded by default — preventing both token waste and accidental data leakage through the model's responses.
