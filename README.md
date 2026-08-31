# okf-wiki

okf-wiki is a knowledge base that lives in your repo: an [Open Knowledge Format](https://github.com/GoogleCloudPlatform/knowledge-catalog) (OKF v0.2) bundle and a Karpathy-style [LLM wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) — plain markdown + YAML frontmatter, navigated by `index.md` and file-relative links. No database, no embeddings, no runtime: any agent or human can read, extend, and carry the bundle between tools without conversion.

To grow and maintain that bundle, okf-wiki ships **37 skills** — markdown instructions your AI coding agent executes directly — plus a small **CLI** for deterministic checks (lint, doctor, trust, manifest cache, graph export). No API keys, no vendor: the agent is the runtime.

**The point:** clone the repo, say one sentence to your agent, and you have a knowledge base
your agent can grow and query from any project.

## What's in this repo

| Path | What it is |
|---|---|
| `.skills/` | The 37 skills — markdown instructions the agent executes (ingest, query, lint, rebuild…). Each is a folder with a `SKILL.md`. |
| `okf_wiki/` + `pyproject.toml` | The `okf-wiki` Python CLI — deterministic checks and helpers (lint, doctor, trust, manifest cache, graph export, query ranking). Optional; the skills work without it. Zero runtime dependencies, Python ≥ 3.9. |
| `setup.sh` | One-shot installer: symlinks skills into Claude Code, Cursor, Windsurf, Pi, Kiro, and generic AGENTS.md agents (Codex, OpenCode, Aider, …); writes the global config. |
| `AGENTS.md` | The agent entry point. `CLAUDE.md`, `GEMINI.md`, `.hermes.md` are symlinks to it. |
| `docs/` | Full documentation: installation, skills reference, configuration, architecture. |

## Skills vs CLI — read this first

Two different things share similar names, and mixing them up is the #1 confusion:

| | Skills | CLI |
|---|---|---|
| Examples | `wiki-ingest`, `wiki-query`, `wiki-setup`, `wiki-lint` | `okf-wiki lint`, `okf-wiki doctor`, `okf-wiki cache-update` |
| What it is | Markdown instructions in `.skills/<name>/SKILL.md` that your **agent** executes | A real binary from the Python package |
| How to invoke | **Say it to your agent** in chat: *"ingest ~/research"*, *"what do I know about X"* — or `/wiki-ingest` in agents with slash-command support | **Type it in a terminal**: `okf-wiki --help` |
| Where it comes from | The `.skills/` folder, wired into your agent by `setup.sh` | `okf_wiki/cli.py`, installed with pip |

So `wiki-ingest ~/research` typed in a shell does nothing — that is a sentence for your
agent. `okf-wiki doctor` typed in a shell works once the CLI is installed.

## Install

### Path A — by hand

```bash
git clone https://github.com/azimuth0x28/okf-wiki.git
cd okf-wiki
bash setup.sh
```

`setup.sh` creates `.env` from `.env.example`, writes the global config
(`~/.config/okf-wiki/config`), and symlinks every skill into each supported agent's skills
directory. Re-running it picks up skills added or removed under `.skills/`.

Then open this project in your agent and say **"set up my bundle"** — the agent asks where
your bundle should live and initializes the full OKF v0.2 structure.

Optional, for the CLI:

```bash
pip install -e .        # or: uv pip install -e .
okf-wiki --help
```

### Path B — one prompt

Paste this into any coding agent and it does the rest:

```text
Clone https://github.com/azimuth0x28/okf-wiki, run `bash setup.sh` inside it, then read
AGENTS.md and .skills/wiki-setup/SKILL.md. Ask me where my bundle should live, initialize
the OKF v0.2 bundle there, and confirm which skills are now available.
```

Both paths end at the same place: skills discoverable by your agent, and your bundle path
in the global config. Per-agent setup matrix, multiple bundles, and `@name` routing →
[docs/installation.md](docs/installation.md).

> **Next step:** installed — now what? Where to run your agent (repo vs bundle folder),
> how to address bundles, CLI vs skills, MCP server → [docs/how-to-use.md](docs/how-to-use.md).

## First ten minutes

From any project, say these to your agent (each maps to one skill):

| You say | Skill | What happens |
|---|---|---|
| "set up my bundle" | `wiki-setup` | Creates the bundle: `index.md` with `okf_version: "0.2"`, `log.md`, taxonomy, manifest |
| "ingest ~/research" | `wiki-ingest` | Distills documents, PDFs, chat exports, URLs into cross-linked bundle pages |
| "what do I know about X" | `wiki-query` | Answers with citations from bundle pages |
| "update wiki" | `wiki-update` | Syncs the current project's knowledge into the bundle |
| "audit my bundle" | `wiki-lint` | Finds broken links, orphans, OKF violations |

In a terminal, the CLI covers the deterministic side:

```bash
okf-wiki doctor          # validate resolved config and bundle shape
okf-wiki lint <bundle>   # OKF conformance gate (exit 0/1/2) — CI-friendly
okf-wiki cache-update    # scan sources and update the SHA-256 ingest manifest
```

Full CLI reference → `okf-wiki --help`. Full skill catalog → [docs/skills.md](docs/skills.md).

## OKF v0.2 native

Every page conforms to OKF v0.2 from creation: parseable YAML frontmatter with a `type`,
reserved `index.md`/`log.md` in their defined structure, file-relative links between pages,
and extension fields (`aliases`, `provenance`, `lifecycle`, …) preserved verbatim by any
conformant consumer. A bundle looks like:

```
<bundle>/                          # a git repo is the unit of distribution
├── index.md                       # okf_version: "0.2"; master catalog
├── log.md                         # newest-first ISO-dated entries
├── concepts/  entities/  skills/  references/  synthesis/  journal/  projects/
├── _raw/  _staging/  _archives/  _readouts/  _meta/  _cache/   # ops, out of OKF scope
└── .manifest.json                 # SHA-256 delta ledger of ingests
```

Full schema and ingest pipeline → [docs/architecture.md](docs/architecture.md).

## Docs

| Looking for | Go to |
|---|---|
| Install paths, supported agents, multiple bundles | [docs/installation.md](docs/installation.md) |
| Where to run the agent, bundles, CLI vs skills, MCP | [docs/how-to-use.md](docs/how-to-use.md) |
| Every skill and when to say it | [docs/skills.md](docs/skills.md) |
| Every config variable | [docs/configuration.md](docs/configuration.md) |
| Bundle structure, ingest stages, OKF conformance | [docs/architecture.md](docs/architecture.md) |

## Attribution & license

okf-wiki is an independent project. It was founded on [Ar9av/obsidian-wiki](https://github.com/Ar9av/obsidian-wiki) (MIT) — taken as a good working example of the pattern — with one deliberate inversion: **"format not platform."** Portability is the native state of every page from the moment it is written, and the source of truth is the bundle's markdown, whatever agent or tool maintains it.

Licensed [MIT](LICENSE) — see the LICENSE file for full text.
