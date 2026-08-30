---
name: wiki-lint
description: >
  Audit and maintain the health of an OKF v0.2 bundle: verify conformance (error classes E1–E4,
  warning classes W1–W7), find orphaned pages, detect contradictions, identify stale content,
  fix broken links, and perform general maintenance on the knowledge base. Use this skill when the
  user wants to check their bundle for issues, says "clean up the wiki", "what needs fixing",
  "audit my notes", "lint my bundle", or "wiki health check". Add --consolidate to switch from
  report-only to act-and-report mode (the "dream cycle"): fixes truly broken links, adds missing
  cross-references for orphans, flags lifecycle promotions for human review, demotes stale
  peripheral pages, normalizes tag aliases, and adds contradiction callouts — all with a dry-run
  preview and explicit user confirmation before any writes.
---

# Wiki Lint — OKF Conformance and Health Audit

You are performing a health check on an OKF v0.2 bundle. The skill has a dual mandate:

1. **OKF v0.2 conformance** — verify the three conformance rules and report error classes
   `E1`–`E4` and warning classes `W1`–`W7` with exactly the semantics of `scripts/validate.sh`
   in the okf-wiki repo.
2. **Knowledge-graph health** — find and fix structural issues that degrade the bundle's value
   over time: orphans, broken links, contradictions, staleness, provenance drift, fragmented
   tag clusters, and illegal lifecycle transitions.

**Before scanning anything:** follow the Retrieval Primitives table in `.skills/okf-wiki/SKILL.md`. Prefer frontmatter-scoped greps and section-anchored reads over full-page reads. On a large bundle, blindly reading every page to lint it is exactly what this framework is built to avoid.

## Before You Start

**Writing profile:** Before drafting or rewriting natural-language Markdown, read and apply the `Writing Profile Resolution` section in `.skills/okf-wiki/SKILL.md`. Framework schema, provenance, safety, and operation-specific requirements take precedence.
Apply `WRITING.md` preferences only to generated consolidation reports; deterministic findings and fixes keep their existing formats.

1. **Resolve config** — follow the Config Resolution Protocol in `.skills/okf-wiki/SKILL.md` (inline `@name` override → walk up CWD for `.env` → global config → prompt setup). This gives `OKF_BUNDLE_PATH` plus any `OKF_ALLOWED_LIFECYCLES`, `OKF_ALLOWED_RELATIONSHIP_TYPES`, `OKF_REQUIRED_TRUST_FIELDS`, `OKF_SCHEMA_SOURCE`, `OKF_TRUST_STRICT`, and `LINT_SCHEDULE` values. (Legacy installs that still resolve `~/.obsidian-wiki/config` map `OBSIDIAN_VAULT_PATH` to `OKF_BUNDLE_PATH`.)
2. **Read owner rules** — if `$OKF_BUNDLE_PATH/AGENTS.md` exists, read it before interpreting any schema. Owner rules override framework defaults and may extend the status set, the relationship allowlist, and required trust fields.
3. **Form the effective schema** — record the schema source locator (`OKF_SCHEMA_SOURCE`, typically `$OKF_BUNDLE_PATH/AGENTS.md`) plus effective required/optional frontmatter, status values, relationship types, and trust fields. Framework values are defaults; preserve owner extensions and relaxed requiredness exactly. Never coerce an owner type to a framework type.
4. Read `index.md` for the full page inventory
5. Read `log.md` for recent activity context

Schema precedence is resolved environment/config values (including owner extensions recorded in bundle `AGENTS.md`) > framework defaults; status and relationship extensions remain additive. Strip every override before use. An explicitly configured empty or whitespace-only value—and any empty comma-separated list entry—fails closed; never treat it as a valid status, relationship type, required field, or authority locator. Remove the variable instead when defaults are intended.

## Deterministic Validation: okflint → validate.sh

Run the deterministic conformance pass first — it is cheap, and its verdict anchors everything the agent-side checks report afterwards:

1. **okflint (preferred).** If `command -v okflint` succeeds, run it against the bundle with the bundle's own profile:

   ```bash
   okflint --profile "$OKF_BUNDLE_PATH/okf-base.yaml" "$OKF_BUNDLE_PATH"
   ```

   `okf-base.yaml` is the okflint profile created by `wiki-setup`: it declares `okf_version: "0.2"` plus the `extensions` block (`fields`, `reserved_dirs`, `reserved_files`) this bundle uses on top of OKF v0.2 core. Hand the profile to okflint exactly as written — do not inline or edit it for the run.

2. **`scripts/validate.sh` (self-sufficient fallback).** If okflint is unavailable, run the repo's validator:

   ```bash
   bash scripts/validate.sh "$OKF_BUNDLE_PATH"
   ```

   Exit codes: `0` = conformant, `1` = at least one E-class error, `2` = usage error. The script implements E1–E4 and a subset of the warnings — W1, W3, W5, W6, W7, plus an unnumbered unknown-`status` warning. It does **not** implement W2 (broken links) or W4 (missing per-dir `index.md`): those are agent-side health checks below. The script skips out-of-scope zones and prints a trust/provenance/lifecycle summary. It needs nothing but bash — okf-wiki's core is self-sufficient, and okflint is optional.

The deterministic runners apply framework defaults plus the bundle's `okf-base.yaml` profile. Owner extensions beyond the profile (from `OKF_*` overrides and bundle `AGENTS.md`) are applied by the agent-side checks below. Record the tool used, its exit code, and its raw findings in the final report. Agent-side checks re-derive the same classes the script implements (E1–E4, W1/W3/W5/W6/W7) plus the health checks it does not cover (W2, W4, orphans, staleness, contradictions). For the classes the deterministic run covers, any disagreement between the agent's conformance findings and the deterministic run is a bug in the agent pass — trust the deterministic result. For W2/W4 and the other agent-side health checks, the agent's findings stand (there is no deterministic counterpart to contradict them).

## OKF v0.2 Conformance Core

### The three conformance rules

1. Every non-reserved `.md` file in the tree contains a parseable YAML frontmatter block.
2. Every frontmatter block contains a non-empty `type` field (TitleCase — see the canonical mapping in `.skills/okf-wiki/SKILL.md` §Canonical Frontmatter; reference it, do not re-derive it here).
3. Every reserved filename (`index.md`, `log.md`) follows its defined structure when present: the bundle-root `index.md` MAY carry frontmatter and MUST declare `okf_version: "0.2"` when it does; every other `index.md` carries no frontmatter; `log.md` is newest-first with ISO 8601 dates. (The root-`index.md` `okf_version` requirement has no dedicated E/W class — the deterministic runner checks it and reports it unnumbered; report agent-side findings for it the same way.)

### Error classes (E1–E4)

| Class | Condition |
|---|---|
| `E1` | A non-reserved `.md` file has no YAML frontmatter |
| `E2` | A frontmatter block is missing a `type` field, or it is empty |
| `E3` | A reserved file violates its structure — a non-root `index.md` with frontmatter |
| `E4` | An `Attested Computation` concept is missing its required `runtime` field |

### Warning classes (W1–W7)

| Class | Condition |
|---|---|
| `W1` | Missing recommended `title` or `description` field |
| `W2` | Broken cross-link in a file (see Check 2 for the forward-ref vs broken-link split) |
| `W3` | No `generated` field on a page that still carries a legacy v0.1 `timestamp` field — migrate `timestamp` to `generated`. A page with neither `generated` nor a legacy `timestamp` is a fresh page, not a W3 finding |
| `W4` | No `index.md` in a directory |
| `W5` | `log.md` dates not in ISO 8601 form |
| `W6` | A `sources` entry is missing its `resource` field |
| `W7` | `stale_after` has passed — content is stale |

### Out-of-scope zones

Skip `_`-prefixed directories (`_raw/`, `_staging/`, `_archives/`, `_readouts/`, `_meta/`, `_cache/`), `_`-prefixed files (`_insights.md`), and dot-files/dot-directories (`.manifest.json`, `.obsidian/`, `.git/`) in every check — the same filter `scripts/validate.sh` applies. These hold frozen snapshots, unprocessed staging drafts, operational caches, and derived readouts (saved by `wiki-narrate`) — they are not knowledge-graph pages, so orphan, frontmatter, and link checks don't apply to them.

## Lint Checks

Run these checks in order. Report findings as you go. Conformance classes (E1–E4, W1–W7) and health findings land in one combined Bundle Health Report. The out-of-scope filter above applies to every check.

### 1. Orphaned Pages

Find pages with zero incoming links. These are knowledge islands that nothing connects to.

**How to check:**
- Glob all `.md` files in the bundle (in-scope zones only)
- For each page, Grep the rest of the bundle for file-relative links whose target resolves to it
- Pages with zero incoming links (except `index.md` and `log.md`) are orphans

**How to fix:**
- Identify which existing pages should link to the orphan
- Add file-relative markdown links in appropriate sections

### 2. Broken Links (W2)

Find markdown links `[display](./path.md)` whose target page doesn't exist. Split every finding into one of two subclasses — they have opposite dispositions:

- **`forward-ref` (legal, informational).** A link to a not-yet-written page: the target is a plausible future page (naming is consistent with the bundle's slug conventions, the linking context says "see also" / "planned" / "to be written", or the target appears in an index or `relationships:` block as a declared intention). Forward-references are legal OKF — consumers must accept broken links — and they survive migration. Report them under a separate `forward-ref` heading as warning-level informational findings; track them until the target is written. Never delete or rewrite a forward-ref just because the target doesn't exist yet.
- **`broken-link` (actionable).** The target is obviously typo'd or nonexistent anywhere in the bundle: a fuzzy match against existing filenames/titles finds a close candidate (edit distance ≤ 2 or same root word), or no page by that name was ever planned. These are real W2 findings to fix.

**How to check:**
- Grep for markdown links (`\]\(.*?\.md\)`) across all in-scope pages
- Extract the link targets, resolve them relative to each linking file
- Check whether a corresponding `.md` file exists; classify each miss as `forward-ref` or `broken-link`

**How to fix:**
- `forward-ref`: leave the link; list it so the owner knows what's planned
- `broken-link`: if the target was renamed, update the link; if the target should exist, create it; if the link is wrong, remove or correct it

**Migration residue:** legacy wikilinks (`[[path/to/page]]`) appear only in bundles migrated from an obsidian-wiki source vault — the migrator converts them to file-relative markdown links (conversion table in `.skills/okf-wiki/SKILL.md` §Link Format). Raw wikilinks in a bundle page are migration residue: flag them and convert them the same way the migrator would.

### 3. Missing Frontmatter (E1 / E2)

OKF v0.2 requires every non-reserved page to carry parseable YAML frontmatter with a non-empty `type`. The canonical field set — `type` (TitleCase), `title`, `description`, `tags`, `generated`, `status`, `stale_after`, `sources`, plus the §4.1 extension fields — is defined once in `.skills/okf-wiki/SKILL.md` §Canonical Frontmatter; reference it, do not re-derive the mapping here.

**How to check:**
- Grep frontmatter blocks (scope to `^---` at file heads) instead of reading every page in full
- No frontmatter block → `E1`; frontmatter present but `type` missing/empty → `E2`
- Flag pages missing recommended fields (`title`, `description`) as `W1`

**How to fix:**
- Add the missing fields following the canonical frontmatter template in `.skills/okf-wiki/SKILL.md` §Schema

### 3a. Missing Description (soft warning)

Every page *should* have a `description:` frontmatter field — 1–2 sentences, ≤200 chars. This is what cheap retrieval (e.g. `wiki-query`'s index-only mode) reads to avoid opening page bodies. (`description` is the OKF successor of the source project's `summary` field.)

**How to check:**
- Grep frontmatter for `^description:` across the bundle
- Flag pages without it, **but as a soft warning, not an error** — older pages predating this field are fine; the check exists to nudge ingest skills into filling it on new writes.
- Also flag pages whose description exceeds 200 chars.

**How to fix:**
- Re-ingest the page, or manually write a short description (1–2 sentences of the page's content).

### 4. Stale Content (W7)

Staleness is written into frontmatter at write time: `stale_after = updated + 90 days`, recomputed on every write. `stale_after` is an absolute instant, not a TTL — a page is stale when `now >= stale_after`.

**How to check:**
- Grep frontmatter for `^stale_after:`; flag pages where the instant has passed → `W7`
- Additionally compare the `updated` extension field to source file modification times (`last_modified` in the `sources:` entries, or the raw source files tracked in `.manifest.json`) — flag pages where sources changed after the page was last updated even if `stale_after` hasn't passed yet

**How to fix:**
- Re-ingest from the changed sources; a re-ingest bumps `updated` and recomputes `stale_after`, which clears the finding automatically. Never edit `stale_after` by hand to silence the warning.

### 5. Contradictions

Claims that conflict across pages.

**How to check:**
- This requires reading related pages and comparing claims
- Focus on pages that share tags or are heavily cross-referenced
- Look for phrases like "however", "in contrast", "despite" that may signal existing acknowledged contradictions vs. unacknowledged ones
- Pages already linked by a `contradicts` relationship are acknowledged — check only that the callout exists (see Action 6)

**How to fix:**
- Add an "Open Questions" section noting the contradiction
- Reference both sources and their claims

### 6. Index Consistency (W4)

Verify `index.md` matches the actual page inventory, and that every category directory has one.

**How to check:**
- Compare pages listed in the root `index.md` and per-directory `index.md` files to actual files on disk
- Check that descriptions in `index.md` still match page content
- A category directory with no `index.md` → `W4`

**How to fix:**
- Add or update the missing `index.md` (per-dir index files carry no frontmatter — links plus one-line descriptions only)

### 7. Provenance Drift

Check whether pages are being honest about how much of their content is inferred vs extracted. See the provenance markers convention in `.skills/okf-wiki/SKILL.md`.

**How to check:**
- For each page with a `provenance:` block or any `^[inferred]`/`^[ambiguous]` markers, count sentences/bullets and how many end with each marker
- Compute rough fractions (`extracted`, `inferred`, `ambiguous`)
- Apply these thresholds:
  - **AMBIGUOUS > 15%**: flag as "speculation-heavy" — even 1-in-7 claims being genuinely uncertain is a signal the page needs tighter sourcing or should be moved to `synthesis/`
  - **INFERRED > 40% with no `sources:` in frontmatter**: flag as "unsourced synthesis" — the page is making connections but has nothing to cite
  - **Hub pages** (top 10 by incoming-link count) with INFERRED > 20%: flag as "high-traffic page with questionable provenance" — errors on hub pages propagate to every page that links to them
  - **Drift**: if the page has a `provenance:` frontmatter block, flag it when any field is more than 0.20 off from the recomputed value
- **Skip** pages with no `provenance:` frontmatter and no markers — treated as fully extracted by convention

**How to fix:**
- For ambiguous-heavy: re-ingest from sources, resolve the uncertain claims, or split speculative content into a `synthesis/` page
- For unsourced synthesis: add `sources:` (each entry with its `resource`) to frontmatter or clearly label the page as synthesis
- For hub pages with INFERRED > 20%: prioritize for re-ingestion — errors here have the widest blast radius
- For drift: update the `provenance:` frontmatter to match the recomputed values

### 8. Fragmented Tag Clusters

Checks whether pages that share a tag are actually linked to each other. Tags imply a topic cluster; if those pages don't reference each other, the cluster is fragmented — knowledge islands that should be woven together.

**How to check:**
- For each tag that appears on ≥ 5 pages (user tags only — `visibility/*` system tags are excluded):
  - `n` = count of pages with this tag
  - `actual_links` = count of links between any two pages in this tag group (check both directions)
  - `cohesion = actual_links / (n × (n−1) / 2)`
- Flag any tag group where cohesion < 0.15 and n ≥ 5

**How to fix:**
- Run the `cross-linker` skill targeted at the fragmented tag — it will surface and insert the missing links
- If a tag group is large (n > 15) and still fragmented, consider splitting it into more specific sub-tags

### 9. Visibility Tag Consistency

Checks that `visibility/` tags are applied correctly and aren't silently missing where they matter.

**How to check:**

- **Untagged PII patterns:** Grep page bodies for patterns that commonly indicate sensitive data — lines containing `password`, `api_key`, `secret`, `token`, `ssn`, `email:`, `phone:` followed by an actual value (not a field description). If a page matches and lacks `visibility/pii` or `visibility/internal`, flag it as a likely mis-classification.
- **`visibility/pii` without `sources:`:** A page tagged `visibility/pii` should always have a `sources:` frontmatter field — if there's no provenance, there's no way to verify the classification. Flag any `visibility/pii` page missing `sources:`.
- **Visibility tags in taxonomy:** `visibility/` tags are system tags and must **not** appear in `_meta/taxonomy.md`. If found there, flag as misconfigured — they'd be counted toward the 5-tag limit on pages that include them.

**How to fix:**
- For untagged PII patterns: add `visibility/pii` (or `visibility/internal` if it's team-context rather than personal data) to the page's frontmatter tags
- For missing `sources:`: add provenance or escalate to the user — don't auto-fill
- For taxonomy contamination: remove the `visibility/` entries from `_meta/taxonomy.md`

### 10. Misc Promotion Candidates

> **Legacy note:** `misc/`, `affinity`, and `promotion_status` are concepts carried over from the source project's vault layout. They appear in **migrated bundles** (via `migrate-vault.sh`); a native okf-wiki bundle files pages correctly at creation, so this check is typically a no-op there. Run it only when `$OKF_BUNDLE_PATH/misc/` exists.

Find pages in `misc/` that have accumulated enough project affinity to be promoted.

**How to check:**
- Glob `$OKF_BUNDLE_PATH/misc/*.md`
- For each page, read the `affinity` frontmatter field
- Flag pages where any single project's score ≥ 3

**How to fix:**
- Run the `cross-linker` skill first if affinity scores look stale (e.g., `affinity: {}` on a page with many links)
- To promote: move the page to `projects/<project-name>/references/` (or another appropriate directory), update its `type` frontmatter, remove `promotion_status`, and grep the bundle for backlinks to update them

### 12. Trust and Lifecycle Schema

Enforces the trust + lifecycle frontmatter schema (see `.skills/okf-wiki/SKILL.md`, §Required trust/lifecycle fields and §Human-only lifecycle invariant).

Two modes:
- **default (read-only)** — reports errors and warnings
- **`OKF_TRUST_STRICT`** — trust/lifecycle findings become hard failures (see Rule 12e)

Confidence is a semantic judgment. A deterministic tool cannot infer independent evidence lineages or whole-page claim coverage from source strings alone. Confidence automation therefore validates an explicitly approved manual trust ledger; it never substitutes URL counting for review.

#### Rule 12a — `status` enum validation

**How to check:** Grep frontmatter for `^status:` across all pages. Flag any value outside the effective status set (framework default: `{draft, stable, deprecated}`). The `lifecycle: disputed` extension may coexist with any status except `deprecated` — validate it only against `OKF_ALLOWED_LIFECYCLES` owner extensions.

**How to fix:** n/a (only a human should change lifecycle state)

#### Rule 12b — `base_confidence` range

**How to check:** Grep frontmatter for `^base_confidence:` across all pages. Flag any present value outside `[0.0, 1.0]`; flag absence when the effective schema requires it — the framework default requires `base_confidence` and `status` (see Current enforcement below), and `OKF_REQUIRED_TRUST_FIELDS` may relax or extend that default.

**How to fix:** n/a (wrong value means the skill computed it wrong — surface for manual correction)

#### Rule 12c — Stale page report (computed overlay)

Staleness is never stored as a state — it is computed at read time from `stale_after` (equivalently `updated + 90d`).

**How to check:** For each page, read `stale_after:` (or recompute from `updated:`) and determine staleness. If stale, also check `status:` and `verified:`. Report:
- Stale pages that are human-verified (`status: stable` with a `verified:` entry) with a louder annotation (these are the most dangerous — high-trust pages that may be wrong)
- All other stale pages as a standard warning

**How to fix:** `--consolidate` does **not** rewrite `status`. Staleness clears automatically when a re-ingest bumps `updated` and recomputes `stale_after`.

#### Rule 12c-2 — Illegal lifecycle transitions

The status enum is a state machine with a human-only trust boundary, not a free-form label. Report `illegal_lifecycle_transitions` by comparing each page's current state against the value recorded in `_meta/trust-ledger.json` at its last review, and by checking the actor on every trust-bearing field:

**Flagged:**
- Any `status: stable` page whose promotion is not backed by a human actor — `draft → stable` and every `verified:` entry are performed ONLY by `human:<id>` (see `.skills/okf-wiki/SKILL.md` §Human-only lifecycle invariant). A `verified[].by` holding a producer (`<producer>/<version>`) or `process:<id>` actor is an illegal transition.
- Any state falling back to `draft` after review (only ingest sets `draft`).
- Any exit from `deprecated` (terminal — a restore is a deliberate human delete-and-recreate).

**Not flagged:**
- Agent deprecation via `status: deprecated` + `superseded_by` — legal for agents, provided it went through `wiki-stage-commit` when staged writes are enabled (`WIKI_STAGED_WRITES`). Flag it only if `log.md` shows the change without a stage-commit record.
- Ledger snapshots are sparse, so a legitimate intermediate state may have happened between two reviews; flagging it would fire on valid history.

Warns by default; fails under `OKF_TRUST_STRICT`. Pages whose ledger entry predates the `status` field have no baseline and are skipped silently.

**How to fix:** n/a — a page that moved along a forbidden edge means either a skill wrote trust state when it shouldn't have, or a human transition needs recording. Surface for human resolution.

#### Rule 12d — Supersession integrity

**How to check:** For each page with `superseded_by: "./target.md"` (a file-relative link):
- Verify the target page exists
- Verify the target page is not itself `deprecated` (no circular or chained supersession)
- Verify there are no cycles (A supersedes B which supersedes A)
- Warn if `status != deprecated` while `superseded_by` is set (inconsistent state)

**How to fix:** n/a — flag for human resolution

#### Rule 12e — Confidence review integrity

The deterministic ledger check validates `_meta/trust-ledger.json` against the bundle. okf-wiki has no CLI for this — the agent performs the check directly:

1. Read `_meta/trust-ledger.json` (out-of-scope zone — read it as operational data, never lint it as a page).
2. For each entry, compare the recorded material fingerprint inputs — body, description, sources, provenance, tags, relationships — against the page's current content. The fingerprint excludes volatile bookkeeping (`updated`, `base_confidence`, and lifecycle transition fields), so timestamp-only edits do not reopen review.
3. Classify each page:
   - `reviewed` — current material content and stored score both match the approved review; do **not** recompute from source strings.
   - `stale` — body, description, sources, provenance, tags, or relationships changed; a new manual lineage + claim-coverage review is required.
   - `unreviewed` — page has no approved ledger entry; manual review is required.
   - `score_mismatches` — material content still matches, but stored `base_confidence` differs from the approved value; fail the lint.
   - `errors` — malformed/missing ledger data; fail the lint.

Under `OKF_TRUST_STRICT`, `stale`, `unreviewed`, and missing-page findings return as hard failures; without it they remain warnings, and only hard ledger errors or score mismatches fail the lint.

The approved ledger lives at `_meta/trust-ledger.json`. Each entry records the human-reviewed score plus a SHA-256 fingerprint of material page content and evidence metadata. A ledger refresh means a human approved every score being recorded. It is a workflow assertion, not a cryptographic signature: keep the ledger under version control and require human diff review before merging ledger changes. Never refresh the ledger merely to silence warnings.

**Manual recomputation protocol for stale/unreviewed pages:**

1. Decompose the page into material claims and map each claim to evidence.
2. Collapse dependent evidence into independent lineages: files/commits from one repository, retries in one task chain, snapshots plus their captured source, duplicate memories, and parent/child tasks each count once.
3. Assign reviewed quality per independent lineage using the source-quality buckets in `.skills/okf-wiki/SKILL.md` §Confidence formula.
4. Compute the raw base score, then assess whole-page claim coverage. The formula is a starting point, not an automatic target.
5. Classify the result as `raise`, `keep`, `lower`, or `repair first`; require approval before changing `base_confidence` or refreshing the ledger.

**How to fix:** There is no automatic confidence fix. Apply only an explicitly approved exact patch, verify its scope, then refresh only the reviewed ledger state. `--consolidate` must never rewrite `base_confidence`.

#### Current enforcement

Under framework defaults, every non-reserved content page must contain a finite `base_confidence` in `[0.0, 1.0]` and a documented `status` value — unless `OKF_REQUIRED_TRUST_FIELDS` relaxes requiredness; present values remain validated. Missing or malformed trust fields, malformed ledger data, and a missing required ledger are hard errors. New pages with valid trust fields but no approved ledger entry are `unreviewed`; material changes to approved pages are `stale`.

#### Output additions

Add to the Bundle Health Report:

```markdown
### Trust/Lifecycle Issues (N found)
- `concepts/foo.md` — missing `status` field (warning)
- `entities/bar.md` — `status: stalestate` is not a valid enum value
- `concepts/scaling.md` — `base_confidence: 1.4` is out of range [0.0, 1.0]
- `synthesis/old-analysis.md` — STALE (stale_after 2026-03-01 passed, 182 days) status=stable verified ⚠️ HIGH PRIORITY
- `concepts/outdated.md` — STALE (stale_after 2026-05-15 passed, 137 days) status=draft
- `entities/tool-v1.md` — `superseded_by: ./tool-v2.md` but status=draft (expected deprecated)
- `concepts/selfpromoted.md` — ILLEGAL TRANSITION: status=stable but verified[].by=claude/2.5.0 (human:<id> required)
- `concepts/drift-example.md` — confidence review stale: material fingerprint changed; manual lineage + coverage review required
- `entities/mismatch.md` — confidence mismatch: stored=0.80, approved=0.59
```

Append to the `LINT` log entry:
```
- [TIMESTAMP] LINT ... lifecycle_issues=N
```

### 13. Typed Relationships Validity

Validate `relationships:` frontmatter blocks. Skip pages that have no `relationships:` block — the field is an optional §4.1 extension.

**Framework-default types:** `extends`, `implements`, `contradicts`, `derived_from`, `uses`, `replaces`, `related_to`. Validate against the effective set after applying `OKF_ALLOWED_RELATIONSHIP_TYPES` owner extensions.

**How to check:**
- Grep frontmatter for `^relationships:` across all in-scope pages
- For each page that has a `relationships:` block, read its frontmatter (not the full page body)
- For each entry in the block:
  1. **Type validation** — flag any `type:` value not in the allowed set above
  2. **Broken target** — resolve the `target:` file-relative path against the page's directory and check whether a `.md` file exists there. Flag unresolved targets — but apply the Check 2 split first: a declared intention to a not-yet-written page is a `forward-ref`, a typo'd path is a `broken-link`.
  3. **Self-reference** — flag any entry where the resolved target equals the page's own path

**How to fix:**
- Invalid type: report the value and effective schema source. Correct it only if it is absent from both framework defaults and owner extensions; never replace a valid owner type with `related_to`.
- Broken target: update or remove the entry; if the target page should exist, create it first
- Self-reference: remove the entry

**Output additions:**

```markdown
### Typed Relationship Issues (N found)
- `concepts/foo.md` — relationships[1]: type "contradication" is not an allowed type (did you mean "contradicts"?)
- `concepts/bar.md` — relationships[0]: target "./skills/nonexistent-skill.md" resolves to no page in bundle
- `entities/baz.md` — relationships[2]: self-reference (target resolves to this page's own path)
```

Append to the `LINT` log entry:
```
... relationship_issues=N
```

### 11. Synthesis Gaps

Identify high-value synthesis opportunities the bundle is missing — concept pairs that co-occur across many pages but have no `synthesis/` page connecting them.

**How to check:**
- List all pages in `synthesis/` — collect the concept pairs each one already covers (from its links or title)
- Pick 10-15 frequently linked concepts from `concepts/` and `entities/`
- For each pair, run a quick grep to count pages that link to both:
  ```bash
  rg -l --glob '*.md' "concepts/concept-a\.md" "$OKF_BUNDLE_PATH" > /tmp/a.txt
  rg -l --glob '*.md' "concepts/concept-b\.md" "$OKF_BUNDLE_PATH" > /tmp/b.txt
  comm -12 <(sort /tmp/a.txt) <(sort /tmp/b.txt) | wc -l
  ```
- Flag pairs with co-occurrence ≥ 3 that have no existing synthesis page

**How to fix:**
- Run `/wiki-synthesize` to automatically discover and fill the top gaps

## Output Format

Report findings as a structured list:

```markdown
## Bundle Health Report

### Conformance (okflint | validate.sh — exit N)
- E-class errors: N, W-class warnings: M (details verbatim from the deterministic run)

### Forward-References (N found — legal, informational)
- `concepts/foo.md:15` — links to ./concepts/planned-page.md (not yet written)

### Broken Links (N found)
- `entities/bar.md:15` — links to ./entites/typo-page.md (closest match: ../entities/type-page.md)

### Orphaned Pages (N found)
- `concepts/foo.md` — no incoming links

### Missing Frontmatter (N found)
- `skills/baz.md` — E1: no frontmatter
- `references/paper-x.md` — E2: empty `type`

### Stale Content (N found)
- `references/paper-x.md` — W7: stale_after 2026-01-05 passed; source modified 2026-03-10

### Contradictions (N found)
- `concepts/scaling.md` claims "X" but `synthesis/efficiency.md` claims "not X"

### Index Issues (N found)
- `concepts/new-page.md` exists on disk but not in index.md
- `entities/` — W4: no index.md

### Missing Description (N found — soft)
- `concepts/foo.md` — no `description:` field
- `entities/bar.md` — description exceeds 200 chars

### Provenance Issues (N found)
- `concepts/scaling.md` — AMBIGUOUS > 15%: 22% of claims are ambiguous (re-source or move to synthesis/)
- `entities/some-tool.md` — drift: frontmatter says inferred=0.10, recomputed=0.45
- `concepts/transformers.md` — hub page (31 incoming links) with INFERRED=28%: errors here propagate widely
- `synthesis/speculation.md` — unsourced synthesis: no `sources:` field, 55% inferred

### Fragmented Tag Clusters (N found)
- **#systems** — 7 pages, cohesion=0.06 ⚠️ — run cross-linker on this tag
- **#databases** — 5 pages, cohesion=0.10 ⚠️

### Visibility Issues (N found)
- `entities/user-records.md` — contains `email:` value pattern but no `visibility/pii` tag
- `concepts/auth-flow.md` — tagged `visibility/pii` but missing `sources:` frontmatter
- `_meta/taxonomy.md` — contains `visibility/internal` entry (system tag must not be in taxonomy)

### Misc Promotion Candidates (N found)
Pages in misc/ that have ≥ 3 connections to a single project and are ready to be promoted:

| Page | Top Project | Affinity Score |
|---|---|---|
| `misc/web-martinfowler-articles-microservices.md` | `my-project` | 4 |

### Typed Relationship Issues (N found)
- `concepts/foo.md` — relationships[1]: type "contradication" is not an allowed type
- `concepts/bar.md` — relationships[0]: target "./skills/nonexistent.md" resolves to no page

### Trust/Lifecycle Issues (N found)
(see Rule 12 output additions)

### Synthesis Gaps (N found)
Concept pairs that co-occur frequently but have no synthesis page:

| Pair | Co-occurrence | Suggested Action |
|---|---|---|
| [Caching](./concepts/caching.md) × [Consistency](./concepts/consistency.md) | 5 pages | Run `/wiki-synthesize` |
| [Testing](./concepts/testing.md) × [Observability](./concepts/observability.md) | 3 pages | Run `/wiki-synthesize` |
```

## After Linting

Append to `log.md` (newest-first):
```
- [TIMESTAMP] LINT issues_found=N conformance_errors=E conformance_warnings=W orphans=X broken_links=Y forward_refs=FR stale=Z contradictions=W prov_issues=P missing_description=S fragmented_clusters=F visibility_issues=V promotion_candidates=C synthesis_gaps=G relationship_issues=R lifecycle_issues=L
```

Offer to fix issues automatically or let the user decide which to address.

If `LINT_SCHEDULE` is set to `daily` or `weekly` (see `.skills/daily-update/SKILL.md`), this skill runs as part of that cadence automatically; `LINT_SCHEDULE=manual` means it runs only when invoked. Scheduled runs stay report-only — `--consolidate` is always an explicit, interactive invocation.

---

## Consolidate Mode (`--consolidate`)

Triggered by `wiki-lint --consolidate`. Switches from report-only to **act-and-report** — the "dream cycle" that runs periodically so the bundle self-heals.

### Safety protocol

**Always run in dry-run first.** Before writing anything:

1. Run all lint checks above.
2. Print the planned consolidation actions as a structured list (see Dry-Run Output below).
3. Ask the user: `"Apply these N changes? [yes / no / select]"`.
4. Only proceed with writes after explicit confirmation. If the user selects individual actions, apply only those.
5. Never merge pages — use `wiki-dedup` for that. Only link, promote, demote, and flag.
6. Never touch trust state: `--consolidate` never promotes `status`, never adds `verified:` entries, and never rewrites `base_confidence` — those are human-only (see Rule 12c-2).

### Consolidation actions (in order, after confirmation)

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
    if ! git -C "$OKF_BUNDLE_PATH" commit -m "pre-wiki-lint snapshot" --quiet; then
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

#### Action 1: Fix broken links (broken-link subclass only)

For each `broken-link` finding from Check 2 (forward-refs are left untouched — they are legal):
- Search the bundle for a page whose title or filename is the closest fuzzy match (use `Grep` across `index.md` titles)
- If a unique best match exists (edit distance ≤ 2 characters or same root word): rewrite the link target. Note the rewrite: `./oringal-page.md → ./corrected-page.md`.
- If no match or ambiguous: convert to plain text (drop the link markup, keep the display text) and add a comment `<!-- broken link: no match found -->`.
- Never create a new page just to satisfy a broken link — creating the target is a decision for the owner (or the link stays as a forward-ref).

#### Action 2: Add missing cross-references for orphans

For each orphan page found in Check 1 (zero incoming links):
- Grep the bundle body text for mentions of the page's title or aliases (case-insensitive).
- For each mention found in another page, add a file-relative markdown link replacing the plain-text mention.
- Limit to 3 insertions per orphan — don't flood pages with links.
- This is scoped to orphans only (different from `cross-linker` which runs broadly).

#### Action 3: Lifecycle maintenance (human-gated)

The `draft → stable` transition and every `verified:` entry are human-only — `--consolidate` never applies them. Instead:

- **Flag promotion candidates:** pages where `status: draft` AND `generated.at` > 30 days ago AND `base_confidence > 0.7` go on a "ready for human review" list in the consolidation report. The owner promotes them manually (setting `status: stable` as `human:<id>`).
- **Stale callouts:** for human-verified pages (`status: stable` with a `verified:` entry) where `is_stale = (today − updated) > 180 days`, add a callout at the top of the page body: `> ⚠️ **Stale**: This page was last updated <date>. Verify before relying on it.` Only add if the callout isn't already present.
- **Agent deprecation:** setting `status: deprecated` + `superseded_by` is legal for agents, but must go through `wiki-stage-commit` when staged writes are enabled (`WIKI_STAGED_WRITES`). Outside staged mode, list proposed deprecations for human approval instead of writing them.
- **Do not change any other transition** — those are human-only.

#### Action 4: Tier demotion

For pages with `tier: supporting` (or unset) that have 0 incoming links AND haven't been updated in 90+ days:
- Set `tier: peripheral`.
- Emit a list of demotions for the user to review.
- Do not demote `tier: core` pages automatically — those were manually set.

#### Action 5: Tag normalization

Read `_meta/taxonomy.md` for the alias mapping (e.g., `ml → machine-learning`). For each page, replace known alias tags with their canonical form in the `tags:` frontmatter field. This is a subset of `tag-taxonomy`'s work — only alias fixes, no full audit. `visibility/*` system tags are never touched.

#### Action 6: Contradiction callouts

For each pair of pages marked as contradicting each other (via `relationships: contradicts` in frontmatter, or flagged in Check 5):
- Check whether a `> ⚠️ Contradiction flagged with [Other Page](../concepts/other-page.md)` callout already exists near the relevant claim.
- If not, add it at the end of the "Key Ideas" section (or before "Open Questions" if no "Key Ideas" section). Keep it concise — one line.
- Do not resolve the contradiction; only flag it visually.

### Action 7: Write consolidation report

After all actions, write a report to `synthesis/consolidation-<YYYY-MM-DD>.md` with canonical frontmatter (see `.skills/okf-wiki/SKILL.md` §Canonical Frontmatter):

```markdown
---
type: Synthesis
title: Consolidation Report <YYYY-MM-DD>
description: Auto-generated consolidation report from wiki-lint --consolidate run on <date>.
tags: [maintenance, consolidation]
generated:
  by: okf-wiki/<version>
  at: <ISO timestamp>
status: draft
stale_after: <generated.at + 90d>
sources: []
updated: <ISO timestamp>
tier: peripheral
---

# Consolidation Report — <YYYY-MM-DD>

## Summary
- Broken links fixed: N
- Forward-references left open: FR
- Cross-references added: M
- Promotion candidates flagged for human review: K
- Tier demotions: D
- Tags normalized: T
- Contradiction callouts added: C

## Broken Link Fixes
- `concepts/foo.md:12` — ./old-target.md → ./correct-target.md
- `entities/bar.md:8` — ./missing.md → plain text (no match found)

## Forward-References Tracked
- `concepts/baz.md` — ./concepts/planned-page.md (not yet written)

## Cross-References Added (orphan rescue)
- `concepts/baz.md` — now linked from: concepts/alpha.md, skills/beta.md

## Promotion Candidates (human review required)
- `concepts/old-draft.md` — draft, age 45d, confidence 0.74 — ready for human promotion to stable

## Stale Callouts
- `synthesis/stale-verified.md` — stale callout added (last updated 2026-03-01)

## Tier Demotions
- `concepts/unused-concept.md` — supporting → peripheral (0 links, 120 days stale)

## Tag Normalizations
- `entities/some-tool.md` — `ml` → `machine-learning`

## Contradiction Callouts
- `concepts/scaling.md` — flagged contradiction with synthesis/efficiency.md
```

### Dry-Run Output (shown before any writes)

```
wiki-lint --consolidate — Dry Run

Planned actions (N total):
[1] Fix broken link: concepts/foo.md:12 ./old-target.md → ./correct-target.md
[2] Add cross-ref: concepts/baz.md ← concepts/alpha.md (orphan rescue)
[3] Flag for human review: concepts/old-draft.md (draft, age 45d, confidence 0.74)
[4] Tier demotion: concepts/unused.md → peripheral (0 links, 112 days stale)
[5] Tag alias: entities/some-tool.md: ml → machine-learning
[6] Contradiction callout: concepts/scaling.md ↔ synthesis/efficiency.md

Apply these 6 changes? [yes / no / select by number]
```

### Log entry for consolidate mode

```
- [TIMESTAMP] LINT_CONSOLIDATE links_fixed=N forward_refs_open=FR orphans_rescued=M promotion_candidates=K tier_demotions=D tag_fixes=T contradiction_callouts=C report=synthesis/consolidation-YYYY-MM-DD.md
```

## QMD Refresh After Bundle Writes

QMD is a search index, not the source of truth. If `$QMD_WIKI_COLLECTION` is empty or unset, skip this step. Run it only after this skill has written or rewritten bundle markdown. If QMD refresh fails, do not roll back the bundle changes; report the QMD status separately.

Use `$QMD_CLI` if set; otherwise use `qmd`.

```bash
${QMD_CLI:-qmd} update
```

If the output says vectors are needed or embeddings may be stale, run:

```bash
${QMD_CLI:-qmd} embed
```

Verify the collection with either:

```bash
${QMD_CLI:-qmd} ls "$QMD_WIKI_COLLECTION"
```

or, when a specific page path is known:

```bash
${QMD_CLI:-qmd} get "qmd://$QMD_WIKI_COLLECTION/<page>.md" -l 5
```

Record one of:
- `QMD refreshed: update + embed + verified`
- `QMD refreshed: update only + verified`
- `QMD skipped: QMD_WIKI_COLLECTION unset`
- `QMD skipped: qmd CLI unavailable`
- `QMD failed: <short error summary>`

---

Derived from Ar9av/obsidian-wiki wiki-lint skill (MIT).
