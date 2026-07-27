#!/usr/bin/env python3
"""
Graph memory: prior task outcomes, claim decisions, reviewer disagreements,
blocked-gate reasons, and repair patterns, persisted as structured graph data
-- typed nodes and typed edges -- rather than a flattened transcript or a
JSON blob bolted onto the side of the graph.

THIS MODULE MUTATES THE GRAPH. That is a deliberate exception to the
read-only rule the rest of the query/report layer follows: `graph_inspector.py`,
`graph_queries.py`, `graph_roadmap.py`, and `graph_evals.py` all say in their
own docstrings that they never write, and CLAUDE.md rule 4 says a task that
seems to need one of them to write is a sign the write belongs somewhere
else. This is that somewhere else for durable, cross-run memory --
`research_graph_workers.WorkerSpawner` is the other legitimate writer, but it
is scoped to admitting one extraction job's output, not to remembering what
happened across runs. Do not import `graph_memory` from any read-only
module, and do not add a mutating function to one of those instead of here.

Every memory record is a `NodeType.MEMORY_RECORD` node -- one closed
`MemoryKind` enum value distinguishes what it records -- connected to the
thing it is about by one of five typed edges (added to `EdgeType`'s semantic
section, not the gate-control section, since memory is not workflow control):

  SUPPORTED_BY      claim -> memory_record       claim was accepted; this is why
  REJECTED_BECAUSE  claim -> memory_record       claim was rejected; this is why
  DISAGREED_ON      memory_record -> any node    two reviewers disagreed on it
  REPAIRED_VIA       any node -> memory_record    this is how it got fixed
  DERIVED_FROM      memory_record -> any node    computed from that graph node

This subsumes the `gap_typed_provenance_edges` backlog item (ROADMAP.md):
rather than one generic edge for "this came from that," memory gets typed
relations from the start.

None of this replaces two things that already exist:
  - `ConflictEdge` is two *claims* contradicting each other on the merits.
    `DISAGREED_ON`/`MemoryKind.REVIEWER_DISAGREEMENT` is two *humans*
    disagreeing about the same node -- a reviewing-process fact, not a
    claims-content fact.
  - `WorkflowGate.should_unlock_next_stage()` still computes the live,
    re-run verdict. `record_blocked_reason` persists one such verdict as
    data so it can be queried *after* the gate has moved on, which is what
    `graph_queries.why_blocked` alone cannot do -- that function only ever
    returns a decision, it never remembers one.

`MemoryKind.REPAIR_PATTERN` describes the shape a successful repair would
have; the adaptive-recovery retry loop that would produce these
automatically (`gap_adaptive_recovery`, ROADMAP.md backlog) does not exist
in this repo yet. `record_repair_pattern` still works today for a repair a
human carried out by hand -- it does not require the retry loop to exist.

Two more pieces, added from a 2026 literature pass on agent-memory security
(a memory-lifecycle survey plus a provenance-capped belief-updating paper,
both converging on the same finding): don't trust a node's confidence at
face value just because it says so, and treat forgetting/rolling back a
prior memory as a governed action, not a silent overwrite.
  - `provenance_trust_weight_for`/`provenance_bound_confidence` cap a
    node's self-reported confidence by how independently verified its
    source actually is (`ExtractionMethod`), not the raw figure. Purely
    additive pure functions -- nothing existing calls them.
  - `provenance_weighted_trust_scores` is a new, parallel aggregation to
    `specialist_trust_scores`: same per-role tally, but each disagreement
    is weighted by the disputed node's provenance trust weight instead of
    counted as a flat 1. `specialist_trust_scores` itself is unchanged in
    its own arithmetic; it now additionally skips retracted disagreements
    (see below), which is a no-op for any graph that never retracts one.
  - `retract_memory_record`/`is_retracted`/`active_memory_records_for`
    give "Forget & Rollback" -- named as a first-class, security-relevant
    lifecycle phase this enum previously had no analog for -- a real,
    append-only representation: retraction is itself a new MEMORY_RETRACTED
    record linked back to what it retracts, never a deletion or in-place
    edit of the original.
"""

import hashlib
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from research_graph_schema import (
    Edge, EdgeType, ExtractionMethod, MemoryKind, Node, NodeType, Provenance,
    ResearchGraph,
)
import research_graph_gates as gates

if TYPE_CHECKING:
    # Type-checking only -- action_policy.py imports this module directly
    # (to call record_action_policy_decision), so a real import here would
    # be circular. This has zero runtime effect; it exists only so mypy
    # can resolve the "action_policy.PolicyDecision" forward reference.
    import action_policy

try:
    from task_graph import TaskSpan
except ImportError:  # pragma: no cover -- task_graph is domain-agnostic; keep this soft
    TaskSpan = None  # type: ignore[assignment,misc]  # intentional soft-dependency fallback


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _slug(*parts: str, n: int = 8) -> str:
    return hashlib.sha1("|".join(parts).encode()).hexdigest()[:n]


def _memory_id(kind: MemoryKind, subject_ref: str) -> str:
    """Deterministic-looking, collision-resistant id: readable prefix + content hash."""
    return f"memory_{kind.value}_{_slug(kind.value, subject_ref, _now())}"


def _memory_node(
    kind: MemoryKind,
    subject_ref: str,
    summary: str,
    confidence: Optional[float],
    source_paper: str,
    human_reviewed: bool,
    review_notes: str,
    details: Dict[str, Any],
) -> Node:
    """Build (but do not insert) one MEMORY_RECORD node. Shared by every record_* below."""
    provenance = Provenance(
        source_paper=source_paper,
        extraction_method=ExtractionMethod.MEMORY_WRITE.value,
        confidence=confidence,
        extracted_at=_now(),
        human_reviewed=human_reviewed,
        review_notes=review_notes,
    )
    return Node(
        id=_memory_id(kind, subject_ref),
        type=NodeType.MEMORY_RECORD.value,
        label=summary,
        provenance=provenance,
        properties={
            "memory_kind": kind.value,
            "summary": summary,
            "recorded_at": _now(),
            "subject_ref": subject_ref,
            "confidence": confidence,
            "details": dict(details),
        },
    )


# ============================================================================
# RECORDING (mutates the graph passed in)
# ============================================================================

def record_task_outcome(graph: ResearchGraph, span: "TaskSpan") -> Node:
    """
    Persist one task_graph.TaskSpan's outcome (task_id, agent_id, status,
    confidence, timing, error) as a MEMORY_RECORD, so a future run can ask
    "how did this task go last time" without replaying the scheduler.

    `span.task_id` is a task_graph.TaskDAG identifier -- it is not
    necessarily a ResearchGraph node id (a demo TaskDAG has no corresponding
    graph nodes at all). A DERIVED_FROM edge back to that id is only added
    when the graph already has a node with that id (e.g. the extraction_job
    the task represents); otherwise the memory record still lands, just
    without a dangling edge to a node that was never there.
    """
    summary = f"Task {span.task_id} ({span.agent_id or 'unassigned'}) ended {span.status}"
    node = _memory_node(
        kind=MemoryKind.TASK_OUTCOME,
        subject_ref=span.task_id,
        summary=summary,
        confidence=span.confidence,
        source_paper=span.task_id,
        human_reviewed=False,
        review_notes="",
        details={
            "task_id": span.task_id,
            "agent_id": span.agent_id,
            "parent_task_id": span.parent_task_id,
            "status": span.status,
            "started_at": span.started_at,
            "ended_at": span.ended_at,
            "error": span.error,
        },
    )
    graph.nodes.append(node)
    if span.task_id in graph.index():
        graph.edges.append(Edge(
            source=node.id, target=span.task_id, type=EdgeType.DERIVED_FROM.value,
            provenance=node.provenance,
        ))
    return node


def record_claim_decision(
    graph: ResearchGraph,
    claim_id: str,
    accepted: bool,
    reviewed_by: str,
    reason: str,
    confidence: Optional[float] = None,
) -> Node:
    """
    Record a human reviewer's verdict on a claim: accepted (a claim that
    passed the gate, possibly via a waiver) or rejected. Links the claim to
    the new memory record with SUPPORTED_BY (accepted) or REJECTED_BECAUSE
    (rejected) -- so "why is this claim still in the graph" and "why was
    this claim thrown out" are both graph-queryable facts, not something
    only a reviewer remembers.
    """
    claim = graph.index().get(claim_id)
    if claim is None:
        raise KeyError(f"no such node: {claim_id!r}")
    if confidence is None:
        confidence = claim.provenance.confidence if claim.provenance else None

    kind = MemoryKind.CLAIM_ACCEPTED if accepted else MemoryKind.CLAIM_REJECTED
    verb = "accepted" if accepted else "rejected"
    summary = f"Claim {claim_id} {verb} by {reviewed_by}: {reason}"
    node = _memory_node(
        kind=kind,
        subject_ref=claim_id,
        summary=summary,
        confidence=confidence,
        source_paper=claim_id,
        human_reviewed=True,
        review_notes=reason,
        details={"claim_id": claim_id, "accepted": accepted,
                 "reviewed_by": reviewed_by, "reason": reason},
    )
    graph.nodes.append(node)
    edge_type = EdgeType.SUPPORTED_BY if accepted else EdgeType.REJECTED_BECAUSE
    graph.edges.append(Edge(source=claim_id, target=node.id, type=edge_type.value,
                             provenance=node.provenance))
    return node


def record_disagreement(
    graph: ResearchGraph,
    node_id: str,
    reviewer_a: str,
    verdict_a: str,
    reviewer_b: str,
    verdict_b: str,
    note: str = "",
) -> Node:
    """
    Record that two reviewers disagreed about the same node -- distinct from
    `ConflictEdge` (two *claims* contradicting each other on their merits):
    this is two *humans* disagreeing on one verdict, which can happen even
    when the claims involved don't conflict with anything. Linked
    DISAGREED_ON -> node_id (the disputed node can be any node type, so
    there is no fixed endpoint contract for this edge in the schema).
    """
    if graph.index().get(node_id) is None:
        raise KeyError(f"no such node: {node_id!r}")
    summary = f"{reviewer_a} said {verdict_a!r}, {reviewer_b} said {verdict_b!r} on {node_id}"
    node = _memory_node(
        kind=MemoryKind.REVIEWER_DISAGREEMENT,
        subject_ref=node_id,
        summary=summary,
        confidence=None,
        source_paper=node_id,
        human_reviewed=True,
        review_notes=note,
        details={"node_id": node_id, "reviewer_a": reviewer_a, "verdict_a": verdict_a,
                 "reviewer_b": reviewer_b, "verdict_b": verdict_b, "note": note},
    )
    graph.nodes.append(node)
    graph.edges.append(Edge(source=node.id, target=node_id,
                             type=EdgeType.DISAGREED_ON.value, provenance=node.provenance))
    return node


def record_confidence_divergence(
    graph: ResearchGraph,
    node_id: str,
    derivation_confidence: Optional[float],
    validation_confidence: Optional[float],
    note: str = "",
) -> Node:
    """
    Record a gap between a node's confidence when it was first derived
    (extracted) and its confidence on a later re-validation (a retry, a
    repair, or a subsequent pipeline re-run against the same source) --
    distinct from `record_disagreement` (two *humans* disagreeing) and from
    `ConflictEdge` (two *claims* contradicting each other): this is one
    node's own confidence reading changing across time, which the gate's
    single scalar `Provenance.confidence` has no memory of on its own.
    Linked DERIVED_FROM -> node_id ("this memory record was computed from
    that node"), the same edge `record_task_outcome`/`record_blocked_reason`
    already use for that relationship.
    """
    if graph.index().get(node_id) is None:
        raise KeyError(f"no such node: {node_id!r}")
    summary = (f"{node_id} confidence diverged: derivation="
               f"{derivation_confidence} -> validation={validation_confidence}")
    node = _memory_node(
        kind=MemoryKind.CONFIDENCE_DIVERGENCE,
        subject_ref=node_id,
        summary=summary,
        confidence=validation_confidence,
        source_paper=node_id,
        human_reviewed=False,
        review_notes=note,
        details={"node_id": node_id, "derivation_confidence": derivation_confidence,
                 "validation_confidence": validation_confidence, "note": note},
    )
    graph.nodes.append(node)
    graph.edges.append(Edge(source=node.id, target=node_id,
                             type=EdgeType.DERIVED_FROM.value, provenance=node.provenance))
    return node


def confidence_divergence_for(graph: ResearchGraph, node_id: str) -> List[Node]:
    """
    Every CONFIDENCE_DIVERGENCE memory record linked to `node_id` via
    DERIVED_FROM. Unlike `prior_disagreements_on` (safe to filter by edge
    type alone, since only `record_disagreement` ever emits DISAGREED_ON),
    DERIVED_FROM is shared with `record_task_outcome`, `record_blocked_reason`,
    and `record_repair_pattern` -- this must also filter by `memory_kind`,
    or it would silently return unrelated memory records that just happen
    to point at the same node.
    """
    idx = graph.index()
    out: List[Node] = []
    for e in graph.edges:
        if e.type != EdgeType.DERIVED_FROM.value or e.target != node_id:
            continue
        record = idx.get(e.source)
        if record is not None and record.properties.get("memory_kind") == \
                MemoryKind.CONFIDENCE_DIVERGENCE.value:
            out.append(record)
    return out


def record_action_policy_decision(
    graph: ResearchGraph,
    subject_ref: str,
    decision: "action_policy.PolicyDecision",
) -> Node:
    """
    Persist a runtime action_policy.ActionPolicy decision (ALLOWED/
    ESCALATED/BLOCKED) as durable audit evidence -- the audit-trail half
    of runtime policy enforcement, not just the allow/block decision
    itself.

    Unlike every other record_* function in this module, `subject_ref`
    does NOT need to already resolve to a graph node: a BLOCKED action, by
    definition, never produces one (the worker is never invoked, so
    there's nothing to point at). When `subject_ref` does resolve to a
    real node (the common case: the job that got authorized to spawn),
    a DERIVED_FROM edge links the audit record to it, same as
    `record_task_outcome`'s conditional edge; otherwise the record still
    lands, just without a dangling edge to a node that was never there.
    """
    summary = f"{subject_ref}: {decision.verdict.value} ({decision.rule_name}) -- {decision.reason}"
    node = _memory_node(
        kind=MemoryKind.ACTION_POLICY_DECISION,
        subject_ref=subject_ref,
        summary=summary,
        confidence=None,
        source_paper=subject_ref,
        human_reviewed=False,
        review_notes=decision.reason,
        details=decision.to_dict(),
    )
    graph.nodes.append(node)
    if subject_ref in graph.index():
        graph.edges.append(Edge(source=node.id, target=subject_ref,
                                 type=EdgeType.DERIVED_FROM.value, provenance=node.provenance))
    return node


def action_policy_decisions_for(graph: ResearchGraph, subject_ref: str) -> List[Node]:
    """Every ACTION_POLICY_DECISION memory record about `subject_ref` (an action
    id or a job id) -- filters by memory_kind since subject_ref match alone
    (unlike an edge type) is already specific to this kind by construction
    of memory_records_for, but this wraps that pattern for readability."""
    return [n for n in memory_records_for(graph, subject_ref)
            if n.properties.get("memory_kind") == MemoryKind.ACTION_POLICY_DECISION.value]


def record_blocked_reason(graph: ResearchGraph, gate_decision: "gates.GateDecision") -> Node:
    """
    Persist a GateDecision's block reason as durable graph data instead of
    something only visible transiently via `graph_queries.why_blocked` --
    that function re-runs the live gate and returns a decision, it never
    remembers one. Only meaningful for a decision that did not let the node
    through; raises if handed one that did, since there is nothing to
    persist a "block" reason for.
    """
    if gate_decision.can_proceed:
        raise ValueError(
            f"record_blocked_reason expects a blocked GateDecision, but "
            f"{gate_decision.node_id} was allowed to proceed "
            f"({gate_decision.reason_code.value})")

    node_id = gate_decision.node_id
    confidence = None
    for check in gate_decision.checks:
        if check.check_name == "confidence_above_threshold":
            confidence = check.evidence.get("confidence")

    summary = f"{node_id} blocked: [{gate_decision.reason_code.value}] {gate_decision.reason}"
    node = _memory_node(
        kind=MemoryKind.BLOCKED_REASON,
        subject_ref=node_id,
        summary=summary,
        confidence=confidence,
        source_paper=node_id,
        human_reviewed=False,
        review_notes="",
        details={
            "node_id": node_id,
            "reason_code": gate_decision.reason_code.value,
            "reason": gate_decision.reason,
            "failed_checks": [c.check_name for c in gate_decision.checks if not c.passed],
        },
    )
    graph.nodes.append(node)
    if node_id in graph.index():
        graph.edges.append(Edge(source=node.id, target=node_id,
                                 type=EdgeType.DERIVED_FROM.value, provenance=node.provenance))
    return node


def record_repair_pattern(
    graph: ResearchGraph,
    description: str,
    before_node_id: str,
    after_node_id: str,
) -> Node:
    """
    Describe the shape of a successful repair: `before_node_id` was
    rejected/blocked, `after_node_id` is what replaced or fixed it and got
    through. Linked REPAIRED_VIA (after_node -> memory_record) and, when
    `before_node_id` still has a live node in the graph, DERIVED_FROM
    (memory_record -> before_node) -- the repair pattern is "derived from"
    the failure it addresses.

    The adaptive-recovery retry loop that would produce these automatically
    (`gap_adaptive_recovery`, ROADMAP.md backlog) does not exist yet in this
    repo; this function doesn't need it to exist -- it just makes the memory
    shape ready to record one when it does. Today, call it for a repair a
    human carried out by hand.
    """
    after = graph.index().get(after_node_id)
    if after is None:
        raise KeyError(f"no such node: {after_node_id!r}")

    confidence = after.provenance.confidence if after.provenance else None
    summary = f"{after_node_id} repaired {before_node_id}: {description}"
    node = _memory_node(
        kind=MemoryKind.REPAIR_PATTERN,
        subject_ref=after_node_id,
        summary=summary,
        confidence=confidence,
        source_paper=before_node_id,
        human_reviewed=True,
        review_notes=description,
        details={"description": description, "before_node_id": before_node_id,
                 "after_node_id": after_node_id},
    )
    graph.nodes.append(node)
    graph.edges.append(Edge(source=after_node_id, target=node.id,
                             type=EdgeType.REPAIRED_VIA.value, provenance=node.provenance))
    if before_node_id in graph.index():
        graph.edges.append(Edge(source=node.id, target=before_node_id,
                                 type=EdgeType.DERIVED_FROM.value, provenance=node.provenance))
    return node


# ============================================================================
# READING (pure -- never mutates, same discipline as graph_queries.py)
# ============================================================================

def memory_records_for(graph: ResearchGraph, subject_ref: str) -> List[Node]:
    """Every MEMORY_RECORD node about `subject_ref` (a claim id, task id, node id, ...)."""
    return [n for n in graph.nodes
            if n.type == NodeType.MEMORY_RECORD.value
            and n.properties.get("subject_ref") == subject_ref]


def prior_disagreements_on(graph: ResearchGraph, node_id: str) -> List[Node]:
    """Every REVIEWER_DISAGREEMENT memory record linked to `node_id` via DISAGREED_ON."""
    idx = graph.index()
    return [idx[e.source] for e in graph.edges
            if e.type == EdgeType.DISAGREED_ON.value
            and e.target == node_id
            and e.source in idx]


def repair_patterns_for(graph: ResearchGraph, node_type: Optional[str] = None) -> List[Node]:
    """
    All REPAIR_PATTERN memory records, optionally filtered to those whose
    `after_node_id` is currently a node of `node_type` (e.g. NodeType.CLAIM.value)
    -- "how have we fixed claims before" as a queryable question.
    """
    idx = graph.index()
    out: List[Node] = []
    for n in graph.nodes:
        if (n.type != NodeType.MEMORY_RECORD.value
                or n.properties.get("memory_kind") != MemoryKind.REPAIR_PATTERN.value):
            continue
        if node_type is not None:
            after = idx.get(n.properties.get("details", {}).get("after_node_id"))
            if after is None or after.type != node_type:
                continue
        out.append(n)
    return out


def _outcome_side_for(graph: ResearchGraph, subject_ref: Optional[str]) -> Optional[str]:
    """
    Classify a node's current status into "pass" (completed/approved),
    "fail" (failed/rejected), or None -- still undecided (queued/running/
    held), or the id no longer resolves to a node. Never a bare guess: the
    absence of a decided outcome is treated as no data, not as a side.
    """
    if not subject_ref:
        return None
    node = graph.index().get(subject_ref)
    if node is None:
        return None
    status = (node.properties or {}).get("status")
    if status in ("completed", "approved"):
        return "pass"
    if status in ("failed", "rejected"):
        return "fail"
    return None


def specialist_trust_scores(graph: ResearchGraph) -> Dict[str, Dict[str, Any]]:
    """
    Aggregate every REVIEWER_DISAGREEMENT memory record into a per-role
    trust tally: how often a role's stated verdict on a disputed node
    matched what actually happened to that node (its own eventual
    completed/approved vs. failed/rejected status), vs. how often it
    didn't. No new signed-edge concept and no schema change -- the ground
    truth for "who was right" already lives in the graph (the disputed
    node's own eventual status), just not aggregated until now.

    `trust_score` is `agreements / (agreements + disagreements)`, or
    `None` when nothing about a role is decided yet -- never a bare
    0.0/1.0 stand-in for "no data," the same `Optional[float]` discipline
    `verdict_from_extraction`'s own confidence already follows.
    """
    tallies: Dict[str, Dict[str, int]] = {}

    def _tally(role: str) -> Dict[str, int]:
        return tallies.setdefault(role, {"agreements": 0, "disagreements": 0, "undecided": 0})

    for n in graph.nodes:
        if (n.type != NodeType.MEMORY_RECORD.value
                or n.properties.get("memory_kind") != MemoryKind.REVIEWER_DISAGREEMENT.value):
            continue
        if is_retracted(graph, n.id):
            # A retracted disagreement record no longer counts as evidence --
            # a no-op for any graph that never calls retract_memory_record.
            continue
        details = n.properties.get("details", {})
        side = _outcome_side_for(graph, details.get("node_id"))
        for role_key, verdict_key in (("reviewer_a", "verdict_a"), ("reviewer_b", "verdict_b")):
            role = details.get(role_key)
            if not role:
                continue
            tally = _tally(role)
            if side is None:
                tally["undecided"] += 1
            elif details.get(verdict_key) == side:
                tally["agreements"] += 1
            else:
                tally["disagreements"] += 1

    result: Dict[str, Dict[str, Any]] = {}
    for role, tally in tallies.items():
        decided = tally["agreements"] + tally["disagreements"]
        result[role] = {
            **tally,
            "trust_score": round(tally["agreements"] / decided, 4) if decided else None,
        }
    return result


def trust_score_for(graph: ResearchGraph, role: str) -> Optional[float]:
    """Convenience accessor over specialist_trust_scores(graph)."""
    return specialist_trust_scores(graph).get(role, {}).get("trust_score")


# ============================================================================
# PROVENANCE-BOUND TRUST (cap self-reported confidence by source reliability)
# ============================================================================

# How much independent evidentiary weight a node's own confidence deserves,
# keyed by what actually produced it -- not the confidence value itself.
# Never 1.0 for anything short of independent human verification; an
# unmapped or missing extraction method gets the same conservative default
# as the least-trusted mapped method, never silent full trust.
PROVENANCE_TRUST_WEIGHT: Dict[str, float] = {
    ExtractionMethod.HUMAN_ANNOTATION.value: 1.0,
    ExtractionMethod.STRUCTURED_LLM.value: 0.7,
    ExtractionMethod.ABSTRACT_PARSE.value: 0.6,
    ExtractionMethod.KEYWORD.value: 0.5,
    ExtractionMethod.METADATA.value: 0.5,
    ExtractionMethod.MEMORY_WRITE.value: 0.3,
    ExtractionMethod.JOB_SPAWN.value: 0.3,
    ExtractionMethod.GATE_HOLD.value: 0.3,
}
_DEFAULT_PROVENANCE_TRUST_WEIGHT = 0.5


def provenance_trust_weight_for(node: Node) -> float:
    """
    How much independent evidentiary weight `node`'s own confidence reading
    deserves, based on what actually produced it. Two independent 2026
    papers (a long-term agent-memory-security survey and a provenance-
    capped belief-updating paper) converge on capping trust by source
    provenance rather than a source's own self-reported confidence, as a
    defense against a poisoned or merely overconfident source. A node with
    no provenance, or an extraction method not in `PROVENANCE_TRUST_WEIGHT`,
    gets the same conservative default as the least-trusted mapped method
    -- never silently treated as fully trusted.
    """
    if node.provenance is None or not node.provenance.extraction_method:
        return _DEFAULT_PROVENANCE_TRUST_WEIGHT
    return PROVENANCE_TRUST_WEIGHT.get(
        node.provenance.extraction_method, _DEFAULT_PROVENANCE_TRUST_WEIGHT)


def provenance_bound_confidence(node: Node) -> Optional[float]:
    """
    `node`'s self-reported confidence, capped by how independently verified
    its source actually is -- never the raw self-reported figure taken at
    face value. `None` when the node has no confidence reading to bound in
    the first place (distinct from a bound value of 0.0).
    """
    if node.provenance is None or node.provenance.confidence is None:
        return None
    return round(node.provenance.confidence * provenance_trust_weight_for(node), 4)


def provenance_weighted_trust_scores(graph: ResearchGraph) -> Dict[str, Dict[str, Any]]:
    """
    A parallel aggregation to `specialist_trust_scores`: the same per-role
    disagreement tally, except each disagreement's contribution is weighted
    by `provenance_trust_weight_for` of the *disputed node*, not counted as
    a flat 1 -- a disagreement about a HUMAN_ANNOTATION-provenance node
    counts more toward a role's trust score than one about a node whose own
    confidence was only ever self-reported by a worker. This is additive: it
    does not change `specialist_trust_scores`'s own arithmetic or its
    return shape, so an existing caller of that function sees no behavior
    change. Retracted disagreements are excluded, same as
    `specialist_trust_scores`.
    """
    idx = graph.index()
    tallies: Dict[str, Dict[str, float]] = {}

    def _tally(role: str) -> Dict[str, float]:
        return tallies.setdefault(role, {
            "weighted_agreements": 0.0, "weighted_disagreements": 0.0, "undecided": 0.0,
        })

    for n in graph.nodes:
        if (n.type != NodeType.MEMORY_RECORD.value
                or n.properties.get("memory_kind") != MemoryKind.REVIEWER_DISAGREEMENT.value):
            continue
        if is_retracted(graph, n.id):
            continue
        details = n.properties.get("details", {})
        disputed = idx.get(details.get("node_id"))
        weight = (provenance_trust_weight_for(disputed) if disputed is not None
                  else _DEFAULT_PROVENANCE_TRUST_WEIGHT)
        side = _outcome_side_for(graph, details.get("node_id"))
        for role_key, verdict_key in (("reviewer_a", "verdict_a"), ("reviewer_b", "verdict_b")):
            role = details.get(role_key)
            if not role:
                continue
            tally = _tally(role)
            if side is None:
                tally["undecided"] += 1
            elif details.get(verdict_key) == side:
                tally["weighted_agreements"] += weight
            else:
                tally["weighted_disagreements"] += weight

    result: Dict[str, Dict[str, Any]] = {}
    for role, tally in tallies.items():
        decided_weight = tally["weighted_agreements"] + tally["weighted_disagreements"]
        result[role] = {
            **tally,
            "weighted_trust_score": (round(tally["weighted_agreements"] / decided_weight, 4)
                                      if decided_weight else None),
        }
    return result


# ============================================================================
# RETRACTION ("Forget & Rollback" as a governed, append-only action)
# ============================================================================

def retract_memory_record(
    graph: ResearchGraph,
    record_id: str,
    retracted_by: str,
    reason: str,
) -> Node:
    """
    Governed retraction of a prior memory record -- "Forget & Rollback,"
    named by a 2026 agent-memory-security survey as a first-class,
    security-relevant lifecycle phase this module's MemoryKind enum
    otherwise has no analog for. Retraction is itself a new, append-only
    MEMORY_RETRACTED record linked DERIVED_FROM -> record_id -- it never
    deletes or mutates the original record, matching this graph's
    append-only discipline everywhere else. The retracted record's node
    still exists and is still directly queryable; `is_retracted`/
    `active_memory_records_for` are how a caller learns to discount it.
    """
    record = graph.index().get(record_id)
    if record is None:
        raise KeyError(f"no such node: {record_id!r}")
    if record.type != NodeType.MEMORY_RECORD.value:
        raise ValueError(f"{record_id!r} is not a memory record (type={record.type!r})")

    summary = f"{record_id} retracted by {retracted_by}: {reason}"
    node = _memory_node(
        kind=MemoryKind.MEMORY_RETRACTED,
        subject_ref=record_id,
        summary=summary,
        confidence=None,
        source_paper=record_id,
        human_reviewed=True,
        review_notes=reason,
        details={"record_id": record_id, "retracted_by": retracted_by, "reason": reason},
    )
    graph.nodes.append(node)
    graph.edges.append(Edge(source=node.id, target=record_id,
                             type=EdgeType.DERIVED_FROM.value, provenance=node.provenance))
    return node


def is_retracted(graph: ResearchGraph, record_id: str) -> bool:
    """Whether `record_id` (a memory record's own node id) has ever been retracted."""
    idx = graph.index()
    for e in graph.edges:
        if e.type != EdgeType.DERIVED_FROM.value or e.target != record_id:
            continue
        record = idx.get(e.source)
        if record is not None and record.properties.get("memory_kind") == \
                MemoryKind.MEMORY_RETRACTED.value:
            return True
    return False


def active_memory_records_for(graph: ResearchGraph, subject_ref: str) -> List[Node]:
    """Same as `memory_records_for`, minus any record that has since been retracted."""
    return [n for n in memory_records_for(graph, subject_ref) if not is_retracted(graph, n.id)]


if __name__ == "__main__":
    import json
    import golden_fixtures as gf
    from task_graph import TaskSpan as _TaskSpan

    g = gf.build_fixture_graph()

    record_task_outcome(g, _TaskSpan(
        task_id="job_2606_claims_001", agent_id="claim_extractor", parent_task_id=None,
        status="completed", confidence=0.91, started_at=_now(), ended_at=_now(),
    ))
    record_claim_decision(g, "claim_2606_001", accepted=True,
                           reviewed_by="parry.s.2324@gmail.com",
                           reason="Confirmed against the source paper's abstract.")
    record_disagreement(g, "claim_2701_014", reviewer_a="alice", verdict_a="accept",
                         reviewer_b="bob", verdict_b="reject",
                         note="alice reads it as scope-dependent, bob as a straight conflict")
    decision = gates.WorkflowGate().should_unlock_next_stage(
        __import__("graph_queries")._to_gate_node(g.index()["job_2606_concepts_001"]), g)
    record_blocked_reason(g, decision)

    print(f"nodes={len(g.nodes)} edges={len(g.edges)}")
    print(json.dumps(g.validate().to_dict(), indent=2)[:400])
