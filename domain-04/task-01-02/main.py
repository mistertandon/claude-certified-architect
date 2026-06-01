"""
Prompt Design Principle — False Positive Impact
================================================
Too many false positives erode developer trust in the system.

This POC simulates a code-review assistant that flags security issues in
code snippets.  Two prompt strategies are compared:

  1. NAIVE prompt  — overly cautious, flags almost everything → high false-positive rate.
  2. TUNED prompt  — balanced, flags only genuine risks   → low  false-positive rate.

A batch of code snippets (some safe, some risky) is sent through both
prompts.  The output shows how the naive prompt cries wolf so often that
developers learn to ignore it — the core "false positive trust erosion"
problem.
"""

import os
import json
from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()

# Single client instance — reuse keeps connection pooling efficient
client = Anthropic()

# --- Code snippets to review (ground truth labels included) ---------------

CODE_SAMPLES = [
    {
        "id": 1,
        "code": "user_id = request.args.get('id')\nquery = f'SELECT * FROM users WHERE id = {user_id}'",
        "actually_risky": True,
        "reason": "Classic SQL injection via string interpolation",
    },
    {
        "id": 2,
        "code": "password_hash = hashlib.sha256(password.encode()).hexdigest()",
        "actually_risky": True,
        "reason": "SHA-256 is not suitable for password hashing (no salt, too fast)",
    },
    {
        "id": 3,
        "code": "logger.info(f'User {user.name} logged in from {request.remote_addr}')",
        "actually_risky": False,
        "reason": "Standard structured logging — no secrets exposed",
    },
    {
        "id": 4,
        "code": "config = json.load(open('config.json'))\ndb_host = config['database']['host']",
        "actually_risky": False,
        "reason": "Reading a local config file is normal application behaviour",
    },
    {
        "id": 5,
        "code": "token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')",
        "actually_risky": False,
        "reason": "Standard JWT signing with a server-side secret",
    },
    {
        "id": 6,
        "code": "os.system(f'convert {user_filename} output.png')",
        "actually_risky": True,
        "reason": "Command injection — unsanitised user input passed to shell",
    },
]

# --- Prompt strategies -------------------------------------------------------

# Naive prompt: deliberately over-sensitive so it triggers on benign code too.
# This mirrors real-world tools whose "flag everything" stance trains devs to
# click "dismiss" reflexively.
NAIVE_SYSTEM_PROMPT = """You are an extremely cautious security reviewer.
Flag ANY code that touches user input, file I/O, networking, cryptography,
logging, or configuration as a HIGH-RISK security issue.  Err heavily on
the side of caution — it is better to over-flag than to miss anything.

Respond ONLY with valid JSON (no markdown):
{"flagged": true/false, "severity": "HIGH"/"MEDIUM"/"LOW"/"NONE", "reason": "..."}
"""

# Tuned prompt: asks the model to reason about *exploitability* before flagging.
# Fewer false positives → developers actually read the remaining alerts.
TUNED_SYSTEM_PROMPT = """You are a pragmatic security reviewer.
Only flag code that contains a concrete, exploitable vulnerability — one an
attacker could realistically use to cause harm (e.g., injection, broken auth,
sensitive data exposure).

Do NOT flag:
- Standard library usage that follows best practices
- Logging that does not leak secrets
- Configuration loading from trusted local files
- Properly parameterised queries or signed tokens

Respond ONLY with valid JSON (no markdown):
{"flagged": true/false, "severity": "HIGH"/"MEDIUM"/"LOW"/"NONE", "reason": "..."}
"""


def review_snippet(system_prompt: str, code: str) -> dict:
    """Send one snippet through the model and parse the structured verdict."""
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=256,
        # System prompt is where prompt-design leverage lives —
        # it shapes the model's threshold for what counts as "risky".
        system=system_prompt,
        messages=[
            {
                "role": "user",
                "content": f"Review this code snippet for security issues:\n\n```python\n{code}\n```",
            }
        ],
    )

    raw = response.content[0].text
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"flagged": True, "severity": "UNKNOWN", "reason": raw}


def run_review_pass(label: str, system_prompt: str) -> dict:
    """Run every snippet through a single prompt strategy and collect metrics."""
    print(f"\n{'=' * 64}")
    print(f"  Strategy: {label}")
    print(f"{'=' * 64}")

    true_pos = 0   # correctly flagged risky code
    false_pos = 0  # incorrectly flagged safe code  ← the trust killer
    true_neg = 0   # correctly passed safe code
    false_neg = 0  # missed genuinely risky code

    for sample in CODE_SAMPLES:
        verdict = review_snippet(system_prompt, sample["code"])
        flagged = verdict.get("flagged", False)
        actually_risky = sample["actually_risky"]

        # Classify the outcome against ground truth
        if flagged and actually_risky:
            true_pos += 1
            tag = "TP"
        elif flagged and not actually_risky:
            false_pos += 1
            tag = "FP"  # ← this is the one that erodes trust
        elif not flagged and not actually_risky:
            true_neg += 1
            tag = "TN"
        else:
            false_neg += 1
            tag = "FN"

        print(f"\n  Snippet #{sample['id']}  [{tag}]")
        print(f"    Flagged : {flagged}  |  Actually risky: {actually_risky}")
        print(f"    Verdict : {verdict.get('severity', '?')} — {verdict.get('reason', '?')}")

    total_flagged = true_pos + false_pos
    # Precision = what fraction of alerts are real — low precision = alert fatigue
    precision = true_pos / total_flagged if total_flagged else 1.0
    # False-positive rate among safe samples — the direct trust-erosion metric
    safe_count = sum(1 for s in CODE_SAMPLES if not s["actually_risky"])
    fp_rate = false_pos / safe_count if safe_count else 0.0

    metrics = {
        "true_positives": true_pos,
        "false_positives": false_pos,
        "true_negatives": true_neg,
        "false_negatives": false_neg,
        "precision": round(precision, 2),
        "false_positive_rate": round(fp_rate, 2),
    }

    print(f"\n  ── Metrics ──")
    print(f"    True  Positives : {true_pos}")
    print(f"    False Positives : {false_pos}  ← trust erosion signal")
    print(f"    True  Negatives : {true_neg}")
    print(f"    False Negatives : {false_neg}")
    print(f"    Precision       : {metrics['precision']}")
    print(f"    FP Rate (safe)  : {metrics['false_positive_rate']}")

    return metrics


def main():
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║  False Positive Impact on Developer Trust — POC             ║")
    print("╠══════════════════════════════════════════════════════════════╣")
    print("║  Comparing a NAIVE (over-flagging) prompt vs. a TUNED      ║")
    print("║  (precision-focused) prompt on the same code snippets.     ║")
    print("╚══════════════════════════════════════════════════════════════╝")

    naive_metrics = run_review_pass("NAIVE  (flag everything)", NAIVE_SYSTEM_PROMPT)
    tuned_metrics = run_review_pass("TUNED  (flag real risks)", TUNED_SYSTEM_PROMPT)

    print(f"\n{'=' * 64}")
    print("  COMPARISON")
    print(f"{'=' * 64}")
    print(f"                     NAIVE       TUNED")
    print(f"  False Positives :  {naive_metrics['false_positives']}           {tuned_metrics['false_positives']}")
    print(f"  Precision       :  {naive_metrics['precision']}        {tuned_metrics['precision']}")
    print(f"  FP Rate (safe)  :  {naive_metrics['false_positive_rate']}        {tuned_metrics['false_positive_rate']}")

    print(f"\n  Key Takeaway:")
    print(f"  ─────────────")
    if naive_metrics["false_positives"] > tuned_metrics["false_positives"]:
        print("  The NAIVE prompt produces more false positives.")
        print("  Developers learn to IGNORE its alerts → real bugs slip through.")
        print("  The TUNED prompt preserves trust by only flagging genuine risks.")
    else:
        print("  Both prompts performed similarly on this sample set.")
        print("  Try adding more benign snippets to see divergence.")

    print()


if __name__ == "__main__":
    main()
