---
name: wiki-digest
description: >
  Generate a periodic knowledge digest — a human-readable newsletter-style summary of what was
  learned, updated, and connected in your bundle over a specified period (day/week/month). Use when
  the user says "what did I learn this week", "give me a digest", "weekly summary", "knowledge
  report", "what's new in my bundle", "/wiki-digest [period]", "summarize my recent learning", or
  wants a readable overview of recent bundle activity. Distinct from wiki-status (which reports
  ingestion delta of sources) — wiki-digest summarizes *knowledge*, not sources.
---

# Wiki Digest — Knowledge Newsletter Generator

You are generating a human-readable digest of recent bundle activity: what was learned, what was updated, what themes are emerging, and what's worth reviewing. This skill summarizes *knowledge*, not sources — think of it as a weekly review session, not an ingestion status report.

## Before You Start

1. **Resolve config** — follow the Config Resolution Protocol in `okf-wiki/SKILL.md` (inline `@name` override → walk up CWD for `.env` → global config → prompt setup). This gives `OKF_BUNDLE_PATH`.
2. **Parse the period** from the user's request:
   - "daily" / "today" / "yesterday" → last 24 hours
   - "weekly" / "this week" / no argument (default) → last 7 days
   - "monthly" / "this month" → last 30 days
   - ISO date like "since 2026-05-01" → pages updated since that date
   - Explicit number like "last 14 days" → that many days
3. Read `$OKF_BUNDLE_PATH/log.md` — last 200 lines — for entries within the period (timestamps are ISO-8601 prefixed lines).
4. Read `$OKF_BUNDLE_PATH/_cache/hot.md` for current session context.
5. If `$OKF_BUNDLE_PATH/_insights.md` exists, read its **Anchor Pages** table — you'll use it later to identify which new pages became hubs.

## Step 1: Collect Pages Active in the Period

Glob all `.md` files under `$OKF_BUNDLE_PATH`. Skip special/system files:
- `index.md`, `log.md`, `_cache/hot.md`, `AGENTS.md`, `_insights.md`
- Anything under `_meta/`, `_archives/`, `_raw/`
- Journal digest pages themselves (`journal/digest-*.md`)

For each remaining page, read its frontmatter:
- `created` — when the page was first written
- `updated` — when it was last modified

Classify:
- **New pages**: `created` is within the period
- **Updated pages**: `updated` is within the period but `created` is before it
- **Unchanged**: neither date falls in the period → skip

If fewer than 5 pages were active, note it and offer to widen: *"Only 3 pages were active in the last 7 days — want a monthly digest instead?"* Stop here unless the user says to continue.

For each active page, collect: `title`, `type`, `tags`, `summary` (frontmatter field), `status`, any `^[ambiguous]` or `^[inferred]` markers in the body.

## Step 2: Identify Themes

From all active pages' tags, tally theme frequency:

```
For each tag across new + updated pages:
  count how many active pages carry it
Sort descending, take top 5
```

Also read `$OKF_BUNDLE_PATH/_meta/taxonomy.md` (if it exists). Flag any tag from step 1 that **does not appear** in the taxonomy — these are new vocabulary words that emerged this period.

Note which categories grew most (concepts/, entities/, skills/, synthesis/, references/, etc.).

## Step 3: Find Notable New Connections

Scan new and updated pages for cross-category file-relative links — links that bridge different knowledge layers. These are the most intellectually interesting outputs of the period.

For each active page, extract all markdown links (`[text](./path.md)` targets). Classify each link by the target's category prefix. Flag links that cross categories (e.g., a `concepts/` page linking to an `entities/` page, or a `synthesis/` page bridging two topics).

Rank candidates by interestingness:
- **+3** if the link is across two categories that rarely connect (use `_insights.md` bridge data if available)
- **+2** if the target page is a top-10 hub (per `_insights.md` anchors)
- **+2** if the link appears in a `synthesis/` page (deliberate cross-cutting)
- **+1** if the source page is marked `^[inferred]` (synthesized connection, not directly stated)

Take the top 3–5 connections. Write each as a plain-English sentence: not just "A → B" but *why* the connection is interesting.

## Step 4: Surface Open Threads

Scan active pages and `_raw/` for unresolved work:

- **Drafts**: pages with `status: draft` or `status: stub`
- **Ambiguous claims**: count `^[ambiguous]` markers across all active pages (don't list every one — just the count and which pages have the most)
- **Unstaged notes**: count files in `$OKF_BUNDLE_PATH/_raw/` (anything here hasn't been promoted)
- **Taxonomy gaps**: tags from Step 2 that aren't in `_meta/taxonomy.md`

## Step 5: Choose Recommended Re-reads

From the *existing* (pre-period) pages, identify 2–3 worth revisiting given this week's new context.

Heuristic: find pre-period pages that share the most tags with the active pages from Step 1. These are foundational pages whose topic was extended this period — the new pages build on them but the user may not have revisited the foundation.

Also include any pre-period page that now has 2+ new incoming links from active pages (it just became more connected — a sign it's load-bearing).

Write each recommendation with a concrete reason: *"[(concepts/attention-mechanism.md)](./concepts/attention-mechanism.md) — your foundational page; three new papers ingested this week all extend it"*, not just the page title.

## Step 6: Generate the Digest

Produce a structured, scannable markdown report. The Headlines section is the most important — it should feel like the opening of a good newsletter, synthesizing actual insight rather than listing page names.

Use file-relative markdown links: `[display](./relative/path.md)`.

```markdown
# Wiki Digest — [Period Label]
> [N new pages · M updated pages · period: YYYY-MM-DD to YYYY-MM-DD]

## Headlines

- [Concrete insight #1 — synthesize the actual knowledge, not just "learned about X"]
- [Concrete insight #2]
- [Concrete insight #3]

## New Knowledge

### New pages ([count])
| Page | Type | Summary |
|---|---|---|
| [Foo](./concepts/foo.md) | Concept | One-sentence summary from frontmatter |
| [Bar](./entities/bar.md) | Entity | One-sentence summary |

### Notable updates ([count])
| Page | What changed |
|---|---|
| [React Hooks](./skills/react-hooks.md) | Added patterns for useCallback with async effects |

*(If no updates, omit this subsection.)*

## Emerging Themes

- **#[tag]** ([N pages]) — [One sentence on why this topic was active]
- **#[tag]** ([N pages]) — [...]
- **#[NEW TAG]** ([N pages]) ⭐ *New vocabulary — not yet in taxonomy*

Most active category: **[category/]** ([N pages added or updated])

## Key Connections Made

- [(concepts/A.md)](./concepts/A.md) → [(entities/B.md)](./entities/B.md) — [Plain-English reason this connection is interesting]
- [Synthesis X](./synthesis/X.md) created — bridges [Concept Y](./concepts/Y.md) and [Concept Z](./concepts/Z.md) for the first time
- *(up to 5 connections)*

## Open Threads

- **Drafts to compile** ([count]): [Foo](./concepts/foo.md), [Bar](./concepts/bar.md) — still in draft status
- **Ambiguous claims**: [N] `^[ambiguous]` markers across [M] pages — run `/wiki-synthesize` to resolve
- **Unstaged notes**: [N] files in `_raw/` — run `/wiki-ingest _raw/` to promote them
- **Taxonomy gaps**: Tags `#newtag1`, `#newtag2` used but not in taxonomy — run `/tag-taxonomy`

*(Omit any subsection where count is 0.)*

## Recommended Re-reads

- [Concept X](./concepts/X.md) — [Specific reason: "3 new papers this week all extend this concept"]
- [Synthesis Y](./synthesis/Y.md) — [Specific reason: "2 new pages created this week reference it"]
- [Skill Z](./skills/Z.md) — [Specific reason: "now has 4 new incoming links — it's become a hub"]

---
*Generated by wiki-digest · [TIMESTAMP] · [N pages scanned in [BUNDLE_PATH]]*
```

**Visibility**: If a page is tagged `visibility/pii`, exclude it from all tables and connection lists (but count it in the totals, noted as "+ N private"). If the user explicitly says "include private pages" or "full digest", include them normally.

## Step 7: Output & Optionally Save

**Default (chat output):** Print the digest directly. At the end, ask:
*"Want me to save this as `journal/digest-YYYY-MM-DD.md`?"*

**If user prefixed with "save" or "write"** (e.g., `/wiki-digest save` or "generate and save my weekly digest"):
- Write to `$OKF_BUNDLE_PATH/journal/digest-YYYY-MM-DD.md` (weekly/monthly) or `journal/digest-YYYY-MM-DD-daily.md` (daily)
- Add frontmatter:
  ```yaml
  ---
  title: "Wiki Digest — [Period Label]"
  type: Journal
  tags: [digest, meta/review]
  sources: []
  generated: { by: <agent>, at: <TIMESTAMP> }
  status: published
  updated: TIMESTAMP
  summary: "Weekly knowledge digest: [N new, M updated pages]. Top themes: [tag1], [tag2]."
  ---
  ```
- Update `index.md` with the new entry under Journal
- Do **not** add to `.manifest.json` (digests aren't source ingestions)

Either way, append to `log.md`:
```
- DIGEST period="7d" new_pages=N updated_pages=M themes=T connections=C saved=false
```

## Edge Cases

| Situation | Handling |
|---|---|
| Fewer than 5 active pages | Offer to widen the period; proceed only if user confirms |
| Empty bundle (no pages at all) | Tell the user to run an ingest first; stop |
| No `_meta/taxonomy.md` | Skip taxonomy gap check; omit that line from Open Threads |
| No `_insights.md` | Skip hub-based scoring in Step 3; still produce connections section |
| All pages are `visibility/pii` | Report "N private pages active this period" with no details; offer full mode |
| Period spans a bundle rebuild | Note it in the digest: "Bundle was rebuilt during this period — page dates reflect post-rebuild state" |

## Notes

- **Headlines are the payoff.** Don't list page titles — synthesize the actual learning. If someone learned about attention mechanisms this week, the headline should capture the insight, not just say "added 3 transformer pages".
- **Be concrete about re-reads.** "This page is relevant" is useless. "3 of this week's papers all cite the same claim in this page" is actionable.
- **This skill only reads.** The only writes are the optional journal page, and the `log.md` append. It does not modify existing bundle pages.
- **Don't duplicate wiki-status.** If the user asks "what needs ingesting" or "what's the delta", route to `wiki-status`. This skill answers "what did I learn", not "what's pending".

---
*Derived from Ar9av/obsidian-wiki wiki-digest skill (MIT).*
