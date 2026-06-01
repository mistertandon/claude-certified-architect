"""
POC: Subagent Delegation — Keeping Coordinator Context Clean
=============================================================
Demonstrates the core exam concept: a coordinator agent delegates verbose
exploratory work to disposable subagents, receiving only condensed summaries
back.  The coordinator's context window stays small regardless of how much
research the subagents perform.

Scenario (security audit coordinator):
  1. Coordinator receives a multi-file audit request.
  2. For each file, it spawns a SUBAGENT — a separate API call with its own
     context — that performs deep, verbose analysis.
  3. Each subagent returns ONLY a structured summary (not its full reasoning).
  4. Coordinator synthesizes summaries into a final report, never having seen
     the verbose exploration that produced them.

  Contrast run: same audit done WITHOUT delegation — the coordinator's context
  balloons with every file's verbose analysis.

Why this matters:
  - Coordinator context stays O(summaries), not O(full_analysis * num_files).
  - Each subagent gets a fresh, focused context — no cross-file noise.
  - Subagents can be parallelized (shown sequentially here for clarity).
"""

import os
import json
from datetime import datetime

from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

client = Anthropic()

MODEL = os.getenv("MODEL_NAME", "claude-sonnet-4-20250514")

# ── Simulated codebase for audit ────────────────────────────────────────

CODE_FILES = {
    "auth.py": (
        "def login(user, pwd):\n"
        "    query = f\"SELECT * FROM users WHERE name='{user}' AND pass='{pwd}'\"\n"
        "    token = jwt.encode({'user': user}, 'hardcoded-secret', algorithm='HS256')\n"
        "    return db.execute(query), token\n"
    ),
    "upload.py": (
        "import os\n"
        "def save_file(filename, data):\n"
        "    path = os.path.join('/uploads', filename)\n"
        "    open(path, 'wb').write(data)\n"
        "    os.chmod(path, 0o777)\n"
        "    return path\n"
    ),
    "session.py": (
        "import pickle, base64\n"
        "def load_session(cookie_value):\n"
        "    raw = base64.b64decode(cookie_value)\n"
        "    return pickle.loads(raw)\n"
    ),
    "config.py": (
        "DB_URL = 'postgres://admin:password@prod-db:5432/app'\n"
        "API_KEY = 'sk-live-abc123def456'\n"
        "ALLOWED_ORIGINS = ['*']\n"
        "DEBUG = True\n"
    ),
}


# ── Subagent: isolated, verbose, disposable ─────────────────────────────

def spawn_subagent(filename: str, code: str) -> dict:
    """Spawn a subagent with its own context to deeply analyze ONE file.

    Key design choice: the subagent's system prompt demands structured JSON
    output — this is how we control what leaks back into the coordinator.
    The subagent can reason verbosely internally, but only the JSON summary
    crosses the boundary."""

    # Subagent gets a SEPARATE system prompt — coordinator never sees it
    subagent_system = """\
You are a security auditor subagent. You will receive ONE code file.
Perform a thorough, verbose security analysis internally, but your
FINAL response must be ONLY a JSON object with this schema:
{
  "file": "<filename>",
  "vulnerabilities": [
    {
      "type": "<vulnerability class>",
      "severity": "critical|high|medium|low",
      "line": <line_number>,
      "detail": "<one-sentence explanation>"
    }
  ],
  "summary": "<2-3 sentence overall assessment>"
}
No markdown fences. No preamble. Just the JSON object."""

    # Each subagent call is an INDEPENDENT conversation — no shared history
    # This is what keeps the coordinator's context clean
    subagent_messages = [
        {
            "role": "user",
            "content": (
                f"Audit this file `{filename}` for security vulnerabilities. "
                f"Check for: injection, auth flaws, secrets exposure, insecure "
                f"deserialization, path traversal, and misconfigurations.\n\n"
                f"```python\n{code}```"
            ),
        }
    ]

    resp = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=subagent_system,
        messages=subagent_messages,
    )

    raw_text = resp.content[0].text

    # Parse the subagent's structured output — this is the ONLY thing
    # the coordinator will see from this subagent's entire exploration
    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        return {
            "file": filename,
            "vulnerabilities": [],
            "summary": f"[Parse error] Raw: {raw_text[:200]}",
        }


# ── Coordinator: thin context, delegates everything ─────────────────────

def run_delegated_audit() -> tuple[list[dict], list[dict]]:
    """Coordinator delegates each file to a subagent, collects summaries only.

    The coordinator's message history contains ONLY the summaries — never
    the subagent's internal reasoning or the raw code analysis."""

    # Coordinator tracks its own lean conversation
    coordinator_messages = []
    all_findings = []

    print("Spawning subagents for each file...\n")

    for filename, code in CODE_FILES.items():
        # Each subagent is a fresh, isolated API call
        finding = spawn_subagent(filename, code)
        all_findings.append(finding)

        vuln_count = len(finding.get("vulnerabilities", []))
        print(f"  Subagent [{filename}]: returned {vuln_count} findings")

    # Feed ONLY the condensed findings into the coordinator's context
    # The coordinator never sees the verbose analysis that produced these
    findings_json = json.dumps(all_findings, indent=2)

    coordinator_messages.append({
        "role": "user",
        "content": (
            "You received security audit summaries from subagents who analyzed "
            "individual files. Synthesize them into a prioritized executive report.\n\n"
            f"Subagent findings:\n{findings_json}"
        ),
    })

    resp = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=(
            "You are a security audit coordinator. You receive structured findings "
            "from specialist subagents and synthesize them into an executive report. "
            "You never analyze code directly — you coordinate and summarize."
        ),
        messages=coordinator_messages,
    )

    coordinator_messages.append({
        "role": "assistant",
        "content": resp.content[0].text,
    })

    return coordinator_messages, all_findings


# ── Contrast: monolithic audit (no delegation) ─────────────────────────

def run_monolithic_audit() -> list[dict]:
    """Same audit but EVERYTHING in one conversation — context balloons.

    This is the anti-pattern: the single agent's context accumulates all
    verbose analysis for all files, wasting context window space."""

    messages = []

    for filename, code in CODE_FILES.items():
        # Each file's analysis ADDS to the same conversation
        messages.append({
            "role": "user",
            "content": (
                f"Perform a thorough security audit of `{filename}`:\n"
                f"```python\n{code}```\n"
                f"Be detailed — explain each vulnerability, its impact, and remediation."
            ),
        })

        # Model sees ALL prior file analyses — O(files * analysis_size)
        resp = client.messages.create(
            model=MODEL,
            max_tokens=1024,
            system=(
                "You are a security auditor. Perform detailed analysis of each "
                "code file. Be thorough and verbose in your explanations."
            ),
            messages=messages,
        )

        messages.append({
            "role": "assistant",
            "content": resp.content[0].text,
        })

        token_est = sum(len(m["content"]) for m in messages) // 4
        print(f"  Monolithic [{filename}]: ~{token_est} tokens in context | "
              f"{len(messages)} messages")

    # Now ask for the same synthesis — but the context is bloated
    messages.append({
        "role": "user",
        "content": "Synthesize all findings into a prioritized executive report.",
    })

    resp = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=(
            "You are a security auditor. Perform detailed analysis of each "
            "code file. Be thorough and verbose in your explanations."
        ),
        messages=messages,
    )
    messages.append({"role": "assistant", "content": resp.content[0].text})

    return messages


# ── Token measurement ───────────────────────────────────────────────────

def estimate_tokens(messages: list[dict]) -> int:
    """Rough token estimate — real systems use client.messages.count_tokens()."""
    return sum(len(m["content"]) for m in messages) // 4


# ── Main ────────────────────────────────────────────────────────────────

def main():
    # ── Run 1: Delegated (subagent) approach ─────────────────────────
    print("=" * 64)
    print("RUN 1: DELEGATED AUDIT (subagent per file)")
    print("=" * 64)

    coord_msgs, findings = run_delegated_audit()
    coord_tokens = estimate_tokens(coord_msgs)

    print(f"\nCoordinator context: {len(coord_msgs)} messages, ~{coord_tokens} tokens")
    print(f"Coordinator NEVER saw raw code or verbose analysis\n")
    print("--- Coordinator's synthesized report ---")
    print(coord_msgs[-1]["content"])

    # ── Run 2: Monolithic (no delegation) ────────────────────────────
    print("\n" + "=" * 64)
    print("RUN 2: MONOLITHIC AUDIT (everything in one context)")
    print("=" * 64)

    mono_msgs = run_monolithic_audit()
    mono_tokens = estimate_tokens(mono_msgs)

    print(f"\nMonolithic context: {len(mono_msgs)} messages, ~{mono_tokens} tokens")

    # ── Comparison ───────────────────────────────────────────────────
    print("\n" + "=" * 64)
    print("COMPARISON: DELEGATED vs MONOLITHIC")
    print("=" * 64)

    savings_pct = (1 - coord_tokens / mono_tokens) * 100 if mono_tokens > 0 else 0

    print(f"  Delegated coordinator:  {len(coord_msgs):>3} messages | ~{coord_tokens:>5} tokens")
    print(f"  Monolithic single-agent:{len(mono_msgs):>3} messages | ~{mono_tokens:>5} tokens")
    print(f"  Coordinator savings:    ~{savings_pct:.0f}%")
    print()
    print("  Architecture:")
    print("    Delegated:  Coordinator <-- summary <-- Subagent(file1)")
    print("                Coordinator <-- summary <-- Subagent(file2)")
    print("                Coordinator <-- summary <-- Subagent(fileN)")
    print("                Coordinator context = O(summaries)")
    print()
    print("    Monolithic: Agent(file1 analysis + file2 analysis + ... + fileN)")
    print("                Agent context = O(N * verbose_analysis)")
    print()
    print("Key insight: Subagents are DISPOSABLE — their verbose reasoning is")
    print("discarded after extraction. The coordinator only accumulates the")
    print("structured output, keeping its context window free for synthesis.")

    # ── Save results ─────────────────────────────────────────────────
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    results = {
        "delegated": {
            "coordinator_messages": len(coord_msgs),
            "coordinator_tokens_approx": coord_tokens,
            "subagent_findings": findings,
            "coordinator_report": coord_msgs[-1]["content"],
        },
        "monolithic": {
            "messages": len(mono_msgs),
            "tokens_approx": mono_tokens,
            "final_report": mono_msgs[-1]["content"],
        },
        "savings_pct": round(savings_pct, 1),
    }
    out_file = f"delegation_results_{ts}.json"
    with open(out_file, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to {out_file}")


if __name__ == "__main__":
    main()
