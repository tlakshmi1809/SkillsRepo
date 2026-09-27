# Agentic Frameworks & Multi-Agent Orchestration

Agentic systems leverage LLM reasoning to dynamically decompose goals, select tools, observe execution outcomes, and iteratively adapt execution plans.

---

## 1. Core Architectural Orchestration Patterns

### Router Pattern
A lightweight classifier/LLM directs user input to specialized agents or prompts based on intent.

```
                  +-----------------+
                  |   User Input    |
                  +--------+--------+
                           |
                           v
                  +-----------------+
                  | Router Classifier|
                  +----+-------+----+
                       |       |
            +----------+       +----------+
            v                             v
  +-------------------+         +-------------------+
  | Sales/Billing Agent|         | Tech Support Agent|
  +-------------------+         +-------------------+
```

### Orchestrator-Worker Pattern
A central Orchestrator decomposes tasks, assigns sub-tasks to specialized Worker Agents in parallel or sequence, and synthesizes final outputs.

### Evaluator-Optimizer (Reflection Loop)
One LLM generates an output, while a separate Evaluator LLM assesses the output against criteria (e.g., policy, correctness, schema). The generator refines until quality thresholds are met.

---

## 2. Tool & Function Calling Contracts

1. **Strict Schemas**: Define tool inputs using standard JSON Schema / OpenAPI specs with explicit field descriptions and validation constraints.
2. **Deterministic Output Parsing**: Enforce structured outputs (e.g., Pydantic / JSON Mode) for tool arguments to eliminate regex parsing errors.
3. **Idempotency & Reversibility**: Classify tools as:
   - **Read-Only**: Safe for unconditional automatic execution (e.g., `get_user_profile`).
   - **State-Mutating**: Requires confirmation, rate-limiting, or human-in-the-loop gates (e.g., `process_refund`).

---

## 3. Memory Architecture

```
+-----------------------------------------------------------------------+
|                             Agent Memory                              |
|                                                                       |
|  +---------------------+  +--------------------+  +----------------+  |
|  |   Working Memory    |  |  Episodic Memory   |  | Semantic Mem.  |  |
|  | Context window state|  | Past conversations |  | Knowledge base |  |
|  | Tool execution log  |  | Summaries/vector DB|  | User profile   |  |
|  +---------------------+  +--------------------+  +----------------+  |
+-----------------------------------------------------------------------+
```

- **Short-Term / Working Memory**: Active conversation buffer, tool call results, sliding window token management.
- **Episodic Memory**: Vectorized summaries of past sessions to recall historical context across sessions.
- **Semantic Memory**: Persistent key-value / document profile of user preferences, rules, and facts.

---

## 4. Multi-Agent Communication & Safety Controls

1. **Explicit Hand-off Protocols**: Use explicit state transitions when delegating between agents.
2. **Recursion & Infinite Loop Defenses**: Enforce hard limits on maximum agent steps ($N \le 10$) and tool execution retries.
3. **Human-in-the-Loop (HITL)**: Insert async approval steps for high-risk operations (e.g., financial transactions > $100, system access modification).
