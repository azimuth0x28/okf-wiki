"""Tests for okf_wiki.context_pack — budget compliance and provenance."""

from pathlib import Path

from okf_wiki.context_pack import build_pack

REPO = Path(__file__).resolve().parents[1]
MINI = REPO / "tests" / "fixtures" / "mini-bundle"


class TestBuildPack:
    def test_pack_respects_budget(self, tmp_path):
        bundle = tmp_path / "bundle"
        bundle.mkdir()
        concepts = bundle / "concepts"
        concepts.mkdir()
        for i in range(6):
            (concepts / f"p{i}.md").write_text(
                f"---\ntitle: Cache Topic {i}\ndescription: cache discussion number {i}\n"
                "---\n\n" + ("cache detail line. " * 30),
                encoding="utf-8",
            )
        pack = build_pack(bundle, "cache topic", budget_tokens=200)
        assert pack["pages_included"] < 6
        assert pack["tokens_used"] <= 200 + 20  # header allowance

    def test_pack_contains_provenance(self, tmp_path):
        bundle = tmp_path / "bundle"
        bundle.mkdir()
        concepts = bundle / "concepts"
        concepts.mkdir()
        (concepts / "only.md").write_text(
            "---\n"
            "title: Cache Guide\n"
            "description: cache in depth\n"
            "type: Concept\n"
            "status: stable\n"
            "base_confidence: 0.9\n"
            "generated:\n"
            "  by: claude/2.5.0\n"
            "  at: 2026-08-01T00:00:00Z\n"
            "---\n\nCache body text here.\n",
            encoding="utf-8",
        )
        pack = build_pack(bundle, "cache", budget_tokens=500)
        assert pack["pages_included"] == 1
        assert "status=stable" in pack["text"]
        assert "base_confidence=0.9" in pack["text"]
        assert "generated.by=claude/2.5.0" in pack["text"]

    def test_no_hits_graceful(self, tmp_path):
        bundle = tmp_path / "bundle"
        bundle.mkdir()
        pack = build_pack(bundle, "nothing matches zzz", budget_tokens=100)
        assert pack["pages_included"] == 0
        assert "of 0 ranked" in pack["text"]
