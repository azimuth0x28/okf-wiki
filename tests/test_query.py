"""Tests for okf_wiki.query — deterministic scoring and citation order."""

from pathlib import Path

from okf_wiki.query import query, rank_pages, render, tokenize

REPO = Path(__file__).resolve().parents[1]


class TestTokenize:
    def test_tokens_are_lowercase_and_deduped(self):
        assert tokenize("Canary Canary traffic") == ["canary", "traffic"]

    def test_stopwords_and_short_tokens_dropped(self):
        assert tokenize("what is the canary") == ["canary"]


class TestRanking:
    def _make_bundle(self, tmp_path):
        bundle = tmp_path / "bundle"
        bundle.mkdir()
        (bundle / "index.md").write_text("---\nokf_version: \"0.2\"\n---\n\n# B\n", encoding="utf-8")
        return bundle

    def test_title_hit_beats_description_hit(self, tmp_path):
        bundle = self._make_bundle(tmp_path)
        (bundle / "concepts").mkdir()
        (bundle / "concepts" / "alpha.md").write_text(
            "---\ntitle: Canary Deploy\ndescription: unrelated words\ntags: [deploy]\n---\nBody canary\n",
            encoding="utf-8",
        )
        (bundle / "concepts" / "beta.md").write_text(
            "---\ntitle: Unrelated\ndescription: canary traffic mentioned here\n---\nBody\n",
            encoding="utf-8",
        )
        hits = rank_pages(bundle, "canary traffic")
        assert hits[0]["path"] == "concepts/alpha.md"
        assert hits[0]["score"] > hits[1]["score"]

    def test_top_limit_respected(self, tmp_path):
        bundle = self._make_bundle(tmp_path)
        concepts = bundle / "concepts"
        concepts.mkdir()
        for name in ("a", "b", "c"):
            (concepts / f"{name}.md").write_text(
                f"---\ntitle: {name} canary\ndescription: canary page\ntags: [canary]\n---\nBody canary\n",
                encoding="utf-8",
            )
        result = query(bundle, "canary", top=2)
        assert len(result["hits"]) == 2
        assert result["total_ranked"] == 3

    def test_order_deterministic(self, tmp_path):
        bundle = self._make_bundle(tmp_path)
        (bundle / "concepts").mkdir()
        (bundle / "concepts" / "x.md").write_text(
            "---\ntitle: Canary A\ndescription: rollout\ntags: [canary]\n---\nBody\n",
            encoding="utf-8",
        )
        (bundle / "concepts" / "y.md").write_text(
            "---\ntitle: Canary B\ndescription: canary again\n---\nBody\n",
            encoding="utf-8",
        )
        first = [h["path"] for h in rank_pages(bundle, "canary")]
        second = [h["path"] for h in rank_pages(bundle, "canary")]
        assert first == second and len(first) == 2

    def test_citation_and_excerpt_present(self, tmp_path):
        bundle = self._make_bundle(tmp_path)
        (bundle / "concepts").mkdir()
        (bundle / "concepts" / "c.md").write_text(
            "---\ntitle: Canary Guide\ndescription: rollout\n---\n\nCanary shifts traffic gradually.\n",
            encoding="utf-8",
        )
        result = query(bundle, "canary traffic", top=1)
        hit = result["hits"][0]
        assert hit["path"] == "concepts/c.md"
        assert "traffic" in hit["excerpt"]
        text = render(result)
        assert "[Canary Guide](./concepts/c.md)" in text

    def test_no_hits_empty(self, tmp_path):
        bundle = self._make_bundle(tmp_path)
        (bundle / "concepts").mkdir()
        (bundle / "concepts" / "x.md").write_text(
            "---\ntitle: T\ndescription: D\n---\nBody\n", encoding="utf-8"
        )
        assert rank_pages(bundle, "zzzqqq") == []
