import anthropic
import os

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# Few-shot examples teach the model a consistent output format
# without needing explicit format instructions in the system prompt.
few_shot_examples = [
    # Standard case: positive sentiment
    {"role": "user", "content": "Classify sentiment: 'I love this product, it changed my life!'"},
    {"role": "assistant", "content": "sentiment: positive\nconfidence: 0.95"},

    # Standard case: negative sentiment
    {"role": "user", "content": "Classify sentiment: 'Terrible experience, never buying again.'"},
    {"role": "assistant", "content": "sentiment: negative\nconfidence: 0.92"},

    # Edge case: empty/meaningless input — model must gracefully refuse
    # rather than hallucinate a classification.
    {"role": "user", "content": "Classify sentiment: ''"},
    {"role": "assistant", "content": "sentiment: unclassifiable\nconfidence: 0.0\nreason: empty input"},

    # Edge case: mixed/contradictory sentiment — forces the model
    # to acknowledge ambiguity instead of picking a side.
    {"role": "user", "content": "Classify sentiment: 'The food was amazing but the service ruined everything.'"},
    {"role": "assistant", "content": "sentiment: mixed\nconfidence: 0.70\nreason: positive food, negative service"},
]

# The actual query we want classified
user_query = "Classify sentiment: 'It works I guess, nothing special.'"

# System prompt is minimal — the few-shot examples carry the behavioral weight.
response = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=150,
    system="You are a sentiment classifier. Follow the exact output format shown in prior examples.",
    messages=few_shot_examples + [{"role": "user", "content": user_query}],
)

print(f"Input: {user_query}\n")
print(f"Response:\n{response.content[0].text}")
