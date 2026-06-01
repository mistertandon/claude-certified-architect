# Few-Shot Prompting: Format Consistency

Demonstrates how few-shot examples enforce a consistent output structure across all model responses.

  The key insight: format consistency comes from repetition across examples, not verbose instructions. Three examples with identical structure (Category, Sentiment, Confidence, Key Phrases) teach the model the  
  schema more reliably than describing it in prose.   
  
## Core Concept

All few-shot examples share an identical schema (`Category`, `Sentiment`, `Confidence`, `Key Phrases`). The model learns to replicate this structure for any new input without explicit formatting instructions.

## Setup

```bash
cd domain-04/task-02-02

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install anthropic python-dotenv

# Configure API key
cp .env .env.local
# Edit .env.local and replace 'your-api-key-here' with your actual key
```

## Run

```bash
python few_shot_format_consistency.py
```

## Expected Output

```
Input: This framework makes async programming surprisingly intuitive.
Output:
Category: Product Review
Sentiment: Positive
Confidence: 0.93
Key Phrases: async programming, surprisingly intuitive
------------------------------------------------------------
Input: My flight was canceled twice and nobody offered help.
Output:
Category: Service Complaint
Sentiment: Negative
Confidence: 0.94
Key Phrases: flight canceled twice, nobody offered help
------------------------------------------------------------
```

## Key Takeaways

| Technique | Purpose |
|-----------|---------|
| 3 diverse examples | Cover positive, negative, neutral — prevents bias |
| Identical output keys | Model learns the schema by repetition |
| `temperature=0.0` | Minimizes format drift |
| System prompt constraint | Reinforces "no extra fields" rule |
