"""
Batch vs Synchronous Processing Demo:
Synchronous calls block and return immediately — use for validation gates
where downstream work depends on the result.
Batch API queues requests for later — use for latency-tolerant bulk workloads
(e.g., reviewing 100 PRs overnight) at 50% cost reduction.
"""

import os
import json
import time
from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()

client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
MODEL = "claude-sonnet-4-6"

# Simulated code snippets to validate — small set for demo, but batch shines at 100+
CODE_SNIPPETS = [
    {
        "id": "snippet-1",
        "code": """def divide(a, b):
    return a / b""",
        "context": "Utility function in payments module",
    },
    {
        "id": "snippet-2",
        "code": """def get_user(user_id):
    query = f"SELECT * FROM users WHERE id = {user_id}"
    return db.execute(query)""",
        "context": "User lookup in auth service",
    },
    {
        "id": "snippet-3",
        "code": """import pickle
def load_config(path):
    with open(path, 'rb') as f:
        return pickle.load(f)""",
        "context": "Config loader used at startup",
    },
]

REVIEW_SYSTEM = """You are a code reviewer. For each snippet, identify:
- Security vulnerabilities (SQL injection, XSS, deserialization, etc.)
- Missing error handling that could cause production crashes
- OWASP Top 10 violations
Return JSON: {"severity": "critical"|"high"|"medium"|"low"|"clean", "issues": [...], "recommendation": "..."}"""


# ============================================================
# PART 1: SYNCHRONOUS — Blocking validation gate
# ============================================================

def sync_review(snippet: dict) -> dict:
    """Synchronous review: blocks until the model responds.
    Use this when the NEXT step depends on this result —
    e.g., a CI gate that must pass before merge."""

    response = client.messages.create(
        model=MODEL,
        max_tokens=512,
        # System prompt sets the reviewer persona once, not per-message
        system=REVIEW_SYSTEM,
        messages=[
            {
                "role": "user",
                "content": f"Review this code from: {snippet['context']}\n\n```python\n{snippet['code']}\n```",
            }
        ],
    )

    return {"id": snippet["id"], "raw": response.content[0].text}


def run_sync_reviews():
    """Sequential sync calls — each blocks until done.
    Total latency = sum of all individual call latencies.
    Appropriate when: results gate a blocking decision (CI, deploy, merge)."""

    print("\n" + "=" * 70)
    print("SYNCHRONOUS REVIEW (blocking, sequential)")
    print("=" * 70)

    start = time.time()
    results = []

    for snippet in CODE_SNIPPETS:
        print(f"\n  Reviewing {snippet['id']}... ", end="", flush=True)
        result = sync_review(snippet)
        results.append(result)
        # Each print only appears AFTER the call returns — that's the blocking nature
        print("done")

    elapsed = time.time() - start
    print(f"\n  Total wall time: {elapsed:.1f}s (sequential, each call blocked)")

    return results, elapsed


# ============================================================
# PART 2: BATCH API — Fire-and-forget for bulk workloads
# ============================================================

def create_batch_reviews():
    """Batch API: sends all requests in one call, processes async.
    Use this for latency-tolerant workloads — nightly audits, bulk
    migration reviews, dataset labeling. 50% cheaper than sync."""

    print("\n" + "=" * 70)
    print("BATCH REVIEW (async, latency-tolerant)")
    print("=" * 70)

    # Each request needs a unique custom_id to correlate results later
    requests = []
    for snippet in CODE_SNIPPETS:
        requests.append(
            {
                "custom_id": snippet["id"],
                "params": {
                    "model": MODEL,
                    "max_tokens": 512,
                    "system": REVIEW_SYSTEM,
                    "messages": [
                        {
                            "role": "user",
                            "content": f"Review this code from: {snippet['context']}\n\n```python\n{snippet['code']}\n```",
                        }
                    ],
                },
            }
        )

    print(f"\n  Submitting batch of {len(requests)} reviews...")
    start = time.time()

    # Single API call queues all requests — returns immediately with a batch ID
    batch = client.messages.batches.create(requests=requests)
    submit_time = time.time() - start

    print(f"  Batch ID: {batch.id}")
    print(f"  Submit time: {submit_time:.1f}s (just the queuing, not processing)")
    print(f"  Status: {batch.processing_status}")

    return batch


def poll_batch(batch_id: str, max_wait: int = 300):
    """Poll until batch completes. In production, use webhooks instead.
    Polling is only for this demo — real systems should not spin-wait."""

    print(f"\n  Polling batch {batch_id}...")

    start = time.time()
    while time.time() - start < max_wait:
        batch = client.messages.batches.retrieve(batch_id)

        counts = batch.request_counts
        total = counts.processing + counts.succeeded + counts.errored + counts.canceled + counts.expired
        print(
            f"    [{time.time() - start:5.1f}s] "
            f"status={batch.processing_status} "
            f"succeeded={counts.succeeded}/{total}",
            flush=True,
        )

        if batch.processing_status == "ended":
            print(f"\n  Batch completed in {time.time() - start:.1f}s")
            return batch

        # Batch API has minutes-scale latency; polling every 5s is reasonable
        time.sleep(5)

    print(f"\n  Timed out after {max_wait}s — batch still processing")
    return None


def fetch_batch_results(batch_id: str) -> list[dict]:
    """Stream results from a completed batch.
    Results arrive as a stream of JSON lines — each line is one request's result."""

    results = []
    # .results() returns an iterator over individual result objects
    for result in client.messages.batches.results(batch_id):
        entry = {
            "id": result.custom_id,
            "type": result.result.type,
        }

        if result.result.type == "succeeded":
            entry["raw"] = result.result.message.content[0].text
        else:
            entry["raw"] = f"Failed: {result.result.type}"

        results.append(entry)

    return results


# ============================================================
# COMPARISON
# ============================================================

def extract_json(text: str) -> dict | None:
    try:
        start = text.index("{")
        end = text.rindex("}") + 1
        return json.loads(text[start:end])
    except (ValueError, json.JSONDecodeError):
        return None


def display_results(label: str, results: list[dict]):
    print(f"\n  --- {label} ---")
    for r in results:
        parsed = extract_json(r["raw"])
        if parsed:
            print(f"    {r['id']}: severity={parsed.get('severity', '?')}, "
                  f"issues={len(parsed.get('issues', []))}")
        else:
            print(f"    {r['id']}: (could not parse JSON)")
            print(f"      {r['raw'][:150]}...")


def main():
    print("=" * 70)
    print("BATCH vs SYNCHRONOUS PROCESSING DEMO")
    print("Validation & Review Patterns")
    print("=" * 70)

    # --- Synchronous: blocking, immediate results ---
    sync_results, sync_time = run_sync_reviews()
    display_results("Synchronous Results", sync_results)

    # --- Batch: queued, latency-tolerant, 50% cheaper ---
    batch = create_batch_reviews()

    completed_batch = poll_batch(batch.id)

    if completed_batch and completed_batch.request_counts.succeeded > 0:
        batch_results = fetch_batch_results(batch.id)
        display_results("Batch Results", batch_results)
    else:
        print("\n  Batch did not complete or had no successful results.")
        batch_results = []

    # --- Decision guide ---
    print("\n" + "=" * 70)
    print("WHEN TO USE WHICH")
    print("=" * 70)
    print("""
  SYNCHRONOUS (messages.create)
    - CI/CD gates: block merge until review passes
    - Real-time validation: user submits code, needs immediate feedback
    - Sequential pipelines: step N depends on step N-1's output
    - Latency: seconds | Cost: full price

  BATCH (messages.batches.create)
    - Nightly code audits across entire repo
    - Bulk migration review (100s of files)
    - Dataset labeling / evaluation runs
    - Any workload where "done by tomorrow" is fine
    - Latency: minutes to hours | Cost: 50% of synchronous

  KEY EXAM POINT:
    The API is identical per-request (same model, messages, params).
    The difference is orchestration: sync blocks the caller,
    batch decouples submission from completion.
""")


if __name__ == "__main__":
    main()
