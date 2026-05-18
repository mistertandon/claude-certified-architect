  Parent-Subagent Orchestration Flow
  
  This POC implements a coordinator pattern where a single parent agent delegates to specialized subagents via a custom Task tool. There are three distinct phases:

  Phase 1: Parent Receives User Request & Delegates

  ┌─────────────────────────────────────────────────────────────────────┐
  │                         USER REQUEST                                │
  │  "Research the AI infrastructure market"                            │
  │   → delegate market research to market_researcher                   │
  │   → delegate tech analysis to tech_analyst                          │
  └──────────────────────────────┬──────────────────────────────────────┘
                                 │
                                 ▼
  ┌─────────────────────────────────────────────────────────────────────┐
  │                     PARENT AGENT (Coordinator)                      │
  │                                                                     │
  │  Tools available: [ Task ]    ◄── ONLY the Task tool                │
  │                                                                     │
  │  1. Receives user message                                           │
  │  2. Calls client.messages.create(tools=[task_tool])                 │
  │  3. Model returns stop_reason="tool_use" with TWO ToolUseBlocks:    │
  │                                                                     │
  │     ┌───────────────────────┐   ┌───────────────────────┐           │
  │     │ Task(                 │   │ Task(                 │           │
  │     │   agent_type=         │   │   agent_type=         │           │
  │     │    "market_researcher"│   │    "tech_analyst"     │           │
  │     │   description=...     │   │   description=...     │           │
  │     │   prompt=...          │   │   prompt=...          │           │
  │     │ )                     │   │ )                     │           │
  │     │ id: toolu_017m...     │   │ id: toolu_0128...     │           │
  │     └───────────┬───────────┘   └───────────┬───────────┘           │
  │                 │                             │                     │
  └─────────────────┼─────────────────────────────┼─────────────────────┘
                    │                             │
                    ▼                             ▼
             ┌──────────┐                  ┌──────────┐
             │ SPAWN    │                  │ SPAWN    │
             │ Subagent │                  │ Subagent │
             │   #1     │                  │   #2     │
             └──────────┘                  └──────────┘

  Phase 2: Each Subagent Runs Its Own Agentic Loop (Scoped Tools)

  ┌──────────────────────────────────────────────────────────────────────┐
  │              SUBAGENT #1: market_researcher                          │
  │                                                                      │
  │  Tools: [web_search, read_doc, extract_data]  ◄── SCOPED             |
  │  Context: ONLY the prompt from parent (full isolation)               │
  │                                                                      │
  │  ┌──────────────┐     ┌───────────────┐     ┌──────────────┐         |  
  │  │  web_search  │     │  web_search   │     │ extract_data │         │
  │  │ "AI infra    │     │ "AI infra     │     │ text=...     │         │
  │  │  market size │     │  key trends"  │     │ fields=...   │         │
  │  │  CAGR 2030"  │     │               │     │              │         │
  │  └──────┬───────┘     └──────┬────────┘     └──────┬───────┘         │
  │         │                    │                     │                 │
  │         ▼                    ▼                     ▼                 │
  │  ┌─────────────┐     ┌──────────────┐     ┌──────────────┐           |
  │  │  Simulated   │     │  Simulated    │     │  Simulated   │         │
  │  │  Result      │     │  Result       │     │  Result      │         │
  │  └──────┬───────┘     └──────┬───────┘     └──────┬───────┘          │
  │         │                    │                     │                 │
  │         └────────────────────┼─────────────────────┘                 │
  │                              ▼                                       │
  │                   ┌───────────────────┐                              │
  │                   │  LOOP continues   │                              │
  │                   │  until model sets  │                             │
  │                   │  stop_reason=      │                             │
  │                   │    "end_turn"      │                             │
  │                   └────────┬──────────┘                              │
  │                            ▼                                         │
  │                   Final text output ──────────────────────────► OUT  │
  └──────────────────────────────────────────────────────────────────────┘

  ┌─────────────────────────────────────────────────────────────────────┐
  │              SUBAGENT #2: tech_analyst                              │
  │                                                                     │
  │  Tools: [read_doc, analyze_deps]              ◄── SCOPED            |
  │  Context: ONLY the prompt from parent (full isolation)              │
  │                                                                     │
  │  ┌─────────────┐     ┌──────────────┐                               │
  │  │  read_doc    │     │ analyze_deps  │                             │
  │  │ "AI infra    │     │ tech="GPU     │                             │
  │  │  tech stack" │     │  compute"     │                             │
  │  └──────┬───────┘     └──────┬───────┘                              │
  │         │                    │                                      │
  │         ▼                    ▼                                      │
  │  ┌─────────────┐     ┌──────────────┐                               │
  │  │  Simulated   │     │  Simulated    │                             │
  │  │  Result      │     │  Result       │                             │
  │  └──────┬───────┘     └──────┬───────┘                              │
  │         │                    │                                      │
  │         └────────┬───────────┘                                      │
  │                  ▼                                                  │
  │       ┌───────────────────┐                                         │
  │       │  LOOP until       │                                         │
  │       │  stop_reason=     │                                         │
  │       │    "end_turn"     │                                         │
  │       └────────┬──────────┘                                         │
  │                ▼                                                    │
  │       Final text output ──────────────────────────────────────► OUT │
  └─────────────────────────────────────────────────────────────────────┘

  Phase 3: Parent Collects Results & Synthesizes

  ┌─────────────────────────────────────────────────────────────────────┐
  │                     PARENT AGENT (Synthesis)                        │
  │                                                                     │
  │  Receives both subagent results as a SINGLE user turn:              │
  │                                                                     │
  │  messages = [                                                       │
  │    { role: "user",    content: original_request },                  │
  │    { role: "assistant", content: [Task(...), Task(...)] },          │
  │    { role: "user",    content: [                                    │
  │        { tool_result, tool_use_id: toolu_017m...,                   │
  │          content: market_researcher_output },                       │
  │        { tool_result, tool_use_id: toolu_0128...,                   │
  │          content: tech_analyst_output }                             │
  │    ]}                                                               │
  │  ]                                                                  │
  │                                                                     │
  │  Calls client.messages.create() → Final synthesized report          │
  └─────────────────────────────────────────────────────────────────────┘

  End-to-End Sequence

   User                Parent Agent              Subagent Runner          Claude API
    │                       │                          │                       │
    │  "Research AI infra"  │                          │                       │
    │──────────────────────►│                          │                       │
    │                       │  messages.create(        │                       │
    │                       │    tools=[Task])         │                       │
    │                       │─────────────────────────────────────────────────►│
    │                       │                          │                       │
    │                       │  ◄── 2x ToolUseBlock ──────────────────────────  │
    │                       │   (Task: market_researcher)                      │
    │                       │   (Task: tech_analyst)                           │
    │                       │                          │                       │
    │                       │  run_subagent(           │                       │
    │                       │   "market_researcher")   │                       │
    │                       │─────────────────────────►│                       │
    │                       │                          │  messages.create(     │
    │                       │                          │   tools=[web_search,  │
    │                       │                          │    read_doc,          │
    │                       │                          │    extract_data])     │
    │                       │                          │─────────────────────► │
    │                       │                          │  ◄── tool_use ──────  │
    │                       │                          │  execute_tool()       │
    │                       │                          │  (loop until          │
    │                       │                          │   end_turn)           │
    │                       │  ◄── final text ────────│                        │
    │                       │                          │                       │
    │                       │  run_subagent(           │                       │
    │                       │   "tech_analyst")        │                       │
    │                       │─────────────────────────►│                       │
    │                       │                          │  messages.create(     │
    │                       │                          │   tools=[read_doc,    │
    │                       │                          │    analyze_deps])     │
    │                       │                          │─────────────────────► │
    │                       │                          │  ◄── tool_use ──────  │
    │                       │                          │  execute_tool()       │
    │                       │                          │  (loop until          │
    │                       │                          │   end_turn)           │
    │                       │  ◄── final text ────────│                        │
    │                       │                          │                       │
    │                       │  Combine both results    │                       │
    │                       │  into one tool_result    │                       │
    │                       │  user turn               │                       │
    │                       │  messages.create()       │                       │
    │                       │─────────────────────────────────────────────────►│
    │                       │                          │                       │
    │  ◄── Synthesized ────│  ◄── final report ──────────────────────────────  │
    │      Report           │                          │                       │

  Key Architecture Decisions

  ┌──────────────────────┬─────────────────────────────────────────────────────────────────────────────┬───────────────────────────────┐
  │       Concern        │                              How It's Handled                               │         Code Location         │
  ├──────────────────────┼─────────────────────────────────────────────────────────────────────────────┼───────────────────────────────┤
  │ Tool gating          │ Parent has ONLY [Task] — cannot call web_search etc. directly               │ task_subagent_poc.py:214      │
  ├──────────────────────┼─────────────────────────────────────────────────────────────────────────────┼───────────────────────────────┤
  │ Tool scoping         │ Each subagent type maps to a limited tool set via SUBAGENT_TOOLS registry   │ task_subagent_poc.py:102-105  │
  ├──────────────────────┼─────────────────────────────────────────────────────────────────────────────┼───────────────────────────────┤
  │ Context isolation    │ Subagents see ONLY the prompt string — no parent conversation history       │ task_subagent_poc.py:146      │
  ├──────────────────────┼─────────────────────────────────────────────────────────────────────────────┼───────────────────────────────┤
  │ Result batching      │ All subagent results collected into ONE tool_result user turn, not multiple │ task_subagent_poc.py:232-250  │
  ├──────────────────────┼─────────────────────────────────────────────────────────────────────────────┼───────────────────────────────┤
  │ Sequential execution │ Subagents run one-at-a-time (could be parallelized with asyncio)            │ task_subagent_poc.py:233 loop │
  ├──────────────────────┼─────────────────────────────────────────────────────────────────────────────┼───────────────────────────────┤
  │ Agentic loop         │ Each subagent loops while True until stop_reason == "end_turn"              │ task_subagent_poc.py:149-179  │
  └──────────────────────┴─────────────────────────────────────────────────────────────────────────────┴───────────────────────────────┘
