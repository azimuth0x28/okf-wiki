# Session Brain

Map what you have been working on across coding-agent sessions. The clustering
is sidecar data under `~/.config/okf-wiki/session-graph/` — the bundle is never
touched.

## Ingest vs. retrieve

Three skills and the CLI overlap here, with a clean split:

- `wiki-history-ingest` (and per-agent variants) **ingests** — distils sessions
  into permanent bundle pages.
- `wiki-agent` **ingests a slice** — pulls one topic from another agent's
  history into the bundle.
- `session-brain` / `session-search` and the `sessions-*` CLI commands
  **retrieve** — build a topic graph over raw sessions and find one. They write
  the sidecar and never touch the bundle.

If you want knowledge preserved, ingest. If you want to find the session where
something happened, retrieve.

## How the clustering works

1. `sessions-build` reads Claude/Codex transcripts (full sessions plus
   history-only "thin" sessions), assigns field-weighted TF-IDF terms per
   session, and links sessions by cosine similarity.
2. Community detection groups linked sessions into clusters; each cluster gets
   a stable key from its top 8 terms, so names survive rebuilds.
3. Recency decay (90-day half-life), momentum, and dormancy stats mark hot and
   stale topics. Cross-cluster "bridge" links surface surprising connections.

## From an agent

Say **"build my session map"** (the `session-brain` skill) or run:

```bash
okf-wiki sessions-build --json          # totals, clusters, edges
okf-wiki sessions-clusters --unnamed    # clusters that need names
```

Name clusters conversationally; the agent calls `sessions-name --from -` with
`[{id, name, summary}]` JSON. Names persist across rebuilds via stable keys.

## Tuning the build

```bash
okf-wiki sessions-build --full            # ignore caches, re-read everything
okf-wiki sessions-build --mutual          # keep only mutually-similar edges
okf-wiki sessions-build --half-life 60    # faster decay for short projects
okf-wiki sessions-build --min-sim 0.15    # stricter similarity floor
okf-wiki sessions-build --skip test       # skip projects by name substring
```

## Querying

```bash
okf-wiki sessions-query "rate limiting api"     # top sessions + why they match
okf-wiki sessions-show <session-id> --pretty    # cluster + neighbors
```

Four signals rank results: similarity, cluster lift, bookmark boost, and time
decay. Sessions with only prompt history (no transcript on disk) report
`loadable: false` honestly.

## The interactive graph

`sessions-build` writes `graph.html` — a standalone, zero-CDN canvas page with
cluster cards, degree-sized nodes, dimmed dormant sessions, and click-to-focus.
Open it in any browser; no server needed.

---

Derived from Ar9av/obsidian-wiki `docs/session-brain.md` (MIT).
