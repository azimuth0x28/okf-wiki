---
category: concepts
title: Semantic Search
summary: Search that understands meaning through dense vector embeddings rather than keyword matching.
tags: [search, embeddings, nlp]
created: 2024-04-15T16:00:00Z
lifecycle: archived
superseded_by: concepts/vector-search-v2.md
sources:
  - https://example.com/semantic-search-primer
updated: 2024-06-15T16:00:00Z
base_confidence: 0.75
tier: peripheral
---

# Semantic Search

Semantic search uses dense vector embeddings to find content based on semantic
meaning rather than exact keyword matches. It maps both queries and documents
into a shared embedding space where proximity indicates relevance.

## How It Works

1. Encode documents into dense vectors using a transformer model.
2. Encode the query into the same vector space.
3. Retrieve documents whose vectors are nearest to the query vector (cosine similarity).

## Related

- [[knowledge-graph]] — semantic search and KGs are complementary technologies