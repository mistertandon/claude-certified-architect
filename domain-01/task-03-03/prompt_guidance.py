"""
POC: Prompt-based guidance for soft preferences and style suggestions.

Demonstrates how system prompts steer Claude's tone, format, and style
without hard constraints — the model treats them as preferences, not rules.
"""

import os
from dotenv import load_dotenv
from anthropic import Anthropic

# Load from .env so secrets stay out of source control
load_dotenv()

# Single client instance — reuses connection pool across calls
client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# --- Soft preference guidance embedded in system prompt ---
# System prompt is the canonical place for style/tone steering because
# Claude weighs it more heavily than user-turn instructions, yet still
# treats directives here as soft preferences (can be overridden by user).
SYSTEM_PROMPT = """You are a helpful coding mentor.

## Style preferences (soft guidance)
- Prefer concise answers (3-5 sentences) unless the user asks for detail.
- Use analogies from everyday life to explain technical concepts.
- When suggesting code, favor readability over cleverness.
- Default to Python examples unless the user specifies another language.
- Adopt a friendly, encouraging tone — avoid jargon without explanation.

## Format suggestions
- Use bullet points for lists of options or steps.
- Wrap code in fenced code blocks with language tags.
- Bold key terms on first mention.

These are preferences, not hard rules. Adapt naturally if the user's
request calls for a different approach."""


def ask_with_guidance(user_question: str) -> str:
    """Send a question with soft-preference system prompt."""
    response = client.messages.create(
        model="claude-sonnet-4-6-20250514",
        max_tokens=1024,
        # System prompt carries the style guidance — separated from user
        # content so it persists across multi-turn without repetition
        system=SYSTEM_PROMPT,
        messages=[
            {"role": "user", "content": user_question}
        ],
    )
    # .text extracts the first text block — safe for single-response use
    return response.content[0].text


def demonstrate_preference_override():
    """Show that soft guidance yields to explicit user requests."""
    # This prompt contradicts the 'concise' preference intentionally —
    # proves the guidance is soft, not a hard constraint
    override_prompt = (
        "Explain recursion in great detail with a long Java example. "
        "Be very formal and academic in tone."
    )
    response = client.messages.create(
        model="claude-sonnet-4-6-20250514",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[
            {"role": "user", "content": override_prompt}
        ],
    )
    return response.content[0].text


if __name__ == "__main__":
    print("=" * 60)
    print("DEMO 1: Soft preferences shape the response style")
    print("=" * 60)
    # Simple question — expect concise, friendly, analogy-rich answer
    answer = ask_with_guidance("What is a REST API?")
    print(answer)

    print("\n" + "=" * 60)
    print("DEMO 2: User override trumps soft preferences")
    print("=" * 60)
    # Explicit user instructions override system-level soft guidance
    override_answer = demonstrate_preference_override()
    print(override_answer)
