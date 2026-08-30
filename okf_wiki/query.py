"""Deterministic bundle retrieval following the wiki-query read protocol.

Score pages by question-token hits over frontmatter (title x3, tags x2,
description x1), then excerpt matching bodies of the top hits. The index pass
and scoring are pure functions of bundle content, so identical questions yield
identical answers.
"""

import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from okf_wiki.lint import _in_scope

_TOKEN_RE = re.compile(r"[a-zа-яё0-9]{3,}")
_STOPWORDS = frozenset(
    {
        "the", "and", "for", "with", "what", "how", "does", "are", "was",
        "when", "that", "this", "from", "into", "why", "which", "has",
        "как", "что", "или", "для", "это", "при", "чем", "его", "она",
    }
)
_WEIGHTS = (("title", 3), ("tags", 2), ("description", 1))


def _read_page(path: Path) -> Dict[str, Any]:
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    page: Dict[str, Any] = {
        "title": "",
        "description": "",
        "tags": [],
        "body": [],
        "fields": {},
    }
    if not lines or lines[0].strip() != "---":
        page["body"] = lines
        return page
    fm_lines: List[str] = []
    close = -1
    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            close = i
            break
        fm_lines.append(line)
    page["body"] = lines[close + 1 :] if close != -1 else lines

    current_list: Optional[List[str]] = None
    current_key: Optional[str] = None
    for line in fm_lines:
        if line[:1] in (" ", "\t"):
            item = line.strip().lstrip("-").strip()
            if current_list is not None and item:
                current_list.append(item)
            elif current_key == "generated" and item:
                sub = re.match(r"^(by|at):\s*(.*)$", item)
                if sub:
                    page["fields"][f"generated.{sub.group(1)}"] = sub.group(2).strip().strip('"').strip("'")
            continue
        current_list = None
        stripped = line.strip()
        top = re.match(r"^([A-Za-z_][\w.-]*):\s*(.*)$", stripped)
        if not top:
            continue
        key, value = top.group(1), top.group(2).strip()
        if value == "":
            if key == "tags":
                current_list = page["tags"]
                current_key = key
            else:
                current_key = key
            continue
        current_key = key
        page["fields"][key] = value.strip('"').strip("'")
        if key in ("title", "description"):
            page[key] = page["fields"][key]
        if key == "tags" and value.startswith("["):
            inner = value[1 : value.rindex("]")]
            page["tags"] = [t.strip().strip("'\"") for t in inner.split(",") if t.strip()]
    return page


def tokenize(question: str) -> List[str]:
    seen: set = set()
    tokens: List[str] = []
    for token in _TOKEN_RE.findall(question.lower()):
        if token in _STOPWORDS or token in seen:
            continue
        seen.add(token)
        tokens.append(token)
    return tokens


def _excerpt(body: List[str], tokens: List[str], width: int = 400) -> str:
    for i, line in enumerate(body):
        low = line.lower()
        if any(token in low for token in tokens):
            window = body[max(0, i - 1) : i + 3]
            text = " ".join(part.strip() for part in window if part.strip())
            return text[:width]
    text = " ".join(part.strip() for part in body[:3] if part.strip())
    return text[:width]


def rank_pages(bundle: Path, question: str) -> List[Dict[str, Any]]:
    """Score every in-scope page; deterministic order (-score, path)."""
    tokens = tokenize(question)
    hits: List[Dict[str, Any]] = []
    for path in _in_scope(Path(bundle)):
        page = _read_page(path)
        if path.name in ("index.md", "log.md"):
            continue
        title_low = str(page["title"]).lower()
        desc_low = str(page["description"]).lower()
        tag_low = " ".join(page["tags"]).lower()
        score = 0
        matched: Dict[str, List[str]] = {"title": [], "tags": [], "description": []}
        for token in tokens:
            if token in title_low:
                score += 3
                matched["title"].append(token)
            if token in tag_low:
                score += 2
                matched["tags"].append(token)
            if token in desc_low:
                score += 1
                matched["description"].append(token)
        if score == 0:
            continue
        rel = path.relative_to(bundle).as_posix()
        hits.append(
            {
                "path": rel,
                "title": page["title"] or path.stem,
                "score": score,
                "matched": matched,
                "excerpt": _excerpt(page["body"], tokens),
                "fm": page,
            }
        )
    hits.sort(key=lambda hit: (-hit["score"], hit["path"]))
    return hits


def query(bundle: Path, question: str, top: int = 3) -> Dict[str, Any]:
    """Rank pages and excerpt the top hits."""
    ranked = rank_pages(bundle, question)
    selected = []
    for hit in ranked[: max(1, top)]:
        selected.append({key: hit[key] for key in ("path", "title", "score", "matched", "excerpt")})
    return {"question": question, "total_ranked": len(ranked), "hits": selected}


def render(result: Dict[str, Any]) -> str:
    lines = [f"Query: {result['question']}", f"Ranked pages: {result['total_ranked']}"]
    if not result["hits"]:
        lines.append("No matching pages.")
        return "\n".join(lines)
    lines.append("Top pages:")
    for i, hit in enumerate(result["hits"], start=1):
        lines.append(
            f"  {i}. {hit['path']} — {hit['title']} (score {hit['score']})"
        )
    lines.append("")
    for i, hit in enumerate(result["hits"], start=1):
        lines.append(f"[{i}] [{hit['title']}](./{hit['path']})")
        if hit["excerpt"]:
            lines.append(f"    {hit['excerpt']}")
    return "\n".join(lines)
