#!/usr/bin/env python3
"""
Physics Constraints Engine: Admissible Actions & Envelopes

Evaluates control actions, pulse families, and routing decisions against:
- Qubit coupling constraints
- Resonator frequency separation
- Control line bandwidth and timing
- Cryogenic temperature envelopes
- Policy & governance rules

Pluggable constraint evaluators; default is a deterministic physics-first pass.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Callable, Any
from enum import Enum
import math

from quantum_schema import (
    Node, Edge, NodeType, EdgeType, ConstraintViolation,
    QuantumGraph, ConfidenceLevel
)


# ============================================================================
# CONSTRAINT TYPES
# ============================================================================

class ConstraintType(str, Enum):
    """Physical and policy constraints."""
    # Physical constraints
    COUPLING_ALLOWED = "coupling_allowed"
    FREQUENCY_SEPARATION = "frequency_separation"
    BANDWIDTH_LIMIT = "bandwidth_limit"
    TIMING_CRITICAL = "timing_critical"
    TEMPERATURE_ENVELOPE = "temperature_envelope"
    INTERFERENCE_RISK = "interference_risk"

    # Policy constraints
    GOVERNANCE_RULE = "governance_rule"
    APPROVAL_REQUIRED = "approval_required"
    LATENCY_CAP = "latency_cap"
    RETRY_BUDGET = "retry_budget"


class ConstraintSeverity(str, Enum):
    """Constraint violation severity."""
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


# ============================================================================
# CONSTRAINT MODELS
# ============================================================================

@dataclass
class PhysicsProfile:
    """Device physics parameters."""
    qubit_count: int
    resonator_count: int
    coupling_map: Dict[str, List[str]]  # qubit_id -> [coupled_qubit_ids]
    detuning_mhz: Dict[str, float]  # qubit_id -> frequency offset
    control_line_bandwidth_ghz: float
    t1_microseconds: Dict[str, float]  # qubit_id -> coherence time
    t2_microseconds: Dict[str, float]  # qubit_id -> dephasing time


@dataclass
class CryoProfile:
    """Cryogenic system parameters."""
    base_temperature_mk: float
    cryo_stages: List[str]  # ["4K", "1K", "100mK", "10mK"]
    temperature_distribution: Dict[str, float]  # stage -> temp in mK


@dataclass
class ControlAction:
    """Proposed control action to evaluate."""
    action_id: str
    pulse_family_id: str
    target_qubits: List[str]
    duration_ns: float
    amplitude_normalized: float  # 0.0 - 1.0
    phase_degrees: float
    routing_path: Optional[List[str]] = None  # qubit sequence for CNOT chains
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConstraintEvaluation:
    """Single constraint evaluation result."""
    constraint_type: ConstraintType
    passed: bool
    confidence: float  # 0.0 - 1.0
    severity: ConstraintSeverity
    message: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ActionEnvelope:
    """Complete set of admissible actions and constraints."""
    action_id: str
    is_admissible: bool
    confidence: ConfidenceLevel
    constraints_passed: int
    constraints_failed: int
    constraint_evals: List[ConstraintEvaluation] = field(default_factory=list)
    violations: List[ConstraintViolation] = field(default_factory=list)
    recommended_retries: int = 0
    fallback_actions: List[str] = field(default_factory=list)

    def to_dict(self):
        return {
            "action_id": self.action_id,
            "is_admissible": self.is_admissible,
            "confidence": self.confidence.value,
            "constraints_passed": self.constraints_passed,
            "constraints_failed": self.constraints_failed,
            "constraint_evals": [
                {
                    "constraint_type": c.constraint_type.value,
                    "passed": c.passed,
                    "confidence": c.confidence,
                    "severity": c.severity.value,
                    "message": c.message
                }
                for c in self.constraint_evals
            ],
            "violations": [v.to_dict() for v in self.violations],
            "recommended_retries": self.recommended_retries,
            "fallback_actions": self.fallback_actions
        }


# ============================================================================
# CONSTRAINTS ENGINE
# ============================================================================

class ConstraintsEngine:
    """Evaluate proposed actions against physics and policy constraints."""

    def __init__(
        self,
        graph: QuantumGraph,
        physics_profile: PhysicsProfile,
        cryo_profile: CryoProfile
    ):
        self.graph = graph
        self.physics = physics_profile
        self.cryo = cryo_profile
        self.constraint_evals: List[Callable] = []
        self._register_default_constraints()

    def _register_default_constraints(self):
        """Register deterministic physics-first constraints."""
        self.constraint_evals = [
            self._check_coupling_allowed,
            self._check_frequency_separation,
            self._check_bandwidth_limit,
            self._check_temperature_envelope,
            self._check_interference_risk,
        ]

    def register_constraint(self, evaluator: Callable[[ControlAction], ConstraintEvaluation]):
        """Register custom constraint evaluator."""
        self.constraint_evals.append(evaluator)

    def evaluate_action(self, action: ControlAction) -> ActionEnvelope:
        """Evaluate proposed action against all registered constraints."""
        evals = []
        failures = 0

        for evaluator in self.constraint_evals:
            try:
                result = evaluator(action)
                evals.append(result)
                if not result.passed:
                    failures += 1
            except Exception as e:
                # Constraint evaluation error: treat as failure
                evals.append(
                    ConstraintEvaluation(
                        constraint_type=ConstraintType.GOVERNANCE_RULE,
                        passed=False,
                        confidence=0.0,
                        severity=ConstraintSeverity.ERROR,
                        message=f"Constraint evaluation error: {str(e)}"
                    )
                )
                failures += 1

        # Determine overall admissibility
        is_admissible = failures == 0
        passed_count = len(evals) - failures

        # Map failure count to confidence level
        if failures == 0:
            confidence = ConfidenceLevel.CRITICAL
        elif failures == 1 and len(evals) >= 3:
            confidence = ConfidenceLevel.HIGH
        elif failures == 1:
            confidence = ConfidenceLevel.MODERATE
        else:
            confidence = ConfidenceLevel.LOW

        # Build violations
        violations = [
            ConstraintViolation(
                violation_id=f"{action.action_id}_violation_{i}",
                timestamp=__import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat(),
                constraint_type=e.constraint_type.value,
                node_id=None,
                edge_id=None,
                message=e.message,
                severity=e.severity.value,
                metadata=e.metadata
            )
            for i, e in enumerate(evals) if not e.passed
        ]

        # Determine retry budget based on constraint type
        recommended_retries = 0
        if not is_admissible:
            if failures == 1 and evals[failures - 1].constraint_type == ConstraintType.TIMING_CRITICAL:
                recommended_retries = 3  # Timing issues often resolve on retry
            elif failures == 1 and evals[failures - 1].constraint_type == ConstraintType.INTERFERENCE_RISK:
                recommended_retries = 2

        envelope = ActionEnvelope(
            action_id=action.action_id,
            is_admissible=is_admissible,
            confidence=confidence,
            constraints_passed=passed_count,
            constraints_failed=failures,
            constraint_evals=evals,
            violations=violations,
            recommended_retries=recommended_retries
        )

        return envelope

    def _check_coupling_allowed(self, action: ControlAction) -> ConstraintEvaluation:
        """Check if target qubits can be coupled for this operation."""
        if len(action.target_qubits) <= 1:
            # Single-qubit gates always allowed
            return ConstraintEvaluation(
                constraint_type=ConstraintType.COUPLING_ALLOWED,
                passed=True,
                confidence=1.0,
                severity=ConstraintSeverity.WARNING,
                message="Single-qubit operation, no coupling constraints"
            )

        # For multi-qubit ops, check coupling map
        for i in range(len(action.target_qubits) - 1):
            q1, q2 = action.target_qubits[i], action.target_qubits[i + 1]
            allowed = q2 in self.physics.coupling_map.get(q1, [])
            if not allowed:
                return ConstraintEvaluation(
                    constraint_type=ConstraintType.COUPLING_ALLOWED,
                    passed=False,
                    confidence=0.0,
                    severity=ConstraintSeverity.CRITICAL,
                    message=f"Qubits {q1} and {q2} not coupled in this device",
                    metadata={"qubit_1": q1, "qubit_2": q2}
                )

        return ConstraintEvaluation(
            constraint_type=ConstraintType.COUPLING_ALLOWED,
            passed=True,
            confidence=1.0,
            severity=ConstraintSeverity.WARNING,
            message="All target qubits properly coupled"
        )

    def _check_frequency_separation(self, action: ControlAction) -> ConstraintEvaluation:
        """Check resonator-qubit frequency separation."""
        min_separation_mhz = 10.0  # Minimum detuning for safety

        for qubit_id in action.target_qubits:
            offset = self.physics.detuning_mhz.get(qubit_id, 0.0)
            if abs(offset) < min_separation_mhz:
                return ConstraintEvaluation(
                    constraint_type=ConstraintType.FREQUENCY_SEPARATION,
                    passed=False,
                    confidence=0.5,
                    severity=ConstraintSeverity.WARNING,
                    message=f"Qubit {qubit_id} frequency too close to resonator (offset: {offset} MHz)",
                    metadata={"qubit_id": qubit_id, "offset_mhz": offset}
                )

        return ConstraintEvaluation(
            constraint_type=ConstraintType.FREQUENCY_SEPARATION,
            passed=True,
            confidence=1.0,
            severity=ConstraintSeverity.WARNING,
            message="All qubits properly detuned from resonators"
        )

    def _check_bandwidth_limit(self, action: ControlAction) -> ConstraintEvaluation:
        """Check control line bandwidth limits."""
        # Estimate bandwidth usage: pulse duration and amplitude
        # More realistic model: bandwidth = (amplitude * rise_time_ns) / duration_ns
        # where rise_time ~ 2ns for realistic control envelopes
        estimated_bandwidth_ghz = (action.amplitude_normalized * 0.002) / (action.duration_ns / 1000.0)

        if estimated_bandwidth_ghz > self.physics.control_line_bandwidth_ghz:
            return ConstraintEvaluation(
                constraint_type=ConstraintType.BANDWIDTH_LIMIT,
                passed=False,
                confidence=0.8,
                severity=ConstraintSeverity.ERROR,
                message=f"Estimated bandwidth {estimated_bandwidth_ghz:.3f} GHz exceeds device limit {self.physics.control_line_bandwidth_ghz:.3f} GHz",
                metadata={"estimated_ghz": estimated_bandwidth_ghz, "limit_ghz": self.physics.control_line_bandwidth_ghz}
            )

        return ConstraintEvaluation(
            constraint_type=ConstraintType.BANDWIDTH_LIMIT,
            passed=True,
            confidence=1.0,
            severity=ConstraintSeverity.WARNING,
            message="Control pulse within bandwidth limits"
        )

    def _check_temperature_envelope(self, action: ControlAction) -> ConstraintEvaluation:
        """Check cryogenic temperature requirements."""
        # T2 coherence requires millikelvin temperatures
        base_temp_mk = self.cryo.base_temperature_mk

        if base_temp_mk > 50.0:
            return ConstraintEvaluation(
                constraint_type=ConstraintType.TEMPERATURE_ENVELOPE,
                passed=False,
                confidence=0.9,
                severity=ConstraintSeverity.CRITICAL,
                message=f"Base temperature {base_temp_mk:.1f} mK too warm for coherent operations",
                metadata={"base_temp_mk": base_temp_mk}
            )

        return ConstraintEvaluation(
            constraint_type=ConstraintType.TEMPERATURE_ENVELOPE,
            passed=True,
            confidence=1.0,
            severity=ConstraintSeverity.WARNING,
            message=f"Temperature envelope OK: {base_temp_mk:.1f} mK"
        )

    def _check_interference_risk(self, action: ControlAction) -> ConstraintEvaluation:
        """Check for crosstalk and interference risks."""
        # Simple heuristic: if >3 qubits active, risk of crosstalk
        if len(action.target_qubits) > 3:
            # Risk increases with number of qubits
            risk_score = min(1.0, (len(action.target_qubits) - 3) / 10.0)
            if risk_score > 0.3:
                return ConstraintEvaluation(
                    constraint_type=ConstraintType.INTERFERENCE_RISK,
                    passed=False,
                    confidence=0.6,
                    severity=ConstraintSeverity.WARNING,
                    message=f"High interference risk with {len(action.target_qubits)} active qubits (risk: {risk_score:.2%})",
                    metadata={"active_qubits": len(action.target_qubits), "risk_score": risk_score}
                )

        return ConstraintEvaluation(
            constraint_type=ConstraintType.INTERFERENCE_RISK,
            passed=True,
            confidence=0.9,
            severity=ConstraintSeverity.WARNING,
            message="Interference risk within acceptable bounds"
        )


def default_constraints_engine(
    graph: QuantumGraph,
    qubit_count: int = 5,
    resonator_count: int = 5
) -> ConstraintsEngine:
    """Create default constraints engine with simulation parameters."""
    physics = PhysicsProfile(
        qubit_count=qubit_count,
        resonator_count=resonator_count,
        coupling_map={
            f"q{i}": [f"q{i+1}" if i < qubit_count - 1 else ""]
            for i in range(qubit_count)
        },
        detuning_mhz={f"q{i}": 50.0 + i * 10 for i in range(qubit_count)},
        control_line_bandwidth_ghz=2.0,
        t1_microseconds={f"q{i}": 50.0 for i in range(qubit_count)},
        t2_microseconds={f"q{i}": 30.0 for i in range(qubit_count)}
    )

    cryo = CryoProfile(
        base_temperature_mk=15.0,
        cryo_stages=["4K", "1K", "100mK", "10mK"],
        temperature_distribution={"4K": 4.0, "1K": 1.0, "100mK": 0.1, "10mK": 0.015}
    )

    return ConstraintsEngine(graph, physics, cryo)
