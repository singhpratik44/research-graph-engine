#!/usr/bin/env python3
"""
Runtime policy enforcement: evaluate a proposed ACTION before it executes,
not just the claim/node it would eventually produce.

Every other check in this repo -- WorkflowGate, specialist_review's
verdicts -- gates a node AFTER a worker has already produced it: a claim
gets extracted, then the gate decides whether it can advance. That's
post-hoc data validation, not runtime action enforcement -- the action
(running the worker) has already happened by the time anything checks it.

ActionPolicy closes that specific gap. `authorize_then_spawn()` runs
BEFORE `WorkerSpawner.spawn()`/`worker.run()` are ever called, evaluating
the proposed extraction itself (paper_id, extraction_type,
confidence_floor, max_results) and returning one of three verdicts --
ALLOWED / ESCALATED / BLOCKED -- the same three-way decision space
real-time agent-action-enforcement research converges on (see this
session's research pass: centralized, per-action, auditable allow/block
enforcement is well-supported by multiple independent 2026 papers;
explicit human-escalation-as-a-runtime-primitive is thinner, most of
those papers gesture at it rather than formalize it -- ESCALATED here is
this repo's own concrete attempt at that primitive, not a claim that it's
drawn from a specific paper's mechanism). A BLOCKED action means the
worker is never invoked at all -- not merely that its output would later
be rejected.

Centralized, not per-caller: one ActionPolicy instance, built from
pluggable PolicyRule callables, can be shared across every
worker/paper/pipeline in a process -- policy changes take effect for
every caller without redeploying each one.

Purely additive. research_graph_workers.py, research_graph_gates.py,
graph_memory.py's existing functions, and specialist_review.py are
untouched at the call-signature level -- this module only calls into
WorkerSpawner.spawn() and (optionally) graph_memory.record_action_policy
_decision(), a new function added alongside this feature. A caller who
never constructs an ActionPolicy is completely unaffected: `authorize_
then_spawn` with the default empty-rules ActionPolicy() is behaviorally
identical to calling `spawner.spawn()` directly.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from research_graph_schema import ExtractionType, Node, ResearchGraph
from research_graph_workers import ExtractionDirective, WorkerSpawner
import graph_memory


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class PolicyVerdict(str, Enum):
    ALLOWED = "allowed"
    ESCALATED = "escalated"
    BLOCKED = "blocked"


@dataclass
class ProposedAction:
    """The thing being authorized -- a proposed extraction, before any worker runs."""
    paper_id: str
    extraction_type: ExtractionType
    confidence_floor: float = 0.0
    max_results: Optional[int] = None


@dataclass
class PolicyDecision:
    verdict: PolicyVerdict
    reason: str
    rule_name: str
    action: ProposedAction
    timestamp: str = field(default_factory=_now)

    @property
    def can_proceed(self) -> bool:
        return self.verdict in (PolicyVerdict.ALLOWED, PolicyVerdict.ESCALATED)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "verdict": self.verdict.value,
            "reason": self.reason,
            "rule_name": self.rule_name,
            "action": {
                "paper_id": self.action.paper_id,
                "extraction_type": self.action.extraction_type.value,
                "confidence_floor": self.action.confidence_floor,
                "max_results": self.action.max_results,
            },
            "timestamp": self.timestamp,
        }


# A rule returns None ("no opinion, defer to the next rule") or
# (verdict, reason) to render a verdict.
PolicyRule = Callable[[ProposedAction], Optional[Tuple[PolicyVerdict, str]]]


class ActionPolicy:
    """
    Centralized, pluggable action-level policy, evaluated per action.
    Empty rule list (the default) means every action is ALLOWED -- so
    constructing ActionPolicy() with no rules and using it is behaviorally
    identical to not using it at all.

    Rule precedence, same short-circuit spirit as WorkflowGate: the first
    rule to return BLOCKED wins immediately; otherwise the first rule to
    return ESCALATED wins; otherwise ALLOWED.
    """

    def __init__(self, rules: Optional[List[Tuple[str, PolicyRule]]] = None):
        self.rules: List[Tuple[str, PolicyRule]] = list(rules or [])
        self.decisions: List[PolicyDecision] = []

    def authorize(self, action: ProposedAction) -> PolicyDecision:
        escalation: Optional[PolicyDecision] = None
        for name, rule in self.rules:
            outcome = rule(action)
            if outcome is None:
                continue
            verdict, reason = outcome
            decision = PolicyDecision(verdict=verdict, reason=reason, rule_name=name, action=action)
            if verdict == PolicyVerdict.BLOCKED:
                self.decisions.append(decision)
                return decision
            if verdict == PolicyVerdict.ESCALATED and escalation is None:
                escalation = decision

        final = escalation or PolicyDecision(
            verdict=PolicyVerdict.ALLOWED, reason="no policy rule objected",
            rule_name="default", action=action)
        self.decisions.append(final)
        return final

    def report(self) -> Dict[str, Any]:
        """Diagnostics over all decisions -- same shape/spirit as WorkflowGate.report()."""
        total = len(self.decisions)
        by_verdict: Dict[str, int] = {}
        for d in self.decisions:
            by_verdict[d.verdict.value] = by_verdict.get(d.verdict.value, 0) + 1
        return {
            "total_decisions": total,
            "by_verdict": by_verdict,
            "last_10_decisions": [d.to_dict() for d in self.decisions[-10:]],
        }


# ============================================================================
# BUILT-IN RULE CONSTRUCTORS (pure, deterministic)
# ============================================================================

def deny_extraction_types(denied: Set[ExtractionType]) -> Tuple[str, PolicyRule]:
    """Never allow the given extraction types to run at all."""
    def rule(action: ProposedAction) -> Optional[Tuple[PolicyVerdict, str]]:
        if action.extraction_type in denied:
            return (PolicyVerdict.BLOCKED,
                    f"{action.extraction_type.value} extraction is denied by policy")
        return None
    return "deny_extraction_types", rule


def require_escalation_for(types: Set[ExtractionType]) -> Tuple[str, PolicyRule]:
    """Require human pre-approval before these extraction types are allowed to run."""
    def rule(action: ProposedAction) -> Optional[Tuple[PolicyVerdict, str]]:
        if action.extraction_type in types:
            return (PolicyVerdict.ESCALATED,
                    f"{action.extraction_type.value} extraction requires human pre-approval")
        return None
    return "require_escalation_for", rule


def max_results_ceiling(ceiling: int) -> Tuple[str, PolicyRule]:
    """Block a request for more results than policy allows in one action."""
    def rule(action: ProposedAction) -> Optional[Tuple[PolicyVerdict, str]]:
        if action.max_results is not None and action.max_results > ceiling:
            return (PolicyVerdict.BLOCKED,
                    f"max_results {action.max_results} exceeds policy ceiling {ceiling}")
        return None
    return "max_results_ceiling", rule


# ============================================================================
# THE ENFORCEMENT POINT
# ============================================================================

def authorize_then_spawn(
    spawner: WorkerSpawner,
    policy: ActionPolicy,
    paper_id: str,
    extraction_type: ExtractionType,
    confidence_floor: float = 0.0,
    max_results: Optional[int] = None,
    graph: Optional[ResearchGraph] = None,
) -> Tuple[PolicyDecision, Optional[Node], Optional[ExtractionDirective]]:
    """
    Authorize the proposed action BEFORE spawner.spawn() is ever called.
    Only an ALLOWED verdict spawns immediately -- both BLOCKED and
    ESCALATED mean spawn() never runs here at all, no job node is
    created, no worker is invoked. That's the property that distinguishes
    this from WorkflowGate: that gate decides whether an already-produced
    claim can advance; this decides whether the extraction happens in the
    first place. ESCALATED is not merely a label on an action that
    proceeds anyway -- it's genuinely held, exactly like BLOCKED, until a
    human calls approve_escalated_action() on this same decision. The
    difference between the two is what a human can do about them: an
    ESCALATED action can be approved into existence; a BLOCKED one can't
    (the policy said no, not "ask a human").

    `graph` (default None): when given, the decision is persisted as
    durable audit evidence via graph_memory.record_action_policy_decision
    -- consistent audit evidence generation being the other half of the
    "runtime policy enforcement" pattern, not just the allow/block
    decision itself. Omitting `graph` skips recording entirely (e.g. for
    a caller that only wants the in-memory decision).
    """
    action = ProposedAction(paper_id, extraction_type, confidence_floor, max_results)
    decision = policy.authorize(action)

    if decision.verdict != PolicyVerdict.ALLOWED:
        if graph is not None:
            subject_ref = f"action_{paper_id}_{extraction_type.value}_{len(policy.decisions)}"
            graph_memory.record_action_policy_decision(graph, subject_ref, decision)
        return decision, None, None

    job, directive = spawner.spawn(paper_id, extraction_type, confidence_floor, max_results)
    if graph is not None:
        # A real job now exists -- link the audit record to it (DERIVED_FROM),
        # not a synthetic id, so "why was this job allowed to start" is
        # answerable from the job node itself.
        graph_memory.record_action_policy_decision(graph, job.id, decision)
    return decision, job, directive


def approve_escalated_action(
    spawner: WorkerSpawner,
    decision: PolicyDecision,
    approved_by: str,
    graph: Optional[ResearchGraph] = None,
) -> Tuple[Node, ExtractionDirective]:
    """
    A human approves a previously-ESCALATED decision, allowing the action
    it describes to actually spawn now. Raises ValueError if `decision`
    wasn't genuinely an ESCALATED verdict -- approval is meaningless for
    an ALLOWED action (it already spawned) or a BLOCKED one (the policy
    said no; that's not a human's call to override here).
    """
    if decision.verdict != PolicyVerdict.ESCALATED:
        raise ValueError(
            f"only an ESCALATED decision can be approved, got {decision.verdict.value!r}")
    action = decision.action
    job, directive = spawner.spawn(action.paper_id, action.extraction_type,
                                   action.confidence_floor, action.max_results)
    if graph is not None:
        approval = PolicyDecision(
            verdict=PolicyVerdict.ALLOWED,
            reason=f"escalation approved by {approved_by}: {decision.reason}",
            rule_name="human_approval", action=action)
        graph_memory.record_action_policy_decision(graph, job.id, approval)
    return job, directive


if __name__ == "__main__":
    from research_graph_schema import ResearchGraph as _RG

    graph = _RG()
    spawner = WorkerSpawner(graph)
    policy = ActionPolicy(rules=[
        deny_extraction_types({ExtractionType.CONFLICTS}),
        require_escalation_for({ExtractionType.BENCHMARKS}),
        max_results_ceiling(50),
    ])

    escalated_decision = None
    for extraction_type in (ExtractionType.CLAIMS, ExtractionType.BENCHMARKS, ExtractionType.CONFLICTS):
        decision, job, directive = authorize_then_spawn(
            spawner, policy, "paper_demo_001", extraction_type, graph=graph)
        print(f"{extraction_type.value:12s} -> {decision.verdict.value:9s} "
              f"({decision.rule_name}): {decision.reason}")
        print(f"{'':12s}    job spawned: {job is not None}")
        if decision.verdict == PolicyVerdict.ESCALATED:
            escalated_decision = decision

    if escalated_decision is not None:
        job, directive = approve_escalated_action(
            spawner, escalated_decision, approved_by="parry.s.2324@gmail.com", graph=graph)
        print(f"\nafter human approval: job spawned={job is not None}, job_id={job.id}")

    print(f"\n{policy.report()}")
