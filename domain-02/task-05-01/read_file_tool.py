"""
POC: Built-in Read Tool — Read File Contents (Claude Architect Exam - Domain 02)

Demonstrates the read_file built-in tool in a single-tool agentic loop.
The model reads multiple files to understand code structure, then synthesizes findings.
"""

import os
import json
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

client = Anthropic()
MODEL = os.getenv("MODEL_NAME", "claude-sonnet-4-20250514")

# All file ops scoped to sandbox — prevents accidental reads outside the demo
SANDBOX = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sandbox")
os.makedirs(SANDBOX, exist_ok=True)


# ── Tool Definition ───────────────────────────────────────────────────────────
# Mirrors Claude Code's built-in Read tool. The model receives this schema
# so it knows what arguments it can pass when requesting a file read.

READ_TOOL = {
    "name": "read_file",
    "description": (
        "Read the full contents of a file at the given path. "
        "Returns the file content as a string, or an error if the file does not exist."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Path to the file to read (relative to sandbox).",
            }
        },
        "required": ["file_path"],
    },
}


# ── Tool Handler ──────────────────────────────────────────────────────────────
# The "real world" behind the tool — executes the actual file read when
# the model emits a tool_use block.

def handle_read_file(file_path: str) -> dict:
    # Resolve against sandbox to keep reads contained
    full_path = os.path.join(SANDBOX, file_path) if not os.path.isabs(file_path) else file_path
    try:
        with open(full_path, "r") as f:
            content = f.read()
        return {"content": content, "path": full_path, "size_bytes": len(content.encode())}
    except FileNotFoundError:
        return {"error": f"File not found: {full_path}"}
    except UnicodeDecodeError:
        return {"error": f"Cannot read binary file: {full_path}"}


# ── Agentic Loop ──────────────────────────────────────────────────────────────
# Core exam concept: the loop continues while stop_reason == "tool_use"
# and exits when the model emits "end_turn" (meaning it has enough info
# to answer without further tool calls).

def run_read_agent(task: str):
    """Run the read-file agent loop until the model produces a final answer."""
    print(f"\n{'='*60}")
    print(f"TASK: {task}")
    print(f"{'='*60}")

    messages = [{"role": "user", "content": task}]

    # System prompt constrains the agent to reading — it won't try to write or edit
    system = (
        "You are a file reader agent. Your only capability is reading files using the read_file tool. "
        "Read as many files as needed to fully answer the user's question. "
        f"All files are inside: {SANDBOX}"
    )

    turn = 0
    while True:
        turn += 1
        print(f"\n--- Turn {turn} ---")

        response = client.messages.create(
            model=MODEL,
            max_tokens=1024,
            system=system,
            # Single tool — enforces the "one tool per subagent" pattern
            tools=[READ_TOOL],
            messages=messages,
        )

        print(f"  stop_reason: {response.stop_reason}")

        tool_results = []

        for block in response.content:
            if block.type == "text":
                print(f"  AGENT: {block.text}")
            elif block.type == "tool_use":
                # Model decided it needs to read a file before answering
                print(f"  -> read_file({block.input['file_path']})")
                result = handle_read_file(block.input["file_path"])
                result_str = json.dumps(result)
                print(f"  <- {result_str[:100]}{'...' if len(result_str) > 100 else ''}")
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result_str,
                })

        # stop_reason == "end_turn" means the model is done — no more tool calls needed
        if response.stop_reason == "end_turn":
            print(f"\n{'='*60}")
            print(f"Agent completed in {turn} turn(s).")
            break

        # stop_reason == "tool_use" means the model wants to read more files —
        # feed the tool results back and continue the loop
        messages.append({"role": "assistant", "content": response.content})
        messages.append({"role": "user", "content": tool_results})


# ── Sandbox Seeding ───────────────────────────────────────────────────────────
# Create sample files that give the read agent something meaningful to inspect.

def seed_sandbox():
    """Populate sandbox with files the agent will read and analyze."""
    files = {
        "config.json": json.dumps({
            "app_name": "InventoryService",
            "version": "2.3.1",
            "debug": True,
            "database": {"host": "db.internal", "port": 5432, "name": "inventory"},
            "cache": {"enabled": True, "ttl_seconds": 300},
        }, indent=2),
        "src/models.py": (
            "from dataclasses import dataclass\n"
            "from typing import Optional\n\n"
            "# TODO: add created_at / updated_at timestamps\n"
            "@dataclass\n"
            "class Product:\n"
            "    id: int\n"
            "    name: str\n"
            "    sku: str\n"
            "    price: float\n"
            "    quantity: int\n"
            "    category: Optional[str] = None\n\n"
            "@dataclass\n"
            "class Warehouse:\n"
            "    id: int\n"
            "    name: str\n"
            "    location: str\n"
            "    capacity: int\n"
        ),
        "src/service.py": (
            "import json\n"
            "from models import Product\n\n"
            "def load_config():\n"
            "    with open('config.json') as f:\n"
            "        return json.load(f)\n\n"
            "def get_product(product_id: int) -> Product:\n"
            "    # TODO: replace stub with real DB query\n"
            "    return Product(id=product_id, name='Widget', sku='WDG-001',\n"
            "                   price=9.99, quantity=100)\n\n"
            "def check_stock(product_id: int, requested: int) -> bool:\n"
            "    product = get_product(product_id)\n"
            "    return product.quantity >= requested\n"
        ),
        "tests/test_service.py": (
            "from src.service import check_stock\n\n"
            "def test_check_stock_sufficient():\n"
            "    assert check_stock(1, 50) is True\n\n"
            "def test_check_stock_insufficient():\n"
            "    assert check_stock(1, 200) is False\n"
        ),
    }

    for path, content in files.items():
        full_path = os.path.join(SANDBOX, path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w") as f:
            f.write(content)

    print(f"Sandbox seeded at: {SANDBOX}")
    for path in files:
        print(f"  - {path}")


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    seed_sandbox()

    # Demo 1: Read a single file to understand its structure
    # The agent should make one read_file call and then summarize
    run_read_agent(
        "Read config.json and tell me what database this service connects to "
        "and whether debug mode is on."
    )

    # Demo 2: Read multiple files to build understanding
    # The agent needs multiple turns — read models.py, then service.py —
    # to answer a cross-file question. This shows the agentic loop iterating.
    run_read_agent(
        "I'm new to this codebase. Read the source files in src/ and explain: "
        "what data models exist, what operations are available, "
        "and are there any TODOs or incomplete implementations?"
    )
