---
inclusion: always
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
3. Skills are in `.skills/` (also at `.kiro/skills/`). Each subfolder has a
   `SKILL.md`.

## When to Use Skills

| User says something like… | Read this skill |
|---|---|
| "set up my bundle" / "initialize" | `wiki-setup` |
| "ingest" / "add this to the bundle" / "process these docs" / "process this export" / "ingest this data" | `wiki-ingest` |
| "import my Claude history" / "mine my conversations" | `claude-history-ingest` |
| "import my Codex history" | `codex-history-ingest` |
| "import my Hermes history" | `hermes-history-ingest` |
| "import my OpenClaw history" | `openclaw-history-ingest` |
| "import my Pi history" | `pi-history-ingest` |
| "what's the status" / "show the delta" | `wiki-status` |
| "what do I know about X" | `wiki-query` |
| "use my bundle as context" / "context pack for X" / "bounded context" | `wiki-context-pack` |
| "audit" / "lint" / "find broken links" | `wiki-lint` |
| "rebuild" / "archive" / "restore" | `wiki-rebuild` |
| "link my pages" / "cross-reference" | `cross-linker` |
| "fix my tags" | `tag-taxonomy` |
| "update bundle" / "sync to bundle" | `wiki-update` |
| "export bundle" / "export graph" | `wiki-export` |

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