"""HTTP + MCP front end so remote systems can use a bundle as memory.

Single tenant: one process serves one bundle with one API key. The server
performs no LLM work — it exposes read/append operations over the bundle.

Needs the ``server`` extra::

    pip install 'okf-wiki[server]'

Run::

    python -m okf_wiki.server          # or: okf-wiki serve

Environment:
    OKF_BUNDLE_PATH       bundle root (falls back to the Config Resolution
                          Protocol, then /bundle for the container contract)
    WIKI_API_KEY          required bearer token (401 without it)
    WIKI_ALLOW_ANONYMOUS  "1" disables auth for local development
    WIKI_PORT             listen port (default 8080)

The write endpoint delegates to :func:`okf_wiki.capture.capture` — the A3
memo loop that appends v0.2-shaped ``_raw/`` pages. Full-page authoring
stays with the skills/``sync`` flow; this API is for quick capture from
external systems.
"""

from __future__ import annotations

import hmac
import os
import re
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field

from okf_wiki.capture import capture
from okf_wiki.config import ConfigError, resolve_config


def _default_bundle() -> Path:
    env = os.environ.get("OKF_BUNDLE_PATH", "")
    if env:
        return Path(env)
    try:
        cfg = resolve_config(None)
        if cfg.bundle_path:
            return Path(cfg.bundle_path)
    except ConfigError:
        pass
    # Container contract (A8): OKF_BUNDLE_PATH=/bundle is mounted as a volume.
    return Path("/bundle")


def _default_api_key() -> str:
    return os.environ.get("WIKI_API_KEY", "")


def _default_anonymous() -> bool:
    return os.environ.get("WIKI_ALLOW_ANONYMOUS") == "1"


def _slug(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-") or "untitled"


class PageWrite(BaseModel):
    title: str
    category: str = "concepts"
    content: str = ""
    tags: list[str] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)
    summary: str = ""
    project: Optional[str] = None


class PackRequest(BaseModel):
    topic: str = ""
    budget: int = 8000


def create_app(
    bundle: Optional[Path] = None,
    api_key: Optional[str] = None,
    anonymous: Optional[bool] = None,
) -> FastAPI:
    """Build the FastAPI app.

    Args override environment, which overrides defaults. The no-key guard
    lives here so booting without ``WIKI_API_KEY`` fails observably.
    """
    if bundle is None:
        bundle = _default_bundle()
    if api_key is None:
        api_key = _default_api_key()
    if anonymous is None:
        anonymous = _default_anonymous()
    if not api_key and not anonymous:
        raise RuntimeError(
            "refusing to start without WIKI_API_KEY. "
            "Set it, or set WIKI_ALLOW_ANONYMOUS=1 for local development."
        )

    root = bundle.resolve()

    def _resolve(rel: str) -> Path:
        target = (root / rel).resolve()
        # Trust boundary: URL-supplied paths must stay inside the bundle.
        if target != root and root not in target.parents:
            raise HTTPException(status_code=400, detail="path escapes the bundle")
        return target

    def require_key(request: Request) -> None:
        if anonymous:
            return
        token = ""
        auth = request.headers.get("authorization", "")
        if auth.startswith("Bearer "):
            token = auth[len("Bearer ") :]
        if not hmac.compare_digest(token, api_key):
            raise HTTPException(status_code=401, detail="missing or invalid API key")

    # --- operations over the bundle -------------------------------------

    def search(q: str, limit: int = 8) -> list[dict[str, Any]]:
        from okf_wiki.graph import graph_query

        return graph_query(root, q.split(), graph_json=None)[:limit]

    def read_page(path: str) -> dict[str, Any]:
        target = _resolve(path)
        if not target.is_file():
            raise HTTPException(status_code=404, detail="page not found")
        return {"path": path, "markdown": target.read_text(encoding="utf-8")}

    def write_page(payload: PageWrite) -> dict[str, Any]:
        note_parts = [payload.summary, payload.content]
        note = "\n\n".join(p for p in note_parts if p.strip())
        written = capture(
            root,
            title=payload.title,
            tags=list(payload.tags) or ["web-capture", "raw-ingest"],
            project=payload.project,
            note=note,
            source=payload.sources[0] if payload.sources else "api",
        )
        return {
            "path": str(written.relative_to(root)),
            "created": True,
        }

    def context_pack(payload: PackRequest) -> dict[str, Any]:
        from okf_wiki.context_pack import build_pack

        pack = build_pack(root, payload.topic, budget_tokens=payload.budget)
        return {
            "topic": pack["topic"],
            "pages_included": pack["pages_included"],
            "tokens_used": pack["tokens_used"],
            "text": pack["text"],
        }

    # --- MCP (optional: requires the server extra) ----------------------

    mcp_state: dict[str, Any] = {}

    try:
        from mcp.server.mcpserver import MCPServer

        mcp = MCPServer("okf-wiki")
        # tool() is a decorator factory: mcp.tool(name=...)(fn).
        mcp.tool(name="memory_search")(search)
        mcp.tool(name="memory_read")(read_page)
        mcp.tool(name="memory_write")(write_page)
        mcp.tool(name="memory_context_pack")(context_pack)
        # Build the streamable app BEFORE session_manager is touched: the
        # session manager is created lazily by this call (accessing it
        # earlier raises RuntimeError).
        mcp_state["app"] = mcp.streamable_http_app(
            streamable_http_path="/", stateless_http=True
        )
        mcp_state["manager"] = mcp.session_manager
    except ImportError:
        mcp_state["app"] = None

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Without running the session manager, /mcp accepts the first
        # request then hangs.
        if mcp_state.get("manager") is not None:
            async with mcp_state["manager"].run():
                yield
        else:
            yield

    app = FastAPI(title="okf-wiki memory", lifespan=lifespan)
    if mcp_state.get("app") is not None:
        app.mount("/mcp", mcp_state["app"])

    @app.get("/health")
    def health() -> dict[str, Any]:
        return {"ok": root.is_dir(), "bundle": str(root)}

    @app.get("/v1/search")
    async def v1_search(request: Request, q: str, limit: int = 8) -> Any:
        require_key(request)
        return search(q, limit)

    @app.get("/v1/pages/{path:path}")
    async def v1_read(request: Request, path: str) -> Any:
        require_key(request)
        return read_page(path)

    @app.post("/v1/pages", status_code=201)
    async def v1_write(request: Request, payload: PageWrite) -> Any:
        require_key(request)
        return write_page(payload)

    @app.post("/v1/context-pack")
    async def v1_pack(request: Request, payload: PackRequest) -> Any:
        require_key(request)
        return context_pack(payload)

    return app


def __getattr__(name: str) -> Any:
    # PEP 562: build the env-configured app lazily so importing this module
    # (e.g. from tests or `okf-wiki server --help`) does not trip the
    # no-API-key boot guard.
    if name == "app":
        return create_app()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def main() -> None:
    import uvicorn

    uvicorn.run(
        create_app(),
        host="0.0.0.0",
        port=int(os.environ.get("WIKI_PORT", "8080")),
    )


if __name__ == "__main__":
    main()
