#!/usr/bin/env python3
"""
Golden fixtures — the four canonical states Phase 3 must round-trip and Phase 2's
gate must still judge identically.

These cross the schema/gate seam on purpose. If a future change to either side
breaks the contract between them, one of these four fails first.

  1. auto_pass_job()      — high confidence, reviewed, complete → gate ALLOWS
  2. held_for_review_job() — low confidence → gate BLOCKS (LOW_CONFIDENCE)
  3. human_waived_job()   — low confidence + explicit human waiver on the review_task
  4. conflict_claim_pair() — two claims that contradict each other
"""

from datetime import datetime, timezone

from research_graph_schema import (
    Node, Edge, Provenance, Trace, ConflictEdge, ResearchGraph,
    NodeType, EdgeType, JobStatus, ReviewStatus, ExtractionType,
    ConflictType, DecisionType, ExtractionMethod,
)

TS = "2026-07-26T15:32:00+00:00"
PAPER = "2606.13707"


def _prov(conf, reviewed=False, method=ExtractionMethod.JOB_SPAWN, notes=""):
    return Provenance(
        source_paper=PAPER,
        extraction_method=method.value,
        confidence=conf,
        extracted_at=TS,
        human_reviewed=reviewed,
        review_notes=notes,
    )


# ---------------------------------------------------------------------------
# Fixture 1: high-confidence auto-pass job
# ---------------------------------------------------------------------------

def auto_pass_job() -> Node:
    return Node(
        id="job_2606_claims_001",
        type=NodeType.EXTRACTION_JOB.value,
        label="Extract claims from 2606.13707",
        provenance=_prov(1.0, reviewed=True, notes="Traces reviewed; 2 clean claims"),
        properties={
            "job_id": "job_2606_claims_001",
            "paper_id": f"paper_{PAPER}",
            "extraction_type": ExtractionType.CLAIMS.value,
            "status": JobStatus.COMPLETED.value,
            "spawned_at": TS,
            "worker_id": "worker_abc123",
            "completed_at": "2026-07-26T15:35:20+00:00",
            "result_count": 2,
            "avg_confidence": 0.88,
            "traces": [
                Trace(
                    trace_id="tr_001",
                    decision_type=DecisionType.EXTRACT,
                    worker_id="worker_abc123",
                    confidence=0.91,
                    reason_code="EVIDENCE_IN_ABSTRACT",
                    reasoning_summary="Stated verbatim in abstract and restated in §4.",
                    input_refs=[f"paper_{PAPER}#abstract"],
                    output_refs=["claim_2606_001"],
                ),
                Trace(
                    trace_id="tr_002",
                    decision_type=DecisionType.SKIP,
                    worker_id="worker_abc123",
                    confidence=0.42,
                    reason_code="SPECULATIVE_FUTURE_WORK",
                    reasoning_summary="Appears only in Future Work; not a claim the paper supports.",
                    input_refs=[f"paper_{PAPER}#sec7"],
                ),
            ],
        },
    )


# ---------------------------------------------------------------------------
# Fixture 2: low-confidence job held for review
# ---------------------------------------------------------------------------

def held_for_review_job() -> Node:
    return Node(
        id="job_2606_concepts_001",
        type=NodeType.EXTRACTION_JOB.value,
        label="Extract concepts from 2606.13707",
        provenance=_prov(0.59, reviewed=True, notes="Awaiting reviewer decision"),
        properties={
            "job_id": "job_2606_concepts_001",
            "paper_id": f"paper_{PAPER}",
            "extraction_type": ExtractionType.CONCEPTS.value,
            "status": JobStatus.HELD.value,
            "spawned_at": TS,
            "worker_id": "worker_abc123",
            "completed_at": "2026-07-26T15:34:02+00:00",
            "result_count": 4,
            "avg_confidence": 0.59,
            "traces": [
                Trace(
                    trace_id="tr_010",
                    decision_type=DecisionType.ABSTAIN,
                    worker_id="worker_abc123",
                    confidence=0.51,
                    reason_code="AMBIGUOUS_TERM",
                    reasoning_summary="'multi-agent' used in two senses; cannot pick one.",
                    input_refs=[f"paper_{PAPER}#sec2"],
                ),
            ],
        },
    )


def review_task_pending() -> Node:
    """The review_task that fixture 2's hold produces."""
    return Node(
        id="review_2606_concepts_001",
        type=NodeType.REVIEW_TASK.value,
        label="Review concept extraction from 2606.13707",
        provenance=_prov(1.0, reviewed=False, method=ExtractionMethod.GATE_HOLD),
        properties={
            "task_id": "review_2606_concepts_001",
            "extraction_job_id": "job_2606_concepts_001",
            "status": ReviewStatus.PENDING.value,
            "created_at": "2026-07-26T15:34:03+00:00",
            "gate_reason": "LOW_CONFIDENCE: Confidence 59% below threshold 70%",
        },
    )


# ---------------------------------------------------------------------------
# Fixture 3: human-waived job
# ---------------------------------------------------------------------------

def human_waived_review_task() -> Node:
    return Node(
        id="review_2606_concepts_001",
        type=NodeType.REVIEW_TASK.value,
        label="Review concept extraction from 2606.13707 (waived)",
        provenance=_prov(1.0, reviewed=True, method=ExtractionMethod.HUMAN_ANNOTATION,
                         notes="Low-confidence 'multi-agent' concept confirmed by context"),
        properties={
            "task_id": "review_2606_concepts_001",
            "extraction_job_id": "job_2606_concepts_001",
            "status": ReviewStatus.APPROVED.value,
            "created_at": "2026-07-26T15:34:03+00:00",
            "gate_reason": "LOW_CONFIDENCE: Confidence 59% below threshold 70%",
            "reviewed_by": "parry.s.2324@gmail.com",
            "reviewed_at": "2026-07-26T16:15:00+00:00",
            "confidence_threshold_waived": True,
            "waiver_reason": "'multi-agent' is central to this paper; the low extraction "
                             "confidence reflected term ambiguity, not doubt about relevance.",
            "review_notes": "Approved with waiver. Extractor wording imprecise, concept correct.",
        },
    )


def human_waived_job() -> Node:
    """The underlying job after the waiver is applied — status APPROVED, still low confidence."""
    n = held_for_review_job()
    n.properties = dict(n.properties)
    n.properties["status"] = JobStatus.APPROVED.value
    n.provenance = _prov(0.59, reviewed=True, notes="Approved under waiver (see review task)")
    return n


def waived_graph() -> ResearchGraph:
    """
    Fixture 3 assembled with the link the gate needs to *see* the waiver:
    review_task --approved_for--> extraction_job.

    Schema nodes/edges are duck-compatible with what the gate reads, so this graph
    can be handed to `should_unlock_next_stage` directly.
    """
    job = human_waived_job()
    rt = human_waived_review_task()
    edge = Edge(rt.id, job.id, EdgeType.APPROVED_FOR.value,
                _prov(1.0, reviewed=True, method=ExtractionMethod.HUMAN_ANNOTATION))
    return ResearchGraph(nodes=[job, rt], edges=[edge])


def waived_graph_with_defect(defect: str) -> ResearchGraph:
    """Same waiver with one required element removed — must NOT be honored."""
    g = waived_graph()
    rt = [n for n in g.nodes if n.type == NodeType.REVIEW_TASK.value][0]
    rt.properties = dict(rt.properties)
    if defect == "no_reason":
        rt.properties["waiver_reason"] = ""
    elif defect == "no_reviewer":
        rt.properties["reviewed_by"] = ""
    elif defect == "not_approved":
        rt.properties["status"] = ReviewStatus.NEEDS_REVISION.value
    elif defect == "unreviewed":
        rt.provenance = _prov(1.0, reviewed=False, method=ExtractionMethod.HUMAN_ANNOTATION)
    else:
        raise ValueError(f"unknown defect {defect!r}")
    return g


# ---------------------------------------------------------------------------
# Fixture 4: conflict-marked claim pair
# ---------------------------------------------------------------------------

def conflict_claim_pair():
    a = Node(
        id="claim_2606_001",
        type=NodeType.CLAIM.value,
        label="hierarchical orchestration reduces coordination overhead",
        provenance=_prov(0.91, reviewed=True, method=ExtractionMethod.STRUCTURED_LLM),
        properties={
            "text": "Hierarchical orchestration reduces coordination overhead.",
            "subject": "hierarchical orchestration",
            "relation": "reduces",
            "object": "coordination overhead",
        },
    )
    b = Node(
        id="claim_2701_014",
        type=NodeType.CLAIM.value,
        label="hierarchical orchestration increases coordination overhead",
        provenance=Provenance(
            source_paper="2701.00912",
            extraction_method=ExtractionMethod.STRUCTURED_LLM.value,
            confidence=0.87,
            extracted_at=TS,
            human_reviewed=True,
        ),
        properties={
            "text": "Hierarchical orchestration increases coordination overhead at scale.",
            "subject": "hierarchical orchestration",
            "relation": "increases",
            "object": "coordination overhead",
        },
    )
    conflict = ConflictEdge(
        source_claim_id=a.id,
        target_claim_id=b.id,
        conflict_type=ConflictType.METHOD_DEPENDENT,
        severity=0.8,
        evidence="Both high-confidence, opposite polarity on the same subject/object. "
                 "Likely scope-dependent (small vs. large fleet) rather than a true contradiction.",
    )
    return a, b, conflict


# ---------------------------------------------------------------------------
# Assembled graph
# ---------------------------------------------------------------------------

def build_fixture_graph() -> ResearchGraph:
    job_pass = auto_pass_job()
    job_held = held_for_review_job()
    review = review_task_pending()
    claim_a, claim_b, conflict = conflict_claim_pair()

    paper = Node(
        id=f"paper_{PAPER}",
        type=NodeType.PAPER.value,
        label="Orchestration at Scale",
        provenance=_prov(1.0, reviewed=True, method=ExtractionMethod.METADATA),
        properties={"title": "Orchestration at Scale",
                    "url": f"https://arxiv.org/abs/{PAPER}"},
    )

    edges = [
        Edge(job_held.id, review.id, EdgeType.REQUIRES_REVIEW.value, _prov(1.0)),
        Edge(job_pass.id, job_held.id, EdgeType.UNLOCKS.value, _prov(1.0)),
        Edge(paper.id, claim_a.id, EdgeType.PRODUCES.value, _prov(1.0)),
        Edge(claim_a.id, claim_b.id, EdgeType.CONTRADICTS.value, _prov(0.8), strength=0.8),
    ]

    return ResearchGraph(
        nodes=[paper, job_pass, job_held, review, claim_a, claim_b],
        edges=edges,
        conflicts=[conflict],
    )
