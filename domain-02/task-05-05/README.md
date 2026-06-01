# Domain 02 / Task 05-05 — Built-in Tool: Grep (Pattern Search)

## What This Demonstrates

The **grep** built-in tool in a single-tool agentic loop. The model searches for regex patterns across a multi-file codebase to locate TODOs, trace symbol usage, and flag security issues — without reading every file.

```
   User Task (e.g. "find all SQL injection risks")
       |
   +────────────────+
   | GREP AGENT     |  (single tool: grep)
   +────────────────+
       |
   Agentic Loop:
     grep("pattern1") → matches → reasoning
     grep("pattern2") → matches → reasoning
       ↓
     end_turn → synthesized report
```

### Why Grep Matters

| Use Case | Pattern | What It Finds |
|----------|---------|---------------|
| Tech debt audit | `TODO\|FIXME\|HACK` | Deferred tasks across entire codebase |
| Impact analysis | `hash_password` | All callers before refactoring a function |
| Security scan | `f"SELECT.*{` | SQL injection via f-string queries |
| Dependency tracing | `^from\|^import` | Module dependency graph |

## Key Exam Concepts

| Concept | Where in Code |
|---------|---------------|
| Tool schema (JSON) | `GREP_TOOL` dict — regex pattern + optional filters |
| Tool handler | `handle_grep()` — walks tree, applies regex, collects matches |
| Agentic loop | `while turn < max_turns` in `run_grep_agent()` |
| Loop continuation | `stop_reason == "tool_use"` → model needs more searches |
| Loop exit | `stop_reason == "end_turn"` → enough data to answer |
| File filtering | `file_pattern` param narrows to `*.py`, `*.js`, etc. |
| Sandbox isolation | All paths resolved relative to `sandbox/` directory |

## Setup

```bash
cd domain-02/task-05-05

# 1. Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 2. Install dependencies
pip install anthropic python-dotenv

# 3. Set your API key
#    Open .env and replace your-api-key-here with a real Anthropic API key
nano .env
```

## Run

```bash
python grep_tool_poc.py
```

## What to Observe

### Demo 1 — Tech Debt Audit (`TODO|FIXME|HACK`)
- Agent greps for `TODO`, `FIXME`, and `HACK` in separate or combined searches
- Finds comments across `.py` and `.yaml` files
- Synthesizes a severity-ranked report of technical debt
- **Key insight**: grep finds patterns without needing to read entire files

### Demo 2 — Symbol Tracing (`hash_password`)
- Agent searches for a function name across imports, definitions, and call sites
- Maps: defined in `auth.py` → imported in `api.py` → tested in `test_auth.py`
- **Key insight**: impact analysis before refactoring — "who calls this?"

### Demo 3 — Security Scan (SQL injection, weak crypto)
- Agent uses multiple grep calls with different patterns per turn
- Finds: f-string SQL in `db.py`, md5/sha256 in `auth.py`, missing auth in `api.py`
- **Key insight**: automated security auditing via regex pattern matching

## Sandbox File Structure

```
sandbox/
├── config/
│   └── settings.yaml       ← has TODO for rate limiting
├── src/
│   ├── api.py              ← Flask routes, missing auth on /orders
│   ├── auth.py             ← weak hashing (sha256/md5), broken verify
│   ├── db.py               ← SQL injection via f-string
│   └── utils.py            ← incomplete sanitization
└── tests/
    └── test_auth.py        ← TODO for missing test
```

## How Grep Differs from Other Built-in Tools

| Tool | Action | Best For |
|------|--------|----------|
| **read_file** | Read entire file contents | Understanding a specific file |
| **grep** | Search patterns across files | Finding needles in haystacks |
| **glob** | Find files by name pattern | Discovering project structure |
| **bash** | Run arbitrary shell commands | Build, test, validate |

Grep is the **discovery** tool — it answers "where in the codebase does X happen?" without the model needing to read every file first.
