#!/usr/bin/env python3
"""
Phase 3: Schema Expansion (data plane)

Additive to Phase 2's gate logic (research_graph_gates.py) — this module does not
import or modify the gate. It defines what a conforming node/edge *is*, so that
every field the gate reads has a declared owner, type, and (where applicable) a
closed enum.

Design rules carried in from review:
  1. `traces` is structured, not freeform — each entry is a Trace with queryable fields.
  2. Closed enums wherever a field has a finite value set (status, extraction_type,
     conflict_type, decision_type, extraction_method, node/edge type).
  3. Validation returns structured errors, never a bare bool — the caller needs to
     know *which* field failed for the same reason the gate needs reason codes.
"""

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Type
from enum import Enum
from datetime import datetime, timezone
import json

SCHEMA_VERSION = "3.3.0"


# ============================================================================
# ENUMS (closed value sets — validation and gate tests both key off these)
# ============================================================================

class NodeType(str, Enum):
    PAPER = "paper"
    CONCEPT = "concept"
    CLAIM = "claim"
    GAP = "gap"
    METHOD = "method"
    DOMAIN = "domain"
    BENCHMARK = "benchmark"
    EXTRACTION_JOB = "extraction_job"
    REVIEW_TASK = "review_task"
    MEMORY_RECORD = "memory_record"   # graph memory: task outcomes, claim decisions,
                                      # reviewer disagreements, blocked reasons, repairs


class EdgeType(str, Enum):
    # Semantic (research content)
    CITES = "cites"
    BUILDS_ON = "builds_on"
    CONTRADICTS = "contradicts"
    EXTENDS = "extends"
    APPLIES = "applies"
    ADDRESSES = "addresses"
    LEAVES_GAP = "leaves_gap"
    BENCHMARKS = "benchmarks"
    PROPOSES = "proposes"
    USES_METHOD = "uses_method"
    PRODUCES = "produces"
    # Graph memory (typed, so memory is more than a flat log -- see graph_memory.py,
    # which subsumes the old gap_typed_provenance_edges backlog item).
    SUPPORTED_BY = "supported_by"       # claim -> memory_record: claim accepted, this is why
    REJECTED_BECAUSE = "rejected_because"  # claim -> memory_record: claim rejected, this is why
    DISAGREED_ON = "disagreed_on"       # memory_record -> any node: reviewers disagreed on it
    REPAIRED_VIA = "repaired_via"       # any node -> memory_record: this is how it got fixed
    DERIVED_FROM = "derived_from"       # memory_record -> any node: computed from that node
    # Gate control (workflow-as-data)
    REQUIRES_REVIEW = "requires_review"   # extraction_job -> review_task
    APPROVED_FOR = "approved_for"         # review_task -> extraction_job
    BLOCKED_BY = "blocked_by"             # extraction_job -> extraction_job
    UNLOCKS = "unlocks"                   # extraction_job -> extraction_job


GATE_CONTROL_EDGES = frozenset({
    EdgeType.REQUIRES_REVIEW,
    EdgeType.APPROVED_FOR,
    EdgeType.BLOCKED_BY,
    EdgeType.UNLOCKS,
})

# Endpoint contract for structurally-constrained edges: (allowed source types, allowed
# target types). Originally just the four gate-control edges above; SUPPORTED_BY and
# REJECTED_BECAUSE join them because graph_memory.py only ever uses them claim -> memory
# record, so the same fixed-endpoint discipline applies. DISAGREED_ON/REPAIRED_VIA/
# DERIVED_FROM are deliberately left out: their non-memory endpoint can legitimately be
# any node type (a disagreement or a repair can be about a claim, a job, a concept...),
# so there's no fixed set to enforce here.
EDGE_ENDPOINT_CONTRACT: Dict[EdgeType, Any] = {
    EdgeType.REQUIRES_REVIEW: ({NodeType.EXTRACTION_JOB}, {NodeType.REVIEW_TASK}),
    EdgeType.APPROVED_FOR:    ({NodeType.REVIEW_TASK}, {NodeType.EXTRACTION_JOB}),
    EdgeType.BLOCKED_BY:      ({NodeType.EXTRACTION_JOB}, {NodeType.EXTRACTION_JOB}),
    EdgeType.UNLOCKS:         ({NodeType.EXTRACTION_JOB}, {NodeType.EXTRACTION_JOB}),
    EdgeType.SUPPORTED_BY:    ({NodeType.CLAIM}, {NodeType.MEMORY_RECORD}),
    EdgeType.REJECTED_BECAUSE: ({NodeType.CLAIM}, {NodeType.MEMORY_RECORD}),
}


class JobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    HELD = "held"
    APPROVED = "approved"
    REJECTED = "rejected"


class ReviewStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    NEEDS_REVISION = "needs_revision"


class ExtractionType(str, Enum):
    CLAIMS = "claims"
    CONCEPTS = "concepts"
    METHODS = "methods"
    BENCHMARKS = "benchmarks"
    CONFLICTS = "conflicts"


class ConflictType(str, Enum):
    CONTRADICTS = "contradicts"
    INCOMPATIBLE_SCOPE = "incompatible_scope"
    METHOD_DEPENDENT = "method_dependent"


class DecisionType(str, Enum):
    """What kind of decision a worker recorded in a trace entry."""
    EXTRACT = "extract"            # produced a candidate node
    SKIP = "skip"                  # saw a candidate, rejected it
    MERGE = "merge"                # folded into an existing node
    FLAG_CONFLICT = "flag_conflict"  # noticed a contradiction
    ABSTAIN = "abstain"            # insufficient evidence to decide


class ExtractionMethod(str, Enum):
    METADATA = "metadata"
    ABSTRACT_PARSE = "abstract_parse"
    KEYWORD = "keyword"
    STRUCTURED_LLM = "structured_llm"
    HUMAN_ANNOTATION = "human_annotation"
    JOB_SPAWN = "job_spawn"
    GATE_HOLD = "gate_hold"
    MEMORY_WRITE = "memory_write"   # graph_memory.py: a memory_record, not an extraction


class MemoryKind(str, Enum):
    """What a NodeType.MEMORY_RECORD node records. See graph_memory.py."""
    TASK_OUTCOME = "task_outcome"                 # a task_graph.TaskSpan's result
    CLAIM_ACCEPTED = "claim_accepted"              # a claim that passed the gate
    CLAIM_REJECTED = "claim_rejected"              # a claim a human reviewer rejected
    REVIEWER_DISAGREEMENT = "reviewer_disagreement"  # two humans disagreeing on one node
    BLOCKED_REASON = "blocked_reason"              # a GateDecision's block, persisted
    REPAIR_PATTERN = "repair_pattern"              # how a rejected/blocked item got fixed
    CONFIDENCE_DIVERGENCE = "confidence_divergence"  # derivation- vs validation-time confidence gap
    ACTION_POLICY_DECISION = "action_policy_decision"  # a runtime ActionPolicy allow/escalate/block verdict


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _enum_values(e: Type[Enum]) -> List[str]:
    return [m.value for m in e]


# ============================================================================
# STRUCTURED TRACE (adjustment #1 — queryable, not a text blob)
# ============================================================================

@dataclass
class Trace:
    """
    One worker decision. Every field here exists so a trace set can be *queried*
    later ("show me every ABSTAIN by worker X under 0.6 confidence") rather than
    grepped.
    """
    trace_id: str
    decision_type: DecisionType
    worker_id: str
    confidence: float
    reason_code: str                  # worker-local code, e.g. "EVIDENCE_IN_ABSTRACT"
    reasoning_summary: str            # one line, human-readable
    input_refs: List[str] = field(default_factory=list)   # e.g. ["paper_2606.13707#abstract"]
    output_refs: List[str] = field(default_factory=list)  # e.g. ["claim_2606_004"]
    timestamp: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["decision_type"] = self.decision_type.value
        return d

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "Trace":
        return Trace(
            trace_id=d["trace_id"],
            decision_type=DecisionType(d["decision_type"]),
            worker_id=d["worker_id"],
            confidence=d["confidence"],
            reason_code=d["reason_code"],
            reasoning_summary=d["reasoning_summary"],
            input_refs=list(d.get("input_refs", [])),
            output_refs=list(d.get("output_refs", [])),
            timestamp=d.get("timestamp", _now()),
        )


TRACE_REQUIRED_FIELDS = [
    "trace_id", "decision_type", "worker_id", "confidence",
    "reason_code", "reasoning_summary", "timestamp",
]


# ============================================================================
# CORE RECORDS
# ============================================================================

@dataclass
class Provenance:
    source_paper: str
    extraction_method: str
    confidence: Optional[float]
    extracted_at: str
    human_reviewed: bool = False
    review_notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Node:
    id: str
    type: str
    label: str
    provenance: Optional[Provenance] = None
    properties: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        props = dict(self.properties)
        if "traces" in props:
            props["traces"] = [
                t.to_dict() if isinstance(t, Trace) else t for t in props["traces"]
            ]
        return {
            "id": self.id,
            "type": self.type,
            "label": self.label,
            "provenance": self.provenance.to_dict() if self.provenance else None,
            "properties": props,
        }

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "Node":
        prov = d.get("provenance")
        props = dict(d.get("properties", {}))
        if "traces" in props:
            props["traces"] = [
                t if isinstance(t, Trace) else Trace.from_dict(t) for t in props["traces"]
            ]
        return Node(
            id=d["id"],
            type=d["type"],
            label=d["label"],
            provenance=Provenance(**prov) if prov else None,
            properties=props,
        )


@dataclass
class Edge:
    source: str
    target: str
    type: str
    provenance: Optional[Provenance] = None
    strength: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source,
            "target": self.target,
            "type": self.type,
            "provenance": self.provenance.to_dict() if self.provenance else None,
            "strength": self.strength,
        }

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "Edge":
        prov = d.get("provenance")
        return Edge(
            source=d["source"],
            target=d["target"],
            type=d["type"],
            provenance=Provenance(**prov) if prov else None,
            strength=d.get("strength", 1.0),
        )


@dataclass
class ConflictEdge:
    """
    A recorded contradiction between two claims. Deliberately a distinct record
    from Edge: a conflict carries severity + evidence and is a first-class thing
    the gate blocks on, not a research relationship to render.
    """
    source_claim_id: str
    target_claim_id: str
    conflict_type: ConflictType
    severity: float                  # 0.0-1.0
    evidence: str
    resolved: bool = False
    resolution_note: str = ""
    detected_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["conflict_type"] = self.conflict_type.value
        return d

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "ConflictEdge":
        return ConflictEdge(
            source_claim_id=d["source_claim_id"],
            target_claim_id=d["target_claim_id"],
            conflict_type=ConflictType(d["conflict_type"]),
            severity=d["severity"],
            evidence=d["evidence"],
            resolved=d.get("resolved", False),
            resolution_note=d.get("resolution_note", ""),
            detected_at=d.get("detected_at", _now()),
        )


# ============================================================================
# FIELD SPECS — the declarative schema the gate's checks are shadowing
# ============================================================================

@dataclass
class FieldSpec:
    name: str
    py_type: Any
    required: bool = False
    enum: Optional[Type[Enum]] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None


NODE_SCHEMA: Dict[NodeType, List[FieldSpec]] = {
    NodeType.EXTRACTION_JOB: [
        FieldSpec("job_id", str, required=True),
        FieldSpec("paper_id", str, required=True),
        FieldSpec("extraction_type", str, required=True, enum=ExtractionType),
        FieldSpec("status", str, required=True, enum=JobStatus),
        FieldSpec("spawned_at", str),
        FieldSpec("worker_id", str),
        FieldSpec("completed_at", str),
        FieldSpec("result_count", int, min_value=0),
        FieldSpec("avg_confidence", float, min_value=0.0, max_value=1.0),
        FieldSpec("traces", list),
    ],
    NodeType.REVIEW_TASK: [
        FieldSpec("task_id", str, required=True),
        FieldSpec("extraction_job_id", str, required=True),
        FieldSpec("status", str, required=True, enum=ReviewStatus),
        FieldSpec("created_at", str),
        FieldSpec("reviewed_by", str),
        FieldSpec("reviewed_at", str),
        FieldSpec("gate_reason", str),
        FieldSpec("confidence_threshold_waived", bool),
        FieldSpec("waiver_reason", str),
        FieldSpec("review_notes", str),
    ],
    NodeType.PAPER: [
        FieldSpec("title", str, required=True),
        FieldSpec("url", str, required=True),
        FieldSpec("published", str),
        FieldSpec("authors", list),
    ],
    NodeType.CLAIM: [
        FieldSpec("text", str, required=True),
        FieldSpec("subject", str),
        FieldSpec("relation", str),
        FieldSpec("object", str),
    ],
    NodeType.CONCEPT: [FieldSpec("text", str, required=True)],
    NodeType.GAP: [FieldSpec("text", str, required=True)],
    NodeType.METHOD: [FieldSpec("text", str, required=True)],
    NodeType.DOMAIN: [FieldSpec("text", str, required=True)],
    NodeType.BENCHMARK: [FieldSpec("text", str, required=True)],
    NodeType.MEMORY_RECORD: [
        FieldSpec("memory_kind", str, required=True, enum=MemoryKind),
        FieldSpec("summary", str, required=True),
        FieldSpec("recorded_at", str, required=True),
        FieldSpec("subject_ref", str, required=True),
        FieldSpec("confidence", float, min_value=0.0, max_value=1.0),
        FieldSpec("details", dict),
    ],
}


# ============================================================================
# VALIDATION
# ============================================================================

@dataclass
class ValidationError:
    field_path: str
    code: str        # MISSING_REQUIRED | BAD_TYPE | NOT_IN_ENUM | OUT_OF_RANGE | UNKNOWN_TYPE
    message: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ValidationResult:
    valid: bool
    errors: List[ValidationError] = field(default_factory=list)

    def __bool__(self) -> bool:
        return self.valid

    @property
    def codes(self) -> List[str]:
        return [e.code for e in self.errors]

    def to_dict(self) -> Dict[str, Any]:
        return {"valid": self.valid, "errors": [e.to_dict() for e in self.errors]}


def _check_value(spec: FieldSpec, value: Any, path: str, errors: List[ValidationError]) -> None:
    if spec.py_type is float and isinstance(value, int) and not isinstance(value, bool):
        value = float(value)
    if spec.py_type is not None and not isinstance(value, spec.py_type):
        errors.append(ValidationError(
            path, "BAD_TYPE",
            f"{path} expected {spec.py_type.__name__}, got {type(value).__name__}",
        ))
        return
    if spec.enum is not None and value not in _enum_values(spec.enum):
        errors.append(ValidationError(
            path, "NOT_IN_ENUM",
            f"{path}={value!r} not one of {_enum_values(spec.enum)}",
        ))
        return
    if spec.min_value is not None and value < spec.min_value:
        errors.append(ValidationError(path, "OUT_OF_RANGE", f"{path}={value} < {spec.min_value}"))
    if spec.max_value is not None and value > spec.max_value:
        errors.append(ValidationError(path, "OUT_OF_RANGE", f"{path}={value} > {spec.max_value}"))


def validate_trace(trace: Any, path: str) -> List[ValidationError]:
    errors: List[ValidationError] = []
    d = trace.to_dict() if isinstance(trace, Trace) else trace
    if not isinstance(d, dict):
        return [ValidationError(path, "BAD_TYPE", f"{path} must be a Trace or dict")]
    for fname in TRACE_REQUIRED_FIELDS:
        if d.get(fname) in (None, ""):
            errors.append(ValidationError(f"{path}.{fname}", "MISSING_REQUIRED",
                                          f"trace missing required field '{fname}'"))
    dt = d.get("decision_type")
    if dt is not None and dt not in _enum_values(DecisionType):
        errors.append(ValidationError(f"{path}.decision_type", "NOT_IN_ENUM",
                                      f"decision_type={dt!r} not one of {_enum_values(DecisionType)}"))
    conf = d.get("confidence")
    if isinstance(conf, (int, float)) and not isinstance(conf, bool) and not (0.0 <= conf <= 1.0):
        errors.append(ValidationError(f"{path}.confidence", "OUT_OF_RANGE",
                                      f"confidence={conf} outside [0,1]"))
    return errors


def validate_node(node: Node) -> ValidationResult:
    """Structural validation. Says nothing about trust — that is the gate's job."""
    errors: List[ValidationError] = []

    if node.type not in _enum_values(NodeType):
        return ValidationResult(False, [ValidationError(
            "type", "UNKNOWN_TYPE",
            f"type={node.type!r} not one of {_enum_values(NodeType)}")])

    ntype = NodeType(node.type)
    props = node.properties or {}

    for spec in NODE_SCHEMA.get(ntype, []):
        path = f"properties.{spec.name}"
        if spec.name not in props or props[spec.name] is None:
            if spec.required:
                errors.append(ValidationError(path, "MISSING_REQUIRED",
                                              f"{node.type} requires '{spec.name}'"))
            continue
        _check_value(spec, props[spec.name], path, errors)

    for i, t in enumerate(props.get("traces", []) or []):
        errors.extend(validate_trace(t, f"properties.traces[{i}]"))

    if node.provenance is not None:
        pm = node.provenance.extraction_method
        if pm and pm not in _enum_values(ExtractionMethod):
            errors.append(ValidationError("provenance.extraction_method", "NOT_IN_ENUM",
                                          f"extraction_method={pm!r} not one of "
                                          f"{_enum_values(ExtractionMethod)}"))
        c = node.provenance.confidence
        if c is not None and not (0.0 <= c <= 1.0):
            errors.append(ValidationError("provenance.confidence", "OUT_OF_RANGE",
                                          f"confidence={c} outside [0,1]"))

    return ValidationResult(len(errors) == 0, errors)


def validate_edge(edge: Edge, node_index: Optional[Dict[str, Node]] = None) -> ValidationResult:
    errors: List[ValidationError] = []

    if edge.type not in _enum_values(EdgeType):
        return ValidationResult(False, [ValidationError(
            "type", "UNKNOWN_TYPE",
            f"type={edge.type!r} not one of {_enum_values(EdgeType)}")])

    etype = EdgeType(edge.type)

    if node_index is not None:
        for endpoint, nid in (("source", edge.source), ("target", edge.target)):
            if nid not in node_index:
                errors.append(ValidationError(endpoint, "MISSING_REQUIRED",
                                              f"{endpoint} node {nid!r} not in graph"))
        if etype in EDGE_ENDPOINT_CONTRACT and not errors:
            allowed_src, allowed_tgt = EDGE_ENDPOINT_CONTRACT[etype]
            src_t, tgt_t = node_index[edge.source].type, node_index[edge.target].type
            if src_t not in {t.value for t in allowed_src}:
                errors.append(ValidationError("source", "BAD_TYPE",
                    f"{etype.value} source must be one of "
                    f"{sorted(t.value for t in allowed_src)}, got {src_t!r}"))
            if tgt_t not in {t.value for t in allowed_tgt}:
                errors.append(ValidationError("target", "BAD_TYPE",
                    f"{etype.value} target must be one of "
                    f"{sorted(t.value for t in allowed_tgt)}, got {tgt_t!r}"))

    if not (0.0 <= edge.strength <= 1.0):
        errors.append(ValidationError("strength", "OUT_OF_RANGE",
                                      f"strength={edge.strength} outside [0,1]"))

    return ValidationResult(len(errors) == 0, errors)


def validate_conflict(conflict: ConflictEdge) -> ValidationResult:
    errors: List[ValidationError] = []
    if not conflict.source_claim_id:
        errors.append(ValidationError("source_claim_id", "MISSING_REQUIRED", "required"))
    if not conflict.target_claim_id:
        errors.append(ValidationError("target_claim_id", "MISSING_REQUIRED", "required"))
    if conflict.source_claim_id and conflict.source_claim_id == conflict.target_claim_id:
        errors.append(ValidationError("target_claim_id", "BAD_TYPE",
                                      "a claim cannot conflict with itself"))
    if not isinstance(conflict.conflict_type, ConflictType):
        errors.append(ValidationError("conflict_type", "NOT_IN_ENUM",
                                      f"must be a ConflictType, got {conflict.conflict_type!r}"))
    if not (0.0 <= conflict.severity <= 1.0):
        errors.append(ValidationError("severity", "OUT_OF_RANGE",
                                      f"severity={conflict.severity} outside [0,1]"))
    if not conflict.evidence:
        errors.append(ValidationError("evidence", "MISSING_REQUIRED",
                                      "a conflict must carry evidence for why it conflicts"))
    return ValidationResult(len(errors) == 0, errors)


# ============================================================================
# CONFLICT DETECTION (stub — real detection is Phase 4, worker-side)
# ============================================================================

# Antonym pairs sufficient to prove the plumbing; a real detector is LLM-side.
_POLARITY_PAIRS = [
    ("increases", "reduces"), ("increases", "decreases"),
    ("improves", "degrades"), ("enables", "prevents"),
    ("outperforms", "underperforms"),
]


def detect_conflicts_in_graph(nodes: List[Node]) -> List[ConflictEdge]:
    """
    Phase 3 stub. Detects only the trivial case: two claims with the same
    subject+object but opposed relation verbs. Real semantic contradiction
    detection is a worker (Phase 4) concern; this exists so the gate's
    CONFLICT_UNRESOLVED path has a real producer to wire against.
    """
    claims = [n for n in nodes if n.type == NodeType.CLAIM.value]
    found: List[ConflictEdge] = []

    for i, a in enumerate(claims):
        for b in claims[i + 1:]:
            sa, oa = a.properties.get("subject"), a.properties.get("object")
            sb, ob = b.properties.get("subject"), b.properties.get("object")
            if not (sa and oa) or (sa, oa) != (sb, ob):
                continue
            ra = (a.properties.get("relation") or "").lower()
            rb = (b.properties.get("relation") or "").lower()
            if any({ra, rb} == {x, y} for x, y in _POLARITY_PAIRS):
                found.append(ConflictEdge(
                    source_claim_id=a.id,
                    target_claim_id=b.id,
                    conflict_type=ConflictType.CONTRADICTS,
                    severity=0.9,
                    evidence=f"Opposed relation on same subject/object: "
                             f"'{sa} {ra} {oa}' vs '{sb} {rb} {ob}'",
                ))
    return found


# ============================================================================
# GRAPH CONTAINER
# ============================================================================

@dataclass
class ResearchGraph:
    nodes: List[Node] = field(default_factory=list)
    edges: List[Edge] = field(default_factory=list)
    conflicts: List[ConflictEdge] = field(default_factory=list)
    schema_version: str = SCHEMA_VERSION

    def index(self) -> Dict[str, Node]:
        return {n.id: n for n in self.nodes}

    def validate(self) -> ValidationResult:
        errors: List[ValidationError] = []
        idx = self.index()
        for n in self.nodes:
            for e in validate_node(n).errors:
                errors.append(ValidationError(f"nodes[{n.id}].{e.field_path}", e.code, e.message))
        for i, e_ in enumerate(self.edges):
            for e in validate_edge(e_, idx).errors:
                errors.append(ValidationError(f"edges[{i}].{e.field_path}", e.code, e.message))
        for i, c in enumerate(self.conflicts):
            for e in validate_conflict(c).errors:
                errors.append(ValidationError(f"conflicts[{i}].{e.field_path}", e.code, e.message))
        return ValidationResult(len(errors) == 0, errors)

    def unresolved_conflicts_for(self, node_id: str) -> List[ConflictEdge]:
        return [c for c in self.conflicts
                if not c.resolved and node_id in (c.source_claim_id, c.target_claim_id)]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "generated_at": _now(),
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": [e.to_dict() for e in self.edges],
            "conflicts": [c.to_dict() for c in self.conflicts],
        }

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "ResearchGraph":
        return ResearchGraph(
            nodes=[Node.from_dict(n) for n in d.get("nodes", [])],
            edges=[Edge.from_dict(e) for e in d.get("edges", [])],
            conflicts=[ConflictEdge.from_dict(c) for c in d.get("conflicts", [])],
            schema_version=d.get("schema_version", SCHEMA_VERSION),
        )


# ============================================================================
# JSON-SCHEMA EXPORT (generated, never hand-edited — see graph_schema.json)
# ============================================================================

_JSON_TYPE = {str: "string", int: "integer", float: "number",
              bool: "boolean", list: "array", dict: "object"}


def export_json_schema() -> Dict[str, Any]:
    """
    Emit graph_schema.json from the same FieldSpecs validate_node() uses, so the
    published schema and the enforced schema cannot drift apart.
    """
    defs: Dict[str, Any] = {}
    for ntype, specs in NODE_SCHEMA.items():
        props: Dict[str, Any] = {}
        for s in specs:
            entry: Dict[str, Any] = {"type": _JSON_TYPE[s.py_type]}
            if s.enum is not None:
                entry["enum"] = _enum_values(s.enum)
            if s.min_value is not None:
                entry["minimum"] = s.min_value
            if s.max_value is not None:
                entry["maximum"] = s.max_value
            if s.name == "traces":
                entry["items"] = {"$ref": "#/definitions/trace"}
            props[s.name] = entry
        defs[f"props_{ntype.value}"] = {
            "type": "object",
            "required": [s.name for s in specs if s.required],
            "properties": props,
        }

    defs["trace"] = {
        "type": "object",
        "required": TRACE_REQUIRED_FIELDS,
        "properties": {
            "trace_id": {"type": "string"},
            "decision_type": {"type": "string", "enum": _enum_values(DecisionType)},
            "worker_id": {"type": "string"},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            "reason_code": {"type": "string"},
            "reasoning_summary": {"type": "string"},
            "input_refs": {"type": "array", "items": {"type": "string"}},
            "output_refs": {"type": "array", "items": {"type": "string"}},
            "timestamp": {"type": "string", "format": "date-time"},
        },
    }
    defs["provenance"] = {
        "type": "object",
        "required": ["source_paper", "extraction_method", "confidence", "extracted_at"],
        "properties": {
            "source_paper": {"type": "string"},
            "extraction_method": {"type": "string", "enum": _enum_values(ExtractionMethod)},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            "extracted_at": {"type": "string", "format": "date-time"},
            "human_reviewed": {"type": "boolean", "default": False},
            "review_notes": {"type": "string"},
        },
    }
    defs["node"] = {
        "type": "object",
        "required": ["id", "type", "label"],
        "properties": {
            "id": {"type": "string"},
            "type": {"type": "string", "enum": _enum_values(NodeType)},
            "label": {"type": "string"},
            "provenance": {"$ref": "#/definitions/provenance"},
            "properties": {"type": "object"},
        },
        "allOf": [
            {"if": {"properties": {"type": {"const": nt.value}}},
             "then": {"properties": {"properties": {"$ref": f"#/definitions/props_{nt.value}"}}}}
            for nt in NODE_SCHEMA
        ],
    }
    defs["edge"] = {
        "type": "object",
        "required": ["source", "target", "type"],
        "properties": {
            "source": {"type": "string"},
            "target": {"type": "string"},
            "type": {"type": "string", "enum": _enum_values(EdgeType)},
            "provenance": {"$ref": "#/definitions/provenance"},
            "strength": {"type": "number", "minimum": 0, "maximum": 1},
        },
    }
    defs["conflict"] = {
        "type": "object",
        "required": ["source_claim_id", "target_claim_id", "conflict_type",
                     "severity", "evidence"],
        "properties": {
            "source_claim_id": {"type": "string"},
            "target_claim_id": {"type": "string"},
            "conflict_type": {"type": "string", "enum": _enum_values(ConflictType)},
            "severity": {"type": "number", "minimum": 0, "maximum": 1},
            "evidence": {"type": "string"},
            "resolved": {"type": "boolean", "default": False},
            "resolution_note": {"type": "string"},
            "detected_at": {"type": "string", "format": "date-time"},
        },
    }

    return {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": "Research Knowledge Graph Schema",
        "description": ("GENERATED by research_graph_schema.export_json_schema() — "
                        "do not hand-edit. Edit the FieldSpecs in NODE_SCHEMA instead, "
                        "so the published schema and the enforced schema stay identical."),
        "x-schema-version": SCHEMA_VERSION,
        "x-gate-control-edges": sorted(e.value for e in GATE_CONTROL_EDGES),
        "x-edge-endpoint-contract": {
            e.value: {"source": sorted(t.value for t in src),
                      "target": sorted(t.value for t in tgt)}
            for e, (src, tgt) in EDGE_ENDPOINT_CONTRACT.items()
        },
        "definitions": defs,
        "type": "object",
        "required": ["schema_version", "generated_at", "nodes", "edges"],
        "properties": {
            "schema_version": {"type": "string"},
            "generated_at": {"type": "string", "format": "date-time"},
            "nodes": {"type": "array", "items": {"$ref": "#/definitions/node"}},
            "edges": {"type": "array", "items": {"$ref": "#/definitions/edge"}},
            "conflicts": {"type": "array", "items": {"$ref": "#/definitions/conflict"}},
        },
    }


if __name__ == "__main__":
    import sys
    if "--emit-json-schema" in sys.argv:
        print(json.dumps(export_json_schema(), indent=2))
        raise SystemExit(0)

    import golden_fixtures as gf
    g = gf.build_fixture_graph()
    print(f"schema_version={SCHEMA_VERSION}")
    print(f"nodes={len(g.nodes)} edges={len(g.edges)} conflicts={len(g.conflicts)}")
    print(json.dumps(g.validate().to_dict(), indent=2)[:400])
