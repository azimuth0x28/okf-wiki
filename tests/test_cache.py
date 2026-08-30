"""Tests for okf_wiki.cache — deterministic hashing and delta detection."""

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

from okf_wiki.cache import (
    cache_hash,
    cache_update,
    canonical_key,
    load_manifest,
    save_manifest,
    upsert_entry,
)

BUNDLE_MD = """---
type: Concept
title: Sample
description: A sample page.
---

Body
"""


def _make_bundle(tmp_path):
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    (bundle / "index.md").write_text("---\nokf_version: \"0.2\"\n---\n\n# B\n", encoding="utf-8")
    sources = tmp_path / "sources"
    sources.mkdir()
    src = sources / "note.md"
    src.write_text("source note\n", encoding="utf-8")
    return bundle, src


def _now():
    return datetime.now(timezone.utc).isoformat()


def _persist(bundle, manifest, key):
    upsert_entry(manifest, "sources", key, {"ingested_at": _now()})
    save_manifest(bundle, manifest)


class TestCacheHash:
    def test_hash_is_deterministic(self, tmp_path):
        bundle, _src = _make_bundle(tmp_path)
        manifest_path = bundle / ".manifest.json"
        manifest_path.write_text(
            json.dumps({"version": 1, "sources": {}, "projects": {}, "stats": {}}),
            encoding="utf-8",
        )
        first = cache_hash(bundle)
        second = cache_hash(bundle)
        assert first == second
        assert len(first) == 64

    def test_hash_changes_with_manifest(self, tmp_path):
        bundle, _src = _make_bundle(tmp_path)
        manifest_path = bundle / ".manifest.json"
        manifest_path.write_text(
            json.dumps({"version": 1, "sources": {}, "projects": {}, "stats": {}}),
            encoding="utf-8",
        )
        before = cache_hash(bundle)
        manifest = load_manifest(bundle)
        manifest["sources"]["/tmp/x"] = {"ingested_at": "2026-01-01T00:00:00Z"}
        manifest_path.write_text(
            json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8"
        )
        after = cache_hash(bundle)
        assert before != after


class TestCacheUpdate:
    def test_new_then_unchanged(self, tmp_path):
        bundle, src = _make_bundle(tmp_path)
        first = cache_update(bundle)
        assert first["new"] == [canonical_key(str(src))]
        _persist(bundle, first["manifest"], canonical_key(str(src)))

        second = cache_update(bundle)
        assert second["new"] == []
        assert second["unchanged"] == 1

    def test_mtime_bump_marks_modified(self, tmp_path):
        bundle, src = _make_bundle(tmp_path)
        first = cache_update(bundle)
        assert first["new"] == [canonical_key(str(src))]
        _persist(bundle, first["manifest"], canonical_key(str(src)))
        future = time.time() + 120
        os.utime(src, (future, future))
        result = cache_update(bundle)
        assert result["modified"] == [canonical_key(str(src))]

    def test_entry_keeps_page_lists_on_merge(self, tmp_path):
        bundle, src = _make_bundle(tmp_path)
        cache_update(bundle)
        key = canonical_key(str(src))
        manifest = load_manifest(bundle)
        manifest["sources"][key] = {
            "ingested_at": "2026-01-01T00:00:00Z",
            "pages_created": ["concepts/sample.md"],
        }
        upsert_entry(manifest, "sources", key, {"ingested_at": "2026-02-01T00:00:00Z"})
        save_manifest(bundle, manifest)
        merged = load_manifest(bundle)["sources"][key]
        assert merged["ingested_at"] == "2026-02-01T00:00:00Z"
        assert "concepts/sample.md" in merged["pages_created"]
