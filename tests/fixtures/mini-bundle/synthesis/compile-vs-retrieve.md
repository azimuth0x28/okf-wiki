---
type: Synthesis
title: "Compile vs Retrieve"
description: "Synthesis comparing precompiled knowledge packs with live retrieval over the bundle."
tags: [synthesis, retrieval, compile]
generated:
  by: okf-wiki/0.1.0
  at: 2026-08-30T10:20:00Z
status: stable
stale_after: 2026-11-28T10:20:00Z
sources:
  - resource: "https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md"
    title: "OKF v0.2 Spec"
updated: 2026-08-30T10:20:00Z
provenance:
  human: 0.2
  machine: 0.8
base_confidence: 0.75
relationships:
  - type: derived_from
    target: ./references/okf-spec.md
  - type: uses
    target: ./concepts/okf-bundle.md
---

# Compile vs Retrieve

This synthesis page weighs two consumption strategies for an OKF bundle: compiling a
static knowledge pack ahead of time, or retrieving pages live during a session. The
`relationships` extension field records typed edges to the pages it draws on.
