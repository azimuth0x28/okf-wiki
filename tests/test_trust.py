"""Tests for okf_wiki.trust — trust ranks and scalar conflict resolution (A5)."""

from okf_wiki.trust import RANK_HUMAN, RANK_MACHINE, RANK_VERIFIED, resolve_scalar, trust_rank


def _page(by="claude/2.5.0", at="2026-01-01T00:00:00Z", verified=None):
    page = {"type": "Concept", "generated": {"by": by, "at": at}}
    if verified is not None:
        page["verified"] = verified
    return page


class TestTrustRank:
    def test_machine_rank_zero(self):
        assert trust_rank(_page()) == RANK_MACHINE

    def test_human_rank_one(self):
        assert trust_rank(_page(by="human:evgeniy")) == RANK_HUMAN

    def test_verified_rank_two(self):
        page = _page(by="ghost-writer/0.3", verified=[{"by": "human:evgeniy"}])
        assert trust_rank(page) == RANK_VERIFIED

    def test_verified_empty_list_is_not_verified(self):
        page = _page(verified=[])
        assert trust_rank(page) == RANK_MACHINE

    def test_missing_generated_is_machine(self):
        assert trust_rank({"type": "Concept"}) == RANK_MACHINE


class TestResolveScalar:
    def test_rank_beats_recency(self):
        existing = _page(at="2026-09-01T00:00:00Z")
        existing["description"] = "machine newer"
        incoming = _page(
            by="ghost-writer/0.3",
            at="2026-01-01T00:00:00Z",
            verified=[{"by": "human:evgeniy"}],
        )
        incoming["description"] = "verified older"
        value, rule = resolve_scalar(existing, incoming, "description")
        # existing is machine rank 0, incoming is verified rank 2 → incoming wins
        assert value == "verified older"
        assert rule == "rank"

    def test_rank_differ_higher_wins(self):
        existing = _page(by="human:evgeniy", at="2026-01-01T00:00:00Z")
        existing["description"] = "human text"
        incoming = _page(by="claude/2.5.0", at="2026-09-01T00:00:00Z")
        incoming["description"] = "machine text"
        value, rule = resolve_scalar(existing, incoming, "description")
        assert value == "human text"
        assert rule == "rank"

    def test_rank_tie_newer_wins(self):
        existing = _page(at="2026-01-01T00:00:00Z")
        existing["description"] = "old"
        incoming = _page(at="2026-02-01T00:00:00Z")
        incoming["description"] = "new"
        value, rule = resolve_scalar(existing, incoming, "description")
        assert value == "new"
        assert rule == "recency"

    def test_rank_tie_older_incoming_loses(self):
        existing = _page(at="2026-02-01T00:00:00Z")
        existing["description"] = "current"
        incoming = _page(at="2026-01-01T00:00:00Z")
        incoming["description"] = "stale"
        value, rule = resolve_scalar(existing, incoming, "description")
        assert value == "current"
        assert rule == "recency"

    def test_full_tie_existing_wins(self):
        existing = _page(at="2026-01-01T00:00:00Z")
        existing["description"] = "keep"
        incoming = _page(at="2026-01-01T00:00:00Z")
        incoming["description"] = "drop"
        value, rule = resolve_scalar(existing, incoming, "description")
        assert value == "keep"
        assert rule == "existing-tie"

    def test_unparseable_timestamp_falls_back_to_existing(self):
        existing = _page(at="2026-01-01T00:00:00Z")
        existing["description"] = "keep"
        incoming = _page(at="not-a-date")
        incoming["description"] = "drop"
        value, _rule = resolve_scalar(existing, incoming, "description")
        assert value == "keep"
