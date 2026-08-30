---
name: wiki-export
description: >
  Export the bundle as a filtered, lossless OKF pack plus knowledge-graph artifacts for
  external tools. Use this skill when the user says "export bundle", "export graph",
  "export to JSON", "export to Gephi", "export to Neo4j", "export to Postgres",
  "export to SQL", "graphml", "visualize bundle", "knowledge graph export", "pack bundle",
  "portable snapshot", "share my bundle", "export to OKF", "OKF bundle", "open knowledge
  format", "public export", or wants to hand their bundle data to another tool or agent.
  The primary output is a packed bundle — the in-scope pages copied verbatim into a
  directory that still validates as OKF v0.2 (`scripts/validate.sh` exit 0) — filtered by
  project and/or visibility tags, with out-of-scope zones always excluded. Alongside it,
  the skill emits graph analysis artifacts: graph.json (NetworkX node_link format),
  graph.graphml, cypher.txt (Neo4j), postgres.sql (Postgres), and graph.html (interactive
  browser visualization). Everything lands in `_readouts/export/` (out of OKF scope) or a
  target directory outside the bundle — the conformant bundle tree is never polluted.
---

# Wiki Export — Filtered Lossless Pack + Knowledge Graph

You are exporting a compiled OKF bundle in two forms:

1. **The pack (primary deliverable)** — a filtered, lossless copy of the bundle that
   remains a **valid OKF v0.2 bundle**. The bundle is natively OKF ("format not
   platform"), so export is packing with filters, never format conversion. The pack drops
   straight into any OKF consumer, another agent, or `wiki-import` on a different bundle.
2. **Graph analysis artifacts** — a lossy projection of the same filtered page set into
   `graph.json`, `graph.graphml`, `cypher.txt` (Neo4j), `postgres.sql` (Postgres), and
   `graph.html` (interactive browser visualization) for Gephi, Neo4j, custom scripts, and
   browser visualization.

Both outputs are derived from the **same filtered page set**, so a "public export" and its
graph always agree.

## Before You Start

1. **Resolve config** — follow the Config Resolution Protocol in `okf-wiki/SKILL.md` (inline `@name` override → walk up CWD for `.env` → global config → prompt setup). This gives `OKF_BUNDLE_PATH` and optionally `OKF_WIKI_REPO`. Legacy installs migrated from the source project keep their `~/.obsidian-wiki` config directory and are honored unchanged.
2. Read `$OKF_BUNDLE_PATH/AGENTS.md` if it exists — owner conventions apply for the session.
3. Confirm the bundle has pages to export — if fewer than 5 in-scope pages exist, warn the user and stop.

## Out-of-Scope Exclusion (always on)

The machine rule from the core skill's *Out-of-Scope Convention* applies to **every** output of this skill — graph and pack alike — with no opt-out:

- **Directories with a `_` prefix**: `_raw/`, `_staging/`, `_archives/`, `_readouts/`, `_meta/`, `_cache/`.
- **Dot-files and dot-directories**: `.manifest.json`, `.manifest.lock`, `.git/`, `.obsidian/` if present.
- **Non-markdown operational files.**
- **Bookkeeping files, excluded from the graph only**: `index.md` (root and per-directory), `log.md`, `_insights.md`, `_cache/hot.md`. These are bookkeeping, not knowledge-graph pages — but `index.md` and `log.md` ARE included in the pack (they are OKF-reserved and required for validity; see Step 3.5).

`AGENTS.md` (owner conventions) is an operational file: excluded from both graph and pack.

## Project Filter (optional)

If the user's invocation includes a project name — e.g. `/wiki-export prismor`, `"export the prismor project"`, `"export project:security"` — activate **project filter mode**:

1. **Extract the project name** from the argument or phrase. Normalise: lowercase, strip the word "project".
2. Keep only pages where **either** condition holds:
   - The page path starts with `projects/<name>/` (path-based match)
   - The page's `tags` array contains `<name>` (tag-based match)
3. Drop any edge where either endpoint was excluded.
4. Note the filter in the summary: `(filtered: project:<name> — X of Y pages)`
5. Set `graph.graph.filter = "project:<name>"` in the JSON output.

If both a project filter and a visibility filter are active, apply both (project filter first, then visibility filter on the remaining set).

## Visibility Filter (optional)

By default, **all in-scope pages are exported** regardless of visibility tags. This preserves existing behavior.

If the user requests a filtered export — phrases like **"public export"**, **"user-facing export"**, **"exclude internal"**, **"no internal pages"** — activate **visibility filtered mode**:

- Build a **blocked tag set**: `{visibility/internal, visibility/pii}`
- Skip any page whose frontmatter tags contain a blocked tag when building the node list
- Skip any edge where either endpoint was excluded
- Note the filter in the summary: `(filtered: visibility/internal, visibility/pii excluded)`

Pages with no `visibility/` tag, or tagged `visibility/public`, are always included. `visibility/` tags are **system tags** — they never count toward the 5-tag limit and are listed separately in `_meta/taxonomy.md`.

## Step 1: Build the Node and Edge Lists

Glob all `.md` files in the bundle, excluding the out-of-scope zones above **and** the bookkeeping files (`index.md`, `log.md`, `_insights.md`, `_cache/hot.md`). Apply any active filters (project and/or visibility) after collecting the full file list.

For each page, extract from frontmatter:
- `id` — relative path from bundle root, without `.md` extension (e.g. `concepts/transformer-architecture`)
- `label` — `title` field from frontmatter, or filename if missing
- `type` — the frontmatter `type` value (TitleCase: `Concept`, `Entity`, `Skill`, `Reference`, `Synthesis`, `Project`, `Journal` — canonical frontmatter reference: `okf-wiki/SKILL.md` §Schema); fall back to the TitleCase of the directory prefix if missing
- `status` — frontmatter `status` value (`draft`/`stable`/`deprecated`), if present
- `tags` — array from frontmatter tags field
- `description` — frontmatter `description` field if present

This is your **node list**.

For each page, Grep the body for markdown links — the pattern `\]\(([^)]+\.md)\)` captures every internal link target; the display text is the bracketed span immediately before each match:
- Before resolving, strip an optional `"title"` suffix and any surrounding `<>` from the captured target, and strip a `#fragment` before path resolution
- Skip image embeds (a `!` immediately before the `[`), external `http(s)://` targets, and non-`.md` targets
- Resolve each target path **relative to the source page's directory** (`normpath(join(dirname(page_path), target))`); a leading `/` resolves from the bundle root (the OKF bundle-relative option)
- The resolved bundle-relative path without `.md` is the node id
- Skip links that point outside the node list — a missing target is a legal OKF forward-reference, but it yields no edge
- Each resolved link becomes an edge: `{source: page_id, target: linked_id, relation: "related_to", confidence: 1.0}`
- If the line containing the link ends with a provenance marker, override confidence: `^[inferred]` → `confidence: 0.5`; `^[ambiguous]` → `confidence: 0.5` **and** `ambiguous: true`. `^[extracted]` and no marker both mean `confidence: 1.0`

**Typed edge enrichment:** After building the body-link edge list, read each page's `relationships:` frontmatter block (OKF §4.1 extension). For each `{target, type}` entry:
- The `target` value is a file-relative path such as `./references/okf-spec.md` (or bundle-relative `/concepts/foo.md`). Resolve it the same way as body links to get the node id.
- Skip entries whose resolved target is not in the node list (broken link)
- If an edge for this `(source, target)` pair already exists, override its `relation` field with the typed value (e.g., `"contradicts"`) and set `typed: true`
- If no edge exists yet for this pair, add one: `{source: page_id, target: target_id, relation: <type>, confidence: 1.0, typed: true}`

This means `relation: "related_to"` is the default for plain untyped body links; a `relationships:` entry promotes it to a named semantic type from the allowlist (`extends`, `implements`, `contradicts`, `derived_from`, `uses`, `replaces`, `related_to`). Edges that originated from both a body link and a `relationships:` entry keep a single record — the typed version wins.

This is your **edge list**.

## Step 2: Assign Community IDs

Group pages into communities by tag clustering:
- Pages sharing the same dominant tag belong to the same community
- Dominant tag = the first tag in the page's frontmatter tags array
- Pages with no tags get community id `null`
- Number communities starting from 0, ordered by size descending (largest community = 0); ties broken alphabetically by dominant tag

This enables community-based coloring in the HTML visualization and tools like Gephi.

## Step 3: Write the Graph Artifacts

Create the output directory — default `_readouts/export/<UTC-timestamp>/graph/` inside the bundle (the `_readouts/` zone is out of OKF conformance scope, so the conformant tree stays untouched), or a user-specified directory **outside** the bundle. Never write artifacts into the category directories or the bundle root. Write all five files:

---

### 3a. `graph.json`

NetworkX node_link format — standard for graph tools and scripts:

```json
{
  "directed": false,
  "multigraph": false,
  "graph": {
    "exported_at": "<ISO timestamp>",
    "bundle": "<OKF_BUNDLE_PATH>",
    "bundle_id": "<BUNDLE_ID>",
    "total_nodes": N,
    "total_edges": M,
    "filter": "project:<name>"
  },
  "nodes": [
    {
      "id": "concepts/transformer-architecture",
      "label": "Transformer Architecture",
      "type": "Concept",
      "status": "draft",
      "tags": ["ml", "architecture"],
      "description": "The attention-based architecture introduced in Attention Is All You Need.",
      "community": 0
    }
  ],
  "links": [
    {
      "source": "concepts/transformer-architecture",
      "target": "entities/ashish-vaswani",
      "relation": "related_to",
      "confidence": 1.0
    },
    {
      "source": "concepts/transformer-architecture",
      "target": "concepts/lstm",
      "relation": "contradicts",
      "confidence": 1.0,
      "typed": true
    },
    {
      "source": "concepts/lstm",
      "target": "concepts/transformer-architecture",
      "relation": "related_to",
      "confidence": 0.5,
      "ambiguous": true
    }
  ]
}
```

Omit the `graph.filter` key when no filter is active. `typed: true` appears only on edges promoted by a `relationships:` entry; `ambiguous: true` only on edges marked `^[ambiguous]`.

**NetworkX availability.** Producing this file needs only the Python standard library (glob, string parsing, `json`) — the agent writes the node_link JSON by hand. NetworkX is required only to *load* it (`networkx.read_json.node_link_graph`); if python3 NetworkX is unavailable on the consuming side, any JSON reader can reconstruct the adjacency from `nodes` + `links` in a few lines, so nothing in this skill depends on installing it.

---

### 3b. `graph.graphml`

GraphML XML format — loadable in Gephi, yEd, and Cytoscape:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<graphml xmlns="http://graphml.graphdrawing.org/graphml">
  <key id="label" for="node" attr.name="label" attr.type="string"/>
  <key id="type" for="node" attr.name="type" attr.type="string"/>
  <key id="tags" for="node" attr.name="tags" attr.type="string"/>
  <key id="status" for="node" attr.name="status" attr.type="string"/>
  <key id="community" for="node" attr.name="community" attr.type="int"/>
  <key id="relation" for="edge" attr.name="relation" attr.type="string"/>
  <key id="edgetype" for="edge" attr.name="type" attr.type="string"/>
  <key id="confidence" for="edge" attr.name="confidence" attr.type="double"/>
  <key id="ambiguous" for="edge" attr.name="ambiguous" attr.type="boolean"/>
  <graph id="bundle" edgedefault="undirected">
    <node id="concepts/transformer-architecture">
      <data key="label">Transformer Architecture</data>
      <data key="type">Concept</data>
      <data key="tags">ml, architecture</data>
      <data key="status">draft</data>
      <data key="community">0</data>
    </node>
    <!-- Untyped body link — no <data key="edgetype"> element -->
    <edge source="concepts/transformer-architecture" target="entities/ashish-vaswani">
      <data key="relation">related_to</data>
      <data key="confidence">1.0</data>
    </edge>
    <!-- Typed edge from relationships: block -->
    <edge source="concepts/transformer-architecture" target="concepts/lstm">
      <data key="relation">contradicts</data>
      <data key="edgetype">contradicts</data>
      <data key="confidence">1.0</data>
    </edge>
  </graph>
</graphml>
```

Write one `<node>` per page and one `<edge>` per link. The node `type` key carries the TitleCase page type; the edge key is named `edgetype` to avoid colliding with it in tools that flatten key ids. For typed edges (those where `typed: true` in the edge list), emit both `<data key="relation">` with the semantic type value **and** `<data key="edgetype">` with the same value — this keeps `relation` readable for tools that already consume it while letting type-aware tools filter on the dedicated key. Untyped `related_to` edges omit the `<data key="edgetype">` element entirely.

---

### 3c. `cypher.txt`

Neo4j Cypher `MERGE` statements — paste into Neo4j Browser or run with `cypher-shell`:

```cypher
// Bundle knowledge graph export — <TIMESTAMP>
// Load with: cypher-shell -u neo4j -p password < cypher.txt

// Nodes
MERGE (n:Page {id: "concepts/transformer-architecture"}) SET n.label = "Transformer Architecture", n.type = "Concept", n.status = "draft", n.tags = ["ml","architecture"], n.community = 0;
MERGE (n:Page {id: "entities/ashish-vaswani"}) SET n.label = "Ashish Vaswani", n.type = "Entity", n.status = "draft", n.tags = ["person","ml"], n.community = 0;
MERGE (n:Page {id: "concepts/lstm"}) SET n.label = "LSTM", n.type = "Concept", n.status = "draft", n.tags = ["ml","rnn"], n.community = 0;

// Relationships
// Untyped body links use [:RELATED_TO]
MATCH (a:Page {id: "concepts/transformer-architecture"}), (b:Page {id: "entities/ashish-vaswani"}) MERGE (a)-[r:RELATED_TO]->(b) SET r.relation = "related_to", r.confidence = 1.0;
// Typed edges use the relationship type as the label (UPPERCASE)
MATCH (a:Page {id: "concepts/transformer-architecture"}), (b:Page {id: "concepts/lstm"}) MERGE (a)-[r:CONTRADICTS]->(b) SET r.relation = "contradicts", r.confidence = 1.0;
// Ambiguous edges carry the flag
MATCH (a:Page {id: "concepts/lstm"}), (b:Page {id: "concepts/transformer-architecture"}) MERGE (a)-[r:RELATED_TO]->(b) SET r.relation = "related_to", r.confidence = 0.5, r.ambiguous = true;
```

Write one `MERGE` node statement per page, then one `MATCH`/`MERGE` relationship statement per edge — merge on the relationship **type only** and set properties afterwards (`SET r.relation = ..., r.confidence = ...`) so re-runs update existing edges instead of creating duplicates. For typed edges, use the `relation` value uppercased as the Cypher relationship label (e.g., `contradicts` → `[:CONTRADICTS]`, `derived_from` → `[:DERIVED_FROM]`). Untyped body links always use `[:RELATED_TO]`. Add the `ambiguous: true` property only on edges flagged ambiguous.

---

### 3d. `postgres.sql`

Plain SQL — loadable into any Postgres database (local, Supabase, RDS, Neon, …) with `psql -f postgres.sql` or a migration runner. Two tables: `bundle_pages` (nodes) and `bundle_edges` (links), with `ON CONFLICT` upserts so re-running the export is safe and idempotent, mirroring the `MERGE` semantics of `cypher.txt`.

```sql
-- Bundle knowledge graph export — <TIMESTAMP>
-- Load with: psql -d yourdb -f postgres.sql

CREATE TABLE IF NOT EXISTS bundle_pages (
  id          TEXT PRIMARY KEY,
  label       TEXT NOT NULL,
  type        TEXT,
  tags        JSONB NOT NULL DEFAULT '[]'::jsonb,
  description TEXT,
  status      TEXT,
  community   INT
);

CREATE TABLE IF NOT EXISTS bundle_edges (
  source     TEXT NOT NULL REFERENCES bundle_pages(id) ON DELETE CASCADE,
  target     TEXT NOT NULL REFERENCES bundle_pages(id) ON DELETE CASCADE,
  relation   TEXT NOT NULL DEFAULT 'related_to',
  confidence DOUBLE PRECISION NOT NULL DEFAULT 1.0,
  ambiguous  BOOLEAN NOT NULL DEFAULT false,
  typed      BOOLEAN NOT NULL DEFAULT false,
  PRIMARY KEY (source, target, relation)
);

CREATE INDEX IF NOT EXISTS bundle_edges_source_idx ON bundle_edges(source);
CREATE INDEX IF NOT EXISTS bundle_edges_target_idx ON bundle_edges(target);

-- Nodes
INSERT INTO bundle_pages (id, label, type, tags, description, status, community)
VALUES ('concepts/transformer-architecture', 'Transformer Architecture', 'Concept', '["ml","architecture"]'::jsonb, 'The attention-based architecture introduced in Attention Is All You Need.', 'draft', 0)
ON CONFLICT (id) DO UPDATE SET
  label = EXCLUDED.label, type = EXCLUDED.type, tags = EXCLUDED.tags,
  description = EXCLUDED.description, status = EXCLUDED.status, community = EXCLUDED.community;

-- Edges
-- Untyped body link
INSERT INTO bundle_edges (source, target, relation, confidence, ambiguous, typed)
VALUES ('concepts/transformer-architecture', 'entities/ashish-vaswani', 'related_to', 1.0, false, false)
ON CONFLICT (source, target, relation) DO UPDATE SET confidence = EXCLUDED.confidence, ambiguous = EXCLUDED.ambiguous, typed = EXCLUDED.typed;

-- Typed edge from relationships: block
INSERT INTO bundle_edges (source, target, relation, confidence, ambiguous, typed)
VALUES ('concepts/transformer-architecture', 'concepts/lstm', 'contradicts', 1.0, false, true)
ON CONFLICT (source, target, relation) DO UPDATE SET confidence = EXCLUDED.confidence, ambiguous = EXCLUDED.ambiguous, typed = EXCLUDED.typed;
```

Write one `INSERT ... ON CONFLICT (id) DO UPDATE` statement per page (values escaped: single quotes doubled, `tags` serialized as a JSON array literal cast to `jsonb`), then one `INSERT ... ON CONFLICT (source, target, relation) DO UPDATE` per edge. `relation` stays lowercase since it's a plain column value, directly filterable with `WHERE relation = 'contradicts'`. `typed` is `true` only for edges promoted by a `relationships:` frontmatter entry; plain body links stay `false`. `confidence` is numeric: `1.0` extracted, `0.5` inferred or ambiguous.

Do not deduplicate synthetic multi-edges (same source/target holding both a `related_to` and a typed relation): the composite primary key `(source, target, relation)` keeps them as distinct rows; the typed version wins at query time (`SELECT ... WHERE source=$1 AND target=$2 ORDER BY typed DESC LIMIT 1`).

---

### 3e. `graph.html`

A self-contained interactive visualization using the vis.js CDN (no local dependencies). The user opens this file in any browser — no server needed.

Build the HTML file by:

1. Generating a JSON array of node objects for vis.js:
```js
{id: "concepts/transformer-architecture", label: "Transformer Architecture", color: {background: "#4E79A7"}, size: <degree * 3 + 8>, title: "Concept | #ml #architecture", community: 0}
```
- Color by community (cycle through: `#4E79A7`, `#F28E2B`, `#E15759`, `#76B7B2`, `#59A14F`, `#EDC948`, `#B07AA1`, `#FF9DA7`, `#9C755F`, `#BAB0AC`)
- Size by degree (incoming + outgoing link count): `size = degree * 3 + 8`, capped at 60
- `title` = tooltip text shown on hover: type, tags, description (if available)

2. Generating a JSON array of edge objects for vis.js:
```js
// Untyped body link
{from: "concepts/transformer-architecture", to: "entities/ashish-vaswani", dashes: false, width: 1, color: {color: "#666", opacity: 0.6}, title: "related_to"}
// Typed edge
{from: "concepts/transformer-architecture", to: "concepts/lstm", dashes: false, width: 2, color: {color: "#E15759", opacity: 0.8}, label: "contradicts", font: {size: 9, color: "#ccc"}, title: "contradicts"}
```
- `dashes: true` for edges with `confidence: 0.5` from an `^[inferred]` marker
- `dashes: [4,8]` for edges flagged `ambiguous` (`^[ambiguous]`)
- **Typed edges** (`typed: true`): set `width: 2`, add a `label` field showing the type, and apply a type-specific color:

| Type | Edge color |
|---|---|
| `extends` | `#59A14F` (green) |
| `implements` | `#4E79A7` (blue) |
| `contradicts` | `#E15759` (red) |
| `derived_from` | `#F28E2B` (orange) |
| `uses` | `#76B7B2` (teal) |
| `replaces` | `#B07AA1` (purple) |
| `related_to` | `#BAB0AC` (grey — same as untyped) |

Untyped `related_to` edges keep the `#666` grey color and no label.

3. Writing the full HTML file:

```html
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Bundle Knowledge Graph</title>
<script src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { background: #0f0f1a; color: #e0e0e0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; display: flex; height: 100vh; }
  #graph { flex: 1; }
  #sidebar { width: 260px; background: #1a1a2e; border-left: 1px solid #2a2a4e; padding: 14px; overflow-y: auto; font-size: 13px; }
  #sidebar h3 { color: #aaa; font-size: 11px; text-transform: uppercase; letter-spacing: 0.05em; margin: 0 0 10px; }
  #info { margin-bottom: 16px; line-height: 1.6; color: #ccc; }
  .legend-item { display: flex; align-items: center; gap: 8px; padding: 3px 0; font-size: 12px; }
  .dot { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }
  #stats { margin-top: 16px; color: #555; font-size: 11px; }
</style>
</head>
<body>
<div id="graph"></div>
<div id="sidebar">
  <h3>Bundle Knowledge Graph</h3>
  <div id="info">Click a node to see details.</div>
  <h3 style="margin-top:12px">Communities</h3>
  <div id="legend"><!-- populated by JS --></div>
  <div id="stats"><!-- populated by JS --></div>
</div>
<script>
const NODES_DATA = /* NODES_JSON */;
const EDGES_DATA = /* EDGES_JSON */;
const COMMUNITY_COLORS = ["#4E79A7","#F28E2B","#E15759","#76B7B2","#59A14F","#EDC948","#B07AA1","#FF9DA7","#9C755F","#BAB0AC"];

const nodes = new vis.DataSet(NODES_DATA);
const edges = new vis.DataSet(EDGES_DATA);
const network = new vis.Network(document.getElementById('graph'), {nodes, edges}, {
  physics: { solver: 'forceAtlas2Based', forceAtlas2Based: { gravitationalConstant: -60, springLength: 120 }, stabilization: { iterations: 200 } },
  interaction: { hover: true, tooltipDelay: 100 },
  nodes: { shape: 'dot', borderWidth: 1.5 },
  edges: { smooth: { type: 'continuous' }, arrows: { to: { enabled: true, scaleFactor: 0.4 } } }
});
network.once('stabilizationIterationsDone', () => network.setOptions({ physics: { enabled: false } }));

network.on('click', ({nodes: sel}) => {
  if (!sel.length) return;
  const n = NODES_DATA.find(x => x.id === sel[0]);
  if (!n) return;
  document.getElementById('info').innerHTML = `<b>${n.label}</b><br>Type: ${n.type||'—'}<br>Tags: ${n.tags||'—'}<br>${n.description ? '<br>'+n.description : ''}`;
});

// Build legend
const communities = {};
NODES_DATA.forEach(n => { if (n.community != null) communities[n.community] = (communities[n.community]||0)+1; });
const leg = document.getElementById('legend');
Object.entries(communities).sort((a,b)=>b[1]-a[1]).forEach(([cid, count]) => {
  const color = COMMUNITY_COLORS[cid % COMMUNITY_COLORS.length];
  leg.innerHTML += `<div class="legend-item"><div class="dot" style="background:${color}"></div>Community ${cid} (${count})</div>`;
});
document.getElementById('stats').textContent = `${NODES_DATA.length} pages · ${EDGES_DATA.length} links`;
</script>
</body>
</html>
```

Replace `/* NODES_JSON */` and `/* EDGES_JSON */` with the actual JSON arrays you generated in step 1.

---

## Step 3.5: Filtered Lossless Pack (primary deliverable)

The five graph files are a *lossy* projection (graph skeleton only). The **pack** is the export proper: a filtered copy of the bundle that **remains a valid OKF v0.2 bundle** — full page bodies, full frontmatter, extension fields intact. Because the bundle is natively OKF ("format not platform"), packing is a filtered copy with zero conversion: the result drops straight into MkDocs, Notion, Hugo, GitHub's renderer, any [Open Knowledge Format](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md) consumer, or `wiki-import` on another bundle.

### Destination

- **Default:** `$OKF_BUNDLE_PATH/_readouts/export/<UTC-timestamp>/bundle/` — inside the bundle directory but inside the out-of-scope `_readouts/` zone, so the conformant tree is never polluted.
- **Named target:** if the user gives a directory (e.g. "export to ~/shared/bundle"), use it — it must lie **outside** the bundle.
- Never write the pack or any graph artifact into the conformant tree (category directories or bundle root).

### What gets copied

Copy the in-scope page set (out-of-scope exclusion + active filters applied), preserving relative paths:

1. **One file per in-scope page**, at its exact bundle-relative path — frontmatter and body copied verbatim. The bundle is natively OKF v0.2, so pages need zero transformation.
2. **Root `index.md`** and **`log.md`** — OKF-reserved files; root `index.md` carries `okf_version` and is what `wiki-import` uses to detect the pack.
3. **Per-directory `index.md`** files — copied with their pages; when all pages in a directory are filtered out, drop that directory and its `index.md` from the pack.

Excluded always (the out-of-scope machine rule): `_`-prefixed directories (`_raw/`, `_staging/`, `_archives/`, `_readouts/`, `_meta/`, `_cache/`), `_insights.md`, dot-files (`.manifest.json`, `.manifest.lock`), and `AGENTS.md` (owner-operational conventions — knowledge travels lossless without it; copy it manually if the recipient is your own future session).

### Link handling

- **No filters active** → straight copy; every link already points at an in-scope file. Zero rewriting.
- **A filter is active** → any markdown link (page body, `index.md`, or `log.md` line) whose target page was filtered out degrades to **plain text**: keep the display text, drop the link syntax. Do not emit a path pointing into filtered-out content. Additionally, when the **visibility filter** is active, redact plain-text mentions of filtered-out page titles from `log.md` entries — a public export must not leak internal/pii page names through the log; alternatively offer to omit `log.md` from the pack entirely (the bundle validates without it).
- **Broken links to nowhere** (target exists in no scope) stay as links — OKF treats them as legal forward-references, and the pack must not silently delete the user's forward-references.

### Validation gate (mandatory)

After writing the pack, run the deterministic validator:

```bash
bash scripts/validate.sh <packed-dir>
```

Resolve `scripts/` from `OKF_WIKI_REPO` if the config sets it; otherwise use the okf-wiki repo checkout this skill lives in. **The pack must exit 0** (warnings are acceptable; errors are not). If it exits 1, a rewrite broke conformance — fix the offending file and re-run. Never deliver a failing pack.

### Archive option

When the user wants a single file ("tarball", "zip it", "single-file export"), tar the validated directory:

```bash
tar -czf okf-bundle-<timestamp>.tar.gz -C <export-dir> bundle
```

The archive contents are the same validated directory — the tar is transport packaging, one more format on top of the same lossless copy.

---

## Step 4: Print Summary

```
Bundle export complete → _readouts/export/<timestamp>/
  bundle/       — filtered lossless OKF v0.2 pack (N pages; validate.sh exit 0)
  graph/graph.json    — N nodes, M edges (NetworkX node_link format)
  graph/graph.graphml — N nodes, M edges (Gephi / yEd / Cytoscape)
  graph/cypher.txt    — N MERGE nodes + M MERGE relationships (Neo4j)
  graph/postgres.sql  — N upsert rows (bundle_pages) + M upsert rows (bundle_edges) (any Postgres)
  graph/graph.html    — interactive browser visualization (open in any browser)
```

Append filter notes when active:
```
  (filtered: project:prismor — 19 of 67 pages)
  (filtered: X of Y pages excluded — visibility/internal, visibility/pii)
```
Only include lines for filters that were actually applied. If the user asked for graphs only or pack only, list only what was produced.

## Notes

- **The pack is the lossless format** — it is the bundle itself, filtered. `graph.json` reconstructs only a skeleton; the pack preserves full page bodies, frontmatter, and extension fields. Use the pack for bundle-to-bundle transfer (hand it to `wiki-import`) and external OKF consumers (MkDocs, Notion, Hugo, GitHub); use the graph files for analysis tools (Gephi, Neo4j)
- **Re-running is safe** — each run writes a fresh timestamped directory under `_readouts/export/`; old exports are disposable operational artifacts and can be deleted freely
- **Broken links are forward-references** — only edges to pages that exist in the filtered page set become graph edges; in the pack, links to filtered-out pages degrade to plain text while links to not-yet-written pages stay intact
- **Out-of-scope zones never leak** — `_`-prefixed directories, dot-files, and bookkeeping are excluded from the graph and the pack by the same machine rule `scripts/validate.sh` applies
- **`graph.json` is the primary graph format** — the others are derived from it. If a future tool supports graph queries natively, point it at `graph.json`
- **NetworkX is optional** — the node_link JSON is produced with stdlib tooling only; NetworkX (or a small stdlib loader) is needed only on the consumer side to rehydrate the graph object

---

Derived from Ar9av/obsidian-wiki wiki-export skill (MIT).
