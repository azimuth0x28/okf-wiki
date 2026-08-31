"""Session graph (sessions-*) end-to-end tests over the agent-history fixture."""
import json
from pathlib import Path

import pytest

from okf_wiki.sessions.graph import build, load_graph, set_cluster_names
from okf_wiki.sessions.query import query, show
from okf_wiki.sessions.viz import render_html

FIXTURE = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "agent-history"
KW = {"claude_dir": FIXTURE, "min_sim": 0.02}


@pytest.fixture()
def sidecar(tmp_path):
    out = tmp_path / "sg"
    build(out_dir=out, **KW)
    return out


def _cluster_by_id(clusters, cid):
    return next(c for c in clusters if c["id"] == cid)


class TestBuild:
    def test_build_creates_sidecar_with_stats(self, sidecar):
        for name in ("graph.json", "clusters.json", "docs.jsonl", "state.json", "idf.json"):
            assert (sidecar / name).is_file(), name
        graph, clusters_doc = load_graph(sidecar)
        assert graph["stats"]["sessions"] == 3
        assert graph["stats"]["full"] == 3
        assert graph["stats"]["thin"] == 0

    def test_cluster_covers_connected_pair(self, sidecar):
        graph, clusters_doc = load_graph(sidecar)
        assert graph["stats"]["edges"] >= 1
        assert clusters_doc["clusters"]
        clustered = {n["cluster"] for n in graph["nodes"]}
        assert any(c != -1 for c in clustered)

    def test_rebuild_reuses_state(self, sidecar):
        graph_before, _ = load_graph(sidecar)
        info = build(out_dir=sidecar, **KW)
        graph_after, _ = load_graph(sidecar)
        assert info["stats"]["reused"] > 0
        assert [n["id"] for n in graph_after["nodes"]] == [n["id"] for n in graph_before["nodes"]]
        assert graph_after["edges"] == graph_before["edges"]


class TestQuery:
    def test_query_finds_topic_session(self, sidecar):
        result = query(sidecar, "rate limiting api")
        cands = result["candidates"]
        assert cands, "expected at least one hit"
        assert "rate" in cands[0]["title"].lower()

    def test_query_without_graph_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            query(tmp_path / "missing", "anything")


class TestNaming:
    def test_name_persists_across_rebuild(self, sidecar):
        graph, clusters_doc = load_graph(sidecar)
        cid = clusters_doc["clusters"][0]["id"]
        out = set_cluster_names(sidecar, [{
            "id": cid, "name": "Rate limiting client work",
            "summary": "API rate limiting and per-client rate decisions",
        }])
        assert out["named"] == 1
        info = build(out_dir=sidecar, **KW)
        assert info["names_carried_over"] >= 1
        _graph, after = load_graph(sidecar)
        named = [c for c in after["clusters"] if c.get("name")]
        assert named and named[0]["name"] == "Rate limiting client work"

    def test_unnamed_filter(self, sidecar):
        graph, clusters_doc = load_graph(sidecar)
        cid = clusters_doc["clusters"][0]["id"]
        set_cluster_names(sidecar, [{"id": cid, "name": "Named", "summary": "s"}])
        _g, after = load_graph(sidecar)
        unnamed = [c for c in after["clusters"] if not c.get("name")]
        assert unnamed == []


class TestViz:
    def test_html_standalone_no_cdn(self, sidecar):
        graph, clusters_doc = load_graph(sidecar)
        render_html(graph, clusters_doc, out_dir=sidecar)
        html = (sidecar / "graph.html").read_text()
        assert len(html) > 1000
        assert "http://" not in html and "https://" not in html


class TestShow:
    def test_show_returns_cluster_and_neighbors(self, sidecar):
        graph, _clusters = load_graph(sidecar)
        sid = next(n["id"] for n in graph["nodes"] if n.get("cluster", -1) != -1)
        result = show(sidecar, sid)
        assert result["session"]["id"] == sid
        assert result["cluster"] is not None
        assert result["cluster"]["name"] or result["cluster"]["label"]
