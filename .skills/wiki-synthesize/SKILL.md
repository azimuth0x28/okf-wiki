---
name: wiki-synthesize
description: >
  Systematically discover synthesis opportunities across the OKF bundle — pairs or clusters of
  concepts that co-occur frequently across pages but have no synthesis page connecting them. Creates
  new synthesis/ pages that draw explicit cross-cutting conclusions. Use when the user says "synthesize
  my bundle", "find connections", "what concepts keep coming up together", "/wiki-synthesize", or after
  a large ingest when the bundle has grown significantly.
---

# Wiki Synthesize — First-Class Synthesis Discovery

You are scanning the bundle for concepts that co-occur across many pages but have no dedicated synthesis page connecting them. Your job is to surface these gaps and fill the most valuable ones with cross-cutting synthesis pages.

## Before You Start

**Writing profile:** Before drafting or rewriting natural-language Markdown, read and apply the `Writing Profile Resolution` section in `okf-wiki/SKILL.md`. Framework schema, provenance, safety, and operation-specific requirements take precedence.
`WRITING.md` preferences apply only to newly drafted or rewritten natural-language Markdown; preserve source content and structured records.

1. **Resolve config** — follow the Config Resolution Protocol in `okf-wiki/SKILL.md` (inline `@name` override → walk up CWD for `.env` → global config → prompt setup). This gives `OKF_BUNDLE_PATH`.
2. Read `index.md` to get the full page inventory.
3. Read `_cache/hot.md` if it exists — it surfaces recent activity and active threads that may already point to synthesis opportunities.
4. Read `_meta/taxonomy.md` to understand the tag vocabulary.

## Step 1: Build the Co-occurrence Map

Scan every non-special page in the bundle (skip `index.md`, `log.md`, `_cache/hot.md`, `_insights.md`, `_meta/*`, `_archives/*`, `_raw/*`).

For each page, collect:
- All file-relative markdown links it contains (outgoing links)
- Its `tags` frontmatter
- Its `type` frontmatter

Build a co-occurrence matrix: for every pair of concept/entity pages (A, B), count how many other pages link to **both** A and B. This is their co-occurrence score.

You don't need to be exhaustive — aim for the top 20-30 pairs by co-occurrence score. Use Grep to find backlinks efficiently:

```bash
rg -l --glob '*.md' '\[.*\]\(\.\/.*ConceptA.*\)' "$OKF_BUNDLE_PATH"
```

Run this for your top candidate concepts and intersect the result sets.

## Step 2: Filter Out Already-Synthesized Pairs

Check the `synthesis/` directory for existing pages. For each existing synthesis page:
- Read its `sources` frontmatter or its body for file-relative markdown links
- Mark those concept pairs as already covered

Remove covered pairs from your candidate list.

## Step 3: Score and Rank Candidates

For each remaining candidate pair (or cluster of 3+), assign a synthesis value score:

| Signal | Points |
|---|---|
| Co-occurrence count ≥ 5 | +3 |
| Co-occurrence count 3-4 | +2 |
| Co-occurrence count 1-2 | +1 |
| Concepts are in different categories (cross-domain) | +2 |
| Concepts share tags but live in different folders | +1 |
| One or both concepts are tagged as hubs in `_insights.md` | +1 |
| A synthesis would resolve a flagged contradiction | +2 |

Pick the top 5 candidates. If the user asked for a specific topic ("synthesize everything about observability"), filter candidates to that domain first.

## Step 4: Draft Synthesis Pages

For each top candidate, create a page in `synthesis/` using this template:

```markdown
---
type: Synthesis
title: "<Concept A> × <Concept B>"
description: "Cross-cutting synthesis of how <A> and <B> interact, with implications for <domain>."
tags: [<shared tags>, <domain tags>]
sources:
  - resource: <path-to-all-pages-that-link-to-both>
generated:
  by: okf-wiki/<version>
  at: TIMESTAMP
status: draft
stale_after: TIMESTAMP_DATE
updated: TIMESTAMP
provenance:
  extracted: 0.2
  inferred: 0.7
  ambiguous: 0.1
---

# <Concept A> × <Concept B>

## The Connection

*What makes these two concepts worth synthesizing together — the non-obvious relationship that pages about each individually don't capture.* ^[inferred]

## Where They Co-occur

*The pages and contexts where both appear. What situations bring them together.* ^[extracted]

## Cross-cutting Insight

*The conclusion that only becomes visible when you look at both together. This is the point of the page — the thing you couldn't see from either concept page alone.* ^[inferred]

## Tensions and Trade-offs

*Where the two concepts pull in opposite directions. Unresolved contradictions. Cases where applying one undermines the other.* ^[inferred]

## Strongest Objection

*The best skeptical reading of THIS page's cross-cutting insight — the case a sharp critic would make that the connection is spurious, overstated, or an artifact of how the sources were written. Follow it with a testable search query (e.g. `> test: does X actually hold when Y is controlled for?`), never an invented citation. A synthesis that can't name its own strongest objection hasn't earned its conclusion.* ^[inferred]

## Open Questions

*What this synthesis surfaces that the bundle doesn't yet have an answer for. Good candidates for future research.*

## Related

- [Concept A](./concepts/concept-a.md)
- [Concept B](./concepts/concept-b.md)
- [Other related pages](./concepts/other.md)
```

**Provenance marker discipline:** Every synthesized claim (cross-page connections, gap-fill conclusions) carries the `^[inferred]` provenance marker; extracted/quoted claims keep `^[extracted]`. Synthesis pages are mostly `^[inferred]` — you are drawing connections across sources, which is synthesis by definition. Apply `^[inferred]` to cross-cutting conclusions and `^[ambiguous]` where sources disagree. See the Provenance Markers section in `.skills/okf-wiki/SKILL.md` for the full conventions; do not redefine them here.

**The title format is `A × B`** — this signals to readers that it's a synthesis page, not a page about either concept alone.

## Step 5: Back-link from Source Pages

For each synthesis page you created, add a link to it from the two (or more) concept pages it synthesizes. In the concept page, add to its `## Related` section:

```markdown
- [Concept A × Concept B](./synthesis/concept-a-x-concept-b.md) — synthesis
```

If the concept page has no `## Related` section, add one at the bottom.

## Step 6: Report Synthesis Opportunities Not Taken

After creating pages for the top 5, list the next 10 candidates in your output — pairs that scored well but you didn't write pages for. This gives the user visibility into what the bundle thinks is worth exploring without forcing every synthesis in one run.

Format:
```
Skipped (consider next time):
- [Caching](./concepts/caching.md) × [Consistency](./concepts/consistency.md) — co-occurs in 4 pages, cross-domain
- [Testing](./concepts/testing.md) × [Observability](./concepts/observability.md) — co-occurs in 3 pages, shares tags
...
```

## Step 7: Update Special Files

**`index.md`** — Add entries for all new synthesis pages.

**`log.md`** — Append:
```
- [TIMESTAMP] WIKI_SYNTHESIZE pages_scanned=N synthesis_created=M candidates_skipped=K
```

**`_cache/hot.md`** — Read `$OKF_BUNDLE_PATH/_cache/hot.md` (create from the template in `wiki-ingest` if missing). Update **Recent Activity** with what was synthesized — e.g. "Synthesized 5 cross-cutting pages: Caching × Consistency, Testing × Observability, …". Update **Active Threads** with any open questions the synthesis surfaced. Update `updated` timestamp.

## Quality Checklist

- [ ] Every synthesis page has a `summary:` field (≤200 chars)
- [ ] Every synthesis page links back to its source concepts (file-relative)
- [ ] Source concept pages link forward to the synthesis page
- [ ] No synthesis page just restates what's already on the source pages — it must add a cross-cutting insight
- [ ] Every synthesis page names its Strongest Objection with a testable search query (not an invented source)
- [ ] Every synthesized claim carries `^[inferred]`; every extracted claim carries `^[extracted]` or no marker
- [ ] `index.md` and `log.md` updated
- [ ] `_cache/hot.md` updated

## Tips

- **A synthesis page that only summarizes its sources is useless.** The value is the connection — the thing neither source page says explicitly.
- **Don't synthesize for synthesis's sake.** If two concepts just happen to appear together a lot without a real conceptual link, skip them.
- **Three-way syntheses are powerful but rare.** Only create them when three concepts form a genuine triangle of mutual influence — not just because all three appear in the same project page.
- **Check `_insights.md` first.** The wiki-status skill may have already flagged synthesis candidates there — start with those before running the co-occurrence scan from scratch.

---

Derived from Ar9av/obsidian-wiki wiki-synthesize skill (MIT).
