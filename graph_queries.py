#!/usr/bin/env python3
"""
Phase 6: Agent query behavior (read-only)

Built on top of graph_inspector's inspection surface: once a human can eyeball
the graph, the same primitives get exposed as structured functions an agent can
call directly, instead of parsing report text. Every function here takes a
ResearchGraph (plus an optional WorkflowGate where a live decision is needed)
and returns nodes/edges/decisions -- never text, never a mutation.

Seven questions an agent actually needs to ask:
  get_node              -- "what is this id"
  claims_for_paper       -- "what did this paper produce"
  neighbors              -- "what connects to this node, and how"
  unresolved_conflicts   -- "what's still contradicting what"
  contradicting_claims   -- "what contradicts this specific claim"
  blocked_jobs/why_blocked -- "what's stuck, and why" (re-runs the real gate)
  search                 -- "find nodes whose text mentions X"
  detect_job_dependency_cycles -- "will this job graph deadlock" (BLOCKED_BY cycles)
"""

from typing import Any, Dict, List, Optional

from research_graph_schema import (
    ConflictEdge, EdgeType, ExtractionMethod, Node, NodeType, ResearchGraph,
)
import research_graph_gates as gates
import graph_algorithms


def _to_gate_node(n: Node) -> gates.Node:
    """schema Node -> gate Node adapter. Same field names; the gate is trace-agnostic."""
    p = n.provenance
    return gates.Node(
        id=n.id,
        type=n.type,
        label=n.label,
        provenance=None if p is None else gates.Provenance(
            source_paper=p.source_paper,
            extraction_method=p.extraction_method,
            confidence=p.confidence,
            extracted_at=p.extracted_at,
            human_reviewed=p.human_reviewed,
            review_notes=p.review_notes,
        ),
        properties=n.properties,
    )


def get_node(graph: ResearchGraph, node_id: str) -> Optional[Node]:
    """The node with this id, or None if it isn't in the graph."""
    return graph.index().get(node_id)


def neighbors(
    graph: ResearchGraph,
    node_id: str,
    edge_type: Optional[str] = None,
    direction: str = "out",
) -> List[Node]:
    """
    Nodes reachable from `node_id` by one edge hop.

    direction="out": edges where node_id is the source (default).
    direction="in":  edges where node_id is the target.
    direction="both": either.
    """
    if direction not in ("out", "in", "both"):
        raise ValueError(f"direction must be 'out', 'in', or 'both', got {direction!r}")

    idx = graph.index()
    found: List[Node] = []
    for e in graph.edges:
        if edge_type is not None and e.type != edge_type:
            continue
        if direction in ("out", "both") and e.source == node_id and e.target in idx:
            found.append(idx[e.target])
        if direction in ("in", "both") and e.target == node_id and e.source in idx:
            found.append(idx[e.source])
    return found


def claims_for_paper(graph: ResearchGraph, paper_id: str) -> List[Node]:
    """Claim nodes this paper PRODUCES."""
    return [n for n in neighbors(graph, paper_id, edge_type=EdgeType.PRODUCES.value)
            if n.type == NodeType.CLAIM.value]


def unresolved_conflicts(graph: ResearchGraph) -> List[ConflictEdge]:
    """Every conflict in the graph that hasn't been marked resolved."""
    return [c for c in graph.conflicts if not c.resolved]


def contradicting_claims(graph: ResearchGraph, claim_id: str, include_resolved: bool = False) -> List[Node]:
    """Claim nodes that conflict with `claim_id`, via the graph's conflict list."""
    idx = graph.index()
    other_ids = set()
    for c in graph.conflicts:
        if c.resolved and not include_resolved:
            continue
        if c.source_claim_id == claim_id:
            other_ids.add(c.target_claim_id)
        elif c.target_claim_id == claim_id:
            other_ids.add(c.source_claim_id)
    return [idx[i] for i in other_ids if i in idx]


def why_blocked(
    graph: ResearchGraph,
    node_id: str,
    gate: Optional[gates.WorkflowGate] = None,
) -> gates.GateDecision:
    """
    Re-run the real gate against the node's current state in `graph` and return
    the full decision -- reflects waivers/reviews applied since the node was
    last evaluated, not a stored snapshot.
    """
    node = get_node(graph, node_id)
    if node is None:
        raise KeyError(f"no such node: {node_id!r}")
    gate = gate or gates.WorkflowGate()
    return gate.should_unlock_next_stage(_to_gate_node(node), graph)


def blocked_jobs(
    graph: ResearchGraph,
    gate: Optional[gates.WorkflowGate] = None,
) -> List[gates.GateDecision]:
    """The GateDecision for every extraction_job node currently unable to proceed."""
    gate = gate or gates.WorkflowGate()
    jobs = [n for n in graph.nodes if n.type == NodeType.EXTRACTION_JOB.value]
    decisions = [gate.should_unlock_next_stage(_to_gate_node(j), graph) for j in jobs]
    return [d for d in decisions if not d.can_proceed]


def search(graph: ResearchGraph, text: str) -> List[Node]:
    """
    Nodes whose label or common text-bearing properties (title, text, subject,
    relation, object) contain `text`, case-insensitively.
    """
    needle = text.lower()
    text_fields = ("title", "text", "subject", "relation", "object")

    def matches(n: Node) -> bool:
        if needle in n.label.lower():
            return True
        return any(needle in str(n.properties.get(f, "")).lower() for f in text_fields)

    return [n for n in graph.nodes if matches(n)]


def status_summary(graph: ResearchGraph) -> Dict[str, Any]:
    """Counts by node type, plus job/review status breakdowns -- the numbers behind the report."""
    by_type: Dict[str, int] = {}
    for n in graph.nodes:
        by_type[n.type] = by_type.get(n.type, 0) + 1

    job_status: Dict[str, int] = {}
    for n in graph.nodes:
        if n.type == NodeType.EXTRACTION_JOB.value:
            s = n.properties.get("status", "unknown")
            job_status[s] = job_status.get(s, 0) + 1

    review_status: Dict[str, int] = {}
    for n in graph.nodes:
        if n.type == NodeType.REVIEW_TASK.value:
            s = n.properties.get("status", "unknown")
            review_status[s] = review_status.get(s, 0) + 1

    return {
        "nodes_by_type": by_type,
        "job_status": job_status,
        "review_status": review_status,
        "unresolved_conflicts": len(unresolved_conflicts(graph)),
    }


def derivation_mechanism_for(node: Node) -> str:
    """
    Classify an existing node's derivation mechanism purely from data
    already on it -- its Provenance.extraction_method plus whether its
    properties look like a full subject/relation/object triple vs. bare
    text. A plain string, not a new schema-validated enum: nothing here
    can become a second, competing source of truth for extraction_method
    itself, which is why this stays in the read-only query layer rather
    than becoming a new closed enum ahead of a real producer for one.
    """
    if node.provenance is not None:
        method = node.provenance.extraction_method
        if method == ExtractionMethod.MEMORY_WRITE.value:
            return "memory_synthesis"
        if method == ExtractionMethod.HUMAN_ANNOTATION.value:
            return "human_annotated"
    props = node.properties or {}
    if props.get("subject") and props.get("relation") and props.get("object"):
        return "structured_relational"
    if props.get("text"):
        return "structured_named"
    return "unclassified"


def derivation_mechanism_breakdown(graph: ResearchGraph) -> Dict[str, int]:
    """How many nodes fall into each derivation-mechanism class -- "how was
    most of this graph actually produced" as a queryable question."""
    breakdown: Dict[str, int] = {}
    for n in graph.nodes:
        key = derivation_mechanism_for(n)
        breakdown[key] = breakdown.get(key, 0) + 1
    return breakdown


def detect_job_dependency_cycles(graph: ResearchGraph) -> List[List[str]]:
    """
    The "task DAG" from the graph-theory survey must actually be acyclic, or
    two extraction_job nodes wait on each other forever. Delegates the actual
    cycle detection to graph_algorithms.detect_cycles() -- the same algorithm
    task_graph.TaskDAG uses for its DEPENDS_ON edges -- over BLOCKED_BY edges
    (declared in the schema's EDGE_ENDPOINT_CONTRACT but not otherwise
    consumed anywhere until this function). Empty list means no deadlock.
    """
    adjacency: Dict[str, List[str]] = {}
    for e in graph.edges:
        if e.type == EdgeType.BLOCKED_BY.value:
            adjacency.setdefault(e.source, []).append(e.target)
    return graph_algorithms.detect_cycles(adjacency)
