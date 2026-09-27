# RAG Architectures & Retrieval Engineering

Retrieval-Augmented Generation (RAG) bridges non-parametric LLM reasoning with parametric/external knowledge repositories. This guide covers architectural design patterns from Naive to Advanced and Modular RAG.

---

## 1. RAG Maturity Spectrum

```
+------------------+     +--------------------------+     +-----------------------------+
|    Naive RAG     | --> |       Advanced RAG       | --> |         Modular RAG         |
| Chunk -> Vector  |     | Pre/Post Retrieval Hooks |     | Dynamic Routing, GraphRAG   |
| Top-K -> LLM     |     | Hybrid Search + Re-rank  |     | Agentic Knowledge Fallback  |
+------------------+     +--------------------------+     +-----------------------------+
```

---

## 2. Ingestion & Pre-Retrieval Pipeline

### Chunking Strategies
- **Fixed-size Chunking**: (e.g., 512 tokens with 50-token overlap). Simple but breaks context boundaries.
- **Semantic Chunking**: Split text based on embedding distance shifts between adjacent sentences.
- **Document-Structure Aware**: Parse markdown/HTML headers, tables, and sections as discrete units.
- **Parent-Child Chunking**: Store small chunks (128 tokens) for vector indexing, but retrieve large parent chunks (1024 tokens) or full sections for LLM context.

### Vector Indexing & Hybrid Search
Combine keyword (sparse) and semantic (dense) search to maximize recall and precision:

$$\text{Combined Score} = \alpha \cdot \text{DenseScore} + (1 - \alpha) \cdot \text{SparseScore (BM25)}$$

- **Reciprocal Rank Fusion (RRF)**:
  $$RRF(d) = \sum_{m \in M} \frac{1}{k + r_m(d)}$$
  where $r_m(d)$ is the rank position of document $d$ in system $m$, and $k \approx 60$.

---

## 3. Advanced Retrieval & Post-Processing

### Query Transformations
- **HyDE (Hypothetical Document Embeddings)**: Generate a hypothetical answer with an LLM, embed the synthetic answer, and query the vector index.
- **Multi-Query Expansion**: Use an LLM to generate 3-5 variations of the input query to overcome vocabulary mismatches.
- **Query Decomposition**: Break complex queries into sub-questions (e.g., "Compare X product in Q1 vs Q2").

### Re-Ranking Models
Pass `Top-N` (e.g., 50) initial retrieval results through a Cross-Encoder (e.g., Cohere Rerank, BGE-Reranker-Large) to score fine-grained query-document relevance, narrowing down to `Top-K` (e.g., 5).

---

## 4. Vector Database Selection Framework

| Feature | pgvector / PostgreSQL | Vertex AI Vector Search / Pinecone | Qdrant / Weaviate |
| :--- | :--- | :--- | :--- |
| **Best For** | Existing Postgres infra, relational data joining | Millions/Billions of vectors, managed cloud scale | High-throughput dedicated vector workloads |
| **Indexing** | HNSW / IVFFlat | ScaNN | HNSW with payload filtering |
| **Filter Performance** | Medium | High | Very High |
| **Operational Overhead** | Low (if Postgres already running) | Minimal (Fully managed) | Medium |

---

## 5. Architectural Failure Modes & Mitigations

1. **Lost in the Middle**: LLMs ignore context buried in the middle of long prompts.
   - *Mitigation*: Sort retrieved passages so most relevant chunks are at the extreme start and end of the context window.
2. **Context Contamination / Noise**: Irrelevant retrieved chunks induce hallucinations.
   - *Mitigation*: Set strict similarity score thresholds and cross-encoder score cutoffs before passing context to LLM.
3. **Stale Indexing**: Vector database out of sync with source data.
   - *Mitigation*: Event-driven pipeline (CDC / Cloud Storage triggers) for real-time document upserts/deletions.
