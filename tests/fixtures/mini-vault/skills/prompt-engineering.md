---
category: skills
title: Prompt Engineering
summary: Techniques for crafting effective prompts to get reliable, high-quality outputs from LLMs.
tags: [llm, prompting, practical]
created: 2024-07-01T14:00:00Z
lifecycle: reviewed
sources:
  - https://example.com/prompt-guide
updated: 2024-09-15T14:00:00Z
base_confidence: 0.60
tier: supporting
---

# Prompt Engineering

Prompt engineering is the practice of designing inputs to LLMs that produce
reliable, high-quality outputs. It has emerged as a critical skill for
effectively using language models in production.

## Core Techniques

- **Few-shot prompting**: Provide 2-5 examples in the prompt to guide output format and style.
- **Chain-of-thought**: Ask the model to reason step by step before giving a final answer.
- **Role prompting**: Assign a persona or expertise level to the model (e.g., "You are a senior software engineer").
- **Structured output**: Request specific formats like JSON, markdown tables, or bullet lists.

## Common Pitfalls

- Overly long prompts that exceed context windows
- Ambiguous instructions that lead to inconsistent outputs
- Prompt injection vulnerabilities in user-facing applications

## Related

- [[Random Thought]] — creativity in prompting sometimes yields surprising results
- [[NonExistentPage]] — this page doesn't exist in the vault