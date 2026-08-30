---
name: wiki-stage-commit
description: >
  Review and promote staged bundle pages to their final locations. Use when WIKI_STAGED_WRITES=true
  and the user says "/wiki-stage-commit", "review staged pages", "commit staged writes",
  "promote staged pages", "approve staged changes", or "what's waiting in staging".
  Shows each staged file, lets the user accept or reject it, and moves accepted files to
  their final bundle locations. Rejected files are deleted from _staging/ with a log note —
  no residue.
---

# Wiki Stage Commit — Staged Write Promotion

You are reviewing agent-written pages that are waiting in `_staging/` for human approval before they land in the live bundle. This skill is only useful when `WIKI_STAGED_WRITES=true` in the bundle config.

The staged-writes cycle: with `WIKI_STAGED_WRITES` enabled, write skills (ingest, capture, dedup, …) place new and updated pages in `_staging/` instead of the live bundle. `_staging/` is an **out-of-scope operational directory** (see *Out-of-Scope Convention* in `okf-wiki/SKILL.md`) — staged candidates are exempt from OKF conformance and skipped by validation. Promotion is the only moment an agent-written page becomes visible and conformant. Agents always stage pages with `status: draft`; the draft → stable transition and any `verified:` entry are human-only, and agent-side deprecation is staged as `superseded_by` for human sign-off during this review.

## Before You Start

1. **Resolve config** — follow the Config Resolution Protocol in `okf-wiki/SKILL.md` (inline `@name` override → walk up CWD for `.env` → global config → prompt setup). This gives `OKF_BUNDLE_PATH` and `WIKI_STAGED_WRITES`. Then read `$OKF_BUNDLE_PATH/AGENTS.md` if it exists — owner conventions override framework defaults.
2. If `WIKI_STAGED_WRITES` is not set or is `false`, tell the user: "Staged writes mode is not enabled. Set `WIKI_STAGED_WRITES=true` in your `.env` to use this feature." Then stop.
3. Read the `_staging/` directory inventory.

## Invocation Forms

```
/wiki-stage-commit               # interactive review: show each file and ask accept/reject
/wiki-stage-commit --all         # accept all staged files without per-file review
/wiki-stage-commit --reject-all  # reject all staged files (delete from _staging/, log each)
/wiki-stage-commit --list        # list staged files with summary, no changes
```

## Step 1: Inventory Staged Files

Glob `$OKF_BUNDLE_PATH/_staging/**/*.md` — these are the pending pages.

Also glob `$OKF_BUNDLE_PATH/_staging/**/*.patch.md` — these are pending *updates* to existing pages (diff-style files showing proposed additions and deletions; format defined in `wiki-ingest/SKILL.md`).

Report the inventory:

```
Staged files: 4 new pages, 2 updates

New pages:
  _staging/concepts/attention-mechanism.md         (staged 2 days ago)
  _staging/entities/andrej-karpathy.md             (staged 2 days ago)
  _staging/skills/fine-tuning-llms.md              (staged yesterday)
  _staging/references/attention-is-all-you-need.md (staged 3 hours ago)

Updates (patch files):
  _staging/concepts/transformer-architecture.patch.md  (target: concepts/transformer-architecture.md)
  _staging/skills/prompt-engineering.patch.md          (target: skills/prompt-engineering.md)
```

If `_staging/` is empty, report: "Nothing staged. All writes have been committed or no staged writes have been produced yet."

## Step 2: Per-File Review (interactive mode)

For each staged file (new pages first, then updates):

### For new pages:

Display a summary:

```
--- New page: concepts/attention-mechanism.md ---
Title:          Attention Mechanism
Tags:           #ml #architecture
Description:    Core building block of transformers — computes weighted sum of values based on query-key similarity.
Status:         draft
Tier:           supporting
Base confidence: 0.72
Sources:        papers/attention.pdf

[Preview first 20 lines of body]
...

Accept [a], Reject [r], Skip [s], Preview full [p]?
```

### For patch files:

Display a structured diff:

```
--- Update: concepts/transformer-architecture.md ---
Source: _staging/concepts/transformer-architecture.patch.md

Proposed additions (+):
+ Transformers outperform RNNs on tasks requiring long-range dependencies. ^[inferred]
+ New source: papers/survey-2026.pdf

Proposed deletions (-):
- The attention mechanism was first described in [Bahdanau 2015].  (to be replaced by updated claim)

⚠️  Conflict check: target page was modified 3 days after staging. Review carefully.

Accept [a], Reject [r], Skip [s], Preview full diff [p]?
```

**Lifecycle changes in patches.** If a patch proposes a lifecycle change, surface it above the diff so the human knows what they are signing off:

- `superseded_by` / `status: deprecated` (agent-side deprecation, e.g. staged by `wiki-dedup` during a merge): show which page supersedes which. Human acceptance here **is** the sign-off — apply it only after an explicit accept.
- `status: stable` or a new `verified:` entry: **illegal transition** — an agent can never stage these. Block the patch, report `illegal_lifecycle_transition`, and offer to apply the patch with the lifecycle change stripped out.

If `--all` flag is set, skip prompting and accept every file — except patches blocked for `illegal_lifecycle_transition`, which still require per-file review.
If `--reject-all` flag is set, skip prompting and reject every file.
If `--list` flag is set, stop after printing the inventory (Step 1).

## Step 3: Apply Decisions

### Accepting a new page

1. Move `_staging/<category>/page.md` → `<category>/page.md` (the final location; `<category>` is the lowercase directory matching the page's TitleCase `type` per the canonical mapping in `okf-wiki/SKILL.md` §Schema)
2. Update the per-directory `index.md` with the new page entry (file-relative link + `description`)
3. Rebuild the root `index.md` master catalog (it must still declare `okf_version: "0.2"`)
4. Update `.manifest.json`: add the page path to the `pages_created` list of the source entry that produced it (identified via the page's `sources`); if no source entry matches, note that in the report and skip
5. Remove the staged file

The promoted page keeps `status: draft` — promotion changes location and visibility, never lifecycle. The draft → stable transition and any `verified:` entry remain human-only (see *Human-only lifecycle invariant* in `okf-wiki/SKILL.md` §Schema).

### Accepting a patch/update

1. Read the current page at the target path
2. Apply the proposed additions and deletions (merge, don't just overwrite)
3. If the patch was a signed-off deprecation: set `status: deprecated` plus the `superseded_by` extension field (file-relative path) on the target
4. Update the `updated` extension-field timestamp and recompute `stale_after` (= `updated` + 90d)
5. Update the per-directory `index.md` and root `index.md` if the `description` changed
6. Update `.manifest.json`: add the target path to the `pages_updated` list of the patch's source entry
7. Remove the staged patch file

### Rejecting a file

Delete it from `_staging/` — a rejected page must leave no residue:

- `_staging/concepts/page.md` → deleted
- `_staging/concepts/page.patch.md` → deleted (the live target page is untouched)

Append one log line per rejection (Step 4) recording what was discarded and why, so the decision stays auditable after the file is gone. If the user explicitly asks to keep a rejected file for manual editing, move it to `_raw/rejected-<category>-<name>.md` instead of deleting — this is opt-in per rejection, never the default.

### Conflict detection on patch accept

Before applying a patch, check whether the target page's `updated` field is newer than the patch's `ingested_at`:
- If the target was modified AFTER the patch was staged, warn: `⚠️ Conflict: target was updated since this patch was staged. Applying may lose recent changes.`
- Give the user a chance to abort: `Apply anyway [y], Skip [s], Reject [r]?`

## Step 4: Update Tracking Files

After processing all staged files — atomically, per the write protocol in `okf-wiki/SKILL.md`:

1. **`_cache/hot.md`** — update the Recent Activity section: "Committed N staged pages; rejected M."
2. **`log.md`** — newest-first under today's ISO-date heading:
   ```
   - STAGE_COMMIT accepted=N rejected=M skipped=K
   - REJECT page=_staging/concepts/fine-tuning-llms.md reason="duplicate of existing page"
   ```

## Step 5: Report

```
Stage commit complete.

✅  Accepted (N):
  concepts/attention-mechanism.md      → now live (status: draft)
  entities/andrej-karpathy.md          → now live (status: draft)
  concepts/transformer-architecture.md → updated (patch applied)

❌  Rejected (M):
  skills/fine-tuning-llms.md           → deleted from _staging/ (logged)

⏭️  Skipped (K):
  references/attention-is-all-you-need.md → still in _staging/

Staging queue: K files remaining
```

## Notes

- Staged files use the same page template as live pages — they are ready to land, just awaiting approval. Frontmatter follows the canonical OKF v0.2 template (see `okf-wiki/SKILL.md` §Schema — reference it; don't re-derive the mapping here).
- Patch files use a human-readable diff format: `## Additions` / `## Deletions` / `## Updated Fields` sections (format defined in `wiki-ingest/SKILL.md`)
- Only category pages go through staging. Of the tracking files, `log.md` and `_cache/hot.md` are always updated immediately by write skills (low-risk tracking files); the `index.md` entry for a staged page is added here, at promotion — so the live index never lists a page before it exists
- `_staging/` is out of OKF conformance scope: staged pages are invisible to `wiki-lint`, `wiki-query`, and any OKF consumer until promoted. The bundle stays portable throughout — promotion is a file move plus tracking updates, with no format conversion ("format not platform")
- Obsidian (optional viewer) and any other OKF reader only see a page after promotion

---

Derived from Ar9av/obsidian-wiki wiki-stage-commit skill (MIT).
