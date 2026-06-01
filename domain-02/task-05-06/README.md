# Built-in Glob Tool — File Discovery by Pattern

## What This Demonstrates

The **glob** built-in tool lets Claude discover files matching wildcard patterns (`**/*.py`, `config/*`, `*.test.tsx`). Unlike `grep` (which searches file _contents_), glob matches file _paths_ — making it the right tool for:

- Mapping project structure and layout
- Locating files by type, convention, or directory
- Navigating unfamiliar codebases without reading every file

## How It Works

```
User Task → Claude calls glob("**/*.py") → gets file list
          → Claude calls glob("*.test.*") → gets test files
          → Claude synthesizes → final answer (end_turn)
```

The agentic loop continues while `stop_reason == "tool_use"` and exits on `end_turn`.

## Step-by-Step Setup

### 1. Prerequisites

- Python 3.10+
- Anthropic API key

### 2. Create virtual environment

```bash
cd domain-02/task-05-06
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install anthropic python-dotenv
```

### 4. Configure environment

```bash
cp .env .env.local
# Edit .env.local and set your real API key:
# ANTHROPIC_API_KEY=sk-ant-...
```

Or export directly:

```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

### 5. Run the POC

```bash
python glob_tool_poc.py
```

## What You'll See

The script runs **3 demo tasks**:

| Demo | Task | Glob Use Case |
|------|------|---------------|
| 1 | Map project structure | Onboarding — discover languages & frameworks |
| 2 | Find all test files | CI setup — locate tests across naming conventions |
| 3 | Audit infrastructure | DevOps — find Dockerfiles, CI configs, env templates |

Each demo shows the agent calling `glob()` with different patterns, accumulating results across turns, then synthesizing a final answer.

## Key Exam Concepts

- **Glob vs Grep**: Glob matches file _names/paths_; Grep matches file _contents_. Use glob for navigation, grep for search.
- **Agentic loop**: `stop_reason: tool_use` → feed results back; `stop_reason: end_turn` → done.
- **Tool schema**: `input_schema` tells the model what arguments glob accepts (pattern, directory).
- **Sandbox scoping**: All operations are constrained to a local sandbox directory.
