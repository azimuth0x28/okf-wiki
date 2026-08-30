---
name: wiki-history-ingest
description: >
  Unified wiki-history-ingest entrypoint for conversation/session sources. Use this when the user says
  "/wiki-history-ingest claude", "/wiki-history-ingest copilot", "/wiki-history-ingest codex",
  "/wiki-history-ingest hermes", "/wiki-history-ingest openclaw", "/wiki-history-ingest pi", or
  asks to ingest agent history without naming the underlying skill.
  This router dispatches to the specialized history skill.
---

# Unified History Ingest Router

This is a thin router for **history sources only**. It does not replace [wiki-ingest](../wiki-ingest/SKILL.md) for documents.

## Configuration

Each vendor history skill expects its own `*_HISTORY_PATH` environment variable. Resolve config via the [Config Resolution Protocol](../okf-wiki/SKILL.md) (walk up from CWD for `.env`, then global config), then export:

| Variable | Agent | Typical default |
|---|---|---|
| `CLAUDE_HISTORY_PATH` | Claude Code | `~/.claude` |
| `CODEX_HISTORY_PATH` | Codex CLI | `~/.codex` |
| `COPILOT_HISTORY_PATH` | GitHub Copilot | `~/.copilot` |
| `HERMES_HISTORY_PATH` | Hermes | `~/.hermes` |
| `OPENCLAW_HISTORY_PATH` | OpenClaw | `~/.openclaw` |
| `PI_HISTORY_PATH` | Pi coding agent | `~/.pi/agent/sessions` |

If the variable is unset, the destination skill falls back to the path listed above. Legacy `~/.obsidian-wiki` config is still honored; new installs use `~/.config/okf-wiki`.

## Subcommands

If the user invokes `/wiki-history-ingest <target>` (or equivalent text command), dispatch directly:

| Subcommand | Route To | Skill file |
|---|---|---|
| `claude` | `claude-history-ingest` | [claude-history-ingest/SKILL.md](../claude-history-ingest/SKILL.md) |
| `codex` | `codex-history-ingest` | [codex-history-ingest/SKILL.md](../codex-history-ingest/SKILL.md) |
| `copilot` | `copilot-history-ingest` | [copilot-history-ingest/SKILL.md](../copilot-history-ingest/SKILL.md) |
| `hermes` | `hermes-history-ingest` | [hermes-history-ingest/SKILL.md](../hermes-history-ingest/SKILL.md) |
| `openclaw` | `openclaw-history-ingest` | [openclaw-history-ingest/SKILL.md](../openclaw-history-ingest/SKILL.md) |
| `pi` | `pi-history-ingest` | [pi-history-ingest/SKILL.md](../pi-history-ingest/SKILL.md) |
| `auto` | infer from context using rules below | — |

## Routing Rules

1. If the user explicitly says `claude`, `codex`, `copilot`, `hermes`, `openclaw`, or `pi`, route directly.
2. If the user provides a path/source:
   - `~/.claude` or Claude memory/session JSONL artifacts → `claude-history-ingest`
   - `~/.codex` or rollout/session index artifacts → `codex-history-ingest`
   - `~/.copilot`, `session-store.db`, VS Code copilot-chat transcripts → `copilot-history-ingest`
   - `~/.hermes` or Hermes memories/session artifacts → `hermes-history-ingest`
   - `~/.openclaw` or OpenClaw MEMORY.md/session JSONL artifacts → `openclaw-history-ingest`
   - `~/.pi/agent/sessions` or Pi session JSONL artifacts → `pi-history-ingest`
3. If ambiguous, ask one short clarification:
   - "Should I ingest `claude`, `codex`, `copilot`, `hermes`, `openclaw`, or `pi` history?"

## Execution Contract

- After routing, execute the destination skill's workflow exactly.
- Do not duplicate destination logic in this file.
- Leave manifest/index/log update semantics to the destination skill.
- Every page written by a destination skill must carry OKF v0.2 frontmatter (`type`, `generated`, `status`) — see [okf-wiki §Schema](../okf-wiki/SKILL.md) for the canonical mapping.
- `generated.by` must use the acting agent in `<producer>/<version>` format; fallback: `okf-wiki/<version>`. Human-only invariant: `draft→stable` and `stable→verified` transitions must be performed by a human (`human:<id>`). Staged `superseded_by` entries are allowed per the core [Lifecycle](../okf-wiki/SKILL.md).
- Pages connect via file-relative markdown links (`[topic](../concepts/topic.md)`); forward-references are legal. Out-of-scope content uses `_raw/`, `_staging/`, `_archives/`, `_readouts/`, `_meta/`, `_cache/` directories.

## UX Convention

- Use [wiki-ingest](../wiki-ingest/SKILL.md) for **documents/content sources**.
- Use `wiki-history-ingest` for **agent history sources**.

Examples:

- `/wiki-history-ingest claude`
- `/wiki-history-ingest codex`
- `/wiki-history-ingest copilot`
- `/wiki-history-ingest hermes`
- `/wiki-history-ingest openclaw`
- `/wiki-history-ingest pi`
- `$wiki-history-ingest claude` (agents that use `$skill` invocation)
- `$wiki-history-ingest copilot`

---

Derived from Ar9av/obsidian-wiki wiki-history-ingest skill (MIT).
