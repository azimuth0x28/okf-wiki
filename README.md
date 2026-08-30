# What is okf-wiki

okf-wiki is a skill-based framework for building and maintaining knowledge bases where the
store is natively an **OKF v0.2 (Open Knowledge Format)** bundle. The knowledge base is
a distributable unit — a directory of markdown files — that any AI agent (Claude, Codex,
Gemini, Copilot, Cursor, Windsurf, Kiro, OpenClaw, pi, and others) and any human can read,
extend, and transfer between tools without conversion. Producer and consumer are independent;
trust and provenance are first-class entities of the format.

The framework is derived from Ar9av/obsidian-wiki (MIT) with one key inversion: instead of
"Obsidian is the IDE," the guiding principle is **"format not platform."** The knowledge you
compile is portable by design, not as an export option but as the native state of every page
from the moment it is written.

## Benchmark

Structural questions — "how is X connected to Y," "which pages hold my bundle together,"
"what breaks if I delete this" — are where a plain agent is weakest. It has to grep every
file and reconstruct the link graph by hand every single time.

Same model, same bundle, same questions. The only difference is whether the wiki framework
was installed:

| | Plain agent | With obsidian-wiki |
|---|---|---|
| **Time to answer** | 81s | **19s** — 4.4× faster |
| **Correct answers** | 44% | **83%** |
| **Tool calls used** | 9.9 | **4.6** |
| **API cost** | $0.202 | $0.208 — unchanged |

These numbers were measured on the source project (obsidian-wiki, Claude Sonnet, headless,
38-page vault). The same performance profile applies to okf-wiki since the core retrieval
mechanism is identical.

## OKF v0.2 native

okf-wiki writes every page in conformance with OKF v0.2 from the moment of creation. The three
conformance rules are:

1. Every non-reserved `.md` file has parseable YAML frontmatter.
2. Every such file has a non-empty `type` field in its frontmatter.
3. Reserved files (`index.md`, `log.md`) follow their defined structure.

Consumers are required to accept: missing optional fields, unknown `type` values, unknown
frontmatter keys, broken links, and missing `index.md` files. Extension fields (such as
`aliases`, `relationships`, `provenance`, `base_confidence`, `tier`, `lifecycle_changed`,
`updated`, `superseded_by`, and `lifecycle`) are preserved verbatim by any conformant
consumer — your enriched metadata travels with the bundle.

## Quick start

```bash
# 1. Install into your agents
bash setup.sh

# 2. Point at your bundle and initialize if it's new
export OKF_BUNDLE_PATH=~/my-brain
okf-wiki setup   # or: wiki-setup skill in your agent

# 3. Ingest knowledge
wiki-ingest ~/research      # any documents, PDFs, chat exports, URLs
```

## Skills

okf-wiki ships **37 skills** (adapted from the 40 in the source project: 30 adapted,
1 rewritten core, 3 transformed, 3 preserved as meta). Three Obsidian-specific skills were
removed: graph-colorize, wiki-dashboard, and obsidian-layout-adjustment.

Full catalog → **[Skills Reference](docs/skills.md)**

## Bundle anatomy

A complete okf-wiki bundle (OKF v0.2) looks like this:

```
<bundle>/                          # git repo recommended as unit of distribution
├── index.md                       # okf_version: "0.2"; master catalog
├── log.md                         # Newest-first, ISO-dated entries
├── AGENTS.md                      # Owner conventions (extends, not an OKF concept)
├── concepts/  entities/  skills/  references/  synthesis/  journal/  projects/
│   ├── index.md                   # Per-dir, no frontmatter
│   └── <concept>.md               # OKF v0.2 + extension fields
├── _raw/  _staging/  _archives/  _readouts/  _meta/  _cache/  # Out of OKF scope
│   ├── _meta/taxonomy.md
│   └── _cache/hot.md
├── _insights.md
├── .manifest.json                 # Delta-ledger of ingests (SHA-256)
└── .manifest.lock                 # Advisory lock
```

Directories prefixed with `_` and dot-files are outside OKF conformance scope and are
excluded from validation. They contain staging, caching, and operational artifacts.

## Attribution

okf-wiki is **derived from Ar9av/obsidian-wiki** ([MIT](https://github.com/Ar9av/obsidian-wiki)).

## License

[MIT](LICENSE) — see LICENSE file for full text.
