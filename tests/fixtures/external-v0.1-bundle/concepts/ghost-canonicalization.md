---
category: concepts
title: "Ghost Canonicalization"
summary: "The ghost-writer rule that every v0.1 header block emits its keys in one fixed order so diffs stay readable."
tags: [ghost-writer, canonicalization, v0.1]
by: ghost-writer/0.3
timestamp: 2026-08-29T09:00:00Z
lifecycle: draft
sources:
  - "https://ghost-writer.example/spec/canonical-order"
# ===== legacy extension fields =====
base_confidence: 0.7
---

# Ghost Canonicalization

Ghost-writer emits every v0.1 header block in one fixed key order:
category, title, summary, tags, by, timestamp, lifecycle, sources.

A fixed order turns header changes into line-level diffs: a retitled page
changes one line, a retag moves nothing else.

The order is a serialization detail, not a schema — readers accept any key
order, and the v0.2 upgrade re-emits keys in the OKF canonical order anyway.

Applies to every page in this bundle; see [OKF Bundle](./okf-bundle.md) for
the unit these rules decorate.
