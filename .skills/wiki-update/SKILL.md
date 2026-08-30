---
name: wiki-update
description: >
  Sync the current project's knowledge into the OKF bundle. Use this skill from any project
  when the user says "update wiki", "update bundle", "sync to bundle", "save this to my bundle",
  or wants to distill what they've been working on into their knowledge base. This is the
  cross-project skill that lets you push knowledge from wherever you are into the bundle. Accepts
  inline named-bundle routing like "@work update" via the shared Config Resolution Protocol.
---

# Wiki Update — Sync Any Project to Your Bundle

You are distilling knowledge from the current project into the user's OKF v0.2 bundle. This skill works from any project directory, not just the okf-wiki repo. The bundle is portable by design — format, not platform — so every page you write here is readable by any agent or OKF consumer without conversion.

## Before You Start

**Writing profile:** Before drafting or rewriting natural-language Markdown, read and apply the `Writing Profile Resolution` section in `okf-wiki/SKILL.md`. Framework schema, provenance, safety, and operation-specific requirements take precedence.
`WRITING.md` preferences apply only to newly drafted or rewritten natural-language Markdown; preserve source content and structured records.

1. **Resolve config** — follow the Config Resolution Protocol in `okf-wiki/SKILL.md` (inline `@name` override → walk up CWD for `.env` → global config → prompt setup). This gives `OKF_BUNDLE_PATH`, `OKF_WIKI_REPO`, and optional QMD settings such as `QMD_WIKI_COLLECTION`. The global config dir is XDG-style (`~/.config/okf-wiki`; legacy `~/.obsidian-wiki` installs keep working). Works from any project directory. Then read `$OKF_BUNDLE_PATH/AGENTS.md` if it exists — owner conventions override framework defaults.
2. Read `$OKF_BUNDLE_PATH/.manifest.json` to check if this project has been synced before.
3. Read `$OKF_BUNDLE_PATH/index.md` to know what the bundle already contains.

When writing internal links in Steps 4–5, use **file-relative markdown links** per the *Link Format* section in `okf-wiki/SKILL.md` — there is no wikilink mode.

## Step 1: Understand the Project

Figure out what this project is by scanning the current working directory:

- `README.md`, docs/, any markdown files
- Source structure (frameworks, languages, key abstractions)
- `package.json`, `pyproject.toml`, `go.mod`, `Cargo.toml` or whatever defines the project
- Git log (focus on commit messages that signal decisions, not "fix typo" stuff)
- Agent memory files if they exist (`.claude/` in the project, or your agent's equivalent)

Skip machine-generated directories (`.codegraph/`, `node_modules/`, build output) — they inform the scan, never the bundle (see Step 3b for the `.codegraph/` rule).

Derive a clean project name from the directory name.

## Step 2: Compute the Delta

Check `.manifest.json` for this project:

- **First time?** Full scan. Everything is new.
- **Synced before?** Look at `last_commit_synced` (top level in `.manifest.json` — this skill maintains it; `wiki-status` reads it and leaves it untouched). Before computing the delta, verify the stored SHA is still reachable:
  ```bash
  git merge-base --is-ancestor <last_commit_synced> HEAD
  ```
  - **Exit 0 (ancestor):** Safe. Run `git log <last_commit_synced>..HEAD --oneline` to see what changed.
  - **Exit 1 (not an ancestor — rebase or force-push occurred):** The stored SHA is no longer in this branch's history. Warn the user: *"Stored commit `<sha>` is no longer reachable — branch may have been rebased or force-pushed. Falling back to full scan."* Then treat as first-time sync: re-scan everything and update `last_commit_synced` to the current HEAD SHA at the end of Step 6.

**Multi-project bundles:** when several projects sync into one bundle, also record each project's own `last_commit_synced` inside its `projects` entry and prefer that value for this project's delta check; the top-level key always reflects the most recent sync.

If nothing meaningful changed since last sync, tell the user and stop.

## Step 3: Decide What to Distill

This is the core question from Karpathy's pattern: **what would you want to know about this project if you came back in 3 months with zero context?**

Worth distilling:

- Architecture decisions and *why* they were made
- Patterns discovered while building (things you'd Google again otherwise)
- What tools, services, APIs the project depends on and how they're wired together
- Key abstractions, how they connect, what the mental model is
- Trade-offs that were evaluated, what was picked and why
- Things learned while building that aren't obvious from reading the code

Not worth distilling:

- File listings, boilerplate, config that's obvious
- Individual bug fixes with no broader lesson
- Dependency versions, lock file contents
- Implementation details the code already says clearly
- Routine changes anyone could read from the diff

The heuristic: **if reading the codebase answers the question, don't wiki it. If you'd have to re-derive the reasoning by reading git blame across 20 commits, wiki it.**

### Step 3b: Build a code-understanding focus map (optional)

**GUARD: If the `okf-wiki code-understand` command fails or is unavailable, skip this step and continue — it is an optimisation, not a requirement.**

When this project contains code, run the local code-understanding extractor before distilling. It parses the codebase locally and returns a focus map — the ranked files and symbols the architecture hangs on — so you read the load-bearing parts instead of scanning everything. Backend selection follows `CODE_UNDERSTANDING_BACKEND` (see *Environment Variables* in `okf-wiki/SKILL.md`):

- `auto` (default) — use CodeGraph when installed, fall back to the builtin extractor (regex AST + `rg`) otherwise.
- `builtin` — force the dependency-free path.
- `codegraph` — explicitly require the enhanced backend; warn or error when it's unavailable rather than silently degrading.

```bash
okf-wiki code-understand --project "$(pwd)" --pretty
```

When this is not the first sync (Step 2 computed `last_commit_synced`), seed the focus map from the delta:

```bash
okf-wiki code-understand --project "$(pwd)" --since <last_commit_synced> --pretty
```

(First sync: omit `--since`. An explicit `--backend` flag overrides `CODE_UNDERSTANDING_BACKEND` for that run.)

#### What to do with the focus-map output

1. **Read the output selectively** — when `backend: codegraph`, treat focus-map entries as structural facts with `file:line` citations; when `backend: builtin`, treat `defines`/`imports` entries as facts but treat `rg-reference` entries as weaker evidence — open the file and verify before citing. Open only the ranked `files`/`file:lines` the focus map points at; never paste the JSON into the bundle.
2. **Cite the evidence** — every architectural claim written to a page references its evidence as `(file:lines)` from the focus map or from the opened source; keep using the existing provenance markers.
3. **Prune stale relationships (required)** — when updating an existing `projects/<name>/` page, cross-check each previously recorded code relationship against the current focus map (or `okf-wiki ast-extract` for a symbol-level recheck). Remove relationships whose target symbol no longer exists or is no longer reachable; update the page and record the removals in `log.md`. This keeps false positives from accumulating.
4. **Never write `.codegraph/` into the bundle.** The project's `.codegraph/` directory is a machine-generated CodeGraph index — a disposable cache/sidecar in the project repo (git-ignored), outside bundle scope. It is an *input* to distillation only: the sources behind it get scanned and distilled, and the index itself never lands in `$OKF_BUNDLE_PATH` — as a page, an attachment, a manifest entry, or anything else. The same rule covers the `code-understand` JSON output.
5. **Offer CodeGraph when it's missing (optional)** — if the output reports `backend: builtin` because codegraph is unavailable and the user wants the enhanced backend, offer to install it for them: `npm install -g @colbymchenry/codegraph` (or set `CODE_UNDERSTANDING_CODEGRAPH_BIN` to an existing binary), then re-run this step so the focus map uses the graph. Never install without the user's go-ahead, and never let a missing codegraph block the sync.

If `okf-wiki` is not installed or the command fails, skip this step and proceed to Step 4 as normal — it is an optimisation, not a requirement.

## Step 4: Distill into Bundle Pages

### Project-specific knowledge

Goes under `$OKF_BUNDLE_PATH/projects/<project-name>/`:

```
projects/<project-name>/
├── <project-name>.md          ← project overview (named after the project, NEVER _project.md)
├── concepts/                  ← project-specific ideas, architectures
├── skills/                    ← project-specific how-tos, patterns
└── references/                ← project-specific source summaries
```

**Naming rule:** the overview page is `<project-name>.md`. A leading `_` (`_project.md`) would place the file outside OKF conformance scope (the out-of-scope convention reserves `_`-prefixed names for operational artifacts) and give every project a `_project` concept ID — both wrong. See *Projects* in `okf-wiki/SKILL.md`.

The overview page (`<project-name>.md`) should have:
- What the project is (one paragraph)
- Key concepts and how they connect
- File-relative links to project-specific and global bundle pages

### Global knowledge

Things that aren't project-specific go in the global categories:

| What you found | Where it goes |
|---|---|
| A general concept learned | `concepts/` |
| A reusable pattern or technique | `skills/` |
| A tool/service/person | `entities/` |
| Cross-project analysis | `synthesis/` |

### Page format

Every page needs OKF v0.2 YAML frontmatter. The canonical mapping and full field reference live in `okf-wiki/SKILL.md` → *Canonical Frontmatter (Schema)* — this skill redefines nothing; write against it:

```markdown
---
type: Concept                      # TitleCase of the category dir: Concept|Entity|Skill|Reference|Synthesis
title: >-
    Page Title
description: >-
    One or two sentences (≤200 chars) describing what this page covers.
tags: [tag1, tag2]
generated:
  by: claude/2.5.0                 # acting agent <producer>/<version>; fallback okf-wiki/<version>
  at: TIMESTAMP
status: draft                      # agents always write draft — see the lifecycle invariant below
stale_after: TIMESTAMP             # = updated + 90d, recomputed on every write
sources:
  - resource: "/absolute/path/to/project"   # scope descriptor: the synced project (resource is mandatory)
# ===== OKF §4.1 extension fields (any conformant consumer preserves them) =====
updated: TIMESTAMP
provenance:
  extracted: 0.6
  inferred: 0.35
  ambiguous: 0.05
base_confidence: 0.59              # wiki-update default
---

Use folded scalar syntax (description: >-) for title and description to keep frontmatter parser-safe across punctuation (:, #, quotes) without escaping rules.
Keep the title and description contents indented by two spaces under description: >-.

# Page Title

- A fact the codebase or a doc actually states.
- A reason the design works this way. ^[inferred]

Use file-relative markdown links to connect to other pages.
```

**Write a `description:` frontmatter field** on every new/updated page (1–2 sentences, ≤200 chars), using `>-` folded style. For project sync, a good description answers "what does this page tell me about the project I wouldn't guess from its title?" This field powers cheap retrieval by `wiki-query`.

**Apply provenance markers** per `okf-wiki/SKILL.md` (Provenance Markers section). For project sync specifically:

- **Extracted** — anything visible in the code, config, or a doc/commit message: file structure, dependencies, function signatures, what a file does.
- **Inferred** — *why* a decision was made, design rationale, trade-offs, "the team chose X because Y" — unless a commit message, doc, or ADR states it explicitly.
- **Ambiguous** — when the code and docs disagree, or when there's clearly an in-progress migration with two patterns living side by side.

Compute the rough fractions and write the `provenance:` block on every new/updated page.

**Lifecycle invariant:** pages written by this skill are always `status: draft`. The `draft → stable` transition and any `verified:` entry are performed only by a `human:<id>` actor — see *Human-only lifecycle invariant* in `okf-wiki/SKILL.md`.

### Updating vs creating

- If a page already exists in the bundle, **merge** new information into it. Don't create duplicates.
- If you're adding to an existing page, update the `updated` timestamp (and recompute `stale_after`), add the new source, and set `generated` to the current acting agent.
- Check `index.md` to see what's already there before creating anything new.

## Step 5: Cross-link

After creating/updating pages:

- Add file-relative markdown links from new pages to existing related pages (compute the path from the current file's directory, using `..` to climb as needed; always include the `.md` extension)
- Add links from existing pages back to the new ones where relevant
- Link the project overview to all project-specific pages and relevant global pages

File-relative links render in GitHub, in Obsidian (as an optional viewer), and in any static site generator.

## Step 6: Update Tracking

### Update `.manifest.json`

Update the top-level `last_commit_synced` and this project's entry:

```json
{
  "last_commit_synced": "abc123f",
  "projects": {
    "<project-name>": {
      "source_cwd": "/absolute/path/to/project",
      "last_synced": "TIMESTAMP",
      "pages_in_bundle": ["projects/<project-name>/<project-name>.md", "..."]
    }
  }
}
```

`last_commit_synced` is the git SHA this skill last synced into the bundle — top level, canonical (see `wiki-status`). `source_cwd` is an absolute expanded path. Only update `last_commit_synced` **after** the pages have been written successfully.

### Update `index.md`

Add entries for any new pages created — the root `index.md` and the `index.md` of every category directory that gained pages.

### Update `log.md`

Append (newest-first under today's ISO-date heading):
```
- [TIMESTAMP] WIKI_UPDATE project=<project-name> pages_updated=X pages_created=Y source_cwd=/path/to/project
```

### Update `_cache/hot.md`

Read `$OKF_BUNDLE_PATH/_cache/hot.md` (create from the template in `wiki-ingest` if missing). Rewrite **Recent Activity** with what was just synced — last 3 operations max. Update **Active Threads** if this project is an ongoing focus. Update **Key Takeaways** with the most important architectural insight or decision surfaced during this sync. Update `updated` timestamp.

Write conceptually: "Synced my-api — added the rate-limiter concept and the retry-backoff skill; core insight is the token-bucket choice over a fixed-window counter."

## Step 7: Refresh QMD Wiki Index (optional — requires `QMD_WIKI_COLLECTION`)

**GUARD: If `$QMD_WIKI_COLLECTION` is empty or unset, skip this step.** The markdown bundle is the source of truth; QMD is only a search index.

Run this step only after pages, `.manifest.json`, `index.md`, `log.md`, and `_cache/hot.md` have been written. If Step 2 found no meaningful changes and the sync stopped early, do not refresh QMD.

This refresh currently requires the local QMD CLI. Use `$QMD_CLI` if set; otherwise use `qmd`. If the CLI is unavailable or returns an error, do not roll back the bundle update; report that the bundle was updated but QMD refresh was skipped or failed.

For CLI refresh:

```bash
${QMD_CLI:-qmd} update
```

If the output says new hashes need vectors, or if pages were created/updated and embeddings may be stale, run:

```bash
${QMD_CLI:-qmd} embed
```

Verify at least one created or materially updated page is visible in the wiki collection:

```bash
${QMD_CLI:-qmd} get "qmd://$QMD_WIKI_COLLECTION/projects/<project-name>/<page>.md" -l 5
```

If the exact `qmd://` path is uncertain, use:

```bash
${QMD_CLI:-qmd} ls "$QMD_WIKI_COLLECTION" | rg "<project-name>"
```

Record QMD refresh in the final report as one of:
- `QMD refreshed: update + embed + verified`
- `QMD skipped: QMD_WIKI_COLLECTION unset`
- `QMD skipped: qmd CLI unavailable`
- `QMD failed: <short error summary>`

## Tips

- **Be aggressive about merging.** If the project uses React Server Components, don't create a new page if `concepts/react-server-components.md` already exists. Update the existing one and add this project as a source.
- **Consult the tag taxonomy.** Read `$OKF_BUNDLE_PATH/_meta/taxonomy.md` if it exists, and use canonical tags.
- **Don't copy code.** Distill the *knowledge*, not the implementation. "This project uses a debounced search pattern with 300ms delay" is useful. Pasting the actual debounce function is not.
- **Project overview is the anchor.** The `<project-name>.md` file is what you'd read to get oriented. Make it good.

---

Derived from Ar9av/obsidian-wiki wiki-update skill (MIT).
