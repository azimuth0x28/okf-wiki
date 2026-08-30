"""okf-wiki CLI entry point.

Card 01 subcommands: list / info / doctor.
Card 02 subcommands: lint / trust-check / trust-record / cache-check /
cache-update / cache-hash / batch-plan.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
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


def _resolve_bundle(args: argparse.Namespace) -> Path:
    """Bundle dir from --bundle override or resolved config; ConfigError if unset."""
    cfg = resolve_config(getattr(args, "name", None))
    bundle = getattr(args, "bundle", None)
    target = Path(bundle).expanduser() if bundle else cfg.bundle_path
    if target is None:
        raise ConfigError("no bundle given: pass --bundle or set OKF_BUNDLE_PATH")
    return Path(target).expanduser().resolve()


def _cmd_lint(args: argparse.Namespace) -> int:
    from okf_wiki.lint import lint_bundle

    try:
        bundle = _resolve_bundle(args)
    except ConfigError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if not bundle.is_dir():
        print(f"error: not a directory: {bundle}", file=sys.stderr)
        return 2
    result = lint_bundle(bundle)
    print(result.summary())
    return 0 if result.ok else 1


def _load_page_frontmatter(path: Path) -> dict:
    """Minimal frontmatter parse: flat scalar keys between --- fences."""
    import re

    page: dict = {}
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    if not lines or lines[0].strip() != "---":
        return page
    block: List[str] = []
    for line in lines[1:]:
        if line.strip() == "---":
            break
        block.append(line)
    # naive flat YAML: top-level `key: value`, plus the two nested shapes the
    # trust commands emit and read back: generated.by/at and verified entries
    section = None
    for line in block:
        indented = bool(line) and line[0] in (" ", "\t")
        stripped = line.strip()
        if not indented:
            section = None
            m = re.match(r"^([A-Za-z_][\w-]*):\s*(.*)$", stripped)
            if m:
                page[m.group(1)] = m.group(2).strip().strip("'\"")
            if stripped == "generated:":
                page["generated"] = {}
                section = "generated"
            if stripped == "verified:":
                page["verified"] = []
                section = "verified"
        elif section == "generated" and stripped.startswith("by:"):
            page["generated"]["by"] = stripped[3:].strip()
        elif section == "generated" and stripped.startswith("at:"):
            page["generated"]["at"] = stripped[3:].strip()
        elif section == "verified" and stripped.startswith("- "):
            raw = stripped[2:]
            try:
                page["verified"].append(json.loads(raw))
            except json.JSONDecodeError:
                page["verified"].append({"by": raw.strip("'\"")})
    return page


def _cmd_trust_check(args: argparse.Namespace) -> int:
    """Print the trust rank chain for a page (A5: verified > human > machine)."""
    from okf_wiki.trust import trust_rank

    path = Path(args.page).expanduser()
    if not path.is_file():
        print(f"error: page not found: {path}", file=sys.stderr)
        return 1
    page = _load_page_frontmatter(path)
    rank = trust_rank(page)
    label = {2: "verified", 1: "human", 0: "machine"}[rank]
    verified = page.get("verified")
    by = page.get("generated", {}).get("by") if isinstance(page.get("generated"), dict) else None
    print(f"page:    {path}")
    print(f"rank:    {rank} ({label})")
    print(f"verified: {verified if verified else '(none)'}")
    print(f"generated.by: {by if by else '(unset)'}")
    return 0


def _cmd_trust_record(args: argparse.Namespace) -> int:
    """Append a verified: entry to a page's frontmatter (human/machine attestation)."""
    path = Path(args.page).expanduser()
    if not path.is_file():
        print(f"error: page not found: {path}", file=sys.stderr)
        return 1
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        print(f"error: {path} has no frontmatter", file=sys.stderr)
        return 1
    entry = {
        "by": args.by,
        "note": args.note or "",
        "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    rendered = "verified:\n  - " + json.dumps(entry, ensure_ascii=False) + "\n"
    close = next(i for i in range(1, len(lines)) if lines[i].strip() == "---")
    lines.insert(close, rendered)
    path.write_text("".join(lines), encoding="utf-8")
    print(f"recorded: {path} by={args.by}")
    return 0


def _cmd_cache_check(args: argparse.Namespace) -> int:
    from okf_wiki.cache import cache_check

    bundle = _resolve_bundle(args)
    if not bundle.is_dir():
        print(f"error: not a directory: {bundle}", file=sys.stderr)
        return 2
    report = cache_check(bundle)
    print(f"manifest: {bundle / '.manifest.json'}")
    print(f"sources:  {report['stats']['sources']}  projects: {report['stats']['projects']}")
    print(f"pages_created total: {report['stats']['pages_created']}  pages_updated total: {report['stats']['pages_updated']}")
    for p in report["problems"]:
        print(f"problem: {p}")
    return 0 if not report["problems"] else 1


def _cmd_cache_update(args: argparse.Namespace) -> int:
    from okf_wiki.cache import cache_update

    bundle = _resolve_bundle(args)
    if not bundle.is_dir():
        print(f"error: not a directory: {bundle}", file=sys.stderr)
        return 2
    skip = args.skip.split(",") if args.skip else []
    delta = cache_update(bundle, section=args.section, skip=skip)
    print(f"scan of {bundle}:")
    print(f"  new:      {len(delta['new'])}")
    print(f"  modified: {len(delta['modified'])}")
    print(f"  unchanged: {delta['unchanged']}")
    if args.dry_run:
        for k in delta["new"]:
            print(f"  NEW {k}")
        for k in delta["modified"]:
            print(f"  MOD {k}")
        return 0
    manifest = delta["manifest"]
    from okf_wiki.cache import save_manifest, _recount_stats

    now_iso = datetime.now(timezone.utc).isoformat(timespec="seconds")
    for k in delta["new"] + delta["modified"]:
        manifest.setdefault(args.section, {})[k] = {
            "ingested_at": now_iso,
            "pages_created": manifest.get(args.section, {}).get(k, {}).get("pages_created", []),
            "pages_updated": manifest.get(args.section, {}).get(k, {}).get("pages_updated", []),
        }
    _recount_stats(manifest)
    save_manifest(bundle, manifest)
    print(f"manifest updated: {bundle / '.manifest.json'}")
    return 0


def _cmd_cache_hash(args: argparse.Namespace) -> int:
    from okf_wiki.cache import cache_hash

    bundle = _resolve_bundle(args)
    if not bundle.is_dir():
        print(f"error: not a directory: {bundle}", file=sys.stderr)
        return 2
    print(cache_hash(bundle))
    return 0


def _cmd_batch_plan(args: argparse.Namespace) -> int:
    from okf_wiki.batch import batch_plan

    bundle = _resolve_bundle(args)
    if not bundle.is_dir():
        print(f"error: not a directory: {bundle}", file=sys.stderr)
        return 2
    skip = args.skip.split(",") if args.skip else []
    result = batch_plan(bundle, section=args.section, skip=skip)
    print(result["text"])
    return 0


def _cmd_capture(args: argparse.Namespace) -> int:
    from okf_wiki.capture import capture

    try:
        bundle = _resolve_bundle(args)
    except ConfigError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    if not bundle.is_dir():
        print(f"error: not a directory: {bundle}", file=sys.stderr)
        return 1
    tags = [t.strip() for t in args.tags.split(",") if t.strip()] if args.tags else None
    path = capture(
        bundle,
        title=args.title,
        tags=tags,
        project=args.project,
        note=args.note,
        confidence=args.confidence,
        page_type=args.type,
        source=args.source,
    )
    print(f"Captured: {path}")
    return 0


def _cmd_sync(args: argparse.Namespace) -> int:
    from okf_wiki.sync import SyncError, sync

    try:
        bundle = _resolve_bundle(args)
    except ConfigError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    try:
        _committed, message = sync(bundle, message=args.message, push=args.push)
    except SyncError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    if not args.quiet:
        print(message)
    return 0


def _cmd_sync_setup(args: argparse.Namespace) -> int:
    from okf_wiki.sync import SyncError, sync_setup

    try:
        bundle = _resolve_bundle(args)
    except ConfigError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    try:
        hook_path = sync_setup(bundle)
    except SyncError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"Installed post-commit hook: {hook_path}")
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

    def _add_bundle_sub(name: str, help_text: str) -> argparse.ArgumentParser:
        p = sub.add_parser(name, help=help_text)
        p.add_argument("bundle", nargs="?", help="bundle directory (default: resolved config)")
        p.add_argument("--name", help="inline @name bundle override")
        return p

    _add_bundle_sub("lint", "lint a bundle (parity with scripts/validate.sh, exit 0/1/2)")

    p_tc = sub.add_parser("trust-check", help="print trust rank (verified>human>machine) for a page")
    p_tc.add_argument("page", help="path to a bundle page")

    p_tr = sub.add_parser("trust-record", help="append a verified: entry to a page")
    p_tr.add_argument("page", help="path to a bundle page")
    p_tr.add_argument("--by", required=True, help="attesting actor, e.g. human:name or machine:tool")
    p_tr.add_argument("--note", help="optional attestation note")

    _add_bundle_sub("cache-check", "validate .manifest.json structure and recount stats")
    p_cu = _add_bundle_sub("cache-update", "scan sources and update the manifest delta")
    p_cu.add_argument("--section", default="sources", choices=["sources", "projects"])
    p_cu.add_argument("--skip", help="comma-separated substrings to skip")
    p_cu.add_argument("--dry-run", action="store_true", help="print NEW/MOD keys without writing")
    p_ch = _add_bundle_sub("cache-hash", "deterministic sha256 over the canonicalized manifest")
    p_ch.add_argument("--section", default="sources")

    p_bp = _add_bundle_sub("batch-plan", "ordered NEW/MOD ingest plan from the manifest delta")
    p_bp.add_argument("--section", default="sources", choices=["sources", "projects"])
    p_bp.add_argument("--skip", help="comma-separated substrings to skip")

    p_cap = _add_bundle_sub("capture", "write a quick-capture note into _raw/ (A3)")
    p_cap.add_argument("--title", required=True, help="note title (slug source)")
    p_cap.add_argument("--tags", help="comma-separated tags")
    p_cap.add_argument("--project", help="project context recorded in frontmatter")
    p_cap.add_argument("--note", help="finding text stored in body and description")
    p_cap.add_argument("--confidence", type=float, default=0.75)
    p_cap.add_argument("--type", default="Concept", help="OKF page type (default Concept)")
    p_cap.add_argument("--source", help="explicit sources.resource value")

    p_sy = _add_bundle_sub("sync", "commit pending bundle changes as exactly one commit")
    p_sy.add_argument("--message", help="override the conventional commit message")
    p_sy.add_argument("--push", action="store_true", help="push after committing (first remote)")
    p_sy.add_argument("--quiet", action="store_true", help="suppress the result message")

    p_ss = _add_bundle_sub("sync-setup", "install the post-commit sync hook (recursion-guarded)")

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    handlers = {
        "list": _cmd_list,
        "info": _cmd_info,
        "doctor": _cmd_doctor,
        "lint": _cmd_lint,
        "trust-check": _cmd_trust_check,
        "trust-record": _cmd_trust_record,
        "cache-check": _cmd_cache_check,
        "cache-update": _cmd_cache_update,
        "cache-hash": _cmd_cache_hash,
        "batch-plan": _cmd_batch_plan,
        "capture": _cmd_capture,
        "sync": _cmd_sync,
        "sync-setup": _cmd_sync_setup,
    }
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
