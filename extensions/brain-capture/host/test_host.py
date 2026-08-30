#!/usr/bin/env python3
"""Wire-protocol end-to-end test for the Brain Capture native host.

Runs the real host as a subprocess with a throwaway XDG config pointing at a
throwaway bundle, speaks the 4-byte-length-prefix protocol over pipes, and
asserts that a capture message produces a valid _raw/ page. No browser needed.
"""

import json
import os
import struct
import subprocess
import sys
import time
from pathlib import Path

HOST = Path(__file__).with_name("brain_capture_host.py")
REPO = Path(__file__).resolve().parents[3]


def send(host_path, payload, env):
    data = json.dumps(payload).encode("utf-8")
    proc = subprocess.run(
        [sys.executable, str(host_path)],
        input=struct.pack("<I", len(data)) + data,
        capture_output=True,
        timeout=120,
        env=env,
    )
    if proc.stderr:
        print(proc.stderr.decode("utf-8")[:2000], file=sys.stderr)
    if len(proc.stdout) < 4:
        raise RuntimeError(f"no host response (rc={proc.returncode}): {proc.stdout[:200]!r}")
    (length,) = struct.unpack("<I", proc.stdout[:4])
    return json.loads(proc.stdout[4 : 4 + length])


def main() -> int:
    tmp = Path(__file__).resolve().parent / ".tmp-e2e"
    bundle = tmp / "bundle"
    xdg = tmp / "xdg"
    bundle.mkdir(parents=True, exist_ok=True)
    xdg.mkdir(parents=True, exist_ok=True)
    (bundle / "index.md").write_text('---\nokf_version: "0.2"\n---\n\n# E2E bundle\n')
    (xdg / "okf-wiki").mkdir(parents=True, exist_ok=True)
    (xdg / "okf-wiki" / "config").write_text(f'OKF_BUNDLE_PATH="{bundle}"\n')

    env = {
        **{k: v for k, v in os.environ.items() if k not in ("OKF_BUNDLE_PATH",)},
        "HOME": str(tmp),
        "XDG_CONFIG_HOME": str(xdg),
        "PATH": f"{REPO / '.venv' / 'bin'}:{os.environ.get('PATH', '')}",
        "OKF_WIKI_BRAIN_CAPTURE_LOG": str(tmp / "host.log"),
    }

    vaults = send(HOST, {"type": "vaults"}, env)
    assert vaults.get("ok") is True, f"vaults failed: {vaults}"
    assert any(b["path"] == str(bundle) for b in vaults["bundles"]), vaults
    print(f"vaults ok: {len(vaults['bundles'])} bundle(s)")

    capture = send(
        HOST,
        {
            "type": "capture",
            "bundle": "",
            "title": "Wire e2e page",
            "url": "https://example.com/e2e",
            "text": "captured by test_host.py",
            "note": "assertion payload",
        },
        env,
    )
    assert capture.get("ok") is True, f"capture failed: {capture}"
    raw_dir = bundle / "_raw"
    pages = sorted(raw_dir.glob("*.md")) if raw_dir.is_dir() else []
    assert pages, f"no _raw page created: {capture}"
    body = pages[0].read_text()
    for marker in ("type: Concept", "generated:", "sources:", "resource:"):
        assert marker in body, f"missing {marker!r} in {pages[0].name}"
    print(f"capture ok: {capture['path']} (frontmatter valid)")

    print("PASS — wire protocol e2e complete")
    return 0


if __name__ == "__main__":
    started = time.time()
    code = main()
    print(f"elapsed: {time.time() - started:.1f}s")
    sys.exit(code)
