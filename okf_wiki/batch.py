"""Batch ingest planning from the manifest delta (mirror of scripts/manifest.py CLI plan)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from .cache import cache_update


def batch_plan(
    bundle: Path,
    section: str = "sources",
    skip: "list[str] | None" = None,
) -> Dict[str, Any]:
    """Produce an ordered ingest plan: NEW sources first, then MODIFIED."""
    skip = skip if skip is not None else []
    delta = cache_update(bundle, section=section, skip=skip)
    plan: List[Dict[str, str]] = []
    for key in delta["new"]:
        plan.append({"action": "create", "source": key})
    for key in delta["modified"]:
        plan.append({"action": "update", "source": key})

    lines = ["Batch plan: {} create(s), {} update(s)".format(len(delta["new"]), len(delta["modified"]))]
    for i, item in enumerate(plan, 1):
        lines.append("  {}. [{}] {}".format(i, item["action"], item["source"]))
    if not plan:
        lines.append("  (nothing to do — manifest is in sync with sources)")

    return {
        "plan": plan,
        "text": "\n".join(lines),
        "new": delta["new"],
        "modified": delta["modified"],
        "unchanged": delta["unchanged"],
        "manifest": delta["manifest"],
    }
