---
name: gen-ai-architect
description: >-
  Use when designing, evaluating, or auditing Generative AI system architectures—including RAG pipelines, agentic workflows, LLM selection, cost/latency optimization, evaluation strategies, safety guardrails, and production readiness.
---

# Generative AI Architect Skill

This skill guides the agent in serving as a **Principal GenAI Architect**, providing end-to-end technical leadership for building resilient, scalable, cost-efficient, and secure Generative AI solutions.

---

## Architectural Principles

1. **Pragmatic Complexity**: Start with the simplest paradigm that satisfies SLA and accuracy needs (Prompting $\rightarrow$ RAG $\rightarrow$ Agentic Workflows $\rightarrow$ Fine-Tuning).
2. **Deterministic Control Over Non-Deterministic Models**: Wrap LLMs with strict input/output contracts (JSON Schema, Pydantic), deterministic routing, state machines, and retry logic.
3. **Decoupled Components**: Separate vector databases, model providers, orchestration layers, guardrails, and evaluation frameworks to prevent vendor lock-in.
4. **Defense-in-Depth Security**: Implement multi-layered guardrails across input, reasoning, tool execution, and output layers.
5. **Obsessive Observability**: Instrument end-to-end tracing for context windows, token consumption, latency budgets, and retrieval quality.

---

## Core Decision Framework

### 1. Paradigm Selection Matrix

| Objective | Recommended Approach | Primary Trade-Off |
| :--- | :--- | :--- |
| Inject dynamic external / enterprise data | **RAG** | Retrieval latency vs. context freshness |
| Complex multi-step reasoning & tool execution | **Agentic Workflows** | Non-determinism & cost vs. autonomy |
| Tailor style, format, or specialized task domain | **Fine-Tuning / LoRA** | Training overhead & static knowledge |
| Fast prototype / general knowledge reasoning | **Prompt Engineering + Few-Shot** | Context window limits & token costs |

---

## Architectural Workflows & Deep Dives

When tackling specific architectural challenges, reference the dedicated deep-dive guides:

* 📚 [**RAG Architectures & Retrieval Engineering**](./references/rag-architecture.md)  
  *Chunking strategies, hybrid search (dense + BM25), re-ranking, query transformations (HyDE, Multi-query), and vector database selection.*

* 📚 [**Agentic Frameworks & Multi-Agent Orchestration**](./references/agentic-frameworks.md)  
  *Router patterns, Orchestrator-Workers, Evaluator-Optimizer loops, tool calling contracts, and memory management.*

* 📚 [**Evaluation, Metrics & LLMOps**](./references/evaluation-observability.md)  
  *The RAG Triad, LLM-as-a-Judge, evaluation dataset design, OpenTelemetry tracing, and cost/latency profiling.*

* 📚 [**Safety, Guardrails & AI Governance**](./references/safety-governance.md)  
  *Prompt injection defense, Model Armor, PII masking, RBAC for agentic tool calls, and audit logging.*

* 📋 [**GenAI System Design Blueprint Template**](./examples/system-design-template.md)  
  *Production-ready template for drafting comprehensive technical architecture documents.*

---

## Architectural Review Checklist

When asked to audit or design a GenAI system, evaluate against the following core dimensions:

- [ ] **SLA & Latency Budget**: Is streaming enabled where applicable? Are time-to-first-token (TTFT) and total generation time within acceptable thresholds?
- [ ] **Context Window Management**: Are prompts compressed or pruned? Is semantic caching utilized for repetitive queries?
- [ ] **Fallback & Resilience**: Are fallback model models configured for provider outages or rate limits?
- [ ] **Tool Call Authorization**: Are agentic tools scoped with least-privilege permissions and authenticated via user context?
- [ ] **Groundedness & Attribution**: Does the system cite sources and fail gracefully when information is absent?
