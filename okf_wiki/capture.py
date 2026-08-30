"""Quick capture: write a wiki-capture --quick shaped note into _raw/ (A3)."""

import datetime as _dt
import re
from pathlib import Path
from typing import Any, List, Optional

_SPECIAL_CHARS = ":#{}[]&*!|>'\"%@`,"


def _slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:50] or "capture"


def _fmt(value: Any) -> str:
    """Minimal YAML scalar rendering: bare when safe, quoted when not."""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    text = str(value)
    if text == "":
        return '""'
    if re.match(r"^-?\d+(\.\d+)?$", text):
        return text
    if any(ch in _SPECIAL_CHARS for ch in text) or text != text.strip():
        escaped = text.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    return text


def _version_or_default() -> str:
    try:
        from okf_wiki import __version__
    except Exception:  # pragma: no cover - packaging edge
        return "0.0.0.dev0"
    return str(__version__)


def _tags_lines(tags: List[str]) -> List[str]:
    if not tags:
        return ["tags: []"]
    lines = ["tags:"]
    lines.extend(f"  - {tag}" for tag in tags)
    return lines


def capture(
    bundle: Path,
    title: str,
    tags: Optional[List[str]] = None,
    project: Optional[str] = None,
    note: Optional[str] = None,
    confidence: float = 0.75,
    page_type: str = "Concept",
    source: Optional[str] = None,
) -> Path:
    """Write one quick-capture file under ``<bundle>/_raw/`` and return its path.

    Frontmatter satisfies the OKF v0.2 minimum (``type``, ``generated``,
    ``sources`` with ``resource``) plus the wiki-capture quick-mode extension
    fields (``base_confidence``, ``provenance``, ``lifecycle_changed``,
    ``tier``, ``project``). ``_raw/`` is out of OKF scope, so wiki-lint skips
    the file until promotion.
    """
    bundle = Path(bundle)
    today = _dt.date.today().isoformat()
    now = _dt.datetime.now(_dt.timezone.utc)
    raw_dir = bundle / "_raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    base = _slugify(title)
    path = raw_dir / f"{today}-{base}.md"
    counter = 2
    while path.exists():
        path = raw_dir / f"{today}-{base}-{counter}.md"
        counter += 1

    description = (note or title).strip()
    if len(description) > 200:
        description = description[:197] + "..."

    resource = source or f"{project or 'session'} session ({today})"

    lines: List[str] = [
        "---",
        f"title: {_fmt(title)}",
        f"type: {_fmt(page_type)}",
        *_tags_lines(tags or []),
        f"description: {_fmt(description)}",
        "generated:",
        f"  by: okf-wiki/{_version_or_default()}",
        f"  at: {now.strftime('%Y-%m-%dT%H:%M:%SZ')}",
        "status: draft",
        "tier: supporting",
        f"project: {_fmt(project)}",
        f"base_confidence: {confidence}",
        "provenance:",
        f"  extracted: {round(confidence, 2)}",
        f"  inferred: {round(1.0 - confidence, 2)}",
        f"lifecycle_changed: {today}",
        "sources:",
        f"  - resource: {_fmt(resource)}",
        "---",
        "",
        f"# {title}",
        "",
    ]
    if note:
        lines.append(note.strip())
        lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")
    return path
