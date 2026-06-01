# Domain 02 / Task 01 — What Makes a Good Tool Description

## Concepts Demonstrated

| # | Best Practice | Where to Look |
|---|---------------|---------------|
| 1 | Input format specs with examples | `convert_temperature` description block |
| 2 | Edge cases & boundary conditions | Absolute-zero guard, out-of-stock, unknown SKU |
| 3 | Clear parameter descriptions (types, ranges, constraints) | Every `"description"` inside `input_schema` |
| 4 | Descriptions as documentation — more detail is better | `lookup_product` "DOES / DOES NOT" sections |

## Setup

```bash
cd domain-02/task-01

# 1. Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 2. Install dependencies
pip install anthropic python-dotenv

# 3. Set your API key
cp .env .env.local          # optional — edit either file
# Open .env and replace your-api-key-here with a real key
```

## Run

```bash
python good_tool_descriptions.py
```

## What to Observe

1. **Basic conversion** — The model picks correct `from_scale`/`to_scale` values because the description provides concrete examples.
2. **Below absolute zero** — The model either warns before calling or the tool returns an error; both paths are documented in the description.
3. **Valid SKU lookup** — Returns product details.
4. **Invalid SKU format** — The description specifies `[A-Z0-9]{6,10}`; the model may refuse to call the tool or the tool rejects the input.
5. **Out-of-stock product** — `stock: 0` is a valid state, not an error — the description explicitly distinguishes the two.
