---
category: concepts
title: Transformer Architecture
summary: The dominant architecture for sequence modeling, introduced in "Attention Is All You Need".
tags: [ml, architecture, transformers]
created: 2024-03-15T10:30:00Z
lifecycle: draft
sources:
  - https://arxiv.org/abs/1706.03762
  - papers/attention.pdf
updated: 2024-06-01T10:30:00Z
aliases: [transformers, self-attention-model]
relationships:
  - target: concepts/attention-mechanism.md
    type: extends
provenance:
  extracted: 0.72
  inferred: 0.25
  ambiguous: 0.03
base_confidence: 0.85
tier: core
---

# Transformer Architecture

The Transformer architecture replaces recurrence with self-attention, enabling
massive parallelization during training. Introduced by Vaswani et al. in 2017,
it has become the foundation of modern LLMs.

## Key Ideas

- Self-attention computes pairwise interactions between all positions in a sequence.
- Multi-head attention allows the model to attend to different representation subspaces.
- Positional encodings inject sequence order information since the architecture has no recurrence.

## Related

- [[attention-mechanism]] — the core building block
- [[knowledge-graph]] — transformers are used in modern KG construction
- [[attention-paper]] — the original paper
- [[openai]] — GPT models are decoder-only transformers
- [[fine-tuning-llms]] — how to adapt pre-trained transformers