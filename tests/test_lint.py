"""Tests for okf_wiki.lint — parity with scripts/validate.sh plus unit rules."""

import subprocess
from pathlib import Path

from okf_wiki import cli
from okf_wiki.lint import lint_bundle

REPO = Path(__file__).resolve().parents[1]
MINI = REPO / "tests" / "fixtures" / "mini-bundle"
BAD = REPO / "tests" / "fixtures" / "non-conformant"


def _cli_exit(*args):
    return cli.main(["lint", *args])


class TestValidateParity:
    """okf-wiki lint must agree with scripts/validate.sh exit codes."""

    def test_mini_bundle_both_exit_zero(self):
        bash_exit = subprocess.run(
            ["bash", str(REPO / "scripts" / "validate.sh"), str(MINI)],
            capture_output=True,
        ).returncode
        ours = _cli_exit(str(MINI))
        assert bash_exit == 0
        assert ours == 0

    def test_non_conformant_both_exit_one(self):
        bash_exit = subprocess.run(
            ["bash", str(REPO / "scripts" / "validate.sh"), str(BAD)],
            capture_output=True,
        ).returncode
        ours = _cli_exit(str(BAD))
        assert bash_exit == 1
        assert ours == 1

    def test_no_bundle_matches_usage_exit_two(self, monkeypatch, tmp_path):
        home = tmp_path / "home"
        home.mkdir()
        monkeypatch.setenv("HOME", str(home))
        monkeypatch.setenv("XDG_CONFIG_HOME", str(home / ".config"))
        monkeypatch.chdir(tmp_path)
        bash_exit = subprocess.run(
            ["bash", str(REPO / "scripts" / "validate.sh")], capture_output=True
        ).returncode
        ours = _cli_exit()
        assert bash_exit == 2
        assert ours == 2


class TestRules:
    def _make_bundle(self, tmp_path):
        bundle = tmp_path / "bundle"
        bundle.mkdir()
        (bundle / "index.md").write_text(
            "---\nokf_version: \"0.2\"\n---\n\n# B\n", encoding="utf-8"
        )
        return bundle

    def test_missing_type_is_e2_error(self, tmp_path):
        bundle = self._make_bundle(tmp_path)
        page = bundle / "concepts"
        page.mkdir()
        (page / "no-type.md").write_text(
            "---\ntitle: T\ndescription: D\n---\n\nBody\n", encoding="utf-8"
        )
        result = lint_bundle(bundle)
        assert result.ok is False
        assert any("(E2)" in e for e in result.errors)

    def test_stale_page_warns_w7(self, tmp_path):
        bundle = self._make_bundle(tmp_path)
        page = bundle / "concepts"
        page.mkdir()
        (page / "stale.md").write_text(
            "---\n"
            "type: Concept\n"
            "title: T\n"
            "description: D\n"
            "stale_after: 2020-01-01T00:00:00Z\n"
            "---\n\nBody\n",
            encoding="utf-8",
        )
        result = lint_bundle(bundle)
        assert result.ok is True  # warnings only
        assert any("(W7)" in w for w in result.warnings)

    def test_fresh_page_passes(self, tmp_path):
        bundle = self._make_bundle(tmp_path)
        page = bundle / "concepts"
        page.mkdir()
        (page / "ok.md").write_text(
            "---\n"
            "type: Concept\n"
            "title: T\n"
            "description: D\n"
            "stale_after: 2999-01-01T00:00:00Z\n"
            "---\n\nBody\n",
            encoding="utf-8",
        )
        result = lint_bundle(bundle)
        assert result.ok is True
        assert result.errors == []
