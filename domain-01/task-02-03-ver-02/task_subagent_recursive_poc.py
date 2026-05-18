"""
POC: Recursive subagent delegation via the Task tool.

Extends task-02-03 by granting selected subagents the Task tool itself,
enabling multi-level delegation: parent → subagent → sub-subagent.

Key design decisions:
  - max_depth caps recursion so the call tree cannot grow unboundedly.
  - Each level's Task tool carries an updated depth counter; when depth
    reaches the limit the Task tool is withheld from that subagent's
    tool list, making it a leaf.
  - SUBAGENT_REGISTRY declares, per agent type, which tools it gets AND
    whether it may delegate further (can_delegate flag).
"""

import os
import json
from dotenv import load_dotenv
import anthropic

load_dotenv()

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
MODEL = os.getenv("MODEL_ID", "claude-sonnet-4-6")
MAX_DEPTH = 3


# ---------------------------------------------------------------------------
# Scoped tool definitions
# ---------------------------------------------------------------------------

web_search_tool = {
    "name": "web_search",
    "description": "Search the web for current information on a topic.",
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query"}
        },
        "required": ["query"]
    }
}

read_doc_tool = {
    "name": "read_doc",
    "description": "Read and extract content from a document or URL.",
    "input_schema": {
        "type": "object",
        "properties": {
            "source": {"type": "string", "description": "Document path or URL"}
        },
        "required": ["source"]
    }
}

extract_data_tool = {
    "name": "extract_data",
    "description": "Extract structured data points from unstructured text.",
    "input_schema": {
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "Raw text to extract from"},
            "fields": {"type": "string", "description": "Comma-separated field names to extract"}
        },
        "required": ["text", "fields"]
    }
}

analyze_deps_tool = {
    "name": "analyze_deps",
    "description": "Analyze technology dependencies and compatibility.",
    "input_schema": {
        "type": "object",
        "properties": {
            "technology": {"type": "string", "description": "Technology to analyze"}
        },
        "required": ["technology"]
    }
}

summarize_tool = {
    "name": "summarize",
    "description": "Summarize a block of text into key bullet points.",
    "input_schema": {
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "Text to summarize"}
        },
        "required": ["text"]
    }
}


# ---------------------------------------------------------------------------
# Subagent registry
# ---------------------------------------------------------------------------
# can_delegate=True means this agent type receives the Task tool (if depth
# budget remains), allowing it to spawn its own subagents.

SUBAGENT_REGISTRY = {
    "market_researcher": {
        "tools": [web_search_tool, read_doc_tool, extract_data_tool],
        "can_delegate": True,
        "delegatable_types": ["data_summarizer"],
    },
    "tech_analyst": {
        "tools": [read_doc_tool, analyze_deps_tool],
        "can_delegate": True,
        "delegatable_types": ["data_summarizer"],
    },
    "data_summarizer": {
        "tools": [summarize_tool],
        "can_delegate": False,
        "delegatable_types": [],
    },
}


def build_task_tool(available_agent_types: list[str]) -> dict:
    """Build a Task tool definition scoped to a subset of agent types."""
    return {
        "name": "Task",
        "description": (
            "Spawn a named subagent to handle a discrete subtask. "
            "The subagent runs independently with its own tool set."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "description": {
                    "type": "string",
                    "description": "Short label for the subtask"
                },
                "prompt": {
                    "type": "string",
                    "description": "Full instructions for the subagent"
                },
                "agent_type": {
                    "type": "string",
                    "enum": available_agent_types,
                    "description": "Which specialist subagent to invoke"
                }
            },
            "required": ["description", "prompt", "agent_type"]
        }
    }


# ---------------------------------------------------------------------------
# Simulated tool execution
# ---------------------------------------------------------------------------

def execute_tool(tool_name: str, tool_input: dict) -> str:
    if tool_name == "web_search":
        return json.dumps({
            "results": [
                f"Top result for '{tool_input['query']}': "
                "Market analysis shows 23% YoY growth in this segment."
            ]
        })
    if tool_name == "read_doc":
        return f"Document content from {tool_input['source']}: [simulated excerpt]"
    if tool_name == "extract_data":
        return json.dumps({
            field.strip(): f"extracted_{field.strip()}_value"
            for field in tool_input["fields"].split(",")
        })
    if tool_name == "analyze_deps":
        return json.dumps({
            "technology": tool_input["technology"],
            "dependencies": ["runtime-A", "lib-B"],
            "compatibility": "stable"
        })
    if tool_name == "summarize":
        text = tool_input["text"]
        return f"Summary: {text[:120]}… [condensed]"
    return f"Unknown tool: {tool_name}"


# ---------------------------------------------------------------------------
# Recursive subagent runner
# ---------------------------------------------------------------------------

def run_subagent(agent_type: str, prompt: str, depth: int = 1) -> str:
    """
    Run a subagent with its own agentic loop.

    If the agent's registry entry has can_delegate=True AND depth < MAX_DEPTH,
    the Task tool is included in its tool set so it can spawn sub-subagents.
    Otherwise the agent is a leaf — it works only with its scoped tools.
    """
    indent = "    " * depth
    entry = SUBAGENT_REGISTRY.get(agent_type)
    if entry is None:
        return f"[error] unknown agent_type: {agent_type}"

    tools = list(entry["tools"])

    can_delegate = entry["can_delegate"] and depth < MAX_DEPTH
    if can_delegate:
        task_tool = build_task_tool(entry["delegatable_types"])
        tools.append(task_tool)

    print(f"{indent}[depth={depth}] [{agent_type}] tools: {[t['name'] for t in tools]}"
          f" | can_delegate={can_delegate}")

    messages = [{"role": "user", "content": prompt}]

    while True:
        response = client.messages.create(
            model=MODEL,
            max_tokens=1024,
            tools=tools,
            messages=messages
        )

        if response.stop_reason == "end_turn":
            break

        tool_results = []
        for block in response.content:
            if block.type != "tool_use":
                continue

            if block.name == "Task":
                task_input = block.input
                child_type = task_input["agent_type"]
                print(f"{indent}  ↳ delegating to {child_type}: "
                      f"{task_input['description']}")
                result = run_subagent(child_type, task_input["prompt"], depth + 1)
            else:
                print(f"{indent}  calling {block.name}("
                      f"{json.dumps(block.input)[:80]})")
                result = execute_tool(block.name, block.input)

            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": result
            })

        if not tool_results:
            break

        messages.append({"role": "assistant", "content": response.content})
        messages.append({"role": "user", "content": tool_results})

    for block in response.content:
        if block.type == "text":
            return block.text
    return "[subagent produced no text output]"


# ---------------------------------------------------------------------------
# Parent (coordinator) agent
# ---------------------------------------------------------------------------

def run_parent_agent():
    all_top_level_types = list(SUBAGENT_REGISTRY.keys())
    parent_task_tool = build_task_tool(all_top_level_types)

    messages = [
        {
            "role": "user",
            "content": (
                "Research the AI infrastructure market. Delegate:\n"
                "1. Market research (trends, growth, key players) → market_researcher\n"
                "   The market_researcher should further delegate summarization "
                "   of raw findings to a data_summarizer subagent.\n"
                "2. Technology analysis (core tech, dependencies, maturity) → tech_analyst\n"
                "   The tech_analyst should further delegate summarization "
                "   of its analysis to a data_summarizer subagent.\n"
                "Synthesize all results into a final report."
            )
        }
    ]

    print(f"=== Parent Agent (max_depth={MAX_DEPTH}) ===\n")

    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        tools=[parent_task_tool],
        messages=messages
    )

    task_calls = []
    for block in response.content:
        if block.type == "tool_use" and block.name == "Task":
            task_calls.append(block)
        elif block.type == "text":
            print(f"Parent says: {block.text}\n")

    if not task_calls:
        print("No subagent delegation requested.")
        return

    messages.append({"role": "assistant", "content": response.content})

    tool_results = []
    for block in task_calls:
        task_input = block.input
        agent_type = task_input["agent_type"]
        print(f"--- Spawning subagent: {task_input['description']} "
              f"(type={agent_type}) ---")
        print(f"    Prompt: {task_input['prompt'][:120]}...")

        result = run_subagent(agent_type, task_input["prompt"], depth=1)
        print(f"    Result: {result[:200]}\n")

        tool_results.append({
            "type": "tool_result",
            "tool_use_id": block.id,
            "content": result
        })

    messages.append({"role": "user", "content": tool_results})

    final = client.messages.create(
        model=MODEL,
        max_tokens=2048,
        tools=[parent_task_tool],
        messages=messages
    )

    print("=== Final Synthesis ===")
    for block in final.content:
        if block.type == "text":
            print(block.text)


if __name__ == "__main__":
    run_parent_agent()
