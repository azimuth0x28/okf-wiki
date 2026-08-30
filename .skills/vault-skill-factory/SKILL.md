---
name: vault-skill-factory
description: >
  Generate a portable, self-contained Agent Skill from mature, curated bundle pages —
  turning a cluster of mature knowledge into a reusable "digital expert" (SKILL.md + references/).
  Use this skill when the user says "/vault-skill-factory", "make a skill from my bundle", "turn these
  pages into a skill", "generate an agent skill from my bundle", "package my notes on X as a skill",
  "build a domain-expert skill from my bundle", or wants to distill recurring, mature bundle knowledge
  into a shareable skill. Inspired by OpenKB's "drop in a book → out comes a digital expert" pattern.
  The factory ONLY reads the bundle and WRITES TO A REVIEW DIRECTORY — it never installs skills,
  never writes into .skills/, and never touches global skill directories.
---

# Vault Skill Factory

You turn a cluster of **mature, curated** bundle pages into a **portable Agent Skill**: a
`SKILL.md` plus a `references/` folder, written to a review directory for the human to inspect
and (only if they choose) install. This is the inverse of `wiki-capture`: capture turns a
conversation into a page; the factory turns pages into a reusable skill.

## Hard guardrails (read first)

- **Never write into `.skills/`** and **never run `setup.sh`** or create symlinks into any global
  skill directory (`~/.claude/skills`, `~/.codex/skills`, …). Generated skills go to the review
  dir only. Installation is a separate, explicit human decision.
- **Never auto-install.** End by telling the user where the skill is and how to install it
  *project-locally* if they want — do not do it for them.
- Source pages are trusted bundle content, but do not invent capabilities: the generated skill must
  reflect what the pages actually say.

## Before You Start

1. **Resolve config** (Config Resolution Protocol in `okf-wiki/SKILL.md`): get `OKF_BUNDLE_PATH`,
   `OKF_WIKI_REPO`, the QMD vars, and:
   - `SKILL_FACTORY_OUTPUT_DIR` — where generated skills land. Default:
     `$OKF_BUNDLE_PATH/_generated-skills` (a bundle-level, underscore-prefixed *out-of-scope* dir —
     like `_raw`/`_staging`/`_meta`, outside OKF conformance, NOT the `skills/` knowledge category).
     This co-locates generated skills with the bundle they were distilled from. Create it if missing.
     Note: `_generated-skills/` holds runtime Agent-Skill bundles (`name` + `description` frontmatter),
     **not** bundle pages — never write them into `skills/` (that category is for knowledge pages and
     is graph-/lint-/index-tracked).
   - `SKILL_FACTORY_MATURITY` — comma list of `status:` values that count as "mature".
     Default: `stable`. Pages with `tier: core` also qualify. A human `verified:` entry on a page
     is a bonus trust signal (human-reviewed tier), not a gate. Maturity is read, never written:
     per the human-only lifecycle invariant in `okf-wiki/SKILL.md`, agents must not promote pages
     to `status: stable` to make them qualify — if the cluster is too immature, say so.
2. Read `index.md` to understand what the bundle holds.

## Step 1: Choose the cluster

Decide which pages become the skill. The user may name a topic, tag, or project; otherwise propose
candidates.

1. **Seed** from the user's intent (a topic, tag, project, or a named page).
2. **Expand** the cluster:
   - If QMD is configured (`QMD_WIKI_COLLECTION`), run `qmd query "<topic>" -c "$QMD_WIKI_COLLECTION" --files`
     (or `vsearch`) to gather semantically related pages — this is the intended way to find the
     full cluster, not just exact-tag matches.
   - Otherwise `Grep`/`Glob` by tag and link-neighbourhood (pages linked from the seed pages via
     file-relative markdown links).
3. **Filter by maturity:** keep pages whose `status:` is in `SKILL_FACTORY_MATURITY` **or**
   whose `tier:` is `core`. Drop `draft` pages unless the user explicitly includes them.
4. **Confirm the cluster with the user** (list page names + count) before generating. If fewer than
   ~3 mature pages match, say so — a skill from one thin page isn't worth it; offer to proceed anyway
   or widen the net.

## Step 2: Design the skill

From the cluster, decide:

- **`name`** — kebab-case, derived from the cluster's subject (e.g. `french-theory-expert`,
  `peptide-protocols`). Must not collide with an existing skill in `.skills/`.
- **`description`** — the trigger. Write it "pushy" (per `skill-creator`): state **when** to use it
  (all the phrasings a user might say) **and** what it does. This field is what makes the skill fire.
- **Reasoning approach** — how an agent should *use* this knowledge: the questions it answers, the
  method it applies, the caveats it respects. Distil this from the pages' synthesis, not a copy-paste.
- **Depth material** — which page bodies become `references/` files.

## Step 3: Write the skill to the review dir

Create `$SKILL_FACTORY_OUTPUT_DIR/<name>/` with:

```
<name>/
├── SKILL.md            # frontmatter (name + pushy description) + reasoning approach + key knowledge
├── references/         # depth material distilled from the cluster
│   ├── <topic>.md      # one per sub-theme; declarative knowledge, not chat
│   └── sources.md      # provenance: which bundle pages this was built from (+ their sources)
└── SKILL_FACTORY.md    # provenance manifest (see below) — NOT part of the installed skill
```

**SKILL.md body** should be lean (the trigger logic + a compact reasoning guide), pushing depth into
`references/`. Follow the structure of existing skills in this repo. Preserve `^[inferred]` /
`^[ambiguous]` markers when carrying over uncertain claims — a generated skill must not launder
synthesis into fact.

**`references/sources.md`** lists every bundle page used (by file-relative markdown link) and their upstream
`sources:` — so the skill stays auditable back to the bundle and original sources.

**`SKILL_FACTORY.md`** (factory metadata, kept out of the installable skill) records: generation
date, the cluster pages + their status/tier, the maturity filter used, and the bundle git commit/hash
if available. This lets a regenerate-on-update workflow diff later.

Optional, if the user asks: append/update a `marketplace.json` entry in the output dir (the OpenKB
one-line-install convention) — still **not** an install, just a manifest.

## Step 4: Optionally lean on skill-creator

`skill-creator` ships reusable scripts. Their path differs between a packaged install and a source
checkout, so check both layouts under `$OKF_WIKI_REPO` and use the first that exists:

- `$OKF_WIKI_REPO/.skills/skill-creator/scripts/` — source checkout.
- `$OKF_WIKI_REPO/skills/skill-creator/scripts/` — packaged install.

Whichever resolves, it holds:

- `improve_description.py` — tighten the generated `description` for better triggering.
- `package_skill.py` — bundle the skill dir into a distributable archive.
- `quick_validate.py` — sanity-check the skill's structure.

If neither path exists in this install (some installs carry only the SKILL.md files), skip this
optional step and say so. Use the scripts when present and the user wants a polished/validated
artifact; don't reinvent them.

## Step 5: Report — and stop

Tell the user:

- the path: `$SKILL_FACTORY_OUTPUT_DIR/<name>/`
- the cluster it was built from (page count + names)
- the trigger `description`
- **How to install if they want it (their decision, project-local only):**

  ```
  cp -r $SKILL_FACTORY_OUTPUT_DIR/<name> <repo>/.skills/<name>   # after copying <name>/ into .skills/, sans SKILL_FACTORY.md
  ```

  Note explicitly: review first; do not run `setup.sh` (it fans skills into global dirs); never global-install without explicit agreement.

Do **not** install it yourself. Do not write to `.skills/`. Done.

## Quality checklist

- [ ] Output went to `$SKILL_FACTORY_OUTPUT_DIR`, never `.skills/` or a global dir
- [ ] Cluster confirmed with the user; only mature pages (per `SKILL_FACTORY_MATURITY` / `tier: core`)
- [ ] `description` is pushy and accurate (when + what)
- [ ] SKILL.md body is lean; depth lives in `references/`
- [ ] `^[inferred]`/`^[ambiguous]` markers preserved; no synthesis laundered into fact
- [ ] `references/sources.md` traces back to bundle pages + their sources
- [ ] `SKILL_FACTORY.md` provenance manifest present (excluded from the installable skill)
- [ ] Report names the path and the manual, project-local-only install step; nothing auto-installed

---

Derived from Ar9av/obsidian-wiki vault-skill-factory skill (MIT).
