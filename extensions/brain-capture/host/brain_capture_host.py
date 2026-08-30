#!/usr/bin/env python3
"""Brain Capture native-messaging host.

Wire protocol (4-byte little-endian length prefix + JSON on stdin/stdout) is
shared with the source project's host. The host resolves bundles through the
okf-wiki Config Resolution Protocol and delegates every capture to the
`okf-wiki capture` CLI, so markdown shaping lives in exactly one place.

Messages:
  {"type": "vaults"}                          -> {"ok": true, "bundles": [...]}
  {"type": "capture", "bundle": "", ...}      -> {"ok": true, "path": "..."}
"""

import json
import os
import shutil
import struct
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

HOME = Path.home()
LOG_PATH = Path(
    os.environ.get("OKF_WIKI_BRAIN_CAPTURE_LOG")
    or (HOME / ".config" / "okf-wiki" / "brain-capture.log")
)
MAX_MESSAGE_BYTES = 4 * 1024 * 1024

# Chrome launches this host with its own cwd and, on macOS, its own TCC
# context; relative lookups from that cwd can fail on paths the user can read
# fine from a shell. All resolution therefore starts from a neutral home.
NEUTRAL_CWD = HOME


def log(message: str) -> None:
    try:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with LOG_PATH.open("a", encoding="utf-8") as fh:
            fh.write(f"{stamp} {message}\n")
    except OSError:
        pass  # stdout is the wire; diagnostics are best-effort


def read_message() -> dict:
    raw_length = sys.stdin.buffer.read(4)
    if len(raw_length) < 4:
        raise EOFError("host stdin closed")
    (length,) = struct.unpack("<I", raw_length)
    if length > MAX_MESSAGE_BYTES:
        raise ValueError(f"message too large: {length}")
    return json.loads(sys.stdin.buffer.read(length).decode("utf-8"))


def write_message(payload: dict) -> None:
    data = json.dumps(payload).encode("utf-8")
    sys.stdout.buffer.write(struct.pack("<I", len(data)))
    sys.stdout.buffer.write(data)
    sys.stdout.buffer.flush()


def find_okf_wiki_bin() -> str:
    located = shutil.which("okf-wiki")
    if located:
        return located
    for candidate in (
        HOME / "Web-dev/_petProjects/AI/okf-wiki/.venv/bin/okf-wiki",
        HOME / ".local/bin/okf-wiki",
    ):
        if candidate.is_file():
            return str(candidate)
    raise FileNotFoundError(
        "okf-wiki CLI not found on PATH; install the package or symlink it into ~/.local/bin"
    )


def list_bundles() -> list:
    from okf_wiki.config import list_named_bundles, resolve_config

    bundles = []
    try:
        default = resolve_config(None)
        if default.bundle_path is not None:
            bundles.append(
                {
                    "name": "",
                    "label": "Default (active config)",
                    "path": str(default.bundle_path),
                    "exists": default.bundle_path.is_dir(),
                }
            )
        else:
            log("default bundle resolve returned no OKF_BUNDLE_PATH")
    except Exception as exc:  # noqa: BLE001 - reported to the popup, never fatal
        log(f"default bundle resolve failed: {exc}")

    for name, _path in sorted(list_named_bundles().items()):
        try:
            cfg = resolve_config(name)
            if cfg.bundle_path is None:
                log(f"bundle {name} has no OKF_BUNDLE_PATH")
                continue
            bundles.append(
                {
                    "name": name,
                    "label": name,
                    "path": str(cfg.bundle_path),
                    "exists": cfg.bundle_path.is_dir(),
                }
            )
        except Exception as exc:  # noqa: BLE001
            log(f"bundle {name} resolve failed: {exc}")
    return bundles


def build_note(message: dict) -> str:
    parts = [message.get("note") or "", message.get("selection") or "", message.get("text") or ""]
    note = "\n\n".join(part.strip() for part in parts if part and part.strip())
    return note[:60000]


def capture(message: dict) -> dict:
    from okf_wiki.config import resolve_config

    cfg = resolve_config((message.get("bundle") or "").strip() or None)
    if cfg.bundle_path is None:
        raise RuntimeError("bundle resolves to no OKF_BUNDLE_PATH — check okf-wiki config")
    title = (message.get("title") or "").strip() or "Web capture"
    url = (message.get("url") or "").strip()
    note = build_note(message)

    cmd = [
        find_okf_wiki_bin(),
        "capture",
        str(cfg.bundle_path),
        "--title",
        title,
        "--tags",
        "web-capture,raw-ingest",
        "--note",
        note,
        "--source",
        url,
    ]
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=60,
        cwd=str(NEUTRAL_CWD),
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip().splitlines()
        raise RuntimeError(detail[-1] if detail else f"okf-wiki capture exited {result.returncode}")

    for line in result.stdout.splitlines():
        if line.startswith("Captured:"):
            return {"ok": True, "path": line.split(":", 1)[1].strip()}
    raise RuntimeError("okf-wiki capture produced no path")


def dispatch(message: dict) -> dict:
    kind = message.get("type")
    if kind == "vaults":
        return {"ok": True, "bundles": list_bundles()}
    if kind == "capture":
        try:
            return capture(message)
        except Exception as exc:  # noqa: BLE001 - the popup shows this string
            log(f"capture failed: {exc}")
            return {"ok": False, "error": str(exc)}
    return {"ok": False, "error": f"unknown message type: {kind!r}"}


def main() -> int:
    try:
        while True:
            try:
                message = read_message()
            except EOFError:
                return 0
            write_message(dispatch(message))
    except Exception as exc:  # noqa: BLE001 - last-ditch wire error report
        log(f"fatal: {exc}")
        try:
            write_message({"ok": False, "error": str(exc)})
        except Exception:
            pass
        return 1


if __name__ == "__main__":
    os.chdir(NEUTRAL_CWD)
    sys.exit(main())
