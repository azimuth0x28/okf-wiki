# Architecture

The bundle is the artifact. The agent is the maintainer. The format is portable.

No scripts run your knowledge pipeline. The skills are markdown files that tell an AI agent how to operate on your bundle. The agent uses the same read, write, and search tools it already has.

> **Format not platform.** okf-wiki is derived from Ar9av/obsidian-wiki (MIT) with one key inversion: the principle is no longer "Obsidian is the IDE." The bundle is portable by design. Obsidian remains a fine optional viewer; the source of truth is the bundle's markdown.

## Three-layer model

The architecture separates concerns into three layers:

1. **Skill layer** (`.skills/<name>/SKILL.md`). Markdown instructions the agent reads and executes. No runtime, no dependencies. Each skill is self-contained and platform-agnostic.

2. **Bundle layer** (`$OKF_BUNDLE_PATH/`). The OKF v0.2 knowledge bundle. A directory of markdown files with YAML frontmatter, category subfolders, and reserved files. This is the persistent artifact.

3. **Agent layer** (the AI coding agent). Claude Code, Cursor, Windsurf, Codex, Gemini CLI, Kiro, OpenClaw, Pi, or any AGENTS.md-aware agent. The agent reads skills, operates on the bundle, and writes results using its built-in tools.

The skill layer is identical across agents (portability invariant FR-7.3). The bundle layer is identical across tools (OKF v0.2 conformance). Only the agent layer varies.

## The four ingest stages

Every time you feed the brain, it runs through these:

### 1. Ingest

The agent reads your source material directly. Markdown, PDFs (with page ranges), JSONL conversation exports, plain text logs, chat exports, meeting transcripts, and images (screenshots, whiteboard photos, diagrams; vision-capable model required). No preprocessing step, no pipeline to run. The agent reads the file the same way it reads code.

### 2. Pull information

From the raw source, the agent pulls out concepts, entities, claims, relationships, and open questions. A conversation about debugging a React hook yields a "stale closure" pattern. A research paper yields the key idea and its caveats. A work log yields decisions and their rationale. Noise gets dropped, signal gets kept.

Each page also gets a 1-2 sentence `summary:` in its frontmatter at write time. Later queries use this to preview pages without opening them.

### 3. Merge

New knowledge merges against what is already there. If a concept page exists, the agent updates it: merging new information, noting contradictions, strengthening cross-references. If it is genuinely new, a page gets created. Nothing is duplicated. Sources are tracked in frontmatter so every claim stays attributable.

### 4. Schema

The schema is not fixed upfront. It emerges from your sources and evolves as you add more. The agent maintains coherence: categories stay consistent, links point to real pages, the index reflects what is actually there. When you add a new domain, the schema expands without breaking what exists.

A `.manifest.json` tracks every source that has been ingested (path, timestamps, which pages it produced). On the next run, the agent computes the delta and only processes what is new or changed.

## The loop

1. Agent resolves the bundle path (`@name` override, then `.env`, then global config)
2. Agent reads `.manifest.json` to know what has already been done
3. Agent reads the relevant skill for instructions
4. Agent uses its built-in tools to do the work
5. Agent updates `.manifest.json`, `index.md`, `log.md`, and `_cache/hot.md`
6. Output is OKF v0.2 conformant markdown with frontmatter and file-relative links

## Code-aware project ingest

`/wiki-update` adds a code-understanding step before distillation when the current project contains source code. Git answers what changed; `code-understand` answers what that change touches; the agent decides what is worth remembering; the bundle stores only the distilled result.

With the default `CODE_UNDERSTANDING_BACKEND=auto`, CodeGraph is used when available and the built-in extractor plus `rg` is used otherwise. CodeGraph is an optional local accelerator, not part of the bundle: its `.codegraph/` index stays beside the project and is never copied into bundle pages.

### First project ingest

On the first `/wiki-update`, there is no `last_commit_synced` entry for the project, so the agent needs an initial architecture map:

1. Resolve the bundle and read `.manifest.json`; treat the project as new when no previous sync exists.
2. Run `code-understand` across the tracked project.
3. If CodeGraph is available, the first enhanced run initializes the local `.codegraph/` index. Otherwise the built-in extractor plus `rg` produces the focus map.
4. Use the ranked symbols and `file:line` evidence to read the load-bearing code selectively instead of opening the whole repository.
5. Distill architecture, decisions, dependencies, and reusable knowledge into project and global bundle pages.
6. Update `.manifest.json`, `index.md`, `log.md`, and `_cache/hot.md`, recording the current `HEAD` as `last_commit_synced`.

```text
project
   |
full code-understand pass
   |
CodeGraph index (when available)
   |
ranked focus map
   |
selective source reads
   |
LLM distillation
   |
OKF bundle + last_commit_synced
```

### Ongoing project maintenance

Later `/wiki-update` runs are delta-based. The previous `last_commit_synced` narrows the work to what changed and the impact area around it:

1. Read `last_commit_synced` from `.manifest.json` and verify that commit is still an ancestor of `HEAD`. If history was rewritten, fall back to the first-ingest path.
2. Compute the Git delta since the previous sync. If nothing meaningful changed, stop without rewriting the bundle.
3. Run `code-understand --since <last_commit_synced>`.
4. When CodeGraph is active, reuse the existing local index, sync the changed code, and expand changed files into relevant callers, callees, tests, and impact areas.
5. Read only the ranked affected code, re-check previously recorded relationships, and prune relationships that are no longer valid.
6. Merge only meaningful new knowledge into the bundle, then advance `last_commit_synced` to the current `HEAD`.

```text
last_commit_synced
   |
Git delta
   |
code-understand --since
   |
changed symbols + impact area
   |
selective re-read / stale-link pruning
   |
LLM distillation
   |
updated bundle + new last_commit_synced
```

This keeps the responsibilities separate: Git tracks change history, CodeGraph (or the built-in fallback) maps code structure and impact, the LLM performs judgement and distillation, and the OKF bundle remains the persistent knowledge artifact.

## Bundle anatomy (OKF v0.2 native)

```
$OKF_BUNDLE_PATH/
+-- index.md                       # Root catalog with okf_version: "0.2"
+-- log.md                         # Newest-first ISO-dated entries
+-- _cache/hot.md                  # ~500-word semantic snapshot of recent activity
+-- .manifest.json                 # Delta-ledger of ingests (SHA-256)
+-- .manifest.lock                 # Advisory lock held during manifest writes
+-- concepts/  entities/  skills/  references/  synthesis/  journal/  projects/
|   +-- index.md                   # Per-dir, no frontmatter (links only)
|   +-- <name>.md                  # OKF v0.2 + okf-wiki extension fields
+-- _raw/                          # Staging: drop rough notes, next ingest promotes them
+-- _staging/                      # Review queue when WIKI_STAGED_WRITES=true
+-- _archives/                     # Timestamped snapshots for rebuild/restore
+-- _readouts/                     # Narrative readouts from wiki-narrate
+-- _meta/
|   +-- taxonomy.md                # Controlled tag vocabulary
+-- _insights.md                   # Graph analysis: hubs, bridges, dead ends
+-- okf-base.yaml                  # okflint profile (extension-fields whitelist)
```

Knowledge that is project-specific goes under `projects/`. Knowledge that is general goes in the global category directories. Both are cross-referenced with file-relative markdown links (`[topic](./concepts/topic.md)`).

### Reserved files

Two files at the bundle root are reserved by OKF v0.2:

- **`index.md`** carries `okf_version: "0.2"` in its frontmatter and serves as the master catalog. Every page links from here.
- **`log.md`** is a newest-first chronological activity log. Every write skill appends an ISO-dated entry.

Per-directory `index.md` files (inside each category folder) contain links only, no frontmatter.

### Out-of-scope zones

Directories prefixed with `_` and dot-files are outside OKF conformance scope. They contain staging, caching, and operational artifacts:

- `_raw/`: unprocessed captures and rough notes
- `_staging/`: review queue for staged writes
- `_archives/`: timestamped snapshots
- `_readouts/`: narrative output from `wiki-narrate`
- `_meta/`: controlled vocabulary (`taxonomy.md`)
- `_cache/`: warm context (`hot.md`)
- `.manifest.json`: ingest ledger
- `.manifest.lock`: advisory lock

These are excluded from OKF validation. They are implementation details of the framework, not part of the portable knowledge format.

### `_cache/hot.md`

`hot.md` deserves a mention. It is a running semantic snapshot (roughly 500 words) of recent activity. Every write skill updates it, so the next session picks up where the last one left off without crawling the whole bundle. It lives at `_cache/hot.md` (not at the root) because it is an operational artifact, not portable knowledge.

### `.manifest.json`

The manifest is the one file several writers touch at once (parallel ingest subagents, the Dockerized server writing a bundle a local skill is also using). Updates to it go through an advisory lock (`.manifest.lock`) and atomic file replacement. Hand-editing the manifest in a parallel run bypasses that and drops whichever write lands second. The prose files take no lock: `log.md` is append-only, and `index.md` / `_cache/hot.md` are rewritten wholesale by whichever skill last ran.

## OKF v0.2 conformance

The bundle format is the [Open Knowledge Format (OKF) v0.2](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md). Three conformance rules:

1. Every non-reserved `.md` file has parseable YAML frontmatter.
2. Every such file has a non-empty `type` field in its frontmatter.
3. Reserved files (`index.md`, `log.md`) follow their defined structure.

Consumers are required to accept: missing optional fields, unknown `type` values, unknown frontmatter keys, broken links, and missing `index.md` files. Extension fields (such as `aliases`, `relationships`, `provenance`, `base_confidence`, `tier`, `lifecycle_changed`, `updated`, `superseded_by`, and `lifecycle`) are preserved verbatim by any conformant consumer. Your enriched metadata travels with the bundle.

### Validation rules

The `wiki-lint` skill audits the bundle against two rule sets:

- **E1-E4 (error rules).** Structural violations: missing frontmatter, missing `type` field, reserved-file structure violations, broken links.
- **W1-W7 (warning rules).** Lifecycle and quality checks: illegal lifecycle transitions, stale content, orphaned pages, missing trust fields, score mismatches.

The OKF round-trip (bundle to OKF and back) is lossless. The `graph.json` round-trip is not (it carries structure, not page bodies), though extension fields survive.

For the canonical frontmatter mapping (native fields to OKF v0.2 fields) and the full write protocol, read [`.skills/okf-wiki/SKILL.md`](../.skills/okf-wiki/SKILL.md).

## Core principles

- **Compile, don't retrieve.** The bundle is pre-compiled knowledge. Update existing pages. Don't append or duplicate.
- **Track everything.** `.manifest.json` after ingesting; `index.md`, `log.md`, and `_cache/hot.md` after any write.
- **Connect with file-relative links.** `[topic](./concepts/topic.md)` is the link format. This is what makes it a knowledge graph rather than a folder of files.
- **Frontmatter is required (OKF v0.2).** Every page, every time. Minimum `type` and `generated`; pages built from sources also carry `sources` with `resource`.
- **Single source of truth.** Visibility tags shape how content surfaces. They never duplicate or separate it.
- **Keep context warm.** `_cache/hot.md` is updated by every write skill so the next session starts with recent context.

## Portability invariant (FR-7.3)

**Skill content is identical across agents; platform-specific differences live only in the bootstrap files.** The `.skills/<name>/SKILL.md` files are the same regardless of whether the agent is Claude Code, Cursor, Windsurf, Gemini CLI, Codex, Kiro, OpenClaw, Pi, or any other AGENTS.md-aware agent.

Per-agent entry points (`.agent/`, `.claude/`, `.cursor/`, `.github/`, `.kiro/`, `.pi/`, `.windsurf/`) differ only in their discovery mechanism: the routing tables, hooks, and frontmatter matchers that tell the host where to find the skills. If two skills are different, that is a content decision; if two bootstrap files are different, that is a platform constraint. Never duplicate skill content into a bootstrap file.

## What was added on top of Karpathy's pattern

The [original gist](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) is the seed: compile knowledge once into interconnected markdown and keep it current, instead of asking an LLM the same questions repeatedly or running RAG every time. Here is what got built around it.

- **Delta tracking.** A manifest tracks every source file ingested. Come back later and it computes the delta, processing only what is new or changed. You are not re-ingesting your document library every time.

- **Project-based organization.** Knowledge is filed under projects when project-specific, globally when not. Both cross-referenced. Ten codebases, ten spaces in the bundle.

- **Archive and rebuild.** When the bundle drifts too far from its sources, archive the whole thing (timestamped snapshot, nothing lost) and rebuild. Or restore any previous archive.

- **Multi-agent ingest.** Documents, PDFs, Claude Code history, Codex sessions, Hermes memories, OpenClaw `MEMORY.md`, Pi sessions, Copilot CLI history, Windsurf data, ChatGPT exports, Slack logs, meeting transcripts, raw text. Dedicated skills for each agent, plus a catch-all for arbitrary exports.

- **Cross-agent targeted search.** `/wiki-codex "rust ownership"` from inside Claude Code finds your Codex sessions on that topic, extracts the relevant blobs, distills them into pages, and returns a synthesized answer. Topic-first, not session-first. Each agent has its own extraction strategy. Pair with `/memory-bridge diff` to see what each tool uniquely contributed.

- **Audit and lint.** Orphaned pages, broken links, stale content, contradictions, missing frontmatter. Plus a dashboard of what is ingested vs. pending.

- **Identity resolution.** `wiki-dedup` finds pages covering the same concept under different names ("RSC" vs. "React Server Components") and merges them.

- **Automated cross-linking.** After ingest, the cross-linker scans for unlinked mentions and weaves them into the graph with typed references.

- **Tag taxonomy.** A controlled vocabulary in `_meta/taxonomy.md`, with a skill that audits and normalizes tags bundle-wide.

- **Provenance tracking.** Every claim is tagged: extracted (default), `^[inferred]` (LLM synthesis), or `^[ambiguous]` (sources disagree). A `provenance:` block in frontmatter summarizes the mix per page, and `wiki-lint` flags pages drifting into mostly speculation. You can always tell what your bundle knows from what it guessed.

- **Trust ledger.** `trust-record` and `trust-check` record and validate human-approved confidence reviews against material fingerprints, so CI can gate on "a person actually checked this."

- **Multimodal sources.** Screenshots, whiteboard photos, slide captures, and diagrams ingest like text. Visible text is transcribed verbatim, interpreted content tagged as inferred.

- **Bundle insights.** `wiki-status` can analyze the shape of the bundle itself: top hubs, bridge pages (nodes whose removal would partition the graph), tag cluster cohesion, scored surprising connections, a graph delta since last run, and questions the structure is uniquely positioned to answer. Output goes to `_insights.md`.

- **Bundle equilibrium.** The maintenance skills (`wiki-lint`, `wiki-dedup`, `cross-linker`, `tag-taxonomy`) each optimize one shared bundle for a different objective, so any of them can undo another's work. `wiki-status` equilibrium mode runs every audit in report-only form and reports whether any skill still has a pending change. The bundle is converged only when all of them propose nothing. It also detects oscillation, where two skills keep reversing each other and the bundle can never settle.

- **Graph export and import.** `wiki-export` turns the link graph into `graph.json`, `graph.graphml` (Gephi/yEd), `cypher.txt` (Neo4j), `postgres.sql` (Postgres), a self-contained interactive `graph.html`, or an OKF bundle. `wiki-import` reads any of it back.

- **Tiered retrieval.** `wiki-query` reads titles, tags, and summaries first, opening page bodies only when the cheap pass cannot answer. Say "quick answer" to force index-only mode. Query cost stays roughly flat from 20 pages to 2000.

- **Session brain.** A topic graph over your raw agent session history, so you can find the session where something happened.

- **Staged writes.** Set `WIKI_STAGED_WRITES=true` and LLM-written pages queue in `_staging/` for review before landing in the live bundle.

## Repo layout

```
okf-wiki/
+-- .skills/                             # Canonical skill definitions (source of truth)
|   +-- <skill-name>/SKILL.md            #   37 skills (see docs/skills.md)
|
+-- CLAUDE.md                            # Bootstrap symlink to AGENTS.md (Claude Code)
+-- GEMINI.md                            # Bootstrap symlink to AGENTS.md (Gemini CLI)
+-- AGENTS.md                            # Bootstrap (Codex, OpenCode, Aider, Droid, Trae, Hermes, OpenClaw)
+-- .hermes.md                           # Bootstrap symlink to AGENTS.md (Hermes)
+-- .cursor/rules/okf-wiki.mdc           # Always-on rule (Cursor)
+-- .windsurf/rules/okf-wiki.md          # Always-on rule (Windsurf)
+-- .kiro/steering/okf-wiki.md           # Always-on rule (Kiro)
+-- .agent/rules/okf-wiki.md             # Always-on rule (Google Antigravity)
+-- .agent/workflows/okf-wiki.md         # Slash-command registry (Antigravity)
+-- .github/copilot-instructions.md      # Always-on (GitHub Copilot)
|
+-- .claude/skills/   -> symlinks to .skills/*   (created by setup.sh)
+-- .cursor/skills/   -> symlinks to .skills/*
+-- .windsurf/skills/ -> symlinks to .skills/*
+-- .agents/skills/   -> symlinks to .skills/*
+-- .pi/skills/       -> symlinks to .skills/*
+-- .kiro/skills/     -> symlinks to .skills/*
|
+-- setup.sh                             # One-command agent setup
+-- .env.example                         # Configuration template
+-- scripts/
|   +-- validate.sh                      # Deterministic OKF v0.2 check
+-- docs/                                # You are here
```

Global symlink targets created by setup are listed in [Installation](installation.md).

For the full pattern (three-layer architecture, page templates, project organization, canonical frontmatter mapping) read [`.skills/okf-wiki/SKILL.md`](../.skills/okf-wiki/SKILL.md).
