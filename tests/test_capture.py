"""Tests for okf_wiki.capture — _raw/ quick notes (A3)."""

import datetime as dt
import re

from okf_wiki.capture import capture
from okf_wiki.lint import lint_bundle


def _make_bundle(tmp_path):
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    (bundle / "index.md").write_text("---\nokf_version: \"0.2\"\n---\n\n# B\n", encoding="utf-8")
    return bundle


def _frontmatter(text):
    match = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    assert match, "file must start with frontmatter"
    return match.group(1)


class TestCapture:
    def test_writes_okf_minimum_frontmatter(self, tmp_path):
        bundle = _make_bundle(tmp_path)
        path = capture(bundle, title="Actor reentrancy gotcha", tags=["swift", "actor"], note="Fix applied after debugging.")
        text = path.read_text(encoding="utf-8")
        fm = _frontmatter(text)
        assert "type: Concept" in fm
        assert "by: okf-wiki/" in fm
        assert "at: " in fm
        assert "resource: " in fm
        assert path.parent.name == "_raw"
        assert path.name.startswith(f"{dt.date.today().isoformat()}-")

    def test_tags_and_project_recorded(self, tmp_path):
        bundle = _make_bundle(tmp_path)
        path = capture(bundle, title="Some finding", tags=["a", "b"], project="demo")
        fm = _frontmatter(path.read_text(encoding="utf-8"))
        assert "  - a" in fm
        assert "  - b" in fm
        assert "project: demo" in fm
        assert "base_confidence: 0.75" in fm
        assert "extracted: 0.75" in fm
        assert "inferred: 0.25" in fm

    def test_duplicate_title_gets_suffix(self, tmp_path):
        bundle = _make_bundle(tmp_path)
        first = capture(bundle, title="Same title")
        second = capture(bundle, title="Same title")
        assert first != second
        assert second.stem.endswith("-2")

    def test_raw_dir_is_lint_invisible(self, tmp_path):
        bundle = _make_bundle(tmp_path)
        capture(bundle, title="Not linted")
        result = lint_bundle(bundle)
        assert result.ok is True
        assert all("_raw/" not in str(err) for err in result.errors)
        assert not any("_raw/" in msg for msg in result.warnings + result.errors)
