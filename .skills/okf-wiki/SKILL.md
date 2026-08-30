---
name: okf-wiki
description: >
  The foundational knowledge distillation pattern for building and maintaining an AI-powered
  OKF (Open Knowledge Format) knowledge bundle. Based on Andrej Karpathy's LLM Wiki architecture,
  rewritten from the llm-wiki skill of Ar9av/obsidian-wiki. Use this skill whenever the user wants
  to understand the wiki pattern, set up a new knowledge base, or needs guidance on the three-layer
  architecture (raw sources → bundle → schema). Also use when discussing knowledge management
  strategy, bundle structure decisions, or how to organize distilled knowledge. This is the
  "theory" skill — other skills handle specific operations (ingesting, querying, linting).
---

# OKF Wiki — Knowledge Distillation Pattern

You are maintaining a persistent, compounding knowledge base. The bundle is not a chatbot — it is a **compiled artifact** where knowledge is distilled once and kept current, not re-derived on every query. Unlike the source project, the knowledge base is natively an **OKF v0.2 bundle** (Open Knowledge Format): a directory of markdown files that any agent and any human can read, extend, and transfer between tools without conversion. Producer and consumer are independent; trust and provenance are first-class fields of the format.

## Three-Layer Architecture

### Layer 1: Raw Sources (immutable)

The user's original documents — articles, papers, notes, PDFs, conversation logs, bookmarks, **and images** (screenshots, whiteboard photos, diagrams, slide captures). These are never modified by the system. They live wherever the user keeps them (configured via `OKF_SOURCES_DIR` in `.env`). Images are first-class sources: the ingest skills read them via the Read tool's vision support and treat their interpreted content as inferred unless it's verbatim transcribed text. Image ingestion requires a vision-capable model — models without vision support should skip image sources and report which files were skipped.

Think of raw sources as the "source code" — authoritative but hard to query directly.

Don't confuse this with the in-bundle `_raw/` staging folder, which is a different thing: a scratch inbox for quick captures and drafts awaiting promotion (see `wiki-capture` and `wiki-ingest`). Files there aren't Layer 1 sources, but `wiki-ingest` still moves rather than deletes them on promotion, since some have no other copy. `_raw/` is outside OKF conformance scope (see *Out-of-Scope Convention*).

### Layer 2: The Bundle (agent-maintained)

A collection of interconnected OKF v0.2 markdown files organized by category. This is the compiled knowledge — synthesized, cross-referenced, and navigable. Each page has:

- YAML frontmatter (`type`, `title`, `description`, `tags`, `sources`, `generated`, `status`, timestamps)
- Standard markdown links connecting related concepts (no wikilinks — see *Link Format*)
- Clear provenance — every claim traces back to a source

The bundle lives at the path configured via `OKF_BUNDLE_PATH` in `.env`. It is conformant with OKF v0.2 at every moment, without a separate "export" step.

### Layer 3: The Schema (this skill + config)

The rules governing how the bundle is structured — categories, the canonical frontmatter mapping, page templates, and operational workflows. The schema tells the LLM *how* to maintain the bundle. This skill is the source of truth; all other skills reference it for the canonical frontmatter mapping and write protocol.

## The Four Ingest Stages

Every time you feed the bundle, it runs through these four stages:

1. **Ingest** — The agent reads the source material directly: markdown, PDFs (with page ranges), JSONL conversation exports, plain text logs, chat exports, meeting transcripts, and images. No preprocessing pipeline — the agent reads the file the same way it reads code.

2. **Pull** — From the raw source, the agent pulls out concepts, entities, claims, relationships, and open questions. Noise gets dropped, signal gets kept. Each page also gets a one-sentence `description` in its frontmatter at write time, so later queries can preview it without opening it.

3. **Merge** — New knowledge merges against what's already there. If a concept page exists, the agent updates it: merging new information, noting contradictions, strengthening cross-references. If it's genuinely new, a page gets created. Nothing is duplicated. Sources are tracked in frontmatter so every claim stays attributable.

4. **Schema** — The schema isn't fixed upfront. It emerges from sources and evolves as more are added. The agent maintains coherence: categories stay consistent, links point to real pages, the index reflects what's actually there. A `.manifest.json` tracks every ingested source, so the next run computes the delta and only processes what changed.

## Bundle Organization

The bundle has two levels of structure: **categories** (what kind of knowledge) and **projects** (where the knowledge came from).

### Categories

Organize pages into these default category directories (customizable in `.env`). The `type` field is the Title-case form of the category, per the canonical mapping:

| Directory | `type` value | Purpose | Example |
|---|---|---|---|
| `concepts/` | `Concept` | Ideas, theories, mental models | `concepts/transformer-architecture.md` |
| `entities/` | `Entity` | People, orgs, tools, projects | `entities/andrej-karpathy.md` |
| `skills/` | `Skill` | How-to knowledge, procedures | `skills/fine-tuning-llms.md` |
| `references/` | `Reference` | Summaries of specific sources; academic papers use the Paper Deep-Dive Template (below) | `references/attention-is-all-you-need.md` |
| `synthesis/` | `Synthesis` | Cross-cutting analysis across sources | `synthesis/scaling-laws-debate.md` |
| `journal/` | `Journal` | Timestamped observations, session logs | `journal/2024-03-15.md` |
| `projects/` | `Project` | Project overview pages (see below) | `projects/my-project.md` |

These seven types are the framework convention, not a closed set. `type` is a free-form string in OKF; a bundle's `AGENTS.md` may extend the vocabulary, and consumers must tolerate unknown types.

### Projects

Knowledge often belongs to a specific project. The `projects/` directory mirrors this:

```
$OKF_BUNDLE_PATH/
├── projects/
│   ├── my-project/
│   │   ├── my-project.md      ← project overview (named after project)
│   │   ├── concepts/          ← project-scoped category pages
│   │   ├── skills/
│   │   └── ...
│   ├── another-project/
│   │   └── ...
│   └── side-project/
│       └── ...
├── concepts/                   ← global (cross-project) knowledge
├── entities/
├── skills/
└── ...
```

**When knowledge is project-specific** (a debugging technique that only applies to one codebase, a project-specific architecture decision), put it under `projects/<project-name>/<category>/`.

**When knowledge is general** (a concept like "React Server Components", a person like "Andrej Karpathy", a widely applicable skill), put it in the global category directory.

**Cross-referencing:** Project pages should link to global pages and vice versa. A project's overview page should link to the key concept, skill, and entity pages relevant to that project — whether they live under the project or globally.

**Naming rule:** The project overview file must be named `<project-name>.md`, not `_project.md`. Naming the file `<project-name>.md` yields clean concept IDs (e.g. `projects/acme/acme`), whereas `_project.md` gives every project an ID ending in `_project` — harder to read and distinguish in the graph. So `projects/my-project/my-project.md`, `projects/another-project/another-project.md`, etc. (Note: a leading `_` would also place the file outside conformance scope — see *Out-of-Scope Convention*.)

Each project directory has an overview page structured like this:

```markdown
---
type: Project
title: My Project
description: One-paragraph summary of what this project is.
tags: [ai, web, backend]
resource: https://github.com/me/my-project
generated: { by: claude/2.5.0, at: 2026-03-01T00:00:00Z }
status: draft
stale_after: 2026-07-05T00:00:00Z
updated: 2026-04-06T00:00:00Z
---

# My Project

One-paragraph summary of what this project is.

## Key Concepts
- [some-api](./concepts/some-api.md) — used for core functionality
- [main-architecture](./concepts/main-architecture.md) — project-specific architecture

## Related
- [some-service](../entities/some-service.md) — deployment platform
```

## Reserved Files

Every bundle has these files. The first two are OKF-reserved; the rest are operational and outside conformance scope.

### `index.md` (bundle root)

The master catalog with progressive disclosure, organized by category. This is the **only** `index.md` permitted to carry frontmatter — and it MUST declare the spec version:

```markdown
---
okf_version: "0.2"
---

# My Bundle

- [Concepts](./concepts/index.md)
- [Entities](./entities/index.md)
- [Skills](./skills/index.md)
- [References](./references/index.md)
- [Synthesis](./synthesis/index.md)
- [Journal](./journal/index.md)
- [Projects](./projects/index.md)
```

Rebuild this after every ingest operation.

### `index.md` (per-directory)

Every category directory has its own `index.md` for progressive disclosure. No frontmatter. One line per concept:

```markdown
# Concepts

- [Transformer Architecture](./transformer-architecture.md) — The dominant architecture for sequence modeling
- [Attention Mechanism](./attention-mechanism.md) — Core building block of transformers
```

Each line is a file-relative link plus the `description` from the linked concept's frontmatter.

### `log.md`

Chronological append-only record tracking every operation. Entries are newest-first under ISO-date headings. Each entry is parseable:

```markdown
# Log

## 2026-08-30
- INGEST source="papers/attention.pdf" pages_created=3 pages_updated=12
- UPDATE page=concepts/transformer-architecture.md
- MIGRATE vault=/path/to/source-vault pages=142

## 2026-08-29
- INGEST source="https://example.com/post" pages_created=1
```

The leading verb is a convention: `INGEST source=... pages_created=N`, `UPDATE page=...`, `MIGRATE ...`.

### `_cache/hot.md`

A ~500-word semantic snapshot of recent activity. Every write skill updates it so the next session can pick up where the last one left off without crawling the whole bundle. `hot.md` is an operational artifact, so it lives in the out-of-scope `_cache/` directory rather than at the bundle root.

### `.manifest.json` (operational, out of scope)

Tracks every source file that has been ingested — path, timestamps, what bundle pages it produced. This is the backbone of the delta system. It is a dot-file, so it sits outside OKF conformance scope (see *Out-of-Scope Convention*). See the `wiki-status` skill for the full schema.

The manifest enables:
- **Delta computation** — what's new or modified since last ingest
- **Append mode** — only process the delta, not everything
- **Audit** — which source produced which bundle page
- **Staleness detection** — source changed but bundle page hasn't been updated

**Canonical source keys.** Source keys MUST be stored in a single canonical form: **absolute paths with `~` and env vars expanded** (e.g. `/Users/me/.claude/projects/.../abc.jsonl`, never `~/.claude/...`). The manifest is keyed by the raw string, so a mix of `~`-relative and absolute keys lets the *same file* be tracked twice — and the delta check then re-ingests an already-processed file because the lookup misses the other-form key. Always expand before you compare against the manifest and before you write a new entry. To repair an existing bundle that already has both forms, run `scripts/manifest.py normalize <bundle>` (merges colliding entries, keeps the newest `ingested_at`).

**Recording provenance.** When you write a manifest entry, populate `pages_created` and `pages_updated` with the bundle-relative page paths that source contributed to. This is what makes re-ingestion (when a source changes) able to find the pages to revisit, instead of guessing.

## Canonical Frontmatter (Schema)

This section is the single source of truth for how obsidian-wiki frontmatter maps to OKF v0.2. Every write skill, the migrator, and lint reference this table — do not duplicate it elsewhere.

### Canonical mapping table

| obsidian-wiki | okf-wiki (OKF v0.2) | Rule |
|---|---|---|
| `category: concepts` … `projects`, `journal` | `type: Concept` / `Entity` / `Skill` / `Reference` / `Synthesis` / `Project` / `Journal` | Title-case derived from category |
| `title` | `title` | verbatim |
| `summary` (≤200 chars) | `description` | verbatim |
| `tags` | `tags` | verbatim; system `visibility/*` tags pass through as-is |
| `created` | `generated.at` + new `generated.by` | `by` = the acting agent's `<producer>/<version>` actor |
| `updated` | extension `updated` | OKF v0.2 has no `updated` field; kept as a §4.1 extension, updated on every write |
| `lifecycle: draft` | `status: draft` | direct |
| `lifecycle: reviewed` | `status: stable` | transition only by a human actor |
| `lifecycle: verified` | `status: stable` + `verified: [{by: human:<id>, at: <ISO>}]` | trust recorded by actor |
| `lifecycle: archived` | `status: deprecated` + extension `superseded_by` | terminal state |
| `lifecycle: disputed` | extension `lifecycle: disputed` | OKF has no analogue; kept as an extension on top of `status` |
| `sources` (obsidian format) | `sources:` v0.2 list | each entry: `resource` required (path/URL/scope descriptor); optional `id`, `title`, `author`, `last_modified` |
| first http(s) source | `resource` | optional, iff URL |
| 90-day staleness rule | `stale_after` | computed at write time: `updated + 90d` |
| `aliases`, `relationships`, `provenance` (fractions), `base_confidence`, `tier`, `lifecycle_changed` | same-name §4.1 extension fields | kept verbatim; any OKF consumer must preserve them |

### Canonical frontmatter template

```yaml
---
type: Concept                      # Title-case of the category: Concept|Entity|Skill|Reference|Synthesis|Project|Journal
title: "OKF Bundle"
description: "A digest ≤200 chars (successor to summary)"
tags: [okf, format]
generated:
  by: claude/2.5.0                 # producer actor: <producer>/<version>; fallback okf-wiki/<version>
  at: 2026-08-30T12:00:00Z
status: draft                      # draft|stable|deprecated; transitions to stable/deprecated and verified: entries are human:<id> only
stale_after: 2026-11-28T12:00:00Z  # = updated + 90d, recomputed on every write
sources:                           # v0.2 list; resource is required in each entry
  - resource: "https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md"
    title: "OKF v0.2 Spec"
# ===== extension fields (OKF §4.1 — any consumer must preserve verbatim) =====
updated: 2026-08-30T12:00:00Z      # updated on every write
aliases: ["knowledge bundle"]
relationships:                     # typed relationships; allowlist below, extensible in $BUNDLE/AGENTS.md
  - type: extends                  # extends|implements|contradicts|derived_from|uses|replaces|related_to
    target: ./references/okf-spec.md
provenance:                        # provenance fractions — value format inherited from the source §Schema
  extracted: 0.72
  inferred: 0.25
  ambiguous: 0.03
base_confidence: 0.8               # format inherited from the source
tier: core                         # format inherited from the source
---
```

The only always-required field in OKF is `type`. Everything else above is either recommended (`title`, `description`, `resource`, `tags`) or a v0.2 trust/lifecycle/provenance field. The `updated`, `aliases`, `relationships`, `provenance`, `base_confidence`, `tier`, and `lifecycle_changed` fields are OKF §4.1 extension fields — a conformant consumer MUST preserve them verbatim on round-trip.

### Human-only lifecycle invariant

The trust and lifecycle state is human-curated. **Transitions from `status: draft` to `status: stable`, and any entry added to the `verified:` list, are performed ONLY by an actor `human:<id>`.** An agent writing `verified: [{by: <producer>/<version>}]` or flipping a page to `stable` on its own is an illegal transition: it is blocked and reported as `illegal_lifecycle_transition`. Agents set `status: draft` on creation and leave promotion to a human. Deprecation with a `superseded_by` link (for example by `wiki-dedup` during a merge) is allowed for agents, but must be staged for human sign-off via `wiki-stage-commit` when staged writes are enabled. `stale_after` is the only agent-managed lifecycle field (computed at write time).

### Actor rule

`generated.by` records the acting agent's producer identity: `<producer>/<version>` (for example `claude/2.5.0`, `reference_agent/gemini-2.5-pro`). When the acting agent cannot determine its own producer/version, the fallback is `okf-wiki/<version>`. `verified[].by` uses `human:<id>` for people and `process:<id>` for automated checks. `process:<id>` actors are recognized when reading external bundles (any OKF producer may use them); okf-wiki's own writes append `verified:` entries only via human actors. The full actor convention is: `<producer>/<version>` for agents, `human:<id>` for people, `process:<id>` for automation.

## Page Template

When creating a new concept page, use this structure:

```markdown
---
type: Concept
title: Page Title
description: One or two sentences, ≤200 chars, so a reader (or another skill) can preview this page without opening it.
tags: [ml, architecture]
generated: { by: claude/2.5.0, at: 2024-03-15T10:30:00Z }
status: draft
stale_after: 2024-06-13T10:30:00Z
sources: [papers/attention.pdf]
updated: 2024-03-15T10:30:00Z
aliases: [alternate name]
relationships:
  - target: ./references/related-concept.md
    type: extends
provenance:
  extracted: 0.72
  inferred: 0.25
  ambiguous: 0.03
base_confidence: 0.65
tier: supporting
---

# Page Title

One-paragraph summary of what this page covers.

## Key Ideas

- The source's central claim, paraphrased directly.
- A generalization the source implies but doesn't state outright. ^[inferred]
- A figure two sources disagree on. ^[ambiguous]

Use file-relative markdown links to connect to related pages.

## Open Questions

Things that are unresolved or need more sources.

## Sources

- [attention-is-all-you-need](./references/attention-is-all-you-need.md) — Original paper
```

## Paper Deep-Dive Template

The generic template suits most sources. **Academic papers are the exception.** For ML/AI/LLM/VLM (and similar) papers landing in `references/`, the substance lives in the architecture, the equations, and the results table — exactly what a terse "Key Ideas" list flattens away. For these, use the richer template below. This is the one place where *"compile, don't retrieve"* yields to a thorough, self-contained walkthrough a reader could study instead of the paper.

Standard markdown renders the needed primitives natively, so no extra tooling is required: Mermaid fenced diagrams, `$$…$$` LaTeX, markdown tables, and `![image](path)` embeds.

Use this template only when the source is an academic paper (arXiv/conference) with load-bearing figures or equations. Everything else uses the generic Page Template above. Frontmatter, provenance markers, trust, lifecycle, and `relationships:` are unchanged — only the body sections differ.

````markdown
---
# ...required frontmatter, same as the generic template; type: Reference...
---

# Paper Title

> One sentence: what's new, plus the headline result.

## Problem & Motivation

What's broken or missing that this paper addresses.

## Method / Architecture

Prose walkthrough. Embed the paper's real architecture figure as the primary
visual (see *Academic papers* in `wiki-ingest` for the PyMuPDF extraction recipe).
Fall back to a Mermaid flowchart only when no figure can be extracted.

![Figure N](./attachments/<slug>-fig1.png)
*Figure N (Author Year): one-line caption.*

## Key Equations

The 1–3 core equations as display math, not backtick code:

$$ \mathcal{L} = \mathbb{E}_{x}\!\left[-\log p_\theta(y \mid z)\right] $$

## Results

Headline numbers as a table, not a comma-separated blob — and embed a key
results/motivating figure (scaling plot, benchmark chart, capability collage)
when the paper has one:

| Method | Benchmark | Metric | Cost |
|---|---|---|---|
| Baseline | … | … | … |
| **This paper** | … | … | … |

![Figure N](./attachments/<slug>-resultsN.png)
*Figure N (Author Year): one-line caption.*

## Limitations

What the paper concedes or sidesteps. Mark reading-between-the-lines as ^[inferred].

## Related

Typed file-relative links to neighbouring work.

## Sources

- Clickable canonical link, e.g. <https://arxiv.org/abs/XXXX.XXXXX>
````

A Mermaid diagram reconstructed from the paper's prose is a synthesis, not a transcription — treat it as `^[inferred]` when the interpretation is non-trivial.

## Provenance Markers

Every claim on a concept page has one of three provenance states. Mark them inline so the reader (and future ingest passes) can tell signal from synthesis.

These are framework defaults. A bundle's `AGENTS.md` may add markers or workflow flags. Preserve owner extensions and treat orthogonal workflow flags separately from the extracted/inferred/ambiguous truth-state axis.

| State | Marker | Meaning |
|---|---|---|
| **Extracted** | *(no marker — default)* | A paraphrase of something a source actually says. |
| **Inferred** | `^[inferred]` suffix | An LLM-synthesized claim — a connection, generalization, or implication the source doesn't state directly. |
| **Ambiguous** | `^[ambiguous]` suffix | Sources disagree, or the source is unclear. |

Example:

```markdown
- Transformers parallelize across positions, unlike RNNs.
- This is why they scale better on modern hardware. ^[inferred]
- GPT-4 was trained on roughly 13T tokens. ^[ambiguous]
```

**Why this syntax:**
- `^[...]` is an inline suffix — it never collides with markdown links or with OKF footnotes `[^source-id]` (which attribute claims to `sources` entries, a distinct mechanism).
- Inline (suffix) so a single bullet stays a single bullet.
- Default = extracted means existing pages without markers stay valid.

**Frontmatter summary:** Optionally surface the rough mix at the page level so the user can scan for speculation-heavy pages without reading them:

```yaml
provenance:
  extracted: 0.72   # rough fraction of sentences/bullets with no marker
  inferred: 0.25
  ambiguous: 0.03
```

These are best-effort numbers written by the ingest skill at create/update time. `wiki-lint` recomputes them and flags drift. The block is optional — pages without it are treated as fully extracted by convention.

**Per-claim source attribution** is separate from truth-state: use OKF footnotes keyed to `sources[].id` (`The table is sharded daily.[^ga4-schema]`), resolving through the matching `sources` entry.

## Typed Relationships

Plain markdown links in page bodies carry no semantic weight — they indicate "related to" but not *how*. The optional `relationships:` frontmatter block adds typed, directional edges to the knowledge graph. It is an OKF §4.1 extension field.

### The `relationships:` block

```yaml
relationships:
  - target: ./transformer-architecture.md
    type: extends
  - target: ./lstm.md
    type: contradicts
  - target: ./attention-mechanism.md
    type: implements
```

Each entry has two required fields:
- `target` — a file-relative markdown path to the related page (same form as a body link)
- `type` — one of the allowed semantic types below

### Allowed relationship types

The table below is the framework default allowlist. A bundle's `AGENTS.md` may extend it; consumers must use the effective allowlist and preserve owner semantics without coercion.

| Type | Meaning | Example |
|---|---|---|
| `extends` | This page builds on or generalises the target | GPT extends Transformer Architecture |
| `implements` | This page is a concrete realisation of the target concept | BERT implements Masked Language Modelling |
| `contradicts` | This page's claims conflict with or refute the target | Evidence A contradicts Evidence B |
| `derived_from` | This page is based on or adapted from the target | Fine-tuning is derived from Transfer Learning |
| `uses` | This page depends on or relies on the target | RAG uses Vector Databases |
| `replaces` | This page supersedes or deprecates the target | GPT-4 replaces GPT-3 |
| `related_to` | Catch-all: related but no stronger directional type applies | Concept A is related to Concept B |

### Rules

- **Optional field** — omit the block entirely if no typed relationships are known. Untagged links remain valid and are treated as `related_to` by `wiki-export`.
- **Don't duplicate** — if a link already appears in the body, the `relationships:` entry just enriches it with a type; it is not a second link.
- **Direction matters** — the page declaring the entry is the *source*; `target` is the destination. Only declare relationships from this page's perspective.
- **Don't fabricate** — only add a typed entry when the source material makes the relationship direction and type clear. When in doubt, use `related_to` or omit.

Skills that read `relationships:`: `wiki-export` (emits typed edges), `cross-linker` (writes typed entries when inferring links), `wiki-query` (surfaces type in answers and walks the typed-edge graph for multi-hop "how is X connected to Y" path queries — bounded BFS over the `relationships:` adjacency, frontmatter-only).

## Trust and Lifecycle

Every page carries two orthogonal trust signals plus an optional supersession link, expressed in OKF v0.2 fields.

The requiredness and values below are framework defaults. A bundle's `AGENTS.md` may extend status values or make trust fields optional. Validators must apply that effective owner schema while still validating any trust value that is present.

The deterministic lint/trust consumer accepts owner schema through `OKF_ALLOWED_LIFECYCLES`, `OKF_ALLOWED_RELATIONSHIP_TYPES`, `OKF_REQUIRED_TRUST_FIELDS`, and `OKF_SCHEMA_SOURCE`. Resolution precedence is CLI > environment/config > these framework defaults (with status and relationship extensions additive). Explicit blank or whitespace-only values fail closed; omit the variable to select defaults. `wiki-lint/SKILL.md` owns the operational invocation contract.

### Trust tiers (derived from `verified`)

Consumers derive a trust tier from `verified`, lowest to highest:

| Condition | Trust tier |
|---|---|
| No `verified` key | **unverified** |
| `verified` by non-`human:` actors only | **machine-confirmed** |
| `verified` by a `human:<id>` actor | **human-reviewed** |

Trust tiers are advisory signals, not access control. `generated` records who *wrote* the content; `verified` records who *confirmed* it — kept distinct because the writer and the confirmer need not be the same actor.

### Lifecycle (`status`)

```yaml
status: draft        # draft | stable | deprecated
```

- `draft`: not yet reviewed; possibly incomplete. Set by any ingest skill on first write; the default for all new pages.
- `stable`: ready for consumption. **Entered only by a `human:<id>` actor** (the `draft → stable` transition is human-only).
- `deprecated`: kept for links and history; no longer current. Terminal.

Absent `status` => `stable` by spec default. `superseded_by` (a file-relative link to the replacement page) is an extension field used only when `status: deprecated`. The `lifecycle: disputed` extension overrides every state except `deprecated` in display. Update `lifecycle_changed` whenever `status` changes.

### Required trust/lifecycle fields

```yaml
base_confidence: 0.65          # [0.0, 1.0] — time-independent quality estimate. Stored once, recomputed on content change.
status: draft                  # draft | stable | deprecated
stale_after: 2024-06-13T00:00:00Z  # ISO datetime — content is stale on/after this instant
# superseded_by: "./new-page.md"    # file-relative link; only when status=deprecated
```

`superseded_by` is optional. Never fabricate it.

### Staleness (`stale_after`)

`stale_after` is an absolute instant, not a TTL: a concept is stale when `now >= stale_after`. The 90-day rule from the source project is now written into frontmatter at write time: `stale_after = updated + 90 days`, recomputed on every write. Time alone never demotes a human-reviewed page — but `stale_after` still flags it for re-review.

### Confidence formula

`base_confidence` is an extension field, but its formula is unchanged from the source:

```
base_confidence = lineage_count_score * 0.5 + source_quality_score * 0.5

lineage_count_score  = min(independent_evidence_lineages / 3, 1.0)
source_quality_score = avg(reviewed quality score per independent lineage)
```

After calculating the raw score, assess whether the evidence covers the page's material claims. Partial coverage may justify keeping or lowering the score; unsupported material claims require source/claim repair before any confidence change. Avoid small score churn without meaningful epistemic change.

**Source-quality scores** (use the highest-matching bucket):

| Bucket | Score | Examples |
|---|---|---|
| `paper` | 1.0 | arXiv, conference proceedings |
| `official` | 0.9 | `*.gov`, vendor docs |
| `documentation` | 0.85 | well-maintained third-party docs |
| `book` | 0.8 | books, technical references |
| `repository` | 0.75 | content-addressed repository/code evidence |
| `blog` | 0.55 | personal blogs |
| `session_transcript` | 0.5 | conversation history or completed operation |
| `forum` | 0.4 | Stack Overflow, HN, Reddit, issue-grade reports |
| `unknown` | 0.4 | catch-all/current config |
| `llm_generated` | 0.3 | LLM synthesis or unvalidated memory seed |

**An independent evidence lineage** is an origin that can corroborate a claim independently. Canonical source IDs remain useful for identity, but identity alone does not prove independence. Collapse dependent evidence before counting:

- files, releases, and commits from one repository → one repository lineage;
- retry/review/fix tasks in one workstream → one task lineage;
- parent/child Kanban records → one task lineage;
- byte-identical memories across profiles → one memory lineage;
- a snapshot plus the mutable source it captures → one lineage;
- aliases or metadata references resolving to one origin → one lineage.

The deterministic `wiki-lint` path validates `_meta/trust-ledger.json`; it does not recompute confidence from source strings. New or materially changed pages are marked for manual review. Refresh the ledger only after explicit human approval.

**Per-skill defaults** (ingest skills compute this automatically):

| Skill | base_confidence | status |
|---|---|---|
| `wiki-ingest` (URL) | `0.17 + 0.5 × classify(url)` | `draft` |
| `wiki-ingest` (single doc) | per-source classifier | `draft` |
| `wiki-ingest` (multi-doc) | `min(N/3,1)×0.5 + avg_q×0.5` | `draft` |
| `wiki-research` | varies, often 0.85+ | `draft` |
| `wiki-capture` | 0.42 | `draft` |
| `*-history-ingest` | 0.42 | `draft` |
| `wiki-update` | 0.59 | `draft` |
| `wiki-synthesize` | `min(input_pages.base_confidence)` | `draft` |

## Importance Tiering

The `tier:` extension field controls which pages get updated on each ingest pass and their priority in retrieval. As bundles grow, re-reading every page on every ingest wastes tokens — tiering lets ingest and query skills focus effort where it matters most.

### Three tiers

| Tier | Meaning | Ingest behavior | Query priority |
|---|---|---|---|
| `core` | Load-bearing pages — many other pages depend on them (high incoming-link count or bridge position). Always worth updating. | Always update if the source is even marginally relevant | Surfaced first in index and full-read passes |
| `supporting` *(default)* | Standard pages with moderate connectivity | Update when the source has clear new claims for this page | Standard priority |
| `peripheral` | Low-connectivity pages — rarely linked, narrowly scoped | Skip unless the source is *primarily* about this topic | Last resort; skipped when trimming to context budget |

### Assignment rules

- **New pages:** default to `tier: supporting`
- **Promote to `core`:** when a page accumulates ≥5 incoming links **or** is flagged as a bridge by `wiki-status` insights mode
- **Demote to `peripheral`:** when a page has ≤1 incoming link and hasn't been updated in 90+ days
- **Human override always wins** — edit `tier:` manually to lock a page at any level
- Existing pages without `tier:` are treated as `supporting` (backward compatible — no migration needed)

### Who manages tier

- `wiki-ingest` reads `tier:` to decide whether to update a page on the current pass
- `wiki-query` uses `tier:` to order candidates in the index pass and trim to context budget
- `wiki-status` insights mode computes graph metrics and **suggests** tier assignments — it never writes them automatically
- `wiki-lint` flags missing `tier:` on newly created pages

## Retrieval Primitives

Reading the bundle is the dominant cost of every read-side skill. Use the cheapest primitive that can answer the question and **escalate only when the cheaper one is insufficient**. Any skill that needs content from the bundle should follow this table rather than jumping straight to full-page reads.

| Need | Primitive | Relative cost |
|---|---|---|
| Does a page exist? What's its type/title/tags? | Read `index.md`; `Grep` frontmatter blocks (scope with a pattern that targets `^---` blocks at file heads) | **Cheapest** |
| 1–2 sentence preview of a page | Read the `description:` field in its frontmatter | **Cheap** |
| A specific claim or section inside a page | `Grep -A <n> -B <n> "<term>" <file>` — returns only the matching lines plus context | **Medium** |
| Whole-page content | `Read <file>` | **Expensive** — last resort |
| Relationships across pages | `Grep` markdown links (`\]\(.*?\.md\)`) across the bundle, or walk links from a known page | Case-by-case |

**Search command preference:** for shell/file searches, use ripgrep (`rg`, `rg --files`) when available; if not, fall back to `grep`/`find`. Capitalized `Grep`/`Glob` names in these skills are tool-generic primitives for agents that expose those tools.

**The rule:** escalate only when the cheaper primitive can't answer the question. If you can answer from `description:` fields alone, don't read page bodies. If a grepped section with `-A 10 -B 2` gives you the claim, don't read the whole page. A 500-line page opened to read 15 lines is 485 lines of wasted tokens.

**Why this matters:** a 20-page bundle lets you get away with full-bundle scans. A 200-page bundle does not. The primitives above are how the skills framework scales to large bundles without a database.

Skills that consume this table: `wiki-query`, `cross-linker`, `wiki-lint`, `wiki-status` (insights mode). Any new skill that reads the bundle should cite this section rather than reinvent the pattern.

## OKF Conformance

Every page is written OKF v0.2-conformant from the moment of creation. The bundle must pass validation at all times.

### The three conformance rules

1. Every non-reserved `.md` file in the tree contains a parseable YAML frontmatter block.
2. Every frontmatter block contains a non-empty `type` field.
3. Every reserved filename (`index.md`, `log.md`) follows its defined structure when present.

### Versioning

The bundle declares its target spec version with `okf_version: "0.2"` in the bundle-root `index.md` frontmatter — the only place frontmatter is permitted in an `index.md`. The migrator upgrades legacy `okf_version: "0.1"` bundles by rewriting the key to `"0.2"` and applying the v0.1→v0.2 field conversions (`timestamp` → `generated.at`, body `# Citations` → frontmatter `sources`).

### Error classes (conformance failures)

| Class | Condition |
|---|---|
| `E1` | A non-reserved `.md` file has no YAML frontmatter |
| `E2` | A frontmatter block is missing a `type` field, or it is empty |
| `E3` | A reserved file (`index.md`/`log.md`) violates its structure (e.g. a non-root `index.md` with frontmatter) |
| `E4` | An `Attested Computation` concept is missing its required `runtime` field |

### Warning classes (non-blocking — the spec allows these)

| Class | Condition |
|---|---|
| `W1` | Missing recommended `title` or `description` field |
| `W2` | Broken cross-link in a file |
| `W3` | No `generated` field (v0.2 recommended) |
| `W4` | No `index.md` in a directory |
| `W5` | `log.md` dates not in ISO 8601 form |
| `W6` | A `sources` entry is missing its `resource` field |
| `W7` | `stale_after` has passed — content is stale |

Run `scripts/validate.sh <bundle>` for a deterministic check (exit 0 = conformant, 1 = errors, 2 = usage). `wiki-lint` integrates `okflint` when it is installed (profile `okf-base.yaml`), with the script as a self-sufficient fallback.

### Consumer guarantees

A conformant consumer MUST NOT reject a bundle because of any of the following — and every okf-wiki skill must behave this way when reading another producer's bundle:

- Missing optional frontmatter fields.
- Unknown `type` values.
- Unknown additional frontmatter keys.
- Broken cross-links.
- Missing `index.md` files.

### Extension fields

Producers MAY include any additional frontmatter keys. Consumers SHOULD preserve unknown keys when round-tripping and MUST NOT reject documents with unrecognized fields. okf-wiki's enriched metadata (`updated`, `aliases`, `relationships`, `provenance`, `base_confidence`, `tier`, `lifecycle_changed`, `superseded_by`, `lifecycle`) is stored as §4.1 extension fields, so it survives any conformant reader — this is what makes the round-trip lossless.

### Out-of-scope convention

OKF conformance applies to knowledge content only. Operational artifacts are excluded by a trivially parseable machine rule, and are stripped from any "clean" bundle at packaging time:

- Directories with a `_` prefix: `_raw/`, `_staging/`, `_archives/`, `_readouts/`, `_meta/`, `_cache/`.
- Dot-files: `.manifest.json`, `.manifest.lock`.
- Non-markdown operational files.

`_insights.md` keeps its `_` prefix (out of scope). `AGENTS.md` (owner conventions) is an operational file, not an OKF concept. Validation skips everything matching the rule; no exception list is needed.

## Core Principles

1. **Compile, don't retrieve.** The bundle is pre-compiled knowledge. When you ingest a source, update every relevant page — don't just create a summary of the source.

2. **Compound over time.** Each ingest should make the bundle smarter, not just bigger. Merge new information into existing pages, resolve contradictions, strengthen cross-references.

3. **Provenance matters.** Every claim should trace to a source. When updating a page, note which source prompted the update.

4. **Mark inferences.** Default sentences are extracted. Mark synthesized claims with `^[inferred]` and contested claims with `^[ambiguous]`. A bundle that hides its guessing rots silently; one that marks it stays trustworthy.

5. **Human curates, agent maintains.** The human decides what sources to add, what questions to ask, and what earns trust (status transitions and `verified:`). The agent handles the bookkeeping — updating cross-references, maintaining consistency, noting contradictions.

6. **Format, not platform.** The bundle is portable OKF v0.2 by design. Any agent, any human, and any OKF tool can read it without conversion. No vendor, no plugin, no proprietary syntax — value comes from how many parties speak the format.

7. **Track everything.** Update `.manifest.json` after ingesting; `index.md`, `log.md`, and `_cache/hot.md` after any write. This is the atomic write protocol every write skill follows.

## Link Format

All internal links connecting concept pages are **standard markdown**, file-relative by default. There is no wikilink mode.

### Default: file-relative markdown

Compute the path from the **current file's directory** to the **target `.md` file** using `..` to climb up as needed, and always include the `.md` extension:

| Current file | Target | Relative link |
|---|---|---|
| `index.md` | `concepts/foo.md` | `[foo](./concepts/foo.md)` |
| `concepts/foo.md` | `entities/bar.md` | `[bar](../entities/bar.md)` |
| `projects/my-project/my-project.md` | `concepts/foo.md` | `[foo](../../concepts/foo.md)` |
| `projects/my-project/concepts/arch.md` | `entities/bar.md` | `[bar](../../../entities/bar.md)` |

File-relative links render in GitHub, in Obsidian (as an optional viewer), and in any static site generator.

### Bundle-relative `/absolute` (option)

The OKF spec also allows bundle-relative absolute links (`/concepts/foo.md`, interpreted from the bundle root). They are **not** the default — they break GitHub rendering — but remain an option for GCP integrations (kcmd / Knowledge Catalog) that expect `/`-absolute paths. Use them only when a consumer requires them.

### Broken links are forward-references

A link whose target does not exist is **not malformed** — it is a *forward-reference*: legal "not-yet-written knowledge". `wiki-lint` surfaces broken links as a separate class (`W2`), distinct from real errors, so they survive migration and are tracked until the target is written.

### Migration: converting wikilinks

When migrating an obsidian-wiki vault to a bundle, the migrator converts legacy wikilink syntax to file-relative markdown:

| Legacy wikilink | Converted link |
|---|---|
| `[[path/to/page]]` | `[path/to/page](./path/to/page.md)` |
| `[[path/to/page\|display text]]` | `[display text](./path/to/page.md)` |
| `[[path/to/page#Heading]]` | `[path/to/page](./path/to/page.md#heading)` |
| unmatched bare-title `[[Title]]` | plain text (no link) |

New pages are always written as markdown links; wikilinks exist only inside the migrator and are never produced by write skills.

## Config Resolution Protocol

**All skills must resolve config using this algorithm — do not hard-code `.env` or the global config path directly.** This ensures single-bundle, multi-bundle, project-local, and VPS setups all work correctly.

### Global config directory

The global config directory is **XDG-style**: `$XDG_CONFIG_HOME/okf-wiki` (default `~/.config/okf-wiki`). Installs that already have a `~/.obsidian-wiki` directory keep using it — so an existing setup never breaks — but any **new** install lands under the XDG path. Resolve it with:

```
okf_wiki_config_dir() {
  local xdg_dir="${XDG_CONFIG_HOME:-$HOME/.config}/okf-wiki"
  local legacy_dir="$HOME/.obsidian-wiki"
  if [ -d "$legacy_dir" ] && [ ! -e "$xdg_dir" ]; then
    echo "$legacy_dir"
  else
    echo "$xdg_dir"
  fi
}
```

Everywhere below, "the global config dir" means `$(okf_wiki_config_dir)`, and "the global config" means `$(okf_wiki_config_dir)/config`.

### Resolution order

0. **Inline bundle override (`@name`)** — if the user's request contains an `@<name>` token (e.g. `@work save this`, `query @personal about X`), resolve `<global config dir>/config.<name>` directly and use its `OKF_BUNDLE_PATH`. This **overrides** both the CWD `.env` walk-up and the active symlink, and applies to **that invocation only** — never run `ln -sf` or otherwise change the active bundle for an `@name` request. If `<global config dir>/config.<name>` doesn't exist, tell the user it doesn't exist and list the available bundles (the `bundle-switch` **List** logic), then stop — do **not** silently fall back to the default. The `@name` is a routing directive, not content: strip it out before treating the rest of the request as the actual instruction or page text.
1. **Walk up from CWD** — look for a `.env` file in the current directory, then each parent, up to `$HOME`. Stop at the first `.env` that contains `OKF_BUNDLE_PATH`.
2. **Global config** — if no local `.env` found, read the global config (`$(okf_wiki_config_dir)/config`).
3. **Prompt setup** — if neither exists, tell the user: "No config found. Run `wiki-setup` to initialize your bundle."

`@name` is a **per-invocation override** — it targets one bundle for one request. `/bundle-switch <name>` is the **persistent default** — it re-points the active symlink for all future requests. Use `@name` to touch the other bundle from anywhere without disturbing your default ("brain") bundle.

```
find_config() {
  # $1 = parsed @name from the request, if any (else empty)
  local config_dir
  config_dir="$(okf_wiki_config_dir)"
  if [ -n "$1" ]; then
    [ -f "$config_dir/config.$1" ] && { echo "$config_dir/config.$1"; return; }
    echo ""; return   # named bundle missing → caller reports + lists, no fallback
  fi
  dir="$PWD"
  while [ "$dir" != "$HOME" ] && [ "$dir" != "/" ]; do
    [ -f "$dir/.env" ] && grep -q "OKF_BUNDLE_PATH" "$dir/.env" && { echo "$dir/.env"; return; }
    dir="$(dirname "$dir")"
  done
  [ -f "$config_dir/config" ] && { echo "$config_dir/config"; return; }
  echo ""
}
```

**Legacy alias:** `OBSIDIAN_VAULT_PATH` is read as a legacy alias of `OKF_BUNDLE_PATH` during migration.

### Bundle-scoped state

Skills that write runtime state (e.g. `daily-update`) must scope that state to the resolved bundle, not to a global path. Use:

```
BUNDLE_ID=$(echo "$OKF_BUNDLE_PATH" | md5sum 2>/dev/null || md5 -q - <<< "$OKF_BUNDLE_PATH" | cut -c1-8)
STATE_DIR="$(okf_wiki_config_dir)/state/$BUNDLE_ID"
```

### Standard "Before You Start" block

Every skill's setup section should read:

> **Resolve config** — follow the Config Resolution Protocol in `okf-wiki/SKILL.md`. Honor an inline `@name` override first, then walk up from CWD for `.env`, fall back to the global config, else prompt setup. This gives `OKF_BUNDLE_PATH` and any tool-specific path overrides. Then read `$OKF_BUNDLE_PATH/AGENTS.md` if it exists — owner conventions override framework defaults.

## Writing Profile Resolution

Before drafting or rewriting natural-language Markdown, resolve the global config directory with the XDG/legacy algorithm above, then read `<global config dir>/WRITING.md` when it exists. A missing or empty `WRITING.md` means there are no custom writing preferences. If that optional read fails, warn and continue with the default framework guidance.

The effective precedence is framework invariants > current task/skill requirements > current project `AGENTS.md` > bundle `AGENTS.md` > global `WRITING.md`. Framework invariants include the canonical mapping, provenance, and safety; operation-specific requirements remain authoritative for the current task. Unspecified project and bundle rules are inherited from less-specific layers, and more specific same-topic rules win.

Writing preferences apply only to newly drafted or rewritten natural-language fields and body content. This includes natural-language title and description values in YAML frontmatter, but preferences cannot alter YAML syntax, required keys, structure, types, or machine-generated fields. JSON, structured logs, and pass-through content remain unchanged and retain their required formats and source fidelity.

## Environment Variables

The bundle is configured through environment variables (see `.env.example`). The only required variable is the bundle path — everything else has sensible defaults.

- `OKF_BUNDLE_PATH` — Where the bundle lives **(required)**
- `OKF_SOURCES_DIR` — Where raw source documents are
- `OKF_CATEGORIES` — Comma-separated list of categories
- `OKF_RAW_DIR` — Staging inbox directory (default: `_raw`)
- `OKF_MAX_PAGES_PER_INGEST` — cap on pages created/updated per `wiki-ingest` run (default: `15`)
- `OKF_ALLOWED_LIFECYCLES`, `OKF_ALLOWED_RELATIONSHIP_TYPES`, `OKF_REQUIRED_TRUST_FIELDS`, `OKF_SCHEMA_SOURCE` — owner schema overrides (see *Trust and Lifecycle*)
- `WIKI_SKIP_PROJECTS` — Comma-separated substrings; any project dir whose name contains one is excluded from history ingest (scan + delta + manifest)
- `WIKI_TOKEN_WARN_THRESHOLD` — Emit a warning in `wiki-status` when the full-bundle token estimate exceeds this value (default: `100000`). Set to `0` to disable.
- `WIKI_STAGED_WRITES` — When `true`, all agent-written pages go to `_staging/<category>/` for human review before promotion. See `wiki-setup` and `wiki-stage-commit`.
- `CLAUDE_HISTORY_PATH` / `CODEX_HISTORY_PATH` / `HERMES_HOME` / `OPENCLAW_HOME` / `COPILOT_HISTORY_PATH` / `PI_HISTORY_PATH` — where to find each third-party agent's session data (vendor names unchanged)
- `CODE_UNDERSTANDING_BACKEND` — how wiki-update understands a project before distilling: `auto` (CodeGraph when available, else builtin ast-extract + rg; default), `builtin`, or `codegraph` (explicitly require; warn/error if unavailable).
- `CODE_UNDERSTANDING_CODEGRAPH_BIN` — optional path to the codegraph binary when it isn't on PATH.
- `LINT_SCHEDULE` — how often `daily-update` also runs `wiki-lint`: `daily` | `weekly` (default) | `manual`.
- `BUNDLE_ID` — derived bundle-scoped identifier used for runtime state (see *Bundle-scoped state*).

No API keys are needed — the agent running these skills already has LLM access built in.

## Modes of Operation

The bundle supports three ingest modes:

| Mode | When to use | What happens |
|---|---|---|
| **Append** | Small delta, incremental updates | Compute delta via manifest, ingest only new/modified sources |
| **Rebuild** | Major drift, fresh start needed | Archive current bundle to `_archives/`, clear, reprocess all sources |
| **Restore** | Need to go back | Bring back a previous archive |

Use `wiki-status` to see the delta and get a recommendation. Use `wiki-rebuild` for archive/rebuild/restore operations.

## Reference

For details on specific operations, see the companion skills:
- **wiki-status** — Audit what's ingested, compute delta, recommend append vs rebuild
- **wiki-rebuild** — Archive current bundle, rebuild from scratch, or restore from archive
- **wiki-ingest** — Distill source documents into bundle pages and raw text/chat/log data
- **claude-history-ingest** / **codex-history-ingest** (and the other agent history skills) — Ingest conversation/session history from third-party agents
- **wiki-query** — Answer questions against the bundle
- **wiki-lint** — Audit and maintain bundle health (OKF conformance + broken links/orphans/staleness)
- **wiki-setup** — Initialize a new bundle
- **bundle-switch** — Manage multiple bundles (persistent default + `@name` override)
- **wiki-import** / **wiki-export** — Merge external OKF bundles / package the bundle with filters + graph artifacts
- **migrate-vault.sh** — Migrate an obsidian-wiki vault to a bundle (wikilink conversion + v0.1→v0.2 upgrade)

---

Derived from Ar9av/obsidian-wiki llm-wiki skill (MIT).
