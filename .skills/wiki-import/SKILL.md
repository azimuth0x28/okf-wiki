---
name: wiki-import
description: >
  Merge an external OKF bundle into the current bundle — full page bodies, conflict resolution
  by trust priority, extension fields preserved on both sides — or reconstruct page stubs from
  a wiki-export graph.json. Reads legacy OKF v0.1 bundles and upgrades them to v0.2 on merge.
  Use this skill when the user says "import bundle", "import OKF bundle", "import OKF",
  "load graph.json", "import markdown bundle", "merge external bundle", "/wiki-import", or wants
  to transfer pages from one bundle to another using the output of wiki-export.
---

# Wiki Import — Merge External OKF Bundles

You are importing an external bundle's knowledge into the current bundle from one of two sources produced by `wiki-export`:

- **`graph.json`** — the graph skeleton. Reconstructs page **stubs** (frontmatter, typed relationships, a `## Related` link list — no body). Lossy.
- **OKF bundle** (a `wiki-export/okf/` directory, or any OKF v0.1/v0.2 bundle directory) — the actual markdown files. Reconstructs **full pages** with their real bodies. Lossless. Use this for true bundle-to-bundle transfer.

**Scope — OKF bundles only.** This skill consumes OKF v0.2 bundles, legacy OKF v0.1 bundles (upgraded on merge), and `wiki-export` graph artifacts. It does not import Obsidian vaults: migrating an Obsidian vault is a separate pipeline (`migrate-vault.sh`). If the user points at a raw vault — `[[wikilinks]]` in bodies, a `.obsidian/` directory, pages without OKF frontmatter — stop and redirect them to the migration pipeline.

**Format, not platform.** The external bundle may come from any OKF producer — another agent, another tool, another vendor. Apply the consumer guarantees from `.skills/okf-wiki/SKILL.md` (§OKF Conformance): accept missing optional fields, unknown `type` values, unknown frontmatter keys, broken links, and missing `index.md` files. Preserve extension fields on round-trip — that is what makes the merge lossless for both sides.

Either way, the import writes pages with canonical OKF v0.2 frontmatter and file-relative markdown links, then updates all bundle metadata. **Step 2, Step 3 (graph only), and Step 5 are shared; Step 4 forks by source type.**

## Before You Start

**Writing profile:** Before drafting or rewriting natural-language Markdown, read and apply the `Writing Profile Resolution` section in `.skills/okf-wiki/SKILL.md`. Framework schema, provenance, safety, and operation-specific requirements take precedence.
Preserve imported source prose; apply `WRITING.md` preferences only to newly generated metadata or stubs.

1. **Resolve config** — follow the Config Resolution Protocol in `.skills/okf-wiki/SKILL.md` (inline `@name` override → walk up CWD for `.env` → global config → prompt setup). This gives `OKF_BUNDLE_PATH`. (Legacy installs with `~/.obsidian-wiki` resolve through the same protocol.) Use `@name` or `bundle-switch` to target a different destination bundle.
2. Read `$OKF_BUNDLE_PATH/AGENTS.md` if it exists — apply any owner-specific conventions.

## Step 1: Locate and Detect Source Type

**Find the import source:**
- If the user provided a path argument, use it directly.
- Otherwise auto-detect, in order: `./wiki-export/okf/` (a directory) → `./wiki-export/graph.json` (a file).
- If neither exists, ask the user for the path.

**Detect the source type:**
- The path is a **file ending in `.json`** → **graph.json import** (validate below, then Step 3 + Step 4-Graph).
- The path is a **directory** containing `.md` files with OKF frontmatter (a non-empty `type:` key), and/or a root `index.md` with `okf_version` → **OKF bundle import** (skip Step 3; go to Step 4-OKF).
- The path looks like a raw Obsidian vault (`.obsidian/` directory, `[[wikilinks]]` in bodies, pages without OKF frontmatter) → **stop and redirect**: vault migration is the separate `migrate-vault.sh` pipeline; this skill consumes OKF v0.1/v0.2 bundles only.
- Anything else → report what's wrong and stop.

**Validate a graph.json source:**
- Must be valid JSON
- Must have top-level keys: `nodes` (array), `links` (array), `graph` (object)
- Must have at least 1 node

If validation fails, report what's wrong and stop.

**Validate an OKF bundle source:**
- Must contain at least 1 non-reserved `.md` file (i.e. not `index.md`/`log.md`) with parseable YAML frontmatter containing a non-empty `type`.
- A `.md` with no frontmatter or no `type` is skipped (with a count), not fatal — OKF consumers are permissive (OKF §9; see the consumer guarantees in `.skills/okf-wiki/SKILL.md`).
- Skip out-of-scope paths while walking: `_`-prefixed directories (`_raw/`, `_archives/`, `_meta/`, `_cache/`, …) and dot-files (`.manifest.json`, …) are operational artifacts, never imported.

**Detect the source spec version:**
- The external bundle's root `index.md` frontmatter says `okf_version: "0.1"` → **legacy v0.1 bundle** — read its legacy forms and upgrade to v0.2 on merge (see Step 4-OKF).
- No `okf_version`, but pages carry legacy field forms (`timestamp:` instead of `generated`, a `# Citations` body section instead of `sources:` frontmatter) → treat as v0.1 as well.
- `okf_version: "0.2"` (or v0.2 field forms throughout) → v0.2, import as-is.

**Show a preview before importing:**

graph.json:
```
Import preview (graph.json — stubs)
  Source: <path>  (exported at <graph.exported_at>)
  Nodes:  N total  (concepts: A, entities: B, skills: C, references: D, ...)
  Links:  M edges  (X typed, Y untyped)
  Target: $OKF_BUNDLE_PATH
```

OKF bundle:
```
Import preview (OKF bundle — full pages)
  Source: <dir>  (okf_version <ver if present>; v0.1 → will be upgraded on merge)
  Pages:  N total  (concepts: A, entities: B, skills: C, references: D, ...)
  Target: $OKF_BUNDLE_PATH
```

## Step 2: Determine Conflict Resolution Mode and Trust Priority

Read the user's phrasing to determine mode. Default is `merge`.

| Mode | Trigger phrases | Behaviour |
|---|---|---|
| `merge` | (default, no special phrasing) | Existing pages: trust-priority merge — union list-valued fields, resolve scalar conflicts by trust priority (below), merge bodies per Step 4; new pages: create. |
| `skip` | "skip existing", "don't overwrite", "only new pages" | Leave existing pages completely untouched; only create pages that don't exist yet. |
| `overwrite` | "overwrite", "replace existing", "force import" | Replace all matched pages with the imported version regardless of existing content. Trust ranks are ignored — record every replacement in the review report. |

### Trust priority (merge-mode conflict resolution)

When a merged page carries conflicting values, resolve by **trust priority** — never silently:

1. **Rank each side** (existing page and incoming page):
   - **human-verified** — the page has at least one `verified[]` entry whose `by` actor starts with `human:`
   - **human-authored** — `generated.by` starts with `human:`
   - **machine** — `generated.by` is `<producer>/<version>` or `process:<id>`, or `generated` is missing

   Rank: human-verified > human-authored > machine.
2. **Ranks differ** → the higher-trust side wins the field.
3. **Ranks tie** → the newer `generated.at` timestamp wins (a missing `generated.at` loses to any present timestamp).
4. **Still tied** (same timestamp) → the existing page wins (the destination bundle is authoritative on full ties) — and the conflict is reported.
5. **Every conflict is reported to the human in the review report (Step 6)** — page, field, existing value, incoming value, rule applied, winner. Conflicts are never silently resolved.

List-valued fields are exempt from winner-takes-all: `tags`, `aliases`, `relationships`, `sources`, and `verified` are **unioned with dedup** so both sides survive the merge (see Step 4-OKF). The trust priority governs scalar fields only.

## Step 3: Build Internal Maps  *(graph.json only — skip for OKF bundles)*

Before writing anything, build two maps from the `links` array:

**Adjacency map** — for each node id, collect all neighbour ids (edges in either direction):
```
adjacency["concepts/transformers"] = ["entities/vaswani", "concepts/lstm", ...]
```

**Typed edge map** — for each node id, collect outgoing typed edges only (`typed: true`):
```
typed_edges["concepts/transformers"] = [
  {target: "concepts/lstm", relation: "contradicts"},
  ...
]
```

## Step 4-Graph: Reconstruct Page Stubs from graph.json  *(graph.json source only)*

Record counts: `created = 0`, `skipped = 0`, `merged = 0`.

For each node in `nodes`:

1. Compute `page_path = $OKF_BUNDLE_PATH/<node.id>.md`
2. Ensure the parent directory exists (e.g. `$OKF_BUNDLE_PATH/concepts/`)
3. Check if the file already exists:
   - **merge mode (default) + exists** → read existing file, apply merge logic (see below), increment `merged`
   - **merge mode (default) + doesn't exist** → proceed to create stub, increment `created`
   - **skip mode + exists** → increment `skipped`, continue to next node
   - **skip mode + doesn't exist** → proceed to create stub, increment `created`
   - **overwrite mode + exists** → proceed to write fresh stub (overwrite), increment `merged`
   - **overwrite mode + doesn't exist** → proceed to create stub, increment `created`

### Page template (new or overwrite) — canonical OKF v0.2

```markdown
---
type: <node.type from the export — Concept|Entity|Skill|Reference|Synthesis|Project|Journal; for foreign producers, coerce to TitleCase>
title: <node.label>
description: "<node.description>"        # only if node.description exists
tags: <node.tags as YAML list>
generated: { by: <producer>/<version>, at: <ISO timestamp> }   # acting agent; fallback okf-wiki/<version>
status: draft
stale_after: <updated + 90 days>
sources:
  - resource: "<graph.json path>"
    title: "wiki-export graph.json"
# ===== extension fields (OKF §4.1 — preserve verbatim) =====
updated: <ISO timestamp>
relationships:                            # only if typed_edges[node.id] is non-empty
  - target: ./<file-relative path to target>.md
    type: <relation>
base_confidence: 0.5
tier: supporting
---

# <node.label>

<node.description paragraph if available, else omit>

## Related

<for each neighbour in adjacency[node.id], sorted alphabetically>
<if edge is typed>
- [<neighbour title>](./<file-relative path>.md) — <relation>
<else>
- [<neighbour title>](./<file-relative path>.md)
</if>
</for>
```

If `adjacency[node.id]` is empty, omit the `## Related` section entirely. Relationship targets and `## Related` links are **file-relative markdown paths** — compute them from the new page's directory to the target page's `$OKF_BUNDLE_PATH/<node-id>.md` location (e.g. from `concepts/transformers.md` to `concepts/lstm` the target is `./lstm.md`).

### Merge logic (merge mode, existing page)

1. Read the existing page's frontmatter.
2. **Tags**: union of existing tags and `node.tags` (deduplicated, keep existing order, append new ones).
3. **Description**: if the existing page has no `description` field and `node.description` exists, add it.
4. **Relationships**: union of existing `relationships:` entries and `typed_edges[node.id]` — normalize targets to bundle-relative ids before comparing, skip entries where the same `(target, type)` pair already exists, store file-relative to this page.
5. **Trust priority**: a stub never overwrites a scalar field on a higher-trust existing page. Rank both sides per Step 2; when the existing page outranks the stub (or ranks tie), keep the existing scalar values and record the suppressed stub fields in the review report.
6. **Updated**: set `updated` to the current ISO timestamp; recompute `stale_after = updated + 90 days`.
7. **Body**: scan for a `## Related` section. If it exists, append any missing links from `adjacency[node.id]` that aren't already linked anywhere in the body. If no `## Related` section exists, append one with the missing links.
8. Leave the rest of the body untouched.

## Step 4-OKF: Merge Pages from an OKF bundle  *(OKF source only)*

Record counts: `created = 0`, `skipped = 0`, `merged = 0`, `unparseable = 0`, `upgraded_v01 = 0`, `conflicts = 0`.

Walk the external bundle directory tree. For each `.md` file that is **not** a reserved file (`index.md`, `log.md`) and **not** out of scope (`_`-dirs, dot-files):

1. Parse the YAML frontmatter. If it has no frontmatter or no non-empty `type`, increment `unparseable` and skip the file.
2. **Resolve the page identity:**
   - **Primary — path identity:** the concept id is the file's path relative to the external bundle root with `.md` stripped (e.g. `concepts/transformers.md` → `concepts/transformers`). The target page is `$OKF_BUNDLE_PATH/<id>.md`. Same id → same page.
   - **Title-collision fallback:** an incoming page with a *different* id whose `title` matches an existing page's title (case-insensitive) is a candidate duplicate. Confirm with `aliases`/`description` overlap: a clear match → treat as the same page and record the identity decision in the review report; ambiguous → escalate to the human with the options *merge anyway*, *import side-by-side*, or *skip*.
   - **Unresolvable identity clash** (same id on both sides, both human-verified, materially different content): default to a **side-by-side namespace** — import under `imports/<source-bundle-name>/<id>.md`, rewriting the imported page's internal links to the new layout — and escalate consolidation to the human (`wiki-dedup` can merge the twins later). Never pick a winner silently.
3. **Upgrade v0.1 legacy forms to v0.2** (applies per page; the rules are self-contained — the same semantics are encoded in the vault migrator, `migrate-vault.sh`):

   | Legacy v0.1 form | v0.2 upgrade on merge |
   |---|---|
   | `timestamp: <ISO>` | `generated: {by: <actor>, at: <ISO>}` — `by` inferred from the source manifest/producer when determinable, else the fallback `okf-wiki/<version>` |
   | `# Citations` section in the body | `sources:` frontmatter list — one entry per citation with `resource` required; drop the body section after conversion |
   | root `index.md` `okf_version: "0.1"` | `"0.2"` — the destination bundle is already v0.2; imported pages are written in v0.2 form |

   Reading legacy forms is always safe (v0.2 consumers read v0.1); **writing always upgrades**. Count each upgraded page in `upgraded_v01`.
4. **Normalize links and relationship targets.** The imported page's internal links are file-relative to the *source* layout. For every markdown link and `relationships[].target`: resolve it against the external bundle root to a bundle-relative id, then re-emit it as a file-relative markdown link from the page's destination path. `/`-absolute links are converted to file-relative the same way (the destination bundle's default). External `http(s)://` links stay untouched. Links whose targets don't exist yet are forward-references — keep them (W2 tracks them).
5. **Write the page** using the conflict mode from Step 2:
   - **merge + exists** → perform the **trust-priority merge** below. Increment `merged`.
   - **merge + doesn't exist** → write the full page (upgraded to v0.2 if the source was v0.1), frontmatter preserved verbatim from the source — external `status`/`verified` values are external provenance and carry over verbatim. Increment `created`.
   - **skip + exists** → increment `skipped`, continue.
   - **skip + doesn't exist** → write the full page. Increment `created`.
   - **overwrite + exists** → write the full page, replacing the existing one. Increment `merged` (label as `Replaced` in the summary) and record the replacement in the review report.
   - **overwrite + doesn't exist** → write the full page. Increment `created`.
6. Ensure the parent directory (`$OKF_BUNDLE_PATH/concepts/`, etc.) exists before writing.

Unlike the graph.json path, **do not** generate a `## Related` stub section — the bundle body already contains the real cross-links.

### Trust-priority merge (merge mode, existing page)

1. **Rank both sides** per Step 2 (human-verified > human-authored > machine).
2. **Body**: the OKF bundle carries a real body. Replace the existing body with the bundle body **only if the existing page is a stub** (body is just a heading + `## Related`); otherwise keep the existing body and append any bundle `##` sections not already present. When bodies merge, recompute `provenance` fractions over the merged body (source-merge semantics — the block describes the merged page's claim mix).
3. **Frontmatter — union fields (both sides preserved, dedup):**
   - `tags`, `aliases` — union, keep existing order, append new.
   - `relationships` — union; dedup on the normalized `(target id, type)` pair; store targets file-relative to the merged page.
   - `sources` — union; dedup on `resource`.
   - `verified` — union; dedup on `(by, at)`. **Never drop a `human:` entry from either side.**
4. **Frontmatter — scalar fields** (`title`, `description`, `base_confidence`, `tier`, `lifecycle: disputed`, and any unknown extension keys): apply the trust priority from Step 2 (rank → newer `generated.at` → existing wins on full tie). Every changed value is a reported conflict. `type` is implied by the destination directory and is kept as-is on merge.
5. **`provenance`**: when bodies merged (per step 2), recompute over the merged body; when the existing body was kept unchanged, keep the existing block and report the incoming one if it differed.
6. **`superseded_by`**: never resolved by trust priority. Carry it only when the merged page is (or becomes, human-approved) `deprecated`; otherwise record it in the review report as a pending deprecation.
7. **`generated`**: keep the trust-priority winner's value — it records the content's origin. The merge actor is recorded in `log.md`, and `updated`/`stale_after` are refreshed (`updated` = now; `stale_after` = `updated + 90d`).
8. **`status` / `verified`**: on merge, keep the existing page's `status`. If the incoming status differs, record both values in the review report for human confirmation. Never apply trust priority to `status`. The import never elevates trust: it never performs a `draft → stable` transition and never adds `verified` entries of its own (human-only lifecycle invariant, `.skills/okf-wiki/SKILL.md` §Schema). Any page arriving as `status: stable` or carrying `human:`-verified entries is listed in the review report for human confirmation.
8. **Extension-field preservation is both-sides**: the union rules above apply to the full §4.1 extension list from `.skills/okf-wiki/SKILL.md` §Schema (`updated`, `aliases`, `relationships`, `provenance`, `base_confidence`, `tier`, `lifecycle_changed`, `superseded_by`, `lifecycle`) plus any producer-specific keys — unknown keys are preserved verbatim per the OKF consumer guarantees.

## Step 5: Update Bundle Metadata

### `.manifest.json`

Add a new entry keyed by the canonical path of the source (absolute, `~` and env vars expanded):

```json
"<absolute path to source>": {
  "ingested_at": "<ISO timestamp>",
  "source_type": "okf-bundle",
  "content_hash": "sha256:<64-char-hex>",
  "pages_created": ["list/of/created/pages.md"],
  "pages_updated": ["list/of/merged/pages.md"]
}
```

- `source_type` is `"wiki-export-graph"` for a graph.json import or `"okf-bundle"` for an OKF bundle import.
- `content_hash`: for a graph.json file, the SHA-256 of the file. For a bundle directory, the SHA-256 over the sorted list of `<relative-path>:<sha256-of-contents>` pairs (deterministic — recompute it to detect changes on re-import).
- Key by the canonical expanded-absolute path (the `graph.json` file or the bundle directory).

Also increment:
- `stats.total_sources_ingested` by 1
- `stats.total_pages` by the count of pages actually created (not skipped/merged)

If `.manifest.json` doesn't exist, create it with `version: 1` and the standard structure. It is a dot-file at the bundle root — operational, outside OKF conformance scope.

### `index.md` (per-directory)

For each **created** or **merged** page, add or update the entry in its category directory's `index.md`:

```markdown
- [Title](./<file>.md) — <description or title>
```

Keep entries sorted alphabetically. Create the directory and its `index.md` if they don't exist. Rebuild the root `index.md` catalog only when a new category directory appeared (the root index is the progressive-disclosure catalog with `okf_version: "0.2"`).

### `log.md`

Add one entry under today's ISO-date heading (newest-first):

```
- [<ISO timestamp>] IMPORT source="<source path>" pages_created=<N> pages_skipped=<K> pages_merged=<M> conflicts_reported=<C> v0.1_upgraded=<U>
```

### `_cache/hot.md`

Rewrite the **Recent Activity** section to include this import as the latest entry:

```
- [<timestamp>] IMPORT from <source path> — created X, merged Z pages, C conflicts reported
```

Update the `updated:` frontmatter timestamp if present. Leave other `_cache/hot.md` sections (Active Threads, Key Takeaways) intact unless they reference pages that were just created — in which case add brief mentions.

## Step 6: Review Report and Summary

### Review report (mandatory when anything conflicted)

Write `_readouts/import-review-<YYYY-MM-DD>.md` (out-of-scope directory) containing:

- **Every field-level conflict** — page, field, existing value, incoming value, rule applied (trust rank / newer `generated.at` / existing-on-tie), winner.
- **Identity decisions** — title-collision merges, side-by-side namespace imports, escalations awaiting the human.
- **v0.1 upgrades** — pages converted from legacy forms, with what changed.
- **Trust carry-overs** — every imported page arriving `status: stable` or carrying `human:` `verified` entries, for human confirmation.

Print the report path in the summary. **No conflict is ever silently resolved** — if it changed a value, it is in the report.

### Summary

```
Wiki import complete → $OKF_BUNDLE_PATH
  Source:  <source path>  (<graph.json | OKF bundle v0.2 | OKF bundle v0.1 → upgraded>)
           <graph: exported at <graph.exported_at>, N nodes, M links | okf: N pages, okf_version <ver>>
  Created: <X> pages
  Merged:  <Z> pages  (trust-priority merge)
  Skipped: <Y> pages  (only when skip mode was used)
  Conflicts: <C>  → _readouts/import-review-<date>.md
  Upgraded from v0.1: <U> pages
```

Only show the `Skipped` line if `skip` mode was explicitly requested. If `overwrite` mode was used, label merged pages as `Replaced` instead. For an OKF import, also report `Unparseable: <U> files (no frontmatter/type, skipped)` when `U > 0`.

## Notes

- **Stub vs full pages**: A **graph.json** import produces stubs — structure and links but no body, a starting point for future ingestion. An **OKF bundle** import produces full pages with real bodies — it is the lossless, content-bearing path and the right choice for bundle-to-bundle transfer.
- **Re-running is safe**: The default `merge` mode is idempotent — re-running on an unchanged source will update timestamps but won't destroy content. Use `overwrite` only when you want to fully reset pages to the imported version.
- **Directory creation**: Always create missing category directories before writing pages.
- **Broken links are forward-references**: Since pages are being created together from the same source, most links will resolve. Any page referenced in the source but absent from it (broken in the original export) will still appear as a link — it just won't have a corresponding page file, which is valid (W2 forward-reference).
- **Filtered sources**: If the source graph.json was produced with visibility filtering (noted in the top-level `graph` object through its `filter` key), imported pages will only reflect the filtered set. Note this in the summary if the top-level `graph` object contains a `filter` key.
- **Trust is never fabricated**: the import preserves external `verified`/`status` values verbatim, never elevates them, and reports every trust-bearing page to the human. Extension fields survive on both sides — that is the lossless guarantee.

---

Derived from Ar9av/obsidian-wiki wiki-import skill (MIT).
