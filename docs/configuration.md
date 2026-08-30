# Configuration

## How config is resolved

Skills resolve the bundle path in this order:

0. **Inline bundle override (`@name`)**: an `@<name>` token anywhere in a request resolves `<config dir>/config.<name>` directly, overriding everything below, for that request only.
1. **Walk up from CWD**: look for a `.env` in the current directory, then each parent, up to `$HOME`. Stop at the first one containing `OKF_BUNDLE_PATH`.
2. **Global config**: `<config dir>/config`.
3. **Prompt setup**: if neither exists, you will be told to run setup.

### Where the global config lives

The config directory follows the XDG Base Directory spec: `$XDG_CONFIG_HOME/okf-wiki`, which defaults to `~/.config/okf-wiki`.

Earlier versions of the source project used `~/.obsidian-wiki`. That location is still honored: if `~/.obsidian-wiki` exists and the XDG path does not, it is used as is. Upgrading never strands a working config, and no migration is required. New installs use the XDG path. To move an existing install, `mv ~/.obsidian-wiki ~/.config/okf-wiki`.

After resolving, skills also read `$OKF_BUNDLE_PATH/AGENTS.md` if it exists. That is where you put owner-specific conventions (domain vocabulary, ingest preferences, writing style, project scoping) which override framework defaults for every skill.

## Global writing profile

Setup creates a global `WRITING.md` profile for preferences that should apply across projects. New installs use `~/.config/okf-wiki/WRITING.md`. When the legacy `~/.obsidian-wiki` directory is active, the profile is `~/.obsidian-wiki/WRITING.md` instead.

Start with a small profile and edit it to suit your habits:

```markdown
## Language

Write in English. Keep technical terms in their original form.

## Tone and Voice

Be clear, concise, and practical.

## Avoid

Avoid filler, repetition, and unsupported claims.
```

Writing preferences are applied in this order, from highest to lowest precedence: framework and task requirements, project `AGENTS.md`, bundle `AGENTS.md`, then global `WRITING.md`. The global profile guides bundle markdown prose only. It does not change lint rules or create blocking behavior.

If the profile is missing, empty, or unreadable, skills fall back to the framework defaults and continue without custom global preferences.

Both the global config and `.env` use the same `KEY=value` format. Start from [`.env.example`](../.env.example).

The deterministic `lint`, `trust-record`, and `trust-check` commands use the same bundle-scoped resolution: an explicit path uses no unrelated config, `@name` reads only `<config dir>/config.<name>`, otherwise the nearest CWD `.env` wins before global config. Schema settings are read from that same resolved config only, so one bundle's lifecycle extensions cannot leak into another bundle.

## Core

| Variable | What it does | Default |
|---|---|---|
| `OKF_BUNDLE_PATH` | **Required.** Absolute path to your OKF bundle | *(empty)* |
| `OKF_WIKI_REPO` | Where this repo is cloned (set by setup; used for skill and asset lookups) | *auto* |
| `OKF_SOURCES_DIR` | Comma-separated source directories to ingest documents from | *(empty)* |
| `OKF_CATEGORIES` | Bundle page categories (directories created in the bundle) | `concepts,entities,skills,references,synthesis,journal` |
| `OKF_MAX_PAGES_PER_INGEST` | Max pages created or updated per ingest | `15` |
| `OKF_RAW_DIR` | Staging directory inside the bundle for unprocessed drafts | `_raw` |
| `LINT_SCHEDULE` | Health-check frequency: `daily` \| `weekly` \| `manual` | `weekly` |

> **Legacy alias.** `OBSIDIAN_VAULT_PATH` is recognized as a fallback for `OKF_BUNDLE_PATH` during migration from the source project. New configs should use `OKF_BUNDLE_PATH`.

Local git repo clones work in `OKF_SOURCES_DIR` (public or private, any host). Clone locally, then add the path. Repo directories are auto-detected via a `.git` folder and enumerated with `git ls-files`, so whatever the repo's own `.gitignore` excludes (`node_modules`, build output, venvs, secrets) is skipped automatically rather than relying on a hardcoded skip-list.

## History ingest

| Variable | What it does | Default |
|---|---|---|
| `CLAUDE_HISTORY_PATH` | Where to find Claude data | *auto-discovers from `~/.claude`* |
| `CODEX_HISTORY_PATH` | Where to find Codex data | `~/.codex` |
| `HERMES_HISTORY_PATH` | Where to find Hermes data | `~/.hermes` |
| `OPENCLAW_HISTORY_PATH` | Where to find OpenClaw data | `~/.openclaw` |
| `COPILOT_HISTORY_PATH` | Where to find Copilot CLI data | `~/.copilot/session-state` |
| `PI_HISTORY_PATH` | Where to find Pi sessions | `~/.pi/agent/sessions` |
| `WIKI_SKIP_PROJECTS` | Comma-separated substrings; project dirs matching any are skipped during scan, delta, and manifest steps. Example: `archived,scratch,sandbox` | *(empty)* |
| `WIKI_SESSION_BRAIN_DIR` | Where the session-brain sidecar is written | `~/.claude/session-brain` |

## Staged writes and trust

| Variable | What it does | Default |
|---|---|---|
| `WIKI_STAGED_WRITES` | When `true`, LLM-written pages land in `_staging/` for human review instead of the live bundle. Promote them with `/wiki-stage-commit` | *(unset, direct writes)* |
| `OKF_TRUST_STRICT` | When `1`, `okf-wiki lint` treats missing trust fields, ledger errors, stale reviews, and score mismatches as failures rather than warnings. Same as `lint --strict-trust` | *(unset)* |
| `OKF_ALLOWED_LIFECYCLES` | Comma-separated lifecycle extensions for this resolved bundle | *(framework defaults only)* |
| `OKF_ALLOWED_RELATIONSHIP_TYPES` | Comma-separated relationship-type extensions for this resolved bundle | *(framework defaults only)* |
| `OKF_REQUIRED_TRUST_FIELDS` | Comma-separated effective required trust fields. Allowed values: `base_confidence`, `lifecycle`, `lifecycle_changed`, `updated`; unknown values fail closed | `base_confidence,lifecycle` for lint; also `updated` for standalone trust commands |
| `OKF_SCHEMA_SOURCE` | Owner authority locator emitted in machine reports | `config:<resolved-config-path>` when overrides exist |

Schema resolution precedence is CLI flags > resolved environment/config values > framework defaults. Lifecycle and relationship-type extension lists are additive to framework defaults; CLI required-field values replace environment requiredness. CLI-only schema overrides use a `cli:<context>` source label rather than claiming a config-file provenance. If CLI and resolved config both contribute overrides, reports use `cli+config:<resolved-config-path>` unless `--schema-source` or `OKF_SCHEMA_SOURCE` supplies the owner authority explicitly.

The four schema variables are `OKF_ALLOWED_LIFECYCLES`, `OKF_ALLOWED_RELATIONSHIP_TYPES`, `OKF_REQUIRED_TRUST_FIELDS`, and `OKF_SCHEMA_SOURCE`. When any is present, its value and every comma-separated entry must be non-empty after trimming whitespace. Empty values, repeated commas, and trailing commas fail closed with exit 1; remove the variable entirely to use framework defaults. The distributable `.env.example` documents safe commented examples for all four.

Staged pages are not visible in graph views until promoted. `wiki-status` lists pending staged writes first when this mode is on. The work is done, it just needs your eyes. The `_staging/` directory is created at setup even when the mode is off.

## Bundle Skill Factory

`vault-skill-factory` turns mature curated pages into portable Agent Skills. Generated skills land in a review directory, never auto-installed, never written into `.skills/`.

| Variable | What it does | Default |
|---|---|---|
| `SKILL_FACTORY_OUTPUT_DIR` | Where generated skills are written | `<bundle>/_generated-skills` |
| `SKILL_FACTORY_MATURITY` | Which lifecycle states count as mature enough to harvest (pages with `tier: core` also qualify) | `reviewed,verified` |

## PageIndex (optional, long PDFs)

For long PDFs (books, reports), PageIndex builds a table-of-contents tree (section titles, summaries, page ranges) before ingest, so the agent reads only the relevant sections. Without it, `wiki-ingest` reads PDFs directly.

Install: clone [PageIndex](https://github.com/VectifyAI/PageIndex), create a venv, and put an LLM key in its `.env` (LiteLLM). See `.skills/wiki-ingest/references/pageindex.md`.

| Variable | What it does | Default |
|---|---|---|
| `PAGEINDEX_REPO` | Path to the PageIndex repo. Setting this enables the long-PDF branch | *(empty, disabled)* |
| `PAGEINDEX_MODEL` | LiteLLM model id PageIndex uses | `openai/glm-4.6` |
| `PAGEINDEX_MIN_PAGES` | Only preprocess PDFs with at least this many pages | `30` |
| `PAGEINDEX_WORKSPACE` | Cache dir for `*_structure.json` | `<PAGEINDEX_REPO>/results` |

## QMD semantic search (optional)

By default, `wiki-ingest` and `wiki-query` use Grep/Glob. Fully functional, no extra setup. If your bundle grows large or you want concept-level matches across your sources, plug in [QMD](https://github.com/tobi/qmd), either through MCP or by letting the agent call the local `qmd` CLI.

| Variable | What it does | Default |
|---|---|---|
| `QMD_WIKI_COLLECTION` | Collection indexing your compiled bundle pages. Used by `wiki-query` | *(empty, disabled)* |
| `QMD_PAPERS_COLLECTION` | Collection indexing your raw source documents. Used by `wiki-ingest` | *(empty, disabled)* |
| `QMD_TRANSPORT` | `mcp` (agent-configured MCP server) or `cli` (local `qmd` binary) | `mcp` |
| `QMD_CLI_SEARCH_MODE` | `quality` (rerank, best relevance), `balanced` (`--no-rerank`), or `fast` (semantic only) | `quality` |
| `QMD_CLI` | Override the `qmd` binary path if it is not on `PATH` | `qmd` |

**Setup:**

```bash
qmd collection add /path/to/bundle --name my-wiki
qmd collection add /path/to/sources --name papers
```

```env
QMD_WIKI_COLLECTION=my-wiki
QMD_PAPERS_COLLECTION=papers
QMD_TRANSPORT=mcp
QMD_CLI_SEARCH_MODE=quality
```

> **The two collections must stay disjoint.** `wiki-query` treats them as separate layers (compiled knowledge vs. raw staging) and cites them separately. Since `OKF_BUNDLE_PATH` contains `_raw/`, a plain `qmd collection add <bundle>` merges the two layers and makes superseded drafts retrievable and citable as though they were compiled pages.
>
> QMD has no `--ignore` flag, so scope the collection by editing `~/.config/qmd/index.yml`:
>
> ```yaml
> collections:
>   my-wiki:
>     path: /path/to/bundle
>     pattern: "**/*.md"
>     ignore:
>       - "_raw/**"
>       - "log.md"
> ```
>
> Then run `qmd update`.

**What changes when it is on:**

- `wiki-query` runs a semantic pass (lex+vec) against your bundle collection before falling back to Grep. Finds conceptually related pages even when the exact terms don't match.
- `wiki-ingest` queries your papers collection before writing a new page. Surfaces related sources, spots contradictions, and decides whether to create a new page or merge into an existing one.

Both degrade gracefully: with the collection names unset, they skip the QMD step silently and use Grep.

## Code understanding (optional)

`wiki-update` distills a project's structure before it writes knowledge into the bundle. When a supported code graph backend is available, `wiki-update` uses it to rank the project's most important modules, trace callers and callees, and expand changed files into their impact area before distilling. Without one, the built-in `ast-extract` + `rg` fallback is used. No extra dependency.

Missing CodeGraph never breaks normal `wiki-update` runs. The graph index lives in the project's `.codegraph/` sidecar and is never written into the bundle.

| Variable | What it does | Default |
|---|---|---|
| `CODE_UNDERSTANDING_BACKEND` | How `wiki-update` understands project structure: `auto` (CodeGraph when available, else the built-in `ast-extract` + `rg`), `builtin` (always the built-in, dependency-free), or `codegraph` (explicitly require CodeGraph; warn/error if unavailable) | `auto` |
| `CODE_UNDERSTANDING_CODEGRAPH_BIN` | Path to the `codegraph` binary if it is not on `PATH` | *(empty)* |

### Setup (optional)

Install the CodeGraph CLI once to enable the enhanced backend:

```bash
npm install -g @colbymchenry/codegraph
```

**MCP configuration is not required for okf-wiki; only the CodeGraph CLI is required.**

Verify with `code-understand` on your project. The codegraph check should flip to pass. If the binary is not on your `PATH`, set `CODE_UNDERSTANDING_CODEGRAPH_BIN` to its location instead.

- The first enhanced `wiki-update` run auto-initializes the project's `.codegraph/` index; later runs sync only what changed.
- Your agent can run the install for you. Just ask it to use CodeGraph when running `/wiki-update`.

## `_raw/` staging directory

`_raw/` is a staging area inside your bundle for unprocessed captures: rough notes, clipboard pastes, quick voice-memo transcripts. Drop files there and the next `wiki-ingest` run promotes them to proper bundle pages and removes the originals, so nothing is processed twice.

The fastest way to feed it during a live coding session:

```text
/wiki-capture --quick
```

It scans the current conversation, extracts bugs and gotchas, and writes structured draft files in under 60 seconds. No subagents, no manifest writes.

To promote everything waiting there:

```text
/wiki-ingest promote my raw pages
```

The directory is created automatically by `wiki-setup`. The path is configurable via `OKF_RAW_DIR`.

## Multi-bundle setup

You can maintain multiple bundles and route requests between them. Each bundle gets its own config file at `<config dir>/config.<name>`.

### Setting up a named bundle

```bash
# Create a named config
bundle-switch new work
# or manually: write to ~/.config/okf-wiki/config.work
```

Each config file sets `OKF_BUNDLE_PATH` (and optionally `OKF_WIKI_REPO`) for that bundle. The `BUNDLE_ID` (renamed from `VAULT_ID` in the source project) identifies the active bundle.

### Routing with `@name`

From any directory, route one request to a named bundle with `@name`:

```text
@work update wiki
@research save this
wiki-query @personal what do I know about MCP security
```

The `@name` override applies only to that request and never changes your default bundle.

### Switching the default

To change the default bundle, use `/bundle-switch <name>`. It re-points the active symlink so all future requests use that bundle.

All supported agents can use this syntax after `setup.sh`, because the shared skills and always-on bootstrap files all point back to the same Config Resolution Protocol.

## Syncing your bundle to GitHub

Your bundle is a directory of plain markdown files. Push it to a private GitHub repo and you get version history, backup, and cross-device sync for free. `setup.sh` offers to configure this during install.

**What setup does:**

1. `git init` your bundle if it is not already a repo
2. Creates a `.gitignore` excluding workspace and cache files
3. Sets the remote you supply. The bundle's own `git remote` is the source of truth for whether sync is configured, so it cannot drift
4. Optionally adds a `wiki-sync` shell alias
5. Optionally installs an hourly cron job

**Run a sync at any time:**

```bash
wiki-sync            # alias added by setup
```

Each run stages all changes, commits as `sync 2026-07-30 14:00`, and pushes.

**Configure it later, or by hand:**

```bash
cd /path/to/your/bundle
git init
git remote add origin https://github.com/you/my-wiki.git
```

**Hourly auto-sync via cron:**

```
0 * * * * cd /path/to/your/bundle && git add -A && git commit -m "sync $(date +'%Y-%m-%d %H:%M')" && git push >> ~/.config/okf-wiki/sync.log 2>&1
```

> Keep the repo **private** if your bundle contains personal notes. Nothing is sent to any third-party service. Your bundle lives on your machines and in your GitHub account only.

## Visibility tags (optional)

Pages can carry a `visibility/` tag marking their intended reach. This is entirely optional. Untagged pages behave exactly as they always have (visible everywhere). The system stays single-bundle, single source of truth.

| Tag | Meaning |
|---|---|
| *(none)* | Same as `visibility/public`. Visible in all modes |
| `visibility/public` | Explicitly public |
| `visibility/internal` | Team-only. Excluded in filtered mode |
| `visibility/pii` | Sensitive. Excluded in filtered mode |

**Filtered mode** is opt-in, triggered by phrases like "public only", "user-facing answer", "no internal content", or "as a user would see it" in a query. Default mode shows everything.

`visibility/` tags are system tags. They don't count toward the 5-tag limit and are listed separately from domain/type tags in the taxonomy.

## Memory server (optional)

Only read by the Dockerized HTTP + MCP front end. Irrelevant to local skill use.

| Variable | What it does | Default |
|---|---|---|
| `WIKI_API_KEY` | Bearer token required on every request | *(none, the server refuses to start without it)* |
| `WIKI_ALLOW_ANONYMOUS` | `1` disables auth entirely. Local development only | *(unset)* |
| `WIKI_PORT` | Port the server listens on | `8080` |
