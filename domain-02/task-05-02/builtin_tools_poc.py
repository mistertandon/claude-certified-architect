"""
POC: Built-in Tools — Write, Edit, Bash, Grep, Glob (Claude Architect Exam - Domain 02)

Demonstrates five built-in tools in a single multi-tool agentic loop.
The agent scaffolds a project, modifies it, searches it, and validates it —
all through tool calls orchestrated by the model.
"""

import os
import json
import subprocess
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

client = Anthropic()
MODEL = os.getenv("MODEL_NAME", "claude-sonnet-4-20250514")

# Sandbox prevents file operations from escaping the demo directory
SANDBOX = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sandbox")
os.makedirs(SANDBOX, exist_ok=True)


# ── Tool Definitions ─────────────────────────────────────────────────────────
# Each dict mirrors the JSON schema Claude Code sends to the model.
# The model picks which tool(s) to call based on these schemas.

WRITE_TOOL = {
    "name": "write_file",
    "description": (
        "Create a new file at the given path with the provided content. "
        "Overwrites if the file already exists. Use for generating files from scratch."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Path to the file to create (relative to sandbox).",
            },
            "content": {
                "type": "string",
                "description": "Full content to write into the file.",
            },
        },
        "required": ["file_path", "content"],
    },
}

EDIT_TOOL = {
    "name": "edit_file",
    "description": (
        "Apply a targeted edit to an existing file by replacing an exact substring "
        "(old_string) with a new substring (new_string). "
        "old_string must match exactly one location in the file."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Path to the file to edit (relative to sandbox).",
            },
            "old_string": {
                "type": "string",
                "description": "The exact text to find and replace (must be unique in file).",
            },
            "new_string": {
                "type": "string",
                "description": "The replacement text.",
            },
        },
        "required": ["file_path", "old_string", "new_string"],
    },
}

BASH_TOOL = {
    "name": "bash",
    "description": (
        "Execute a shell command and return its stdout, stderr, and exit code. "
        "Use for building, testing, listing files, or any system operation."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "The shell command to execute.",
            },
        },
        "required": ["command"],
    },
}

GREP_TOOL = {
    "name": "grep",
    "description": (
        "Search for a regex pattern across files in a directory. "
        "Returns matching lines with file paths and line numbers. "
        "Use for finding patterns, symbols, or strings across a codebase."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "pattern": {
                "type": "string",
                "description": "Regex pattern to search for.",
            },
            "directory": {
                "type": "string",
                "description": "Directory to search in (relative to sandbox). Defaults to '.'",
            },
            "file_pattern": {
                "type": "string",
                "description": "Glob to filter files, e.g. '*.py'. Optional.",
            },
        },
        "required": ["pattern"],
    },
}

GLOB_TOOL = {
    "name": "glob",
    "description": (
        "Find files matching a glob pattern for discovery and navigation. "
        "Returns a list of matching file paths relative to the search directory."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "pattern": {
                "type": "string",
                "description": "Glob pattern, e.g. '**/*.py' or 'src/**/*.json'.",
            },
            "directory": {
                "type": "string",
                "description": "Base directory for the search (relative to sandbox). Defaults to '.'",
            },
        },
        "required": ["pattern"],
    },
}

ALL_TOOLS = [WRITE_TOOL, EDIT_TOOL, BASH_TOOL, GREP_TOOL, GLOB_TOOL]


# ── Tool Handlers ────────────────────────────────────────────────────────────
# Each handler is the "real world" behind a tool — the code that actually
# executes when the model emits a tool_use block for that tool.

def _resolve(path: str) -> str:
    """Anchor all paths to sandbox — single choke point for path safety."""
    if os.path.isabs(path):
        return path
    return os.path.join(SANDBOX, path)


def handle_write_file(file_path: str, content: str) -> dict:
    full = _resolve(file_path)
    # Parent dirs created automatically — matches Claude Code behavior
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w") as f:
        f.write(content)
    return {"status": "created", "path": full, "size_bytes": len(content.encode())}


def handle_edit_file(file_path: str, old_string: str, new_string: str) -> dict:
    full = _resolve(file_path)
    try:
        with open(full, "r") as f:
            original = f.read()
    except FileNotFoundError:
        return {"error": f"File not found: {full}"}

    count = original.count(old_string)
    # Uniqueness constraint prevents ambiguous edits — same as Claude Code's Edit tool
    if count == 0:
        return {"error": "old_string not found in file"}
    if count > 1:
        return {"error": f"old_string matches {count} locations — must be unique"}

    updated = original.replace(old_string, new_string, 1)
    with open(full, "w") as f:
        f.write(updated)
    return {"status": "edited", "path": full, "replacements": 1}


def handle_bash(command: str) -> dict:
    # cwd set to sandbox so relative commands resolve correctly
    result = subprocess.run(
        command, shell=True, capture_output=True, text=True,
        cwd=SANDBOX, timeout=30
    )
    return {
        "stdout": result.stdout,
        "stderr": result.stderr,
        "exit_code": result.returncode,
    }


def handle_grep(pattern: str, directory: str = ".", file_pattern: str = None) -> dict:
    search_dir = _resolve(directory)
    matches = []
    import re
    compiled = re.compile(pattern)

    for root, _, files in os.walk(search_dir):
        for fname in files:
            # Optional file_pattern filter — mirrors --include in grep
            if file_pattern and not __import__("fnmatch").fnmatch(fname, file_pattern):
                continue
            fpath = os.path.join(root, fname)
            try:
                with open(fpath, "r") as f:
                    for lineno, line in enumerate(f, 1):
                        if compiled.search(line):
                            rel = os.path.relpath(fpath, SANDBOX)
                            matches.append(f"{rel}:{lineno}: {line.rstrip()}")
            except (UnicodeDecodeError, PermissionError):
                continue

    return {"matches": matches, "total": len(matches)}


def handle_glob(pattern: str, directory: str = ".") -> dict:
    import glob as glob_mod
    search_dir = _resolve(directory)
    # recursive=True enables ** patterns for deep directory traversal
    full_pattern = os.path.join(search_dir, pattern)
    hits = glob_mod.glob(full_pattern, recursive=True)
    # Return relative paths — cleaner for the model to reason about
    rel_hits = [os.path.relpath(h, SANDBOX) for h in hits]
    return {"files": sorted(rel_hits), "total": len(rel_hits)}


# Dispatch table — maps tool names to their handlers
HANDLERS = {
    "write_file": lambda inp: handle_write_file(inp["file_path"], inp["content"]),
    "edit_file": lambda inp: handle_edit_file(inp["file_path"], inp["old_string"], inp["new_string"]),
    "bash": lambda inp: handle_bash(inp["command"]),
    "grep": lambda inp: handle_grep(inp["pattern"], inp.get("directory", "."), inp.get("file_pattern")),
    "glob": lambda inp: handle_glob(inp["pattern"], inp.get("directory", ".")),
}


# ── Agentic Loop ─────────────────────────────────────────────────────────────
# Core exam concept: the loop runs until stop_reason != "tool_use".
# Unlike task-05-01 (single tool), this loop routes to multiple handlers
# based on the tool name the model selects.

def run_agent(task: str, max_turns: int = 15):
    """Run the multi-tool agent until end_turn or max_turns reached."""
    print(f"\n{'='*70}")
    print(f"TASK: {task}")
    print(f"{'='*70}")

    messages = [{"role": "user", "content": task}]

    system = (
        "You are a code agent with five tools: write_file, edit_file, bash, grep, glob. "
        "Use them to accomplish the user's task step by step. "
        f"All file paths are relative to the sandbox directory: {SANDBOX}\n"
        "Work methodically: discover → create → modify → verify."
    )

    turn = 0
    while turn < max_turns:
        turn += 1
        print(f"\n--- Turn {turn} ---")

        response = client.messages.create(
            model=MODEL,
            max_tokens=4096,
            system=system,
            # All five tools available — model decides which to use per turn
            tools=ALL_TOOLS,
            messages=messages,
        )

        print(f"  stop_reason: {response.stop_reason}")

        tool_results = []

        for block in response.content:
            if block.type == "text":
                print(f"  AGENT: {block.text}")
            elif block.type == "tool_use":
                tool_name = block.name
                print(f"  -> {tool_name}({json.dumps(block.input)[:120]})")

                handler = HANDLERS.get(tool_name)
                if handler:
                    result = handler(block.input)
                else:
                    result = {"error": f"Unknown tool: {tool_name}"}

                result_str = json.dumps(result)
                print(f"  <- {result_str[:120]}{'...' if len(result_str) > 120 else ''}")

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result_str,
                })

        # end_turn = model is satisfied, no more tool calls needed
        if response.stop_reason == "end_turn":
            print(f"\n{'='*70}")
            print(f"Agent completed in {turn} turn(s).")
            break

        # tool_use = model wants to do more — feed results back and continue
        messages.append({"role": "assistant", "content": response.content})
        messages.append({"role": "user", "content": tool_results})

    if turn >= max_turns:
        print(f"\nAgent hit max_turns limit ({max_turns}).")


# ── Seed Sandbox ─────────────────────────────────────────────────────────────
# Pre-populate sandbox with files that the agent can discover, search, and edit.

def seed_sandbox():
    """Create starter files the agent will work with."""
    files = {
        "src/app.py": (
            "from flask import Flask, jsonify\n\n"
            "app = Flask(__name__)\n\n"
            "@app.route('/health')\n"
            "def health():\n"
            "    return jsonify(status='ok')\n\n"
            "@app.route('/users')\n"
            "def list_users():\n"
            "    # TODO: implement database query\n"
            "    return jsonify(users=[])\n\n"
            "if __name__ == '__main__':\n"
            "    app.run(debug=True)\n"
        ),
        "src/models.py": (
            "class User:\n"
            "    def __init__(self, id, name, email):\n"
            "        self.id = id\n"
            "        self.name = name\n"
            "        self.email = email\n\n"
            "    def to_dict(self):\n"
            "        return {'id': self.id, 'name': self.name, 'email': self.email}\n"
        ),
        "src/utils.py": (
            "import re\n\n"
            "def validate_email(email):\n"
            "    # TODO: improve regex\n"
            "    pattern = r'^[a-zA-Z0-9+_.-]+@[a-zA-Z0-9.-]+$'\n"
            "    return bool(re.match(pattern, email))\n\n"
            "def sanitize_input(text):\n"
            "    # TODO: add XSS protection\n"
            "    return text.strip()\n"
        ),
        "config/settings.json": json.dumps({
            "app_name": "UserService",
            "version": "1.0.0",
            "debug": True,
            "port": 5000,
        }, indent=2),
        "requirements.txt": "flask==3.0.0\nrequests==2.31.0\n",
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

    # Demo 1 — Write: Agent creates a new test file from scratch
    # Exercises: write_file
    run_agent(
        "Create a new file 'tests/test_utils.py' with pytest unit tests for the "
        "validate_email and sanitize_input functions in src/utils.py. "
        "First read src/utils.py using bash (cat), then write the test file."
    )

    # Demo 2 — Edit: Agent applies a targeted fix to an existing file
    # Exercises: edit_file (and optionally bash to verify)
    run_agent(
        "In src/app.py, the /users endpoint returns an empty list. "
        "Edit it to return a hardcoded list of two sample users instead. "
        "Use the edit_file tool with old_string/new_string to make a surgical change."
    )

    # Demo 3 — Bash: Agent runs shell commands to inspect and validate
    # Exercises: bash
    run_agent(
        "Run shell commands to: (1) list all files recursively in the sandbox, "
        "(2) count total lines of Python code, and (3) check if flask is in requirements.txt."
    )

    # Demo 4 — Grep: Agent searches for patterns across the codebase
    # Exercises: grep
    run_agent(
        "Search the entire sandbox for all TODO comments. "
        "Report each one with its file path and line number."
    )

    # Demo 5 — Glob: Agent discovers files by pattern
    # Exercises: glob
    run_agent(
        "Use the glob tool to find all Python files (*.py) in the sandbox, "
        "then find all JSON config files. List what you found."
    )
