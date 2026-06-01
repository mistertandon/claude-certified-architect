# Task 03-03: Prompt-Based Guidance for Soft Preferences and Style Suggestions

## Concept

System prompts can include **soft preferences** — style, tone, and format guidance that Claude follows by default but yields when the user explicitly requests something different. This contrasts with hard constraints (e.g., tool-use schemas or stop sequences) that cannot be overridden.

## Key Architectural Insight

| Guidance Type | Where to Place | Override Behavior |
|---|---|---|
| Soft preference | System prompt | User can override naturally |
| Hard constraint | Tool schemas / code logic | Cannot be overridden by user |

## Setup

```bash
cd domain-01/task-03-03

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
python prompt_guidance.py
```

## Expected Output

- **Demo 1**: Claude answers concisely with analogies and friendly tone (following soft preferences).
- **Demo 2**: Claude produces a long, formal, Java-based answer (user override trumps soft preferences).

## Exam Relevance

- Soft preferences belong in the **system prompt** — they shape default behavior without rigid enforcement.
- The user can always override soft guidance; this is by design.
- Separating guidance into system vs. user messages keeps multi-turn conversations clean.
