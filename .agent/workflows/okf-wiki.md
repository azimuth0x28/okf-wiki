---
name: okf-wiki
description: okf-wiki workflows — query, update, ingest, lint, status.
commands:
  - name: wiki-context-pack
    description: Compile a bounded bundle context slice for a downstream agent.
    skill: .skills/wiki-context-pack/SKILL.md
  - name: wiki-query
    description: Answer questions from the compiled OKF bundle with file-relative link citations.
    skill: .skills/wiki-query/SKILL.md
  - name: wiki-update
    description: Sync the current project's knowledge into the OKF bundle.
    skill: .skills/wiki-update/SKILL.md
  - name: wiki-ingest
    description: Ingest documents into the OKF bundle.
    skill: .skills/wiki-ingest/SKILL.md
  - name: wiki-status
    description: Show what's been ingested, what's pending, and the delta.
    skill: .skills/wiki-status/SKILL.md
  - name: wiki-lint
    description: Audit the bundle for orphans, broken links, stale content, OKF conformance.
    skill: .skills/wiki-lint/SKILL.md
---

# okf-wiki — Workflow Registry

Each command above maps to a `SKILL.md` in `.skills/`. When a user invokes one
of these commands, read the mapped skill file and follow its instructions
exactly. The skills handle bundle path resolution, manifest tracking, and
file-relative link connectivity on their own.

For the full routing table (all 37 skills), see `AGENTS.md` at the repo root.

> Derived from Ar9av/obsidian-wiki (MIT).