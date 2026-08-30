#!/usr/bin/env bash
# ============================================================================
# migrate-vault.sh — Obsidian vault → OKF v0.2 bundle migration pipeline
# ============================================================================
# Deterministic, idempotent, backup-first. Operates on a COPY of the vault;
# the original is never modified in-place.
#
# Usage:
#   migrate-vault.sh [--dry-run] <vault-path>
#   migrate-vault.sh --help
#
# Output:
#   <vault-path>.migrated-<timestamp>/  — the migrated OKF v0.2 bundle
#   <vault-path>.bak-<timestamp>/       — backup of the original vault
#
# Pipeline stages:
#   1. BACKUP — cp -a the vault to a timestamped sibling directory
#   2. INVENTORY — classify files, build page map
#   3. FRONTMATTER TRANSFORM — category→type, created→generated, lifecycle→status, etc.
#   4. WIKILINK CONVERSION — [[...]] → file-relative markdown links
#   5. v0.1→v0.2 UPGRADE — timestamp→generated, # Citations→sources
#   6. SERVICE FILES — hot.md→_cache/, index.md regen, log.md, obsidian artifacts→_archives/
#   7. VERIFY — validate.sh + extension round-trip + edge comparison
#   8. IDEMPOTENCY — all transformers detect already-OKF fields and skip
# ============================================================================

set -euo pipefail

# --- helpers ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

die()   { echo -e "${RED}FATAL: $*${NC}" >&2; exit 1; }
info()  { echo -e "${CYAN}===${NC} ${BOLD}$*${NC}"; }
ok()    { echo -e "  ${GREEN}✓${NC} $*"; }
warn()  { echo -e "  ${YELLOW}⚠${NC} $*"; }
detail(){ echo -e "    $*"; }

# --- argument parsing ---
DRY_RUN=false
VAULT=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run) DRY_RUN=true; shift ;;
    --help|-h)
      echo "Usage: migrate-vault.sh [--dry-run] <vault-path>"
      echo ""
      echo "Migrate an Obsidian vault to an OKF v0.2 bundle."
      echo "The original vault is NEVER modified — migration writes to a new directory."
      echo ""
      echo "Options:"
      echo "  --dry-run  Inventory + transform plan, zero writes (beyond backup)"
      echo "  --help     Show this help"
      echo ""
      echo "Output:"
      echo "  <vault>.bak-<ts>/         Backup of the original vault"
      echo "  <vault>.migrated-<ts>/    The migrated OKF v0.2 bundle"
      echo ""
      echo "Idempotent: re-running on an already-migrated bundle leaves the bundle"
      echo "content byte-identical (a fresh backup + output directory are still created)."
      exit 0
      ;;
    -*) die "Unknown option: $1. Use --help for usage." ;;
    *)  VAULT="$1"; shift ;;
  esac
done

[[ -z "$VAULT" ]] && die "Missing vault path. Usage: migrate-vault.sh [--dry-run] <vault-path>"
[[ ! -d "$VAULT" ]] && die "'$VAULT' is not a directory"

VAULT="$(realpath "$VAULT")"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
BACKUP_DIR="${VAULT}.bak-${TIMESTAMP}"
OUTPUT_DIR="${VAULT}.migrated-${TIMESTAMP}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VALIDATE_SCRIPT="${SCRIPT_DIR}/validate.sh"

# ============================================================================
# Stage 1: BACKUP (mandatory, always runs)
# ============================================================================
info "Stage 1: Backup"
cp -a "$VAULT" "$BACKUP_DIR" || die "Backup failed — aborting"
ok "Backup created: $BACKUP_DIR"

if $DRY_RUN; then
  info "DRY RUN mode — inventory + transform plan only, no migration writes"
fi

# Dry-run inventories the original vault directly — no working copy is created
INVENTORY_DIR="$OUTPUT_DIR"
if $DRY_RUN; then
  INVENTORY_DIR="$VAULT"
else
  # Create working copy for migration
  info "Creating working copy at $OUTPUT_DIR"
  cp -a "$VAULT" "$OUTPUT_DIR"
  # A vault that is itself a git repo must not carry .git into the bundle
  rm -rf "$OUTPUT_DIR/.git"
fi

# ============================================================================
# Stage 2: INVENTORY
# ============================================================================
info "Stage 2: Inventory"

KNOWLEDGE_PAGES=()
OBSIDIAN_ARTIFACTS=()
OUT_OF_SCOPE=()
V01_PAGES=()
PAGE_MAP_FILE="$(mktemp)"

cd "$INVENTORY_DIR"

while IFS= read -r -d '' file; do
  rel="${file#./}"
  basename=$(basename "$file")

  # Out-of-scope: _-prefixed dirs/files, dot-files/dirs (except .obsidian/)
  if [[ "$rel" == _* || "$rel" == .* ]]; then
    if [[ "$rel" == .obsidian/* || "$rel" == .obsidian-snippet* || "$rel" == .base* ]]; then
      OBSIDIAN_ARTIFACTS+=("$rel")
    else
      OUT_OF_SCOPE+=("$rel")
    fi
    continue
  fi

  # Non-markdown files → out of scope
  if [[ "$basename" != *.md ]]; then
    OUT_OF_SCOPE+=("$rel")
    continue
  fi

  # Check for v0.1 markers (timestamp: in frontmatter)
  if head -10 "$file" | grep -qE "^timestamp:" 2>/dev/null; then
    V01_PAGES+=("$rel")
  fi

  KNOWLEDGE_PAGES+=("$rel")

  # Build page map: basename (without .md) → relative path
  page_basename="${basename%.md}"
  echo "${page_basename}=${rel}" >> "$PAGE_MAP_FILE"
done < <(find . -type f -not -path "*/.git/*" -print0 | sort -z)

cd - > /dev/null

# Print inventory summary
echo ""
detail "Knowledge pages:    ${#KNOWLEDGE_PAGES[@]}"
detail "Obsidian artifacts: ${#OBSIDIAN_ARTIFACTS[@]}"
detail "Out-of-scope:       ${#OUT_OF_SCOPE[@]}"
detail "v0.1 legacy pages:  ${#V01_PAGES[@]}"
echo ""

# Count wikilinks before migration
WIKILINK_COUNT_BEFORE=0
for page in ${KNOWLEDGE_PAGES[@]+"${KNOWLEDGE_PAGES[@]}"}; do
  count=$(grep -c '\[\[' "$INVENTORY_DIR/$page" 2>/dev/null || true)
  WIKILINK_COUNT_BEFORE=$((WIKILINK_COUNT_BEFORE + ${count:-0}))
done
detail "Wikilinks before migration: $WIKILINK_COUNT_BEFORE"

if $DRY_RUN; then
  echo ""
  info "DRY RUN — transform plan (no writes to output)"
  echo ""
  for page in ${KNOWLEDGE_PAGES[@]+"${KNOWLEDGE_PAGES[@]}"}; do
    detail "Would transform: $page"
  done
  for art in ${OBSIDIAN_ARTIFACTS[@]+"${OBSIDIAN_ARTIFACTS[@]}"}; do
    detail "Would archive:   $art → _archives/obsidian/"
  done
  echo ""
  info "Dry run complete. No migration performed."
  rm -f "$PAGE_MAP_FILE"
  exit 0
fi

# ============================================================================
# Stage 3-5: TRANSFORM (python3 — frontmatter + wikilinks + v0.1 upgrade)
# ============================================================================
info "Stage 3-5: Frontmatter Transform + Wikilink Conversion + v0.1 Upgrade"

export MIGRATE_OUTPUT_DIR="$OUTPUT_DIR"
export MIGRATE_PAGE_MAP="$PAGE_MAP_FILE"
export MIGRATE_V01_PAGES="$(printf '%s\n' ${V01_PAGES[@]+"${V01_PAGES[@]}"})"
export MIGRATE_KNOWLEDGE_PAGES="$(printf '%s\n' ${KNOWLEDGE_PAGES[@]+"${KNOWLEDGE_PAGES[@]}"})"
export MIGRATE_STATS_FILE="$(mktemp)"

python3 << 'PYEOF'
import sys, os, re, json
from datetime import datetime, timedelta, timezone

output_dir = os.environ['MIGRATE_OUTPUT_DIR']
page_map_file = os.environ['MIGRATE_PAGE_MAP']
v01_pages_str = os.environ.get('MIGRATE_V01_PAGES', '')
knowledge_pages_str = os.environ.get('MIGRATE_KNOWLEDGE_PAGES', '')
stats_file = os.environ.get('MIGRATE_STATS_FILE', '')

# --- load page map: basename -> relative path ---
page_map = {}
if page_map_file and os.path.exists(page_map_file):
    with open(page_map_file) as f:
        for line in f:
            line = line.strip()
            if '=' in line:
                k, v = line.split('=', 1)
                page_map[k] = v

v01_pages = set(v01_pages_str.split('\n')) if v01_pages_str else set()
knowledge_pages = [p for p in knowledge_pages_str.split('\n') if p] if knowledge_pages_str else []

stats = {
    'pages_transformed': 0, 'pages_skipped': 0,
    'wikilinks_converted': 0, 'wikilinks_unmatched': 0, 'wikilinks_forward_ref': 0,
    'v01_upgraded': 0, 'frontmatter_errors': 0,
}

# ========================================================================
# Frontmatter helpers
# ========================================================================

def parse_frontmatter(text):
    """Extract frontmatter lines between first two --- markers."""
    lines = text.split('\n')
    if not lines or lines[0].strip() != '---':
        return None, 0, False
    end_idx = None
    for i in range(1, len(lines)):
        if lines[i].strip() == '---':
            end_idx = i
            break
    if end_idx is None:
        return None, 0, False
    return lines[1:end_idx], end_idx + 1, True

def get_fm_field(fm_lines, field):
    """Get the value of a simple top-level field from frontmatter lines."""
    for line in fm_lines:
        # Only match top-level fields: line must NOT start with whitespace
        if line and line[0] in (' ', '\t'):
            continue
        stripped = line.strip()
        if stripped.startswith(field + ':'):
            val = stripped[len(field)+1:].strip()
            if (val.startswith('"') and val.endswith('"')) or \
               (val.startswith("'") and val.endswith("'")):
                val = val[1:-1]
            return val
    return None

def has_fm_field(fm_lines, field):
    """Check if a top-level field exists in frontmatter (ignores nested sub-fields)."""
    for line in fm_lines:
        stripped = line.strip()
        # Only match top-level fields: line must NOT start with whitespace
        if line and line[0] not in (' ', '\t') and stripped.startswith(field + ':'):
            return True
    return False

def category_to_type(cat):
    """Map category string to TitleCase type."""
    cat_clean = cat.strip().strip('"').strip("'")
    mapping = {
        'concept': 'Concept', 'concepts': 'Concept',
        'entity': 'Entity', 'entities': 'Entity',
        'skill': 'Skill', 'skills': 'Skill',
        'reference': 'Reference', 'references': 'Reference',
        'synthesis': 'Synthesis',
        'project': 'Project', 'projects': 'Project',
        'journal': 'Journal',
    }
    cat_lower = cat_clean.lower()
    if cat_lower in mapping:
        return mapping[cat_lower]
    if cat_lower.endswith('s') and cat_lower[:-1] in mapping:
        return mapping[cat_lower[:-1]]
    if cat_clean:
        return cat_clean[0].upper() + cat_clean[1:]
    return 'Concept'

def compute_stale_after(updated_str):
    """Compute stale_after = updated + 90 days."""
    if not updated_str:
        return None
    try:
        updated_str = updated_str.strip().strip('"').strip("'")
        dt = datetime.fromisoformat(updated_str.replace('Z', '+00:00'))
        stale = (dt + timedelta(days=90)).astimezone(timezone.utc)
        return stale.strftime('%Y-%m-%dT%H:%M:%SZ')
    except (ValueError, AttributeError):
        return None

# ========================================================================
# Frontmatter transform
# ========================================================================

def transform_frontmatter(fm_lines, filepath):
    """Transform Obsidian frontmatter to OKF v0.2.
    Returns (new_fm_lines, changed, errors)."""
    result = []
    changed = False
    errors = []
    i = 0

    already_has_type = has_fm_field(fm_lines, 'type')
    already_has_generated = has_fm_field(fm_lines, 'generated')
    already_has_description = has_fm_field(fm_lines, 'description')
    already_has_status = has_fm_field(fm_lines, 'status')
    already_has_stale = has_fm_field(fm_lines, 'stale_after')

    append_fields = []

    while i < len(fm_lines):
        line = fm_lines[i]
        stripped = line.strip()

        # --- category: -> type: ---
        if stripped.startswith('category:') and not already_has_type:
            cat_val = stripped[len('category:'):].strip().strip('"').strip("'")
            result.append('type: ' + category_to_type(cat_val))
            changed = True
            i += 1
            continue

        # --- created: -> generated: ---
        if stripped.startswith('created:') and not already_has_generated:
            created_val = stripped[len('created:'):].strip().strip('"').strip("'")
            result.append('generated:')
            result.append('  by: okf-wiki/0.1.0')
            result.append('  at: ' + created_val)
            changed = True
            i += 1
            continue

        # --- lifecycle: -> status: (+ extensions) ---
        if stripped.startswith('lifecycle:') and not already_has_status:
            lc_val = stripped[len('lifecycle:'):].strip().strip('"').strip("'")

            if lc_val == 'draft':
                result.append('status: draft')
            elif lc_val in ('reviewed', 'stable'):
                result.append('status: stable')
            elif lc_val == 'verified':
                result.append('status: stable')
                now = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
                append_fields.append('verified:')
                append_fields.append('  - by: human:migration')
                append_fields.append('    at: ' + now)
            elif lc_val == 'disputed':
                result.append('status: draft')
                append_fields.append('lifecycle: disputed')
                # lifecycle_reason is already passed through from original frontmatter
            elif lc_val == 'archived':
                result.append('status: deprecated')
                # superseded_by passes through verbatim from the original
                # frontmatter — re-appending it here would duplicate the key
            else:
                result.append('status: ' + lc_val)

            changed = True
            i += 1
            continue

        # --- summary: -> description: ---
        if stripped.startswith('summary:') and not already_has_description:
            desc_val = stripped[len('summary:'):].strip()
            result.append('description: ' + desc_val)
            changed = True
            i += 1
            continue

        # --- sources: transform to v0.2 list form ---
        if stripped.startswith('sources:'):
            # Check if already v0.2 form (has resource: sub-keys)
            is_v02 = False
            j = i + 1
            while j < len(fm_lines):
                sub = fm_lines[j].strip()
                if sub.startswith('-') and 'resource:' in sub:
                    is_v02 = True
                    break
                if sub and not sub.startswith('-') and not sub.startswith('  ') and not sub.startswith('\t'):
                    break
                j += 1

            if is_v02:
                result.append(line)
                i += 1
                continue

            src_val = stripped[len('sources:'):].strip()

            # Case 1: inline list sources: [a, b, c]
            if src_val.startswith('[') and src_val.endswith(']'):
                inner = src_val[1:-1].strip()
                if inner:
                    items = [x.strip().strip('"').strip("'") for x in inner.split(',')]
                    result.append('sources:')
                    for item in items:
                        if item:
                            result.append('  - resource: ' + item)
                else:
                    result.append('sources: []')
                changed = True
                i += 1
                continue

            # Case 2: single value on same line
            if src_val and not src_val.startswith('-'):
                result.append('sources:')
                result.append('  - resource: ' + src_val.strip().strip('"').strip("'"))
                changed = True
                i += 1
                continue

            # Case 3: block list
            result.append('sources:')
            i += 1
            while i < len(fm_lines):
                sub = fm_lines[i].strip()
                if sub.startswith('-'):
                    item = sub[1:].strip().strip('"').strip("'")
                    if item:
                        result.append('  - resource: ' + item)
                    changed = True
                    i += 1
                elif sub == '' or sub.startswith('#'):
                    result.append(fm_lines[i])
                    i += 1
                else:
                    break
            continue

        # --- timestamp: -> generated: (v0.1 upgrade) ---
        if stripped.startswith('timestamp:') and not already_has_generated:
            ts_val = stripped[len('timestamp:'):].strip().strip('"').strip("'")
            result.append('generated:')
            result.append('  by: okf-wiki/0.1.0')
            result.append('  at: ' + ts_val)
            changed = True
            i += 1
            continue

        # --- okf_version: "0.1" -> "0.2" ---
        if stripped.startswith('okf_version:') and '"0.1"' in stripped:
            result.append('okf_version: "0.2"')
            changed = True
            i += 1
            continue

        # --- Pass through ---
        result.append(line)
        i += 1

    # Add stale_after if not present
    if not already_has_stale:
        updated = get_fm_field(fm_lines, 'updated')
        if updated:
            stale = compute_stale_after(updated)
            if stale:
                result.append('stale_after: ' + stale)
                changed = True

    # Add append fields
    if append_fields:
        result.extend(append_fields)
        changed = True

    return result, changed, errors

# ========================================================================
# Wikilink conversion
# ========================================================================

def convert_wikilinks(text, source_relpath):
    """Convert [[wikilinks]] to markdown links in text body."""
    lines = text.split('\n')

    # Find body start (after second ---)
    body_start = 0
    fm_count = 0
    for i, line in enumerate(lines):
        if line.strip() == '---':
            fm_count += 1
            if fm_count == 2:
                body_start = i + 1
                break

    if body_start == 0:
        return text, 0, 0, 0

    header = '\n'.join(lines[:body_start])
    body = '\n'.join(lines[body_start:])

    converted = 0
    unmatched = 0
    forward_ref = 0

    def replace_wikilink(match):
        nonlocal converted, unmatched, forward_ref
        inner = match.group(1)

        # Parse [[target|display]] or [[target]]
        if '|' in inner:
            target, display = inner.split('|', 1)
            target = target.strip()
            display = display.strip()
        else:
            target = inner.strip()
            display = target

        # Split heading fragment ([[page#section]]) — resolve the base page,
        # then re-append the fragment to the resolved relative link
        fragment = ''
        if '#' in target:
            target, fragment = target.split('#', 1)
            target = target.strip()
            fragment = fragment.strip()

        # Strip .md extension if present
        clean_target = target[:-3] if target.endswith('.md') else target

        def emit_link(rel):
            link = rel + ('#' + fragment if fragment else '')
            # Percent-encode spaces so filenames with spaces produce valid links
            return '[' + display + '](' + link.replace(' ', '%20') + ')'

        # Path-based wikilink (contains /) -> always convert to link
        if '/' in clean_target:
            target_path = clean_target if clean_target.endswith('.md') else clean_target + '.md'
            try:
                rel = os.path.relpath(
                    os.path.join(output_dir, target_path),
                    os.path.join(output_dir, os.path.dirname(source_relpath))
                )
            except ValueError:
                rel = target_path
            if not rel.startswith('.'):
                rel = './' + rel
            forward_ref += 1
            converted += 1
            return emit_link(rel)

        # Bare-title wikilink -> look up in page_map
        basename = clean_target
        if basename in page_map:
            target_path = page_map[basename]
            try:
                rel = os.path.relpath(
                    os.path.join(output_dir, target_path),
                    os.path.join(output_dir, os.path.dirname(source_relpath))
                )
            except ValueError:
                rel = target_path
            if not rel.startswith('.'):
                rel = './' + rel
            converted += 1
            return emit_link(rel)

        # Unmatched bare-title -> plain text (display keeps any #fragment)
        unmatched += 1
        return display

    body = re.sub(r'\[\[([^\]]+)\]\]', replace_wikilink, body)

    result = header + '\n' + body if header else body
    return result, converted, unmatched, forward_ref

# ========================================================================
# v0.1 body upgrade
# ========================================================================

def upgrade_v01_body(text):
    """Upgrade v0.1 body: remove # Citations section, extract to sources list."""
    lines = text.split('\n')

    citations_start = None
    citations_end = None
    for i, line in enumerate(lines):
        stripped = line.strip()
        # Match any heading level (#, ##, ###, etc.) containing 'citation'
        if stripped.startswith('#') and 'citation' in stripped.lower():
            citations_start = i
        elif citations_start is not None and stripped.startswith('#'):
            citations_end = i
            break

    if citations_start is None:
        return text, []

    if citations_end is None:
        citations_end = len(lines)

    sources = []
    for i in range(citations_start + 1, citations_end):
        line = lines[i].strip()
        if line.startswith('- '):
            item = line[2:].strip()
            if item:
                sources.append(item)

    new_lines = lines[:citations_start] + lines[citations_end:]
    return '\n'.join(new_lines), sources

# ========================================================================
# MAIN TRANSFORM LOOP
# ========================================================================

per_file_decisions = []

for page_rel in knowledge_pages:
    filepath = os.path.join(output_dir, page_rel)
    basename = os.path.basename(page_rel)

    # Skip reserved files and hot.md (handled in Stage 6)
    if basename in ('index.md', 'log.md'):
        continue
    if page_rel == 'hot.md':
        continue
    if not os.path.exists(filepath):
        continue

    with open(filepath, 'r') as f:
        original = f.read()

    fm_lines, body_start, has_fm = parse_frontmatter(original)

    if not has_fm:
        stats['frontmatter_errors'] += 1
        per_file_decisions.append('  SKIP  ' + page_rel + ' — no YAML frontmatter (moved to _staging/migration-review/)')
        staging_dir = os.path.join(output_dir, '_staging', 'migration-review')
        staging_target = os.path.join(staging_dir, page_rel)
        os.makedirs(os.path.dirname(staging_target), exist_ok=True)
        os.rename(filepath, staging_target)
        continue

    # --- Frontmatter transform ---
    new_fm, fm_changed, fm_errors = transform_frontmatter(fm_lines, page_rel)
    stats['frontmatter_errors'] += len(fm_errors)

    if fm_changed:
        stats['pages_transformed'] += 1
    else:
        stats['pages_skipped'] += 1

    # --- v0.1 upgrade (body) ---
    is_v01 = page_rel in v01_pages
    v01_sources = []
    body_text = '\n'.join(original.split('\n')[body_start:])

    if is_v01:
        body_text, v01_sources = upgrade_v01_body(body_text)
        if v01_sources:
            stats['v01_upgraded'] += 1
            new_fm.append('sources:')
            for src in v01_sources:
                new_fm.append('  - resource: "' + src + '"')

    # --- Wikilink conversion ---
    body_with_fm = '---\n' + '\n'.join(new_fm) + '\n---\n' + body_text
    converted_text, wl_converted, wl_unmatched, wl_forward = convert_wikilinks(body_with_fm, page_rel)

    stats['wikilinks_converted'] += wl_converted
    stats['wikilinks_unmatched'] += wl_unmatched
    stats['wikilinks_forward_ref'] += wl_forward

    # --- Write back ---
    with open(filepath, 'w') as f:
        f.write(converted_text)

    # Per-file decision log
    decisions = []
    if fm_changed:
        decisions.append('frontmatter-transformed')
    if is_v01 and v01_sources:
        decisions.append('v0.1-upgraded(' + str(len(v01_sources)) + ' citations)')
    if wl_converted > 0 or wl_unmatched > 0 or wl_forward > 0:
        parts = ['wikilinks(' + str(wl_converted) + ' converted']
        if wl_unmatched > 0:
            parts.append(str(wl_unmatched) + ' unmatched')
        if wl_forward > 0:
            parts.append(str(wl_forward) + ' fwd-refs')
        parts.append(')')
        decisions.append(' '.join(parts))

    decision_str = ', '.join(decisions) if decisions else 'no-changes'
    tag = 'TRANS' if fm_changed else 'OK   '
    per_file_decisions.append('  ' + tag + '  ' + page_rel + ' — ' + decision_str)

# --- Print summary ---
print('')
print('  Frontmatter transforms:')
print('    Pages transformed: ' + str(stats['pages_transformed']))
print('    Pages skipped (already OKF): ' + str(stats['pages_skipped']))
print('    Frontmatter errors: ' + str(stats['frontmatter_errors']))
print('    v0.1 pages upgraded: ' + str(stats['v01_upgraded']))
print('')
print('  Wikilink conversion:')
print('    Converted to links: ' + str(stats['wikilinks_converted']))
print('    Unmatched -> plain text: ' + str(stats['wikilinks_unmatched']))
print('    Forward references preserved: ' + str(stats['wikilinks_forward_ref']))
print('')
print('  Per-file decisions:')
for d in per_file_decisions:
    print(d)

# --- Write stats for bash ---
if stats_file:
    with open(stats_file, 'w') as f:
        json.dump(stats, f)
PYEOF

# Read stats back
TRANSFORM_STATS=$(cat "$MIGRATE_STATS_FILE" 2>/dev/null || echo '{}')
rm -f "$MIGRATE_STATS_FILE" "$PAGE_MAP_FILE"

# ============================================================================
# Stage 6: SERVICE FILES
# ============================================================================
info "Stage 6: Service Files"

cd "$OUTPUT_DIR"

# 6a. Move hot.md -> _cache/hot.md
if [[ -f "hot.md" ]]; then
  mkdir -p "_cache"
  mv "hot.md" "_cache/hot.md"
  ok "Moved hot.md -> _cache/hot.md"
fi

# 6b. Move Obsidian artifacts -> _archives/obsidian/
if [[ ${#OBSIDIAN_ARTIFACTS[@]} -gt 0 ]]; then
  mkdir -p "_archives/obsidian"
  for art in ${OBSIDIAN_ARTIFACTS[@]+"${OBSIDIAN_ARTIFACTS[@]}"}; do
    if [[ -f "$art" || -d "$art" ]]; then
      art_dir=$(dirname "$art")
      mkdir -p "_archives/obsidian/$art_dir"
      mv "$art" "_archives/obsidian/$art" 2>/dev/null || true
    fi
  done
  ok "Moved ${#OBSIDIAN_ARTIFACTS[@]} Obsidian artifacts -> _archives/obsidian/"
fi

# 6c. Regenerate per-directory index.md files
info "  Regenerating per-directory index.md files..."

for dir in concepts entities skills references synthesis journal projects; do
  if [[ -d "$dir" ]]; then
    entries=()
    while IFS= read -r -d '' page; do
      rel="${page#./}"
      fname=$(basename "$page")
      [[ "$fname" == "index.md" ]] && continue
      title=$(head -20 "$page" | grep -E "^title:" | head -1 | sed 's/^title:[[:space:]]*//' | tr -d '"' | tr -d "'" | xargs)
      [[ -z "$title" ]] && title="${fname%.md}"
      desc=$(head -20 "$page" | grep -E "^description:" | head -1 | sed 's/^description:[[:space:]]*//' | tr -d '"' | tr -d "'" | xargs)
      if [[ -n "$desc" ]]; then
        entries+=("- [$title](./$fname) — $desc")
      else
        entries+=("- [$title](./$fname)")
      fi
    done < <(find "$dir" -maxdepth 1 -name "*.md" -type f -print0 | sort -z)

    if [[ ${#entries[@]} -gt 0 ]]; then
      {
        printf "# %s\n\n" "${dir^}"
        for entry in ${entries[@]+"${entries[@]}"}; do
          printf "%s\n" "$entry"
        done
      } > "$dir/index.md"
      ok "Regenerated $dir/index.md (${#entries[@]} entries)"
    fi
  fi
done

# Extract transform stats (drives service-file no-op detection + the report)
V01_COUNT=$(echo "$TRANSFORM_STATS" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('v01_upgraded',0))" 2>/dev/null || echo 0)
WL_COUNT=$(echo "$TRANSFORM_STATS" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('wikilinks_converted',0))" 2>/dev/null || echo 0)
WL_UNMATCHED=$(echo "$TRANSFORM_STATS" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('wikilinks_unmatched',0))" 2>/dev/null || echo 0)
WL_FWD=$(echo "$TRANSFORM_STATS" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('wikilinks_forward_ref',0))" 2>/dev/null || echo 0)
PG_TRANS=$(echo "$TRANSFORM_STATS" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('pages_transformed',0))" 2>/dev/null || echo 0)
PG_SKIP=$(echo "$TRANSFORM_STATS" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('pages_skipped',0))" 2>/dev/null || echo 0)
FM_ERR=$(echo "$TRANSFORM_STATS" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('frontmatter_errors',0))" 2>/dev/null || echo 0)

# No-op re-run signal: nothing was transformed, linked, or upgraded this pass.
# Service files keep their existing content so a re-run is zero-diff at bundle level.
NO_TRANSFORM=false
if [[ "$PG_TRANS" == "0" && "$WL_COUNT" == "0" && "$V01_COUNT" == "0" ]]; then
  NO_TRANSFORM=true
fi

# 6d. Update root index.md
if [[ "$NO_TRANSFORM" == true && -f "index.md" ]] && grep -q 'okf_version: "0.2"' "index.md"; then
  info "  Root index.md already migrated — leaving unchanged (no-op re-run)"
else
  info "  Updating root index.md..."
  {
    echo "---"
    echo "okf_version: \"0.2\""
    echo "---"
    echo ""
    echo "# Migrated Bundle"
    echo ""
    echo "Migrated from Obsidian vault on $(date -u +%Y-%m-%dT%H:%M:%SZ)."
    echo ""
    for dir in concepts entities skills references synthesis journal projects; do
      if [[ -d "$dir" ]]; then
        echo "- [${dir^}](./${dir}/index.md)"
      fi
    done
  } > "index.md"
  ok "Updated root index.md"
fi

# 6e. Update/create log.md
if [[ "$NO_TRANSFORM" == true && -f "log.md" ]]; then
  info "  log.md already records this state — leaving unchanged (no-op re-run)"
else
  info "  Updating log.md..."
  LOG_ENTRY="## $(date -u +%Y-%m-%d)
- MIGRATE vault=\"$VAULT\" pages=${#KNOWLEDGE_PAGES[@]} v0.1_upgraded=$V01_COUNT wikilinks_converted=$WL_COUNT"

  if [[ -f "log.md" ]]; then
    tmp_log=$(mktemp)
    head -1 "log.md" > "$tmp_log"
    echo "" >> "$tmp_log"
    echo "$LOG_ENTRY" >> "$tmp_log"
    echo "" >> "$tmp_log"
    tail -n +2 "log.md" >> "$tmp_log"
    mv "$tmp_log" "log.md"
  else
    {
      echo "# Log"
      echo ""
      echo "$LOG_ENTRY"
    } > "log.md"
  fi
  ok "Updated log.md"
fi

# 6f. Write migration report
if [[ "$NO_TRANSFORM" == true && -f "_archives/migration-report.md" ]]; then
  info "  Migration report already reflects this state — leaving unchanged (no-op re-run)"
else
  info "  Writing migration report..."
  mkdir -p "_archives"
  {
    echo "# Migration Report"
    echo ""
    echo "**Source vault:** $VAULT"
    echo "**Migration date:** $(date -u +%Y-%m-%dT%H:%M:%SZ)"
    echo "**Output bundle:** $OUTPUT_DIR"
    echo ""
    echo "## Inventory"
    echo ""
    echo "| Class | Count |"
    echo "|---|---|"
    echo "| Knowledge pages | ${#KNOWLEDGE_PAGES[@]} |"
    echo "| Obsidian artifacts | ${#OBSIDIAN_ARTIFACTS[@]} |"
    echo "| Out-of-scope files | ${#OUT_OF_SCOPE[@]} |"
    echo "| v0.1 legacy pages | ${#V01_PAGES[@]} |"
    echo ""
    echo "## Wikilink Conversion"
    echo ""
    echo "| Metric | Count |"
    echo "|---|---|"
    echo "| Wikilinks before migration | $WIKILINK_COUNT_BEFORE |"
    echo "| Converted to markdown links | $WL_COUNT |"
    echo "| Unmatched -> plain text | $WL_UNMATCHED |"
    echo "| Forward references preserved | $WL_FWD |"
    echo ""
    echo "## Frontmatter Transforms"
    echo ""
    echo "| Metric | Count |"
    echo "|---|---|"
    echo "| Pages transformed | $PG_TRANS |"
    echo "| Pages skipped (already OKF) | $PG_SKIP |"
    echo "| v0.1 pages upgraded | $V01_COUNT |"
    echo "| Frontmatter errors | $FM_ERR |"
    echo ""
    echo "## Obsidian Artifacts Archived"
    echo ""
    for art in ${OBSIDIAN_ARTIFACTS[@]+"${OBSIDIAN_ARTIFACTS[@]}"}; do
      echo "- \`$art\` -> \`_archives/obsidian/$art\`"
    done
  } > "_archives/migration-report.md"
  ok "Wrote _archives/migration-report.md"
fi

cd - > /dev/null

# ============================================================================
# Stage 7: VERIFY
# ============================================================================
info "Stage 7: Verify"

VERIFY_OK=true

# 7a. Run validate.sh
if [[ -x "$VALIDATE_SCRIPT" ]]; then
  info "  Running validate.sh..."
  if bash "$VALIDATE_SCRIPT" "$OUTPUT_DIR"; then
    ok "validate.sh: PASS (exit 0)"
  else
    rc=$?
    if [[ $rc -eq 1 ]]; then
      warn "validate.sh: ERRORS found (exit 1) — see output above"
      VERIFY_OK=false
    else
      warn "validate.sh: exit $rc"
    fi
  fi
else
  warn "validate.sh not found at $VALIDATE_SCRIPT — skipping"
fi

# 7b. Check for remaining wikilinks
REMAINING_WIKILINKS=$(grep -r '\[\[' "$OUTPUT_DIR" --include="*.md" -l | grep -v '_staging/' | grep -v '_archives/' | grep -v '_cache/' || true)
if [[ -n "$REMAINING_WIKILINKS" ]]; then
  warn "Remaining wikilinks found in:"
  echo "$REMAINING_WIKILINKS" | while read -r f; do detail "$f"; done
else
  ok "Zero [[wikilinks]] remaining in knowledge pages"
fi

# 7c. Count markdown links after migration
LINK_COUNT_AFTER=$(grep -r '\[.*\](.*\.md)' "$OUTPUT_DIR" --include="*.md" | grep -v '_staging/' | grep -v '_archives/' | grep -v '_cache/' | wc -l || true)
detail "Markdown links after migration: $LINK_COUNT_AFTER"

# ============================================================================
# DONE
# ============================================================================
echo ""
info "Migration complete"
echo ""
detail "Backup:  $BACKUP_DIR"
detail "Output:  $OUTPUT_DIR"
detail "Report:  $OUTPUT_DIR/_archives/migration-report.md"
echo ""

if $VERIFY_OK; then
  ok "All checks passed"
else
  warn "Some checks failed — review output above"
  exit 1
fi