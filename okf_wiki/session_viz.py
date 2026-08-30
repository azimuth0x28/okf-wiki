"""Self-contained HTML visualization for the session graph.

Canvas-based rendering with zero CDN dependencies — the page works fully
offline. Layout is deterministic (golden-angle seeded positions per
cluster), so the same graph always renders identically. Consumes the
graph.json / clusters.json shapes produced by :mod:`okf_wiki.session_graph`.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

# 20 distinguishable community colors (same family as the bundle graph page).
_PALETTE = [
    "#4e79a7", "#f28e2b", "#59a14f", "#e15759", "#76b7b2",
    "#af7aa1", "#edc948", "#9c755f", "#b07aa1", "#86bcb6",
    "#d37295", "#fabfd2", "#499894", "#d4a6c8", "#ffbe7d",
    "#8cd17d", "#b6992d", "#499894", "#a0cbe8", "#ff9d9a",
]

_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Session graph — __TOTAL__ sessions</title>
<style>
  html, body { margin: 0; height: 100%; background: #11151c; color: #d7dce3;
               font: 13px/1.45 system-ui, sans-serif; }
  #wrap { display: flex; height: 100%; }
  #side { width: 300px; overflow-y: auto; padding: 12px 14px; box-sizing: border-box;
          border-right: 1px solid #2a3140; flex-shrink: 0; }
  #side h1 { font-size: 15px; margin: 0 0 4px; }
  #side .meta { color: #8b93a3; font-size: 11px; margin-bottom: 12px; }
  .cluster { margin-bottom: 10px; padding: 8px 10px; border-radius: 6px;
             background: #1a2029; cursor: pointer; border: 1px solid transparent; }
  .cluster:hover, .cluster.active { border-color: #4e79a7; }
  .cluster .name { font-weight: 600; }
  .cluster .stats { color: #8b93a3; font-size: 11px; }
  .cluster .terms { color: #a8b3c4; font-size: 11px; margin-top: 2px; }
  .dot { display: inline-block; width: 9px; height: 9px; border-radius: 50%;
         margin-right: 6px; vertical-align: baseline; }
  #stage { flex: 1; position: relative; }
  canvas { display: block; width: 100%; height: 100%; }
  #tip { position: absolute; pointer-events: none; display: none; max-width: 320px;
         background: #1a2029; border: 1px solid #4e79a7; border-radius: 6px;
         padding: 7px 10px; font-size: 12px; z-index: 5; }
  .dormant .name::after { content: " · dormant"; color: #6b7280; font-weight: 400; }
</style>
</head>
<body>
<div id="wrap">
  <div id="side">
    <h1>Session graph</h1>
    <div class="meta">__TOTAL__ sessions · __EDGES__ links · half-life __HALF__d · __GENERATED__</div>
    <div id="clusters">__CLUSTER_CARDS__</div>
  </div>
  <div id="stage"><canvas id="cv"></canvas><div id="tip"></div></div>
</div>
<script>
const NODES = __NODES__;
const EDGES = __EDGES__;
const CLUSTERS = __CLUSTERS__;
const PALETTE = __PALETTE__;

const cv = document.getElementById("cv");
const ctx = cv.getContext("2d");
const tip = document.getElementById("tip");

// Deterministic layout: golden-angle spiral from the cluster centroid.
// Cluster centroids sit on a circle; member sessions spiral outward.
const W = () => cv.width = cv.clientWidth * devicePixelRatio;
const H = () => cv.height = cv.clientHeight * devicePixelRatio;

function layout() {
  const w = cv.clientWidth, h = cv.clientHeight;
  const R = Math.min(w, h) * 0.36;
  const byCluster = {};
  NODES.forEach(n => { (byCluster[n.cluster] = byCluster[n.cluster] || []).push(n); });
  const ids = Object.keys(byCluster).map(Number).sort((a, b) => a - b);
  const centers = {};
  ids.forEach((cid, i) => {
    const a = 2 * Math.PI * i / Math.max(ids.length, 1) - Math.PI / 2;
    centers[cid] = [w / 2 + R * Math.cos(a), h / 2 + R * Math.sin(a)];
  });
  const GOLDEN = Math.PI * (3 - Math.sqrt(5));
  NODES.forEach(n => {
    const members = byCluster[n.cluster] || [n];
    const idx = members.indexOf(n);
    const [cx, cy] = centers[n.cluster] || [w / 2, h / 2];
    const r = 26 + 13 * Math.sqrt(idx) * (devicePixelRatio > 1 ? 1.4 : 1);
    n.x = (cx + r * Math.cos(GOLDEN * idx)) * devicePixelRatio;
    n.y = (cy + r * Math.sin(GOLDEN * idx)) * devicePixelRatio;
    n.color = PALETTE[((n.cluster % PALETTE.length) + PALETTE.length) % PALETTE.length];
  });
}

function draw() {
  ctx.clearRect(0, 0, cv.width, cv.height);
  EDGES.forEach(e => {
    const s = NODES.find(n => n.id === e.source), t = NODES.find(n => n.id === e.target);
    if (!s || !t) return;
    ctx.strokeStyle = s.color + "55";
    ctx.lineWidth = Math.min(2.2, 0.5 + e.weight * 0.9) * devicePixelRatio;
    ctx.beginPath(); ctx.moveTo(s.x, s.y); ctx.lineTo(t.x, t.y); ctx.stroke();
  });
  NODES.forEach(n => {
    const r = (2.6 + Math.min(n.degree || 0, 12) * 0.55) * devicePixelRatio;
    ctx.beginPath(); ctx.arc(n.x, n.y, r, 0, 2 * Math.PI);
    ctx.fillStyle = n.color; ctx.globalAlpha = n.dormant ? 0.35 : 0.95;
    ctx.fill(); ctx.globalAlpha = 1;
  });
}

function hit(p) {
  let best = null, bd = 14 * devicePixelRatio;
  NODES.forEach(n => {
    const d = Math.hypot(n.x - p.x, n.y - p.y);
    if (d < bd) { bd = d; best = n; }
  });
  return best;
}

cv.addEventListener("mousemove", ev => {
  const rect = cv.getBoundingClientRect();
  const n = hit({ x: (ev.clientX - rect.left) * devicePixelRatio,
                  y: (ev.clientY - rect.top) * devicePixelRatio });
  if (!n) { tip.style.display = "none"; return; }
  const c = CLUSTERS.find(k => k.id === n.cluster);
  tip.innerHTML = "<b>" + (n.title || n.id.slice(0, 12)) + "</b><br>" +
    (n.project || "") + (n.date ? " · " + n.date : "") +
    (c ? "<br><i>" + (c.name || c.label || "cluster " + c.id) + "</i>" : "");
  tip.style.display = "block";
  tip.style.left = (ev.clientX - rect.left + 14) + "px";
  tip.style.top = (ev.clientY - rect.top + 14) + "px";
});
cv.addEventListener("mouseleave", () => tip.style.display = "none");

document.getElementById("clusters").addEventListener("click", ev => {
  const card = ev.target.closest(".cluster");
  if (!card) return;
  const cid = Number(card.dataset.cluster);
  const focus = cid === -1 ? null : cid;
  NODES.forEach(n => n.hidden = focus !== null && n.cluster !== focus);
  draw();
  NODES.forEach(n => n.hidden = false);
  document.querySelectorAll(".cluster").forEach(el => el.classList.remove("active"));
  card.classList.add("active");
});

window.addEventListener("resize", () => { W(); H(); layout(); draw(); });
W(); H(); layout(); draw();
</script>
</body>
</html>
"""


def render_html(
    graph: dict[str, Any],
    clusters_doc: dict[str, Any],
    half_life_days: float = 90.0,
    out_dir: Path | None = None,
) -> str:
    """Render the session graph as a standalone HTML page.

    ``graph`` is the sidecar ``graph.json`` document, ``clusters_doc`` the
    sidecar ``clusters.json``. Both shapes come from
    :func:`okf_wiki.session_graph.build`. ``out_dir`` is accepted for
    signature compatibility with the source implementation and ignored —
    the page embeds all data.
    """
    nodes = [
        {
            "id": n["id"],
            "title": n.get("title") or n["id"][:12],
            "project": n.get("project"),
            "date": (n.get("last_active") or n.get("start_ts") or "")[:10],
            "degree": n.get("degree", 0),
            "cluster": n.get("cluster", -1),
            "dormant": bool(n.get("dormant")),
        }
        for n in graph.get("nodes", [])
    ]
    edges = [
        {"source": e["source"], "target": e["target"], "weight": e.get("weight", 0.0)}
        for e in graph.get("edges", [])
    ]
    clusters = [
        {
            "id": c["id"], "size": c.get("size", 0),
            "label": c.get("label"), "name": c.get("name"),
            "recency": round(c.get("recency", 0.0), 2),
            "momentum": round(c.get("momentum", 0.0), 2),
            "dormant": bool(c.get("dormant")),
            "top_terms": (c.get("top_terms") or [])[:6],
        }
        for c in clusters_doc.get("clusters", [])
    ]

    cards = []
    for c in sorted(clusters, key=lambda k: -k["size"]):
        name = c["name"] or c["label"] or f"cluster {c['id']}"
        color = _PALETTE[c["id"] % len(_PALETTE)] if c["id"] >= 0 else "#6b7280"
        # top_terms arrives as (term, weight) pairs from clusters_doc; take the term side
        terms = ", ".join(
            t[0] if isinstance(t, (list, tuple)) else str(t)
            for t in c["top_terms"]
        )
        cards.append(
            f'<div class="cluster{" dormant" if c["dormant"] else ""}" data-cluster="{c["id"]}">'
            f'<div class="name"><span class="dot" style="background:{color}"></span>{name}</div>'
            f'<div class="stats">{c["size"]} sessions · recency {c["recency"]} · '
            f'momentum {c["momentum"]:+.2f}</div>'
            + (f'<div class="terms">{terms}</div>' if terms else "")
            + "</div>"
        )

    return (
        _TEMPLATE
        .replace("__TOTAL__", str(len(nodes)))
        .replace("__EDGES__", str(len(edges)))
        .replace("__HALF__", str(half_life_days))
        .replace("__GENERATED__", str(graph.get("generated_at", ""))[:19])
        .replace("__CLUSTER_CARDS__", "\n".join(cards))
        .replace("__NODES__", json.dumps(nodes, ensure_ascii=False))
        .replace("__EDGES__", json.dumps(edges, ensure_ascii=False))
        .replace("__CLUSTERS__", json.dumps(clusters, ensure_ascii=False))
        .replace("__PALETTE__", json.dumps(_PALETTE))
    )
