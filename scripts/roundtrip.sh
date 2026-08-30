#!/usr/bin/env bash
# roundtrip.sh — OKF frontmatter round-trip autotest (T-3.6).
#
# For every page of a bundle: extract frontmatter → parse → re-emit → re-parse
# → assert (a) semantic identity with the original data and (b) canonical-form
# stability (emit(parse(emit(parse(x)))) == emit(parse(x))).
#
# Canonicalization: YAML keys are sorted (sort_keys=True), so two frontmatters
# that differ only in key order compare equal. Scalar values keep their types
# (quoted timestamps stay strings, unquoted become datetimes) — the comparison
# is between parse results, so formatting differences that preserve semantics
# pass.
#
# Usage:  roundtrip.sh [bundle-dir]        (default: tests/fixtures/mini-bundle)
# Exit:   0 all pages round-trip, 1 identity violated, 2 usage error.

set -euo pipefail

if [ $# -gt 1 ]; then
  echo "usage: $0 [bundle-dir]" >&2
  exit 2
fi

BUNDLE="${1:-tests/fixtures/mini-bundle}"
if [ ! -d "$BUNDLE" ]; then
  echo "roundtrip: bundle directory not found: $BUNDLE" >&2
  exit 2
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Re-export every page path so the embedded Python stays arg-list clean.
PAGE_LIST="$(find "$BUNDLE" -type f -name '*.md' \
  -not -path '*/_*' -not -path '*/.*' | sort)"

export ROUNDTRIP_BUNDLE="$BUNDLE"
export ROUNDTRIP_PAGES="$PAGE_LIST"

python3 - <<'PY'
import os
import sys

try:
    import yaml
except ImportError:
    print("roundtrip: PyYAML is required (pip install pyyaml)", file=sys.stderr)
    sys.exit(2)

pages = [p for p in os.environ.get("ROUNDTRIP_PAGES", "").splitlines() if p]
checked = skipped = failed = 0


def split_frontmatter(text):
    """Return (fm_text, had_fm). Only a leading '---' block counts."""
    if not text.startswith("---"):
        return None
    parts = text.split("---", 2)
    if len(parts) < 3:
        return None
    return parts[1]


for path in pages:
    with open(path, encoding="utf-8") as f:
        text = f.read()
    fm_text = split_frontmatter(text)
    if fm_text is None:
        skipped += 1
        continue
    try:
        data = yaml.safe_load(fm_text)
        canonical = yaml.safe_dump(data, sort_keys=True, allow_unicode=True)
        roundtripped = yaml.safe_load(canonical)
        canonical2 = yaml.safe_dump(roundtripped, sort_keys=True, allow_unicode=True)
    except yaml.YAMLError as e:
        print(f"FAIL {path}: YAML error: {e}")
        failed += 1
        continue

    problems = []
    if roundtripped != data:
        problems.append("semantic mismatch after re-emit")
    if canonical != canonical2:
        problems.append("canonical form unstable across re-emit")
    if problems:
        print(f"FAIL {path}: {'; '.join(problems)}")
        failed += 1
    else:
        checked += 1

print(f"roundtrip: {checked} pages round-tripped, {skipped} skipped (no frontmatter), {failed} failed")
sys.exit(1 if failed else 0)
PY

status=$?
if [ "$status" -ne 0 ]; then
  echo "roundtrip: frontmatter identity violated" >&2
fi
exit "$status"
