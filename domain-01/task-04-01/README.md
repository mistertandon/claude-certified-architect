# Task 04-01: `--resume` Flag — Session Continuity

## Concept

The `--resume` flag in Claude Code continues a previous conversation by replaying stored message history to the API. The model has no built-in memory — context is preserved entirely by resending prior turns.

## Setup

```bash
cd domain-01/task-04-01

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install anthropic python-dotenv
```

## Configure

Edit `.env` and set your API key:

```
ANTHROPIC_API_KEY=sk-ant-...
```

## Run

### Start a new session

```bash
python resume_session.py
```

Ask a few questions, then type `quit`.

### Resume the session

```bash
python resume_session.py --resume
```

The model now remembers everything from the previous run — ask it to recall earlier answers.

## How It Works

1. Each user/assistant message pair is appended to a list and saved to `session_history.json`.
2. With `--resume`, that JSON is loaded and sent as the `messages` parameter — the API sees the full prior conversation.
3. Without `--resume`, the history file is deleted and a fresh session begins.

## Example

```
# First run
$ python resume_session.py
You: My name is Alice
Claude: Nice to meet you, Alice!
You: quit

# Second run with --resume
$ python resume_session.py --resume
[Resumed session with 2 prior messages]
You: What is my name?
Claude: Your name is Alice, as you mentioned earlier.
```
