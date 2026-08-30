# Skills Reference

Everything lives in [`.skills/`](../.skills/). Each skill is a markdown file the agent reads when your request matches its description. There is no runtime, no plugin system, no registration step.

Slash commands (`/skill-name`) work in Claude Code, Cursor, Windsurf, and most CLI agents. Everywhere else, just describe what you want.

okf-wiki ships **37 skills** ported from the 40 in the source project (Ar9av/obsidian-wiki): 30 adapted, 1 rewritten, 3 transformed, 3 preserved as meta. Three Obsidian-specific skills were removed.

## Core

| Skill | What it does | Verdict | Slash command |
|---|---|---|---|
| `okf-wiki` | Core architecture: OKF v0.2 conformance, canonical frontmatter mapping, three-layer model, reserved files, write protocol. Every other skill defers to this one | Rewritten from `llm-wiki` | `/okf-wiki` |
| `wiki-setup` | Initialize a fresh OKF v0.2 bundle or attach to an existing one. Creates `index.md` with `okf_version: "0.2"`, `log.md`, `_cache/`, `_raw/`, `_meta/taxonomy.md`, `.manifest.json`, `okf-base.yaml` | Adapted | `/wiki-setup` |
| `bundle-switch` | Maintain multiple named bundles and route requests between them. Re-points the persistent-default symlink | Adapted (renamed from `wiki-switch`) | `/bundle-switch <name>` |

## Ingest

| Skill | What it does | Verdict | Slash command |
|---|---|---|---|
| `wiki-ingest` | Distill documents into bundle pages. Four stages (ingest, pull, merge, schema). Append, Rebuild, and Restore modes. SHA-256 delta manifest | Adapted | `/wiki-ingest` |
| `wiki-capture` | Save the current conversation, finding, or quick note to the bundle and `_raw/`. `--quick` stages findings in under 60 seconds | Adapted | `/wiki-capture` |
| `wiki-update` | Sync the current project's knowledge into the bundle. Code-graph-aware via `code-understand`. Works from any repo | Adapted | `/wiki-update` |
| `wiki-research` | Autonomous multi-round web research, filed straight into the bundle | Adapted | `/wiki-research [topic]` |
| `code-understand` | Code-graph-aware distiller used by `wiki-update` to decide what is worth remembering. Ranks modules, traces callers and callees, expands changed files into their impact area | Adapted | `/code-understand` |
| `daily-update` | Daily maintenance cycle: source freshness, index rebuild, hot cache refresh | Adapted | `/daily-update` |

> **Note on `code-understand`.** This is the 40th source skill, absent from the original PRD skill table but present in the source project. It was adapted alongside the other ingest skills.

## History ingest

A unified router plus six per-agent extractors. Each mines a specific agent's session cache and distills it into bundle pages.

| Skill | What it does | Verdict | Slash command |
|---|---|---|---|
| `wiki-history-ingest` | Unified router for agent history ingest. Dispatches to the right per-agent skill | Adapted | `/wiki-history-ingest <agent>` |
| `claude-history-ingest` | Mine `~/.claude` conversations and memories (Claude Code and desktop) | Adapted | `/claude-history-ingest` |
| `codex-history-ingest` | Mine `~/.codex` sessions and rollout logs | Adapted | `/codex-history-ingest` |
| `copilot-history-ingest` | Mine `~/.copilot` CLI session history | Adapted | `/copilot-history-ingest` |
| `hermes-history-ingest` | Mine `~/.hermes` memories and sessions | Adapted | `/hermes-history-ingest` |
| `openclaw-history-ingest` | Mine `~/.openclaw` `MEMORY.md` and sessions | Adapted | `/openclaw-history-ingest` |
| `pi-history-ingest` | Mine `~/.pi/agent/sessions` JSONL history | Adapted | `/pi-history-ingest` |
| `wiki-agent` | Topic-first ingest from one agent's raw history. Finds sessions about a topic, extracts relevant blobs, distills them into pages | Adapted | `/wiki-claude`, `/wiki-codex`, `/wiki-hermes`, `/wiki-openclaw`, `/wiki-copilot`, `/wiki-pi` |

## Query and retrieval

| Skill | What it does | Verdict | Slash command |
|---|---|---|---|
| `wiki-query` | Answer questions from the bundle with typed-link citations and OKF trust context (`status`, `verified`). Tiered: reads summaries before page bodies | Adapted | `/wiki-query` |
| `wiki-narrate` | Compile a cited briefing, plain-language explanation, or progressive lecture from a topic. Output goes to `_readouts/` | Adapted | `/wiki-narrate <topic>` |
| `wiki-digest` | Newsletter-style summary of what you learned over a day, week, or month. Reads `log.md` (newest-first ISO dates) | Adapted | `/wiki-digest [period]` |
| `wiki-context-pack` | Produce a token-bounded context slice for a downstream agent or skill. No writes to the bundle | Adapted | `/wiki-context-pack` |
| `memory-bridge` | Browse and diff knowledge by which AI tool wrote it. Groups by `generated.by` actor | Adapted | `/memory-bridge` |

## Finding past sessions

These two build a retrieval index over your raw agent sessions. They write a sidecar at `~/.claude/session-brain/` and never touch the bundle.

| Skill | What it does | Verdict | Slash command |
|---|---|---|---|
| `session-brain` | Build and maintain a topic graph over your agent session history | Adapted | `/session-brain` |
| `session-search` | Find a past session by topic and load its context into the current conversation | Adapted | `/wiki-sessions <topic>` |

> **Ingest vs. retrieve.** If you want knowledge preserved as permanent bundle pages, use `wiki-history-ingest`. If you want to find the session where something happened, use these.

## Maintenance

| Skill | What it does | Verdict | Slash command |
|---|---|---|---|
| `wiki-status` | What is ingested, what is pending, the delta. Bundle-shape insights (hubs, bridges, clusters) and an equilibrium check across the maintenance skills | Adapted | `/wiki-status` |
| `wiki-lint` | Audit the bundle for OKF v0.2 conformance (E1-E4), broken links, orphans, stale content, illegal lifecycle transitions (W1-W7). Uses okflint | Transformed | `/wiki-lint` |
| `wiki-dedup` | Identity resolution. Merge pages covering the same concept under different names, with extension-field preservation | Adapted | `/wiki-dedup` |
| `cross-linker` | Discover unlinked mentions and weave them into the graph with typed cross-references (`extends`, `implements`, `contradicts`, `derived_from`, `uses`, `replaces`, `related_to`) | Adapted | `/cross-linker` |
| `tag-taxonomy` | Enforce a consistent tag vocabulary across every page, using the controlled vocabulary in `_meta/taxonomy.md` | Adapted | `/tag-taxonomy` |
| `wiki-synthesize` | Discover and fill synthesis gaps across concepts. Surfaces cross-cutting connections | Adapted | `/wiki-synthesize` |
| `wiki-stage-commit` | Review and promote staged pages when `WIKI_STAGED_WRITES=true` | Adapted | `/wiki-stage-commit` |
| `wiki-rebuild` | Archive the bundle, rebuild from scratch, or restore a previous archive. Timestamped snapshots in `_archives/` | Adapted | `/wiki-rebuild` |

## Transform

| Skill | What it does | Verdict | Slash command |
|---|---|---|---|
| `wiki-import` | Merge an external OKF bundle (any v0.2 producer) with conflict resolution and extension-field preservation. v0.1 fallback | Transformed | `/wiki-import` |
| `wiki-export` | Package the bundle as OKF plus graph artifacts: `graph.json`, GraphML, Cypher, SQL, `graph.html` | Transformed | `/wiki-export` |

## Meta

| Skill | What it does | Verdict | Slash command |
|---|---|---|---|
| `skill-creator` | Create, edit, and eval new skills | Kept | `/skill-creator` |
| `vault-skill-factory` | Turn a cluster of mature bundle pages into a portable "digital expert" skill. Generated skills land in a review directory, never auto-installed | Kept | `/vault-skill-factory` |
| `impl-validator` | Validate an implementation against its stated goal | Kept | `/impl-validator` |

## Removed (Obsidian-only)

Three skills from the source project were not ported. Each depended on Obsidian-specific functionality that has no place in a platform-agnostic bundle framework.

| Skill | Why removed |
|---|---|
| `graph-colorize` | Color-codes the Obsidian graph view by tag, category, or visibility. Purely an Obsidian UI feature |
| `wiki-dashboard` | Creates dynamic Obsidian Bases dashboard views (`.base` files). Obsidian-specific visualization |
| `obsidian-layout-adjustment` | Restyles Obsidian via CSS snippets (tabs, sidebars, graph panes). Purely cosmetic Obsidian customization |

## Verdict summary

| Verdict | Count | Skills |
|---|---|---|
| Adapted | 30 | All ingest, history, query, retrieval, and most maintenance skills, plus `bundle-switch`, `wiki-setup`, `code-understand` |
| Rewritten | 1 | `llm-wiki` became `okf-wiki` (core skill) |
| Transformed | 3 | `wiki-lint` (OKF conformance engine), `wiki-export` (OKF packaging), `wiki-import` (OKF merge) |
| Kept (meta) | 3 | `skill-creator`, `vault-skill-factory`, `impl-validator` |
| **Total ported** | **37** | |
| Removed | 3 | `graph-colorize`, `wiki-dashboard`, `obsidian-layout-adjustment` |
| **Source total** | **40** | |

## Writing your own

Ask your agent:

> "Create a skill that generates weekly summaries from my journal entries"

`skill-creator` walks you through drafting, testing, and refining it in `.skills/`.
