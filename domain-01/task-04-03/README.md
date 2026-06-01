# Task 04-03: Named Sessions — Organized Multi-Session Workflows

## Concept

Claude Code's `--session-id <name>` flag lets you maintain **multiple parallel conversations**, each with its own isolated context. This is essential when working on a project with distinct workstreams (frontend, backend, debugging) that shouldn't pollute each other's token budget.

```
Terminal 1 (backend):    claude --session-id backend   "Design the /orders API"
Terminal 2 (frontend):   claude --session-id frontend  "Build the product listing"
Terminal 3 (debugging):  claude --session-id debugging "Why is the cart 500-ing?"

Each session has its own message history — no cross-contamination.
```

## Why This Matters

| Problem | How named sessions solve it |
|---|---|
| One long session mixes unrelated topics | Each workstream gets a focused context |
| Context window fills with irrelevant turns | Sessions stay lean — only their own turns |
| Resuming requires remembering where you left off | `--session-id backend` always picks up where backend left off |
| Team members share a project | Each can have their own named session |

## Setup

```bash
cd domain-01/task-04-03
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Configure

Edit `.env` and set your API key:

```
ANTHROPIC_API_KEY=sk-ant-...
MODEL_NAME=claude-sonnet-4-6
```

## Run

### Scripted Demo (no interaction needed)

```bash
python named_sessions.py --demo
```

This walks through 4 steps automatically:
1. **Create** two named sessions (`backend` and `frontend`)
2. **Continue** each session — proves context is isolated per session
3. **List** all sessions with message counts
4. **Recall** — each session summarizes only its own discussion

### Interactive Mode

```bash
python named_sessions.py
```

Commands:
| Command | Description |
|---|---|
| `/new <name>` | Create or switch to a named session |
| `/switch <name>` | Switch to an existing session |
| `/list` | Show all sessions with message counts |
| `/delete <name>` | Remove a session |
| `/quit` | Exit |

### Example Interactive Workflow

```
(no session) > /new backend
  Created new session 'backend'
[backend] You: Design the /users endpoint
  Claude: ...
[backend] You: /new frontend
  Created new session 'frontend'
[frontend] You: What React state library should I use?
  Claude: ...
[frontend] You: /switch backend
  Switched to 'backend' (2 messages)
[backend] You: Now add authentication to /users
  Claude: ...  (remembers the earlier /users discussion)
```

## Expected Demo Output

1. **Step 1** — Two sessions created: `backend` discusses REST endpoints, `frontend` discusses React components
2. **Step 2** — Each session continues its own topic with full prior context
3. **Step 3** — Session listing shows both sessions with independent message counts
4. **Step 4** — Each session's summary proves it only knows about its own workstream
