"""
POC: Task tool for spawning subagents via Anthropic SDK.
Key insight: allowedTools MUST include 'Task' to permit subagent creation.
Each subagent gets scoped tools — only the capabilities relevant to its subtask.
"""

import os
import json
from dotenv import load_dotenv
import anthropic

load_dotenv()

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
MODEL = os.getenv("MODEL_ID", "claude-sonnet-4-6")


# ---------------------------------------------------------------------------
# Tool definitions
# ---------------------------------------------------------------------------

# The Task tool — this is how a parent agent spawns a subagent.
# Without 'Task' in the parent's tools list, the model cannot delegate.
task_tool = {
    "name": "Task",
    "description": (
        "Spawn a named subagent to handle a discrete subtask independently. "
        "Choose agent_type to route to the right specialist."
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
                "description": "Full instructions for the subagent (include ALL context it needs)"
            },
            "agent_type": {
                "type": "string",
                "enum": ["market_researcher", "tech_analyst"],
                "description": "Which specialist subagent to invoke"
            }
        },
        "required": ["description", "prompt", "agent_type"]
    }
}

# Scoped tools per subagent type — each specialist gets only what it needs.
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

# Subagent registry: agent_type -> scoped tool list
SUBAGENT_TOOLS = {
    "market_researcher": [web_search_tool, read_doc_tool, extract_data_tool],
    "tech_analyst": [read_doc_tool, analyze_deps_tool],
}


# ---------------------------------------------------------------------------
# Simulated tool execution (in production, these would call real services)
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
    return f"Unknown tool: {tool_name}"


# ---------------------------------------------------------------------------
# Subagent runner (agentic loop with scoped tools)
# ---------------------------------------------------------------------------

def run_subagent(agent_type: str, prompt: str) -> str:
    """
    Run a subagent with its own agentic loop and scoped tools.
    The subagent sees ONLY the prompt it receives — full context isolation.
    """
    tools = SUBAGENT_TOOLS.get(agent_type, [])
    messages = [{"role": "user", "content": prompt}]

    print(f"    [{agent_type}] tools available: {[t['name'] for t in tools]}")

    while True:
        response = client.messages.create(
            model=MODEL,
            max_tokens=1024,
            tools=tools,
            messages=messages
        )

        if response.stop_reason == "end_turn":
            break

        # Process any tool calls the subagent makes
        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                print(f"    [{agent_type}] calling tool: {block.name}({json.dumps(block.input)[:80]})")
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

    # Return the final text output
    for block in response.content:
        if block.type == "text":
            return block.text
    return "[subagent produced no text output]"


# ---------------------------------------------------------------------------
# Parent (coordinator) agent
# ---------------------------------------------------------------------------

def run_parent_agent():
    """Parent agent that delegates subtasks via the Task tool."""

    messages = [
        {
            "role": "user",
            "content": (
                "Research the AI infrastructure market. Delegate:\n"
                "1. Market research (trends, growth, key players) → market_researcher\n"
                "2. Technology analysis (core tech, dependencies, maturity) → tech_analyst\n"
                "Pass each subagent ONLY the context relevant to their task."
            )
        }
    ]

    print("=== Parent Agent: Requesting subtask delegation ===\n")

    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        tools=[task_tool],   # Task MUST be listed here to enable subagent spawning
        messages=messages
    )

    # Collect all tool_use blocks, then append the assistant message ONCE
    task_calls = []
    for block in response.content:
        if block.type == "tool_use" and block.name == "Task":
            task_calls.append(block)
        elif block.type == "text":
            print(f"Parent says: {block.text}\n")

    if not task_calls:
        print("No subagent delegation requested.")
        return

    # Append the assistant turn once (fixes multi-append bug)
    messages.append({"role": "assistant", "content": response.content})

    # Execute each subagent and collect results into a single tool_result turn
    tool_results = []
    for block in task_calls:
        task_input = block.input
        agent_type = task_input["agent_type"]
        print(f"--- Spawning subagent: {task_input['description']} (type={agent_type}) ---")
        print(f"    Prompt: {task_input['prompt'][:100]}...")

        result = run_subagent(agent_type, task_input["prompt"])
        print(f"    Result: {result[:200]}\n")

        tool_results.append({
            "type": "tool_result",
            "tool_use_id": block.id,
            "content": result
        })

    # Feed ALL subagent results back in one user turn
    messages.append({"role": "user", "content": tool_results})

    # Final synthesis
    final = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        tools=[task_tool],
        messages=messages
    )

    print("=== Final Synthesis ===")
    for block in final.content:
        if block.type == "text":
            print(block.text)


if __name__ == "__main__":
    run_parent_agent()
