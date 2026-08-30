---
category: skills
title: Fine-Tuning LLMs
summary: How to adapt pre-trained language models for specific tasks and domains.
tags: [llm, fine-tuning, practical]
created: 2024-06-01T12:00:00Z
lifecycle: draft
sources:
  - https://example.com/fine-tuning-guide
updated: 2024-09-01T12:00:00Z
base_confidence: 0.65
tier: supporting
---

# Fine-Tuning LLMs

Fine-tuning adapts a pre-trained language model to a specific domain or task
by continuing training on a smaller, task-specific dataset. This is more
efficient than training from scratch and often yields better task performance.

## Methods

- **Full fine-tuning**: Update all model parameters on the target dataset.
- **LoRA** (Low-Rank Adaptation): Train small adapter matrices while keeping base weights frozen.
- **QLoRA**: Quantized LoRA — combines 4-bit quantization with LoRA for memory-constrained environments.

## Best Practices

- Use a small learning rate (1e-5 to 5e-5) to avoid catastrophic forgetting.
- Monitor validation loss to detect overfitting on small datasets.
- Start with instruction-tuned variants when available.

## Related

- [[transformer-architecture|Transformers]] — the base architecture being fine-tuned
- [[openai]] — provides fine-tuning API for GPT models