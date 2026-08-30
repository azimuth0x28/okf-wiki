"""Community detection for the session graph.

Ported from the source repo's graph_analysis — only the functions the
session graph needs: detect_communities (Leiden when the ``graph`` extra
is installed, greedy label propagation otherwise), surprising_connections
(cross-cluster bridge ranking), and the greedy detector itself.
"""
from __future__ import annotations

import math
import random
from collections import defaultdict

try:
    from typing import Dict, List, Set, Tuple  # noqa: F401  (py3.9 typing aid)
except ImportError:  # pragma: no cover
    Dict = List = Set = Tuple = None  # type: ignore[assignment]

def detect_communities_greedy(outgoing: dict[str, list[str]]) -> list[set[str]]:
    """Greedy modularity community detection (label propagation variant).

    Fast O(n·k) approach suitable for vaults up to ~5 000 pages. Each node
    adopts the most frequent label among its neighbours; iterate until stable.
    Falls back gracefully to one community per page if the graph is empty.
    """
    nodes = list(outgoing.keys())
    if not nodes:
        return []

    # Build undirected adjacency
    adj: dict[str, list[str]] = defaultdict(list)
    for src, targets in outgoing.items():
        for t in targets:
            adj[src].append(t)
            adj[t].append(src)

    # Initialise: each node in its own community (label = index)
    labels: dict[str, int] = {n: i for i, n in enumerate(nodes)}

    # Visit nodes in a shuffled order each round. A fixed sequential sweep
    # cascades one label along chains and collapses well-separated clusters
    # into a single community (a barbell graph comes back as one group). The
    # RNG is seeded from the node set, so the result stays reproducible.
    rng = random.Random(len(nodes))
    order = list(nodes)

    for _ in range(20):  # max 20 rounds
        changed = False
        rng.shuffle(order)
        for n in order:
            neighbours = adj[n]
            if not neighbours:
                continue
            freq: dict[int, int] = defaultdict(int)
            for nb in neighbours:
                freq[labels[nb]] += 1
            best = max(freq, key=lambda lbl: (freq[lbl], -lbl))
            if best != labels[n]:
                labels[n] = best
                changed = True
        if not changed:
            break

    # Group by label
    groups: dict[int, set[str]] = defaultdict(set)
    for n, lbl in labels.items():
        groups[lbl].add(n)
    return list(groups.values())


def detect_communities(outgoing: dict[str, list[str]]) -> list[set[str]]:
    """Try Leiden (leidenalg + igraph) first; fall back to greedy label propagation."""
    try:
        import igraph as ig
        import leidenalg

        nodes = list(outgoing.keys())
        node_idx = {n: i for i, n in enumerate(nodes)}
        edges = [
            (node_idx[s], node_idx[t])
            for s, targets in outgoing.items()
            for t in targets
            if t in node_idx
        ]
        g = ig.Graph(n=len(nodes), edges=edges, directed=False)
        partition = leidenalg.find_partition(g, leidenalg.ModularityVertexPartition)
        return [
            {nodes[i] for i in cluster}
            for cluster in partition
        ]
    except ImportError:
        return detect_communities_greedy(outgoing)


def _node_community_map(communities: list[set[str]]) -> dict[str, int]:
    return {n: i for i, comm in enumerate(communities) for n in comm}



def surprising_connections(
    outgoing: dict[str, list[str]],
    communities: list[set[str]],
    top_n: int = 20,
) -> list[dict]:
    """Edges that cross community boundaries, ranked by unexpectedness.

    Score = 1 / sqrt(cross_degree(source) * cross_degree(target))
    Low cross-degree nodes connected across communities are the most surprising.

    Results are ordered so that each (community A, community B) boundary is
    represented once before any boundary repeats — graphify's dedup, which
    stops one high-betweenness hub from filling every slot.
    """
    node_comm = _node_community_map(communities)

    # Count how many cross-community edges each node already has
    cross_deg: dict[str, int] = defaultdict(int)
    for src, targets in outgoing.items():
        for t in targets:
            if node_comm.get(src) != node_comm.get(t):
                cross_deg[src] += 1
                cross_deg[t] += 1

    results = []
    seen: set[tuple[str, str]] = set()
    for src, targets in outgoing.items():
        for t in targets:
            pair = tuple(sorted((src, t)))
            if pair in seen:
                continue
            if node_comm.get(src) != node_comm.get(t):
                cd_s = cross_deg.get(src, 1)
                cd_t = cross_deg.get(t, 1)
                score = 1.0 / math.sqrt(cd_s * cd_t)
                cs, ct = node_comm.get(src), node_comm.get(t)
                results.append({
                    "source": src, "target": t, "score": round(score, 4),
                    "note": f"bridges community {cs} -> community {ct}",
                    "_pair": (min(cs, ct), max(cs, ct)) if cs is not None and ct is not None else None,
                })
                seen.add(pair)

    results.sort(key=lambda x: -x["score"])
    # One representative per community pair first, then the rest by score.
    seen_pairs: set = set()
    first: list[dict] = []
    rest: list[dict] = []
    for r in results:
        pair = r.pop("_pair")
        if pair not in seen_pairs:
            seen_pairs.add(pair)
            first.append(r)
        else:
            rest.append(r)
    return (first + rest)[:top_n]
