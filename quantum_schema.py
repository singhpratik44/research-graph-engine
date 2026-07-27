#!/usr/bin/env python3
"""
Quantum-Classical OS Controller: Shared State-Graph Schema

Defines node/edge types and contracts for the layered graph model:
- Physical graph (qubits, resonators, coupling)
- Logical graph (circuits, graph states, pulse families)
- Workflow DAG (tasks, retries, approvals)
- Capability graph (devices, workloads, confidence)
- Governance graph (roles, policies, approvals)

All layers use closed enums and structured traces for observability.
Schema version: 1.0.0
"""

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum
from datetime import datetime, timezone
import json

SCHEMA_VERSION = "1.0.0"


# ============================================================================
# NODE TYPES
# ============================================================================

class NodeType(str, Enum):
    """All node types across layered graph."""
    # Physical layer
    QUBIT = "qubit"
    RESONATOR = "resonator"
    CONTROL_LINE = "control_line"
    CRYO_TIER = "cryo_tier"

    # Logical layer
    CIRCUIT = "circuit"
    GRAPH_STATE = "graph_state"
    DECODER = "decoder"
    PULSE_FAMILY = "pulse_family"

    # Workflow layer
    WORKFLOW_TASK = "workflow_task"
    RETRY_RECORD = "retry_record"
    APPROVAL_RECORD = "approval_record"
    VALIDATION_RECORD = "validation_record"

    # Capability layer
    DEVICE = "device"
    WORKLOAD = "workload"
    CAPABILITY_RECORD = "capability_record"
    EMBEDDING = "embedding"

    # Governance layer
    ROLE = "role"
    POLICY = "policy"
    MISSION = "mission"
    APPROVAL_NODE = "approval_node"

    # Runtime state
    TELEMETRY_EVENT = "telemetry_event"
    RUNTIME_STATE = "runtime_state"
    RECOVERY_ACTION = "recovery_action"
    PIV_STAGE = "piv_stage"


class EdgeType(str, Enum):
    """Graph edges connecting layers."""
    # Physical layer
    COUPLES = "couples"  # qubit -> qubit
    RESONATES_WITH = "resonates_with"  # resonator -> qubit
    CONTROLLED_BY = "controlled_by"  # qubit -> control_line
    THERMALLY_COUPLED = "thermally_coupled"  # cryo_tier -> cryo_tier

    # Logical layer
    IMPLEMENTS = "implements"  # circuit -> pulse_family
    DECODES = "decodes"  # decoder -> graph_state
    SUBSTITUTES = "substitutes"  # pulse_family -> pulse_family
    COMMUTES_WITH = "commutes_with"  # logical op -> logical op

    # Workflow layer
    DEPENDS_ON = "depends_on"  # task -> task
    RETRIED_FROM = "retried_from"  # retry_record -> task
    APPROVED_BY = "approved_by"  # approval_record -> approval_node
    VALIDATES = "validates"  # validation_record -> any node

    # Capability & governance
    SUITABLE_FOR = "suitable_for"  # device -> workload
    SIMILAR_TO = "similar_to"  # capability_record -> capability_record
    AUTHORIZES = "authorizes"  # role -> mission
    REQUIRES_APPROVAL = "requires_approval"  # mission -> approval_node

    # Cross-layer
    SUPERVISES = "supervises"  # governance -> workflow
    CONSTRAINS = "constrains"  # policy -> capability
    MEASURES = "measures"  # telemetry_event -> runtime_state
    TRIGGERS = "triggers"  # runtime_state -> recovery_action


# ============================================================================
# ENUMS
# ============================================================================

class TimingDomain(str, Enum):
    """Real-time classification."""
    HARD_REAL_TIME = "hard_real_time"
    SOFT_REAL_TIME = "soft_real_time"
    NEARLINE = "nearline"
    OFFLINE = "offline"


class TaskStatus(str, Enum):
    """Workflow task status."""
    PENDING = "pending"
    AUTHORIZED = "authorized"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    ESCALATED = "escalated"
    RETRIED = "retried"


class RecoveryAction(str, Enum):
    """Recovery classification."""
    RETRY = "retry"
    ROLLBACK = "rollback"
    FALLBACK = "fallback"
    ESCALATE = "escalate"
    MANUAL_INTERVENTION = "manual_intervention"


class PIVStage(str, Enum):
    """Prototype-Integrate-Validate lifecycle."""
    PROTOTYPE = "prototype"
    INTEGRATE = "integrate"
    VALIDATE = "validate"
    SCALE = "scale"


class ConfidenceLevel(str, Enum):
    """Action confidence scoring."""
    CRITICAL = "critical"  # >= 0.95
    HIGH = "high"  # >= 0.80
    MODERATE = "moderate"  # >= 0.60
    LOW = "low"  # >= 0.40
    UNCERTAIN = "uncertain"  # < 0.40


class FreshnessLevel(str, Enum):
    """Graph/state freshness."""
    CURRENT = "current"  # < 1ms
    FRESH = "fresh"  # < 10ms
    RECENT = "recent"  # < 100ms
    STALE = "stale"  # >= 100ms


class AnomalyTag(str, Enum):
    """Telemetry anomaly classification."""
    NONE = "none"
    DRIFT = "drift"
    DEGRADATION = "degradation"
    FAULT = "fault"
    UNKNOWN = "unknown"


# ============================================================================
# STRUCTURED EVENTS & TRACES
# ============================================================================

@dataclass
class ServiceMetrics:
    """One service's current observability snapshot."""
    service_name: str
    healthy: bool
    latency_ms: float
    error_count: int
    last_update_timestamp: str

    def to_dict(self):
        return asdict(self)


@dataclass
class GraphMetrics:
    """Graph layer health snapshot."""
    total_nodes: int
    total_edges: int
    freshness: FreshnessLevel
    staleness_seconds: float
    constraint_violations: int

    def to_dict(self):
        return asdict(self)


@dataclass
class LoopPhaseMetrics:
    """Per-phase feedback loop timing and confidence."""
    phase_name: str  # "sense", "estimate", "constrain", "act", "validate", "learn"
    started_at: str
    duration_ms: float
    confidence: float  # 0.0 - 1.0
    anomalies: List[AnomalyTag]

    def to_dict(self):
        return {
            "phase_name": self.phase_name,
            "started_at": self.started_at,
            "duration_ms": self.duration_ms,
            "confidence": self.confidence,
            "anomalies": [a.value for a in self.anomalies]
        }


@dataclass
class RuntimeEvent:
    """One discrete runtime event with full trace."""
    event_id: str
    timestamp: str
    phase: str  # sense, estimate, constrain, act, validate, learn
    timing_domain: TimingDomain
    node_id: Optional[str]
    node_type: Optional[NodeType]
    event_type: str  # "telemetry", "decision", "action", "recovery", "validation"
    message: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0
    freshness: FreshnessLevel = FreshnessLevel.CURRENT
    anomalies: List[AnomalyTag] = field(default_factory=list)

    def to_dict(self):
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp,
            "phase": self.phase,
            "timing_domain": self.timing_domain.value,
            "node_id": self.node_id,
            "node_type": self.node_type.value if self.node_type else None,
            "event_type": self.event_type,
            "message": self.message,
            "metadata": self.metadata,
            "confidence": self.confidence,
            "freshness": self.freshness.value,
            "anomalies": [a.value for a in self.anomalies]
        }


# ============================================================================
# NODE & EDGE DEFINITIONS
# ============================================================================

@dataclass
class Node:
    """Graph node with schema conformance."""
    node_id: str
    node_type: NodeType
    label: str
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    # Observability
    confidence: Optional[float] = None  # 0.0 - 1.0, if applicable
    freshness: FreshnessLevel = FreshnessLevel.CURRENT
    anomalies: List[AnomalyTag] = field(default_factory=list)

    # Provenance
    source: Optional[str] = None
    version: int = 1

    # Schema-specific metadata (subclasses override)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self):
        return {
            "node_id": self.node_id,
            "node_type": self.node_type.value,
            "label": self.label,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "confidence": self.confidence,
            "freshness": self.freshness.value,
            "anomalies": [a.value for a in self.anomalies],
            "source": self.source,
            "version": self.version,
            "metadata": self.metadata
        }


@dataclass
class Edge:
    """Graph edge with schema conformance."""
    edge_id: str
    source_id: str
    target_id: str
    edge_type: EdgeType
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    # Metadata
    weight: float = 1.0
    confidence: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self):
        return {
            "edge_id": self.edge_id,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "edge_type": self.edge_type.value,
            "created_at": self.created_at,
            "weight": self.weight,
            "confidence": self.confidence,
            "metadata": self.metadata
        }


@dataclass
class ConstraintViolation:
    """Policy or physics constraint violation."""
    violation_id: str
    timestamp: str
    constraint_type: str
    node_id: Optional[str]
    edge_id: Optional[str]
    message: str
    severity: str  # "warning", "error", "critical"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self):
        return asdict(self)


# ============================================================================
# VALIDATION CONTRACT
# ============================================================================

@dataclass
class ValidationError:
    """Structured validation error."""
    field: str
    error_code: str
    message: str
    expected_type: Optional[str] = None
    received_value: Optional[str] = None


def validate_node(node: Node) -> Tuple[bool, List[ValidationError]]:
    """Validate node against schema contract."""
    errors = []

    if not node.node_id:
        errors.append(ValidationError("node_id", "REQUIRED", "node_id is required"))

    if not node.label:
        errors.append(ValidationError("label", "REQUIRED", "label is required"))

    if node.confidence is not None and not (0.0 <= node.confidence <= 1.0):
        errors.append(
            ValidationError(
                "confidence",
                "OUT_OF_RANGE",
                "confidence must be between 0.0 and 1.0",
                expected_type="float[0.0-1.0]",
                received_value=str(node.confidence)
            )
        )

    return len(errors) == 0, errors


def validate_edge(edge: Edge, graph: 'QuantumGraph') -> Tuple[bool, List[ValidationError]]:
    """Validate edge against schema contract."""
    errors = []

    if not edge.edge_id:
        errors.append(ValidationError("edge_id", "REQUIRED", "edge_id is required"))

    source = graph.get_node(edge.source_id)
    target = graph.get_node(edge.target_id)

    if source is None:
        errors.append(
            ValidationError("source_id", "NOT_FOUND", f"source node {edge.source_id} not found")
        )

    if target is None:
        errors.append(
            ValidationError("target_id", "NOT_FOUND", f"target node {edge.target_id} not found")
        )

    return len(errors) == 0, errors


# ============================================================================
# GRAPH REGISTRY CONTRACT
# ============================================================================

@dataclass
class QuantumGraph:
    """Shared state-graph registry."""
    graph_id: str
    nodes: Dict[str, Node] = field(default_factory=dict)
    edges: Dict[str, Edge] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    # Runtime state
    metrics: Optional[GraphMetrics] = None
    constraint_violations: List[ConstraintViolation] = field(default_factory=list)

    def add_node(self, node: Node) -> Tuple[bool, List[ValidationError]]:
        """Add node with validation."""
        valid, errors = validate_node(node)
        if not valid:
            return False, errors

        self.nodes[node.node_id] = node
        self.updated_at = datetime.now(timezone.utc).isoformat()
        return True, []

    def add_edge(self, edge: Edge) -> Tuple[bool, List[ValidationError]]:
        """Add edge with validation."""
        valid, errors = validate_edge(edge, self)
        if not valid:
            return False, errors

        self.edges[edge.edge_id] = edge
        self.updated_at = datetime.now(timezone.utc).isoformat()
        return True, []

    def get_node(self, node_id: str) -> Optional[Node]:
        """Get node by id."""
        return self.nodes.get(node_id)

    def get_edge(self, edge_id: str) -> Optional[Edge]:
        """Get edge by id."""
        return self.edges.get(edge_id)

    def neighbors(self, node_id: str, edge_type: Optional[EdgeType] = None) -> List[str]:
        """Get neighbor node ids."""
        neighbors = []
        for edge in self.edges.values():
            if edge.source_id == node_id:
                if edge_type is None or edge.edge_type == edge_type:
                    neighbors.append(edge.target_id)
        return neighbors

    def to_dict(self):
        return {
            "graph_id": self.graph_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "node_count": len(self.nodes),
            "edge_count": len(self.edges),
            "metrics": self.metrics.to_dict() if self.metrics else None,
            "constraint_violations": [v.to_dict() for v in self.constraint_violations]
        }
