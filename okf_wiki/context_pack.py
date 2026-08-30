"""Bounded context pack: rank pages for a topic and emit a provenance-rich excerpt set."""

from pathlib import Path
from typing import Any, Dict

from okf_wiki.query import rank_pages

_CHARS_PER_TOKEN = 4


def _provenance_line(fields: Dict[str, Any]) -> str:
    fields = fields or {}
    parts = []
    for key in ("generated.by", "status", "base_confidence", "generated.at"):
        if fields.get(key):
            parts.append(f"{key}={fields[key]}")
    return " | ".join(parts)


def build_pack(bundle: Path, topic: str, budget_tokens: int = 2000) -> Dict[str, Any]:
    """Compile a bounded pack for ``topic``; stop adding pages at the budget."""
    budget_chars = max(400, budget_tokens * _CHARS_PER_TOKEN)
    ranked = rank_pages(Path(bundle), topic)
    header = (
        f"# Context pack: {topic}\n"
        f"Budget: ~{budget_tokens} tokens | Pages: pending (of {len(ranked)} ranked)\n"
    )
    body_parts: list = []
    used = len(header)
    included = 0
    for hit in ranked:
        fm = hit["fm"]
        fields = fm.get("fields") or {}
        section = [
            f"## {hit['path']}",
            f"description: {fm.get('description') or hit['title']}",
        ]
        if hit["excerpt"]:
            section.append(f"excerpt: {hit['excerpt']}")
        prov = _provenance_line(fm.get("fields") or {})
        if prov:
            section.append(f"provenance: {prov}")
        section_text = "\n".join(section)
        if included and used + len(section_text) + 2 > budget_chars:
            break
        body_parts.append(section_text)
        used += len(section_text) + 2
        included += 1

    text = header + "\n\n" + "\n\n".join(body_parts)
    text = text.replace("Pages: pending", f"Pages: {included}", 1)
    pack = {
        "topic": topic,
        "budget_tokens": budget_tokens,
        "tokens_used": max(1, len(text) // _CHARS_PER_TOKEN),
        "pages_included": included,
        "pages_ranked": len(ranked),
        "text": text,
    }
    return pack


def render(pack: Dict[str, Any]) -> str:
    return pack["text"]
