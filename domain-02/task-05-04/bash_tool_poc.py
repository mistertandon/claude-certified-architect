"""
POC: Built-in Bash Tool — Shell Command Execution (Claude Architect Exam - Domain 02)

Demonstrates the Bash built-in tool in an agentic loop.
The model executes shell commands for building, testing, and system inspection —
the same mechanism Claude Code uses when running commands on your behalf.
"""

import os
import json
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

client = Anthropic()
MODEL = os.getenv("MODEL_NAME", "claude-sonnet-4-20250514")

# Sandbox isolates all shell commands — prevents accidental writes to real directories
SANDBOX = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sandbox")
os.makedirs(SANDBOX, exist_ok=True)


# ── Tool Definition ──────────────────────────────────────────────────────────
# Schema mirrors Claude Code's built-in Bash tool. The model sees this schema
# and knows it can request arbitrary shell command execution.

BASH_TOOL = {
    "name": "bash",
    "description": (
        "Execute a shell command and return stdout, stderr, and exit code. "
        "Use for building, testing, linting, listing files, or any system operation. "
        "Commands run inside the sandbox directory."
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


# ── Tool Handler ─────────────────────────────────────────────────────────────
# Translates the model's tool_use request into an actual subprocess execution.
# This is the boundary between model reasoning and real-world side effects.

def handle_bash(command: str) -> dict:
    import subprocess

    # cwd=SANDBOX so relative paths in commands resolve inside the sandbox
    result = subprocess.run(
        command,
        shell=True,
        capture_output=True,
        text=True,
        cwd=SANDBOX,
        # Timeout prevents runaway commands from blocking the loop indefinitely
        timeout=30,
    )
    return {
        "stdout": result.stdout,
        "stderr": result.stderr,
        "exit_code": result.returncode,
    }


# ── Agentic Loop ─────────────────────────────────────────────────────────────
# stop_reason drives the loop: "tool_use" means the model wants another command,
# "end_turn" means the model has enough information to answer.

def run_bash_agent(task: str, max_turns: int = 10):
    """Run the bash-only agent until end_turn or max_turns reached."""
    print(f"\n{'='*70}")
    print(f"TASK: {task}")
    print(f"{'='*70}")

    messages = [{"role": "user", "content": task}]

    system = (
        "You are a shell agent. Your only tool is bash — use it to execute "
        "shell commands for building, testing, and inspecting the system. "
        f"All commands run inside: {SANDBOX}\n"
        "Work step by step. After each command, decide if you need more "
        "commands or if you have enough information to answer."
    )

    turn = 0
    while turn < max_turns:
        turn += 1
        print(f"\n--- Turn {turn} ---")

        response = client.messages.create(
            model=MODEL,
            max_tokens=2048,
            system=system,
            # Single tool — the model can only call bash
            tools=[BASH_TOOL],
            messages=messages,
        )

        print(f"  stop_reason: {response.stop_reason}")

        tool_results = []

        for block in response.content:
            if block.type == "text":
                print(f"  AGENT: {block.text}")
            elif block.type == "tool_use":
                cmd = block.input["command"]
                print(f"  $ {cmd}")

                result = handle_bash(cmd)
                result_str = json.dumps(result)
                # Truncate long outputs in console — model still sees full result
                preview = result_str[:200]
                print(f"  <- {preview}{'...' if len(result_str) > 200 else ''}")

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    # Full result fed back so the model can reason over complete output
                    "content": result_str,
                })

        # end_turn = model is done, no more shell commands needed
        if response.stop_reason == "end_turn":
            print(f"\n{'='*70}")
            print(f"Agent completed in {turn} turn(s).")
            break

        # tool_use = model wants to run more commands — append results and loop
        messages.append({"role": "assistant", "content": response.content})
        messages.append({"role": "user", "content": tool_results})

    if turn >= max_turns:
        print(f"\nAgent hit max_turns limit ({max_turns}).")


# ── Sandbox Seeding ──────────────────────────────────────────────────────────
# Pre-populate sandbox with a small Python project so the bash agent
# has something meaningful to build, test, and inspect.

def seed_sandbox():
    """Create a mini project the bash agent will operate on."""
    files = {
        "src/calculator.py": (
            "def add(a: float, b: float) -> float:\n"
            "    return a + b\n\n"
            "def subtract(a: float, b: float) -> float:\n"
            "    return a - b\n\n"
            "def multiply(a: float, b: float) -> float:\n"
            "    return a * b\n\n"
            "def divide(a: float, b: float) -> float:\n"
            "    if b == 0:\n"
            "        raise ValueError('Cannot divide by zero')\n"
            "    return a / b\n"
        ),
        "tests/test_calculator.py": (
            "import sys, os\n"
            "sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))\n\n"
            "from calculator import add, subtract, multiply, divide\n"
            "import pytest\n\n"
            "def test_add():\n"
            "    assert add(2, 3) == 5\n\n"
            "def test_subtract():\n"
            "    assert subtract(10, 4) == 6\n\n"
            "def test_multiply():\n"
            "    assert multiply(3, 7) == 21\n\n"
            "def test_divide():\n"
            "    assert divide(10, 2) == 5.0\n\n"
            "def test_divide_by_zero():\n"
            "    with pytest.raises(ValueError):\n"
            "        divide(1, 0)\n"
        ),
        "Makefile": (
            "test:\n"
            "\tpython -m pytest tests/ -v\n\n"
            "lint:\n"
            "\tpython -m py_compile src/calculator.py\n\n"
            "structure:\n"
            "\tfind . -type f -name '*.py' | head -20\n"
        ),
        "requirements.txt": "pytest>=7.0.0\n",
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
# Each demo targets a distinct bash use case: build, test, system ops.

if __name__ == "__main__":
    seed_sandbox()

    # Demo 1 — System inspection: discover project structure and file contents
    # Use case: understanding an unfamiliar codebase via shell commands
    run_bash_agent(
        "Explore this project. List the directory structure, then read the "
        "source files and the Makefile. Summarize what this project does."
    )

    # Demo 2 — Testing: run the test suite and interpret results
    # Use case: CI/CD validation — the agent acts as a test runner
    run_bash_agent(
        "Run the test suite using 'make test'. Report which tests passed "
        "or failed and the overall result."
    )

    # Demo 3 — Build validation: compile-check and lint the source code
    # Use case: pre-commit checks — catch syntax errors before they ship
    run_bash_agent(
        "Lint the project by running 'make lint'. Also check if there are "
        "any syntax errors in the Python files using py_compile. "
        "Report whether the code is clean."
    )

    # Demo 4 — Multi-step operations: combine discovery + analysis
    # Use case: the agent chains multiple commands to answer a complex question
    run_bash_agent(
        "Count the total lines of Python code in this project, find which "
        "file has the most lines, and check what dependencies are listed "
        "in requirements.txt. Give me a project health summary."
    )
