---
category: concepts
title: "OKF Bundle"
summary: "A portable knowledge directory assembled by ghost-writer, where every page carries legacy v0.1 provenance."
tags: [okf, bundle, portability, v0.1]
by: ghost-writer/0.3
timestamp: 2026-09-01T12:00:00Z
lifecycle: draft
sources:
  - "https://ghost-writer.example/spec/okf-bundle"
  - "Ghost Writer Field Manual, ch. 2"
# ===== legacy extension fields =====
base_confidence: 0.9
tier: core
ghost_note: "written by ghost-writer"
---

# OKF Bundle

Ghost-writer treats the bundle as a self-contained folder of markdown pages.
Each page opens with a legacy v0.1 header block: a category, a summary, and a
timestamp recorded by the producing agent.

The v0.1 header predates the generated/status split, so trust has to be
reconstructed from the by field during any upgrade.

## Ghost Writer Notes

Canonical ordering of header keys is defined in
[Ghost Canonicalization](./ghost-canonicalization.md); the bundle is the unit
those rules apply to.
