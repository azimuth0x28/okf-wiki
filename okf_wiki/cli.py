"""okf-wiki CLI entry point.

Card 01 subcommands: list / info / doctor.
Card 02 subcommands: lint / trust-check / trust-record / cache-check /
cache-update / cache-hash / batch-plan.
"""

from __future__ import annotations

import argparse
import json
import os
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


def _cmd_query(args: argparse.Namespace) -> int:
    from okf_wiki.query import query as run_query
    from okf_wiki.query import render

    try:
        bundle = _resolve_bundle(args)
    except ConfigError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    if not bundle.is_dir():
        print(f"error: not a directory: {bundle}", file=sys.stderr)
        return 1
    question = " ".join(args.question).strip()
    result = run_query(bundle, question, top=args.top)
    print(render(result))
    return 0 if result["hits"] else 1


def _cmd_context_pack(args: argparse.Namespace) -> int:
    from okf_wiki.context_pack import build_pack
    from okf_wiki.context_pack import render

    try:
        bundle = _resolve_bundle(args)
    except ConfigError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    if not bundle.is_dir():
        print(f"error: not a directory: {bundle}", file=sys.stderr)
        return 1
    pack = build_pack(bundle, args.topic, budget_tokens=args.budget)
    print(render(pack))
    return 0 if pack["pages_included"] else 1


def _cmd_graph(args: argparse.Namespace) -> int:
    from okf_wiki.graph import export_graph

    try:
        bundle = _resolve_bundle(args)
    except ConfigError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    if not bundle.is_dir():
        print(f"error: not a directory: {bundle}", file=sys.stderr)
        return 1
    dest = Path(args.out) if args.out else bundle / "_readouts" / "graph"
    result = export_graph(bundle, dest)
    print(f"Graph: {result['node_count']} nodes, {result['edge_count']} links (exported_at {result['exported_at']})")
    for name in ("graph.json", "graph.graphml", "cypher.txt", "postgres.sql", "graph.html"):
        print(f"  {result['paths'][name]}")
    return 0


def _cmd_graph_query(args: argparse.Namespace) -> int:
    from okf_wiki.graph import graph_query

    try:
        bundle = _resolve_bundle(args)
    except ConfigError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    if not bundle.is_dir():
        print(f"error: not a directory: {bundle}", file=sys.stderr)
        return 1
    tokens = args.tokens
    graph_json = Path(args.out) if args.out else None
    hits = graph_query(bundle, tokens, graph_json=graph_json)
    if not hits:
        print(f"No nodes matching all tokens: {' '.join(tokens)}")
        return 1
    print(f"Matching nodes: {len(hits)}")
    for node in hits:
        print(f"  [{node.get('type', '?')}] {node.get('id', '?')} — {node.get('label', '')}")
    return 0


_DEFAULT_SIDECAR = Path.home() / ".config" / "okf-wiki" / "session-graph"


def _sidecar_dir(args: argparse.Namespace) -> Path:
    return Path(getattr(args, "out", None) or _DEFAULT_SIDECAR).expanduser()


def _cmd_sessions_build(args: argparse.Namespace) -> int:
    from okf_wiki.sessions.graph import HALF_LIFE_DAYS_DEFAULT, build

    claude_dir = Path(args.claude_dir).expanduser()
    if not claude_dir.is_dir():
        print(f"error: not a directory: {claude_dir}", file=sys.stderr)
        return 1
    skip = [s.strip() for s in (args.skip or "").split(",") if s.strip()]
    summary = build(
        claude_dir,
        _sidecar_dir(args),
        k=args.k,
        min_sim=args.min_sim,
        mutual=args.mutual,
        half_life_days=args.half_life if args.half_life is not None else HALF_LIFE_DAYS_DEFAULT,
        full=args.full,
        skip=skip or None,
        write_html=not args.no_html,
    )
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0
    stats = summary["stats"]
    print(f"Sessions: {stats['sessions']} (full {stats['full']}, thin {stats['thin']})")
    print(f"Edges: {stats['edges']}  Clusters: {stats['clusters']}  "
          f"Unclustered: {stats['unclustered']}")
    print(f"Named: {summary['clusters'].__len__() - summary['unnamed']}/{summary['clusters'].__len__()}"
          if summary["clusters"] else "Clusters: 0")
    print(f"Sidecar: {summary['out_dir']}")
    return 0


def _cmd_sessions_query(args: argparse.Namespace) -> int:
    from okf_wiki.sessions.query import query

    question = " ".join(args.question)
    out_dir = _sidecar_dir(args)
    try:
        result = query(
            out_dir,
            question,
            top_n=args.top,
            project=args.project,
            cluster=args.cluster,
            since=args.since,
        )
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    results = result.get("candidates") or []
    if not results:
        print("No matching sessions.")
        return 1
    print(f"Question: {question}  (of {result.get('total_ranked', len(results))} ranked sessions)")
    for r in results:
        title = r.get("title") or r.get("id", "?")
        sid = r.get("session_id") or r.get("id", "?")
        print(f"  [{sid}] {title}")
        print(f"      project={r.get('project', '?')}  score={r.get('score', 0):.3f}  "
              f"loadable={r.get('loadable', '?')}")
        why = r.get("why")
        if isinstance(why, str) and why:
            print(f"      {why}")
        elif isinstance(why, list):
            for line in why[:2]:
                print(f"      {line}")
    should = result.get("should_load") or []
    if should:
        print(f"Load first: {', '.join(should[:3])}")
    return 0


def _cmd_sessions_show(args: argparse.Namespace) -> int:
    from okf_wiki.sessions.query import show

    try:
        result = show(_sidecar_dir(args), args.session_id, neighbors=args.neighbors)
    except (FileNotFoundError, KeyError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    if args.pretty:
        session = result.get("session") or {}
        title = session.get("title") or session.get("id", "?")
        print(f"Session: {session.get('id', '?')}")
        print(f"  title:   {title}")
        print(f"  project: {session.get('project', '?')}  tier={session.get('tier', '?')}  "
              f"end={session.get('end_ts', '?')}")
        cluster = result.get("cluster")
        if cluster:
            print(f"  cluster: [{cluster['id']}] {cluster.get('name') or cluster.get('label')}  "
                  f"size={cluster.get('size')}")
        else:
            print("  cluster: none")
        neighbors = result.get("neighbors") or []
        if neighbors:
            print("  neighbors:")
            for n in neighbors:
                print(f"    [{n['session_id']}] {n.get('title', '')[:70]}  "
                      f"weight={n.get('weight', 0)}  shared={n.get('shared')}")
        load = result.get("load_command") or ""
        if load:
            print(f"  load:    {load}")
        return 0
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def _cmd_sessions_clusters(args: argparse.Namespace) -> int:
    from okf_wiki.sessions.graph import load_graph

    try:
        _graph, clusters_doc = load_graph(_sidecar_dir(args))
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    clusters = clusters_doc.get("clusters") or []
    if args.unnamed:
        clusters = [c for c in clusters if not c.get("name")]
    if args.json:
        print(json.dumps({"clusters": clusters}, ensure_ascii=False, indent=2))
        return 0
    if not clusters:
        print("No clusters to show.")
        return 1
    print(f"Clusters: {len(clusters)}")
    for c in clusters:
        name = c.get("name") or c.get("label") or f"cluster-{c.get('id')}"
        print(f"  [{c.get('id')}] {name}  size={c.get('size')}  "
              f"momentum={c.get('momentum', 0):.2f}  dormant={c.get('dormant')}")
        # top_terms entries are (term, weight) pairs — weight is display noise here
        terms = ", ".join(t[0] if isinstance(t, (list, tuple)) else t
                          for t in (c.get("top_terms") or [])[:6])
        if terms:
            print(f"      terms: {terms}")
    return 0


def _cmd_sessions_name(args: argparse.Namespace) -> int:
    from okf_wiki.sessions.graph import set_cluster_names

    updates: List[dict] = []
    if args.from_file:
        if args.from_file == "-":
            raw = sys.stdin.read()
        else:
            raw = Path(args.from_file).read_text(encoding="utf-8")
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            print(f"error: invalid JSON: {exc}", file=sys.stderr)
            return 1
        if not isinstance(parsed, list):
            print("error: expected a JSON array of {id,name,summary} objects", file=sys.stderr)
            return 1
        updates = parsed
    elif args.id and args.name:
        updates = [{"id": args.id, "name": args.name, "summary": args.summary}]
    else:
        print("error: provide --from FILE (or '-' for stdin) or --id/--name",
              file=sys.stderr)
        return 1
    try:
        result = set_cluster_names(_sidecar_dir(args), updates)
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"Named {result['named']} of {result['clusters']} clusters")
    return 0


def _cmd_ast_extract(args: argparse.Namespace) -> int:
    from okf_wiki.codeintel.ast_extractor import extract

    path = Path(args.path).expanduser().resolve()
    try:
        result = extract(path)
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    if args.pretty:
        print(json.dumps(result, indent=2))
    else:
        print(json.dumps(result))
    return 0


def _cmd_code_understand(args: argparse.Namespace) -> int:
    from okf_wiki.codeintel.code_understanding import ProviderError, code_understand

    project = Path(args.project or os.getcwd())
    try:
        result = code_understand(
            project,
            # "auto" must pass through as None so CODE_UNDERSTANDING_BACKEND can win (flag > env > auto).
            backend_flag=None if args.backend == "auto" else args.backend,
            changed=args.changed,
            since=args.since,
            max_symbols=args.max_symbols,
        )
    except ProviderError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    if args.pretty:
        print(f"backend: {result['backend']}")
        print(f"project: {result['project']}")
        print(f"focus map: {len(result['focus_map'])} symbol(s)")
        for item in result["focus_map"]:
            lines = item.get("lines") or []
            span = str(lines[0]) if lines else ""
            if len(lines) > 1:
                span += f"-{lines[-1]}"
            print(
                f"  {item.get('rank', '?')}. {item['symbol']} "
                f"({item['kind']}) {item['file']}:{span} [{item.get('evidence', '')}]"
            )
        if result["warnings"]:
            print("warnings:")
            for warning in result["warnings"]:
                print(f"  - {warning}")
        else:
            print("warnings: none")
    else:
        print(json.dumps(result, indent=2))
    return 0


def _cmd_server(args: argparse.Namespace) -> int:
    import os

    import uvicorn

    from okf_wiki.server import create_app

    if args.port is not None:
        os.environ["WIKI_PORT"] = str(args.port)
    app = create_app()
    uvicorn.run(app, host=args.host or "0.0.0.0", port=int(os.environ.get("WIKI_PORT", "8080")))
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

    p_q = _add_bundle_sub("query", "rank pages for a question (index -> description -> excerpt)")
    p_q.add_argument("question", nargs="+", help="free-text question")
    p_q.add_argument("--top", type=int, default=3, help="hits to excerpt (default 3)")

    p_cp = _add_bundle_sub("context-pack", "bounded provenance-rich context pack for a topic")
    p_cp.add_argument("--topic", required=True, help="topic keywords to rank pages by")
    p_cp.add_argument("--budget", type=int, default=2000, help="token budget (default 2000)")

    p_g = _add_bundle_sub("graph", "export 5 deterministic graph artifacts")
    p_g.add_argument("--out", default=None, help="destination dir (default <bundle>/_readouts/graph)")

    p_gq = _add_bundle_sub("graph-query", "filter graph nodes by tokens")
    p_gq.add_argument("--out", default=None, help="path to an existing graph.json (default <bundle>/_readouts/graph/graph.json)")
    p_gq.add_argument("tokens", nargs="+", help="tokens AND-matched on label/type/tags/description")

    default_sidecar = str(Path.home() / ".config" / "okf-wiki" / "session-graph")

    p_sb = sub.add_parser("sessions-build", help="build the session topic graph sidecar")
    p_sb.add_argument("--claude-dir", default="~/.claude", help="agent history dir (default ~/.claude)")
    p_sb.add_argument("--out", default=default_sidecar, help="sidecar dir (default ~/.config/okf-wiki/session-graph)")
    p_sb.add_argument("--full", action="store_true", help="ignore caches, full rebuild")
    p_sb.add_argument("--mutual", action="store_true", help="keep only mutual-kNN edges")
    p_sb.add_argument("--half-life", type=float, default=None, help="recency half-life in days")
    p_sb.add_argument("--min-sim", type=float, default=0.08, help="edge similarity floor")
    p_sb.add_argument("--k", type=int, default=8, help="neighbors per node")
    p_sb.add_argument("--skip", help="comma-separated substrings to skip")
    p_sb.add_argument("--no-html", action="store_true", help="skip graph.html rendering")
    p_sb.add_argument("--json", action="store_true", help="machine-readable summary")

    p_sq = sub.add_parser("sessions-query", help="find sessions by topic in the built graph")
    p_sq.add_argument("question", nargs="+", help="free-text topic")
    p_sq.add_argument("--out", default=default_sidecar, help="sidecar dir")
    p_sq.add_argument("--project", help="filter by project")
    p_sq.add_argument("--cluster", type=int, default=None, help="filter by cluster id")
    p_sq.add_argument("--since", help="ISO date; ignore sessions older than this")
    p_sq.add_argument("--top", type=int, default=10, help="results to show")
    p_sq.add_argument("--json", action="store_true", help="machine-readable output")

    p_ssh = sub.add_parser("sessions-show", help="show one session node and its neighbors")
    p_ssh.add_argument("session_id", help="session id from the graph")
    p_ssh.add_argument("--out", default=default_sidecar, help="sidecar dir")
    p_ssh.add_argument("--neighbors", type=int, default=8, help="neighbors to list (default 8)")
    p_ssh.add_argument("--pretty", action="store_true", help="human-readable output (default: JSON)")

    p_sc = sub.add_parser("sessions-clusters", help="list clusters with terms and exemplars")
    p_sc.add_argument("--out", default=default_sidecar, help="sidecar dir")
    p_sc.add_argument("--unnamed", action="store_true", help="only clusters without a name")
    p_sc.add_argument("--json", action="store_true", help="machine-readable output")

    p_sn = sub.add_parser("sessions-name", help="apply cluster names (stdin JSON or inline)")
    p_sn.add_argument("--out", default=default_sidecar, help="sidecar dir")
    p_sn.add_argument("--from", dest="from_file", default=None,
                      help="JSON file (or '-' for stdin) with [{id,name,summary}]")
    p_sn.add_argument("--id", help="inline single-cluster id")
    p_sn.add_argument("--name", help="inline single-cluster name")
    p_sn.add_argument("--summary", help="inline single-cluster summary")

    ap = sub.add_parser(
        "ast-extract",
        help="extract code structure (classes, functions, imports) from a file or directory — no LLM, no API calls",
    )
    ap.add_argument("path", help="file or directory to extract from")
    ap.add_argument("--pretty", action="store_true", help="pretty-print JSON output")

    cdu = sub.add_parser(
        "code-understand",
        help="build a ranked code-understanding focus map for a project — CodeGraph when available, builtin AST + rg otherwise",
    )
    cdu.add_argument("--project", default=None, help="project directory (defaults to the current directory)")
    cdu.add_argument(
        "--backend",
        choices=["auto", "builtin", "codegraph"],
        default="auto",
        help="code-understanding backend (default: auto)",
    )
    cdu.add_argument(
        "--changed",
        action="append",
        default=None,
        metavar="FILE",
        help="treat FILE as a seed file (repeatable; overrides --since)",
    )
    cdu.add_argument(
        "--since",
        default=None,
        metavar="SHA",
        help="seed files changed since this git ref",
    )
    cdu.add_argument(
        "--max-symbols",
        type=int,
        default=50,
        help="cap the focus map size (default 50)",
    )
    cdu.add_argument("--pretty", action="store_true", help="human-readable summary (default: JSON)")

    srv = sub.add_parser(
        "server",
        help="run the HTTP/MCP memory server for a bundle (needs the 'server' extra)",
    )
    srv.add_argument("--host", default=None, help="bind host (default 0.0.0.0)")
    srv.add_argument("--port", type=int, default=None, help="bind port (default WIKI_PORT or 8080)")

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
        "query": _cmd_query,
        "context-pack": _cmd_context_pack,
        "graph": _cmd_graph,
        "graph-query": _cmd_graph_query,
        "sessions-build": _cmd_sessions_build,
        "sessions-query": _cmd_sessions_query,
        "sessions-show": _cmd_sessions_show,
        "sessions-clusters": _cmd_sessions_clusters,
        "sessions-name": _cmd_sessions_name,
        "ast-extract": _cmd_ast_extract,
        "code-understand": _cmd_code_understand,
        "server": _cmd_server,
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
