#!/usr/bin/env python3
"""
Phase 2: Production Gate Logic
Research graph workflow control plane.
Implements should_unlock_next_stage() with explicit reason codes + structured tracing.
"""

from dataclasses import dataclass, asdict, field
from typing import Callable, Dict, List, Tuple, Optional, Any, TYPE_CHECKING
from enum import Enum
from datetime import datetime
import json

if TYPE_CHECKING:
    # Type-checking only -- this module is deliberately schema-agnostic at
    # runtime (it defines its own local Node/Provenance stubs below and never
    # imports research_graph_schema), so this import has zero runtime effect.
    # It exists only so mypy can resolve the "ResearchGraph" forward references
    # used as a type hint throughout this file.
    from research_graph_schema import ResearchGraph

# ============================================================================
# REASON CODES (Explicit Gate Verdicts)
# ============================================================================

class GateReasonCode(Enum):
    """Deterministic gate verdicts."""
    ALLOWED = "ALLOWED"  # All checks passed, can advance
    ALLOWED_BY_WAIVER = "ALLOWED_BY_WAIVER"  # Advanced only because a human waived a gate
    SCHEMA_INVALID = "SCHEMA_INVALID"  # Required fields missing or malformed
    PROVENANCE_MISSING = "PROVENANCE_MISSING"  # No source information
    CLAIM_NOT_ENTAILED = "CLAIM_NOT_ENTAILED"  # Claim text not supported by its cited source
    REVIEW_REQUIRED = "REVIEW_REQUIRED"  # Human approval needed
    LOW_CONFIDENCE = "LOW_CONFIDENCE"  # Confidence below threshold
    CONFLICT_UNRESOLVED = "CONFLICT_UNRESOLVED"  # Contradictory claims exist
    DOWNSTREAM_NOT_ALLOWED = "DOWNSTREAM_NOT_ALLOWED"  # Node type cannot advance further


# ============================================================================
# STRUCTURED TRACING
# ============================================================================

@dataclass
class CheckTrace:
    """Single gate check, with tracing."""
    check_name: str  # "schema_valid", "confidence_above_threshold", etc.
    passed: bool
    reason: str  # Human-readable explanation
    reason_code: GateReasonCode
    evidence: Dict[str, Any] = field(default_factory=dict)  # Supporting data
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self):
        return {
            "check_name": self.check_name,
            "passed": self.passed,
            "reason": self.reason,
            "reason_code": self.reason_code.value,
            "evidence": self.evidence,
            "timestamp": self.timestamp
        }


@dataclass
class GateDecision:
    """Complete gate evaluation, with full trace."""
    node_id: str
    can_proceed: bool
    reason_code: GateReasonCode
    reason: str
    checks: List[CheckTrace]
    decision_timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self):
        return {
            "node_id": self.node_id,
            "can_proceed": self.can_proceed,
            "reason_code": self.reason_code.value,
            "reason": self.reason,
            "checks": [c.to_dict() for c in self.checks],
            "decision_timestamp": self.decision_timestamp,
            "summary": f"{sum(1 for c in self.checks if c.passed)} / {len(self.checks)} checks passed"
        }


# ============================================================================
# NODE & PROVENANCE STUBS (for testing)
# ============================================================================

@dataclass
class Provenance:
    source_paper: str
    extraction_method: str
    # Optional, not float: _check_confidence_above_threshold already treats a
    # missing confidence as LOW_CONFIDENCE (checks `is None` before use) --
    # this annotation just makes that already-defensive handling honest.
    confidence: Optional[float]
    extracted_at: str
    human_reviewed: bool = False
    review_notes: str = ""

    def to_dict(self):
        return asdict(self)


@dataclass
class Node:
    id: str
    type: str  # "paper", "claim", "concept", "extraction_job", "review_task"
    label: str
    provenance: Optional[Provenance] = None
    properties: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self):
        return {
            "id": self.id,
            "type": self.type,
            "label": self.label,
            "provenance": self.provenance.to_dict() if self.provenance else None,
            "properties": self.properties
        }


# ============================================================================
# PRODUCTION GATE LOGIC (Phase 2)
# ============================================================================

class WorkflowGate:
    """
    Production gate logic.
    Every decision is traced, every reason is explicit.
    """

    def __init__(
        self,
        confidence_threshold: float = 0.7,
        require_human_review: bool = True,
        detect_conflicts: bool = True,
        waiver_confidence_floor: float = 0.4,
        honor_waivers: bool = True,
        entailment_checker: Optional[Callable[["Node", Optional["ResearchGraph"]], bool]] = None,
    ):
        self.confidence_threshold = confidence_threshold
        self.require_human_review = require_human_review
        self.detect_conflicts = detect_conflicts
        # A waiver can rescue a below-threshold node, but not an arbitrarily bad one.
        # Without a floor the confidence gate is decorative: anything can be waived past it.
        self.waiver_confidence_floor = waiver_confidence_floor
        self.honor_waivers = honor_waivers
        # Pluggable claim-source verification (see claim_verification.py for a real,
        # deterministic default implementation). `None` — the default, and the only
        # mode every test written before this check existed exercises — makes
        # _check_claim_entailed a no-op pass for every node, so existing behavior is
        # unchanged unless a caller opts in explicitly.
        self.entailment_checker = entailment_checker
        self.decisions: List[GateDecision] = []

    def should_unlock_next_stage(
        self,
        node: Node,
        graph: Optional["ResearchGraph"] = None
    ) -> GateDecision:
        """
        Core gate logic: deterministic verdicts, one CheckTrace per check, run in
        a fixed order (schema, provenance, claim-entailment, confidence, human
        review, conflicts, downstream eligibility). Claim-entailment is a no-op
        pass unless the gate was constructed with an `entailment_checker`.

        Returns: GateDecision with full trace
        """

        traces: List[CheckTrace] = []

        # CHECK 1: Schema validity
        trace1 = self._check_schema_valid(node)
        traces.append(trace1)
        if not trace1.passed:
            decision = GateDecision(
                node_id=node.id,
                can_proceed=False,
                reason_code=GateReasonCode.SCHEMA_INVALID,
                reason=trace1.reason,
                checks=traces
            )
            self.decisions.append(decision)
            return decision

        # CHECK 2: Provenance present
        trace2 = self._check_provenance_present(node)
        traces.append(trace2)
        if not trace2.passed:
            decision = GateDecision(
                node_id=node.id,
                can_proceed=False,
                reason_code=GateReasonCode.PROVENANCE_MISSING,
                reason=trace2.reason,
                checks=traces
            )
            self.decisions.append(decision)
            return decision

        # CHECK 3: Claim entailed by its cited source (claim nodes only; a no-op
        # pass when no entailment_checker is configured -- see claim_verification.py)
        trace3 = self._check_claim_entailed(node, graph)
        traces.append(trace3)
        if not trace3.passed:
            decision = GateDecision(
                node_id=node.id,
                can_proceed=False,
                reason_code=GateReasonCode.CLAIM_NOT_ENTAILED,
                reason=trace3.reason,
                checks=traces
            )
            self.decisions.append(decision)
            return decision

        # CHECK 4: Confidence above threshold
        trace4 = self._check_confidence_above_threshold(node, graph)
        traces.append(trace4)
        if not trace4.passed:
            decision = GateDecision(
                node_id=node.id,
                can_proceed=False,
                reason_code=GateReasonCode.LOW_CONFIDENCE,
                reason=trace4.reason,
                checks=traces
            )
            self.decisions.append(decision)
            return decision

        # CHECK 5: Human review state
        trace5 = self._check_human_reviewed(node)
        traces.append(trace5)
        if not trace5.passed:
            decision = GateDecision(
                node_id=node.id,
                can_proceed=False,
                reason_code=GateReasonCode.REVIEW_REQUIRED,
                reason=trace5.reason,
                checks=traces
            )
            self.decisions.append(decision)
            return decision

        # CHECK 6: No unresolved conflicts
        trace6 = self._check_no_conflicts(node, graph)
        traces.append(trace6)
        if not trace6.passed:
            decision = GateDecision(
                node_id=node.id,
                can_proceed=False,
                reason_code=GateReasonCode.CONFLICT_UNRESOLVED,
                reason=trace6.reason,
                checks=traces
            )
            self.decisions.append(decision)
            return decision

        # CHECK 7: Downstream stage allowed
        trace7 = self._check_downstream_allowed(node)
        traces.append(trace7)
        if not trace7.passed:
            decision = GateDecision(
                node_id=node.id,
                can_proceed=False,
                reason_code=GateReasonCode.DOWNSTREAM_NOT_ALLOWED,
                reason=trace7.reason,
                checks=traces
            )
            self.decisions.append(decision)
            return decision

        # ALL CHECKS PASSED
        # A pass that depended on a human waiver is reported as ALLOWED_BY_WAIVER, not
        # ALLOWED — otherwise waived advancement is indistinguishable from earned
        # advancement in report(), and the bar drops silently over time.
        waived = [c for c in traces if c.reason_code == GateReasonCode.ALLOWED_BY_WAIVER]
        if waived:
            decision = GateDecision(
                node_id=node.id,
                can_proceed=True,
                reason_code=GateReasonCode.ALLOWED_BY_WAIVER,
                reason="All gate checks passed; " + "; ".join(c.reason for c in waived),
                checks=traces
            )
            self.decisions.append(decision)
            return decision

        decision = GateDecision(
            node_id=node.id,
            can_proceed=True,
            reason_code=GateReasonCode.ALLOWED,
            reason="All gate checks passed",
            checks=traces
        )
        self.decisions.append(decision)
        return decision

    # ========================================================================
    # INDIVIDUAL GATE CHECKS (Hard Rules)
    # ========================================================================

    def _check_schema_valid(self, node: Node) -> CheckTrace:
        """
        Schema validity: required fields for node type.
        """
        required_fields = {
            "extraction_job": ["job_id", "paper_id", "extraction_type", "status"],
            "review_task": ["task_id", "extraction_job_id", "status"],
            "claim": ["text"],
            "concept": ["text"],
            "paper": ["title", "url"],
        }

        required = required_fields.get(node.type, [])
        properties = node.properties or {}

        missing = [f for f in required if f not in properties]

        if missing:
            return CheckTrace(
                check_name="schema_valid",
                passed=False,
                reason=f"Node {node.id} ({node.type}) missing required fields: {', '.join(missing)}",
                reason_code=GateReasonCode.SCHEMA_INVALID,
                evidence={"required": required, "missing": missing}
            )

        return CheckTrace(
            check_name="schema_valid",
            passed=True,
            reason=f"Node {node.id} has all required fields",
            reason_code=GateReasonCode.ALLOWED,
            evidence={"node_type": node.type, "required": required}
        )

    def _check_provenance_present(self, node: Node) -> CheckTrace:
        """
        Provenance check: source, method, confidence all present.
        """
        if node.provenance is None:
            return CheckTrace(
                check_name="provenance_present",
                passed=False,
                reason=f"Node {node.id} has no provenance",
                reason_code=GateReasonCode.PROVENANCE_MISSING,
                evidence={"provenance": None}
            )

        missing = []
        if not node.provenance.source_paper:
            missing.append("source_paper")
        if not node.provenance.extraction_method:
            missing.append("extraction_method")
        if node.provenance.confidence is None:
            missing.append("confidence")

        if missing:
            return CheckTrace(
                check_name="provenance_present",
                passed=False,
                reason=f"Node {node.id} provenance missing: {', '.join(missing)}",
                reason_code=GateReasonCode.PROVENANCE_MISSING,
                evidence={"missing_fields": missing}
            )

        return CheckTrace(
            check_name="provenance_present",
            passed=True,
            reason=f"Node {node.id} has complete provenance",
            reason_code=GateReasonCode.ALLOWED,
            evidence={
                "source_paper": node.provenance.source_paper,
                "extraction_method": node.provenance.extraction_method,
                "confidence": node.provenance.confidence
            }
        )

    def _check_claim_entailed(self, node: Node, graph: Optional["ResearchGraph"] = None) -> CheckTrace:
        """
        Claim-source verification: does the claim's *text* actually get entailed
        by its cited source, or does it merely cite one?

        `_check_provenance_present` above only checks that `source_paper` is a
        non-empty string -- it says nothing about whether the source actually
        supports what the claim asserts. That gap is exactly what let
        qih_stress_corpus.py's `claim_light_angle_derives_gr` through: it cites
        two real, correctly-formatted sources, and neither one addresses the
        specific mechanism the claim asserts. Nothing in the gate itself caught
        that -- the claim was only held because a human set its confidence to
        0.08 by hand after independent research. This check exists to close
        that gap at the gate, not just in a human's notes.

        Deliberately a no-op pass (reason_code ALLOWED, evidence checked=False)
        unless the gate is explicitly constructed with an `entailment_checker`
        (see claim_verification.py for a real, deterministic default) -- every
        fixture and test written before this check existed relies on it never
        firing, so "not configured" has to behave as "not checked," never as
        "checked and always true." Only claim nodes have text worth entailing,
        so every other node type also passes automatically, configured or not.
        """
        if node.type != "claim":
            return CheckTrace(
                check_name="claim_entailed",
                passed=True,
                reason=f"Entailment check does not apply to node type '{node.type}'",
                reason_code=GateReasonCode.ALLOWED,
                evidence={"checked": False, "node_type": node.type}
            )

        if self.entailment_checker is None:
            return CheckTrace(
                check_name="claim_entailed",
                passed=True,
                reason="Entailment verification not configured (no entailment_checker set)",
                reason_code=GateReasonCode.ALLOWED,
                evidence={"checked": False}
            )

        checker_name = getattr(self.entailment_checker, "__name__", repr(self.entailment_checker))
        source_paper = node.provenance.source_paper if node.provenance else None
        entailed = bool(self.entailment_checker(node, graph))

        if not entailed:
            return CheckTrace(
                check_name="claim_entailed",
                passed=False,
                reason=(f"Node {node.id}'s claim text is not entailed by its cited "
                        f"source (per {checker_name})"),
                reason_code=GateReasonCode.CLAIM_NOT_ENTAILED,
                evidence={"checked": True, "source_paper": source_paper, "checker": checker_name}
            )

        return CheckTrace(
            check_name="claim_entailed",
            passed=True,
            reason=f"Node {node.id}'s claim text is entailed by its cited source (per {checker_name})",
            reason_code=GateReasonCode.ALLOWED,
            evidence={"checked": True, "source_paper": source_paper, "checker": checker_name}
        )

    def _find_waiver(self, node: Node, graph: Optional["ResearchGraph"]) -> Tuple[Optional[Any], List[str]]:
        """
        Locate a human confidence waiver for this node.

        Resolution order:
          1. an `approved_for` edge from a review_task to this node (the declared link)
          2. fallback: a review_task whose `extraction_job_id` back-references this job

        Returns (review_task_node, defects). A waiver with defects is NOT honored —
        an incomplete waiver is treated as no waiver, never as a pass. The defects are
        surfaced in the trace so a half-filled waiver is visible rather than silent.
        """
        if graph is None:
            return None, []

        nodes = list(getattr(graph, "nodes", []) or [])
        by_id = {n.id: n for n in nodes}
        job_id = (node.properties or {}).get("job_id") or node.id

        candidate = None
        for e in (getattr(graph, "edges", []) or []):
            if getattr(e, "type", None) == "approved_for" and getattr(e, "target", None) == node.id:
                candidate = by_id.get(getattr(e, "source", None))
                if candidate is not None:
                    break

        if candidate is None:
            for n in nodes:
                if n.type == "review_task" and (n.properties or {}).get("extraction_job_id") == job_id:
                    candidate = n
                    break

        if candidate is None:
            return None, []

        props = candidate.properties or {}
        defects: List[str] = []
        if not props.get("confidence_threshold_waived"):
            return None, []  # a review task that simply isn't a waiver — not a defect
        if props.get("status") != "approved":
            defects.append(f"review_task status is {props.get('status')!r}, not 'approved'")
        if not props.get("waiver_reason"):
            defects.append("waiver_reason is empty")
        if not props.get("reviewed_by"):
            defects.append("reviewed_by is empty — waiver has no accountable human")
        if candidate.provenance is None or not candidate.provenance.human_reviewed:
            defects.append("review_task is not itself marked human_reviewed")

        return candidate, defects

    def _check_confidence_above_threshold(
        self, node: Node, graph: Optional["ResearchGraph"] = None
    ) -> CheckTrace:
        """
        Confidence gate: confidence >= threshold, unless a valid human waiver exists
        and the confidence still clears the waiver floor.
        """
        if node.provenance is None or node.provenance.confidence is None:
            return CheckTrace(
                check_name="confidence_above_threshold",
                passed=False,
                reason=f"Node {node.id} has no confidence score",
                reason_code=GateReasonCode.LOW_CONFIDENCE,
                evidence={"confidence": None, "threshold": self.confidence_threshold}
            )

        conf = node.provenance.confidence
        if conf < self.confidence_threshold:
            waiver: Optional[Any] = None
            defects: List[str] = []
            if self.honor_waivers:
                waiver, defects = self._find_waiver(node, graph)

            if waiver is not None and not defects and conf >= self.waiver_confidence_floor:
                wp = waiver.properties or {}
                return CheckTrace(
                    check_name="confidence_above_threshold",
                    passed=True,
                    reason=(f"Confidence {conf:.0%} below threshold "
                            f"{self.confidence_threshold:.0%}, waived by "
                            f"{wp.get('reviewed_by')}: {wp.get('waiver_reason')}"),
                    reason_code=GateReasonCode.ALLOWED_BY_WAIVER,
                    evidence={
                        "confidence": conf,
                        "threshold": self.confidence_threshold,
                        "waiver_confidence_floor": self.waiver_confidence_floor,
                        "waived": True,
                        "waived_by": wp.get("reviewed_by"),
                        "waiver_reason": wp.get("waiver_reason"),
                        "review_task_id": waiver.id,
                        "original_gate_reason": wp.get("gate_reason"),
                    }
                )

            evidence: Dict[str, Any] = {
                "confidence": conf,
                "threshold": self.confidence_threshold,
                "gap": self.confidence_threshold - conf,
            }
            detail = ""
            if waiver is not None and defects:
                evidence["waiver_rejected"] = defects
                evidence["review_task_id"] = waiver.id
                detail = f" (waiver on {waiver.id} not honored: {'; '.join(defects)})"
            elif waiver is not None and conf < self.waiver_confidence_floor:
                evidence["waiver_rejected"] = ["below waiver floor"]
                evidence["waiver_confidence_floor"] = self.waiver_confidence_floor
                evidence["review_task_id"] = waiver.id
                detail = (f" (waiver on {waiver.id} not honored: {conf:.0%} is below the "
                          f"{self.waiver_confidence_floor:.0%} waiver floor)")

            return CheckTrace(
                check_name="confidence_above_threshold",
                passed=False,
                reason=(f"Confidence {conf:.0%} below threshold "
                        f"{self.confidence_threshold:.0%}{detail}"),
                reason_code=GateReasonCode.LOW_CONFIDENCE,
                evidence=evidence
            )

        return CheckTrace(
            check_name="confidence_above_threshold",
            passed=True,
            reason=f"Confidence {conf:.0%} meets threshold {self.confidence_threshold:.0%}",
            reason_code=GateReasonCode.ALLOWED,
            evidence={"confidence": conf, "threshold": self.confidence_threshold}
        )

    def _check_human_reviewed(self, node: Node) -> CheckTrace:
        """
        Human review gate: if required, must be reviewed.
        """
        if not self.require_human_review:
            return CheckTrace(
                check_name="human_reviewed",
                passed=True,
                reason="Human review not required (config)",
                reason_code=GateReasonCode.ALLOWED,
                evidence={"require_human_review": False}
            )

        if node.provenance is None or not node.provenance.human_reviewed:
            return CheckTrace(
                check_name="human_reviewed",
                passed=False,
                reason=f"Node {node.id} requires human review before advancing",
                reason_code=GateReasonCode.REVIEW_REQUIRED,
                evidence={"human_reviewed": False}
            )

        return CheckTrace(
            check_name="human_reviewed",
            passed=True,
            reason=f"Node {node.id} has been reviewed by human",
            reason_code=GateReasonCode.ALLOWED,
            evidence={"human_reviewed": True, "review_notes": node.provenance.review_notes}
        )

    def _check_no_conflicts(self, node: Node, graph: Optional["ResearchGraph"] = None) -> CheckTrace:
        """
        Conflict detection: does this node — or anything it produced — sit on an
        unresolved contradiction?

        The gate does not *find* conflicts; a detector does (Phase 3's
        detect_conflicts_in_graph, or a worker). The gate only refuses to advance
        past one that nobody has resolved.
        """
        if not self.detect_conflicts or graph is None:
            return CheckTrace(
                check_name="no_conflicts",
                passed=True,
                reason="Conflict checking not active for this evaluation",
                reason_code=GateReasonCode.ALLOWED,
                evidence={"checked": False}
            )

        # A job answers for what it produced, not just for itself.
        scope = {node.id}
        job_id = (node.properties or {}).get("job_id")
        if job_id:
            scope |= {e.target for e in (getattr(graph, "edges", []) or [])
                      if getattr(e, "type", None) == "produces"
                      and getattr(e, "source", None) == node.id}

        conflicts = [c for c in (getattr(graph, "conflicts", []) or [])
                     if not getattr(c, "resolved", False)
                     and (c.source_claim_id in scope or c.target_claim_id in scope)]

        if conflicts:
            return CheckTrace(
                check_name="no_conflicts",
                passed=False,
                reason=(f"{len(conflicts)} unresolved conflict(s) involving {node.id}: "
                        + "; ".join(f"{c.source_claim_id} vs {c.target_claim_id}"
                                    for c in conflicts[:3])),
                reason_code=GateReasonCode.CONFLICT_UNRESOLVED,
                evidence={"checked": True, "scope": sorted(scope), "conflicts": [
                    {"source": c.source_claim_id, "target": c.target_claim_id,
                     "type": getattr(c.conflict_type, "value", str(c.conflict_type)),
                     "severity": c.severity, "evidence": c.evidence}
                    for c in conflicts]}
            )

        return CheckTrace(
            check_name="no_conflicts",
            passed=True,
            reason=f"Node {node.id} has no unresolved conflicts",
            reason_code=GateReasonCode.ALLOWED,
            evidence={"checked": True, "scope": sorted(scope), "conflicts": []}
        )

    def _check_downstream_allowed(self, node: Node) -> CheckTrace:
        """
        State machine: can this node type flow to next stage?
        """
        allowed_transitions = {
            "extraction_job": True,  # Jobs always flow to review_task or next extraction
            "review_task": True,  # Reviews flow to approval edge or hold
            "paper": True,  # Papers flow to extractions
            "claim": False,  # Claims don't extract further (terminal)
            "concept": False,  # Concepts don't extract further (terminal)
        }

        if not allowed_transitions.get(node.type, False):
            return CheckTrace(
                check_name="downstream_allowed",
                passed=False,
                reason=f"Node type '{node.type}' is terminal; cannot advance further",
                reason_code=GateReasonCode.DOWNSTREAM_NOT_ALLOWED,
                evidence={"node_type": node.type}
            )

        return CheckTrace(
            check_name="downstream_allowed",
            passed=True,
            reason=f"Node type '{node.type}' can advance to next stage",
            reason_code=GateReasonCode.ALLOWED,
            evidence={"node_type": node.type}
        )

    def report(self) -> Dict[str, Any]:
        """Diagnostics over all decisions."""
        total = len(self.decisions)
        allowed = sum(1 for d in self.decisions if d.can_proceed)
        blocked = total - allowed

        by_reason: Dict[str, int] = {}
        for d in self.decisions:
            code = d.reason_code.value
            by_reason[code] = by_reason.get(code, 0) + 1

        waived = sum(1 for d in self.decisions
                     if d.reason_code == GateReasonCode.ALLOWED_BY_WAIVER)

        return {
            "total_decisions": total,
            "allowed": allowed,
            "blocked": blocked,
            # Advanced only because a human overrode a gate. Watch this number: a rising
            # waiver rate means the threshold is wrong or the extractor is, and the right
            # response is to fix one of those — not to keep waiving.
            "allowed_by_waiver": waived,
            "by_reason_code": by_reason,
            "last_10_decisions": [d.to_dict() for d in self.decisions[-10:]]
        }


# ============================================================================
# EXAMPLE: Phase 2 Test
# ============================================================================

if __name__ == "__main__":
    gate = WorkflowGate(confidence_threshold=0.7, require_human_review=True)

    print("=" * 70)
    print("TEST 1: Low confidence extraction → BLOCKED")
    print("=" * 70)

    node1 = Node(
        id="concept_001",
        type="concept",
        label="orchestration",
        provenance=Provenance(
            source_paper="2606.13707",
            extraction_method="keyword",
            confidence=0.65,  # Below 0.7 threshold
            extracted_at=datetime.now().isoformat(),
            human_reviewed=False
        ),
        properties={"text": "orchestration"}
    )

    decision1 = gate.should_unlock_next_stage(node1)
    print(json.dumps(decision1.to_dict(), indent=2))

    print("\n" + "=" * 70)
    print("TEST 2: High confidence, unreviewed → BLOCKED (review required)")
    print("=" * 70)

    node2 = Node(
        id="concept_002",
        type="concept",
        label="multi-agent",
        provenance=Provenance(
            source_paper="2606.13707",
            extraction_method="keyword",
            confidence=0.85,  # Above threshold
            extracted_at=datetime.now().isoformat(),
            human_reviewed=False  # ← NOT reviewed
        ),
        properties={"text": "multi-agent"}
    )

    decision2 = gate.should_unlock_next_stage(node2)
    print(json.dumps(decision2.to_dict(), indent=2))

    print("\n" + "=" * 70)
    print("TEST 3: High confidence, reviewed → ALLOWED")
    print("=" * 70)

    node3 = Node(
        id="concept_003",
        type="concept",
        label="governance",
        provenance=Provenance(
            source_paper="2606.13707",
            extraction_method="keyword",
            confidence=0.90,  # Above threshold
            extracted_at=datetime.now().isoformat(),
            human_reviewed=True,  # ← REVIEWED
            review_notes="Confirmed: governance is central to this paper"
        ),
        properties={"text": "governance"}
    )

    decision3 = gate.should_unlock_next_stage(node3)
    print(json.dumps(decision3.to_dict(), indent=2))

    print("\n" + "=" * 70)
    print("TEST 4: No provenance → BLOCKED")
    print("=" * 70)

    node4 = Node(
        id="concept_004",
        type="concept",
        label="unknown",
        provenance=None,  # ← No provenance
        properties={"text": "unknown"}
    )

    decision4 = gate.should_unlock_next_stage(node4)
    print(json.dumps(decision4.to_dict(), indent=2))

    print("\n" + "=" * 70)
    print("GATE STATISTICS")
    print("=" * 70)
    print(json.dumps(gate.report(), indent=2))
