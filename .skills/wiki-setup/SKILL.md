---
name: wiki-setup
description: >
  Initialize a new OKF v0.2 bundle with the correct structure, reserved files, and configuration,
  or attach to an existing bundle. Use this skill when the user wants to set up a new knowledge
  base from scratch, initialize the bundle structure, create the .env file, or says things like
  "set up my bundle", "initialize my wiki", "create a new bundle", "get started with okf-wiki".
  Also use when the user needs to reconfigure their existing bundle or fix a broken setup.
---

# Bundle Setup — OKF v0.2 Bundle Initialization

You are setting up a new OKF v0.2 bundle (or attaching to an existing one). The bundle is the
compiled knowledge store: a directory of markdown files that is conformant with OKF v0.2 from the
first moment, with trust and provenance as first-class fields of the format. It is portable by
design — any agent and any human can read, extend, and transfer it between tools without
conversion (format, not platform). Read `.skills/okf-wiki/SKILL.md` for the canonical architecture,
the frontmatter mapping, and the reserved-file formats — this skill references them rather than
duplicating them.

## Step 0: Choose the Mode

There are two modes:

- **Fresh bundle** — the target path doesn't exist yet (or exists but is empty). Continue with
  Steps 1–3, then verify with Step 6.
- **Attach to an existing bundle** — the target path already contains a knowledge base. Resolve
  config (Step 1), then run the attach checks below instead of creating structure:

  1. **Is this an OKF v0.2 bundle?** Look for a root `index.md` whose frontmatter declares
     `okf_version: "0.2"`.
     - **Yes** — the bundle is already OKF-native. Skip Steps 2–3; run the verification checklist
       (Step 6) to fill in anything missing, and tell the user the bundle is ready.
     - **No** — no root `index.md`, or one without an `okf_version` declaration. If it looks like
       a legacy obsidian-wiki vault (Obsidian-flavored frontmatter, wikilinks, `.obsidian/`),
       do **not** create OKF files on top of it. Suggest migration via
       `scripts/migrate-vault.sh`, which converts wikilinks to file-relative links, upgrades
       v0.1 frontmatter to v0.2, and carries `.manifest.json`/index/log over. The migrator is
       part of Phase 3 and arrives with it — treat `scripts/migrate-vault.sh` as a forward
       reference for now. If the user declines migration, offer a fresh bundle at a different
       path. If the directory is an unrelated folder (not an obsidian-wiki vault either), stop
       and ask the user where the bundle should live.

## Step 1: Create .env

If `.env` doesn't exist (or doesn't contain `OKF_BUNDLE_PATH`), create it from `.env.example`.
Interview the user for:

1. **Where should the bundle live?** → `OKF_BUNDLE_PATH`
   - Default: `~/Documents/okf-wiki-bundle`
   - Must be an absolute path (after expansion)
   - **Legacy alias:** if the config sets `OBSIDIAN_VAULT_PATH` but no `OKF_BUNDLE_PATH`, read it
     as the bundle path, warn that `OBSIDIAN_VAULT_PATH` is deprecated, and rename it to
     `OKF_BUNDLE_PATH` in the config.

2. **Where are your source documents?** → `OKF_SOURCES_DIR`
   - Can be multiple paths, comma-separated
   - Default: `~/Documents`
   - Local git repo clones (public or private, any host) can be listed here too — clone
     the repo locally first, then add its path. See "Ingesting Git Repositories" in
     `wiki-ingest/SKILL.md` for how repo sources are handled.

3. **Which categories?** → `OKF_CATEGORIES`
   - Default: `concepts,entities,skills,references,synthesis,journal` (`projects/` always exists)
   - Each category directory is created in the bundle and maps to a Title-case `type` per the
     canonical mapping in `.skills/okf-wiki/SKILL.md` (§ Schema).

4. **Raw inbox directory?** → `OKF_RAW_DIR`
   - Default: `_raw` — scratch inbox for quick captures and drafts awaiting promotion.

5. **Per-ingest page cap?** → `OKF_MAX_PAGES_PER_INGEST`
   - Default: `15` — max pages created/updated per `wiki-ingest` run.

6. **Strict trust checks?** → `OKF_TRUST_STRICT`
   - Default: unset (`false`). See *Trust and Lifecycle* in `.skills/okf-wiki/SKILL.md` for what
     strict mode enforces.

7. **Owner schema overrides?** → `OKF_ALLOWED_LIFECYCLES`, `OKF_ALLOWED_RELATIONSHIP_TYPES`,
   `OKF_REQUIRED_TRUST_FIELDS`, `OKF_SCHEMA_SOURCE`
   - All default to unset — framework defaults from the core skill apply. Set only when the
     bundle owner wants to extend or restrict the lifecycle vocabulary, relationship allowlist,
     required trust fields, or schema source.

8. **Want to import Claude history?** → `CLAUDE_HISTORY_PATH`
   - Default: auto-discovers from `~/.claude`
   - Set explicitly if Claude data is elsewhere

9. **Have QMD installed?** → `QMD_WIKI_COLLECTION` / `QMD_PAPERS_COLLECTION` / `QMD_TRANSPORT`
   - Optional. Enables semantic search in `wiki-query` and source discovery in `wiki-ingest`.
   - Default to `QMD_TRANSPORT=mcp` unless the user wants the agent to call the local `qmd` CLI directly.
   - If using CLI mode, set `QMD_CLI_SEARCH_MODE=quality` by default; suggest `balanced` if reranking is too slow.
   - If unsure, skip for now — both skills fall back to `Grep` automatically.
   - Install instructions: see `.env.example` (QMD section).
   - **If `QMD_WIKI_COLLECTION` is set, verify the collection excludes `_raw/`.** The wiki
     collection and papers collection must stay disjoint — `wiki-query` cites them as
     separate layers (compiled knowledge vs. raw staging), and `OKF_BUNDLE_PATH` contains
     `_raw/`, so a plain `qmd collection add <bundle>` silently merges the two.
     Read `~/.config/qmd/index.yml`, find the entry for `$QMD_WIKI_COLLECTION`, and check its
     `ignore` list includes `_raw/**` (and ideally `log.md`, which has no semantic value). If
     the collection doesn't exist yet, create it (`qmd collection add "$OKF_BUNDLE_PATH"
     --name <collection-name>`), then add the `ignore` block to `index.yml` by hand — `qmd`
     has no `--ignore` flag and refuses a second `collection add` on a path that already has
     one, so editing the YAML is the only way to scope it. Run `qmd update` after editing.
     If the collection already exists without the `ignore` block, tell the user their
     wiki collection is indexing `_raw/` (including drafts left behind by `wiki-ingest`)
     and offer to add the `ignore` block and re-run `qmd update`.

10. **Token budget warning threshold?** → `WIKI_TOKEN_WARN_THRESHOLD`
    - Default: `100000` (warn when full-bundle read would cost > 100K tokens)
    - Set to `0` to disable the warning entirely
    - `wiki-status` shows a token footprint table and emits this warning automatically

11. **Enable staged writes?** → `WIKI_STAGED_WRITES`
    - Default: unset / `false` (pages written directly to their final location)
    - Set to `true` for team bundles, high-stakes domains, or any bundle where the human wants
      final say on every agent-written page
    - When enabled: all new/updated pages land in `_staging/` first; run `/wiki-stage-commit` to
      review and promote them
    - `wiki-status` shows a "Staged writes pending" count when files are waiting

After resolving config, assign the global config directory with the exact
`okf_wiki_config_dir` algorithm from the Config Resolution Protocol in
`.skills/okf-wiki/SKILL.md` — XDG-style `$XDG_CONFIG_HOME/okf-wiki` for new installs. Create the
shared writing profile only when it does not already exist. Preserve an existing
`$GLOBAL_CONFIG_DIR/WRITING.md`; never overwrite it and do not ask additional writing-style
questions.

Use `OKF_WIKI_REPO` when it was loaded from config. When it is absent, derive the
absolute repository/data root from this loaded skill's absolute path, distinguishing the
packaged `<root>/skills/wiki-setup/SKILL.md` layout from the source
`<root>/.skills/wiki-setup/SKILL.md` layout. Then check both canonical template layouts:

- Packaged install: `<root>/skills/okf-wiki/references/WRITING.md`
- Source checkout: `<root>/.skills/okf-wiki/references/WRITING.md`

```bash
GLOBAL_CONFIG_DIR="$(okf_wiki_config_dir)"
mkdir -p "$GLOBAL_CONFIG_DIR"

SKILL_FILE="<absolute path of this loaded wiki-setup/SKILL.md>"
SKILL_DIR="$(cd "$(dirname "$SKILL_FILE")" && pwd)"
if [ -n "${OKF_WIKI_REPO:-}" ]; then
  WIKI_ROOT="${OKF_WIKI_REPO%/}"
else
  case "$SKILL_DIR" in
    */.skills/wiki-setup) WIKI_ROOT="${SKILL_DIR%/.skills/wiki-setup}" ;;
    */skills/wiki-setup) WIKI_ROOT="${SKILL_DIR%/skills/wiki-setup}" ;;
    *) echo "Cannot derive writing-profile template root from $SKILL_DIR" >&2; exit 1 ;;
  esac
fi

WRITING_TEMPLATE=""
for candidate in \
  "$WIKI_ROOT/skills/okf-wiki/references/WRITING.md" \
  "$WIKI_ROOT/.skills/okf-wiki/references/WRITING.md"
do
  if [ -f "$candidate" ]; then
    WRITING_TEMPLATE="$candidate"
    break
  fi
done

WRITING_PROFILE="$GLOBAL_CONFIG_DIR/WRITING.md"
if [ -n "$WRITING_TEMPLATE" ] && [ ! -e "$WRITING_PROFILE" ]; then
  cp "$WRITING_TEMPLATE" "$WRITING_PROFILE"
elif [ -z "$WRITING_TEMPLATE" ]; then
  echo "Note: no WRITING.md template found under $WIKI_ROOT — continuing with framework default writing guidance."
fi
```

A missing or empty `$GLOBAL_CONFIG_DIR/WRITING.md` means there are no custom writing
preferences — the framework default guidance applies (see *Writing Profile Resolution* in
`.skills/okf-wiki/SKILL.md` for precedence).

## Step 2: Create Bundle Directory Structure

```bash
mkdir -p "$OKF_BUNDLE_PATH"/{concepts,entities,skills,references,synthesis,journal,projects,_archives,_raw,_staging,_readouts,_meta,_cache}
```

- `concepts/ entities/ skills/ references/ synthesis/ journal/` — the six default knowledge
  categories (plus `projects/`); each maps to a Title-case `type`.
- `projects/` — Per-project knowledge (populated during ingest).
- `_archives/` — Stores bundle snapshots for rebuild/restore operations.
- `_raw/` — Staging area for unprocessed drafts. Drop rough notes here; `wiki-ingest` will
  promote them to proper bundle pages and move the originals into `_raw/_archived/` (created on
  first use).
- `_staging/` — Review queue for agent-written pages when `WIKI_STAGED_WRITES=true`. Pages here
  are not part of the compiled bundle until promoted via `/wiki-stage-commit`.
- `_readouts/` — Compiled briefings from `wiki-narrate`.
- `_meta/` — Bundle-level metadata (the tag taxonomy lives here).
- `_cache/` — Operational caches (`hot.md` lives here).

All `_`-prefixed directories are **out of OKF conformance scope** — excluded from validation
(see *Out-of-Scope Convention* in `.skills/okf-wiki/SKILL.md`).

Create the seven per-directory `index.md` files for progressive disclosure (one per category
directory; no frontmatter):

```markdown
# Concepts

*No pages yet — run `wiki-ingest` to add your first source.*
```

Use each directory's own name as the heading (`# Entities`, `# Skills`, `# References`,
`# Synthesis`, `# Journal`, `# Projects`).

## Step 3: Create Reserved Files

### index.md (bundle root)

The master catalog — the **only** `index.md` permitted to carry frontmatter, and it MUST declare
the spec version:

```markdown
---
okf_version: "0.2"
---

# <Bundle Name>

- [Concepts](./concepts/index.md)
- [Entities](./entities/index.md)
- [Skills](./skills/index.md)
- [References](./references/index.md)
- [Synthesis](./synthesis/index.md)
- [Journal](./journal/index.md)
- [Projects](./projects/index.md)
```

Rebuild this after every ingest operation.

### log.md

Chronological append-only record, newest-first under ISO-date headings (format per
`.skills/okf-wiki/SKILL.md` § *log.md*):

```markdown
# Log

## 2026-08-30
- INIT bundle_path="OKF_BUNDLE_PATH" categories=concepts,entities,skills,references,synthesis,journal,projects
```

### _cache/hot.md

The ~500-word semantic snapshot of recent activity. Every write skill updates it so the next
session can pick up where the last one left off without crawling the whole bundle:

```markdown
# Hot Cache

*A ~500-word semantic snapshot of recent activity. Updated after every major write operation.*

## Recent Activity

- [TIMESTAMP] INIT — bundle created at OKF_BUNDLE_PATH

## Active Threads

*None yet — start ingesting sources to populate.*

## Key Takeaways

*None yet.*

## Flagged Contradictions

*None yet.*
```

### _meta/taxonomy.md

Seed the controlled tag vocabulary (`tag-taxonomy` maintains this file; agents read it before
tagging any page):

```markdown
# Tag Taxonomy

Canonical tag vocabulary for this bundle. Read this file before tagging any page.

## Rules

- Max 5 tags per page (system `visibility/*` tags don't count)
- Lowercase, hyphenated
- Prefer broad over narrow

## Canonical Tags

*None yet — add tags as the bundle grows.*

## Aliases

| Alias | Canonical |
|---|---|
| *(none yet)* | |

## System Tags (reserved)

| Tag | Purpose |
|---|---|
| `visibility/public` | Explicitly public — shown in all modes (same as no tag) |
| `visibility/internal` | Team-only — excluded in filtered query/export mode |
| `visibility/pii` | Sensitive data — excluded in filtered query/export mode |
```

### .manifest.json

Create an empty manifest so ingest skills have a tracking file to append to and
`wiki-status` reports the bundle as complete (it treats `.manifest.json` as a required core
file). It is the delta ledger keyed by canonical source paths (absolute, with `~` and env vars
expanded):

```bash
printf '{}\n' > "$OKF_BUNDLE_PATH/.manifest.json"
```

See `.skills/okf-wiki/SKILL.md` (§ `.manifest.json`) for the canonical-source-key rule and the
`wiki-status` skill for the full schema.

### okf-base.yaml

The okflint profile — documents the extension fields this bundle uses on top of OKF v0.2 core
fields, and the out-of-scope zones. `wiki-lint` hands this to okflint when it is available:

```yaml
# okf-wiki bundle profile for okflint. Documents the extension fields this
# bundle uses on top of OKF v0.2 core fields (spec §4.1 — consumers must
# preserve unknown keys verbatim).
okf_version: "0.2"
extensions:
  fields: [updated, aliases, relationships, provenance, base_confidence, tier, lifecycle_changed, superseded_by, lifecycle]
  reserved_dirs: [_raw, _staging, _archives, _readouts, _meta, _cache]
  reserved_files: [_insights.md, .manifest.json, .manifest.lock]
```

`_insights.md` and `.manifest.lock` are reserved by this profile but created on first use by
`wiki-status` and the ingest skills — setup leaves them out.

## Step 4: Optional — Obsidian as a Viewer

The bundle is portable by design and needs no particular editor. Obsidian remains a fine
optional viewer for browsing and graph exploration; the source of truth stays the bundle's
markdown. If the owner plans to open the bundle in Obsidian, create a minimal `.obsidian/`
config for a good out-of-box experience. It is out of OKF scope, platform-specific, and should
be git-ignored:

### .obsidian/app.json
```json
{
  "strictLineBreaks": false,
  "showFrontmatter": false,
  "defaultViewMode": "preview",
  "livePreview": true
}
```

### .obsidian/appearance.json
```json
{
  "baseFontSize": 16
}
```

## Step 5: Optional — Obsidian Viewer Plugins

If the user opens the bundle in Obsidian, tell them about these recommended community plugins
(they install manually). They are viewer-side conveniences — the bundle's knowledge graph is
maintained by the skills themselves (`cross-linker` inserts typed links; the graph survives
without any plugin):

1. **Dataview** — Query page metadata, create dynamic tables. Essential for a wiki-style view.
2. **Graph Analysis** — Enhanced graph view for exploring connections.
3. **Templater** — If they want to create pages manually using templates.
4. **Obsidian Git** — Auto-backup the bundle to a git repo (see the GitHub Sync section below
   for the framework's own recommended flow).

## Step 6: Verify Setup

Run a quick sanity check:
- [ ] Bundle directory exists with: `concepts/`, `entities/`, `skills/`, `references/`, `synthesis/`, `journal/`, `projects/`, `_archives/`, `_raw/`, `_staging/`, `_readouts/`, `_meta/`, `_cache/`
- [ ] `index.md` exists at the bundle root and declares `okf_version: "0.2"`
- [ ] Per-directory `index.md` exists in each of the seven category directories
- [ ] `log.md` exists at the bundle root (newest-first ISO format)
- [ ] `_cache/hot.md` exists
- [ ] `_meta/taxonomy.md` exists
- [ ] `.manifest.json` exists at the bundle root (empty `{}` is fine)
- [ ] `okf-base.yaml` exists at the bundle root
- [ ] `.env` has `OKF_BUNDLE_PATH` set
- [ ] `_staging/` directory exists (required even when `WIKI_STAGED_WRITES` is not set — created on setup for future use)
- [ ] `WRITING_PROFILE` exists at the resolved global config directory (or was intentionally skipped)
- [ ] Source directories (if configured) exist and are readable

Report the results, including the resolved absolute `WRITING_PROFILE` path, and tell the user
they can now:
1. Open the bundle in Obsidian as an optional viewer (File → Open Vault → select the directory)
2. Run `wiki-status` to see what's available to ingest
3. Run `wiki-ingest` to add their first sources
4. Run `claude-history-ingest` to mine their Claude conversations
5. Run `codex-history-ingest` to mine their Codex sessions (if they use Codex)
6. Run `wiki-status` again anytime to check the delta

## Optional: Install the Stop Hook (Auto-Capture)

Ask the user: **"Want to auto-capture findings at session end?"**

If yes, install the Stop hook into their global Claude Code settings so that every session
with meaningful work automatically prompts `/wiki-capture --quick` before closing.

**What the hook does:** reads the session transcript on Stop, counts file edits and shell
calls, and if significant work happened, asks Claude to run `/wiki-capture --quick` once.
The `wiki-capture` quick-mode KEEP/SKIP gate prevents noise — routine or
inconclusive sessions are skipped automatically.

**Installation steps:**

1. Find the okf-wiki repo path. If `OKF_WIKI_REPO` is set in config, use that.
   Otherwise, check common locations: `~/Documents/projects/okf-wiki`, `~/okf-wiki`,
   or ask the user.

2. Locate the `okf-wiki-stop-capture.sh` script. Its path differs between a packaged install
   and a source checkout, so check both layouts under `<REPO_PATH>` and use the first that
   exists:

   - `<REPO_PATH>/hooks/okf-wiki-stop-capture.sh` — packaged install (`OKF_WIKI_REPO`
     points at the bundled data dir, which ships the hook under `hooks/`).
   - `<REPO_PATH>/.claude/hooks/okf-wiki-stop-capture.sh` — source checkout.

   If neither exists, fetch the canonical copy to a stable location and point at that instead.
   Use the global config dir from the Config Resolution Protocol in `okf-wiki/SKILL.md`
   (XDG-style `$XDG_CONFIG_HOME/okf-wiki`):

   ```bash
   CONFIG_DIR="$(okf_wiki_config_dir)"
   mkdir -p "$CONFIG_DIR/hooks"
   # Copy the framework's own copy of the hook (it ships at .claude/hooks/ in the repo):
   cp "<REPO_PATH>/.claude/hooks/okf-wiki-stop-capture.sh" "$CONFIG_DIR/hooks/okf-wiki-stop-capture.sh"
   chmod +x "$CONFIG_DIR/hooks/okf-wiki-stop-capture.sh"
   ```

   Use the resolved absolute path as `<HOOK_PATH>` below.

3. Merge the hook entry into `~/.claude/settings.json`:

```json
{
  "hooks": {
    "Stop": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "bash <HOOK_PATH>"
          }
        ]
      }
    ]
  }
}
```

   If `~/.claude/settings.json` already exists and has a `hooks.Stop` array, **append** the new
   entry rather than replacing — don't clobber existing hooks.

   > **Note — expect a duplicate nudge inside this repo.** The okf-wiki repo ships its own
   > git-tracked `.claude/settings.json` registering the same Stop hook at a relative path.
   > Claude Code *merges* project-level and user-level hook config rather than letting one
   > override the other, so sessions ending inside the repo itself fire both registrations. This
   > is expected and harmless — the hook claims an atomic per-session sentinel, so only one nudge
   > is emitted. Leave both in place: removing the project entry dirties a tracked framework file
   > and disables capture for anyone who clones the repo without doing the global install.

4. Confirm: "Stop hook installed. Claude Code will prompt `/wiki-capture --quick` at the
   end of any session where you write files or run ≥ 4 shell commands."

**To uninstall later:** remove the hook entry from `~/.claude/settings.json`.

## Optional: Configure GitHub Sync

Ask the user: **"Want to sync your bundle to a private GitHub repo?"**

The bundle is plain markdown, so pushing it to git gets you version history, backup, and
cross-device sync for free. A git repo is also the OKF-recommended unit of distribution.
This is opt-in — skip it if the user declines or has no repo ready.

If yes:

1. Ask for the repo URL (e.g. `https://github.com/you/my-bundle.git`). Recommend it be
   **private** if the bundle holds personal notes.
2. Run the following steps directly (the agent is the runtime — there is no CLI to invoke):
   ```bash
   cd "$OKF_BUNDLE_PATH"
   git init -q                       # if not already a repo
   # Create .gitignore if absent (never edit an existing one — it's the user's file):
   printf '%s\n' \
     ".obsidian/workspace.json" ".obsidian/workspace-mobile.json" ".obsidian/cache" \
     ".trash/" ".DS_Store" > .gitignore
   git remote add origin "<repo-url>"   # or: git remote set-url origin ... if origin exists
   ```
3. Tell the user they can run `git add -A && git commit -m "…" && git push` any time afterward
   to commit and push pending bundle changes (stages everything, commits with a timestamp,
   pushes). There's no config file to check for sync status — the bundle's own `git remote`
   is the source of truth.

## Optional: Refresh QMD After Setup

If `QMD_WIKI_COLLECTION` is configured and the local QMD CLI is available, run `qmd update` after
the initial bundle files exist so the fresh bundle is immediately queryable. No embedding pass is
usually needed at setup time because the bundle starts empty, so a plain update is enough unless
you have already populated pages. Before running it, confirm the `_raw/` exclusion described in
Step 1.9 is in place — otherwise this update indexes the (currently empty) staging directory into
the wiki collection too, and every future draft dropped there joins it silently.

---

Derived from Ar9av/obsidian-wiki wiki-setup skill (MIT).
