# Batch vs Synchronous Processing

  What the POC demonstrates:                                                                                                                                                                                       
  
  1. Synchronous path (messages.create) — reviews 3 code snippets sequentially, each call blocking until done. Use this for CI gates or real-time validation where the next step depends on the result.            
  2. Batch path (messages.batches.create) — submits all 3 reviews in one call, polls for completion, then streams results. Use this for nightly audits, bulk migration reviews, or any workload where "done by
  tomorrow" is acceptable — at 50% cost savings.                                                                                                                                                                   
  3. Key exam point: The per-request params (model, messages, system prompt) are identical in both paths. The difference is purely orchestration — sync blocks the caller, batch decouples submission from
  completion.    

---

  Key exam takeaway: The per-request API shape is identical — same model, messages, params.
  The difference is orchestration: synchronous blocks the caller and returns immediately;
  batch decouples submission from completion, trading latency for 50% cost savings.

---

Demonstrates when to use synchronous (blocking) vs batch (async) processing
for validation and review workloads.

## Core Concept

```
Synchronous:  submit → BLOCK → result      (seconds, full price)
Batch:        submit → queue → poll/webhook → result  (minutes-hours, 50% off)
```

| Dimension | Synchronous | Batch |
|-----------|-------------|-------|
| API | `messages.create()` | `messages.batches.create()` |
| Latency | Seconds | Minutes to hours |
| Cost | Full price | 50% discount |
| Use case | CI gates, real-time validation | Nightly audits, bulk reviews |
| Blocking | Yes — caller waits | No — fire and forget |

## Setup

```bash
cd domain-04/task-04-05
python -m venv .venv
source .venv/bin/activate
pip install anthropic python-dotenv
```

## Configure

Edit `.env` and set your API key:

```
ANTHROPIC_API_KEY=sk-ant-...
```

## Run

```bash
python batch_vs_sync.py
```

## What to Expect

1. **Synchronous phase**: Reviews 3 code snippets sequentially. Each call blocks until done. Total time = sum of individual latencies.

2. **Batch phase**: Submits all 3 reviews in a single batch call. Polls until completion. Demonstrates the async lifecycle: submit → poll → retrieve results.

3. **Comparison**: Both produce the same review output; the difference is latency vs cost trade-off.

## Why This Matters for the Architect Exam

- **Synchronous** = blocking, use for validation gates where the next step depends on the result
- **Batch** = async, use for latency-tolerant bulk workloads at 50% cost
- Per-request params are identical — the orchestration pattern is what differs
- Batch uses `custom_id` to correlate requests with results
- In production, prefer webhooks over polling for batch completion
