---
category: references
title: "Attention Is All You Need"
summary: The seminal 2017 paper by Vaswani et al. introducing the Transformer architecture.
tags: [paper, transformers, attention]
created: 2024-03-10T08:00:00Z
lifecycle: verified
sources:
  - https://arxiv.org/abs/1706.03762
updated: 2024-05-01T08:00:00Z
base_confidence: 1.0
tier: core
---

# Attention Is All You Need

Vaswani et al. (2017) introduced the Transformer, a sequence transduction model
based entirely on attention mechanisms, dispensing with recurrence and convolutions.

## Key Contributions

- Proposed the Transformer architecture with self-attention and cross-attention.
- Introduced multi-head attention and positional encodings.
- Achieved state-of-the-art on WMT 2014 English-to-German and English-to-French translation.
- Training time reduced from weeks to 3.5 days on 8 NVIDIA P100 GPUs.

## Architecture Summary

The Transformer uses an encoder-decoder structure where both components consist
of stacked self-attention and feed-forward layers. The decoder additionally
includes cross-attention to the encoder output.

## Related

- [[attention-mechanism]] — the core innovation of the paper
- [[transformer-architecture]] — the full architecture described in the paper
- [[google-deepmind]] — the authors were at Google Brain