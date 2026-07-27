#!/usr/bin/env python3
"""
Specialist agent split: extractor, schema validator, conflict checker,
reviewer/judge -- bounded specialists with explicit handoffs over a
task_graph.TaskDAG, not many freely-chatting agents.

Closes gap_multidim_review (literature_corpus.py, 12 papers -- the corpus's
best-attested gap): a single scalar ReviewStatus/confidence can't represent
multiple independent reviewer signals before a waiver. This module reconciles
four bounded, always-completed specialist verdicts on one extraction job into
a SpecialistPipelineReport, instead of collapsing them into the single
short-circuited GateDecision.

Purely additive. research_graph_gates.py, research_graph_workers.py,
task_graph.py, and graph_orchestrator.py are not modified -- this module
only calls into them. research_graph_schema.py gained one closed-enum
member (MemoryKind.CONFIDENCE_DIVERGENCE) and graph_memory.py gained
confidence-divergence recording/reading -- both purely additive, added to
support the optional confidence-divergence check below (opt-in via
run_specialist_pipeline's divergence_threshold, default None, zero
behavior change for every existing caller).

Two of the four roles were already "built" per graph_orchestrator.py's own
docstring, just not surfaced as an explicit, observable verdict:
  - schema validator: research_graph_schema.validate_node()
  - conflict checker:  research_graph_schema.detect_conflicts_in_graph()
This module wraps those same pure functions in SpecialistVerdicts rather
than reimplementing them, and adds the two roles that didn't exist yet
(extractor, reviewer/judge).

SpecialistVerdict is deliberately NOT folded into GateDecision.checks:
GateDecision is the one short-circuited governing verdict the gate computes;
a SpecialistVerdict is one bounded role's independent, always-completed read.
Conflating them would require inventing GateReasonCode members for roles the
gate itself has no opinion on, and would touch research_graph_gates.py's
closed enum contract for no reason -- these answer different questions.

DAG shape (real concurrency via task_graph.Scheduler):

    extract --> conflict_check --\
            \-> schema_validate --+--> reviewer_judge

conflict_check and schema_validate depend only on extract and run
concurrently; reviewer_judge depends on both.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from research_graph_schema import (
    ExtractionType, Node, ResearchGraph, ValidationError,
    detect_conflicts_in_graph, validate_node,
)
import research_graph_gates as gates
import graph_memory
from research_graph_workers import (
    AdmissionResult, ExtractionDirective, PRODUCES_NODE_TYPE, ReferenceWorker,
    ResultEnvelope, WorkerSpawner,
)
from task_graph import RunResult, Scheduler, TaskDAG, TaskSpan, TaskStatus

ROLE_EXTRACTOR = "extractor"
ROLE_SCHEMA_VALIDATOR = "schema_validator"
ROLE_CONFLICT_CHECKER = "conflict_checker"
ROLE_REVIEWER_JUDGE = "reviewer_judge"

ROLES = (ROLE_EXTRACTOR, ROLE_SCHEMA_VALIDATOR, ROLE_CONFLICT_CHECKER, ROLE_REVIEWER_JUDGE)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ============================================================================
# DATA MODEL
# ============================================================================

@dataclass
class SpecialistVerdict:
    """One bounded specialist role's independent, always-completed read."""
    role: str
    passed: bool
    detail: str
    confidence: Optional[float] = None
    evidence: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "role": self.role,
            "passed": self.passed,
            "detail": self.detail,
            "confidence": self.confidence,
            "evidence": self.evidence,
            "timestamp": self.timestamp,
        }


@dataclass
class SpecialistPipelineReport:
    """Every specialist's verdict on one extraction job, plus the real admission."""
    paper_id: str
    job_id: str
    extraction_type: str
    verdicts: List[SpecialistVerdict] = field(default_factory=list)
    admission: Optional[AdmissionResult] = None
    disagreements: List[Node] = field(default_factory=list)
    run_result: Optional[RunResult] = None
    # Confidence-divergence memory records (graph_memory.CONFIDENCE_DIVERGENCE)
    # written when a re-derived candidate's confidence diverged from its
    # already-admitted prior reading by at least divergence_threshold.
    # Always empty unless run_specialist_pipeline's divergence_threshold is set.
    confidence_divergences: List[Node] = field(default_factory=list)
    # The extractor's raw envelope, kept for a caller that wants to resume a
    # partially-failed run (see resume_specialist_pipeline) without
    # re-invoking the worker for tasks that already completed successfully.
    envelope: Optional[ResultEnvelope] = None

    def verdict_for(self, role: str) -> Optional[SpecialistVerdict]:
        return next((v for v in self.verdicts if v.role == role), None)

    @property
    def all_specialist_checks_passed(self) -> bool:
        return bool(self.verdicts) and all(v.passed for v in self.verdicts)

    @property
    def held_for_review(self) -> bool:
        return bool(self.admission and self.admission.review_task is not None)

    @property
    def has_disagreement(self) -> bool:
        return bool(self.disagreements)

    @property
    def has_confidence_divergence(self) -> bool:
        return bool(self.confidence_divergences)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "paper_id": self.paper_id,
            "job_id": self.job_id,
            "extraction_type": self.extraction_type,
            "verdicts": [v.to_dict() for v in self.verdicts],
            "all_specialist_checks_passed": self.all_specialist_checks_passed,
            "held_for_review": self.held_for_review,
            "has_disagreement": self.has_disagreement,
            "has_confidence_divergence": self.has_confidence_divergence,
            "admission": self.admission.to_dict() if self.admission else None,
            "disagreements": [d.id for d in self.disagreements],
            "confidence_divergences": [d.id for d in self.confidence_divergences],
        }


# ============================================================================
# VERDICT BUILDERS (pure -- no graph mutation)
# ============================================================================

def verdict_from_extraction(env: ResultEnvelope) -> SpecialistVerdict:
    """The extractor's own verdict on its run: did it complete, and with what?"""
    if env.worker_status == "failed":
        return SpecialistVerdict(
            role=ROLE_EXTRACTOR, passed=False,
            detail=env.error or "worker reported failure",
            evidence={"worker_status": env.worker_status, "nodes_produced": 0},
        )
    confs = [n.provenance.confidence for n in env.nodes
             if n.provenance and n.provenance.confidence is not None]
    avg = round(sum(confs) / len(confs), 4) if confs else None
    return SpecialistVerdict(
        role=ROLE_EXTRACTOR, passed=True,
        detail=f"worker {env.worker_id} produced {len(env.nodes)} node(s)",
        confidence=avg,
        evidence={"worker_status": env.worker_status, "nodes_produced": len(env.nodes)},
    )


def verdict_from_schema_validation(nodes: List[Node]) -> SpecialistVerdict:
    """
    Wraps research_graph_schema.validate_node() over every candidate node --
    the same structural check graph_orchestrator.py's docstring already
    credits to WorkerSpawner.admit(), just surfaced here as its own verdict
    instead of an invisible re-check inside admission.
    """
    errors: List[ValidationError] = []
    for n in nodes:
        errors.extend(validate_node(n).errors)
    passed = not errors
    detail = ("all node(s) schema-valid" if passed else
              f"{len(errors)} schema error(s) across {len(nodes)} node(s)")
    return SpecialistVerdict(
        role=ROLE_SCHEMA_VALIDATOR, passed=passed, detail=detail,
        evidence={"nodes_checked": len(nodes),
                  "errors": [e.to_dict() for e in errors]},
    )


def verdict_from_conflict_check(candidate_nodes: List[Node],
                                existing_nodes: List[Node]) -> SpecialistVerdict:
    """
    Wraps research_graph_schema.detect_conflicts_in_graph() -- only conflicts
    touching the candidate batch count, mirroring
    WorkflowGate._check_no_conflicts's own scoping (a job answers for what it
    produced, not for every unrelated conflict already in the graph).
    """
    candidate_ids = {n.id for n in candidate_nodes}
    all_conflicts = detect_conflicts_in_graph(existing_nodes + candidate_nodes)
    scoped = [c for c in all_conflicts
              if c.source_claim_id in candidate_ids or c.target_claim_id in candidate_ids]
    passed = not scoped
    detail = ("no conflicts touching this batch" if passed else
              f"{len(scoped)} conflict(s) touching this batch")
    return SpecialistVerdict(
        role=ROLE_CONFLICT_CHECKER, passed=passed, detail=detail,
        evidence={"conflicts": [
            {"source": c.source_claim_id, "target": c.target_claim_id,
             "type": c.conflict_type.value, "severity": c.severity}
            for c in scoped]},
    )


def check_confidence_divergence(
    graph: ResearchGraph,
    candidate_nodes: List[Node],
    existing_nodes: List[Node],
    threshold: float,
) -> List[Node]:
    """
    For each candidate whose id already exists among existing_nodes (a
    re-derivation of an already-admitted node -- ReferenceWorker/LLMWorker
    both mint deterministic ids from paper_id+text, so re-running the same
    extraction reproduces the same candidate ids), compare the prior node's
    confidence ("derivation") to the new candidate's ("validation"). A gap
    of at least `threshold` is recorded via graph_memory
    .record_confidence_divergence -- advisory only, same posture as
    reconcile_and_admit's disagreement recording: this never blocks or
    alters admission, it only makes the gap a durable, queryable fact
    instead of a silent overwrite of Provenance.confidence.
    """
    existing_by_id = {n.id: n for n in existing_nodes}
    divergences: List[Node] = []
    for candidate in candidate_nodes:
        prior = existing_by_id.get(candidate.id)
        if prior is None:
            continue
        derivation_conf = prior.provenance.confidence if prior.provenance else None
        validation_conf = candidate.provenance.confidence if candidate.provenance else None
        if derivation_conf is None or validation_conf is None:
            continue
        if abs(validation_conf - derivation_conf) >= threshold:
            divergences.append(graph_memory.record_confidence_divergence(
                graph, node_id=candidate.id,
                derivation_confidence=derivation_conf,
                validation_confidence=validation_conf,
                note=f"gap {abs(validation_conf - derivation_conf):.2f} >= "
                     f"threshold {threshold:.2f}",
            ))
    return divergences


# ============================================================================
# RECONCILIATION + COMMIT
# ============================================================================

def reconcile_and_admit(
    graph: ResearchGraph,
    spawner: WorkerSpawner,
    directive: ExtractionDirective,
    env: ResultEnvelope,
    schema_verdict: SpecialistVerdict,
    conflict_verdict: SpecialistVerdict,
) -> Tuple[AdmissionResult, List[Node]]:
    """
    If the schema validator and conflict checker disagree on whether this
    batch is clean, record that disagreement in graph memory (advisory
    context for whoever reviews it, never a control-flow decision) before
    calling the real, unchanged admit() as the actual commit step.

    Candidate nodes aren't in the graph yet at this point, so the job's own
    id stands in for `node_id` in the memory record -- the same id the
    review_task (if one opens) will reference.
    """
    disagreements: List[Node] = []
    if schema_verdict.passed != conflict_verdict.passed:
        record = graph_memory.record_disagreement(
            graph, node_id=directive.job_id,
            reviewer_a=ROLE_SCHEMA_VALIDATOR,
            verdict_a="pass" if schema_verdict.passed else "fail",
            reviewer_b=ROLE_CONFLICT_CHECKER,
            verdict_b="pass" if conflict_verdict.passed else "fail",
            note=f"{schema_verdict.detail} / {conflict_verdict.detail}",
        )
        disagreements.append(record)

    # Advisory only -- prior disagreements never alter whether admit() runs.
    graph_memory.prior_disagreements_on(graph, directive.job_id)

    admission = spawner.admit(directive, env)
    return admission, disagreements


# ============================================================================
# PIPELINE (real concurrency via task_graph.Scheduler)
# ============================================================================

def _build_dag() -> TaskDAG:
    dag = TaskDAG()
    dag.add_task("extract", "Extract candidate nodes", agent_id=ROLE_EXTRACTOR)
    dag.add_task("conflict_check", "Check for conflicts", agent_id=ROLE_CONFLICT_CHECKER)
    dag.add_task("schema_validate", "Validate schema", agent_id=ROLE_SCHEMA_VALIDATOR)
    dag.add_task("reviewer_judge", "Reconcile and admit", agent_id=ROLE_REVIEWER_JUDGE)
    dag.add_dependency("conflict_check", depends_on="extract")
    dag.add_dependency("schema_validate", depends_on="extract")
    dag.add_dependency("reviewer_judge", depends_on="conflict_check")
    dag.add_dependency("reviewer_judge", depends_on="schema_validate")
    return dag


def run_specialist_pipeline(
    graph: ResearchGraph,
    paper_id: str,
    text: str,
    extraction_type: ExtractionType = ExtractionType.CLAIMS,
    gate: Optional[gates.WorkflowGate] = None,
    worker: Optional[ReferenceWorker] = None,
    confidence_floor: float = 0.0,
    max_results: Optional[int] = None,
    max_workers: int = 4,
    divergence_threshold: Optional[float] = None,
) -> SpecialistPipelineReport:
    """
    High-level entry point: spawn one extraction job, run it through the four
    specialist roles over a genuine task_graph.Scheduler-run DAG (extract ->
    {conflict_check, schema_validate} in parallel -> reviewer_judge), and
    return one reconciled report.

    `divergence_threshold` (default None): when set, reviewer_judge also
    checks each candidate against any already-admitted node sharing its id
    (a re-derivation of the same paper_id+text -- workers mint deterministic
    ids, so this only fires on a genuine re-run) and records a
    CONFIDENCE_DIVERGENCE memory record when the confidence gap is at least
    this threshold. None (the default) disables the check entirely -- zero
    behavior change for every existing caller.
    """
    spawner = WorkerSpawner(graph, gate)
    worker = worker or ReferenceWorker(worker_id="specialist_reference_worker")
    _, directive = spawner.spawn(paper_id, extraction_type,
                                 confidence_floor=confidence_floor, max_results=max_results)

    existing_nodes = list(graph.nodes)
    verdicts: Dict[str, SpecialistVerdict] = {}
    envelope_box: Dict[str, ResultEnvelope] = {}
    admission_box: Dict[str, AdmissionResult] = {}
    disagreements_box: Dict[str, List[Node]] = {}
    divergences_box: Dict[str, List[Node]] = {}

    def executor(task_id: str) -> Optional[Dict[str, float]]:
        if task_id == "extract":
            env = worker.run(directive, text)
            envelope_box["env"] = env
            verdict = verdict_from_extraction(env)
            verdicts[ROLE_EXTRACTOR] = verdict
            if not verdict.passed:
                # A failed extraction has nothing for the other three
                # specialists to check -- fail the task so the Scheduler
                # cascades SKIPPED to conflict_check/schema_validate/
                # reviewer_judge, instead of running them over an empty envelope.
                raise RuntimeError(verdict.detail)
            return {"confidence": verdict.confidence} if verdict.confidence is not None else {}

        if task_id == "schema_validate":
            env = envelope_box["env"]
            verdict = verdict_from_schema_validation(env.nodes)
            verdicts[ROLE_SCHEMA_VALIDATOR] = verdict
            return {}

        if task_id == "conflict_check":
            env = envelope_box["env"]
            verdict = verdict_from_conflict_check(env.nodes, existing_nodes)
            verdicts[ROLE_CONFLICT_CHECKER] = verdict
            return {}

        if task_id == "reviewer_judge":
            env = envelope_box["env"]
            divergences: List[Node] = []
            if divergence_threshold is not None:
                divergences = check_confidence_divergence(
                    graph, env.nodes, existing_nodes, divergence_threshold)
            divergences_box["divergences"] = divergences

            admission, disagreements = reconcile_and_admit(
                graph, spawner, directive, env,
                verdicts[ROLE_SCHEMA_VALIDATOR], verdicts[ROLE_CONFLICT_CHECKER],
            )
            admission_box["admission"] = admission
            disagreements_box["disagreements"] = disagreements
            # A held-for-review job is a normal, expected outcome -- not a
            # specialist failure -- so this tracks admission, not gate.can_proceed.
            verdict = SpecialistVerdict(
                role=ROLE_REVIEWER_JUDGE, passed=admission.admitted,
                detail=(f"admitted {admission.nodes_admitted} node(s), "
                        f"status={admission.job_node.properties.get('status')}"),
                evidence={"admitted": admission.admitted,
                          "held_for_review": admission.review_task is not None,
                          "disagreements": len(disagreements),
                          "confidence_divergences": len(divergences)},
            )
            verdicts[ROLE_REVIEWER_JUDGE] = verdict
            return {}

        raise ValueError(f"unknown task_id {task_id!r}")

    dag = _build_dag()
    run_result = Scheduler(dag, max_workers=max_workers).run(executor)

    return SpecialistPipelineReport(
        paper_id=paper_id,
        job_id=directive.job_id,
        extraction_type=extraction_type.value,
        verdicts=[verdicts[role] for role in ROLES if role in verdicts],
        admission=admission_box.get("admission"),
        disagreements=disagreements_box.get("disagreements", []),
        run_result=run_result,
        confidence_divergences=divergences_box.get("divergences", []),
        envelope=envelope_box.get("env"),
    )


# ============================================================================
# SELECTIVE FAILURE-CLASS RECOVERY
# ============================================================================

def resumable_tasks(dag: TaskDAG, run_result: RunResult) -> Set[str]:
    """
    Every task that needs to be re-attempted to resume a partially-failed
    run: FAILED/SKIPPED tasks, plus (fixed-point closure) anything whose
    dependencies include an already-stale task. Generalizes
    TaskDAG.failed_ancestors' transitive-closure idea to "what must be
    redone," not just "what caused this" -- in this DAG's own shape,
    Scheduler's cascade already makes failed|skipped transitively closed,
    but this doesn't assume that; it's a real fixed point over the DAG's
    actual edges, reusable regardless of DAG shape.
    """
    stale: Set[str] = set(run_result.failed) | set(run_result.skipped)
    changed = True
    while changed:
        changed = False
        for task_id in dag.nodes:
            if task_id in stale:
                continue
            if any(dep in stale for dep in dag.dependencies_of(task_id)):
                stale.add(task_id)
                changed = True
    return stale


def _drop_downstream(dag: TaskDAG, stale: Set[str], task_id: str) -> None:
    """Remove task_id and everything that (transitively) depends on it from `stale`."""
    if task_id not in stale:
        return
    stale.discard(task_id)
    for e in dag.edges:
        if e.target == task_id:  # e.source depends_on task_id
            _drop_downstream(dag, stale, e.source)


def classify_specialist_failure(span: TaskSpan) -> str:
    """
    Pure, deterministic classification of a FAILED specialist task's span --
    the classify_rejection (research_graph_workers.py) pattern applied one
    level up, over specialist tasks instead of admit() rejections. Not
    wired into anything by default; a caller passes it to
    resume_specialist_pipeline's `classifier` param to decide what's worth
    retrying.
    """
    if span.status != TaskStatus.FAILED.value:
        return "unclassified"
    if span.task_id == "extract":
        if "unsupported extraction_type" in span.error:
            return "unsupported_extraction_type"  # permanent -- extraction_type is fixed for the run
        return "worker_reported_failure"  # plausibly transient
    return "specialist_internal_error"  # conflict_check/schema_validate/reviewer_judge
                                          # never raise on valid input today -- a real bug, not
                                          # something worth a blind retry


def resume_specialist_pipeline(
    graph: ResearchGraph,
    paper_id: str,
    text: str,
    previous_report: SpecialistPipelineReport,
    extraction_type: ExtractionType = ExtractionType.CLAIMS,
    gate: Optional[gates.WorkflowGate] = None,
    worker: Optional[ReferenceWorker] = None,
    confidence_floor: float = 0.0,
    max_results: Optional[int] = None,
    max_workers: int = 4,
    classifier: Optional[Callable[[TaskSpan], str]] = None,
    retryable_classes: Optional[Set[str]] = None,
) -> SpecialistPipelineReport:
    """
    Resume a partially-failed specialist run, re-attempting only the stale
    (FAILED/SKIPPED, and anything transitively depending on them) tasks --
    not the whole four-role pipeline blindly. If nothing is stale (the
    prior run fully succeeded, or has no run_result), returns
    `previous_report` unchanged.

    `classifier`/`retryable_classes` (both default None -- when either is
    omitted, every stale task is retried, same as calling this with no
    filtering at all): when both are supplied, each FAILED task's span is
    classified and, if its class isn't in `retryable_classes`, that task
    (and anything depending on it) is dropped from the retry set entirely
    rather than blindly retried -- e.g. classify_specialist_failure's
    "unsupported_extraction_type" is never worth retrying, since
    extraction_type is fixed for the run.

    Two concrete resume shapes exist in this DAG's actual failure surface:
    if `extract` is stale, nothing else has valid output to reuse, so this
    redoes the whole pipeline from scratch (via run_specialist_pipeline).
    If only `reviewer_judge` is stale (the only other case this DAG's code
    can currently produce -- conflict_check/schema_validate never raise on
    valid input), only reviewer_judge re-runs, reusing the prior
    extract/schema_validate/conflict_check verdicts and the prior envelope
    untouched -- the worker is never re-invoked. Any other staleness
    pattern (not producible by this DAG's code today, but not assumed
    impossible either) falls back to a full re-run rather than guessing.
    """
    run_result = previous_report.run_result
    if run_result is None or run_result.all_succeeded:
        return previous_report

    dag = _build_dag()
    stale = resumable_tasks(dag, run_result)

    if classifier is not None and retryable_classes is not None:
        spans_by_task = {s.task_id: s for s in run_result.spans}
        for task_id in list(stale):
            span = spans_by_task.get(task_id)
            if span is None or span.status != TaskStatus.FAILED.value:
                continue
            if classifier(span) not in retryable_classes:
                _drop_downstream(dag, stale, task_id)

    if not stale:
        return previous_report

    if "extract" in stale or stale != {"reviewer_judge"}:
        return run_specialist_pipeline(
            graph, paper_id, text, extraction_type, gate, worker,
            confidence_floor, max_results, max_workers)

    # Selective case: only reviewer_judge needs to re-run.
    spawner = WorkerSpawner(graph, gate)
    directive = ExtractionDirective(
        job_id=previous_report.job_id, paper_id=paper_id,
        extraction_type=extraction_type, target_node_type=PRODUCES_NODE_TYPE[extraction_type],
        confidence_floor=confidence_floor, max_results=max_results,
        gate_confidence_threshold=spawner.gate.confidence_threshold,
    )
    env = previous_report.envelope
    schema_verdict = previous_report.verdict_for(ROLE_SCHEMA_VALIDATOR)
    conflict_verdict = previous_report.verdict_for(ROLE_CONFLICT_CHECKER)
    if env is None or schema_verdict is None or conflict_verdict is None:
        # Selective resume is only reachable when extract/schema_validate/
        # conflict_check all completed (stale == {"reviewer_judge"} exactly),
        # which always populates these three -- a missing one here means
        # previous_report wasn't actually produced by a real pipeline run.
        raise ValueError(
            "resume_specialist_pipeline: previous_report is missing envelope/"
            "schema_validator/conflict_checker data required for a selective "
            "reviewer_judge-only resume")
    carried_verdicts = [v for v in previous_report.verdicts if v.role != ROLE_REVIEWER_JUDGE]

    started = _now()
    try:
        admission, disagreements = reconcile_and_admit(
            graph, spawner, directive, env, schema_verdict, conflict_verdict)
    except Exception as exc:
        span = TaskSpan(task_id="reviewer_judge", agent_id=ROLE_REVIEWER_JUDGE,
                        parent_task_id=None, status=TaskStatus.FAILED.value,
                        confidence=None, started_at=started, ended_at=_now(), error=repr(exc))
        return SpecialistPipelineReport(
            paper_id=paper_id, job_id=previous_report.job_id,
            extraction_type=extraction_type.value, verdicts=carried_verdicts,
            admission=None, disagreements=previous_report.disagreements,
            run_result=RunResult(spans=[span], failed={"reviewer_judge"}),
            envelope=env,
        )

    verdict = SpecialistVerdict(
        role=ROLE_REVIEWER_JUDGE, passed=admission.admitted,
        detail=(f"admitted {admission.nodes_admitted} node(s), "
                f"status={admission.job_node.properties.get('status')}"),
        evidence={"admitted": admission.admitted,
                  "held_for_review": admission.review_task is not None,
                  "disagreements": len(disagreements), "resumed": True},
    )
    span = TaskSpan(task_id="reviewer_judge", agent_id=ROLE_REVIEWER_JUDGE,
                    parent_task_id=None, status=TaskStatus.COMPLETED.value,
                    confidence=None, started_at=started, ended_at=_now())
    return SpecialistPipelineReport(
        paper_id=paper_id, job_id=previous_report.job_id,
        extraction_type=extraction_type.value, verdicts=carried_verdicts + [verdict],
        admission=admission, disagreements=previous_report.disagreements + disagreements,
        run_result=RunResult(spans=[span], completed={"reviewer_judge"}),
        envelope=env,
    )


if __name__ == "__main__":
    import json

    text = (
        "Hierarchical orchestration reduces coordination overhead. "
        "We evaluate on SWE-Bench and the PRISM benchmark."
    )
    graph = ResearchGraph()
    report = run_specialist_pipeline(graph, "paper_demo_001", text)

    for v in report.verdicts:
        print(f"{v.role}: passed={v.passed} -- {v.detail}")
    print(f"\nall_specialist_checks_passed={report.all_specialist_checks_passed}")
    print(f"held_for_review={report.held_for_review}")
    print(f"has_disagreement={report.has_disagreement}")
    print(json.dumps(report.to_dict(), indent=2)[:600])
