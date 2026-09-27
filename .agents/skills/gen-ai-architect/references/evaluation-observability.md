# Evaluation, Metrics & LLMOps

Building production GenAI systems requires transitioning from subjective manual prompt checking ("vibe checks") to automated, continuous, quantitative evaluation and observability.

---

## 1. The Quality Flywheel

```
+------------------+     +-------------------+     +---------------------+
| Test Dataset     | --> | Automated Eval    | --> | Failure Diagnostics |
| Golden Questions |     | LLM-as-a-Judge    |     | Root Cause Analysis |
+------------------+     +-------------------+     +---------------------+
         ^                                                    |
         |                                                    v
         +---------------- Continuous Improvement <-----------+
```

---

## 2. RAG Triad Evaluation Metrics

The **RAG Triad** isolates where failures occur in RAG systems:

```
                  +-------------------+
                  |       Query       |
                  +-----+-------+-----+
                       /         \
   Context Relevance  /           \  Answer Relevance
                     v             v
          +-----------------+    +-----------------+
          |    Context      +--->|    Response     |
          +-----------------+    +-----------------+
                              Groundedness
```

1. **Context Relevance**: Measures if retrieved chunks are relevant to the query (Evaluates Vector DB / Search).
2. **Groundedness (Faithfulness)**: Measures if response claims are directly supported by context (Evaluates LLM Hallucinations).
3. **Answer Relevance**: Measures if response directly answers the user query (Evaluates LLM Instructions).

---

## 3. LLM-as-a-Judge Design Guidelines

When using an advanced LLM (e.g., Gemini 1.5 Pro / GPT-4) to evaluate system outputs:

- **Single-Metric Prompts**: Evaluate one property per judge invocation (e.g., separate Safety Judge from Relevance Judge).
- **Explicit Scoring Rubric**: Define exact 1-5 or 0/1 thresholds with examples for each score.
- **Chain-of-Thought (CoT)**: Force judge model to output reasoning steps *before* emitting the final numerical score.
- **Position & Order Bias Mitigation**: Swap order of options when evaluating pairwise comparisons.

---

## 4. Observability & OpenTelemetry Tracing

Production GenAI workloads require distributed tracing conforming to **OpenTelemetry GenAI Semantic Conventions**:

### Key Span Attributes
- `gen_ai.system`: Model provider (e.g., `gemini`, `openai`, `anthropic`)
- `gen_ai.request.model`: Target model name (e.g., `gemini-1.5-pro`)
- `gen_ai.usage.input_tokens`: Prompt token count
- `gen_ai.usage.output_tokens`: Completion token count
- `gen_ai.completion`: Output payload (or SHA256 hash if PII restricted)

### Latency Budget Breakdowns
Monitor and alert on key SLA markers:
- **TTFT (Time-to-First-Token)**: Latency until streaming output starts (target: $< 800\text{ms}$).
- **Inter-Token Latency**: Smoothness of generation stream.
- **Total Request Latency**: Sum of retrieval + reranking + prompt assembly + generation.

---

## 5. Cost & Token Optimization Strategies

- **Semantic Caching**: Store query-response pairs in a vector cache (e.g., Redis VL) with similarity threshold $\ge 0.95$ to serve cached responses instantaneously at zero LLM cost.
- **Prompt Pruning**: Remove redundant system prompt instructions and whitespace.
- **Model Cascade**: Route easy queries to small/fast models ($0.0001 / 1K tokens), escalating only complex queries to large reasoning models.
