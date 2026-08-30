# Agent Compatibility

okf-wiki is an AGENTS.md-first project: the skill instructions live in
`.skills/<name>/SKILL.md`, and every supported agent reads the same content
through its own discovery mechanism. Skill content is identical across agents;
only the bootstrap files differ (a platform constraint, never a content
decision).

## Matrix

| Agent | How it finds the skills | Entry point |
|---|---|---|
| Codex, OpenCode, Aider, Droid, Trae, Hermes, Pi, OpenClaw | reads `AGENTS.md` | `AGENTS.md` |
| Claude Code | `.claude/skills/` + `CLAUDE.md` | `CLAUDE.md` (symlink → `AGENTS.md`) |
| Gemini CLI / Antigravity | `GEMINI.md` | `GEMINI.md` (symlink → `AGENTS.md`) |
| Hermes | `.hermes.md` resolved before `AGENTS.md` | `.hermes.md` (symlink → `AGENTS.md`) |
| Cursor | `.cursor/skills/` + rules | `.cursor/rules/okf-wiki.mdc` (alwaysApply) |
| Windsurf | `.windsurf/skills/` + rules | `.windsurf/rules/okf-wiki.md` (always-on) |
| Kiro | `.kiro/skills/` + steering | `.kiro/steering/okf-wiki.md` (always) |
| GitHub Copilot | `.github/copilot-instructions.md` | auto-attached in VS Code Chat |
| Google Antigravity | `.agent/rules/` + workflows | `.agent/workflows/okf-wiki.md` |
| Generic AGENTS.md-aware agents | `.agents/skills/` symlinks | `AGENTS.md` |

The skill symlinks under `.claude/skills/`, `.agents/skills/`, etc. are
committed, so a fresh clone already wires every agent. If your git does not
preserve symlinks, run `bash setup.sh` to recreate them.

## Manual setup

1. `bash setup.sh` — recreates the skill symlinks and the bootstrap aliases
   (`CLAUDE.md`, `GEMINI.md`, `.hermes.md`).
2. Point the agent at your bundle via the [Config Resolution
   Protocol](./configuration.md) (`.env` with `OKF_BUNDLE_PATH`, or a global
   config, or an inline `@name` override).
3. In the agent, say **"Set up my bundle"** (runs the `wiki-setup` skill) or
   start with any routed command from the [skill catalog](./skills.md).

Session-history mining is available from the agent itself:

- "Mine my Codex history" → `codex-history-ingest`
- "Mine Hermes memory into the wiki" → `hermes-history-ingest`
- "Mine OpenClaw history" → `openclaw-history-ingest`
- "Mine Pi session history" → `pi-history-ingest`
- "Mine my Claude Code history" → `claude-history-ingest`

## The CLI as a second entry point

Every mechanical operation also exists as a deterministic command in the
`okf-wiki` CLI — see the [CLI Reference](./cli.md). Skills describe *how* to
work with the bundle; the CLI executes the invariant parts (lint parity with
`scripts/validate.sh`, capture, graph export, session clustering) so that CI
and external tools get the same behavior without an agent in the loop.

---

Derived from Ar9av/obsidian-wiki `docs/agents.md` (MIT).
