#!/usr/bin/env python3
"""
Phase 7: Roadmap rollup (read-only)

Answers gap_roadmap_queries from literature_corpus.py: aggregate GAP/METHOD/
DOMAIN/BENCHMARK nodes into a rolled-up view showing which papers substantiate
each one, ranked by how many papers do. A single ADDRESSES/USES_METHOD/etc.
edge is one paper's opinion; a rollup across the whole graph is what tells you
which gap actually has traction versus which one paper happened to mention.

Attribution walks CLAIM -> PAPER via the reverse PRODUCES edge, since the
semantic edge (e.g. ADDRESSES) is usually drawn from a claim, not directly
from the paper node -- see literature_corpus.py's paper -> claim -> gap chain.
"""

from typing import Any, Dict, List, Optional

from research_graph_schema import Node, ResearchGraph, NodeType, EdgeType
from graph_queries import get_node, neighbors

# Which edge types count as "this contributes to that rollup node", per node type.
ROLLUP_EDGE_TYPES: Dict[NodeType, set] = {
    NodeType.GAP: {EdgeType.ADDRESSES.value, EdgeType.LEAVES_GAP.value},
    NodeType.METHOD: {EdgeType.USES_METHOD.value, EdgeType.PROPOSES.value},
    NodeType.DOMAIN: {EdgeType.APPLIES.value},
    NodeType.BENCHMARK: {EdgeType.BENCHMARKS.value},
}


def _paper_for(graph: ResearchGraph, node_id: str) -> Optional[Node]:
    """node_id itself if it's a paper, else the paper that PRODUCES it (one hop back)."""
    node = get_node(graph, node_id)
    if node is None:
        return None
    if node.type == NodeType.PAPER.value:
        return node
    for producer in neighbors(graph, node_id, edge_type=EdgeType.PRODUCES.value, direction="in"):
        if producer.type == NodeType.PAPER.value:
            return producer
    return None


def roadmap_summary(graph: ResearchGraph, node_type: NodeType) -> List[Dict[str, Any]]:
    """
    One row per node of `node_type`, sorted by paper_count descending:
      {id, text, paper_count, papers: [(paper_id, title), ...]}
    """
    edge_types = ROLLUP_EDGE_TYPES.get(node_type)
    if edge_types is None:
        raise ValueError(f"{node_type!r} is not a rollup-able node type "
                          f"(expected one of {list(ROLLUP_EDGE_TYPES)})")

    targets = [n for n in graph.nodes if n.type == node_type.value]
    rows: List[Dict[str, Any]] = []
    for t in targets:
        papers: Dict[str, str] = {}
        for e in graph.edges:
            if e.target != t.id or e.type not in edge_types:
                continue
            paper = _paper_for(graph, e.source)
            if paper is not None:
                papers[paper.id] = paper.properties.get("title", paper.label)
        rows.append({
            "id": t.id,
            "text": t.properties.get("text", t.label),
            "paper_count": len(papers),
            "papers": sorted(papers.items()),
        })

    rows.sort(key=lambda r: (-r["paper_count"], r["id"]))
    return rows


def full_roadmap(graph: ResearchGraph) -> Dict[str, List[Dict[str, Any]]]:
    """roadmap_summary() for every rollup-able node type actually present in the graph."""
    present = {n.type for n in graph.nodes}
    return {
        nt.value: roadmap_summary(graph, nt)
        for nt in ROLLUP_EDGE_TYPES
        if nt.value in present
    }


def render_roadmap_report(graph: ResearchGraph) -> str:
    roadmap = full_roadmap(graph)
    if not roadmap:
        return "ROADMAP\n(no GAP/METHOD/DOMAIN/BENCHMARK nodes in this graph)"

    lines: List[str] = ["ROADMAP (rolled up by paper support)"]
    for node_type_value, rows in roadmap.items():
        header = f"\n{node_type_value.upper()} ({len(rows)})"
        lines += [header, "-" * len(header.strip())]
        for r in rows:
            lines.append(f"  [{r['paper_count']}] {r['id']}: {r['text']}")
            for paper_id, title in r["papers"]:
                lines.append(f"        - {paper_id}: {title}")
    return "\n".join(lines)


if __name__ == "__main__":
    import literature_corpus as corpus

    print(render_roadmap_report(corpus.build_corpus_graph()))
