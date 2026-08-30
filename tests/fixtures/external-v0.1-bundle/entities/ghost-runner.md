---
category: entities
title: "Ghost Runner"
summary: "The background process in ghost-writer that walks a bundle directory and re-emits pages after a schema change."
tags: [ghost-writer, tooling]
by: ghost-writer/0.3
timestamp: 2026-08-28T14:30:00Z
lifecycle: draft
sources:
  - "https://ghost-writer.example/docs/ghost-runner"
---

# Ghost Runner

Ghost Runner is the batch process behind ghost-writer/0.3: it walks a bundle
directory, parses each legacy header block, and re-emits the page.

Runs are offline and deterministic — the same tree in, the same tree out —
which is what makes its rewrites reviewable as plain diffs.

The runner is the actor that would apply the canonical order described in
[Ghost Canonicalization](../concepts/ghost-canonicalization.md) across a
whole [OKF Bundle](../concepts/okf-bundle.md).
