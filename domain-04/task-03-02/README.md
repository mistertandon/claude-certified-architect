# Task 03-02: Structured Output — Semantic Errors Are Still Possible
The core insight: tool_choice + schema guarantees the JSON is well-formed and type-correct every time, but the values (capital, population, etc.) can still be hallucinated. Structure is enforced at the        
  protocol level; semantics remain the model's best guess. 
## Concept

`tool_use` forces Claude to return **valid JSON matching a schema** — but it **cannot prevent the model from filling fields with wrong facts**. The structure is guaranteed; the meaning is not.

## Example

A `country_info` tool with required fields (`capital`, `population`, `currency`, `continent`) will always return well-typed JSON. But for an obscure country like **Nauru**, the model may:
- Invent a wrong capital
- Hallucinate population numbers
- Pick the wrong currency

The schema passes validation every time. The facts may not.

## Setup

```bash
cd domain-04/task-03-02

# 1. Create a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 2. Install dependencies
pip install anthropic python-dotenv

# 3. Configure your API key
cp .env .env.local
# Edit .env.local and replace "your-api-key-here" with your real key
# OR export directly:
export ANTHROPIC_API_KEY="sk-ant-..."
```

## Run

```bash
python semantic_error_demo.py
```

## Expected Output

```
STRUCTURED OUTPUT (always valid against schema):
{
  "country": "Nauru",
  "capital": "...",         ← may be wrong
  "population": ...,        ← may be wildly off
  "currency": "...",
  "continent": "Oceania"
}

SEMANTIC ERROR ANALYSIS:
  [SEMANTIC ERROR] capital: model='...', truth='Yaren'
  [SEMANTIC ERROR] population: model=..., truth≈12780
```

## Key Takeaway

| Guaranteed by `tool_use` | NOT Guaranteed |
|--------------------------|----------------|
| Valid JSON               | Factual accuracy |
| Required fields present  | Logical consistency |
| Correct types & enums    | Real-world correctness |

**Structure ≠ Semantics. Always validate meaning, not just shape.**
