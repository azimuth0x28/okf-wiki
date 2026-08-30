"""okf-wiki CLI entry point.

Card 01 subcommands: list / info / doctor. Later cards add invariant
subcommands (lint, trust-check, cache-*, batch-plan, sync, capture, query...).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List, Optional

from okf_wiki import __version__
from okf_wiki.config import Config, ConfigError, global_config_dir, list_named_bundles, resolve_config


def _cmd_list(_args: argparse.Namespace) -> int:
    profiles = list_named_bundles()
    active: Optional[str] = None
    gcfg = global_config_dir() / "config"
    if gcfg.is_symlink():
        active = Path.resolve(gcfg).name.removeprefix("config.")
    if not profiles:
        print(f"No named bundle profiles in {global_config_dir()}")
        return 0
    print("Bundle profiles:")
    for name in sorted(profiles):
        marker = " (active)" if name == active else ""
        print(f"  {name}{marker}  →  {profiles[name]}")
    return 0


def _cmd_info(args: argparse.Namespace) -> int:
    cfg = resolve_config(args.name)
    print(f"okf-wiki {__version__}")
    print(f"config source:  {cfg.source}" + (f" ({cfg.config_file})" if cfg.config_file else ""))
    print(f"bundle path:    {cfg.bundle_path if cfg.bundle_path else '(unset)'}")
    print(f"repo path:      {cfg.repo_path if cfg.repo_path else '(unset)'}")
    print(f"global dir:     {global_config_dir()}")
    if cfg.name:
        print(f"profile:        @{cfg.name}")
    return 0


def _cmd_doctor(args: argparse.Namespace) -> int:
    """Validate the resolved configuration and the bundle's basic OKF shape."""
    problems: List[str] = []
    try:
        cfg: Config = resolve_config(args.name)
    except ConfigError as exc:
        print(f"✗ config: {exc}")
        return 1

    print(f"okf-wiki doctor{f' @{cfg.name}' if cfg.name else ''}")
    if cfg.config_file:
        print(f"✓ config resolved: {cfg.config_file} (source: {cfg.source})")
    else:
        problems.append("no configuration found (.env walk-up and global config both empty)")

    bundle = cfg.bundle_path
    if bundle is None:
        problems.append("OKF_BUNDLE_PATH is not set")
    elif not bundle.is_dir():
        problems.append(f"bundle path does not exist: {bundle}")
    else:
        print(f"✓ bundle path exists: {bundle}")
        index = bundle / "index.md"
        if not index.is_file():
            problems.append(f"root index.md missing in {bundle}")
        else:
            okf_declared = any(
                line.strip().startswith("okf_version:")
                for line in index.read_text(encoding="utf-8", errors="replace").splitlines()[:20]
            )
            if okf_declared:
                print("✓ root index.md declares okf_version")
            else:
                problems.append("root index.md has no okf_version declaration (expected for OKF v0.2)")

    if problems:
        for p in problems:
            print(f"✗ {p}")
        return 1
    print("All checks passed.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="okf-wiki",
        description="OKF v0.2 knowledge-bundle CLI (mirrors the .skills/ framework invariants)",
    )
    parser.add_argument("--version", action="version", version=f"okf-wiki {__version__}")
    sub = parser.add_subparsers(dest="command", metavar="<command>")

    sub.add_parser("list", help="list available bundle profiles (@name targets)")
    p_info = sub.add_parser("info", help="show resolved config paths and version")
    p_info.add_argument("--name", help="inline @name bundle override")
    p_doc = sub.add_parser("doctor", help="validate resolved config and bundle shape")
    p_doc.add_argument("--name", help="inline @name bundle override")

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    handlers = {"list": _cmd_list, "info": _cmd_info, "doctor": _cmd_doctor}
    handler = handlers.get(args.command)
    if handler is None:
        parser.print_help()
        return 2
    try:
        return handler(args)
    except ConfigError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
