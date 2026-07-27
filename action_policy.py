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
from task_graph import TaskDAG
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
    # Every rule that had an opinion on this action (returned non-None), not
    # just the one that won precedence -- (rule_name, verdict_value, reason)
    # triples. AgenticRei (arXiv 2606.19464) argues runtime policy engines
    # need meta-policy conflict resolution as a visible, auditable fact, not
    # just a silently-applied precedence order. Empty for a decision where
    # only one rule (or zero) fired -- the common case, and the same shape
    # every existing decision already has (this field defaults empty, so no
    # existing construction of PolicyDecision needs to change).
    all_rule_verdicts: List[Tuple[str, str, str]] = field(default_factory=list)

    @property
    def can_proceed(self) -> bool:
        return self.verdict in (PolicyVerdict.ALLOWED, PolicyVerdict.ESCALATED)

    @property
    def has_conflicting_rules(self) -> bool:
        """True when more than one distinct verdict was rendered by the
        rules that fired on this action -- a real meta-policy conflict
        (e.g. one rule would ESCALATE, another would BLOCK), not just
        multiple rules agreeing on the same verdict."""
        return len({v for _, v, _ in self.all_rule_verdicts}) > 1

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
            "all_rule_verdicts": [list(v) for v in self.all_rule_verdicts],
            "has_conflicting_rules": self.has_conflicting_rules,
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


@dataclass
class Obligation:
    """
    A standing duty a rendered PolicyDecision creates -- "if this fires, X
    must happen (or be explicitly waived)" -- distinct from the verdict
    itself. AgenticRei (arXiv 2606.19464) names obligation-lifecycle
    management and dispensations (governed waivers) as primitives that
    XACML/Rego/Cedar-style permit/prohibit policies don't model on their
    own; ALLOWED/ESCALATED/BLOCKED alone can't represent "this was allowed,
    AND someone must be notified within N steps."

    `status` moves pending -> fulfilled (someone did the required thing) or
    pending -> dispensed (a human explicitly waived it, on the record) --
    never silently dropped or left ambiguous.
    """
    obligation_id: str
    description: str
    rule_name: str
    decision: PolicyDecision
    status: str = "pending"  # "pending" | "fulfilled" | "dispensed"
    created_at: str = field(default_factory=_now)
    resolved_at: Optional[str] = None
    resolved_by: Optional[str] = None
    resolution_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "obligation_id": self.obligation_id,
            "description": self.description,
            "rule_name": self.rule_name,
            "decision": self.decision.to_dict(),
            "status": self.status,
            "created_at": self.created_at,
            "resolved_at": self.resolved_at,
            "resolved_by": self.resolved_by,
            "resolution_note": self.resolution_note,
        }


# An obligation rule inspects a rendered PolicyDecision (pre- or
# post-execution) and optionally returns a description string naming the
# duty it creates; None means this decision creates no obligation.
ObligationRule = Callable[[PolicyDecision], Optional[str]]


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
        obligation_rules: Optional[List[Tuple[str, ObligationRule]]] = None,
    ):
        self.rules: List[Tuple[str, PolicyRule]] = list(rules or [])
        self.post_execution_rules: List[Tuple[str, PostExecutionRule]] = list(
            post_execution_rules or [])
        self.obligation_rules: List[Tuple[str, ObligationRule]] = list(obligation_rules or [])
        self.decisions: List[PolicyDecision] = []
        self.obligations: List[Obligation] = []
        self._obligation_seq = 0

    def _check_obligations(self, decision: PolicyDecision) -> List[Obligation]:
        """
        Run every obligation_rule against a just-rendered decision, creating
        a pending Obligation for each one that names a duty. Empty
        `obligation_rules` (the default) means this never creates anything
        -- zero behavior change for any caller who doesn't opt in.
        """
        created: List[Obligation] = []
        for name, rule in self.obligation_rules:
            description = rule(decision)
            if description is None:
                continue
            self._obligation_seq += 1
            obligation = Obligation(
                obligation_id=f"obl_{self._obligation_seq:04d}",
                description=description, rule_name=name, decision=decision)
            self.obligations.append(obligation)
            created.append(obligation)
        return created

    def authorize(self, action: ProposedAction) -> PolicyDecision:
        escalation: Optional[PolicyDecision] = None
        fired: List[Tuple[str, str, str]] = []
        for name, rule in self.rules:
            outcome = rule(action)
            if outcome is None:
                continue
            verdict, reason = outcome
            fired.append((name, verdict.value, reason))
            decision = PolicyDecision(verdict=verdict, reason=reason, rule_name=name,
                                      action=action, all_rule_verdicts=list(fired))
            if verdict == PolicyVerdict.BLOCKED:
                self.decisions.append(decision)
                self._check_obligations(decision)
                return decision
            if verdict == PolicyVerdict.ESCALATED and escalation is None:
                escalation = decision

        final = escalation or PolicyDecision(
            verdict=PolicyVerdict.ALLOWED, reason="no policy rule objected",
            rule_name="default", action=action)
        final.all_rule_verdicts = list(fired)
        self.decisions.append(final)
        self._check_obligations(final)
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
        fired: List[Tuple[str, str, str]] = []
        for name, rule in self.post_execution_rules:
            result = rule(action, outcome)
            if result is None:
                continue
            verdict, reason = result
            fired.append((name, verdict.value, reason))
            decision = PolicyDecision(verdict=verdict, reason=reason, rule_name=name,
                                      action=action, all_rule_verdicts=list(fired))
            if verdict == PolicyVerdict.BLOCKED:
                self.decisions.append(decision)
                self._check_obligations(decision)
                return decision
            if verdict == PolicyVerdict.ESCALATED and escalation is None:
                escalation = decision

        final = escalation or PolicyDecision(
            verdict=PolicyVerdict.ALLOWED, reason="no post-execution policy rule objected",
            rule_name="default", action=action)
        final.all_rule_verdicts = list(fired)
        self.decisions.append(final)
        self._check_obligations(final)
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
# BUILT-IN OBLIGATION RULE CONSTRUCTORS
# ============================================================================

def notify_on_verdict(verdicts: Set[PolicyVerdict], description: str) -> Tuple[str, ObligationRule]:
    """
    Create a standing notify/log obligation whenever a rendered decision's
    verdict is one of `verdicts` -- e.g. "every BLOCKED conflicts action
    must be reported to the paper's owning team within one business day."
    The obligation is a fact to be fulfilled or explicitly dispensed later
    (see `fulfill_obligation`/`dispense_obligation`); creating it here never
    blocks or alters the decision it's attached to.
    """
    def rule(decision: PolicyDecision) -> Optional[str]:
        if decision.verdict in verdicts:
            return description
        return None
    return "notify_on_verdict", rule


# ============================================================================
# OBLIGATION LIFECYCLE (fulfill or dispense -- never a silent drop)
# ============================================================================

def _find_obligation(policy: ActionPolicy, obligation_id: str) -> Obligation:
    for o in policy.obligations:
        if o.obligation_id == obligation_id:
            return o
    raise KeyError(f"no such obligation: {obligation_id!r}")


def fulfill_obligation(policy: ActionPolicy, obligation_id: str, evidence: str = "") -> Obligation:
    """Mark a pending obligation fulfilled -- someone did the required thing.
    Raises if the obligation is already resolved (fulfilled or dispensed) --
    resolution happens exactly once, not overwritten."""
    obligation = _find_obligation(policy, obligation_id)
    if obligation.status != "pending":
        raise ValueError(f"obligation {obligation_id!r} is already {obligation.status!r}")
    obligation.status = "fulfilled"
    obligation.resolved_at = _now()
    obligation.resolution_note = evidence
    return obligation


def dispense_obligation(
    policy: ActionPolicy, obligation_id: str, dispensed_by: str, reason: str,
) -> Obligation:
    """
    A human explicitly waives a pending obligation, on the record -- never
    a silent drop. Distinct from fulfillment: the duty was never carried
    out, but a human decided, with a named reason, that it doesn't need to
    be -- the same "waiver, not silence" discipline `WorkflowGate`'s
    ALLOWED_BY_WAIVER already applies to gate decisions, applied here to
    obligations instead.
    """
    obligation = _find_obligation(policy, obligation_id)
    if obligation.status != "pending":
        raise ValueError(f"obligation {obligation_id!r} is already {obligation.status!r}")
    obligation.status = "dispensed"
    obligation.resolved_at = _now()
    obligation.resolved_by = dispensed_by
    obligation.resolution_note = reason
    return obligation


def pending_obligations(policy: ActionPolicy) -> List[Obligation]:
    """Every obligation this policy has created that's neither fulfilled nor dispensed yet."""
    return [o for o in policy.obligations if o.status == "pending"]


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


# ============================================================================
# INTENT-LEVEL GOVERNANCE (a checkpoint upstream of planning itself)
# ============================================================================
#
# Everything above authorizes one PROPOSED ACTION (a single extraction) --
# structurally the same checkpoint CUGA (2026, IBM Research) calls the
# tool-call boundary. CUGA's distinguishing piece this repo didn't have
# yet is a checkpoint upstream of THAT: an "Intent Guard" evaluating a
# whole planned run's intent -- how many extractions, of what types, for
# what paper -- BEFORE a task_graph.TaskDAG (the plan itself) is even
# constructed. This is genuinely new machinery, not an extension of
# ActionPolicy: an Intent describes a planned RUN, not a single action,
# and IntentPolicy's enforcement point holds the DAG builder itself, not
# a worker. Reuses PolicyVerdict (the same three-way ALLOWED/ESCALATED/
# BLOCKED space) rather than inventing a fourth verdict vocabulary.
#
# Purely additive: nothing above is modified, and nothing calls this
# automatically -- a caller who never constructs an IntentPolicy is
# completely unaffected.

@dataclass
class Intent:
    """A planned run, described BEFORE any TaskDAG or job exists for it."""
    paper_id: str
    planned_extraction_types: List[ExtractionType]
    requested_by: str = ""


@dataclass
class IntentDecision:
    verdict: PolicyVerdict
    reason: str
    rule_name: str
    intent: Intent
    timestamp: str = field(default_factory=_now)

    @property
    def can_proceed(self) -> bool:
        return self.verdict in (PolicyVerdict.ALLOWED, PolicyVerdict.ESCALATED)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "verdict": self.verdict.value,
            "reason": self.reason,
            "rule_name": self.rule_name,
            "intent": {
                "paper_id": self.intent.paper_id,
                "planned_extraction_types": [t.value for t in self.intent.planned_extraction_types],
                "requested_by": self.intent.requested_by,
            },
            "timestamp": self.timestamp,
        }


IntentRule = Callable[[Intent], Optional[Tuple[PolicyVerdict, str]]]


class IntentPolicy:
    """
    Same pluggable-rules, same precedence (first BLOCK wins, else first
    ESCALATE, else ALLOWED) as `ActionPolicy`, but evaluated once per
    planned run instead of once per action. Empty rules (the default)
    allows every intent -- constructing `IntentPolicy()` and using it is
    behaviorally identical to not using it at all.
    """

    def __init__(self, rules: Optional[List[Tuple[str, IntentRule]]] = None):
        self.rules: List[Tuple[str, IntentRule]] = list(rules or [])
        self.decisions: List[IntentDecision] = []

    def authorize(self, intent: Intent) -> IntentDecision:
        escalation: Optional[IntentDecision] = None
        for name, rule in self.rules:
            outcome = rule(intent)
            if outcome is None:
                continue
            verdict, reason = outcome
            decision = IntentDecision(verdict=verdict, reason=reason, rule_name=name, intent=intent)
            if verdict == PolicyVerdict.BLOCKED:
                self.decisions.append(decision)
                return decision
            if verdict == PolicyVerdict.ESCALATED and escalation is None:
                escalation = decision

        final = escalation or IntentDecision(
            verdict=PolicyVerdict.ALLOWED, reason="no intent rule objected",
            rule_name="default", intent=intent)
        self.decisions.append(final)
        return final

    def report(self) -> Dict[str, Any]:
        total = len(self.decisions)
        by_verdict: Dict[str, int] = {}
        for d in self.decisions:
            by_verdict[d.verdict.value] = by_verdict.get(d.verdict.value, 0) + 1
        return {"total_decisions": total, "by_verdict": by_verdict,
                "last_10_decisions": [d.to_dict() for d in self.decisions[-10:]]}


def deny_intent_extraction_types(denied: Set[ExtractionType]) -> Tuple[str, IntentRule]:
    """Block a planned run outright if it includes any denied extraction type."""
    def rule(intent: Intent) -> Optional[Tuple[PolicyVerdict, str]]:
        hit = denied & set(intent.planned_extraction_types)
        if hit:
            return (PolicyVerdict.BLOCKED,
                    f"planned run includes denied extraction type(s): "
                    f"{sorted(t.value for t in hit)}")
        return None
    return "deny_intent_extraction_types", rule


def require_escalation_for_intent_types(types: Set[ExtractionType]) -> Tuple[str, IntentRule]:
    """Require human pre-approval before a run planning any of these types starts."""
    def rule(intent: Intent) -> Optional[Tuple[PolicyVerdict, str]]:
        hit = types & set(intent.planned_extraction_types)
        if hit:
            return (PolicyVerdict.ESCALATED,
                    f"planned run includes extraction type(s) requiring pre-approval: "
                    f"{sorted(t.value for t in hit)}")
        return None
    return "require_escalation_for_intent_types", rule


def max_planned_extractions_ceiling(ceiling: int) -> Tuple[str, IntentRule]:
    """Block a run that plans more distinct extraction types in one intent than policy allows."""
    def rule(intent: Intent) -> Optional[Tuple[PolicyVerdict, str]]:
        count = len(intent.planned_extraction_types)
        if count > ceiling:
            return (PolicyVerdict.BLOCKED,
                    f"planned run includes {count} extraction type(s), "
                    f"exceeding policy ceiling {ceiling}")
        return None
    return "max_planned_extractions_ceiling", rule


def authorize_intent_then_build_dag(
    intent_policy: IntentPolicy,
    intent: Intent,
    dag_builder: Callable[[], TaskDAG],
) -> Tuple[IntentDecision, Optional[TaskDAG]]:
    """
    The enforcement point: authorize the whole planned run BEFORE
    `dag_builder()` is ever called. Only ALLOWED calls it -- a BLOCKED or
    ESCALATED intent means no `TaskDAG` is constructed at all, not merely
    that one gets built and then discarded. This is the "upstream of
    planning" checkpoint CUGA names: by the time `ActionPolicy.authorize()`
    would ever run (per proposed action), a BLOCKED intent here has
    already prevented the plan itself from existing.
    """
    decision = intent_policy.authorize(intent)
    if decision.verdict != PolicyVerdict.ALLOWED:
        return decision, None
    return decision, dag_builder()


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
