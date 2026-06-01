# Domain 02 / Task 03-03 — tool_choice Options (Tool Distribution Strategy)

## Concept Demonstrated

**`tool_choice` controls whether and which tools the model invokes:**

| `tool_choice` | Behavior | Best For |
|---|---|---|
| `{"type": "auto"}` | Model decides freely — may skip tools entirely | Open-ended assistants |
| `{"type": "any"}` | Model **must** call at least one tool (picks which) | Pipelines requiring structured output every turn |
| `{"type": "tool", "name": "X"}` | Model **must** call the exact named tool | Deterministic extraction, form-filling |

### Why This Matters

1. **`auto`** — default behavior; the model uses judgment, which is ideal for general chat but unpredictable for pipelines
2. **`any`** — guarantees a tool call happens, preventing the model from "answering from memory" when you need live data
3. **`tool` (forced)** — developer overrides model choice entirely; critical for deterministic workflows where the exact tool matters

### Architecture

```
Same 2 tools (get_weather, get_forecast) × 3 strategies
─────────────────────────────────────────────────────────

  auto:   User → Model decides → tool or no tool
  any:    User → Model forced  → must pick a tool
  tool:   User → Developer forced → exact tool specified

The ONLY variable is tool_choice — tools, model, and system prompt
stay identical, isolating the effect of each strategy.
```

## Setup

```bash
cd domain-02/task-03-03

# 1. Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 2. Install dependencies
pip install anthropic python-dotenv

# 3. Set your API key
#    Edit .env and replace "your-api-key-here" with your real Anthropic API key
nano .env
```

## Run

```bash
python tool_choice_options.py
```

## Expected Output

```
╔════════════════════════════════════════════════════════════════╗
║   POC: tool_choice Options — auto / any / forced tool        ║
╚════════════════════════════════════════════════════════════════╝

▶ DEMO 1: tool_choice = 'auto' (model decides)

================================================================
  Strategy: AUTO — model decides (greeting, expects NO tool call)
  tool_choice = {"type": "auto"}
  User: "Hello! How are you?"
================================================================
  stop_reason: end_turn
  [text]: Hello! I'm doing well, thanks for asking...
  [final answer]: Hello! I'm doing well...

================================================================
  Strategy: AUTO — model decides (weather query, expects tool call)
  tool_choice = {"type": "auto"}
  User: "What's the weather like in Tokyo?"
================================================================
  stop_reason: tool_use
  [tool_call]: get_weather({"city": "Tokyo"})
  [tool_result]: {"city": "Tokyo", "temp_celsius": 22, ...}
  [final answer]: The weather in Tokyo is currently 22°C...

▶ DEMO 2: tool_choice = 'any' (must use a tool)

================================================================
  Strategy: ANY — must use a tool (even for a greeting)
  tool_choice = {"type": "any"}
  User: "Hello! How are you?"
================================================================
  stop_reason: tool_use
  [tool_call]: get_weather({"city": "..."})   ← forced even for greeting
  ...

▶ DEMO 3: tool_choice = {type: 'tool', name: '...'} (forced)

================================================================
  Strategy: FORCED — must call get_forecast (overrides model's natural pick)
  tool_choice = {"type": "tool", "name": "get_forecast"}
  User: "What's the weather like in Berlin right now?"
================================================================
  stop_reason: tool_use
  [tool_call]: get_forecast({"city": "Berlin"})   ← forced forecast, not current
  ...
```

## Key Exam Takeaways

| Principle | How This POC Shows It |
|---|---|
| `auto` = model autonomy | Greeting gets text-only reply; weather query triggers tool |
| `any` = guaranteed tool use | Even a greeting forces a tool call — model can't skip |
| `tool` = developer override | User asks current weather → forced to call forecast instead |
| Same tools, different behavior | All 3 strategies use identical tool definitions |
| `tool_choice` is the control knob | It's the **only** variable across all demos |
