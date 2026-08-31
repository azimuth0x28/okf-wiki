# How to Use

A practical guide: where to run your agent, how to address bundles, and what
each moving part does. For install steps see [Installation](installation.md);
for config precedence see [Configuration](configuration.md).

## The mental model

| Piece | What it is | Where it lives |
|---|---|---|
| This repo | The control center: 37 skills, the `okf-wiki` CLI, the protocol docs | One clone anywhere |
| A bundle | Your data: a plain OKF v0.2 markdown directory (its own git repo) | Any path, e.g. `~/kb/work` |
| Global config | `~/.config/okf-wiki/config` — names the default bundle | Written once by `setup.sh` |

The repo is tooling; bundles are content. One clone serves any number of
bundles, and bundles contain no code.

## Where do you run the agent?

| Where | What you get | How to address a bundle |
|---|---|---|
| **This repo** (recommended) | All 37 skills auto-discovered via the committed symlinks | The default bundle; `@name` for one request; `/bundle-switch` to change the default |
| **Inside a bundle folder** | No skill auto-discovery — skills live in the repo | Point the agent at a skill file, install skills at user level, or use the MCP server (below) |
| **Any other project** | Same as a bundle folder | The three portable skills: `wiki-update`, `wiki-query`, `wiki-context-pack` |

### From the repo

Open your agent in the repo clone and every skill is available. The repo's
config only sets the *default* bundle — one session can serve all of them:

- `ingest ~/papers/attention into @research` — one request into the `research` bundle;
- `/bundle-switch research` — make it the default for everything that follows;
- `/bundle-switch list` — see what is configured.

You never need to `cd` into a bundle to work on it.

### From a bundle folder

An agent opened inside a bundle starts without the skill catalog (the
symlinks live in the repo clone). Three ways to close that gap — pick one:

1. **Point the agent at the skill.** Works everywhere, zero setup:

   ```text
   Read and follow /path/to/okf-wiki/.skills/wiki-ingest/SKILL.md — ingest ./sources
   ```

   Config resolution still finds the right bundle: a `.env` with
   `OKF_BUNDLE_PATH` inside the bundle folder wins over the global config.

2. **Install the skills at user level.** Symlink the skill folders into your
   agent's user-level skills directory (`~/.claude/skills/`,
   `~/.agents/skills/`, …). Then every folder — bundle, project, home — has
   the full catalog. `bash setup.sh` inside the clone does the project-local
   equivalent; the user-level copy is one `ln -s` per skill directory.

3. **Run the MCP server** and let any agent talk to the bundle as tools
   (see [below](#run-it-as-a-service-mcp--rest)).

### From another project

Three skills are designed to run with any directory as the working directory:
`wiki-update` (push project knowledge into the bundle), `wiki-query` (ask the
bundle), and `wiki-context-pack` (bounded context for another agent). The
project you are in is the *source*; the bundle stays the *destination*:

```text
Read and follow $OKF_WIKI_REPO/.skills/wiki-update/SKILL.md
```

or, with user-level skills installed, just say **"update the wiki"**.

## Skills or CLI?

| | Skills (37) | CLI (`okf-wiki`) |
|---|---|---|
| What it is | Markdown instructions your agent executes | A Python binary (`pip install -e .`) |
| How invoked | Talk: "ingest ~/docs", `/wiki-capture` | Shell: `okf-wiki lint` |
| Where it runs | Inside an agent session | Anywhere, including CI |
| Best for | Distillation, synthesis — judgment work | Deterministic checks, scripting, automation |

`wiki-ingest` is a skill — say it to your agent; there is no `okf-wiki
ingest`. `lint` exists in both: the skill reports and explains, while
`okf-wiki lint` runs the same check as `scripts/validate.sh` for CI. Useful
first commands: `okf-wiki list` (what is installed), `okf-wiki doctor`
(diagnose config). Full reference: [CLI](cli.md).

## Multiple bundles

One clone, many bundles:

```text
/bundle-switch new personal   # create a profile (copies the active config, asks for the new path)
/bundle-switch personal       # point the active symlink at it
"set up my bundle"            # initialize the OKF structure inside it
```

Each profile is `~/.config/okf-wiki/config.<name>`; the active one is
whatever the `config` symlink targets. For automatic per-directory routing,
drop a `.env` with `OKF_BUNDLE_PATH` inside each bundle folder. An inline
`@name` token routes a single request to `config.<name>` without switching.
Details: [Configuration](configuration.md).

## Run it as a service (MCP + REST)

```bash
pip install -e ".[server]"
okf-wiki server --port 8080
```

- MCP at `/mcp` (streamable HTTP): `memory_search`, `memory_read`,
  `memory_write`, `memory_context_pack`
- REST: `GET /v1/search?q=`, `GET /v1/pages/{path}`, `POST /v1/pages`,
  `GET /health`
- Auth: set `WIKI_API_KEY` (or `WIKI_ALLOW_ANONYMOUS=1` for local use)
- One server serves one bundle — the resolved `OKF_BUNDLE_PATH`. Multiple
  bundles mean one process per bundle on different ports
- Docker: `docker compose up` from the repo root

Details: [Deployment](deployment.md).

## How isolated is the install?

`setup.sh` writes exactly one thing outside the repo:
`~/.config/okf-wiki/config`. Everything else — skill symlinks, bootstrap
files, `.env` — stays inside the clone. Fully local variant:

```bash
git clone <url> okf-wiki && cd okf-wiki
cp .env.example .env   # set OKF_BUNDLE_PATH; skips the global config entirely
```

To undo the global piece later: delete `~/.config/okf-wiki/config` (and any
`config.<name>` profiles you created). Nothing else references `$HOME`.

## Why are the symlinks both committed and recreated?

Deliberate redundancy, not an accident:

- **Committed** — 53 symlinks (`.claude/skills/*`, `.agents/skills/*`, …,
  plus `CLAUDE.md`, `GEMINI.md`, `.hermes.md` → `AGENTS.md`). A fresh clone
  with symlink-aware git is fully wired with zero commands.
- **`setup.sh` re-creates them** — if your git checked the symlinks out as
  plain text files (Windows without `core.symlinks=true`), setup.sh replaces
  the stubs with real symlinks. It also generates `.env` and the global
  config, which git cannot ship.

So `setup.sh` is a repair-and-configure pass: idempotent and safe to re-run.
