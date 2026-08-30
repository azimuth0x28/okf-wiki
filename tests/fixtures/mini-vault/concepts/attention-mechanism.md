---
category: concepts
title: Attention Mechanism
summary: Core building block of transformers that computes weighted combinations of values.
tags: [ml, attention, transformers]
created: 2024-03-16T14:00:00Z
lifecycle: reviewed
sources:
  - https://arxiv.org/abs/1706.03762
updated: 2024-05-20T14:00:00Z
relationships:
  - target: concepts/transformer-architecture.md
    type: implements
base_confidence: 0.90
tier: core
---

# Attention Mechanism

Attention computes a weighted sum of values, where the weights are derived from
a compatibility function between a query and a set of keys. The scaled dot-product
variant is the most widely used form.

## Scaled Dot-Product Attention

The attention function maps a query and key-value pairs to an output:

$$\text{Attention}(Q, K, V) = \text{softmax}\left(\frac{QK^T}{\sqrt{d_k}}\right)V$$

## Multi-Head Attention

Instead of performing a single attention function, multi-head attention projects
queries, keys, and values h times with different learned linear projections.

## Related

- [[transformer-architecture|Transformers]] — the architecture built on attention
- [[attention-paper]] — the original paper introducing this mechanism