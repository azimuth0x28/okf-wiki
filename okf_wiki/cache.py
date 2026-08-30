"""Ingest cache operations over .manifest.json (schema from scripts/manifest.py).

Manifest shape: ``{"version": 1, "sources": {}, "projects": {}, "stats": {}}``.
Entries carry ``ingested_at``, ``pages_created[]``, ``pages_updated[]``.
Merge: newest ingested_at wins, page lists union. Delta: NEW if key unknown,
MODIFIED if source mtime > ingested_at.
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

MANIFEST_NAME = ".manifest.json"


def canonical_key(path: str) -> str:
    return os.path.abspath(os.path.expanduser(os.path.expandvars(path)))


def load_manifest(bundle: Path) -> Dict[str, Any]:
    path = bundle / MANIFEST_NAME
    if not path.is_file():
        return {"version": 1, "sources": {}, "projects": {}, "stats": {}}
    data = json.loads(path.read_text(encoding="utf-8"))
    for key in ("version", "sources", "projects", "stats"):
        data.setdefault(key, {} if key != "version" else 1)
    return data


def save_manifest(bundle: Path, manifest: Dict[str, Any]) -> None:
    path = bundle / MANIFEST_NAME
    path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def _parse_ingested(value: Any) -> float:
    if not isinstance(value, str) or not value.strip():
        return 0.0
    try:
        return _dt.datetime.fromisoformat(
            value.strip().replace("Z", "+00:00")
        ).timestamp()
    except ValueError:
        return 0.0


def _merge_entry(old: Dict[str, Any], new: Dict[str, Any]) -> Dict[str, Any]:
    """Newest ingested_at wins; page lists union with dedup."""
    old_ts = _parse_ingested(old.get("ingested_at"))
    new_ts = _parse_ingested(new.get("ingested_at"))
    base, other = (old, new) if old_ts >= new_ts else (new, old)
    merged = dict(base)
    for list_key in ("pages_created", "pages_updated"):
        union = list(base.get(list_key) or [])
        for item in other.get(list_key) or []:
            if item not in union:
                union.append(item)
        merged[list_key] = union
    merged["ingested_at"] = max(old.get("ingested_at") or "", new.get("ingested_at") or "")
    return merged


def upsert_entry(manifest: Dict[str, Any], section: str, key: str, entry: Dict[str, Any]) -> None:
    store = manifest.setdefault(section, {})
    if key in store:
        store[key] = _merge_entry(store[key], entry)
    else:
        store[key] = entry


def _recount_stats(manifest: Dict[str, Any]) -> Dict[str, int]:
    stats = {
        "sources": len(manifest.get("sources", {})),
        "projects": len(manifest.get("projects", {})),
        "pages_created": 0,
        "pages_updated": 0,
    }
    for section in ("sources", "projects"):
        for entry in manifest.get(section, {}).values():
            stats["pages_created"] += len(entry.get("pages_created") or [])
            stats["pages_updated"] += len(entry.get("pages_updated") or [])
    manifest["stats"] = stats
    return stats


def cache_check(bundle: Path) -> Dict[str, Any]:
    """Validate structure; recount stats; report anomalies."""
    manifest = load_manifest(bundle)
    problems: List[str] = []
    for section in ("sources", "projects"):
        for key, entry in manifest.get(section, {}).items():
            if "ingested_at" not in entry:
                problems.append("{}[{}]: missing ingested_at".format(section, key))
    stats = _recount_stats(manifest)
    return {"manifest": manifest, "stats": stats, "problems": problems}


def scan_sources(bundle: Path, skip: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """Discover source documents for a bundle (project dirs / loose files).

    Sources live next to the bundle or inside it under sources/ — we scan the
    bundle's ``sources/`` directory if present, else the bundle root's sibling
    ``sources/``. Skips substrings from WIKI_SKIP_PROJECTS env + explicit list.
    """
    markers: List[str] = list(skip or [])
    env_skip = os.environ.get("WIKI_SKIP_PROJECTS", "")
    markers += [s for s in env_skip.split(",") if s]

    roots = [bundle / "sources", bundle.parent / "sources"]
    found: List[Dict[str, Any]] = []
    seen: set = set()
    for root in roots:
        if not root.is_dir():
            continue
        for p in sorted(root.rglob("*")):
            if p.suffix.lower() not in (".md", ".txt", ".html", ".pdf", ".json"):
                continue
            if any(part.startswith("_") or part.startswith(".") for part in p.relative_to(root).parts):
                continue
            full = str(p)
            if full in seen:
                continue
            seen.add(full)
            if any(marker and marker in full for marker in markers):
                continue
            found.append(
                {
                    "key": canonical_key(full),
                    "path": p,
                    "mtime": p.stat().st_mtime,
                    "size": p.stat().st_size,
                }
            )
    return found


def cache_update(
    bundle: Path,
    section: str = "sources",
    skip: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Diff scan results against the manifest: NEW / MODIFIED / unchanged."""
    manifest = load_manifest(bundle)
    store = manifest.setdefault(section, {})
    new_items: List[str] = []
    modified_items: List[str] = []
    unchanged = 0

    for item in scan_sources(bundle, skip=skip):
        entry = store.get(item["key"])
        if entry is None:
            new_items.append(item["key"])
        elif item["mtime"] > _parse_ingested(entry.get("ingested_at")):
            modified_items.append(item["key"])
        else:
            unchanged += 1

    return {
        "new": new_items,
        "modified": modified_items,
        "unchanged": unchanged,
        "manifest": manifest,
    }


def cache_hash(bundle: Path) -> str:
    """Deterministic sha256 over the canonicalized manifest dump."""
    manifest = load_manifest(bundle)
    dump = json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=True)
    return hashlib.sha256(dump.encode("utf-8")).hexdigest()
