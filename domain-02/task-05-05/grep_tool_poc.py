"""
POC: Built-in Grep Tool — Pattern Search Across Files (Claude Architect Exam - Domain 02)

Demonstrates the grep built-in tool in an agentic loop.
The model searches for regex patterns across a codebase to locate symbols,
TODOs, security concerns, and structural patterns — without reading every file.
"""

import os
import re
import json
import fnmatch
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

client = Anthropic()
MODEL = os.getenv("MODEL_NAME", "claude-sonnet-4-20250514")

# Sandbox scopes all searches — prevents the model from grepping outside the demo
SANDBOX = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sandbox")
os.makedirs(SANDBOX, exist_ok=True)


# ── Tool Definition ──────────────────────────────────────────────────────────
# Schema tells the model what arguments grep accepts.
# This mirrors Claude Code's built-in grep — regex pattern, optional directory
# and file-type filter.

GREP_TOOL = {
    "name": "grep",
    "description": (
        "Search for a regex pattern across files in a directory tree. "
        "Returns matching lines with file paths and line numbers. "
        "Use for finding TODOs, symbols, imports, security issues, or any text pattern."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "pattern": {
                "type": "string",
                "description": "Regex pattern to search for (Python re syntax).",
            },
            "directory": {
                "type": "string",
                "description": "Directory to search in (relative to sandbox). Defaults to '.' for all files.",
            },
            "file_pattern": {
                "type": "string",
                "description": "Glob to filter filenames, e.g. '*.py', '*.js'. Optional — searches all files if omitted.",
            },
        },
        "required": ["pattern"],
    },
}


# ── Tool Handler ─────────────────────────────────────────────────────────────
# Walks the directory tree, applies regex to each line, and collects matches.
# Binary files and permission errors are silently skipped — same as real grep.

def handle_grep(pattern: str, directory: str = ".", file_pattern: str = None) -> dict:
    search_dir = os.path.join(SANDBOX, directory) if not os.path.isabs(directory) else directory
    matches = []

    try:
        compiled = re.compile(pattern)
    except re.error as e:
        return {"error": f"Invalid regex: {e}"}

    for root, _, files in os.walk(search_dir):
        for fname in files:
            # file_pattern filter narrows search to specific file types
            if file_pattern and not fnmatch.fnmatch(fname, file_pattern):
                continue
            fpath = os.path.join(root, fname)
            try:
                with open(fpath, "r") as f:
                    for lineno, line in enumerate(f, 1):
                        if compiled.search(line):
                            # Relative paths are easier for the model to reason about
                            rel = os.path.relpath(fpath, SANDBOX)
                            matches.append({
                                "file": rel,
                                "line": lineno,
                                "content": line.rstrip(),
                            })
            except (UnicodeDecodeError, PermissionError):
                # Skip binary/unreadable files — grep semantics
                continue

    return {"matches": matches, "total": len(matches)}


# ── Agentic Loop ─────────────────────────────────────────────────────────────
# Single-tool loop: model calls grep repeatedly with different patterns
# until it has enough information to synthesize a final answer (end_turn).

def run_grep_agent(task: str, max_turns: int = 10):
    """Run the grep agent until end_turn or max_turns."""
    print(f"\n{'='*70}")
    print(f"TASK: {task}")
    print(f"{'='*70}")

    messages = [{"role": "user", "content": task}]

    # System prompt tells the model it only has grep — forces pattern-search thinking
    system = (
        "You are a codebase search agent. Your only tool is grep — use it to search "
        "for regex patterns across files. You can call grep multiple times with different "
        "patterns to build understanding. When you have enough information, synthesize your "
        f"findings into a clear answer.\nAll files are inside: {SANDBOX}"
    )

    turn = 0
    while turn < max_turns:
        turn += 1
        print(f"\n--- Turn {turn} ---")

        response = client.messages.create(
            model=MODEL,
            max_tokens=2048,
            system=system,
            # Single tool — model must solve everything through pattern search
            tools=[GREP_TOOL],
            messages=messages,
        )

        print(f"  stop_reason: {response.stop_reason}")

        tool_results = []

        for block in response.content:
            if block.type == "text":
                print(f"  AGENT: {block.text}")
            elif block.type == "tool_use":
                inp = block.input
                print(f"  -> grep(pattern={inp['pattern']!r}, "
                      f"dir={inp.get('directory', '.')!r}, "
                      f"file_pattern={inp.get('file_pattern', '*')!r})")

                result = handle_grep(
                    inp["pattern"],
                    inp.get("directory", "."),
                    inp.get("file_pattern"),
                )
                result_str = json.dumps(result)
                print(f"  <- {len(result.get('matches', []))} match(es)")

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result_str,
                })

        # end_turn = model has gathered enough grep results to answer
        if response.stop_reason == "end_turn":
            print(f"\n{'='*70}")
            print(f"Agent completed in {turn} turn(s).")
            break

        # tool_use = model wants to search for more patterns — feed results back
        messages.append({"role": "assistant", "content": response.content})
        messages.append({"role": "user", "content": tool_results})

    if turn >= max_turns:
        print(f"\nAgent hit max_turns limit ({max_turns}).")


# ── Seed Sandbox ─────────────────────────────────────────────────────────────
# Realistic multi-file codebase gives the grep agent meaningful patterns to find.

def seed_sandbox():
    """Create a small codebase the grep agent will search through."""
    files = {
        "src/auth.py": (
            "import hashlib\n"
            "import os\n\n"
            "# TODO: migrate to bcrypt — hashlib is not safe for passwords\n"
            "def hash_password(password: str) -> str:\n"
            "    salt = os.urandom(16).hex()\n"
            "    return hashlib.sha256((salt + password).encode()).hexdigest()\n\n"
            "def verify_password(password: str, hashed: str) -> bool:\n"
            "    # FIXME: broken — salt is not stored separately\n"
            "    return hash_password(password) == hashed\n\n"
            "def create_token(user_id: int) -> str:\n"
            "    # TODO: use JWT instead of homegrown tokens\n"
            "    return hashlib.md5(str(user_id).encode()).hexdigest()\n"
        ),
        "src/api.py": (
            "from flask import Flask, request, jsonify\n"
            "from auth import hash_password, verify_password, create_token\n"
            "from db import get_user, create_user, list_orders\n\n"
            "app = Flask(__name__)\n\n"
            "@app.route('/login', methods=['POST'])\n"
            "def login():\n"
            "    email = request.json['email']\n"
            "    password = request.json['password']\n"
            "    user = get_user(email)\n"
            "    if user and verify_password(password, user['password_hash']):\n"
            "        token = create_token(user['id'])\n"
            "        return jsonify(token=token)\n"
            "    return jsonify(error='Invalid credentials'), 401\n\n"
            "@app.route('/register', methods=['POST'])\n"
            "def register():\n"
            "    # TODO: add input validation\n"
            "    email = request.json['email']\n"
            "    password = request.json['password']\n"
            "    hashed = hash_password(password)\n"
            "    user = create_user(email, hashed)\n"
            "    return jsonify(user_id=user['id']), 201\n\n"
            "@app.route('/orders/<int:user_id>')\n"
            "def orders(user_id):\n"
            "    # HACK: no auth check — anyone can view any user's orders\n"
            "    return jsonify(orders=list_orders(user_id))\n"
        ),
        "src/db.py": (
            "import sqlite3\n\n"
            "DB_PATH = 'app.db'\n\n"
            "def get_connection():\n"
            "    return sqlite3.connect(DB_PATH)\n\n"
            "def get_user(email: str) -> dict:\n"
            "    conn = get_connection()\n"
            "    # WARNING: SQL injection possible if email is not sanitized\n"
            "    row = conn.execute(f\"SELECT * FROM users WHERE email='{email}'\").fetchone()\n"
            "    conn.close()\n"
            "    if row:\n"
            "        return {'id': row[0], 'email': row[1], 'password_hash': row[2]}\n"
            "    return None\n\n"
            "def create_user(email: str, password_hash: str) -> dict:\n"
            "    conn = get_connection()\n"
            "    cursor = conn.execute(\n"
            "        'INSERT INTO users (email, password_hash) VALUES (?, ?)',\n"
            "        (email, password_hash)\n"
            "    )\n"
            "    conn.commit()\n"
            "    user_id = cursor.lastrowid\n"
            "    conn.close()\n"
            "    return {'id': user_id, 'email': email}\n\n"
            "def list_orders(user_id: int) -> list:\n"
            "    conn = get_connection()\n"
            "    rows = conn.execute(\n"
            "        'SELECT id, total, status FROM orders WHERE user_id = ?',\n"
            "        (user_id,)\n"
            "    ).fetchall()\n"
            "    conn.close()\n"
            "    return [{'id': r[0], 'total': r[1], 'status': r[2]} for r in rows]\n"
        ),
        "src/utils.py": (
            "import re\n"
            "import logging\n\n"
            "logger = logging.getLogger(__name__)\n\n"
            "def validate_email(email: str) -> bool:\n"
            "    # TODO: use a proper email validation library\n"
            "    return bool(re.match(r'^[\\w.+-]+@[\\w-]+\\.[\\w.]+$', email))\n\n"
            "def sanitize_html(text: str) -> str:\n"
            "    # FIXME: this is not sufficient for XSS prevention\n"
            "    return re.sub(r'<[^>]+>', '', text)\n\n"
            "def format_currency(amount: float) -> str:\n"
            "    return f'${amount:,.2f}'\n"
        ),
        "tests/test_auth.py": (
            "import pytest\n"
            "from src.auth import hash_password, create_token\n\n"
            "def test_hash_password_returns_string():\n"
            "    result = hash_password('secret123')\n"
            "    assert isinstance(result, str)\n\n"
            "def test_hash_password_not_plaintext():\n"
            "    result = hash_password('secret123')\n"
            "    assert result != 'secret123'\n\n"
            "# TODO: add test for verify_password once salt storage is fixed\n\n"
            "def test_create_token_deterministic():\n"
            "    assert create_token(1) == create_token(1)\n"
        ),
        "config/settings.yaml": (
            "app:\n"
            "  name: OrderService\n"
            "  version: 1.2.0\n"
            "  debug: true\n\n"
            "database:\n"
            "  host: localhost\n"
            "  port: 5432\n"
            "  name: orders_db\n\n"
            "# TODO: add rate limiting config\n"
            "security:\n"
            "  cors_origins: ['*']\n"
            "  session_timeout: 3600\n"
        ),
    }

    for path, content in files.items():
        full = os.path.join(SANDBOX, path)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w") as f:
            f.write(content)

    print(f"Sandbox seeded at: {SANDBOX}")
    for p in files:
        print(f"  - {p}")


# ── Demo Runs ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    seed_sandbox()

    # Demo 1 — Find all TODO/FIXME/HACK comments across the codebase
    # Use case: technical debt audit — grep surfaces every deferred task
    run_grep_agent(
        "Search the codebase for all TODO, FIXME, and HACK comments. "
        "Categorize them by severity and report which files have the most technical debt."
    )

    # Demo 2 — Trace how a symbol is used across files
    # Use case: impact analysis — before changing a function, find all callers
    run_grep_agent(
        "I want to refactor the 'hash_password' function. "
        "Search for everywhere it's defined, imported, or called across the codebase. "
        "Tell me which files I'd need to update."
    )

    # Demo 3 — Security audit via pattern matching
    # Use case: grep catches SQL injection, hardcoded secrets, weak crypto
    run_grep_agent(
        "Do a security scan of the Python files. Search for: "
        "(1) f-string SQL queries (SQL injection risk), "
        "(2) uses of md5 or sha256 for passwords (weak hashing), "
        "(3) any endpoints missing authentication checks. "
        "Report each finding with file, line, and severity."
    )
