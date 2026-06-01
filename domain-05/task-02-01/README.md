# Escalation Trigger Classifier — POC

Demonstrates **demand-based and policy-gap escalation triggers** using Claude's tool use for structured classification. The key insight: escalation should be driven by *what action is needed*, not *how the customer feels*.

## Why This Matters

| Approach | Escalates on | Misses | False positives |
|---|---|---|---|
| Sentiment-based | Angry tone | Calm policy gaps | Every frustrated customer |
| **Trigger-based** | Legal threats, policy gaps, demands | — | Low (action-driven) |

## Setup

```bash
cd domain-05/task-02-01

python -m venv .venv
source .venv/bin/activate

pip install anthropic python-dotenv
```

## Configure

Edit `.env` and replace with your actual API key:

```
ANTHROPIC_API_KEY=sk-ant-...
```

## Run

```bash
python escalation_triggers.py
```

## Expected Output

| Test Case | Tone | Escalates? | Why |
|---|---|---|---|
| msg_001 — Legal + regulatory | Angry | Yes | Legal threat + FTC mention |
| msg_002 — Policy gap | Calm | Yes | No policy covers subscription transfer on death |
| msg_003 — Refund + repeated | Frustrated | Yes | Beyond 30-day window + 4th contact |
| msg_004 — Wrong item | Angry | **No** | Standard exchange — frontline can handle |
| msg_005 — Manager + churn | Firm | Yes | Explicit manager request + competitor threat |

**msg_004 is the control case** — high emotion but zero escalation triggers. A sentiment-based system would escalate it; this one correctly does not.

## Architecture

```
Customer message
       │
       ▼
┌─────────────────────┐
│  Claude + tool_use  │  ← forced structured output via tool_choice
│  (system prompt     │
│   encodes trigger   │
│   taxonomy)         │
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  classify_escalation│  ← returns: triggers[], should_escalate, team
│  (JSON schema)      │
└────────┬────────────┘
         │
         ▼
   Route to team
   (tier1 / legal / retention / policy_review)
```

## Trigger Categories

| Trigger | Example | Routes to |
|---|---|---|
| `legal_threat` | "my lawyer will..." | `legal` |
| `regulatory_complaint` | "filing with FTC" | `legal` |
| `refund_beyond_policy` | "bought 6 months ago" | `tier2_billing` |
| `manager_demand` | "let me speak to a manager" | `retention` |
| `policy_gap` | scenario not covered by FAQ | `policy_review` |
| `repeated_contact` | "4th time contacting" | `tier2_billing` |
| `churn_threat` | "switching to CompetitorX" | `retention` |
