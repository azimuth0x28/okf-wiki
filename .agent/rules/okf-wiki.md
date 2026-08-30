---
alwaysApply: true
description: okf-wiki skill-based framework — routing, conventions, and core rules.
---

# okf-wiki — Agent Context

This project is a **skill-based framework** for building and maintaining
knowledge bases where the store is natively an **OKF v0.2 (Open Knowledge
Format) bundle**.

## Quick Orientation

1. Resolve config via `AGENTS.md`: honor an inline `@name` bundle override
   first, then `.env`, then the global config (`~/.config/okf-wiki/config`,
   XDG-style; legacy `~/.obsidian-wiki/config` still honored). This gives
   `OKF_BUNDLE_PATH` — where the bundle lives.
2. Read `.manifest.json` at the bundle root to see what's already been ingested.
3. Skills are in `.skills/` (also at `.agents/skills/`). Each subfolder has a
   `SKILL.md`.

## When to Use Skills

| User says something like… | Read this skill |
|---|---|
| "set up my bundle" / "initialize" | `.skills/wiki-setup/SKILL.md` |
| "ingest" / "add this to the bundle" / "process this export" / "ingest this data" | `.skills/wiki-ingest/SKILL.md` |
| "import my Claude history" | `.skills/claude-history-ingest/SKILL.md` |
| "import my Codex history" | `.skills/codex-history-ingest/SKILL.md` |
| "import my Hermes history" | `.skills/hermes-history-ingest/SKILL.md` |
| "import my OpenClaw history" | `.skills/openclaw-history-ingest/SKILL.md` |
| "import my Pi history" | `.skills/pi-history-ingest/SKILL.md` |
| "what's the status" / "show the delta" | `.skills/wiki-status/SKILL.md` |
| "what do I know about X" | `.skills/wiki-query/SKILL.md` |
| "use my bundle as context" / "context pack for X" / "bounded context" | `.skills/wiki-context-pack/SKILL.md` |
| "audit" / "lint" / "find broken links" | `.skills/wiki-lint/SKILL.md` |
| "rebuild" / "archive" / "restore" | `.skills/wiki-rebuild/SKILL.md` |
| "link my pages" / "cross-reference" | `.skills/cross-linker/SKILL.md` |
| "fix my tags" | `.skills/tag-taxonomy/SKILL.md` |
| "update bundle" / "sync to bundle" | `.skills/wiki-update/SKILL.md` |
| "export bundle" / "export graph" | `.skills/wiki-export/SKILL.md` |

## Core Rules

- **Compile, don't retrieve** — update existing pages, don't append or duplicate.
- **Track everything** — update `.manifest.json`, per-dir `index.md`, root
  `index.md`, `log.md`, and `_cache/hot.md` after every operation.
- **Connect with file-relative links** — every page should link to related
  pages using `[display](./relative/path.md)`.
- **Frontmatter required (OKF v0.2)** — every page needs `type` (TitleCase)
  and `generated`; pages built from sources also need `sources` with a
  `resource` entry.

For full context (37-skill catalog, configuration protocol, FR-7.3 portability
invariant), read `AGENTS.md` at the repo root.