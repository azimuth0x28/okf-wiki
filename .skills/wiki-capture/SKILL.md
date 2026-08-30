---
name: wiki-capture
description: >
  Save the current conversation as a permanent, structured bundle page. Use this skill when the user
  says "save this", "/wiki-capture", "capture this", "file this conversation", "preserve this",
  "add this to my wiki", or wants to turn what was just discussed into lasting knowledge. The skill
  classifies the content, rewrites it as declarative knowledge (not a chat transcript), and places
  it in the correct bundle category. Also supports a fast QUICK MODE (`/wiki-capture --quick`, "quick
  capture", "capture this finding", "save this bug fix", "save this gotcha", "drop this to raw", "quick
  save to wiki") that drops findings to the `_raw/` staging area in under 60 seconds with no manifest
  or index writes — used by the session-end Stop hook to auto-preserve findings. Accepts inline
  named-bundle routing like "@research save this" via the shared Config Resolution Protocol.
---

# Wiki Capture — Conversation to Bundle Page

You are preserving knowledge from the current conversation as a permanent bundle page. The goal is to extract the *substance* — the knowledge itself — not a summary of what was said.

**Writing profile:** Before drafting or rewriting natural-language Markdown in any mode, read and apply the `Writing Profile Resolution` section in `okf-wiki/SKILL.md`. Framework schema, provenance, safety, and operation-specific requirements take precedence.
`WRITING.md` preferences apply only to newly drafted or rewritten natural-language Markdown; preserve source content and structured records.

This skill has three modes:

- **Full mode (default)** — classify the content and write a finished, cross-linked bundle page directly into the right category. This is the rest of this document (Steps 1–7).
- **Quick mode (`--quick`)** — zero-friction staging: drop findings to `_raw/` in under 60 seconds with no manifest/index/log/QMD writes. Used for mid-session capture and by the session-end Stop hook. See below, then stop — do **not** run the full-mode steps.
- **Correction mode (`--correction`)** — capture one atomic correction as derived knowledge while leaving the immutable conversation/source untouched. Use the template below, then update only the derived consumers and tracking links.

## Quick Mode (`--quick`)

Trigger when invoked as `/wiki-capture --quick`, by "quick capture" / "capture this finding" / "save this bug fix" / "save this gotcha" / "drop this to raw" / "quick save to wiki", or automatically by the session-end Stop hook.

**Speed contract:** Inline only. No subagents. No QMD. No manifest/`index.md`/`log.md`/`_cache/hot.md` writes. Target: <60 seconds. Promotion to full bundle pages happens later via `/wiki-ingest`.

1. **Resolve config** (Config Resolution Protocol in `okf-wiki/SKILL.md`): get `OKF_BUNDLE_PATH` and `OKF_RAW_DIR` (default: `$OKF_BUNDLE_PATH/_raw`). Ensure `$OKF_RAW_DIR` exists; create it if not.

   Capture does not independently reinterpret validator schema inputs. When `OKF_ALLOWED_LIFECYCLES`, `OKF_ALLOWED_RELATIONSHIP_TYPES`, `OKF_REQUIRED_TRUST_FIELDS`, or `OKF_SCHEMA_SOURCE` is present, preserve it for the downstream lint/trust consumer: CLI values take precedence over environment/config values, which take precedence over framework defaults, and explicit blank or whitespace-only values fail closed. Omit a variable to use defaults.

2. **Gate — KEEP or SKIP?** Before extracting, judge whether this session has capture value. This keeps the skill safe to call automatically without spamming `_raw/`.
   - **SKIP** (exit with "Nothing worth capturing in this session.") if ALL are true: the conversation is purely conversational (planning/Q&A/explanation) with no implementation; no errors, debugging, or problem-solving visible; nothing surprising or undocumented; every finding is already obvious from the docs.
   - **KEEP** (proceed) if ANY are true: a fix or workaround was found through investigation; non-obvious library/API/framework behavior was confirmed (edge case, undocumented constraint, time-costing gotcha); a debugging session reached a concrete conclusion; a reusable pattern emerged.
   - When invoked **via the Stop hook, err toward SKIP** — only KEEP on clear evidence. When invoked **manually, err toward KEEP** — the user called it for a reason.

3. **Scan for reusable findings** — non-obvious bugs and root causes, framework/library gotchas, surprising API behavior, investigated workarounds, environment/toolchain quirks, patterns from debugging. Skip PM updates, config already in CLAUDE.md, inconclusive back-and-forth, anything obvious from the docs, and pleasantries. If nothing material emerged, say so and stop.

4. **Cluster by topic** — one `_raw/` file per topic cluster, not per finding. Name each as a kebab-case slug (e.g. `swift-actor-reentrancy`, `nextjs-hydration-mismatch`).

5. **Infer project context** from repo names, file paths, framework mentions, error messages. Use the most specific name you can reliably infer; else `null`.

6. **Write raw files** — for each cluster, write `$OKF_RAW_DIR/<ISO-date>-<slug>.md`. Per-cluster fields that vary: `title`, `tags` (2–4 from taxonomy), `description` (≤200 chars), `project` (inferred or `null`), `base_confidence` (0.6 discussed → 0.75 fix applied → 0.9 test confirmed), `provenance.extracted`/`provenance.inferred` (sum to 1.0), `lifecycle_changed` (today), `sources` (with mandatory `resource` per OKF v0.2 — use `"<project> session (<YYYY-MM-DD>)"` as the resource descriptor). Read `references/RAW-FORMAT.md` for the full frontmatter spec, finding-block body structure, and provenance/confidence calibration. For canonical frontmatter mapping, see `.skills/okf-wiki/SKILL.md` §Schema.

7. **Confirm** — list staged files and tell the user to run `/wiki-ingest` to promote them:
   ```
   Staged to _raw/:
     _raw/2026-05-27-swift-actor-reentrancy.md   — "Actor reentrancy causes deadlock in async forEach"
   Run /wiki-ingest to promote these to full bundle pages.
   ```
   Quick mode deliberately does **not** write the manifest, `index.md`, `log.md`, `_cache/hot.md`, or refresh QMD — promotion via `/wiki-ingest` handles all of that. **Stop here; do not run the full-mode steps below.**

---

## Correction Mode (`--correction`)

Use this mode when a user or stronger authority corrects a claim derived from an immutable conversation, tool result, or other raw source. Never edit or copy the raw source. Resolve config, read the bundle `AGENTS.md`, and update an existing derived page when one owns the claim; otherwise create the smallest owner-compliant derived correction page.

Record exactly one atomic claim pair. `speaker_type` is semantic and must be assessed independently of a serialized message `role` (a tool result may be serialized as `role=user`). Do not include raw transcript excerpts.

```yaml
correction_id: <stable-id>
source_locator: <immutable file:line or channel/thread/timestamp>
source_text_sha256: <64 lowercase hex chars>
serialized_role: <source role, if present>
speaker_type: user | assistant | teammate | tool_result | slack_member
original_claim:
  subject: <exact entity or capability>
  assertion: <single atomic value>
corrected_claim:
  subject: <same exact entity or capability>
  assertion: <single atomic value or null>
authority_class: contract | decision | code | test | deploy | runtime | db | narrative
verification_state: verified | inferred | unverified | contradicted
asserted_at: <ISO-8601 timestamp>
effective_at: <ISO-8601 timestamp or null>
as_of: <ISO-8601 timestamp>
supersedes: [<original-claim-id>]
consumer_propagation:
  kw: open | not_applicable | complete
  ob: open | not_applicable | complete
  requirements: open | not_applicable | complete
  code: open | not_applicable | complete
  tests: open | not_applicable | complete
  ai_memory: open | not_applicable | complete
corrected_at: <ISO-8601 timestamp>
```

Before any derived write, compute `source_pre_sha256` directly from the immutable source and require it to equal `source_text_sha256`. After writing the correction and updating derived consumers, recompute `source_post_sha256` from the same locator. Abort and report an immutability violation unless `source_pre_sha256 == source_post_sha256 == source_text_sha256`. This verification is mandatory even when the correction write succeeds.

After writing the derived correction, link the immutable source to the created/updated page through `.manifest.json`, append only the correction ID and affected-page counts to `log.md`, and propagate the atomic correction to every consumer independently. Mark a consumer `complete` only after verifying that consumer; do not collapse mixed results into a single aggregate status. Keep secrets, raw excerpts, and source copies out of the correction record.

---

## Full Mode

## Before You Start

1. **Resolve config** — follow the Config Resolution Protocol in `okf-wiki/SKILL.md` (inline `@name` override → walk up CWD for `.env` → global config → prompt setup). This gives `OKF_BUNDLE_PATH`.
2. Read `$OKF_BUNDLE_PATH/index.md` to understand existing bundle content (avoid duplicates)
3. Read `$OKF_BUNDLE_PATH/_cache/hot.md` if it exists — it gives context on recent activity

## Step 1: Identify What's Worth Preserving

Scan the conversation. Ask: what knowledge emerged here that would be valuable in 3 months with no memory of this chat?

Worth preserving:
- Decisions made and *why* they were made
- Analysis, frameworks, mental models developed
- Technical findings, patterns, or procedures
- Synthesized understanding of a topic
- Clear explanations of a concept that took effort to arrive at
- Key facts from an external source discussed in the conversation

Skip:
- Logistics, scheduling, pleasantries
- Exploratory back-and-forth where no conclusion was reached
- Content that's already in the bundle

If nothing material emerged, tell the user and stop.

## Step 2: Classify the Content Type

Assign one of five types — this determines the target folder and tone:

| Type | Description | Target folder |
|---|---|---|
| `Synthesis` | Multi-step analysis or an answer to a specific question that required reasoning | `synthesis/` |
| `Concept` | A definition, framework, or mental model (what a thing *is*) | `concepts/` |
| `Reference` | Summary of an external document, article, or resource discussed | `references/` |
| `Synthesis` | A strategic, architectural, or design choice and its rationale (decisions → Synthesis) | `synthesis/` |
| `Journal` | A complete discussion summary when the conversation spans multiple topics | `journal/` |

If the content clearly belongs to a specific project (detected from context or user mention), place it under `projects/<project-name>/<category>/` instead.

## Step 3: Rewrite as Declarative Knowledge

Do **not** write a summary of the conversation. Write the knowledge itself, in declarative present tense:

- Not: "The user asked about X and Claude explained that..."
- Yes: "X works by..."
- Not: "We decided to use Y because..."
- Yes: "Y is preferred over Z because [reason]. [^[inferred] if the rationale was implied, not stated explicitly]"

Apply provenance markers per `okf-wiki`:
- *Extracted* — explicitly stated in the conversation (no marker)
- *Inferred* — generalized or synthesized from the conversation → `^[inferred]`
- *Ambiguous* — disputed, uncertain, or contradictory → `^[ambiguous]`

## Step 4: Generate a Slug and Title

Derive a clear, descriptive title from the content. Slugify it:
- Lowercase, words separated by hyphens
- Max 50 characters
- Avoid dates in the slug (the frontmatter has `generated.at`)

## Step 5: Write the Bundle Page

Create the file at the target path with required frontmatter. For the canonical frontmatter mapping and write protocol, see `.skills/okf-wiki/SKILL.md` §Schema. The minimum required fields are `type` and `generated`. Pages built from sources also require `sources` with a `resource` entry.

```yaml
---
type: Synthesis                           # TitleCase: Concept|Entity|Skill|Reference|Synthesis|Project|Journal
title: >-
  <Title>
description: >-
  <1-2 sentences, ≤200 chars, answering "what knowledge does this page hold?">
tags: [<2-5 domain tags from taxonomy>]
generated:
  by: okf-wiki/<version>                 # producer actor: <producer>/<version>
  at: <ISO-8601 timestamp>
status: draft                             # draft|stable|deprecated
stale_after: <generated.at + 90d>        # recomputed on every write
sources:
  - resource: "<project> session (<YYYY-MM-DD>)"   # mandatory in each entry
# ===== extension fields (OKF §4.1 — preserved verbatim) =====
updated: <ISO-8601 timestamp>
provenance:
  extracted: 0.X
  inferred: 0.X
  ambiguous: 0.X
base_confidence: 0.42
lifecycle_changed: <ISO date today>
---
```

Body structure by type:

**Synthesis:**
```markdown
# Title

## Context
<What prompted this — the problem or question being addressed>

## Finding / Decision
<The core knowledge or conclusion>

## Reasoning
<Why this is the case or why this choice was made>

## Implications
<What follows from this — what to watch for, next steps, trade-offs>

## Related
<[Title](./path/to/related.md) — file-relative links to connected pages>
```

**Concept:**
```markdown
# Title

<Definition in one clear sentence.>

## What It Is
<Explanation of the concept>

## How It Works
<Mechanism or structure>

## When to Use
<Applicability, conditions, trade-offs>

## Related
<[Title](./path/to/related.md)>
```

**Reference:**
```markdown
# Title

> Source: <title or URL>

## What It Covers
<What the source is about>

## Key Points
<Bulleted claims with provenance markers>

## Open Questions
<What it raises but doesn't answer — omit if none>

## Related
<[Title](./path/to/related.md)>
```

**Journal:**
```markdown
# Title

*Session captured: <date>*

## Topics Covered
<Brief list>

## Key Takeaways
<The 3-5 most important things that emerged>

## Decisions Made
<Any explicit decisions, with rationale>

## Open Questions
<What remains unresolved>

## Related
<[Title](./path/to/related.md)>
```

Every page must link to at least 2 existing bundle pages. Search `index.md` before writing. If fewer than 2 related pages exist, create minimal stubs for the most important concepts referenced.

## Step 6: Update Tracking Files

**`index.md`** — Add the new page under its category section.

**`log.md`** — Append:
```
- [TIMESTAMP] CAPTURE type=<type> page="<path>" title="<title>"
```

**`_cache/hot.md`** — Update **Recent Activity** with what was just captured. Update **Key Takeaways** if the note introduced something worth flagging. Update `updated` timestamp.

## Step 7: Confirm to User

Report the saved path and title:
```
Saved to: projects/<name>/synthesis/<slug>.md
Title: <Title>
Type: Synthesis
```

## Quality Checklist

- [ ] Content rewritten as declarative knowledge (not a chat transcript)
- [ ] Type classified correctly; target path is in the right folder
- [ ] Frontmatter complete with type, title, description, tags, generated, sources
- [ ] At least 2 file-relative links to existing pages
- [ ] `index.md`, `log.md`, and `_cache/hot.md` updated
- [ ] Confirmed save path to user

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

> Derived from Ar9av/obsidian-wiki wiki-capture skill (MIT).
