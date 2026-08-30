---
category: synthesis
title: "Ghost Synthesis"
summary: "What ghost-writer's v0.1 corpus implies for any consumer upgrading legacy header blocks to v0.2."
tags: [ghost-writer, synthesis, upgrade]
by: ghost-writer/0.3
timestamp: 2026-08-29T18:00:00Z
lifecycle: draft
sources:
  - "https://ghost-writer.example/spec/v0.1"
  - "https://ghost-writer.example/docs/sync-flow"
---

# Ghost Synthesis

Across the ghost-writer corpus, three facts recur wherever v0.1 bundles are
upgraded: the by field is the only trust signal, timestamps drift between
pages, and plain-string sources lose their titles.

An upgrade path therefore has to reconstruct provenance from the producer
identity and treat missing structure as information loss, not corruption.

The practical recipe is the [Ghost Sync Flow](../skills/ghost-sync-flow.md)
run by [Ghost Runner](../entities/ghost-runner.md), with the canonical-order
rules from [Ghost Canonicalization](../concepts/ghost-canonicalization.md).
