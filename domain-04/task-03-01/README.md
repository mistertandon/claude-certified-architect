# Structured Output via tool_use
Core exam point: tool_use isn't just for function calling — it's the mechanism for guaranteed structured output. By setting tool_choice to "any", Claude has no option to respond with free text; it must produce
   JSON matching the tool's schema, including all required fields.

## Concept

`tool_use` guarantees JSON schema compliance — Claude **must** respond with output matching the defined tool's `input_schema`. Unlike free-text parsing, there is no ambiguity or malformed JSON risk.

## Setup

```bash
cd domain-04/task-03-01
python -m venv .venv
source .venv/bin/activate
pip install anthropic python-dotenv
```

## Configure

```bash
cp .env .env.local
# Edit .env.local and set your real ANTHROPIC_API_KEY
```

## Run

```bash
export $(cat .env.local | xargs)
python structured_output.py
```

## Expected Output

```json
{
  "name": "Sarah Chen",
  "age": 34,
  "occupation": "machine learning engineer",
  "skills": ["Python", "TensorFlow", "distributed systems"]
}
```

## Key Takeaway

| Mechanism | Schema Guarantee |
|-----------|-----------------|
| `tool_choice: "any"` | Forces tool call — no free-text escape |
| `input_schema` | Defines exact JSON structure Claude must produce |
| `required` fields | Ensures no omissions |
