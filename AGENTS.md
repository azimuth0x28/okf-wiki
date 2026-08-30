# okf-wiki — Agent Context

A **skill-based framework** for building and maintaining knowledge bases where
the store is natively an **OKF v0.2 (Open Knowledge Format) bundle**. No
runtime, no API keys, no vendor — every skill here is a markdown instruction
that you, the agent, execute directly. The bundle is markdown you can read,
extend, and transfer between tools without conversion.

> **Format not platform.** okf-wiki is derived from Ar9av/obsidian-wiki (MIT)
> with one key inversion: the principle is no longer "Obsidian is the IDE" —
> the bundle is portable by design. Obsidian remains a fine optional viewer;
> the source of truth is the bundle's markdown.

## Skills (37)

Skills live in `.skills/<name>/SKILL.md`. The current directory may be a subset
(this catalog is the target end-state, not a snapshot); re-run `bash setup.sh`
after pulling new skills so every agent picks them up.

### Core

| Skill | One-line purpose |
|---|---|
| `okf-wiki` | Core architecture: OKF v0.2 conformance, canonical frontmatter mapping, three-layer / four-stage model, reserved files, write protocol. The other 36 skills cite this one. |
| `wiki-setup` | Initialize a fresh OKF v0.2 bundle or attach to an existing one (creates `index.md` with `okf_version: "0.2"`, `log.md`, `_cache/`, `_raw/`, `_meta/taxonomy.md`, `.manifest.json`, `okf-base.yaml`). |
| `bundle-switch` | Maintain multiple bundles and route requests between them (the persistent-default symlink; replaces `wiki-switch`). |

### Ingest

| Skill | One-line purpose |
|---|---|
| `wiki-ingest` | Distill documents into wiki pages — four stages (ingest → pull → merge → schema); Append/Rebuild/Restore modes; SHA-256 delta manifest. |
| `wiki-capture` | Save a current conversation, finding, or quick note to the bundle (and `_raw/`). |
| `wiki-update` | Sync the current project's knowledge into the bundle (code-graph-aware via `code-understand`). |
| `wiki-research` | Research a topic and write findings to the bundle. |
| `code-understand` | Code-graph-aware distiller used by `wiki-update` to decide what's worth remembering. |
| `daily-update` | Refresh indexes, run the daily cron, install terminal notification. |

### History ingest (router + per-agent)

| Skill | One-line purpose |
|---|---|
| `wiki-history-ingest` | Route `/wiki-history-ingest <agent>` to the right per-agent history skill. |
| `claude-history-ingest` | Mine Claude Code session history. |
| `codex-history-ingest` | Mine Codex CLI session and rollout logs. |
| `copilot-history-ingest` | Mine GitHub Copilot session history. |
| `hermes-history-ingest` | Mine Hermes memory and session history. |
| `openclaw-history-ingest` | Mine OpenClaw session history. |
| `pi-history-ingest` | Mine Pi coding-agent session history. |
| `wiki-agent` | Pull a topic slice from another agent's history into the bundle. |

### Query / retrieval

| Skill | One-line purpose |
|---|---|
| `wiki-query` | Answer questions against the bundle with typed-link citations and OKF trust context (`status`, `verified`). |
| `wiki-narrate` | Compile a cited briefing on a topic into `_readouts/`. |
| `wiki-digest` | Weekly/monthly summary of recent learning from `log.md`. |
| `wiki-context-pack` | Compile bounded bundle context for another agent (no writes). |
| `memory-bridge` | Cross-tool memory comparison grouped by `generated.by` actor. |
| `session-brain` | Build a topic graph over raw agent sessions; sidecar at `~/.config/okf-wiki/session-graph/` (out of bundle). |
| `session-search` | Find or load one specific session from the agent's history. |

### Maintenance

| Skill | One-line purpose |
|---|---|
| `wiki-status` | Audit ingestion state, delta, and equilibrium of maintenance skills. |
| `wiki-lint` | Audit the bundle for OKF conformance (E1–E4), broken links, orphans, stale content, illegal lifecycle transitions (W1–W7). |
| `wiki-dedup` | Identity resolution and merge of near-duplicate pages with extension-field preservation. |
| `cross-linker` | Discover and insert typed cross-references (allowlist: `extends`/`implements`/`contradicts`/`derived_from`/`uses`/`replaces`/`related_to`). |
| `tag-taxonomy` | Enforce the controlled vocabulary in `_meta/taxonomy.md`. |
| `wiki-synthesize` | Surface cross-cutting connections and gap-fill synthesis pages. |
| `wiki-stage-commit` | Review and promote staged writes (opt-in via `WIKI_STAGED_WRITES`). |
| `wiki-rebuild` | Archive, rebuild, or restore the bundle via timestamped snapshots in `_archives/`. |

### Transform

| Skill | One-line purpose |
|---|---|
| `wiki-import` | Merge an external OKF bundle (any v0.2 producer) with conflict resolution and extension-field preservation; v0.1 fallback. |
| `wiki-export` | Package the bundle as OKF plus graph artifacts (`graph.json`, GraphML, Cypher, SQL, `graph.html`). |

### Meta

| Skill | One-line purpose |
|---|---|
| `skill-creator` | Create a new skill folder (template, conventions, validation). |
| `vault-skill-factory` | Compile bundle pages into a domain-expert skill (or just turn your notes into a skill). |
| `impl-validator` | Verify a skill or bundle change against expectations before sign-off. |

## Configuration

Resolve config using the **Config Resolution Protocol** in
`.skills/okf-wiki/SKILL.md`:

0. **Inline bundle override (`@name`)** — if the request contains an `@<name>`
   token, resolve `<global config dir>/config.<name>` directly, overriding the
   steps below. See "Targeting a specific bundle" right after this list.
1. **Walk up from CWD** — look for a `.env` file in the current directory,
   then each parent, up to `$HOME`. Stop at the first `.env` that contains
   `OKF_BUNDLE_PATH`.
2. **Global config** — if no local `.env` is found, read `<global config dir>/config`.
3. **Prompt setup** — if neither exists, tell the user to run `wiki-setup`.

The **global config dir** is XDG-style: `$XDG_CONFIG_HOME/okf-wiki` (default
`~/.config/okf-wiki`). Installs migrated from the source project that already
have a `~/.obsidian-wiki` directory keep using it, so existing setups never
break; new installs use the XDG path.

The resolved config sets `OKF_BUNDLE_PATH` (where the bundle lives). It may
also set `OKF_WIKI_REPO` (where this repo is cloned) and other optional
variables.

### Targeting a specific bundle

You can maintain multiple bundles (each a `<global config dir>/config.<name>`
file managed by `bundle-switch`) and reach any of them from any directory:

- **`@name` (per-invocation override)** — prefix or mention `@<name>` anywhere
  in a request to route that one command to that bundle, e.g. `@work save this`
  or `wiki-query @personal what do I know about X`. It overrides the CWD
  `.env` and the active symlink **for that invocation only** — it does **not**
  flip your default bundle. If `config.<name>` doesn't exist, the skill reports
  it and lists available bundles; do **not** silently fall back to the default.
  The `@name` is stripped before the rest of the request is used as content.
- **`/bundle-switch <name>` (persistent default)** — re-points the active
  symlink so all future requests use that bundle. (Legacy alias:
  `wiki-switch`; new name is `bundle-switch`.) This is your default "brain"
  bundle; use `@name` to dip into the other one without switching.

**After reading config, always read `$OKF_BUNDLE_PATH/AGENTS.md` if it exists.**
It contains owner-specific conventions (domain vocabulary, ingest
preferences, writing style, project scoping) that override framework defaults
for all skills. Apply it for the duration of the session.

## Bundle Structure (OKF v0.2 native)

```
$OKF_BUNDLE_PATH/
├── index.md                       # Root catalog with okf_version: "0.2"
├── log.md                         # Newest-first ISO-dated entries
├── _cache/hot.md                  # ~500-word semantic snapshot of recent activity
├── .manifest.json                 # Delta-ledger of ingests (SHA-256)
├── concepts/  entities/  skills/  references/  synthesis/  journal/  projects/
│   ├── index.md                   # Per-dir, no frontmatter (links only)
│   └── <name>.md                  # OKF v0.2 + okf-wiki extension fields
├── _raw/  _staging/  _archives/  _readouts/  _meta/  _cache/  # Out of OKF scope
│   ├── _meta/taxonomy.md
│   └── _cache/hot.md
├── _insights.md
└── okf-base.yaml                  # okflint profile (extension-fields whitelist)
```

Every bundle page carries OKF v0.2 frontmatter — minimum `type` (TitleCase)
and `generated`; pages built from sources also carry `sources` with `resource`.
Pages connect via file-relative markdown links (`[topic](./concepts/topic.md)`);
absolute paths are reserved for `wiki-import`/`wiki-export` cross-bundle
references. See `.skills/okf-wiki/SKILL.md` for the canonical frontmatter
mapping and write protocol.

## Skill Routing

Match the user's intent to the right skill:

| User says something like… | Skill |
|---|---|
| "set up my bundle" / "initialize" | `wiki-setup` |
| "/wiki-history-ingest claude" / "codex" / "copilot" / "hermes" / "openclaw" / "pi" | `wiki-history-ingest` (router) |
| "ingest" / "add this to the bundle" / "process these docs" / "process this export" | `wiki-ingest` |
| "import my Claude history" / "mine my conversations" | `claude-history-ingest` |
| "import my Codex history" / "mine my Codex sessions" | `codex-history-ingest` |
| "import my Hermes history" / "ingest ~/.hermes" | `hermes-history-ingest` |
| "import my OpenClaw history" / "ingest ~/.openclaw" | `openclaw-history-ingest` |
| "import my Copilot history" / "ingest ~/.copilot" | `copilot-history-ingest` |
| "import my Pi history" / "ingest ~/.pi" | `pi-history-ingest` |
| "what's the status" / "show the delta" | `wiki-status` |
| "what do I know about X" / any question | `wiki-query` |
| "use my bundle as context" / "context pack for X" / "bounded context" | `wiki-context-pack` |
| "narrate" / "briefing" / "explain this topic" / "/wiki-narrate" | `wiki-narrate` |
| "audit" / "lint" / "find broken links" / "bundle health" | `wiki-lint` |
| "dedup my bundle" / "find duplicate pages" / "merge duplicates" | `wiki-dedup` |
| "rebuild" / "start over" / "archive" / "restore" | `wiki-rebuild` |
| "link my pages" / "cross-reference" / "connect my bundle" | `cross-linker` |
| "fix my tags" / "normalize tags" / "tag audit" | `tag-taxonomy` |
| "update bundle" / "sync to bundle" / "save this to my bundle" | `wiki-update` |
| `@work update` / `wiki-query @personal …` / `@research save this` | Any matching skill + `@name` override |
| "export bundle" / "export graph" / "graphml" / "neo4j" / "OKF bundle" | `wiki-export` |
| "import bundle" / "load graph.json" / "import OKF bundle" / "/wiki-import` | `wiki-import` |
| "save this" / "/wiki-capture" / "capture this conversation" | `wiki-capture` |
| "/wiki-research [topic]" / "research X" / "find everything about Y" | `wiki-research` |
| "synthesize my bundle" / "find connections" / "what concepts co-occur" | `wiki-synthesize` |
| "create a new skill" | `skill-creator` |
| "/vault-skill-factory" / "make a skill from my bundle" | `vault-skill-factory` |
| "/wiki-claude [topic]" / "/wiki-codex [topic]" / "/wiki-hermes [topic]" / "/wiki-openclaw [topic]" / "/wiki-copilot [topic]" / "/wiki-pi [topic]" | `wiki-agent` |
| "/memory-bridge" / "browse codex memory" / "compare tool memories" | `memory-bridge` |
| "/session-brain" / "cluster my claude sessions" / "rebuild the session graph" | `session-brain` |
| "/wiki-sessions [topic]" / "which session did I do X in" / "find the session about X" | `session-search` |
| "/daily-update" / "morning sync" / "set up the daily cron" | `daily-update` |
| "/impl-validator" / "check this implementation" / "is this correct?" | `impl-validator` |
| "/bundle-switch NAME" / "switch to my work bundle" / "list my bundles" | `bundle-switch` |
| "/wiki-digest" / "weekly digest" / "knowledge summary" | `wiki-digest` |
| "/wiki-stage-commit" / "review staged pages" / "promote staged writes" | `wiki-stage-commit` |

### Session history: ingest vs. retrieve

Three skills read agent session caches, and they are not interchangeable:

- `wiki-history-ingest` (and its per-agent variants) **ingests** — distils
  sessions into permanent bundle pages.
- `wiki-agent` **ingests a slice** — finds sessions about one topic in
  another agent's history and pulls them into the bundle.
- `session-brain` / `session-search` **retrieve** — build a topic graph over
  the raw sessions and find or load one. They write a sidecar at
  `~/.config/okf-wiki/session-graph/` and never touch the bundle.

If the user wants knowledge preserved, ingest. If they want to find the
session where something happened, retrieve.

## Cross-Project Usage

The main use case: you're working in some other project and want to sync
knowledge into your bundle, query it, or compile bounded context. Three
portable skills handle this — `wiki-update`, `wiki-query`, and
`wiki-context-pack`. They work from any directory.

### wiki-update (write to bundle)

1. Resolve config using the Config Resolution Protocol to get `OKF_BUNDLE_PATH`
2. Scan the current project: README, source structure, git log, package metadata
3. Distill what's worth remembering (architecture decisions, patterns,
   trade-offs — not code listings)
4. Write to `$BUNDLE/projects/<project-name>.md`, cross-linking to
   concept/entity pages as needed
5. Update `.manifest.json`, the per-dir `index.md`, root `index.md`, `log.md`,
   and `_cache/hot.md` — atomically ("track everything")

On repeat runs, it checks `last_commit_synced` in `.manifest.json` and only
processes the delta via `git log <last_commit>..HEAD`.

### wiki-query (read from bundle)

1. Resolve config using the Config Resolution Protocol to get `OKF_BUNDLE_PATH`
2. Scan titles, tags, and `summary:` frontmatter fields first (cheap pass)
3. Only open page bodies when the index pass can't answer
4. Return a synthesized answer with `[topic](./concepts/topic.md)` citations

### wiki-context-pack (read-only context)

1. Resolve the target bundle and read its owner `AGENTS.md`
2. Rank existing notes without requiring schema migration
3. Compile summaries and selected excerpts within a hard token budget
4. Return a provenance-rich pack; never write it back to the bundle

## Visibility Tags (optional)

Pages can carry a `visibility/` tag to mark their intended reach. **This is
entirely optional** — untagged pages behave exactly as they always have
(visible everywhere). The system stays single-bundle, single source of truth.

| Tag | Meaning |
|---|---|
| *(no tag)* | Same as `visibility/public` — visible in all modes |
| `visibility/public` | Explicitly public — visible in all modes |
| `visibility/internal` | Team-only — excluded when querying in filtered mode |
| `visibility/pii` | Sensitive data — excluded when querying in filtered mode |

**Filtered mode** is opt-in, triggered by phrases like "public only",
"user-facing answer", "no internal content", or "as a user would see it" in a
query. Default mode shows everything.

`visibility/` tags are **system tags** — they don't count toward the 5-tag
limit and are listed separately from domain/type tags in the taxonomy.

See `wiki-query` and `wiki-export` skills for how the filter is applied.

## Core Principles

- **Compile, don't retrieve.** The bundle is pre-compiled knowledge. Update
  existing pages — don't append or duplicate.
- **Track everything.** Update `.manifest.json`, the per-dir `index.md`, root
  `index.md`, `log.md`, and `_cache/hot.md` after every write operation.
- **Connect with file-relative links.** Every page should link to related
  pages. This is what makes it a knowledge graph, not a folder of files.
- **Frontmatter is required (OKF v0.2).** Every bundle page needs `type` and
  `generated`; pages built from sources also need `sources` with `resource`.
  See `.skills/okf-wiki/SKILL.md` for the full canonical mapping.
- **Single source of truth.** Visibility tags shape how content is surfaced
  — they don't duplicate or separate it.
- **Keep context warm.** `_cache/hot.md` is a ~500-word semantic snapshot of
  recent activity. Every write skill updates it so the next session can pick
  up where the last one left off without crawling the full bundle.

## Portability Invariant (FR-7.3)

**Skill content is identical across agents; platform-specific differences
live ONLY in the bootstrap files.** The `.skills/<name>/SKILL.md` files are
the same regardless of whether the agent is Claude Code, Cursor, Windsurf,
Gemini CLI, Codex, Kiro, OpenClaw, Pi, or any other AGENTS.md-aware agent.
Per-agent entry points (`.agent/`, `.claude/`, `.cursor/`, `.github/`,
`.kiro/`, `.pi/`, `.windsurf/`) differ only in their discovery mechanism —
the routing tables, hooks, and frontmatter matchers that tell the host
where to find the skills. If two skills are different, that's a content
decision; if two bootstrap files are different, that's a platform constraint.
Never duplicate skill content into a bootstrap file.

## Architecture Reference

For the full pattern (three-layer architecture, page templates, project org,
OKF v0.2 schema mapping, write protocol, lifecycle invariants) read
`.skills/okf-wiki/SKILL.md`.

Human-facing documentation lives in `docs/` — `installation.md`, `agents.md`,
`skills.md`, `configuration.md`, `architecture.md`. `README.md` is a landing
page only; when you add a skill, config variable, or section, update the
matching `docs/` page rather than the README.

The bundle format is the [Open Knowledge Format (OKF) v0.2](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md) —
every page is markdown with YAML frontmatter, category subfolders, reserved
`index.md`/`log.md`. The OKF round-trip is lossless; the `graph.json`
round-trip is not (extension fields survive).

---

Derived from Ar9av/obsidian-wiki AGENTS.md (MIT).