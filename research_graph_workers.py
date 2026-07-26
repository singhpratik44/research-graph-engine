#!/usr/bin/env python3
"""
Phase 4: Workers (execution plane)

The governing assumption: **a worker is untrusted**. It may be an LLM, a regex, or a
human pasting JSON. Nothing it returns enters the graph until the spawner has validated
the whole envelope against Phase 3's schema and Phase 2's gate. A rejected envelope
fails the job — it never lands partially.

`WorkerSpawner.admit()` optionally supports a bounded diagnose-and-retry loop
(`gap_adaptive_recovery`): pass `retry_with` — a callable given the directive and the
*actual* `ValidationError`s that rejected the attempt — to produce a new envelope to
try instead, up to `max_retries` times. Every attempt, successful or not, is recorded
on the job (`retry_attempts`, `retry_count`, `original_failure`) — auditable, never a
silent overwrite. Default behavior (no `retry_with`) is untouched: one attempt, fail
whole on rejection, exactly as before.

Three pieces:
  ExtractionDirective — the contract handed *to* a worker (what to do, what to prove)
  ResultEnvelope      — the contract handed *back* (what was produced, why, by whom)
  WorkerSpawner       — mints jobs, admits or rejects envelopes, drives the gate

Plus a deterministic ReferenceWorker so the whole loop runs end-to-end with no model
in it. If the loop only works with an LLM attached, the plumbing isn't proven.
"""

from dataclasses import dataclass, field, asdict
from typing import Any, Callable, Dict, List, Optional, Tuple
from datetime import datetime, timezone
import hashlib
import re

from research_graph_schema import (
    Node, Edge, Provenance, Trace, ResearchGraph, ValidationError,
    NodeType, EdgeType, JobStatus, ReviewStatus, ExtractionType,
    DecisionType, ExtractionMethod,
    validate_node, validate_trace, detect_conflicts_in_graph,
    SCHEMA_VERSION, TRACE_REQUIRED_FIELDS,
)
import research_graph_gates as gates


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _slug(text: str, n: int = 6) -> str:
    return hashlib.sha1(text.encode()).hexdigest()[:n]


# Which node type each extraction type is allowed to produce. A worker that returns
# something else is rejected — the directive is a contract, not a suggestion.
PRODUCES_NODE_TYPE: Dict[ExtractionType, NodeType] = {
    ExtractionType.CLAIMS: NodeType.CLAIM,
    ExtractionType.CONCEPTS: NodeType.CONCEPT,
    ExtractionType.METHODS: NodeType.METHOD,
    ExtractionType.BENCHMARKS: NodeType.BENCHMARK,
    ExtractionType.CONFLICTS: NodeType.CLAIM,
}


# ============================================================================
# THE CONTRACT OUT
# ============================================================================

@dataclass
class ExtractionDirective:
    """
    Everything a worker needs, and everything it will be held to. Deliberately
    self-contained: a worker should never have to read the gate's source to know
    what will be checked.
    """
    job_id: str
    paper_id: str
    extraction_type: ExtractionType
    target_node_type: NodeType
    schema_version: str = SCHEMA_VERSION
    confidence_floor: float = 0.0          # results below this must be SKIPped, not emitted
    trace_every_decision: bool = True
    required_trace_fields: List[str] = field(default_factory=lambda: list(TRACE_REQUIRED_FIELDS))
    max_results: Optional[int] = None
    gate_confidence_threshold: float = 0.7  # echoed so the worker knows what it's aiming at
    issued_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["extraction_type"] = self.extraction_type.value
        d["target_node_type"] = self.target_node_type.value
        return d


# ============================================================================
# THE CONTRACT BACK
# ============================================================================

@dataclass
class ResultEnvelope:
    """What a worker returns. Nodes and traces travel together, always."""
    job_id: str
    worker_id: str
    nodes: List[Node] = field(default_factory=list)
    traces: List[Trace] = field(default_factory=list)
    worker_status: str = "completed"     # "completed" | "failed"
    error: str = ""
    completed_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "worker_id": self.worker_id,
            "nodes": [n.to_dict() for n in self.nodes],
            "traces": [t.to_dict() for t in self.traces],
            "worker_status": self.worker_status,
            "error": self.error,
            "completed_at": self.completed_at,
        }


@dataclass
class AdmissionResult:
    """Outcome of trying to admit an envelope into the graph."""
    admitted: bool
    job_node: Node
    errors: List[ValidationError] = field(default_factory=list)
    gate_decision: Optional[Any] = None
    review_task: Optional[Node] = None
    conflicts_found: int = 0
    nodes_admitted: int = 0

    @property
    def codes(self) -> List[str]:
        return [e.code for e in self.errors]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "admitted": self.admitted,
            "job_id": self.job_node.id,
            "job_status": self.job_node.properties.get("status"),
            "nodes_admitted": self.nodes_admitted,
            "conflicts_found": self.conflicts_found,
            "errors": [e.to_dict() for e in self.errors],
            "gate": self.gate_decision.to_dict() if self.gate_decision else None,
            "review_task": self.review_task.id if self.review_task else None,
        }


# ============================================================================
# FAILURE CLASSIFICATION (failure-class recovery dispatch)
# ============================================================================

def classify_rejection(errors: List[ValidationError]) -> str:
    """
    Pure, deterministic classification of a rejected admit() attempt into a
    broad failure class -- NOT wired into admit() itself. A caller's own
    retry_with can call this to build a differentiated recovery strategy
    (retry / argument-repair / escalate) instead of one undifferentiated
    blind retry, per the failure-class-dispatch pattern this closes.
    admit()'s own signature, defaults, and control flow are completely
    unchanged by this function's existence -- it's a standalone tool for a
    caller to consult, not a new code path inside admission.

    Categories, checked in this order (a rejection can trip more than one
    of _verify_envelope's checks at once, so precedence runs from "least
    fixable by a simple retry" to "most fixable"):
      "worker_reported_failure" -- the worker itself reported failure (the
          synthetic ValidationError("worker_status", ...) admit() raises at
          the env.worker_status == "failed" short-circuit, before
          _verify_envelope ever runs).
      "capacity_violation"      -- too many results for max_results, or a
          node's confidence below the directive's floor -- both about *how
          much*/*how confident* was produced, not a malformed node.
      "structural_mismatch"     -- envelope-level identity errors: job_id
          mismatch, missing worker_id, wrong node type, duplicate/colliding
          node ids -- the envelope doesn't match its own directive's shape.
      "trace_integrity"         -- missing/duplicate/orphaned/mismatched
          trace errors -- the nodes may be fine, but their audit trail isn't.
      "reparable_field_error"   -- a per-node schema field error (missing
          field, bad type, bad enum, out of range, spoofed source_paper,
          self-marked human_reviewed) -- plausibly fixable by re-asking the
          worker for just that field.
      "unclassified"            -- no errors matched any known shape.
    """
    paths = [(e.field_path, e.code) for e in errors]

    if any(p == "worker_status" for p, _ in paths):
        return "worker_reported_failure"
    if any((p == "nodes" and c == "OUT_OF_RANGE") or p.endswith(".provenance.confidence")
           for p, c in paths):
        return "capacity_violation"
    if any(p in ("job_id", "worker_id") or p == "nodes" or p.endswith(".type")
           or p.endswith(".id") for p, _ in paths):
        return "structural_mismatch"
    if any(p.startswith("traces") for p, _ in paths):
        return "trace_integrity"
    if any(p.startswith("nodes[") for p, _ in paths):
        return "reparable_field_error"
    return "unclassified"


# ============================================================================
# SPAWNER
# ============================================================================

class WorkerSpawner:
    """Mints jobs, admits envelopes, drives the gate. The only writer to the graph."""

    def __init__(self, graph: ResearchGraph, gate: Optional[gates.WorkflowGate] = None):
        self.graph = graph
        self.gate = gate or gates.WorkflowGate()

    # -- spawn ------------------------------------------------------------

    def spawn(self, paper_id: str, extraction_type: ExtractionType,
              confidence_floor: float = 0.0,
              max_results: Optional[int] = None) -> Tuple[Node, ExtractionDirective]:
        job_id = f"job_{_slug(paper_id + extraction_type.value)}_{extraction_type.value}"
        job = Node(
            id=job_id,
            type=NodeType.EXTRACTION_JOB.value,
            label=f"Extract {extraction_type.value} from {paper_id}",
            provenance=Provenance(
                source_paper=paper_id,
                extraction_method=ExtractionMethod.JOB_SPAWN.value,
                confidence=1.0,
                extracted_at=_now(),
                human_reviewed=False,
            ),
            properties={
                "job_id": job_id,
                "paper_id": paper_id,
                "extraction_type": extraction_type.value,
                "status": JobStatus.QUEUED.value,
                "spawned_at": _now(),
            },
        )
        self.graph.nodes.append(job)

        directive = ExtractionDirective(
            job_id=job_id,
            paper_id=paper_id,
            extraction_type=extraction_type,
            target_node_type=PRODUCES_NODE_TYPE[extraction_type],
            confidence_floor=confidence_floor,
            max_results=max_results,
            gate_confidence_threshold=self.gate.confidence_threshold,
        )
        return job, directive

    # -- admit ------------------------------------------------------------

    def _verify_envelope(self, directive: ExtractionDirective,
                         env: ResultEnvelope) -> List[ValidationError]:
        """
        Everything checked here is checked *before* a single node reaches the graph.
        Order matters only for readability; all errors are collected, not short-circuited,
        so a worker gets its whole report card at once.
        """
        errors: List[ValidationError] = []
        E = lambda p, c, m: errors.append(ValidationError(p, c, m))  # noqa: E731

        if env.job_id != directive.job_id:
            E("job_id", "BAD_TYPE",
              f"envelope job_id {env.job_id!r} != directive {directive.job_id!r}")
        if not env.worker_id:
            E("worker_id", "MISSING_REQUIRED", "envelope has no worker_id")

        produced_ids = set()
        for i, n in enumerate(env.nodes):
            path = f"nodes[{i}]"
            if n.type != directive.target_node_type.value:
                E(f"{path}.type", "BAD_TYPE",
                  f"directive requires {directive.target_node_type.value!r}, got {n.type!r}")
            for e in validate_node(n).errors:
                E(f"{path}.{e.field_path}", e.code, e.message)
            if n.provenance is None:
                E(f"{path}.provenance", "MISSING_REQUIRED", "produced node has no provenance")
            else:
                if n.provenance.source_paper != directive.paper_id:
                    E(f"{path}.provenance.source_paper", "BAD_TYPE",
                      f"node claims source {n.provenance.source_paper!r}, "
                      f"directive is for {directive.paper_id!r}")
                c = n.provenance.confidence
                if c is not None and c < directive.confidence_floor:
                    E(f"{path}.provenance.confidence", "OUT_OF_RANGE",
                      f"confidence {c} below directive floor {directive.confidence_floor}; "
                      "should have been SKIPped, not emitted")
                if n.provenance.human_reviewed:
                    E(f"{path}.provenance.human_reviewed", "BAD_TYPE",
                      "a worker may not mark its own output human_reviewed")
            if n.id in produced_ids:
                E(f"{path}.id", "BAD_TYPE", f"duplicate node id {n.id!r} in envelope")
            produced_ids.add(n.id)

        if n_ids := (produced_ids & set(self.graph.index())):
            E("nodes", "BAD_TYPE", f"node ids already in graph: {sorted(n_ids)}")

        if directive.max_results is not None and len(env.nodes) > directive.max_results:
            E("nodes", "OUT_OF_RANGE",
              f"{len(env.nodes)} results exceeds max_results {directive.max_results}")

        if directive.trace_every_decision and env.nodes and not env.traces:
            E("traces", "MISSING_REQUIRED",
              "directive requires a trace per decision; envelope has none")

        seen_trace_ids = set()
        for i, t in enumerate(env.traces):
            for e in validate_trace(t, f"traces[{i}]"):
                errors.append(e)
            if t.trace_id in seen_trace_ids:
                E(f"traces[{i}].trace_id", "BAD_TYPE", f"duplicate trace_id {t.trace_id!r}")
            seen_trace_ids.add(t.trace_id)
            if t.worker_id != env.worker_id:
                E(f"traces[{i}].worker_id", "BAD_TYPE",
                  f"trace worker_id {t.worker_id!r} != envelope {env.worker_id!r}")
            for ref in t.output_refs:
                if ref not in produced_ids:
                    E(f"traces[{i}].output_refs", "BAD_TYPE",
                      f"trace claims output {ref!r} that is not in the envelope")

        # Every emitted node must be accounted for by an EXTRACT trace. Untraced output
        # is exactly the thing this whole design exists to prevent.
        if directive.trace_every_decision:
            traced = {r for t in env.traces if t.decision_type == DecisionType.EXTRACT
                      for r in t.output_refs}
            for orphan in sorted(produced_ids - traced):
                E("traces", "MISSING_REQUIRED",
                  f"node {orphan!r} was emitted with no EXTRACT trace explaining it")

        return errors

    def admit(self, directive: ExtractionDirective, env: ResultEnvelope,
              retry_with: Optional[Callable[[ExtractionDirective, List[ValidationError]],
                                            ResultEnvelope]] = None,
              max_retries: int = 1) -> AdmissionResult:
        """
        Admit `env` against `directive`. On rejection by `_verify_envelope`, and only
        if `retry_with` is supplied, retry up to `max_retries` times: `retry_with` is
        called with the directive and the *actual* `ValidationError`s from the failed
        attempt (why it was rejected, not just that it was) and must produce a new
        envelope to try instead.

        `retry_with=None` (the default) is byte-for-byte the original behavior: one
        attempt, and a rejection fails the job wholly — no extra bookkeeping is even
        written to `job.properties` in that path. Every attempt actually made when a
        retry function IS supplied stays on the record (`retry_attempts`,
        `retry_count`, `original_failure`), so a retried admission is still fully
        auditable, never a silent overwrite of what went wrong the first time.
        """
        job = self.graph.index().get(directive.job_id)
        if job is None:
            raise KeyError(f"unknown job {directive.job_id!r} — spawn it first")
        assert job.provenance is not None  # spawn() always sets one

        job.properties["worker_id"] = env.worker_id
        job.properties["completed_at"] = env.completed_at
        job.properties["traces"] = list(env.traces)

        if env.worker_status == "failed":
            job.properties["status"] = JobStatus.FAILED.value
            return AdmissionResult(False, job,
                                   [ValidationError("worker_status", "BAD_TYPE",
                                                    env.error or "worker reported failure")])

        # -- diagnose-and-retry loop (gap_adaptive_recovery) ---------------
        # `attempts` stays empty -- and no extra job.properties get written -- unless
        # retry_with is actually supplied and actually used, so the retry_with=None
        # default takes exactly one pass through this loop, identical to the
        # original single-shot admit.
        attempts: List[Dict[str, Any]] = []
        current_env = env
        while True:
            errors = self._verify_envelope(directive, current_env)
            if not errors:
                break
            if retry_with is None or len(attempts) >= max_retries:
                # Fail whole, not partial. A half-admitted extraction is unauditable.
                job.properties["status"] = JobStatus.FAILED.value
                job.properties["result_count"] = 0
                if attempts:
                    attempts.append({"errors": [e.to_dict() for e in errors]})
                    job.properties["retry_attempts"] = attempts
                    job.properties["retry_count"] = len(attempts) - 1
                    job.properties["original_failure"] = attempts[0]["errors"]
                return AdmissionResult(False, job, errors)
            attempts.append({"errors": [e.to_dict() for e in errors]})
            current_env = retry_with(directive, errors)
            job.properties["worker_id"] = current_env.worker_id
            job.properties["completed_at"] = current_env.completed_at
            job.properties["traces"] = list(current_env.traces)

        env = current_env
        if attempts:
            job.properties["retry_attempts"] = attempts
            job.properties["retry_count"] = len(attempts)
            job.properties["original_failure"] = attempts[0]["errors"]

        confs = [n.provenance.confidence for n in env.nodes
                 if n.provenance and n.provenance.confidence is not None]
        avg = round(sum(confs) / len(confs), 4) if confs else 0.0

        self.graph.nodes.extend(env.nodes)
        for n in env.nodes:
            self.graph.edges.append(Edge(
                source=job.id, target=n.id, type=EdgeType.PRODUCES.value,
                provenance=Provenance(directive.paper_id, ExtractionMethod.JOB_SPAWN.value,
                                      1.0, _now()),
            ))

        job.properties["status"] = JobStatus.COMPLETED.value
        job.properties["result_count"] = len(env.nodes)
        job.properties["avg_confidence"] = avg
        job.provenance.confidence = avg

        new_conflicts = [c for c in detect_conflicts_in_graph(self.graph.nodes)
                         if not any(c.source_claim_id == x.source_claim_id
                                    and c.target_claim_id == x.target_claim_id
                                    for x in self.graph.conflicts)]
        self.graph.conflicts.extend(new_conflicts)

        # research_graph_gates.Node is a structurally-identical local stub (see
        # its own module docstring) -- the gate is deliberately schema-agnostic
        # and never imports research_graph_schema, so it type-checks against
        # its own Node, not this one. Verified duck-typed by the full test
        # suite; not a real type error.
        decision = self.gate.should_unlock_next_stage(job, self.graph)  # type: ignore[arg-type]
        review = None
        if not decision.can_proceed:
            job.properties["status"] = JobStatus.HELD.value
            review = self._open_review(job, decision)

        return AdmissionResult(
            admitted=True, job_node=job, gate_decision=decision, review_task=review,
            conflicts_found=len(new_conflicts), nodes_admitted=len(env.nodes),
        )

    def _open_review(self, job: Node, decision) -> Node:
        task_id = f"review_{job.properties['job_id']}"
        existing = self.graph.index().get(task_id)
        if existing is not None:
            existing.properties["gate_reason"] = f"{decision.reason_code.value}: {decision.reason}"
            return existing

        task = Node(
            id=task_id,
            type=NodeType.REVIEW_TASK.value,
            label=f"Review {job.label}",
            provenance=Provenance(
                source_paper=job.properties["paper_id"],
                extraction_method=ExtractionMethod.GATE_HOLD.value,
                confidence=1.0, extracted_at=_now(), human_reviewed=False,
            ),
            properties={
                "task_id": task_id,
                "extraction_job_id": job.properties["job_id"],
                "status": ReviewStatus.PENDING.value,
                "created_at": _now(),
                "gate_reason": f"{decision.reason_code.value}: {decision.reason}",
            },
        )
        self.graph.nodes.append(task)
        self.graph.edges.append(Edge(job.id, task.id, EdgeType.REQUIRES_REVIEW.value,
                                     Provenance(job.properties["paper_id"],
                                                ExtractionMethod.GATE_HOLD.value, 1.0, _now())))
        return task

    # -- review -----------------------------------------------------------

    def approve_review(self, task_id: str, reviewed_by: str, notes: str = "",
                       waive_confidence: bool = False, waiver_reason: str = ""):
        """
        Human approval. Re-runs the gate afterwards and returns the fresh decision —
        approval is a *request* to re-evaluate, not a decree that the node advances.
        """
        idx = self.graph.index()
        task = idx.get(task_id)
        if task is None:
            raise KeyError(f"unknown review task {task_id!r}")
        if waive_confidence and not waiver_reason:
            raise ValueError("a confidence waiver requires a waiver_reason")

        job = next(n for n in self.graph.nodes
                   if n.type == NodeType.EXTRACTION_JOB.value
                   and n.properties.get("job_id") == task.properties["extraction_job_id"])
        assert task.provenance is not None  # _open_review()/spawn() always set one
        assert job.provenance is not None

        task.properties.update({
            "status": ReviewStatus.APPROVED.value,
            "reviewed_by": reviewed_by,
            "reviewed_at": _now(),
            "review_notes": notes,
        })
        if waive_confidence:
            task.properties["confidence_threshold_waived"] = True
            task.properties["waiver_reason"] = waiver_reason
        task.provenance.human_reviewed = True
        task.provenance.review_notes = notes

        self.graph.edges.append(Edge(task.id, job.id, EdgeType.APPROVED_FOR.value,
                                     Provenance(job.properties["paper_id"],
                                                ExtractionMethod.HUMAN_ANNOTATION.value,
                                                1.0, _now())))

        job.provenance.human_reviewed = True
        job.provenance.review_notes = notes
        for n in self.graph.nodes:
            if (n.provenance is not None
                    and any(e.source == job.id and e.target == n.id
                            and e.type == EdgeType.PRODUCES.value for e in self.graph.edges)):
                n.provenance.human_reviewed = True

        decision = self.gate.should_unlock_next_stage(job, self.graph)  # type: ignore[arg-type]
        job.properties["status"] = (JobStatus.APPROVED.value if decision.can_proceed
                                    else JobStatus.HELD.value)
        return decision

    def reject_review(self, task_id: str, reviewed_by: str, notes: str) -> Node:
        task = self.graph.index()[task_id]
        job = next(n for n in self.graph.nodes
                   if n.type == NodeType.EXTRACTION_JOB.value
                   and n.properties.get("job_id") == task.properties["extraction_job_id"])
        assert task.provenance is not None  # _open_review()/spawn() always set one
        task.properties.update({"status": ReviewStatus.REJECTED.value,
                                "reviewed_by": reviewed_by, "reviewed_at": _now(),
                                "review_notes": notes})
        task.provenance.human_reviewed = True
        job.properties["status"] = JobStatus.REJECTED.value
        return job


# ============================================================================
# REFERENCE WORKER (deterministic — no model required)
# ============================================================================

_STOP = {"the", "a", "an", "of", "and", "or", "for", "to", "in", "on", "at", "we",
         "this", "that", "with", "is", "are", "be", "by", "as", "it", "our", "can"}

_RELATIONS = ["reduces", "increases", "improves", "degrades", "enables",
              "prevents", "outperforms", "underperforms", "decreases"]

# Two deliberately dumb signals, same spirit as the concept/claim heuristics
# above: a name ending in "Bench"/"bench" (SWE-Bench, MLR-Bench, LEGOBench) is
# a strong signal; a capitalized phrase immediately before the word
# "benchmark" (the "PRISM benchmark") is a weaker one.
_BENCHMARK_SUFFIX_RE = re.compile(r"\b[A-Z][\w\-]*(?:Bench|bench)\b")
_BENCHMARK_PHRASE_RE = re.compile(r"\b([A-Z][\w\-]{2,})\s+benchmark\b")


class ReferenceWorker:
    """
    A deliberately dumb extractor. Its job is to prove the envelope contract is
    satisfiable and the loop closes — not to extract well.
    """

    def __init__(self, worker_id: str = "reference_worker_v1"):
        self.worker_id = worker_id
        self._seq = 0

    def _trace_id(self) -> str:
        self._seq += 1
        return f"tr_{self.worker_id}_{self._seq:04d}"

    def run(self, directive: ExtractionDirective, text: str) -> ResultEnvelope:
        if directive.extraction_type == ExtractionType.CONCEPTS:
            return self._concepts(directive, text)
        if directive.extraction_type == ExtractionType.CLAIMS:
            return self._claims(directive, text)
        if directive.extraction_type == ExtractionType.BENCHMARKS:
            return self._benchmarks(directive, text)
        return ResultEnvelope(directive.job_id, self.worker_id, worker_status="failed",
                              error=f"unsupported extraction_type "
                                    f"{directive.extraction_type.value}")

    def _prov(self, directive: ExtractionDirective, conf: float,
              method: ExtractionMethod) -> Provenance:
        return Provenance(directive.paper_id, method.value, conf, _now(), human_reviewed=False)

    def _concepts(self, d: ExtractionDirective, text: str) -> ResultEnvelope:
        nodes: List[Node] = []
        traces: List[Trace] = []
        counts: Dict[str, int] = {}
        for w in re.findall(r"[a-zA-Z][a-zA-Z\-]{2,}", text.lower()):
            if w not in _STOP:
                counts[w] = counts.get(w, 0) + 1

        for term, n in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])):
            conf = min(0.95, 0.45 + 0.12 * n)
            if conf < d.confidence_floor:
                traces.append(Trace(self._trace_id(), DecisionType.SKIP, self.worker_id,
                                    conf, "BELOW_DIRECTIVE_FLOOR",
                                    f"'{term}' scored {conf:.2f}, under floor "
                                    f"{d.confidence_floor:.2f}",
                                    input_refs=[f"{d.paper_id}#text"]))
                continue
            if d.max_results is not None and len(nodes) >= d.max_results:
                traces.append(Trace(self._trace_id(), DecisionType.ABSTAIN, self.worker_id,
                                    conf, "MAX_RESULTS_REACHED",
                                    f"'{term}' qualified but directive caps at "
                                    f"{d.max_results}",
                                    input_refs=[f"{d.paper_id}#text"]))
                continue
            nid = f"concept_{_slug(d.paper_id + term)}"
            nodes.append(Node(nid, NodeType.CONCEPT.value, term,
                              self._prov(d, conf, ExtractionMethod.KEYWORD),
                              {"text": term}))
            traces.append(Trace(self._trace_id(), DecisionType.EXTRACT, self.worker_id,
                                conf, "TERM_FREQUENCY",
                                f"'{term}' appears {n}x; frequency-scored {conf:.2f}",
                                input_refs=[f"{d.paper_id}#text"], output_refs=[nid]))
        return ResultEnvelope(d.job_id, self.worker_id, nodes, traces)

    def _claims(self, d: ExtractionDirective, text: str) -> ResultEnvelope:
        nodes: List[Node] = []
        traces: List[Trace] = []
        for sentence in [s.strip() for s in re.split(r"[.;]", text) if s.strip()]:
            rel = next((r for r in _RELATIONS if f" {r} " in f" {sentence.lower()} "), None)
            if rel is None:
                traces.append(Trace(self._trace_id(), DecisionType.SKIP, self.worker_id,
                                    0.1, "NO_RELATION_VERB",
                                    f"no known relation verb in {sentence[:48]!r}",
                                    input_refs=[f"{d.paper_id}#text"]))
                continue
            subj, _, obj = sentence.lower().partition(f" {rel} ")
            subj, obj = subj.strip(), obj.strip()
            conf = 0.85 if subj and obj else 0.4
            if conf < d.confidence_floor:
                traces.append(Trace(self._trace_id(), DecisionType.SKIP, self.worker_id,
                                    conf, "BELOW_DIRECTIVE_FLOOR",
                                    f"incomplete triple in {sentence[:48]!r}",
                                    input_refs=[f"{d.paper_id}#text"]))
                continue
            nid = f"claim_{_slug(d.paper_id + sentence)}"
            nodes.append(Node(nid, NodeType.CLAIM.value, sentence.strip(),
                              self._prov(d, conf, ExtractionMethod.STRUCTURED_LLM),
                              {"text": sentence.strip(), "subject": subj,
                               "relation": rel, "object": obj}))
            traces.append(Trace(self._trace_id(), DecisionType.EXTRACT, self.worker_id,
                                conf, "RELATION_TRIPLE",
                                f"parsed '{subj}' -{rel}-> '{obj}'",
                                input_refs=[f"{d.paper_id}#text"], output_refs=[nid]))
        return ResultEnvelope(d.job_id, self.worker_id, nodes, traces)

    def _benchmarks(self, d: ExtractionDirective, text: str) -> ResultEnvelope:
        nodes: List[Node] = []
        traces: List[Trace] = []
        # name -> confidence, first-seen order preserved; a suffix match (SWE-Bench)
        # is a stronger signal than a bare "<Name> benchmark" phrase, so it wins
        # if a name is caught by both patterns.
        candidates: Dict[str, float] = {}
        for m in _BENCHMARK_SUFFIX_RE.finditer(text):
            candidates.setdefault(m.group(0), 0.8)
        for m in _BENCHMARK_PHRASE_RE.finditer(text):
            candidates.setdefault(m.group(1), 0.6)

        for name, conf in candidates.items():
            if conf < d.confidence_floor:
                traces.append(Trace(self._trace_id(), DecisionType.SKIP, self.worker_id,
                                    conf, "BELOW_DIRECTIVE_FLOOR",
                                    f"'{name}' scored {conf:.2f}, under floor {d.confidence_floor:.2f}",
                                    input_refs=[f"{d.paper_id}#text"]))
                continue
            if d.max_results is not None and len(nodes) >= d.max_results:
                traces.append(Trace(self._trace_id(), DecisionType.ABSTAIN, self.worker_id,
                                    conf, "MAX_RESULTS_REACHED",
                                    f"'{name}' qualified but directive caps at {d.max_results}",
                                    input_refs=[f"{d.paper_id}#text"]))
                continue
            nid = f"benchmark_{_slug(d.paper_id + name)}"
            nodes.append(Node(nid, NodeType.BENCHMARK.value, name,
                              self._prov(d, conf, ExtractionMethod.KEYWORD),
                              {"text": name}))
            traces.append(Trace(self._trace_id(), DecisionType.EXTRACT, self.worker_id,
                                conf, "BENCHMARK_NAME_PATTERN",
                                f"'{name}' matched a benchmark-name pattern",
                                input_refs=[f"{d.paper_id}#text"], output_refs=[nid]))
        return ResultEnvelope(d.job_id, self.worker_id, nodes, traces)
