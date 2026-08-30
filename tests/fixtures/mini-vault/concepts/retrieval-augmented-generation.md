---
category: concepts
title: Retrieval-Augmented Generation
summary: Technique that augments LLM prompts with retrieved documents for grounded, factual generation.
tags: [rag, llm, retrieval]
created: 2024-05-10T11:00:00Z
lifecycle: disputed
lifecycle_reason: Debate over whether RAG or long-context models will dominate production use cases
sources:
  - https://arxiv.org/abs/2005.11401
updated: 2024-08-01T11:00:00Z
base_confidence: 0.70
tier: supporting
lifecycle_changed: 2024-08-01T11:00:00Z
---

# Retrieval-Augmented Generation

RAG combines a retriever (typically dense passage retrieval) with a generator
(an LLM) to produce answers grounded in external knowledge, reducing
hallucination by conditioning generation on retrieved evidence.

## Architecture

1. **Indexing**: Documents are chunked and embedded into a vector store.
2. **Retrieval**: Given a query, the top-k most similar chunks are fetched.
3. **Generation**: The LLM generates an answer conditioned on the query + retrieved chunks.

## Related

- [[semantic-search]] — dense retrieval is a form of semantic search
- [[concepts/vector-database]] — vector DBs are commonly used as the retrieval backend
- [[Random Thought]] — sometimes the best ideas come from random connections