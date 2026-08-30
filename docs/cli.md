# CLI Reference

`okf-wiki` is the deterministic counterpart to the agent skills: every
invariant operation (lint parity, capture, graph export, session clustering)
runs the same code path with or without an agent in the loop.

```bash
uv venv && uv pip install -e '.[server]' && uv run okf-wiki --help
```

All bundle commands accept the bundle path positionally or resolve it through
the [Config Resolution Protocol](./configuration.md) — including `@name`
profile overrides (`okf-wiki lint @work`). Examples below use the repo's
`tests/fixtures/mini-bundle`.

## Setup & inspection

```console
$ okf-wiki list                    # named profiles + active marker
$ okf-wiki info                    # version, config source, paths
$ okf-wiki info --name demo        # resolve the demo profile explicitly
$ okf-wiki doctor --name demo      # validate the profile's bundle
✓ config resolved: /home/evgeniy/.config/okf-wiki/config.demo (source: name)
✓ bundle path exists: /tmp/opencode/p1-bundle
✓ root index.md declares okf_version
$ echo $?
0
```

`doctor` validates config resolution, bundle existence, and the root
`index.md` `okf_version` marker; it exits `1` with ✗ lines when something is
broken. The bundle comes from config resolution (`--name`, `.env`, or the
global config) — the same way every command without an explicit path finds it.

## Querying & linting

```console
$ okf-wiki lint tests/fixtures/mini-bundle      # exit 0 — no E-errors
$ okf-wiki lint tests/fixtures/non-conformant   # exit 1 — errors printed
$ okf-wiki lint                                 # exit 2 — no bundle given
```

`lint` is the exact port of `scripts/validate.sh` (E1–E4 errors, W1/W3/W5–W7
warnings, same scope rules). The CI asserts parity between the two.

```console
$ okf-wiki query tests/fixtures/mini-bundle "okf bundle" --top 2
Query: okf bundle
Ranked pages: 7
Top pages:
  1. concepts/okf-bundle.md — OKF Bundle (score 10)
  2. references/okf-spec.md — OKF Specification (score 5)
```

`query` ranks pages by keyword hits (title ×3, tags ×2, description ×1) over
frontmatter — the cheap retrieval pass of the `wiki-query` skill — and prints
file-relative citations with excerpts.

## Context packs

```console
$ okf-wiki context-pack --topic "okf" --budget 1500 tests/fixtures/mini-bundle
# Context pack: okf
Budget: ~1500 tokens | Pages: 4 (of 4 ranked)
```

`context-pack` compiles bounded context for another agent: ranked pages,
excerpts, and a provenance line per page, hard-capped at the token budget
(~4 chars/token). Read-only; the pack is printed, never written back.

## Session brain

Build and query a topic graph over raw agent sessions. The sidecar lives in
`~/.config/okf-wiki/session-graph/` and never touches the bundle.

```console
$ okf-wiki sessions-build --claude-dir ~/.claude          # full map + graph.html
$ okf-wiki sessions-build --full --mutual --half-life 60  # tuning flags
$ okf-wiki sessions-query "rate limiting api"             # ranked + why
$ okf-wiki sessions-show <session-id> --pretty            # cluster + neighbors
$ okf-wiki sessions-clusters --unnamed                    # naming queue
$ echo '[{"id":0,"name":"Client throttling","summary":"token bucket rollout"}]' \
    | okf-wiki sessions-name --out ~/.config/okf-wiki/session-graph --from -
```

Cluster names persist across rebuilds via stable vocabulary keys.

## Capture & sync

```console
$ okf-wiki capture /path/to/bundle --title "Actor reentrancy gotcha" \
    --tags swift,actors --note "async forEach deadlocks; use a serial queue" \
    --confidence 0.75
Captured: _raw/2026-08-31-actor-reentrancy-gotcha.md
```

`capture` writes a v0.2-shaped `_raw/` page (the `wiki-capture --quick`
contract). `_raw/` is out of lint scope; `/wiki-ingest` promotes it.

```console
$ okf-wiki sync /path/to/bundle                  # exactly one conventional commit
Committed 3 file(s): wiki: sync 3 file(s)
$ okf-wiki sync /path/to/bundle --push           # + push to the first remote
$ okf-wiki sync-setup /path/to/bundle            # post-commit auto-sync hook
Installed post-commit hook: /path/to/bundle/.git/hooks/post-commit
```

## Graph export

```console
$ okf-wiki graph tests/fixtures/mini-bundle --out /tmp/graph
Graph: 8 nodes, 0 links (exported_at 2026-08-30)
  /tmp/graph/graph.json
  /tmp/graph/graph.graphml
  /tmp/graph/cypher.txt
  /tmp/graph/postgres.sql
  /tmp/graph/graph.html
$ okf-wiki graph-query tests/fixtures/mini-bundle okf     # filter nodes by tokens
```

All five formats are deterministic — repeated runs are byte-identical (the
`exported_at` timestamp is data-derived, and the HTML layout is seeded).

## Code intelligence

```console
$ okf-wiki ast-extract src/ --pretty            # structural symbols + edges
$ okf-wiki code-understand --project src/ --backend builtin --pretty
backend: builtin
focus map: 2 symbol(s)
  1. Greeter (class) greet.py:1 [ast]
  2. greeting (function) greet.py:5 [ast]
$ okf-wiki code-understand                      # auto: codegraph when indexed
```

`code-understand` ranks changed/AST-seeded symbols so an agent knows where to
look first — the engine behind the `code-understand` skill.

## Trust ledger

```console
$ okf-wiki trust-check tests/fixtures/mini-bundle/concepts/trust-lifecycle.md
rank: machine (0)
$ okf-wiki trust-record tests/fixtures/mini-bundle/concepts/trust-lifecycle.md \
    --by human:evgeniy --note "S3 parity check"
$ okf-wiki trust-check tests/fixtures/mini-bundle/concepts/trust-lifecycle.md
rank: verified (2)
```

Trust priority (verified > human > machine) is what `wiki-import` uses to
resolve merge conflicts — the CLI reads and appends the same `verified` list.

## Lower-level commands

```console
$ okf-wiki cache-check /path/to/bundle          # manifest sanity + stats recount
$ okf-wiki cache-update /path/to/bundle --dry-run   # NEW/MODIFIED delta
$ okf-wiki cache-hash /path/to/bundle           # deterministic manifest digest
$ okf-wiki batch-plan /path/to/bundle           # ordered ingest plan text
```

`cache-update` is a pure delta detector (source files vs `.manifest.json`);
persistence happens with the real flag off. Newer sources win; page lists
merge as unions.

## Memory server

```console
$ WIKI_API_KEY=change-me okf-wiki server --port 8080   # = python -m okf_wiki.server
```

`server` starts the HTTP + MCP memory front end (see
[deployment](./deployment.md)): open `/health`, bearer-guarded
`/v1/search`, `/v1/pages`, `/v1/context-pack`, and `/mcp`.

---

Derived from Ar9av/obsidian-wiki `docs/cli.md` (MIT).
