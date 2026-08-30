---
name: memory-bridge
description: >
  Browse and compare bundle knowledge by which agent actor originally produced it. Use this skill when the user
  says "/memory-bridge", "browse codex memory", "what did codex know about X", "show me claude knowledge",
  "cross-agent memory", "what does hermes know that claude doesn't", "show me knowledge from <actor>",
  "compare my agent memories", or wants to explore knowledge gaps between agents. Works from any project.
  Diff mode ("what's different", "unique to codex", "gaps between agents") is the killer feature — it surfaces
  blind spots between agents that the user may not know exist.
---

# Memory Bridge — Cross-Agent Knowledge Browser

You are helping the user browse and compare their OKF bundle knowledge filtered by which agent actor originally produced it. The bundle tracks provenance in each page's `generated.by` frontmatter field — this skill surfaces that metadata as a navigable view.

Actor identity follows the convention in `.skills/okf-wiki/SKILL.md` §Actors: `<producer>/<version>` for agents (e.g. `claude/2.5.0`, `reference_agent/gemini-2.5-pro`), `human:<id>` for people, `process:<id>` for automation.

## Before You Start

1. **Resolve config** — follow the Config Resolution Protocol in `.skills/okf-wiki/SKILL.md` (inline `@name` override → walk up CWD for `.env` → global config → prompt setup). This gives `OKF_BUNDLE_PATH`.
2. Read `$OKF_BUNDLE_PATH/.manifest.json` — this is the source-of-truth for what agent produced what.
3. Read `$OKF_BUNDLE_PATH/index.md` for page titles and one-line descriptions.

## Commands

Parse the user's invocation to determine mode:

| Invocation | Mode |
|---|---|
| `/memory-bridge <actor>` | **Browse** — list all bundle pages produced by `<actor>` |
| `/memory-bridge <actor> "<topic>"` | **Search** — pages from `<actor>` that mention `<topic>` |
| `/memory-bridge diff` | **Diff** — pages unique to each actor; overlap; blind spots |
| `/memory-bridge diff <actor-a> <actor-b>` | **Diff** — compare two specific actors |
| `/memory-bridge map` | **Map** — full origin matrix: every page × every actor that touched it |

Recognized actor names: any `<producer>/<version>` string (e.g. `claude/2.5.0`, `codex/gpt-4o`, `hermes/0.9.0`), `human:<id>` (hand-written), `process:wiki-ingest` (ingested documents). The skill matches by prefix — `claude` matches any `claude/*` actor, `human` matches any `human:*` actor.

## Step 1: Build the Actor Map

Scan all bundle pages for their `generated.by` frontmatter field. For each page, extract:

- `generated.by` — the actor identity (e.g. `claude/2.5.0`, `codex/gpt-4o`, `human:evgeniy`)
- Map the actor to a canonical actor group:
  - `claude/*` → `claude`
  - `codex/*` → `codex`
  - `hermes/*` → `hermes`
  - `openclaw/*` → `openclaw`
  - `copilot/*` → `copilot`
  - `pi/*` → `pi`
  - `human:*` → `human`
  - `process:wiki-ingest` → `ingest`
  - `okf-wiki/*` → `okf-wiki` (framework fallback producer)
  - anything else → `<exact-actor-string>`

Build a map:

```
actor_pages = {
  "claude": set(pages where generated.by starts with "claude/"),
  "codex":  set(pages where generated.by starts with "codex/"),
  "human":  set(pages where generated.by starts with "human:"),
  "ingest": set(pages where generated.by is "process:wiki-ingest"),
  ...
}
```

A page can appear in multiple actors' sets if multiple agents contributed to it (e.g. a page initially written by `claude/2.5.0` and later updated by `codex/gpt-4o` — record the latest `generated.by` value, but also check if `.manifest.json` lists the page under multiple source agents).

## Step 2: Execute the Mode

### Browse Mode

Filter `actor_pages[<actor>]` and present as a grouped list:

```
## Knowledge from <actor> (<N> pages)

### By type
- Concept/ — N pages
- Entity/ — N pages
- Skill/   — N pages
...

### Pages
| Page | Type | Tags | Last updated |
|------|------|------|--------------|
| [Page Title](./concepts/page-name.md) | Concept | tag1, tag2 | 2026-04-10 |
...
```

Read frontmatter for the listed pages (grep for `^(type|title|tags|updated):`) — do not read full page bodies unless the user asks.

### Search Mode

Within the filtered page set, run:
```
rg -l "<topic>" <pages in actor set>
```
Then grep section headers (`^##`) around matches to give context without full reads. Present results as a ranked list with the matching excerpt.

### Diff Mode

Compute:
- `only_in_a` = `actor_pages[a]` − `actor_pages[b]`
- `only_in_b` = `actor_pages[b]` − `actor_pages[a]`
- `shared` = `actor_pages[a]` ∩ `actor_pages[b]`

If no specific actors are given, compare all actors pairwise (limit to pairs with >0 overlap or unique pages to keep output concise).

Present:

```
## Memory Bridge Diff — <actor-a> vs <actor-b>

### Only in <actor-a> (<N> pages)
These concepts exist in your bundle from <actor-a> sessions but <actor-b> has never touched them.
<list with one-line descriptions from index.md>

### Only in <actor-b> (<N> pages)
<list>

### Shared (<N> pages)
Both actors have contributed to these pages.
<list — only show if ≤15; otherwise just the count>

### Notable gaps
<highlight the most interesting asymmetries — e.g. "codex has 12 pages on build tooling that claude has never seen">
```

### Map Mode

Build a matrix showing every page and which actors have touched it. Cap at 50 rows; sort by number of contributing actors descending (most cross-agent pages first — these are the richest nodes).

```
| Page | claude | codex | hermes | copilot | human |
|------|--------|-------|--------|---------|-------|
| [React Patterns](./concepts/react-patterns.md) | ✓ | ✓ | — | ✓ | — |
| [Rust Ownership](./concepts/rust-ownership.md) | — | ✓ | — | — | ✓ |
```

## Step 3: Spawn impl-validator (if available)

After generating output, if the `impl-validator` skill is available in the current environment, spawn it as a subagent:

```
impl-validator check:
  goal: "Browse/diff bundle knowledge by source actor and cross-agent blind spots"
  artifacts: [the output you just generated]
  checks:
    - Did you correctly parse generated.by from page frontmatter?
    - Are page counts plausible (not 0 unless bundle is empty)?
    - Is the diff symmetric (a−b and b−a are disjoint)?
    - Did you avoid reading full page bodies when not needed?
```

Apply any issues it surfaces before presenting output to the user.

## Step 4: Log

Append to `$OKF_BUNDLE_PATH/log.md`:
```
- [TIMESTAMP] MEMORY-BRIDGE mode=<browse|search|diff|map> actor=<actor> pages_shown=N
```

## Output Conventions

- Always show page counts so the user can calibrate how much knowledge is in each agent's silo.
- Use file-relative markdown links `[display](./path/to/page.md)` for page references.
- In diff mode, call out the most *surprising* asymmetry explicitly — that's the insight the user came for.
- If `.manifest.json` is empty or missing, say so clearly and suggest running `/wiki-history-ingest` first.
- If no pages have `generated.by` set (pre-migration bundles), fall back to reading `sources:` frontmatter to infer the originating agent from source paths (e.g. `.claude/` paths → claude).

---

Derived from Ar9av/obsidian-wiki memory-bridge skill (MIT).
