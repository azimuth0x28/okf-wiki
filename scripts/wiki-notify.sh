#!/usr/bin/env bash
# Source this from your shell rc file to get wiki freshness reminders on terminal open.
#
# Setup (shell-specific):
#   zsh/bash:  source /path/to/okf-wiki/scripts/wiki-notify.sh
#   fish:      bass source /path/to/okf-wiki/scripts/wiki-notify.sh
#              (or copy _wiki_notify logic natively using fish syntax)
#
# State is bundle-scoped under <global-config-dir>/state/<bundle-id>/ — the
# global config dir is XDG-style (~/.config/okf-wiki by default), with
# the legacy ~/.obsidian-wiki honored if it already exists (see
# llm-wiki/SKILL.md Config Resolution Protocol).
# Multiple bundles are supported — all stale bundles are shown.

_wiki_notify() {
  local xdg_dir="${XDG_CONFIG_HOME:-$HOME/.config}/okf-wiki"
  local legacy_dir="$HOME/.obsidian-wiki"
  local config_dir="$xdg_dir"
  [[ -d "$legacy_dir" && ! -e "$xdg_dir" ]] && config_dir="$legacy_dir"
  local state_base="$config_dir/state"
  [[ -d "$state_base" ]] || return

  local now age_s age_h stale last bundle_path shown=0

  now=$(date +%s)

  # Iterate over all bundle state dirs
  for state_dir in "$state_base"/*/; do
    [[ -f "$state_dir/.last_update" ]] || continue

    last=$(cat "$state_dir/.last_update" 2>/dev/null || echo 0)
    age_s=$(( now - last ))

    # Only show if >20 hours stale
    (( age_s > 72000 )) || continue

    age_h=$(( age_s / 3600 ))
    stale=$(cat "$state_dir/.pending_delta" 2>/dev/null || echo 0)
    bundle_path=$(cat "$state_dir/.bundle_path" 2>/dev/null || echo "unknown bundle")

    echo "┌─ wiki: last synced ${age_h}h ago · ${bundle_path##*/}$([ "$stale" -gt 0 ] && echo " · ${stale} source(s) have new content" || echo "")"
    echo "│  /wiki-history-ingest claude   sync Claude sessions"
    echo "│  /wiki-status                  see full delta"
    echo "└─ /memory-bridge diff           compare tool memories"
    shown=$(( shown + 1 ))
  done
}

_wiki_notify
