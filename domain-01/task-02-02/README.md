# Task 01-02-02: Context Isolation in Subagents

## Concept

Each subagent operates with its own **independent message history**. Information given to one subagent is invisible to others — there is no shared memory or cross-agent state leakage.

## How It Works

```
Parent Orchestrator
├── Agent Alpha (messages=[...])   ← knows secret "FALCON-42"
└── Agent Beta  (messages=[...])   ← has NO knowledge of Alpha's secret
```

The isolation boundary is simply **separate `messages` lists** passed to `client.messages.create()`. The API is stateless — context exists only in what you send.

## Setup

```bash
cd domain-01/task-01-02-02

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install anthropic python-dotenv

# Configure API key
cp .env .env.local
# Edit .env.local and set your ANTHROPIC_API_KEY
```

## Run

```bash
python context_isolation.py
```

## Expected Output

1. **Alpha** confirms it stored the secret code
2. **Beta** says it has no knowledge of any secret code
3. **Alpha** correctly recalls the secret from its own context
4. **Beta** confirms it has never interacted with Alpha

This proves contexts are fully isolated between subagents.
