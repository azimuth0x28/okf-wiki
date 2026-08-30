"""HTTP/MCP server contract tests (no API key in env — factories only)."""

import os

import pytest
from fastapi.testclient import TestClient

# Server tests need the [server] extra; a bare (stdlib-core) install skips them.
pytest.importorskip("fastapi")

from okf_wiki.server import create_app

BUNDLE_INDEX = '---\nokf_version: "0.2"\n---\n\n# Test Bundle\n'


def _make_bundle(tmp_path):
    bundle = tmp_path / "bundle"
    (bundle / "concepts").mkdir(parents=True)
    (bundle / "index.md").write_text(BUNDLE_INDEX, encoding="utf-8")
    (bundle / "concepts" / "alpha.md").write_text(
        "---\ntype: Concept\ntitle: Alpha\nstatus: draft\ngenerated:\n"
        "  by: tester/1.0\n  at: 2026-01-01T00:00:00Z\n---\n\n# Alpha\n\nalpha body\n",
        encoding="utf-8",
    )
    return bundle


@pytest.fixture()
def bundle(tmp_path):
    return _make_bundle(tmp_path)


@pytest.fixture()
def client(bundle):
    app = create_app(bundle=bundle, api_key="secret")
    return TestClient(app)


class TestHealth:
    def test_health_no_auth(self, client, bundle):
        resp = client.get("/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True
        assert body["bundle"] == str(bundle.resolve())


class TestAuth:
    def test_endpoints_401_without_key(self, client):
        # Body validation (422) happens before the handler's auth check, so
        # POST cases send well-formed bodies to prove the 401 path.
        page = {"title": "T", "content": "c"}
        pack = {"topic": "t"}
        for method, url, payload in (
            ("get", "/v1/search?q=x", None),
            ("get", "/v1/pages/concepts/alpha.md", None),
            ("post", "/v1/pages", page),
            ("post", "/v1/context-pack", pack),
        ):
            kwargs = {"json": payload} if payload is not None else {}
            resp = getattr(client, method)(url, **kwargs)
            assert resp.status_code == 401

    def test_endpoints_200_with_bearer(self, client):
        headers = {"Authorization": "Bearer secret"}
        resp = client.get("/v1/search?q=alpha", headers=headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_wrong_key_401(self, client):
        resp = client.get("/v1/search?q=alpha", headers={"Authorization": "Bearer nope"})
        assert resp.status_code == 401


class TestBootGuard:
    def test_runtime_error_without_key(self):
        with pytest.raises(RuntimeError):
            create_app(api_key="", anonymous=False)

    def test_anonymous_open(self, bundle):
        app = create_app(bundle=bundle, api_key="", anonymous=True)
        c = TestClient(app)
        assert c.get("/health").status_code == 200
        assert c.get("/v1/search?q=alpha").status_code == 200


class TestEndpoints:
    def test_read_page_and_404(self, client):
        headers = {"Authorization": "Bearer secret"}
        ok = client.get("/v1/pages/concepts/alpha.md", headers=headers)
        assert ok.status_code == 200
        assert "# Alpha" in ok.json()["markdown"]
        missing = client.get("/v1/pages/concepts/nope.md", headers=headers)
        assert missing.status_code == 404

    def test_escape_rejected(self, client):
        # httpx normalizes literal ../ segments before sending; percent-encode
        # them so the route receives the raw traversal and the 400 fires.
        headers = {"Authorization": "Bearer secret"}
        resp = client.get("/v1/pages/%2e%2e/%2e%2e/etc/passwd", headers=headers)
        assert resp.status_code == 400

    def test_write_creates_raw_capture(self, client, bundle):
        headers = {"Authorization": "Bearer secret"}
        resp = client.post(
            "/v1/pages",
            headers=headers,
            json={"title": "Api Memo", "tags": ["api"], "content": "memo body"},
        )
        assert resp.status_code == 201
        rel = resp.json()["path"]
        assert rel.startswith("_raw/")
        raw = (bundle / rel).read_text(encoding="utf-8")
        assert "type: Concept" in raw
        assert "generated:" in raw
        assert "resource:" in raw

    def test_context_pack(self, client):
        headers = {"Authorization": "Bearer secret"}
        resp = client.post(
            "/v1/context-pack", headers=headers, json={"topic": "alpha", "budget": 500}
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["pages_included"] >= 1
        assert "Alpha" in body["text"]


class TestMcpOptional:
    def test_app_builds_without_mcp_extra(self, bundle, monkeypatch):
        import sys

        monkeypatch.setitem(sys.modules, "mcp", None)
        app = create_app(bundle=bundle, api_key="k")
        c = TestClient(app)
        assert c.get("/health").status_code == 200
