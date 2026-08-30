"""OKF bundle lint — exact semantic port of scripts/validate.sh.

Exit codes match validate.sh: 0 = no E-errors, 1 = at least one E-error,
2 = usage error (no argument / path is not a directory).
"""

from __future__ import annotations

import datetime as _dt
import re
from pathlib import Path
from typing import Dict, List, Optional

_KNOWN_STATUS = ("draft", "stable", "deprecated")
_LOG_DATE = re.compile(r"^## \d{4}-\d{2}-\d{2}\s*$")


class LintResult:
    def __init__(self) -> None:
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.files_checked = 0

    @property
    def ok(self) -> bool:
        return not self.errors

    def summary(self) -> str:
        lines = [
            "OKF validation: {} file(s) checked".format(self.files_checked),
            "Errors (E): {}".format(len(self.errors)),
            "Warnings (W): {}".format(len(self.warnings)),
        ]
        for e in self.errors:
            lines.append("E: " + e)
        for w in self.warnings:
            lines.append("W: " + w)
        return "\n".join(lines)


def _in_scope(bundle: Path) -> List[Path]:
    """In-scope .md files: exclude dot-paths and _-prefixed dirs/files."""
    out: List[Path] = []
    for p in sorted(bundle.rglob("*.md")):
        rel = p.relative_to(bundle)
        parts = rel.parts
        if any(part.startswith(".") for part in parts):
            continue
        if any(part.startswith("_") for part in parts[:-1]):
            continue
        if parts[-1].startswith("_") or parts[-1].startswith("."):
            continue
        out.append(p)
    return out


def _has_frontmatter(text: str) -> bool:
    lines = text.splitlines()
    return bool(lines) and lines[0].strip() == "---"


def _frontmatter_lines(text: str) -> List[str]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return []
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return lines[1:i]
    return []


def _field(fm_lines: List[str], key: str) -> Optional[str]:
    """Top-level scalar field value (nested keys ignored), None if absent."""
    for line in fm_lines:
        if line and line[0] in (" ", "\t"):
            continue
        stripped = line.strip()
        if stripped.startswith(key + ":"):
            value = stripped[len(key) + 1:].strip()
            return value.strip("'\"")
    return None


def _sources_block_entries(fm_lines: List[str]) -> int:
    """Count `- ` entries inside a top-level ``sources:`` block."""
    count = 0
    in_sources = False
    for line in fm_lines:
        if line and line[0] not in (" ", "\t"):
            in_sources = line.strip().startswith("sources:")
            continue
        if in_sources and line.strip().startswith("- "):
            count += 1
    return count


def _sources_block_has_resource(fm_lines: List[str]) -> bool:
    in_sources = False
    for line in fm_lines:
        if line and line[0] not in (" ", "\t"):
            in_sources = line.strip().startswith("sources:")
            continue
        if in_sources and "resource:" in line:
            return True
    return False


def _now_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def lint_bundle(bundle: Path) -> LintResult:
    result = LintResult()
    if not bundle.is_dir():
        raise NotADirectoryError(str(bundle))

    now = _now_iso()
    for path in _in_scope(bundle):
        result.files_checked += 1
        rel = path.relative_to(bundle).as_posix()
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            result.errors.append("{}: unreadable file ({})".format(rel, exc))
            continue

        name = path.name
        fm = _frontmatter_lines(text) if _has_frontmatter(text) else []

        if name == "index.md":
            # Root index may carry frontmatter (okf_version); nested ones may not.
            if rel != "index.md" and fm:
                result.errors.append(
                    "{} (E3): nested index.md must not have frontmatter".format(rel)
                )
            continue

        if name == "log.md":
            if text.strip() and not any(_LOG_DATE.match(l) for l in text.splitlines()):
                result.warnings.append(
                    "{} (W5): log.md has no '## YYYY-MM-DD' date heading".format(rel)
                )
            continue

        # Knowledge page checks -------------------------------------------------
        if not fm:
            result.errors.append(
                "{} (E1): missing frontmatter block".format(rel)
            )
            continue

        ftype = _field(fm, "type")
        if not ftype:
            result.errors.append("{} (E2): missing or empty 'type:'".format(rel))
        elif ftype == "Attested Computation" and _field(fm, "runtime") is None:
            result.errors.append(
                "{} (E4): Attested Computation requires 'runtime:'".format(rel)
            )

        if _field(fm, "title") is None or _field(fm, "description") is None:
            result.warnings.append(
                "{} (W1): missing 'title:' or 'description:'".format(rel)
            )

        if _field(fm, "timestamp") is not None and _field(fm, "generated") is None:
            result.warnings.append(
                "{} (W3): legacy 'timestamp:' without 'generated:'".format(rel)
            )

        if _sources_block_entries(fm) > 0 and not _sources_block_has_resource(fm):
            result.warnings.append(
                "{} (W6): sources entries without 'resource:'".format(rel)
            )

        status = _field(fm, "status")
        if status is not None and status not in _KNOWN_STATUS:
            result.warnings.append(
                "{} (W): unknown status '{}'".format(rel, status)
            )

        stale = _field(fm, "stale_after")
        if stale is not None and stale <= now:
            result.warnings.append(
                "{} (W7): stale (stale_after {} <= now {})".format(rel, stale, now)
            )

    return result
