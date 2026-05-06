# Agentic Loop Lifecycle POC

Demonstrates how `stop_reason` values (`tool_use` vs `end_turn`) control loop continuation in a Claude-powered agent.

## How It Works

```
User prompt
    │
    ▼
┌──────────────────────┐
│  Call Claude API      │◄──────────────────┐
└──────────┬───────────┘                    │
           │                                │
           ▼                                │
   ┌─stop_reason?─┐                        │
   │               │                        │
   ▼               ▼                        │
"end_turn"    "tool_use"                    │
   │               │                        │
   ▼               ▼                        │
 DONE        Execute tool(s)               │
             Return results ────────────────┘
```

## Setup

```bash
# 1. Create a virtual environment
python -m venv .venv
source .venv/bin/activate

# 2. Install dependencies
pip install anthropic python-dotenv

# 3. Configure your API key
cp .env .env.local
# Edit .env and replace 'your-api-key-here' with your actual key
```

## Run

```bash
python agentic_loop.py
```

## Expected Output

```
============================================================
User: What's the weather in Tokyo and Paris? Compare them briefly.
============================================================

--- Iteration 1 ---
stop_reason: tool_use            ← model wants to call tools
  Tool call: get_weather({"city": "Tokyo"})
  Tool result: {"city": "Tokyo", "temp_c": 22, "condition": "Sunny"}
  Tool call: get_weather({"city": "Paris"})
  Tool result: {"city": "Paris", "temp_c": 22, "condition": "Sunny"}

--- Iteration 2 ---
stop_reason: end_turn            ← model is done, loop exits