# Installation

Two paths in. Both end at the same place: your bundle path in the global config (`~/.config/okf-wiki/config`) and the skills discoverable by your agent.

| Path | Best for | Writes global config | Installs into all agents |
|---|---|---|---|
| [git clone + `setup.sh`](#install-via-git-clone) | Most people | Yes | Yes |
| [Let your agent do it](#let-your-agent-set-it-up) | No terminal required | Yes | Yes |

> **Upgrading from obsidian-wiki?** The config directory used to be `~/.obsidian-wiki`. If you already have it, everything keeps working. That path is still honored and nothing needs to move. See [Where the global config lives](configuration.md#where-the-global-config-lives).

## Install via git clone

```bash
git clone https://github.com/Ar9av/obsidian-wiki.git okf-wiki
cd okf-wiki
bash setup.sh
```

`setup.sh` asks for your bundle path, writes the config to `~/.config/okf-wiki/config`, symlinks skills into all your agents, and installs `wiki-update`, `wiki-query`, and `wiki-context-pack` globally so you can use them from any project.

Then open the project in your agent and say **"set up my bundle"**.

For local-only config, copy `.env.example` to `.env` and set `OKF_BUNDLE_PATH`. A `.env` in the working directory (or any parent up to `$HOME`) takes precedence over the global config. See [Configuration](configuration.md).

### What `setup.sh` wires up

1. **`.env` from `.env.example`**: copies the template if no `.env` exists yet. Edit `.env` and set `OKF_BUNDLE_PATH` before using skills.

2. **Global config** at `~/.config/okf-wiki/config` with your bundle path and the repo location. This is how skills know where to read and write. XDG-style by default; legacy `~/.obsidian-wiki` is honored if it already exists.

3. **Bootstrap symlinks**: `CLAUDE.md`, `GEMINI.md`, and `.hermes.md` are symlinked to `AGENTS.md` so all agent entry points surface the same context without drift.

4. **Project-local skill symlinks** for each supported agent:
   - `.claude/skills/` (Claude Code)
   - `.cursor/skills/` (Cursor)
   - `.windsurf/skills/` (Windsurf)
   - `.agents/skills/` (AGENTS.md-aware agents: OpenCode, Aider, Factory Droid, generic)
   - `.pi/skills/` (Pi coding agent)
   - `.kiro/skills/` (Kiro IDE/CLI)

5. **Always-on rule files** committed to the repo:
   - `AGENTS.md`: Codex, OpenClaw, OpenCode, Aider, Droid, Trae, Hermes, Pi
   - `CLAUDE.md` (symlink): Claude Code
   - `GEMINI.md` (symlink): Gemini / Antigravity
   - `.hermes.md` (symlink): Hermes
   - `.cursor/rules/okf-wiki.mdc`: Cursor (alwaysApply)
   - `.windsurf/rules/okf-wiki.md`: Windsurf (always-on)
   - `.kiro/steering/okf-wiki.md`: Kiro (inclusion: always)
   - `.agent/rules/okf-wiki.md`: Google Antigravity (alwaysApply)
   - `.agent/workflows/okf-wiki.md`: Google Antigravity (slash commands)
   - `.github/copilot-instructions.md`: GitHub Copilot (VS Code Chat)

The skill list is enumerated dynamically from `.skills/*/` at runtime. Adding or removing a skill there means a re-run of `setup.sh` picks it up everywhere.

## Let your agent set it up

The fastest path. No commands required. Give your agent this repo and say:

```text
https://github.com/Ar9av/obsidian-wiki: set up my bundle
```

The agent reads `.skills/wiki-setup/SKILL.md` from the repo, asks where you want your bundle to live, and initializes the full structure: directories, `index.md` with `okf_version: "0.2"`, `log.md`, `_cache/`, `_raw/`, `_meta/taxonomy.md`, `.manifest.json`, `okf-base.yaml`. The skill is the setup guide.

This works in any agent that can read files (Claude Code, Cursor, Windsurf, Codex, Gemini CLI, Kiro, and more). After setup, every wiki skill is available immediately.

## Supported agents

okf-wiki works with any agent that reads AGENTS.md or has a bootstrap file. The full list:

| Agent | Discovery mechanism |
|---|---|
| Claude Code | `CLAUDE.md` (symlink to `AGENTS.md`) + `.claude/skills/` |
| Cursor | `.cursor/rules/okf-wiki.mdc` (alwaysApply) + `.cursor/skills/` |
| Windsurf | `.windsurf/rules/okf-wiki.md` (always-on) + `.windsurf/skills/` |
| Codex | `AGENTS.md` |
| OpenClaw | `AGENTS.md` |
| OpenCode | `AGENTS.md` + `.agents/skills/` |
| Aider | `AGENTS.md` + `.agents/skills/` |
| Factory Droid | `AGENTS.md` + `.agents/skills/` |
| Trae | `AGENTS.md` |
| Hermes | `.hermes.md` (symlink to `AGENTS.md`) |
| Pi | `AGENTS.md` + `.pi/skills/` |
| Kiro | `.kiro/steering/okf-wiki.md` (inclusion: always) + `.kiro/skills/` |
| Gemini CLI | `GEMINI.md` (symlink to `AGENTS.md`) |
| Google Antigravity | `.agent/rules/okf-wiki.md` + `.agent/workflows/okf-wiki.md` |
| GitHub Copilot | `.github/copilot-instructions.md` |

All agents share the same skill content (portability invariant FR-7.3). Only the discovery mechanism differs.

## Open in Obsidian (optional)

Open your bundle directory in Obsidian (File, Open Vault). The wiki pages and graph view all work. Nothing about the bundle is proprietary. It is markdown files with YAML frontmatter.

Obsidian is an optional viewer. The bundle is portable by design; the source of truth is the markdown, not the viewer.

## Multiple bundles

Keep a default bundle active in `~/.config/okf-wiki/config`, or create named configs like `~/.config/okf-wiki/config.work` with `/bundle-switch new work`.

From any directory, route one request to a named bundle with `@name`:

```text
@work update wiki
@research save this
wiki-query @personal what do I know about MCP security
```

The `@name` override applies only to that request and never changes your default bundle. To change the default, use `/bundle-switch <name>`. It re-points the active symlink.

All supported agents can use this syntax after `setup.sh`, because the shared skills and always-on bootstrap files all point back to the same Config Resolution Protocol.

The routing token works with write skills (`@work update wiki`, `@research save this`) and read skills (`wiki-query @personal what do I know about X`).

## Next steps

- [Skills Reference](skills.md): what you can actually ask for
- [Configuration](configuration.md): every config variable, QMD, GitHub sync
- [Architecture](architecture.md): bundle structure, ingest stages, OKF conformance
