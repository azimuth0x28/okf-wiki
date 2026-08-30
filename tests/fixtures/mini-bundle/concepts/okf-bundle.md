---
type: Concept
title: "OKF Bundle"
description: "A directory of markdown pages that forms a portable, distributable unit of knowledge."
tags: [okf, bundle, knowledge]
generated:
  by: okf-wiki/0.1.0
  at: 2026-08-30T10:00:00Z
status: stable
stale_after: 2026-11-28T10:00:00Z
sources:
  - resource: "https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md"
    title: "OKF v0.2 Spec"
verified:
  - by: human:evgeniy
    at: 2026-08-30T10:00:00Z
# ===== extension fields =====
updated: 2026-08-30T10:00:00Z
aliases: ["knowledge bundle"]
relationships:
  - type: extends
    target: ./references/okf-spec.md
provenance:
  human: 0.9
  machine: 0.1
base_confidence: 0.85
tier: core
---

# OKF Bundle

A bundle is the unit of distribution for knowledge in the Open Knowledge Format.
Every page carries YAML frontmatter with a type, provenance, and lifecycle state,
so any agent or human can consume the directory without conversion.

This page is the canonical example: full template, human-verified, stable.
