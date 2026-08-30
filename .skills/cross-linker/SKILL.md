---
name: cross-linker
description: >
  Scan the bundle and automatically discover missing cross-references between pages.
  Use this skill when the user says "link my pages", "find missing links", "cross-reference",
  "connect my bundle", "what pages should be linked", or after any large ingestion
  to ensure new pages are woven into the existing knowledge graph. Also trigger when the user
  mentions "orphan pages" in the context of wanting to connect them, or says things like
  "my bundle feels disconnected" or "pages aren't linked well". This is a write-heavy skill —
  it actually modifies pages to add links, unlike wiki-lint which just reports issues.
---

# Cross-Linker — Automated Bundle Cross-Referencing

You are weaving the bundle's knowledge graph tighter by finding and inserting missing file-relative markdown links between pages that should reference each other but currently don't.

**Follow the Retrieval Primitives table in `okf-wiki/SKILL.md`.** Build the registry in Step 1 by grepping frontmatter only (not full pages). Reserve full `Read` for the unlinked-mention detection pass, and even there, only read pages whose summaries/titles make them plausible link targets. Blind full-bundle reads are what this framework exists to avoid.

## Before You Start

**Writing profile:** Before drafting or rewriting natural-language Markdown, read and apply the `Writing Profile Resolution` section in `okf-wiki/SKILL.md`. Framework schema, provenance, safety, and operation-specific requirements take precedence.
`WRITING.md` preferences apply only to newly drafted or rewritten natural-language Markdown; preserve source content and structured records.

1. **Resolve config** — follow the Config Resolution Protocol in `okf-wiki/SKILL.md` (inline `@name` override → walk up CWD for `.env` → global config → prompt setup). This gives `OKF_BUNDLE_PATH`.
2. Read `index.md` to get the full inventory of pages and their one-line descriptions
3. Skim `log.md` to see what was recently ingested (focus linking effort on new pages)

When inserting links in Step 4, use file-relative markdown links (`[display text](./relative/path.md)` form). Compute the relative `.md` path from the **file being edited** to the target page.

## Step 1: Build the Page Registry

Glob all `.md` files in the bundle (excluding `_archives/`, `_readouts/`, `.obsidian/`). For each page, extract:

- **Filename** (without `.md`) — this is the link target
- **Title** from frontmatter
- **Aliases** from frontmatter (if any)
- **Tags** from frontmatter
- **Type** from frontmatter or directory inference
- **One-line summary** — first sentence or `description` field

Build a lookup table:

```
page_name → { path, title, aliases, tags, summary }
```

This is your "vocabulary" — every entry in this table is a valid link target.

## Step 2: Scan for Missing Links

For each page in the bundle:

1. **Read the full content**
2. **Extract existing links** — find all file-relative markdown links already present (e.g., `[text](./path.md)`)
3. **Search for unlinked mentions** — check if the page's text contains any of these, without being wrapped in a markdown link:
   - Page filenames (e.g., the word "MyProject" appears but `[my-project](./projects/my-project/my-project.md)` is missing)
   - Page titles from frontmatter
   - Aliases from frontmatter
   - Entity names, project names, concept names from the registry

4. **Check for semantic connections** — pages that share multiple tags or are in the same project directory but don't link to each other

### Matching Rules

- **Case-insensitive matching** for names (e.g., "my-project" matches page `MyProject`)
- **Diacritic-insensitive matching** — normalize both the page name and the body text with Unicode NFKD (decompose accented characters to base + combining marks, strip combining marks) before comparing. This ensures body text "Muller" matches page `entities/müller.md` and vice versa.
- **Skip self-references** — a page shouldn't link to itself
- **Skip common words** — don't link "the", "and", generic terms. Only match on distinctive names
- **Prefer the shortest unambiguous link path** — use `./page-name.md` not `./full/path/to/page-name.md` when the name is unique across the bundle
- **Don't link inside code blocks** or frontmatter
- **Don't double-link** — if a link to a target already appears on the page, don't add another

## Step 3: Score and Rank Suggestions

Not every possible link is worth adding. Score each candidate using a composite signal, then tag it with a confidence label.

### Scoring

| Signal | Points | Example |
|---|---|---|
| **Exact name match in text** | +4 | "MyProject" appears in body text → link to my-project.md |
| **Shared tags (2+)** | +2 | Both tagged `#ai #agent` but no link between them |
| **Same project, no link** | +2 | Both under `projects/my-project/` but don't reference each other |
| **Mentioned entity/concept** | +2 | Page mentions "knowledge graphs" → link to `./concepts/knowledge-graphs.md` |
| **Cross-type connection** | +2 | Source is in `concepts/`, target is in `entities/` (or `skills/` ↔ `synthesis/`) — different knowledge layers make this link more architecturally valuable |
| **Peripheral→hub reach** | +2 | Source page has ≤ 2 total links (peripheral) but target has ≥ 8 (hub) — connecting a loose page to a load-bearing concept |
| **Partial name match** | +1 | "graph" appears but page is `knowledge-graphs` — plausible but ambiguous |

### Confidence labels

Tag each candidate with a confidence label based on its score:

| Score | Label | Action |
|---|---|---|
| ≥ 6 | **EXTRACTED** | Link is effectively certain — exact mention or very strong match. Apply inline. |
| 3–5 | **INFERRED** | Link is a reasonable inference — shared context, cross-type, peripheral→hub. Apply inline or as Related section. |
| 1–2 | **AMBIGUOUS** | Weak or partial match. Skip unless user specifically asks to connect loose pages. |

Only act on **EXTRACTED** and **INFERRED** candidates. Include the confidence label in the Cross-Link Report so the user can review INFERRED links before trusting them.

## Step 4: Apply Links

**Pre-write snapshot** — before the first file write, check whether the bundle itself is the root of a Git repository. Merely being a subdirectory of a larger repository does not qualify: running `git add -A` there could capture unrelated files. If the bundle is not a standalone Git repository, skip this step silently — no nagging, no suggesting `git init`.

```bash
BUNDLE_REAL_PATH=$(cd "$OKF_BUNDLE_PATH" && pwd -P)
BUNDLE_GIT_ROOT=$(git -C "$OKF_BUNDLE_PATH" rev-parse --show-toplevel 2>/dev/null || true)
SNAPSHOT_SHA=""

if [ -n "$BUNDLE_GIT_ROOT" ] && [ "$BUNDLE_GIT_ROOT" = "$BUNDLE_REAL_PATH" ]; then
  if git -C "$OKF_BUNDLE_PATH" diff --quiet \
    && git -C "$OKF_BUNDLE_PATH" diff --cached --quiet \
    && [ -z "$(git -C "$OKF_BUNDLE_PATH" ls-files --others --exclude-standard)" ]; then
    SNAPSHOT_SHA=$(git -C "$OKF_BUNDLE_PATH" rev-parse HEAD)
  else
    if ! git -C "$OKF_BUNDLE_PATH" add -A; then
      echo "Pre-write snapshot failed; abort the skill without writing any bundle files." >&2
      exit 1
    fi
    if ! git -C "$OKF_BUNDLE_PATH" commit -m "pre-cross-linker snapshot" --quiet; then
      echo "Pre-write snapshot failed; abort the skill without writing any bundle files." >&2
      exit 1
    fi
    SNAPSHOT_SHA=$(git -C "$OKF_BUNDLE_PATH" rev-parse HEAD)
  fi
fi
```

The clean-repository branch deliberately avoids calling `git commit`, so "nothing to commit" is not treated as an error. If `git add` or `git commit` fails, stop before editing the bundle; never continue without the promised snapshot.

If `SNAPSHOT_SHA` is non-empty and the skill writes files, include the SHA in the final report. To discard the entire run, after confirming there are no later changes worth keeping, the user can run:

```bash
git -C "$OKF_BUNDLE_PATH" reset --hard "$SNAPSHOT_SHA"
git -C "$OKF_BUNDLE_PATH" clean -fd
```

For each page with missing links:

### 4a: Inline linking (preferred)

Find the first natural mention of the term in the body text and wrap it in a file-relative markdown link:

**Before:**
```markdown
This project uses knowledge graphs to connect entities.
```

**After:**
```markdown
This project uses [knowledge graphs](./concepts/knowledge-graphs.md) to connect entities.
```

Use the `[display text](./relative/path.md)` form. Compute the relative path from the file being edited to the target.

### 4b: Related section (fallback)

If the term isn't mentioned naturally in the body but the pages are semantically related (shared tags, same project), add a `## Related` section at the bottom of the page:

```markdown
## Related

- [my-project](./projects/my-project/my-project.md) — Also uses AI agents for research automation
- [knowledge-graphs](./concepts/knowledge-graphs.md) — Core technique used in this project
```

If a `## Related` section already exists, append to it. Don't duplicate existing entries.

### 4c: Infer and write relationship type

For every EXTRACTED or INFERRED link added (inline or related section), infer a semantic relationship type from the surrounding sentence context and write it to the page's `relationships:` frontmatter block. Skip AMBIGUOUS links.

**Type inference rules** — scan the sentence containing the mention (or, for related-section links, the page title and shared-tag context):

| Sentence pattern | Inferred type |
|---|---|
| "X extends / builds on / generalises Y" | `extends` |
| "X implements / is an implementation of Y" | `implements` |
| "X contradicts / opposes / refutes / is at odds with Y" | `contradicts` |
| "X is derived from / based on / adapted from Y" | `derived_from` |
| "X uses / relies on / depends on / requires Y" | `uses` |
| "X replaces / supersedes / deprecates Y" | `replaces` |
| Shared tags or cross-type inference with no directional cue | `related_to` |

If the surrounding context is ambiguous or the link came from shared-tag matching (no in-body mention), default to `related_to`.

**Writing the block:**

Read the page's YAML frontmatter. If a `relationships:` block already exists, append new entries without duplicating existing targets. If the block is absent, add it after `aliases:` (or after `tags:` when `aliases:` is missing).

```yaml
relationships:
  - type: uses
    target: ./concepts/knowledge-graphs.md
```

Always use file-relative markdown paths for `target` values in the `relationships:` YAML block. Body links and frontmatter targets use the same form: `[display](./relative/path.md)` for body, `target: ./relative/path.md` for frontmatter.

Only add entries for links added in this cross-linker run — do not touch typed entries that were already present.

**Relationship types allowlist** — the standard set is `extends`, `implements`, `contradicts`, `derived_from`, `uses`, `replaces`, `related_to`. A bundle's `AGENTS.md` may extend this list; use the effective allowlist and preserve owner semantics. See the Typed Relationships section in `okf-wiki/SKILL.md` for the full definitions and rules.

## Step 5: Score Misc Page Affinity

After the main linking pass, update affinity scores for all pages in `misc/` (pages with `promotion_status: misc` in their frontmatter, or located under the `misc/` directory).

For each misc page:

1. **Collect outgoing links** — all file-relative links in the page body
2. **Collect incoming links** — grep the bundle for references to `misc/<slug>.md`
3. For each linked page (both directions), check if it belongs to a project:
   - Lives under `projects/<project-name>/`
   - Has a `project:` frontmatter field matching a project name
4. Group by project name and sum: `outgoing_links + incoming_links`
5. Update the `affinity` frontmatter block on the misc page:

```yaml
affinity:
  my-project: 3
  another-project: 1
```

6. If any project's score ≥ 3: flag this page as a **promotion candidate** and record it for the report

**Efficiency note:** only read the full body of misc pages — other pages only need a frontmatter grep to determine their project membership.

## Step 6: Report

Present a summary:

```markdown
## Cross-Link Report

### Links Added: 23 across 12 pages

| Page | Links Added | Confidence | Placement | Relationship Types |
|---|---|---|---|---|
| `projects/my-project/my-project.md` | 3 | EXTRACTED | 2 inline, 1 related | uses ×2, related_to ×1 |
| `entities/jane-doe.md` | 5 | INFERRED | 3 inline, 2 related | extends ×1, uses ×3, related_to ×1 |
| ... | | | | |

### Orphan Pages Remaining: 2
- `references/foo.md` — no incoming or outgoing links found
- `concepts/bar.md` — could not find related pages

### Misc Promotion Candidates: N
Pages in misc/ that have ≥ 3 connections to a single project — ready to be promoted:

| Page | Top Project | Score |
|---|---|---|
| `misc/web-martinfowler-articles-microservices.md` | `my-project` | 4 |

To promote: move the page to `projects/<project-name>/references/` and update all backlinks.

### Pages Skipped: 3
- `index.md`, `log.md` — special files
- `_archives/*` — archived content
- `_readouts/*` — derived readouts (wiki-narrate output)
```

## Step 7: Update Log and Hot Cache

Append to `log.md`:
```
- [TIMESTAMP] CROSS_LINK pages_scanned=N links_added=M typed_relations_written=T pages_modified=P orphans_remaining=Q misc_affinity_updated=R promotion_candidates=S
```

**`_cache/hot.md`** — Read `$OKF_BUNDLE_PATH/_cache/hot.md` (create from the template in `wiki-ingest` if missing). Update **Recent Activity** with a one-line summary of what was linked — e.g. "Cross-linked 23 mentions across 12 pages; 2 orphans remain." Keep the last 3 operations. Update `updated` timestamp.

## Tips

- **Run after every ingest.** New pages are almost always poorly connected. This is the fix.
- **Be conservative with inline links.** Only link the first natural mention, not every occurrence.
- **Don't touch pages in `_archives/` or `_readouts/`.** Archives are frozen snapshots; readouts are derived output from `wiki-narrate`, not knowledge pages.
- **Respect existing structure.** If a page carefully curates its links in a `## Key Concepts` section, add to that section rather than creating a separate `## Related`.
- **Entity pages are link magnets.** An entity like `jane-doe` should be linked from almost every project page. Prioritize these.

> Derived from Ar9av/obsidian-wiki cross-linker skill (MIT).
