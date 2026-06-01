# Task 03-05: Crash Recovery Manifests — Persistent State for Session Recovery

## Concept

A **crash recovery manifest** is a JSON state file written to disk before each step of an agentic loop. If the process crashes, the next run detects the manifest, skips completed steps, and resumes from the last incomplete one.

```
Step 1  ──write-ahead──►  [manifest.json]  ──API call──►  commit result
Step 2  ──write-ahead──►  [manifest.json]  ──API call──►  commit result
Step 3  ──write-ahead──►  [manifest.json]  ──💥 CRASH──►  (process dies)
                                                          
Re-run  ──load manifest──►  skip 1,2  ──resume step 3──►  continue...
```

## Architecture

| Phase | What happens | Manifest state |
|-------|-------------|----------------|
| **Write-ahead** | Persist intent BEFORE API call | `status: "in_progress"`, `current_step: N` |
| **API call** | The risky operation that might fail | (manifest already saved) |
| **Commit** | Append result, advance step pointer | `current_step: N+1`, result in `completed_results` |
| **Recovery** | On restart, load manifest, skip done steps | Resume from `current_step` |

## Key Design Choices

| Choice | Why |
|--------|-----|
| **Write-ahead** (persist before call) | If crash happens during API call, we know which step to retry |
| **Atomic writes** (temp + rename) | OS-level guarantee: no half-written manifests on disk |
| **Step pointer** (not success flag) | `current_step` points to what to attempt next, not what succeeded |
| **Cleanup on success** | Remove manifest when done so stale state doesn't confuse future runs |

## Setup & Run

### 1. Create virtual environment

```bash
cd domain-05/task-03-05
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment

Edit `.env` and set your API key:

```
ANTHROPIC_API_KEY=sk-ant-...your-key...
MODEL_NAME=claude-sonnet-4-20250514
```

### 4. Run a clean execution (no crash)

```bash
python crash_recovery_manifest_poc.py
```

All 5 steps complete. Manifest is created, used, and cleaned up.

### 5. Simulate a crash and recovery

**First run — crash at step 3:**

```bash
CRASH_AT_STEP=2 python crash_recovery_manifest_poc.py
```

Process dies at step 3 (0-indexed = 2). Steps 1–2 are saved in `recovery_manifest.json`.

**Second run — automatic recovery:**

```bash
python crash_recovery_manifest_poc.py
```

Detects the manifest, skips steps 1–2, resumes from step 3.

### 6. Inspect the manifest (optional)

While the process is running (or after a simulated crash):

```bash
cat recovery_manifest.json | python -m json.tool
```

## Expected Output

### Clean run

```
================================================================
CRASH RECOVERY MANIFEST — Multi-Step Research Agent
================================================================
  Manifest path: /path/to/recovery_manifest.json
  Crash at step: None (clean run)

  [FRESH] Starting new session 20260506_120000

  Step 1/5: Explain how prompt caching reduces latency in multi-turn...
    -> Done (XXX+YYY tokens)
  Step 2/5: Describe the role of stop_reason in controlling an agenti...
    -> Done (XXX+YYY tokens)
  ...

SESSION COMPLETE — manifest cleared (no recovery needed)
```

### Crash + recovery

```
# First run (crash at step 3):
  [FRESH] Starting new session 20260506_120000
  Step 1/5: ...  -> Done
  Step 2/5: ...  -> Done
  Step 3/5: ...
  ** SIMULATED CRASH at step 2! **

# Second run (recovery):
  [RECOVERY] Found manifest from session 20260506_120000
  [RECOVERY] 2/5 steps completed
  [RECOVERY] Resuming from step 2

  Step 3/5: ...  -> Done
  Step 4/5: ...  -> Done
  Step 5/5: ...  -> Done

SESSION COMPLETE — manifest cleared (no recovery needed)
```

## Exam-Relevant Takeaways

1. **Write-ahead**: persist state BEFORE the risky operation — never after, or a crash loses the intent
2. **Atomic writes**: temp-file + `os.replace()` prevents half-written manifests
3. **Idempotent resume**: re-running a failed step must be safe (no side effects from the partial attempt)
4. **Step pointer semantics**: `current_step` = "what to attempt next", not "what just succeeded"
5. **Cleanup discipline**: delete manifest on success — stale manifests cause phantom recoveries
6. **Manifest vs. in-memory state**: conversation history is stored in the manifest, not just in Python variables
