"""Tests for ast_extractor + code_understanding (card 07 / T-P3.2)."""

import json
import subprocess
from pathlib import Path

import pytest

from okf_wiki.ast_extractor import extract
from okf_wiki.code_understanding import (
    ProviderError,
    code_understand,
    index_state,
    resolve_backend,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_project(tmp_path: Path) -> Path:
    """Mini-repo: alpha.py defines symbols, beta.py references one of them."""
    proj = tmp_path / "mini-repo"
    proj.mkdir()
    (proj / "alpha.py").write_text(
        '"""Alpha module."""\n'
        "import os\n"
        "from collections import OrderedDict\n\n\n"
        "class AlphaService:\n"
        '    """Does alpha things."""\n\n'
        "    def run(self):\n"
        "        return helper()\n\n\n"
        "def helper():\n"
        "    return 42\n\n\n"
        "def _private_thing():\n"
        "    return 0\n",
        encoding="utf-8",
    )
    (proj / "beta.py").write_text(
        "from alpha import AlphaService\n\n\n"
        "def consumer():\n"
        "    return AlphaService().run()\n",
        encoding="utf-8",
    )
    (proj / "node_modules").mkdir()
    (proj / "node_modules" / "junk.py").write_text("class Junk:\n    pass\n", encoding="utf-8")
    return proj


# ---------------------------------------------------------------------------
# ast_extractor
# ---------------------------------------------------------------------------


class TestAstExtract:
    def test_python_file_nodes_and_edges(self, tmp_path: Path) -> None:
        proj = _make_project(tmp_path)
        data = extract(proj / "alpha.py")
        kinds = {n["kind"] for n in data["nodes"]}
        assert "file" in kinds and "class" in kinds and "function" in kinds
        labels = {n["label"] for n in data["nodes"]}
        assert "AlphaService" in labels and "helper" in labels
        # private/dunder functions are skipped
        assert "_private_thing" not in labels
        relations = {e["relation"] for e in data["edges"]}
        assert "defines" in relations and "imports" in relations
        imports = {e["target"] for e in data["edges"] if e["relation"] == "imports"}
        assert "import::os" in imports

    def test_inheritance_edge(self, tmp_path: Path) -> None:
        src = tmp_path / "m.py"
        src.write_text("class Base:\n    pass\n\n\nclass Child(Base):\n    pass\n", encoding="utf-8")
        data = extract(src)
        inherits = [e for e in data["edges"] if e["relation"] == "inherits"]
        assert len(inherits) == 1
        assert inherits[0]["source"].endswith("::Child")
        assert inherits[0]["target"].endswith("::Base")

    def test_javascript_imports(self, tmp_path: Path) -> None:
        src = tmp_path / "app.js"
        src.write_text(
            "const fs = require('fs');\nimport path from 'path';\n\n"
            "class App {}\n\nfunction main() {}\n",
            encoding="utf-8",
        )
        data = extract(src)
        langs = {n["language"] for n in data["nodes"]}
        assert "javascript" in langs
        imports = {e["target"] for e in data["edges"] if e["relation"] == "imports"}
        assert "import::fs" in imports and "import::path" in imports

    def test_directory_skips_junk_dirs(self, tmp_path: Path) -> None:
        proj = _make_project(tmp_path)
        data = extract(proj)  # dispatches dirs to extract_directory, returns dict
        files = {n["file"] for n in data["nodes"]}
        assert files  # some files processed
        assert all("node_modules" not in f for f in files)
        assert data["stats"]["files_processed"] >= 2

    def test_missing_path_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            extract(tmp_path / "nope")

    def test_to_dict_god_nodes(self, tmp_path: Path) -> None:
        proj = _make_project(tmp_path)
        data = extract(proj)
        assert "god_nodes" in data and "stats" in data
        assert isinstance(data["god_nodes"], list)


# ---------------------------------------------------------------------------
# code_understanding
# ---------------------------------------------------------------------------


class TestResolveBackend:
    def test_flag_beats_env(self) -> None:
        mode, warnings = resolve_backend(
            flag="builtin",
            env_backend="codegraph",
        )
        assert mode == "builtin" and warnings == []

    def test_env_beats_auto(self) -> None:
        mode, _ = resolve_backend(env_backend="builtin")
        assert mode == "builtin"

    def test_explicit_codegraph_missing_binary_raises(self) -> None:
        with pytest.raises(ProviderError):
            resolve_backend(flag="codegraph", env_bin="")

    def test_explicit_codegraph_with_env_bin_ok(self) -> None:
        mode, _ = resolve_backend(flag="codegraph", env_bin="/usr/bin/env")
        assert mode == "codegraph"


class TestIndexState:
    def test_uninitialized(self, tmp_path: Path) -> None:
        initialized, fresh, detail = index_state(tmp_path)
        assert initialized is False and fresh is False
        assert "no index" in detail


class TestCodeUnderstand:
    def test_builtin_focus_map_on_mini_repo(self, tmp_path: Path) -> None:
        proj = _make_project(tmp_path)
        result = code_understand(proj, backend_flag="builtin", max_symbols=20)
        assert result["backend"] == "builtin"
        assert result["project"] == str(proj.resolve())
        assert result["focus_map"], "expected non-empty focus map"
        # The defining module's symbols are ranked first with ast evidence.
        top = result["focus_map"][0]
        assert top["symbol"] in {"AlphaService", "helper"}
        assert top["file"] == "alpha.py"
        assert top["evidence"] in {"ast", "changed-file", "rg-reference"}
        # Seed files cover the tracked code files.
        assert "alpha.py" in result["seed_files"]
        assert "beta.py" in result["seed_files"]
        # Ranks are 1-based and dense.
        ranks = [item["rank"] for item in result["focus_map"]]
        assert ranks == list(range(1, len(ranks) + 1))

    def test_changed_seeds_mark_changed_file_evidence(self, tmp_path: Path) -> None:
        proj = _make_project(tmp_path)
        result = code_understand(
            proj, backend_flag="builtin", changed=["alpha.py"], max_symbols=20
        )
        changed = [it for it in result["focus_map"] if it["evidence"] == "changed-file"]
        assert changed, "seed-file symbols should carry changed-file evidence"
        assert all(it["file"] == "alpha.py" for it in changed)

    def test_auto_falls_back_to_builtin_with_warning(self, tmp_path: Path) -> None:
        proj = _make_project(tmp_path)
        env = {"CODE_UNDERSTANDING_BACKEND": "", "PATH": ""}
        # No codegraph on PATH and no env bin -> auto resolves to builtin.
        result = code_understand(proj, max_symbols=20, env=env)
        assert result["backend"] == "builtin"
        assert any("codegraph not available" in w for w in result["warnings"])

    def test_missing_project_raises(self, tmp_path: Path) -> None:
        with pytest.raises(ProviderError):
            code_understand(tmp_path / "nope", backend_flag="builtin")

    def test_codegraph_backend_missing_binary_raises(self, tmp_path: Path) -> None:
        with pytest.raises(ProviderError):
            code_understand(
                _make_project(tmp_path),
                backend_flag="codegraph",
                env={"CODE_UNDERSTANDING_CODEGRAPH_BIN": ""},
            )
