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
from research_graph_workers import AdmissionResult, ExtractionDirective, WorkerSpawner
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


@dataclass
class ExecutionOutcome:
    """
    Realized facts about a spawned action's actual execution -- the
    telemetry a closed-loop policy re-evaluates against, as distinct from
    the *declared* ProposedAction it was authorized on before running.
    GAAT (arXiv 2604.05119) names exactly this gap: existing agent
    telemetry is collected but not wired back into real-time enforcement
    ("observe-but-do-not-act"). `ActionPolicy.authorize_outcome` closes
    that loop for this repo -- pre-action authorization decides whether a
    worker runs at all; post-execution authorization decides whether what
    it actually produced is allowed to land in the graph.
    """
    worker_status: str
    node_count: int
    avg_confidence: float


# A post-execution rule sees both the original declared action and what it
# actually produced; same (verdict, reason)-or-None contract as PolicyRule.
PostExecutionRule = Callable[[ProposedAction, ExecutionOutcome], Optional[Tuple[PolicyVerdict, str]]]


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

    def __init__(
        self,
        rules: Optional[List[Tuple[str, PolicyRule]]] = None,
        post_execution_rules: Optional[List[Tuple[str, PostExecutionRule]]] = None,
    ):
        self.rules: List[Tuple[str, PolicyRule]] = list(rules or [])
        self.post_execution_rules: List[Tuple[str, PostExecutionRule]] = list(
            post_execution_rules or [])
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

    def authorize_outcome(self, action: ProposedAction, outcome: ExecutionOutcome) -> PolicyDecision:
        """
        The closed-loop half of enforcement: `authorize()` evaluates a
        *declared* action before it runs; this evaluates what it *actually*
        produced, after the worker ran but before that output is admitted
        into the graph. Same precedence as `authorize()` (first BLOCK wins,
        else first ESCALATE, else ALLOWED) and the same `PolicyDecision`
        shape, reusing `action` (the original ProposedAction) so a decision
        about a realized outcome is still traceable to what was declared.
        Appended to the same `self.decisions` list as `authorize()` -- this
        policy's audit trail is every decision it made, pre- or
        post-execution, not two separate ledgers.
        """
        escalation: Optional[PolicyDecision] = None
        for name, rule in self.post_execution_rules:
            result = rule(action, outcome)
            if result is None:
                continue
            verdict, reason = result
            decision = PolicyDecision(verdict=verdict, reason=reason, rule_name=name, action=action)
            if verdict == PolicyVerdict.BLOCKED:
                self.decisions.append(decision)
                return decision
            if verdict == PolicyVerdict.ESCALATED and escalation is None:
                escalation = decision

        final = escalation or PolicyDecision(
            verdict=PolicyVerdict.ALLOWED, reason="no post-execution policy rule objected",
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
# BUILT-IN POST-EXECUTION RULE CONSTRUCTORS (the closed-loop half)
# ============================================================================

def block_low_average_confidence_outcome(floor: float) -> Tuple[str, PostExecutionRule]:
    """
    Even though the proposed action was authorized before it ran, block
    admission if what the worker actually produced falls short of a
    confidence floor -- closing the loop between declared intent and
    realized outcome, instead of only ever checking intent.
    """
    def rule(action: ProposedAction, outcome: ExecutionOutcome) -> Optional[Tuple[PolicyVerdict, str]]:
        if outcome.node_count > 0 and outcome.avg_confidence < floor:
            return (PolicyVerdict.BLOCKED,
                    f"realized avg confidence {outcome.avg_confidence:.2f} below "
                    f"post-execution floor {floor:.2f}")
        return None
    return "block_low_average_confidence_outcome", rule


def max_nodes_produced_ceiling(ceiling: int) -> Tuple[str, PostExecutionRule]:
    """
    Block admission if the worker actually produced more nodes than policy
    allows -- a real contract violation (a worker ignoring its own
    directive's max_results) rather than a hypothetical one, caught after
    the fact instead of only guarded against in the declared request.
    """
    def rule(action: ProposedAction, outcome: ExecutionOutcome) -> Optional[Tuple[PolicyVerdict, str]]:
        if outcome.node_count > ceiling:
            return (PolicyVerdict.BLOCKED,
                    f"worker produced {outcome.node_count} node(s), exceeding "
                    f"post-execution ceiling {ceiling}")
        return None
    return "max_nodes_produced_ceiling", rule


def escalate_on_worker_failure() -> Tuple[str, PostExecutionRule]:
    """
    A worker that reports failure after being authorized to run is itself
    a signal worth a human's attention, not just a dropped envelope --
    escalate rather than silently letting admission never happen.
    """
    def rule(action: ProposedAction, outcome: ExecutionOutcome) -> Optional[Tuple[PolicyVerdict, str]]:
        if outcome.worker_status == "failed":
            return (PolicyVerdict.ESCALATED,
                    f"worker reported failure for {action.paper_id} "
                    f"({action.extraction_type.value}); admission held pending review")
        return None
    return "escalate_on_worker_failure", rule


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


# ============================================================================
# CLOSED-LOOP ENFORCEMENT: authorize, run, THEN re-authorize before admitting
# ============================================================================

def _outcome_from_envelope(env: Any) -> ExecutionOutcome:
    confs = [n.provenance.confidence for n in env.nodes
             if n.provenance and n.provenance.confidence is not None]
    avg = (sum(confs) / len(confs)) if confs else 0.0
    return ExecutionOutcome(worker_status=env.worker_status,
                            node_count=len(env.nodes), avg_confidence=avg)


def authorize_execute_then_admit(
    spawner: WorkerSpawner,
    policy: ActionPolicy,
    worker: Any,
    paper_id: str,
    extraction_type: ExtractionType,
    text: str,
    confidence_floor: float = 0.0,
    max_results: Optional[int] = None,
    graph: Optional[ResearchGraph] = None,
) -> Tuple[PolicyDecision, Optional[PolicyDecision], Optional[AdmissionResult],
          Optional[ExtractionDirective], Optional[Any]]:
    """
    The full closed-loop path: authorize the declared action, run the
    worker only if that's ALLOWED, then re-authorize the *realized*
    outcome against `policy.post_execution_rules` before ever calling
    `spawner.admit()`. Closes the gap `authorize_then_spawn` alone leaves
    open -- that function's pre-action check can't see what a worker will
    actually produce, only what was declared. A pre-action BLOCKED/
    ESCALATED verdict behaves exactly as `authorize_then_spawn` already
    does (returned immediately, worker never runs). A post-execution
    BLOCKED/ESCALATED verdict means the worker DID run (its side effects,
    e.g. a real model call, already happened -- that can't be undone) but
    its output is never admitted into the graph: `spawner.admit()` is not
    called at all, so nothing it produced becomes a graph node.

    Returns `(pre_decision, post_decision, admission, directive, envelope)`.
    `directive`/`envelope` are returned (not just consumed internally) so a
    caller holding an ESCALATED `post_decision` can later call
    `approve_escalated_outcome(spawner, directive, envelope, post_decision,
    approved_by)` without re-running the worker -- the envelope was already
    produced once; approval only decides whether it's admitted. All of
    `post_decision`/`admission`/`directive`/`envelope` are `None` if the
    pre-action check didn't allow execution in the first place. `admission`
    is `None` (with the rest populated) if execution happened but the
    outcome was blocked or escalated before admission.
    """
    pre_decision, job, directive = authorize_then_spawn(
        spawner, policy, paper_id, extraction_type, confidence_floor, max_results, graph)
    if pre_decision.verdict != PolicyVerdict.ALLOWED:
        return pre_decision, None, None, None, None

    assert job is not None and directive is not None  # ALLOWED always spawns
    env = worker.run(directive, text)
    outcome = _outcome_from_envelope(env)
    post_decision = policy.authorize_outcome(pre_decision.action, outcome)

    if post_decision.verdict != PolicyVerdict.ALLOWED:
        if graph is not None:
            graph_memory.record_action_policy_decision(graph, job.id, post_decision)
        return pre_decision, post_decision, None, directive, env

    admission = spawner.admit(directive, env)
    if graph is not None:
        graph_memory.record_action_policy_decision(graph, job.id, post_decision)
    return pre_decision, post_decision, admission, directive, env


def approve_escalated_outcome(
    spawner: WorkerSpawner,
    directive: ExtractionDirective,
    env: Any,
    decision: PolicyDecision,
    approved_by: str,
    graph: Optional[ResearchGraph] = None,
) -> AdmissionResult:
    """
    A human approves a previously-ESCALATED post-execution decision,
    admitting the already-produced envelope now. Mirrors
    `approve_escalated_action`'s human-only-approval contract, one stage
    later in the pipeline: raises `ValueError` if `decision` wasn't
    genuinely an ESCALATED verdict. The envelope was already produced (the
    worker already ran) -- this only decides whether it's admitted.
    """
    if decision.verdict != PolicyVerdict.ESCALATED:
        raise ValueError(
            f"only an ESCALATED decision can be approved, got {decision.verdict.value!r}")
    admission = spawner.admit(directive, env)
    if graph is not None:
        approval = PolicyDecision(
            verdict=PolicyVerdict.ALLOWED,
            reason=f"escalated outcome approved by {approved_by}: {decision.reason}",
            rule_name="human_approval", action=decision.action)
        graph_memory.record_action_policy_decision(graph, admission.job_node.id, approval)
    return admission


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
