#!/bin/bash
#
# okf-wiki setup — configures skill discovery for all supported AI agents.
#
# Usage: bash setup.sh
#
# What it does:
#   1. Creates .env from .env.example (if .env.example is present)
#   2. Writes the global config (XDG-style, under ~/.config/okf-wiki by
#      default; legacy ~/.obsidian-wiki is honored if it already exists)
#   3. Symlinks .skills/* into each agent's expected project-local skills
#      directory:
#        - .claude/skills/      (Claude Code)
#        - .cursor/skills/      (Cursor)
#        - .windsurf/skills/    (Windsurf)
#        - .agents/skills/      (AGENTS.md-aware agents, generic)
#        - .pi/skills/          (Pi coding agent)
#        - .kiro/skills/        (Kiro IDE/CLI)
#   4. Bootstraps AGENTS.md aliases (CLAUDE.md, GEMINI.md, .hermes.md)
#   5. Prints a summary of what's ready
#
# The skill list is enumerated dynamically from .skills/*/ at runtime — adding
# or removing a skill there means a re-run of setup.sh picks it up everywhere.
# An empty or nearly empty .skills/ directory is fine: the script prints an
# informational message and exits 0.
#
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILLS_DIR="$SCRIPT_DIR/.skills"

# install_skills <target_dir> <label> [relative|absolute]
# "relative" requires target_dir under $SCRIPT_DIR and emits ../-prefixed
# targets matching the committed symlinks. Skill discovery is dynamic: every
# subdirectory of $SKILLS_DIR is treated as a skill and symlinked in.
install_skills() {
  local target_dir="$1"
  local label="$2"
  local mode="${3:-absolute}"
  case "$mode" in
    relative|absolute) ;;
    *) echo "install_skills: bad mode '$mode' (want relative|absolute)" >&2; exit 1 ;;
  esac

  local rel_prefix=""
  if [ "$mode" = "relative" ]; then
    local rel="${target_dir#"$SCRIPT_DIR"/}"
    if [ "$rel" = "$target_dir" ]; then
      echo "install_skills: relative mode requires target under \$SCRIPT_DIR ($target_dir)" >&2
      exit 1
    fi
    local slashes="${rel//[^\/]/}"
    local depth=$(( ${#slashes} + 1 )) i
    for (( i=0; i<depth; i++ )); do rel_prefix="../$rel_prefix"; done
  fi

  mkdir -p "$target_dir"
  local installed=0
  if [ -d "$SKILLS_DIR" ]; then
    for skill in "$SKILLS_DIR"/*/; do
      [ -d "$skill" ] || continue
      local skill_name link_path link_target
      skill_name="$(basename "$skill")"
      link_path="$target_dir/$skill_name"
      if [ "$mode" = "relative" ]; then
        link_target="${rel_prefix}.skills/$skill_name"
      else
        link_target="${skill%/}"
      fi
      if [ -L "$link_path" ]; then
        rm "$link_path"
      elif [ -d "$link_path" ]; then
        echo "⚠️   $link_path is a real directory, skipping symlink"
        continue
      elif [ -f "$link_path" ]; then
        # Git on Windows without core.symlinks=true writes committed symlinks
        # as regular files containing the target path. Replace with a real
        # symlink.
        rm "$link_path"
      fi
      ln -s "$link_target" "$link_path"
      # Sanity check: every skill ships a SKILL.md, so a working symlink
      # resolves it.
      [ -e "$link_path/SKILL.md" ] || { echo "install_skills: broken link $link_path → $link_target" >&2; exit 1; }
      installed=$((installed + 1))
    done
  fi
  if [ "$installed" -gt 0 ]; then
    echo "✅  Installed $installed skill(s) → $label"
  else
    echo "ℹ️   No skills found in $SKILLS_DIR — skipping $label (add a skill under .skills/<name>/ and re-run)"
  fi
}

echo ""
echo "╔══════════════════════════════════════════════════╗"
echo "║           okf-wiki — Agent Setup                  ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""

# ── Step 1: .env ──────────────────────────────────────────────
# .env.example is created by the repo bootstrap (T-0.1); if it isn't present
# yet, skip with info rather than failing — this keeps setup.sh usable on a
# fresh clone mid-bootstrap.
if [ ! -f "$SCRIPT_DIR/.env" ]; then
  if [ -f "$SCRIPT_DIR/.env.example" ]; then
    cp "$SCRIPT_DIR/.env.example" "$SCRIPT_DIR/.env"
    echo "✅  Created .env from .env.example"
    echo "    → Edit .env and set OKF_BUNDLE_PATH before using skills."
  else
    echo "ℹ️  .env.example not present — skipping .env creation (wiki-setup will interview you)"
  fi
else
  echo "✅  .env already exists"
fi

# ── Step 1b: global config ────────────────────────────────────
# XDG-style location by default; installs that already have the legacy
# ~/.obsidian-wiki keep using it so an upgrade from the source project
# doesn't strand a working config.
XDG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/okf-wiki"
LEGACY_DIR="$HOME/.obsidian-wiki"
if [ -d "$LEGACY_DIR" ] && [ ! -e "$XDG_DIR" ]; then
  GLOBAL_CONFIG_DIR="$LEGACY_DIR"
  echo "ℹ️  Legacy ~/.obsidian-wiki found — honoring it for this install"
else
  GLOBAL_CONFIG_DIR="$XDG_DIR"
fi
GLOBAL_CONFIG="$GLOBAL_CONFIG_DIR/config"
mkdir -p "$GLOBAL_CONFIG_DIR"

# Read OKF_BUNDLE_PATH from .env if it's already set; otherwise leave empty
# (wiki-setup will interview the user).
BUNDLE_PATH=""
if [ -f "$SCRIPT_DIR/.env" ]; then
  BUNDLE_PATH=$(grep -E '^OKF_BUNDLE_PATH=' "$SCRIPT_DIR/.env" | cut -d'=' -f2- | sed 's/^"//;s/"$//')
fi

# Write global config with quoted path (preserves spaces).
# Guard: NEVER overwrite an existing global config. The active `config`
# may be a symlink into the user's real bundle profiles (see bundle-switch)
# — writing through it would clobber their bundle. Create only when absent.
if [ -e "$GLOBAL_CONFIG" ] || [ -L "$GLOBAL_CONFIG" ]; then
  echo "ℹ️  Global config already exists at $GLOBAL_CONFIG — left untouched"
else
  cat > "$GLOBAL_CONFIG" <<EOF
OKF_BUNDLE_PATH="$BUNDLE_PATH"
OKF_WIKI_REPO="$SCRIPT_DIR"
EOF
  echo "✅  Global config written to $GLOBAL_CONFIG"
fi

# ── Step 1c: Bootstrap symlinks ──────────────────────────────
# AGENTS.md is the canonical agent entry point. CLAUDE.md, GEMINI.md, and
# .hermes.md are symlinks to it so all entry points surface the same context
# without drift. Hermes resolves .hermes.md before AGENTS.md, so a symlink
# keeps a single source of truth.
for alias_name in CLAUDE.md GEMINI.md .hermes.md; do
  alias_path="$SCRIPT_DIR/$alias_name"
  if [ -L "$alias_path" ]; then
    rm "$alias_path"
  elif [ -f "$alias_path" ]; then
    echo "⚠️   $alias_name is a regular file, replacing with symlink"
    rm "$alias_path"
  fi
  ln -s AGENTS.md "$alias_path"
done
echo "✅  CLAUDE.md, GEMINI.md, .hermes.md → AGENTS.md"

# ── Step 2: Symlink skills into agent directories ─────────────
# Project-local skill dirs. Each is where the matching agent looks for skills
# scoped to this repo. The list of skills inside is dynamic — see
# install_skills above.
AGENT_DIRS=(
  ".claude/skills"
  ".cursor/skills"
  ".windsurf/skills"
  ".agents/skills"
  ".pi/skills"      # Pi coding agent
  ".kiro/skills"    # Kiro IDE/CLI
)

for agent_dir in "${AGENT_DIRS[@]}"; do
  install_skills "$SCRIPT_DIR/$agent_dir" "$agent_dir/" relative
done

# ── Step 3: Summary ──────────────────────────────────────────
SKILL_COUNT=0
if [ -d "$SKILLS_DIR" ]; then
  for _s in "$SKILLS_DIR"/*/; do
    [ -d "$_s" ] || continue
    SKILL_COUNT=$((SKILL_COUNT + 1))
  done
fi

echo ""
echo "───────────────────────────────────────────────────"
echo " Setup complete!"
echo ""
echo " Skills found:    $SKILL_COUNT"
echo " Global config:   $GLOBAL_CONFIG"
echo " Agents ready:    Claude Code, Cursor, Windsurf, Pi, Kiro,"
echo "                  OpenCode, Aider, Factory Droid, generic AGENTS.md agents"
echo ""
echo " Bootstrap files:"
echo "   AGENTS.md                            → Codex, OpenClaw, OpenCode, Aider, Droid, Trae, Hermes, Pi"
echo "   CLAUDE.md  (symlink)                 → Claude Code"
echo "   GEMINI.md  (symlink)                 → Gemini / Antigravity"
echo "   .hermes.md (symlink)                 → Hermes"
echo "   .cursor/rules/okf-wiki.mdc           → Cursor (alwaysApply)"
echo "   .windsurf/rules/okf-wiki.md          → Windsurf (always-on)"
echo "   .kiro/steering/okf-wiki.md           → Kiro (inclusion: always)"
echo "   .agent/rules/okf-wiki.md             → Google Antigravity (alwaysApply)"
echo "   .agent/workflows/okf-wiki.md         → Google Antigravity (slash commands)"
echo "   .github/copilot-instructions.md      → GitHub Copilot (VS Code Chat)"
echo "   .claude/hooks/okf-wiki-stop-capture.sh → Claude Code Stop hook"
echo ""
echo " Next steps:"
echo "   1. Open this project in your agent"
echo "   2. Say: \"Set up my bundle\""
echo ""
echo " From any other project:"
echo "   /wiki-update       → sync knowledge into your bundle"
echo "   /wiki-query        → ask questions against your bundle"
echo "   /wiki-context-pack → compile bounded context for another agent"
echo ""
echo " Derived from Ar9av/obsidian-wiki (MIT)."
echo "───────────────────────────────────────────────────"
echo ""