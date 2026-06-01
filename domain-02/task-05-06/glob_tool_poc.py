"""
POC: Built-in Glob Tool — File Discovery by Pattern (Claude Architect Exam - Domain 02)

Demonstrates the glob built-in tool in an agentic loop.
The model discovers files matching glob patterns (e.g., **/*.py, config/*)
to navigate and understand a codebase's structure — without listing every file.
"""

import os
import json
import fnmatch
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

client = Anthropic()
MODEL = os.getenv("MODEL_NAME", "claude-sonnet-4-20250514")

# Sandbox scopes all glob searches — prevents the model from scanning outside the demo
SANDBOX = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sandbox")
os.makedirs(SANDBOX, exist_ok=True)


# ── Tool Definition ──────────────────────────────────────────────────────────
# Schema mirrors Claude Code's built-in glob — pattern-based file discovery.
# Unlike grep (content search), glob only matches file/directory NAMES,
# making it the right tool for navigation and structure understanding.

GLOB_TOOL = {
    "name": "glob",
    "description": (
        "Find files matching a glob pattern in a directory tree. "
        "Returns a list of matching file paths. "
        "Use for discovering project structure, locating config files, "
        "finding all files of a certain type, or navigating unfamiliar codebases. "
        "Supports **, *, and ? wildcards."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "pattern": {
                "type": "string",
                "description": (
                    "Glob pattern to match against file paths. "
                    "Examples: '**/*.py' (all Python files), 'config/*' (top-level config), "
                    "'src/**/*.test.js' (all JS test files under src)."
                ),
            },
            "directory": {
                "type": "string",
                "description": "Starting directory (relative to sandbox). Defaults to '.' for root.",
            },
        },
        "required": ["pattern"],
    },
}


# ── Tool Handler ─────────────────────────────────────────────────────────────
# Walks the tree and applies fnmatch against relative paths.
# Returns sorted paths — deterministic output helps the model reason consistently.

def handle_glob(pattern: str, directory: str = ".") -> dict:
    search_dir = os.path.join(SANDBOX, directory)

    if not os.path.isdir(search_dir):
        return {"error": f"Directory not found: {directory}", "matches": []}

    matches = []
    for root, dirs, files in os.walk(search_dir):
        for name in files:
            full_path = os.path.join(root, name)
            # Relative paths let the model reference files without knowing the sandbox location
            rel_path = os.path.relpath(full_path, SANDBOX)
            # fnmatch against full relative path — enables ** patterns like 'src/**/*.py'
            if fnmatch.fnmatch(rel_path, pattern):
                matches.append(rel_path)

    # Sorting makes output predictable — model can compare across multiple glob calls
    matches.sort()
    return {"matches": matches, "total": len(matches)}


# ── Agentic Loop ─────────────────────────────────────────────────────────────
# Single-tool loop: model calls glob repeatedly with different patterns
# until it maps enough of the structure to answer (end_turn).

def run_glob_agent(task: str, max_turns: int = 10):
    """Run the glob agent until end_turn or max_turns."""
    print(f"\n{'='*70}")
    print(f"TASK: {task}")
    print(f"{'='*70}")

    messages = [{"role": "user", "content": task}]

    # System prompt constrains the model to glob-only thinking — discovery, not content
    system = (
        "You are a codebase navigator agent. Your only tool is glob — use it to discover "
        "files by matching patterns against their paths. You can call glob multiple times "
        "with different patterns to explore the project structure. When you have enough "
        f"information, synthesize your findings into a clear answer.\nAll files are inside: {SANDBOX}"
    )

    turn = 0
    while turn < max_turns:
        turn += 1
        print(f"\n--- Turn {turn} ---")

        response = client.messages.create(
            model=MODEL,
            max_tokens=2048,
            system=system,
            # Single tool — model must solve everything through pattern-based file discovery
            tools=[GLOB_TOOL],
            messages=messages,
        )

        print(f"  stop_reason: {response.stop_reason}")

        tool_results = []

        for block in response.content:
            if block.type == "text":
                print(f"  AGENT: {block.text}")
            elif block.type == "tool_use":
                inp = block.input
                print(f"  -> glob(pattern={inp['pattern']!r}, "
                      f"dir={inp.get('directory', '.')!r})")

                result = handle_glob(
                    inp["pattern"],
                    inp.get("directory", "."),
                )
                result_str = json.dumps(result)
                print(f"  <- {len(result.get('matches', []))} file(s) found")

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result_str,
                })

        # end_turn = model has discovered enough files to answer the question
        if response.stop_reason == "end_turn":
            print(f"\n{'='*70}")
            print(f"Agent completed in {turn} turn(s).")
            break

        # tool_use = model wants to probe more patterns — feed results back
        messages.append({"role": "assistant", "content": response.content})
        messages.append({"role": "user", "content": tool_results})

    if turn >= max_turns:
        print(f"\nAgent hit max_turns limit ({max_turns}).")


# ── Seed Sandbox ─────────────────────────────────────────────────────────────
# Realistic multi-language project with nested dirs, configs, tests, and docs.
# Glob shines here because the model needs to FIND files before reasoning about them.

def seed_sandbox():
    """Create a realistic project tree the glob agent will navigate."""
    files = {
        # Python backend
        "backend/src/app.py": "from flask import Flask\napp = Flask(__name__)\n",
        "backend/src/auth/login.py": "def login(email, password): ...\n",
        "backend/src/auth/oauth.py": "def google_oauth(): ...\n",
        "backend/src/auth/__init__.py": "",
        "backend/src/models/user.py": "class User:\n    pass\n",
        "backend/src/models/order.py": "class Order:\n    pass\n",
        "backend/src/models/__init__.py": "",
        "backend/tests/test_login.py": "def test_login(): assert True\n",
        "backend/tests/test_oauth.py": "def test_oauth(): assert True\n",
        "backend/tests/test_models.py": "def test_user(): assert True\n",
        "backend/requirements.txt": "flask==3.0.0\npytest==8.0.0\nSQLAlchemy==2.0.0\n",
        "backend/Dockerfile": "FROM python:3.12\nCOPY . /app\n",
        # Frontend
        "frontend/src/App.tsx": "export default function App() { return <div/>; }\n",
        "frontend/src/components/Header.tsx": "export function Header() { return <h1/>; }\n",
        "frontend/src/components/Footer.tsx": "export function Footer() { return <footer/>; }\n",
        "frontend/src/hooks/useAuth.ts": "export function useAuth() { return {}; }\n",
        "frontend/src/hooks/useOrders.ts": "export function useOrders() { return []; }\n",
        "frontend/src/utils/api.ts": "export const fetchAPI = () => fetch('/api');\n",
        "frontend/src/__tests__/App.test.tsx": "test('renders', () => {});\n",
        "frontend/src/__tests__/Header.test.tsx": "test('header', () => {});\n",
        "frontend/package.json": '{"name": "frontend", "dependencies": {"react": "^18"}}\n',
        "frontend/tsconfig.json": '{"compilerOptions": {"strict": true}}\n',
        # Config / infra
        "config/nginx.conf": "server { listen 80; }\n",
        "config/docker-compose.yml": "services:\n  app:\n    build: ./backend\n",
        "config/env.example": "DATABASE_URL=postgres://localhost/app\nSECRET_KEY=changeme\n",
        # CI/CD
        ".github/workflows/ci.yml": "name: CI\non: push\njobs:\n  test:\n    runs-on: ubuntu-latest\n",
        ".github/workflows/deploy.yml": "name: Deploy\non:\n  push:\n    branches: [main]\n",
        ".github/CODEOWNERS": "* @backend-team\nfrontend/ @frontend-team\n",
        # Docs
        "docs/architecture.md": "# Architecture\nMonorepo with backend + frontend.\n",
        "docs/api-spec.yaml": "openapi: 3.0.0\npaths: {}\n",
        # Root files
        "README.md": "# MyProject\nA full-stack app.\n",
        ".gitignore": "node_modules/\n__pycache__/\n*.pyc\n.env\n",
        "Makefile": "test:\n\tpytest backend/\n\tnpm test --prefix frontend/\n",
    }

    for path, content in files.items():
        full = os.path.join(SANDBOX, path)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w") as f:
            f.write(content)

    print(f"Sandbox seeded at: {SANDBOX}")
    print(f"  Total files: {len(files)}")
    for p in sorted(files):
        print(f"  - {p}")


# ── Demo Runs ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    seed_sandbox()

    # Demo 1 — Map the project structure by language/type
    # Use case: onboarding — glob reveals what languages/frameworks are in play
    run_glob_agent(
        "I just joined this project. Use glob to discover what types of files exist "
        "(Python, TypeScript, YAML, Dockerfile, etc.) and map out the project structure. "
        "Tell me what frameworks and languages this project uses."
    )

    # Demo 2 — Locate all test files across a polyglot repo
    # Use case: CI setup — glob finds tests regardless of naming conventions
    run_glob_agent(
        "Find ALL test files in this project. They might follow different naming "
        "conventions: test_*.py, *.test.tsx, *.spec.ts, etc. "
        "Report where tests live and which parts of the codebase lack test coverage."
    )

    # Demo 3 — Find configuration and infrastructure files
    # Use case: DevOps audit — glob locates Dockerfiles, CI configs, env templates
    run_glob_agent(
        "I need to audit the infrastructure setup. Find all configuration files: "
        "Dockerfiles, docker-compose files, CI/CD workflows, nginx configs, "
        "and environment templates. Group them by purpose."
    )
