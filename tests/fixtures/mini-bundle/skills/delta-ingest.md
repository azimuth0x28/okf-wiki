---
type: Skill
title: "Delta Ingest"
description: "Core skill that ingests only the delta between the manifest ledger and the current bundle state."
tags: [skill, ingest, manifest]
generated:
  by: okf-wiki/0.1.0
  at: 2026-08-30T10:15:00Z
status: stable
stale_after: 2026-11-28T10:15:00Z
sources:
  - resource: "https://github.com/Ar9av/obsidian-wiki"
    title: "obsidian-wiki (source project)"
updated: 2026-08-30T10:15:00Z
base_confidence: 0.8
tier: core
---

# Delta Ingest

The skill reads `.manifest.json`, compares the recorded SHA-256 hashes against the
current files, and ingests only the pages that changed. The `tier` extension field
marks it as part of the framework core.
