"""Graph export: 5 deterministic artifacts from an OKF v0.2 bundle.

Ports the T-3.6 wiki-export generator. Stdlib-only core: PyYAML is used when
importable, otherwise the lenient line-based frontmatter fallback (handles
unquoted scalars containing ': ').
"""

import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from xml.sax.saxutils import escape, quoteattr

try:
    import yaml as _yaml
except ImportError:  # pragma: no cover - yaml optional in core
    _yaml = None

BOOKKEEPING = {"index.md", "log.md", "_insights.md"}
LINK_RE = re.compile(r"\]\(([^)]+\.md)\)")
FENCE_RE = re.compile(r"```.*?```", re.S)
MARKER_RE = re.compile(r"\^\[(inferred|ambiguous|extracted)\]\s*$")
COMMUNITY_COLORS = [
    "#4E79A7", "#F28E2B", "#E15759", "#76B7B2", "#59A14F",
    "#EDC948", "#B07AA1", "#FF9DA7", "#9C755F", "#BAB0AC",
]
TYPE_EDGE_COLORS = {
    "extends": "#59A14F", "implements": "#4E79A7", "contradicts": "#E15759",
    "derived_from": "#F28E2B", "uses": "#76B7B2", "replaces": "#B07AA1",
    "related_to": "#BAB0AC",
}
CANONICAL_NODE_KEYS = {"title", "type", "tags", "status", "description", "community"}


def _coerce_scalar(s: str) -> Any:
    s = s.strip()
    if len(s) >= 2 and s[0] == s[-1] and s[0] in ('"', "'"):
        return s[1:-1]
    if s == "[]":
        return []
    if s == "{}":
        return {}
    if re.fullmatch(r"-?\d+", s):
        return int(s)
    if re.fullmatch(r"-?\d+\.\d+", s):
        return float(s)
    return s


def _lenient_frontmatter(fm_text: str) -> Dict[str, Any]:
    fm: Dict[str, Any] = {}
    current_key = None
    current_list: Optional[list] = None
    current_item: Optional[dict] = None
    for raw in fm_text.splitlines():
        if not raw.strip() or raw.strip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        line = raw.strip()
        top = indent == 0
        list_item = line.startswith("- ")
        if top:
            current_list = current_item = None
            m = re.match(r"([\w][\w_-]*)\s*:\s*(.*)$", line)
            if not m:
                continue
            key, val = m.group(1), m.group(2)
            if val == "":
                current_key = key
                fm.setdefault(key, None)
            else:
                fm[key] = _coerce_scalar(val)
                current_key = None
        elif list_item and current_key:
            if current_list is None:
                current_list = fm[current_key] = []
            current_item = None
            item = line[2:].strip()
            m = re.match(r"([\w][\w_-]*)\s*:\s*(.*)$", item)
            if m:
                d = {m.group(1): _coerce_scalar(m.group(2))}
                current_list.append(d)
                current_item = d
            else:
                current_list.append(_coerce_scalar(item))
        elif current_item is not None and indent >= 4:
            m = re.match(r"([\w][\w_-]*)\s*:\s*(.*)$", line)
            if m:
                current_item[m.group(1)] = _coerce_scalar(m.group(2))
        elif current_key is not None and indent >= 2:
            if not isinstance(fm[current_key], dict):
                fm[current_key] = {}
            m = re.match(r"([\w][\w_-]*)\s*:\s*(.*)$", line)
            if m:
                fm[current_key][m.group(1)] = _coerce_scalar(m.group(2))
    return fm


def _jsonable(v: Any) -> Any:
    import datetime

    if isinstance(v, (datetime.date, datetime.datetime)):
        return v.isoformat()
    if isinstance(v, dict):
        return {k: _jsonable(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [_jsonable(x) for x in v]
    return v


def split_frontmatter(text: str) -> Tuple[Optional[Dict[str, Any]], str]:
    if text.startswith("\ufeff"):
        text = text.lstrip("\ufeff")
    if not text.lstrip().startswith("---"):
        return None, text
    lines = text.splitlines()
    start = 0
    while start < len(lines) and lines[start].strip() == "":
        start += 1
    if start >= len(lines) or lines[start].strip() != "---":
        return None, text
    end = None
    for i in range(start + 1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
    if end is None:
        return None, text
    fm_text = "\n".join(lines[start + 1 : end])
    body = "\n".join(lines[end + 1 :])
    fm = None
    if _yaml is not None:
        try:
            fm = _yaml.safe_load(fm_text)
        except _yaml.YAMLError:
            fm = None
    if not isinstance(fm, dict):
        fm = _lenient_frontmatter(fm_text)
    return _jsonable(fm), body


def resolve_target(page_rel: str, target: str) -> Optional[str]:
    t = target.strip()
    if t.startswith("<") and t.endswith(">"):
        t = t[1:-1].strip()
    m = re.match(r'^(\S.*?)(?:\s+"[^"]*")?$', t)
    if m:
        t = m.group(1).strip()
    if t.startswith("<") and t.endswith(">"):
        t = t[1:-1].strip()
    if "://" in t or t.startswith("mailto:"):
        return None
    t = t.split("#", 1)[0]
    if not t.lower().endswith(".md"):
        return None
    if t.startswith("/"):
        resolved = os.path.normpath(t.lstrip("/"))
    else:
        resolved = os.path.normpath(os.path.join(os.path.dirname(page_rel), t))
    return resolved[: -len(".md")]


def line_marker(body: str, char_pos: int) -> Optional[str]:
    line_start = body.rfind("\n", 0, char_pos) + 1
    line_end = body.find("\n", char_pos)
    if line_end == -1:
        line_end = len(body)
    line = body[line_start:line_end]
    m = MARKER_RE.search(line.rstrip())
    return m.group(1) if m else None


def collect_pages(bundle: Path) -> Dict[str, Dict[str, Any]]:
    from okf_wiki.lint import _in_scope

    pages: Dict[str, Dict[str, Any]] = {}
    for path in sorted(_in_scope(Path(bundle))):
        if path.name in BOOKKEEPING:
            continue
        rel = str(path.relative_to(bundle).with_suffix("")).replace(os.sep, "/")
        fm, body = split_frontmatter(path.read_text(encoding="utf-8", errors="replace"))
        fm = fm or {}
        node: Dict[str, Any] = {
            "id": rel,
            "label": fm.get("title") or path.stem,
            "type": fm.get("type") or path.parent.name.rstrip("s").capitalize(),
            "tags": list(fm.get("tags") or []),
            "community": None,
        }
        if fm.get("status"):
            node["status"] = str(fm["status"])
        if fm.get("description"):
            node["description"] = str(fm["description"])
        for k, v in fm.items():
            if k not in CANONICAL_NODE_KEYS:
                node[k] = v
        pages[rel] = {"node": node, "body": body, "path": path}
    return pages


def build_edges(pages: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    edges: Dict[Tuple[str, str], Dict[str, Any]] = {}

    def add_edge(src, dst, relation, confidence, typed=False, ambiguous=False):
        if src == dst:
            return
        key = (src, dst)
        if key in edges:
            e = edges[key]
            if typed:
                e["relation"] = relation
                e["typed"] = True
                e["confidence"] = confidence
                if ambiguous:
                    e["ambiguous"] = True
            else:
                e["confidence"] = min(e.get("confidence", 1.0), confidence)
                if ambiguous:
                    e["ambiguous"] = True
        else:
            e = {
                "source": src,
                "target": dst,
                "relation": relation,
                "confidence": confidence,
            }
            if typed:
                e["typed"] = True
            if ambiguous:
                e["ambiguous"] = True
            edges[key] = e

    for rel, page in pages.items():
        body = FENCE_RE.sub("", page["body"])
        for m in LINK_RE.finditer(body):
            bracket_start = body.rfind("[", 0, m.start())
            if bracket_start > 0 and body[bracket_start - 1] == "!":
                continue
            target_id = resolve_target(rel, m.group(1))
            if target_id is None or target_id not in pages:
                continue
            marker = line_marker(body, m.start())
            confidence = 0.5 if marker in ("inferred", "ambiguous") else 1.0
            add_edge(rel, target_id, "related_to", confidence,
                     ambiguous=(marker == "ambiguous"))

    for rel, page in pages.items():
        rels = page["node"].get("relationships")
        if not isinstance(rels, list):
            continue
        for entry in rels:
            if not isinstance(entry, dict):
                continue
            target = entry.get("target")
            rtype = entry.get("type")
            if not target or not rtype:
                continue
            target_id = resolve_target(rel, str(target))
            if target_id is None or target_id not in pages:
                continue
            add_edge(rel, target_id, str(rtype), 1.0, typed=True)
    return list(edges.values())


def assign_communities(pages: Dict[str, Dict[str, Any]]) -> Dict[str, int]:
    groups: Dict[str, List[str]] = {}
    for rel, page in pages.items():
        tags = page["node"]["tags"]
        if tags:
            groups.setdefault(str(tags[0]), []).append(rel)
    ordered = sorted(groups.items(), key=lambda kv: (-len(kv[1]), kv[0]))
    community_of = {}
    for cid, (tag, members) in enumerate(ordered):
        for rel in members:
            community_of[rel] = cid
    for rel, page in pages.items():
        page["node"]["community"] = community_of.get(rel)
    return community_of


def derive_exported_at(pages: Dict[str, Dict[str, Any]]) -> str:
    dates = []
    for page in pages.values():
        n = page["node"]
        v = n.get("updated")
        if isinstance(v, str) and v[:10]:
            dates.append(v[:10])
        gen = n.get("generated")
        if isinstance(gen, dict) and gen.get("at"):
            dates.append(str(gen["at"])[:10])
    return max(dates) if dates else "1970-01-01"


def _clean_edge(e: Dict[str, Any]) -> Dict[str, Any]:
    return {
        k: v
        for k, v in e.items()
        if not (k == "typed" and not e["typed"])
        and not (k == "ambiguous" and not e["ambiguous"])
    }


def build_node_link(pages, edges, exported_at: str, bundle: Path) -> Dict[str, Any]:
    nodes_out = [pages[rel]["node"] for rel in sorted(pages)]
    links_out = sorted(
        (_clean_edge(e) for e in edges),
        key=lambda e: (e["source"], e["target"], e["relation"]),
    )
    return {
        "directed": False,
        "multigraph": False,
        "graph": {
            "exported_at": exported_at,
            "bundle": str(bundle),
            "bundle_id": bundle.name,
            "total_nodes": len(nodes_out),
            "total_edges": len(links_out),
        },
        "nodes": nodes_out,
        "links": links_out,
    }


def write_graph_json(dest: Path, data: Dict[str, Any]):
    (dest / "graph.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def write_graphml(dest: Path, nodes_out, links_out):
    L = []
    L.append('<?xml version="1.0" encoding="UTF-8"?>')
    L.append('<graphml xmlns="http://graphml.graphdrawing.org/graphml">')
    for kid, attr, atype in [
        ("label", "label", "string"), ("type", "type", "string"),
        ("tags", "tags", "string"), ("status", "status", "string"),
        ("community", "community", "int"),
    ]:
        L.append(f'  <key id="{kid}" for="node" attr.name="{attr}" attr.type="{atype}"/>')
    for kid, attr, atype in [
        ("relation", "relation", "string"), ("edgetype", "type", "string"),
        ("confidence", "confidence", "double"), ("ambiguous", "ambiguous", "boolean"),
    ]:
        L.append(f'  <key id="{kid}" for="edge" attr.name="{attr}" attr.type="{atype}"/>')
    L.append('  <graph id="bundle" edgedefault="undirected">')
    for n in nodes_out:
        L.append(f"    <node id={quoteattr(n['id'])}>")
        L.append(f"      <data key=\"label\">{escape(str(n['label']))}</data>")
        L.append(f"      <data key=\"type\">{escape(str(n['type']))}</data>")
        if n["tags"]:
            L.append(f"      <data key=\"tags\">{escape(', '.join(n['tags']))}</data>")
        if n.get("status"):
            L.append(f"      <data key=\"status\">{escape(str(n['status']))}</data>")
        if n["community"] is not None:
            L.append(f"      <data key=\"community\">{n['community']}</data>")
        L.append("    </node>")
    for i, e in enumerate(links_out):
        typed = bool(e.get("typed"))
        L.append(f"    <edge id=\"e{i}\" source={quoteattr(e['source'])} target={quoteattr(e['target'])}>")
        L.append(f"      <data key=\"relation\">{escape(e['relation'])}</data>")
        if typed:
            L.append(f"      <data key=\"edgetype\">{escape(e['relation'])}</data>")
        L.append(f"      <data key=\"confidence\">{e['confidence']}</data>")
        if e.get("ambiguous"):
            L.append('      <data key="ambiguous">true</data>')
        L.append("    </edge>")
    L.append("  </graph>")
    L.append("</graphml>")
    (dest / "graph.graphml").write_text("\n".join(L) + "\n", encoding="utf-8")


def _cypher_str(s: Any) -> str:
    return '"' + str(s).replace("\\", "\\\\").replace('"', '\\"') + '"'


def write_cypher(dest: Path, nodes_out, links_out, exported_at: str):
    L = [f"// Bundle knowledge graph export — {exported_at}",
         "// Load with: cypher-shell -u neo4j -p password < cypher.txt", "", "// Nodes"]
    for n in nodes_out:
        props = [f"n.label = {_cypher_str(n['label'])}", f"n.type = {_cypher_str(n['type'])}"]
        if n.get("status"):
            props.append(f"n.status = {_cypher_str(n['status'])}")
        props.append("n.tags = [" + ",".join(_cypher_str(t) for t in n["tags"]) + "]")
        if n["community"] is not None:
            props.append(f"n.community = {n['community']}")
        L.append(f"MERGE (n:Page {{id: {_cypher_str(n['id'])}}}) SET " + ", ".join(props) + ";")
    L.extend(["", "// Relationships", "// Untyped body links use [:RELATED_TO]"])
    for e in links_out:
        label = e["relation"].upper().replace(" ", "_")
        sets = [f"r.relation = {_cypher_str(e['relation'])}", f"r.confidence = {e['confidence']}"]
        if e.get("ambiguous"):
            sets.append("r.ambiguous = true")
        L.append(
            f"MATCH (a:Page {{id: {_cypher_str(e['source'])}}}), "
            f"(b:Page {{id: {_cypher_str(e['target'])}}}) "
            f"MERGE (a)-[r:{label}]->(b) SET " + ", ".join(sets) + ";"
        )
    (dest / "cypher.txt").write_text("\n".join(L) + "\n", encoding="utf-8")


def _sql_str(v: Any) -> str:
    if v is None:
        return "NULL"
    return "'" + str(v).replace("'", "''") + "'"


def write_postgres(dest: Path, nodes_out, links_out, exported_at: str):
    L = [f"-- Bundle knowledge graph export — {exported_at}",
         "-- Load with: psql -d yourdb -f postgres.sql", ""]
    L.append("""CREATE TABLE IF NOT EXISTS bundle_pages (
  id          TEXT PRIMARY KEY,
  label       TEXT NOT NULL,
  type        TEXT,
  tags        JSONB NOT NULL DEFAULT '[]'::jsonb,
  description TEXT,
  status      TEXT,
  community   INT
);""")
    L.append("")
    L.append("""CREATE TABLE IF NOT EXISTS bundle_edges (
  source     TEXT NOT NULL REFERENCES bundle_pages(id) ON DELETE CASCADE,
  target     TEXT NOT NULL REFERENCES bundle_pages(id) ON DELETE CASCADE,
  relation   TEXT NOT NULL DEFAULT 'related_to',
  confidence DOUBLE PRECISION NOT NULL DEFAULT 1.0,
  ambiguous  BOOLEAN NOT NULL DEFAULT false,
  typed      BOOLEAN NOT NULL DEFAULT false,
  PRIMARY KEY (source, target, relation)
);""")
    L.extend(["", "CREATE INDEX IF NOT EXISTS bundle_edges_source_idx ON bundle_edges(source);",
              "CREATE INDEX IF NOT EXISTS bundle_edges_target_idx ON bundle_edges(target);", "",
              "-- Nodes"])
    for n in nodes_out:
        tags_json = json.dumps(n["tags"], ensure_ascii=False).replace("'", "''")
        L.append(
            f"INSERT INTO bundle_pages (id, label, type, tags, description, status, community)\n"
            f"VALUES ({_sql_str(n['id'])}, {_sql_str(n['label'])}, {_sql_str(n['type'])}, "
            f"'{tags_json}'::jsonb, {_sql_str(n.get('description'))}, {_sql_str(n.get('status'))}, "
            f"{'NULL' if n['community'] is None else n['community']})\n"
            f"ON CONFLICT (id) DO UPDATE SET\n"
            f"  label = EXCLUDED.label, type = EXCLUDED.type, tags = EXCLUDED.tags,\n"
            f"  description = EXCLUDED.description, status = EXCLUDED.status, community = EXCLUDED.community;"
        )
    L.extend(["", "-- Edges"])
    for e in links_out:
        amb = "true" if e.get("ambiguous") else "false"
        typed = "true" if e.get("typed") else "false"
        L.append(
            f"INSERT INTO bundle_edges (source, target, relation, confidence, ambiguous, typed)\n"
            f"VALUES ({_sql_str(e['source'])}, {_sql_str(e['target'])}, {_sql_str(e['relation'])}, "
            f"{e['confidence']}, {amb}, {typed})\n"
            f"ON CONFLICT (source, target, relation) DO UPDATE SET "
            f"confidence = EXCLUDED.confidence, ambiguous = EXCLUDED.ambiguous, typed = EXCLUDED.typed;"
        )
    (dest / "postgres.sql").write_text("\n".join(L) + "\n", encoding="utf-8")


_HTML_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Bundle Knowledge Graph</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { background: #0f0f1a; color: #e0e0e0; font-family: sans-serif; display: flex; height: 100vh; overflow: hidden; }
  #graph { flex: 1; position: relative; cursor: grab; }
  #tooltip { position: absolute; pointer-events: none; background: #1a1a2e; border: 1px solid #2a2a4e; color: #ccc; padding: 6px 10px; border-radius: 6px; font-size: 12px; display: none; max-width: 320px; z-index: 10; }
  #sidebar { width: 280px; background: #1a1a2e; border-left: 1px solid #2a2a4e; padding: 14px; overflow-y: auto; font-size: 13px; flex-shrink: 0; }
  #sidebar h3 { color: #aaa; font-size: 11px; text-transform: uppercase; letter-spacing: 0.05em; margin: 0 0 10px; }
  #info { margin-bottom: 16px; line-height: 1.6; color: #ccc; }
  .legend-item { display: flex; align-items: center; gap: 8px; padding: 3px 0; font-size: 12px; }
  .dot { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }
  #stats { margin-top: 16px; color: #777; font-size: 11px; }
  #search { width: 100%; padding: 6px 8px; margin-bottom: 12px; background: #0f0f1a; border: 1px solid #2a2a4e; color: #e0e0e0; border-radius: 4px; font-size: 12px; }
</style>
</head>
<body>
<div id="graph"><canvas id="canvas"></canvas><div id="tooltip"></div></div>
<div id="sidebar">
  <h3>Bundle Knowledge Graph</h3>
  <input id="search" type="text" placeholder="Filter nodes…">
  <div id="info">Click a node to see details.</div>
  <h3 style="margin-top:12px">Communities</h3>
  <div id="legend"></div>
  <div id="stats"></div>
</div>
<script>
const NODES_DATA = __NODES_JSON__;
const EDGES_DATA = __EDGES_JSON__;
const COMMUNITY_COLORS = __PALETTE__;

const degree = {};
EDGES_DATA.forEach(e => { degree[e.from] = (degree[e.from]||0)+1; degree[e.to] = (degree[e.to]||0)+1; });

const nodes = NODES_DATA.map((n, i) => ({
  ...n,
  x: 400 + Math.cos(i * 2.399) * 260,
  y: 300 + Math.sin(i * 2.399) * 220,
  vx: 0, vy: 0,
  r: Math.min(6 + (degree[n.id]||0)*1.4, 22),
  color: COMMUNITY_COLORS[(n.community ?? 0) % COMMUNITY_COLORS.length]
}));
const byId = Object.fromEntries(nodes.map(n => [n.id, n]));
const links = EDGES_DATA.map(e => ({ ...e, a: byId[e.from], b: byId[e.to] }));

const canvas = document.getElementById('canvas');
const ctx = canvas.getContext('2d');
const container = document.getElementById('graph');
let W, H, dpr;
function resize() {
  dpr = window.devicePixelRatio || 1;
  W = container.clientWidth; H = container.clientHeight;
  canvas.width = W * dpr; canvas.height = H * dpr;
  canvas.style.width = W + 'px'; canvas.style.height = H + 'px';
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
}
window.addEventListener('resize', () => { resize(); draw(); });

let alpha = 1.0;
function tick() {
  for (let i = 0; i < nodes.length; i++) {
    const a = nodes[i];
    for (let j = i+1; j < nodes.length; j++) {
      const b = nodes[j];
      let dx = b.x - a.x, dy = b.y - a.y;
      let d2 = dx*dx + dy*dy;
      if (d2 < 1) d2 = 1;
      const f = 2400 / d2;
      const d = Math.sqrt(d2);
      const fx = dx/d*f, fy = dy/d*f;
      a.vx -= fx; a.vy -= fy; b.vx += fx; b.vy += fy;
    }
  }
  links.forEach(l => {
    let dx = l.b.x - l.a.x, dy = l.b.y - l.a.y;
    const d = Math.max(Math.sqrt(dx*dx + dy*dy), 1);
    const f = (d - 130) * 0.012;
    const fx = dx/d*f, fy = dy/d*f;
    l.a.vx += fx; l.a.vy += fy; l.b.vx -= fx; l.b.vy -= fy;
  });
  nodes.forEach(n => {
    n.vx += (W/2 - n.x) * 0.003;
    n.vy += (H/2 - n.y) * 0.003;
    n.vx *= 0.85; n.vy *= 0.85;
    n.x += n.vx * alpha; n.y += n.vy * alpha;
  });
  alpha = Math.max(alpha * 0.995, 0.03);
}

let dragging = null, hovered = null, stopped = false;
function draw() {
  ctx.clearRect(0, 0, W, H);
  const visible = new Set(nodes.filter(n => !n._hidden).map(n => n.id));
  links.forEach(l => {
    if (!visible.has(l.from) || !visible.has(l.to)) return;
    ctx.beginPath();
    ctx.moveTo(l.a.x, l.a.y);
    ctx.lineTo(l.b.x, l.b.y);
    ctx.strokeStyle = l._color || '#666';
    ctx.globalAlpha = l._opacity || 0.6;
    ctx.lineWidth = l._width || 1;
    ctx.stroke();
    ctx.globalAlpha = 1;
  });
  nodes.forEach(n => {
    if (n._hidden) return;
    ctx.beginPath();
    ctx.arc(n.x, n.y, n.r, 0, 2*Math.PI);
    ctx.fillStyle = n.color;
    ctx.globalAlpha = hovered && hovered !== n ? 0.35 : 1;
    ctx.fill();
    ctx.globalAlpha = 1;
    ctx.lineWidth = 1.5;
    ctx.strokeStyle = hovered === n ? '#fff' : '#0f0f1a';
    ctx.stroke();
    if (n.r > 10 || hovered === n) {
      ctx.fillStyle = '#e0e0e0';
      ctx.font = '11px sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText(n.label.length > 28 ? n.label.slice(0,26)+'…' : n.label, n.x, n.y + n.r + 13);
    }
  });
}
resize();
for (let i = 0; i < 300; i++) tick();
alpha = 0.3;
(function loop() { if (!stopped) { tick(); draw(); } requestAnimationFrame(loop); })();

function pos(evt) {
  const r = canvas.getBoundingClientRect();
  return { x: evt.clientX - r.left, y: evt.clientY - r.top };
}
function nodeAt(p) {
  return nodes.find(n => !n._hidden && (p.x-n.x)**2 + (p.y-n.y)**2 <= (n.r+4)**2) || null;
}
canvas.addEventListener('mousemove', evt => {
  const p = pos(evt);
  if (dragging) { dragging.x = p.x; dragging.y = p.y; dragging.vx = dragging.vy = 0; draw(); return; }
  const n = nodeAt(p);
  hovered = n;
  canvas.style.cursor = n ? 'pointer' : 'grab';
  const tip = document.getElementById('tooltip');
  if (n) {
    tip.style.display = 'block';
    tip.style.left = (p.x + 14) + 'px';
    tip.style.top = (p.y + 14) + 'px';
    tip.innerHTML = `<b>${n.label}</b><br>${n.type||'—'}${n.tags ? ' · #'+n.tags.join(' #') : ''}`;
  } else tip.style.display = 'none';
  draw();
});
canvas.addEventListener('mousedown', evt => {
  const n = nodeAt(pos(evt));
  if (n) { dragging = n; stopped = true; }
});
window.addEventListener('mouseup', () => { dragging = null; });
canvas.addEventListener('click', evt => {
  const n = nodeAt(pos(evt));
  const info = document.getElementById('info');
  if (!n) { info.innerHTML = 'Click a node to see details.'; return; }
  info.innerHTML = `<b>${n.label}</b><br>Type: ${n.type||'—'}<br>Tags: ${(n.tags&&n.tags.length)?n.tags.join(', '):'—'}<br>${n.description ? '<br>'+n.description : ''}`;
});

document.getElementById('search').addEventListener('input', evt => {
  const q = evt.target.value.toLowerCase();
  nodes.forEach(n => { n._hidden = q && !(n.label||'').toLowerCase().includes(q) && !(n.id||'').toLowerCase().includes(q); });
  draw();
});

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
"""


def write_graph_html(dest: Path, nodes_out, links_out):
    vis_nodes = []
    for n in nodes_out:
        tooltip = f"{n['type']}"
        if n["tags"]:
            tooltip += " | " + " ".join("#" + t for t in n["tags"])
        vis_nodes.append({
            "id": n["id"],
            "label": n["label"],
            "type": n["type"],
            "tags": n["tags"],
            "description": n.get("description", ""),
            "community": n["community"],
            "title": tooltip,
        })
    vis_edges = []
    for e in links_out:
        typed = bool(e.get("typed"))
        amb = bool(e.get("ambiguous"))
        inf = e["confidence"] < 1.0
        edge = {
            "from": e["source"],
            "to": e["target"],
            "dashes": [4, 8] if amb else (True if inf else False),
            "width": 2 if typed else 1,
            "color": {"color": TYPE_EDGE_COLORS.get(e["relation"], "#666") if typed else "#666",
                      "opacity": 0.8 if typed else 0.6},
            "title": e["relation"],
        }
        if typed:
            edge["label"] = e["relation"]
            edge["font"] = {"size": 9, "color": "#ccc"}
        vis_edges.append(edge)

    html = _HTML_TEMPLATE
    html = html.replace("__NODES_JSON__", json.dumps(vis_nodes, ensure_ascii=False))
    html = html.replace("__EDGES_JSON__", json.dumps(vis_edges, ensure_ascii=False))
    html = html.replace("__PALETTE__", json.dumps(COMMUNITY_COLORS))
    (dest / "graph.html").write_text(html, encoding="utf-8")


def export_graph(bundle: Path, dest: Path) -> Dict[str, Any]:
    bundle = Path(bundle)
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    pages = collect_pages(bundle)
    edges = build_edges(pages)
    assign_communities(pages)
    exported_at = derive_exported_at(pages)
    data = build_node_link(pages, edges, exported_at, bundle)
    nodes_out = data["nodes"]
    links_out = data["links"]
    write_graph_json(dest, data)
    write_graphml(dest, nodes_out, links_out)
    write_cypher(dest, nodes_out, links_out, exported_at)
    write_postgres(dest, nodes_out, links_out, exported_at)
    write_graph_html(dest, nodes_out, links_out)
    names = ["graph.json", "graph.graphml", "cypher.txt", "postgres.sql", "graph.html"]
    return {
        "paths": {name: str(dest / name) for name in names},
        "node_count": len(nodes_out),
        "edge_count": len(links_out),
        "exported_at": exported_at,
    }


def graph_query(bundle: Path, tokens: List[str], graph_json: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Filter nodes by token match on label/type/tags/description."""
    bundle = Path(bundle)
    if graph_json is None:
        graph_json = bundle / "_readouts" / "graph" / "graph.json"
    if graph_json.is_file():
        data = json.loads(graph_json.read_text(encoding="utf-8"))
    else:
        pages = collect_pages(bundle)
        edges = build_edges(pages)
        assign_communities(pages)
        data = build_node_link(pages, edges, derive_exported_at(pages), bundle)
    lowered = [t.lower() for t in tokens if t.strip()]
    hits = []
    for node in data.get("nodes", []):
        haystack = " ".join([
            str(node.get("label", "")),
            str(node.get("type", "")),
            " ".join(node.get("tags") or []),
            str(node.get("description", "")),
        ]).lower()
        if all(t in haystack for t in lowered):
            hits.append(node)
    return hits
