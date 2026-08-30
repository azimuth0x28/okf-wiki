"""Trust-priority conflict resolution (plan decision A5).

Mirrors .skills/wiki-import/SKILL.md Step 2: ranks differ -> higher wins;
tie -> newer generated.at wins; full tie -> existing wins. List-valued
fields are unioned by the caller (importer), never resolved here.
"""

from __future__ import annotations

import datetime as _dt
from typing import Any, Dict, Optional, Tuple

RANK_VERIFIED = 2
RANK_HUMAN = 1
RANK_MACHINE = 0

RULE_RANK = "rank"
RULE_RECENCY = "recency"
RULE_EXISTING = "existing-tie"


def _parse_iso(value: Any) -> Optional[_dt.datetime]:
    """Parse an ISO-8601 timestamp; Z suffix -> +00:00. None if unparseable."""
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return _dt.datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None


def trust_rank(page: Dict[str, Any]) -> int:
    """Rank a page's provenance: verified > human > machine (A5).

    - rank 2: frontmatter carries a non-empty ``verified:`` list
    - rank 1: ``generated.by`` starts with ``human``
    - rank 0: anything else (machine producer)
    """
    verified = page.get("verified")
    if isinstance(verified, list) and verified:
        return RANK_VERIFIED
    if isinstance(verified, dict) and verified:
        return RANK_VERIFIED
    generated = page.get("generated")
    by = generated.get("by") if isinstance(generated, dict) else None
    if isinstance(by, str) and by.strip().lower().startswith("human"):
        return RANK_HUMAN
    return RANK_MACHINE


def _generated_at(page: Dict[str, Any]) -> Optional[_dt.datetime]:
    generated = page.get("generated")
    at = generated.get("at") if isinstance(generated, dict) else None
    return _parse_iso(at)


def resolve_scalar(
    existing: Dict[str, Any],
    incoming: Dict[str, Any],
    field: str,
) -> Tuple[Any, str]:
    """Resolve one scalar field conflict by trust priority.

    Returns ``(winner_value, rule)`` where rule is one of
    ``rank`` | ``recency`` | ``existing-tie``.
    """
    existing_value = existing.get(field)
    incoming_value = incoming.get(field)

    existing_rank = trust_rank(existing)
    incoming_rank = trust_rank(incoming)
    if existing_rank != incoming_rank:
        winner = existing if existing_rank > incoming_rank else incoming
        return winner.get(field), RULE_RANK

    existing_at = _generated_at(existing)
    incoming_at = _generated_at(incoming)
    if existing_at is not None and incoming_at is not None and existing_at != incoming_at:
        winner = existing if existing_at > incoming_at else incoming
        return winner.get(field), RULE_RECENCY

    return existing_value, RULE_EXISTING
