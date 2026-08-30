# okf-wiki — Copilot Context

This project is a **skill-based framework** for building and maintaining
**OKF v0.2 (Open Knowledge Format)** knowledge bundles using AI coding
agents. There are no scripts or dependencies — everything is markdown
instructions that the agent executes directly.

## Project Overview

- **Purpose:** Build and maintain an OKF v0.2 bundle using the LLM Wiki
  pattern (Andrej Karpathy).
- **Tech Stack:** Markdown only. No code, no dependencies. The AI agent IS
  the runtime.
- **Key Config:** Resolve config via `AGENTS.md`: inline `@name` bundle
  override first, then `.env`, then the global config (`~/.config/okf-wiki/config`,
  XDG-style; legacy `~/.obsidian-wiki/config` still honored). The resolved
  config supplies `OKF_BUNDLE_PATH`.
- **Skills:** `.skills/` contains skill folders, each with a `SKILL.md`
  defining a workflow.

## Key Concepts

- The bundle is a **compiled artifact** — knowledge distilled from raw
  sources into interconnected pages, natively OKF v0.2.
- Every bundle page has YAML frontmatter: minimum `type` (TitleCase) and
  `generated`; pages built from sources also carry `sources` with a
  `resource` entry.
- Pages are connected with file-relative markdown links
  (`[display](./relative/path.md)`). Wikilinks are not used.
- A `.manifest.json` at the bundle root tracks all ingested sources for
  delta-based updates.
- `index.md` and `log.md` must be updated after every operation.

## Skills Reference

| Skill | Folder | Purpose |
|---|---|---|
| Setup | `.skills/wiki-setup/` | Initialize OKF v0.2 bundle structure |
| Ingest | `.skills/wiki-ingest/` | Distill documents into bundle pages, plus any text data — chat exports, logs, transcripts |
| History Router | `.skills/wiki-history-ingest/` | Route `/wiki-history-ingest <claude|copilot|codex|hermes|openclaw|pi>` to the right history skill |
| Claude History | `.skills/claude-history-ingest/` | Mine `~/.claude` conversations |
| Codex History | `.skills/codex-history-ingest/` | Mine `~/.codex` sessions and rollout logs |
| Status | `.skills/wiki-status/` | Audit ingestion state and delta |
| Query | `.skills/wiki-query/` | Answer questions from the bundle |
| Context Pack | `.skills/wiki-context-pack/` | Compile bounded bundle context for another agent |
| Lint | `.skills/wiki-lint/` | Find broken links, orphans, OKF conformance violations |
| Rebuild | `.skills/wiki-rebuild/` | Archive and rebuild |
| Cross-Linker | `.skills/cross-linker/` | Auto-discover and insert missing file-relative links |
| Tag Taxonomy | `.skills/tag-taxonomy/` | Enforce consistent tag vocabulary |
| okf-wiki | `.skills/okf-wiki/` | Core architecture pattern (OKF v0.2 native) |
| Skill Creator | `.skills/skill-creator/` | Create new skills |

## Coding Conventions

- When creating bundle pages, always use YAML frontmatter.
- Use file-relative markdown links `[display](./path.md)` for
  cross-references — NOT wikilinks.
- Project-specific knowledge goes in `projects/<name>/`. Global knowledge
  goes in top-level categories.
- The bundle is OKF v0.2 native — `index.md` carries `okf_version: "0.2"`,
  every page has `type` and `generated` fields. See `.skills/okf-wiki/SKILL.md`
  for the canonical frontmatter mapping.

> Derived from Ar9av/obsidian-wiki (MIT).