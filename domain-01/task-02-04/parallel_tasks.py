"""
POC: Parallel Subagent Execution via Multiple Task Calls in a Single Response

Demonstrates the full coordinator → parallel dispatch → synthesis pattern:
1. A coordinator agent receives a high-level goal.
2. It responds with multiple tool_use blocks (one Task per subagent) in a SINGLE turn.
3. The runtime executes all Task calls concurrently (asyncio.gather).
4. The coordinator synthesizes results from all subagents.
"""

import asyncio
import json
import time
from anthropic import AsyncAnthropic

client = AsyncAnthropic()

TASK_TOOL = {
    "name": "Task",
    "description": "Spawn an independent subagent to perform a scoped task. "
    "Multiple Task calls in one response are executed in parallel.",
    "input_schema": {
        "type": "object",
        "properties": {
            "agent_name": {
                "type": "string",
                "description": "Name of the specialist subagent.",
            },
            "prompt": {
                "type": "string",
                "description": "The task prompt scoped to this subagent.",
            },
        },
        "required": ["agent_name", "prompt"],
    },
}

COORDINATOR_GOAL = (
    "Analyze this Python snippet: `def add(a, b): return a - b`.\n"
    "Delegate the following to specialist subagents using the Task tool — "
    "issue ALL Task calls in a single response so they run in parallel:\n"
    "1. code_reviewer — review the snippet for bugs\n"
    "2. doc_writer — write a one-line docstring for the function\n"
    "3. test_generator — suggest one pytest test case name for this function"
)


async def coordinator_turn() -> list[dict]:
    """
    Step 1: The coordinator model produces multiple tool_use blocks
    in a single response — each one is a Task call for a subagent.
    """
    response = await client.messages.create(
        model="claude-sonnet-4-6-20250514",
        max_tokens=1024,
        system=(
            "You are a coordinator agent. You delegate work to specialist "
            "subagents by calling the Task tool. Always issue ALL Task calls "
            "in a single response so they can run in parallel."
        ),
        tools=[TASK_TOOL],
        messages=[{"role": "user", "content": COORDINATOR_GOAL}],
    )

    tool_calls = [block for block in response.content if block.type == "tool_use"]

    print(f"\n{'='*60}")
    print(f"  Coordinator emitted {len(tool_calls)} Task calls in ONE response")
    print(f"{'='*60}")
    for tc in tool_calls:
        print(f"  → Task(agent={tc.input['agent_name']})")

    return tool_calls


async def run_subagent(tool_call) -> dict:
    """
    Step 2 (per subagent): Execute a single Task tool_use block.
    Each subagent gets its own scoped system prompt and isolated context.
    """
    agent_name = tool_call.input["agent_name"]
    prompt = tool_call.input["prompt"]

    response = await client.messages.create(
        model="claude-sonnet-4-6-20250514",
        max_tokens=200,
        system=f"You are a specialized '{agent_name}' agent. Be concise.",
        messages=[{"role": "user", "content": prompt}],
    )
    return {
        "tool_use_id": tool_call.id,
        "agent": agent_name,
        "result": response.content[0].text,
    }


async def synthesize(tool_calls, subagent_results) -> str:
    """
    Step 3: Feed all subagent results back to the coordinator as tool_result
    blocks so it can synthesize a final answer.
    """
    tool_result_blocks = [
        {
            "type": "tool_result",
            "tool_use_id": r["tool_use_id"],
            "content": json.dumps({"agent": r["agent"], "output": r["result"]}),
        }
        for r in subagent_results
    ]

    response = await client.messages.create(
        model="claude-sonnet-4-6-20250514",
        max_tokens=512,
        system="You are a coordinator agent. Synthesize the subagent results into a brief summary.",
        tools=[TASK_TOOL],
        messages=[
            {"role": "user", "content": COORDINATOR_GOAL},
            {"role": "assistant", "content": [block.__dict__ for block in tool_calls]},
            {"role": "user", "content": tool_result_blocks},
        ],
    )
    return response.content[0].text


async def run_parallel():
    """
    Full pipeline: coordinator decides → parallel dispatch → synthesis.
    """
    # Step 1 — coordinator emits multiple Task tool_use blocks in one turn
    tool_calls = await coordinator_turn()

    if not tool_calls:
        print("  Coordinator did not emit any Task calls.")
        return

    # Step 2 — runtime dispatches ALL tasks concurrently
    start = time.perf_counter()
    subagent_results = await asyncio.gather(*[run_subagent(tc) for tc in tool_calls])
    elapsed = time.perf_counter() - start

    print(f"\n{'='*60}")
    print(f"  Parallel Dispatch Complete — {elapsed:.2f}s for {len(subagent_results)} subagents")
    print(f"{'='*60}\n")

    for r in subagent_results:
        print(f"  [{r['agent']}]\n  → {r['result']}\n")

    # Step 3 — coordinator synthesizes all results
    summary = await synthesize(tool_calls, subagent_results)
    print(f"{'='*60}")
    print(f"  Coordinator Synthesis")
    print(f"{'='*60}")
    print(f"  {summary}\n")


if __name__ == "__main__":
    asyncio.run(run_parallel())
