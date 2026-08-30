"""Tests for okf_wiki.graph — 5-format export, determinism, edge rules, query filter."""

import hashlib
import json
from pathlib import Path

from okf_wiki.graph import export_graph, graph_query

REPO = Path(__file__).resolve().parents[1]
FORMATS = ("graph.json", "graph.graphml", "cypher.txt", "postgres.sql", "graph.html")


def _write_page(bundle: Path, rel: str, fm: str, body: str) -> Path:
    path = bundle / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"---\n{fm}\n---\n\n{body}\n", encoding="utf-8")
    return path


def _make_bundle(tmp_path) -> Path:
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    (bundle / "index.md").write_text("---\nokf_version: \"0.2\"\n---\n\n# B\n", encoding="utf-8")
    return bundle


class TestExport:
    def test_export_produces_five_nonempty_files(self, tmp_path):
        result = export_graph(REPO / "tests" / "fixtures" / "mini-bundle", tmp_path / "g")
        assert result["node_count"] >= 1
        assert result["edge_count"] >= 0
        for name in FORMATS:
            p = Path(result["paths"][name])
            assert p.is_file(), name
            assert p.stat().st_size > 0, name

    def test_graph_json_is_valid_node_link(self, tmp_path):
        result = export_graph(REPO / "tests" / "fixtures" / "mini-bundle", tmp_path / "g")
        data = json.loads(Path(result["paths"]["graph.json"]).read_text(encoding="utf-8"))
        assert data["directed"] is False
        assert data["multigraph"] is False
        assert isinstance(data["nodes"], list) and data["nodes"]
        assert isinstance(data["links"], list)
        assert "bundle_id" in data["graph"]
        assert data["graph"]["total_nodes"] == len(data["nodes"])
        assert data["graph"]["total_edges"] == len(data["links"])

    def test_export_is_byte_identical_on_rerun(self, tmp_path):
        bundle = REPO / "tests" / "fixtures" / "mini-bundle"
        first = export_graph(bundle, tmp_path / "g1")
        second = export_graph(bundle, tmp_path / "g2")
        for name in FORMATS:
            a = hashlib.md5(Path(first["paths"][name]).read_bytes()).hexdigest()
            b = hashlib.md5(Path(second["paths"][name]).read_bytes()).hexdigest()
            assert a == b, name


class TestEdges:
    def test_self_link_is_dropped(self, tmp_path):
        bundle = _make_bundle(tmp_path)
        _write_page(
            bundle, "concepts/loop.md",
            "title: Loop\ntype: Concept\ntags: [x]",
            "Self [reference](./loop.md) to itself.",
        )
        result = export_graph(bundle, tmp_path / "g")
        assert result["node_count"] == 1
        assert result["edge_count"] == 0

    def test_typed_relationship_wins_and_related_to_fallback(self, tmp_path):
        bundle = _make_bundle(tmp_path)
        _write_page(
            bundle, "concepts/base.md",
            "title: Base\ntype: Concept\ntags: [x]\n"
            "relationships:\n  - target: ./derived.md\n    type: extends",
            "Base body.",
        )
        _write_page(bundle, "concepts/derived.md", "title: Derived\ntype: Concept\ntags: [x]", "Derived body.")
        result = export_graph(bundle, tmp_path / "g")
        data = json.loads(Path(result["paths"]["graph.json"]).read_text(encoding="utf-8"))
        links = data["links"]
        assert len(links) == 1
        assert links[0]["relation"] == "extends"
        assert links[0]["confidence"] == 1.0


class TestGraphQuery:
    def test_query_filters_by_tokens(self, tmp_path):
        bundle = _make_bundle(tmp_path)
        _write_page(bundle, "concepts/cache.md", "title: Bitrix Cache\ntype: Concept\ntags: [php, cache]", "Caching body.")
        _write_page(bundle, "concepts/orm.md", "title: Bitrix ORM\ntype: Concept\ntags: [php, orm]", "ORM body.")
        hits = graph_query(bundle, ["cache"])
        assert len(hits) == 1
        assert hits[0]["label"] == "Bitrix Cache"

    def test_query_no_hits_returns_empty(self, tmp_path):
        bundle = _make_bundle(tmp_path)
        _write_page(bundle, "concepts/a.md", "title: Alpha\ntype: Concept\ntags: [x]", "Body.")
        assert graph_query(bundle, ["zebra"]) == []
