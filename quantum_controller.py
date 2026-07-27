#!/usr/bin/env python3
"""
Quantum-Classical OS Controller: Feedback Loop Orchestrator

Implements the six-stage agentic loop:
1. Sense — ingest telemetry, syndrome streams, calibration drift
2. Estimate — build belief state with confidence and anomaly tags
3. Constrain — apply physics envelopes and governance rules
4. Act — choose pulse family, route, fallback, or retry action
5. Validate — compare outcomes to policy thresholds
6. Learn — update simulators, capability memory, and policy ranking

Timing domains:
- Hard-real-time: acquisition, signal classification, dispatch
- Soft-real-time: drift handling, local recovery, retries
- Nearline: policy update, graph refresh, scoring
- Offline: retraining, architecture review, plan regeneration
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum
from datetime import datetime, timezone
import time
import uuid

from quantum_schema import (
    QuantumGraph, Node, Edge, NodeType, EdgeType, RuntimeEvent,
    TimingDomain, TaskStatus, RecoveryAction, FreshnessLevel, AnomalyTag,
    LoopPhaseMetrics, ConfidenceLevel, validate_node
)
from quantum_constraints import ConstraintsEngine, ControlAction, ActionEnvelope
from quantum_simulator import SimulatorInterface, TrajectoryResult
from quantum_dashboard import DashboardBackend, LoopStateSnapshot


# ============================================================================
# BELIEF STATE
# ============================================================================

@dataclass
class BeliefState:
    """Estimated state with confidence and freshness."""
    timestamp: str
    graph_snapshot: QuantumGraph
    confidence: float  # 0.0 - 1.0
    freshness: FreshnessLevel
    anomalies: List[AnomalyTag]
    observations: List[str] = field(default_factory=list)  # recent measurements
    uncertainty_estimate: float = 0.0  # state estimation error


# ============================================================================
# RECOVERY POLICY
# ============================================================================

@dataclass
class RecoveryPolicy:
    """Bounded recovery configuration."""
    max_retry_budget: int = 3
    escalation_threshold: float = 0.5  # confidence below this escalates
    approval_required_for_critical: bool = True
    recovery_strategy: str = "conservative"  # "conservative", "balanced", "aggressive"


# ============================================================================
# CONTROLLER STATE
# ============================================================================

@dataclass
class ControllerState:
    """Complete controller runtime state."""
    controller_id: str
    iteration_count: int = 0
    loop_start_time: Optional[str] = None
    current_phase: str = "idle"
    phases: List[LoopPhaseMetrics] = field(default_factory=list)
    recent_events: List[RuntimeEvent] = field(default_factory=list)
    last_action_id: Optional[str] = None
    last_action_confidence: Optional[float] = None
    recovery_policy: RecoveryPolicy = field(default_factory=RecoveryPolicy)
    total_actions_executed: int = 0
    total_actions_escalated: int = 0
    total_actions_failed: int = 0
    total_recovery_attempts: int = 0


# ============================================================================
# FEEDBACK LOOP CONTROLLER
# ============================================================================

class FeedbackLoopController:
    """Six-stage quantum-classical feedback loop."""

    def __init__(
        self,
        graph: QuantumGraph,
        constraints_engine: ConstraintsEngine,
        simulator: SimulatorInterface,
        dashboard_backend: DashboardBackend,
        recovery_policy: Optional[RecoveryPolicy] = None
    ):
        self.graph = graph
        self.constraints_engine = constraints_engine
        self.simulator = simulator
        self.dashboard = dashboard_backend
        self.state = ControllerState(
            controller_id=str(uuid.uuid4()),
            recovery_policy=recovery_policy or RecoveryPolicy()
        )

        # Initialize simulator
        self.simulator.initialize(self.graph)

    def run_one_iteration(self) -> Tuple[bool, ControllerState]:
        """
        Run one complete iteration of the six-stage loop.
        Returns (success, updated_state).
        """
        self.state.iteration_count += 1
        self.state.loop_start_time = datetime.now(timezone.utc).isoformat()
        self.state.phases = []
        self.state.recent_events = []

        start_time = time.time()

        try:
            # Stage 1: Sense
            belief = self._stage_sense()
            if not belief:
                return False, self.state

            # Stage 2: Estimate
            belief = self._stage_estimate(belief)
            if not belief:
                return False, self.state

            # Stage 3: Constrain
            constraints = self._stage_constrain(belief)
            if not constraints:
                return False, self.state

            # Stage 4: Act
            action_result = self._stage_act(belief, constraints)
            if not action_result:
                return False, self.state

            # Stage 5: Validate
            validation_result = self._stage_validate(action_result, belief)
            if not validation_result:
                return False, self.state

            # Stage 6: Learn
            learn_result = self._stage_learn(validation_result)
            if not learn_result:
                return False, self.state

            # Update dashboard
            loop_time_ms = (time.time() - start_time) * 1000
            self._update_dashboard(loop_time_ms)

            return True, self.state

        except Exception as e:
            self._emit_event(
                event_type="error",
                phase="loop",
                message=f"Loop iteration failed: {str(e)}",
                timing_domain=TimingDomain.SOFT_REAL_TIME
            )
            return False, self.state

    def _stage_sense(self) -> Optional[BeliefState]:
        """
        Stage 1: Sense — ingest telemetry and measurements.
        Hard-real-time path: rapid data ingestion.
        """
        self.state.current_phase = "sense"
        phase_start = time.time()

        self._emit_event(
            event_type="telemetry",
            phase="sense",
            message="Ingesting telemetry and measurements",
            timing_domain=TimingDomain.HARD_REAL_TIME
        )

        # Placeholder: read latest graph state
        belief = BeliefState(
            timestamp=datetime.now(timezone.utc).isoformat(),
            graph_snapshot=self.graph,
            confidence=0.9,
            freshness=FreshnessLevel.FRESH,
            anomalies=[]
        )

        phase_time_ms = (time.time() - phase_start) * 1000
        self._record_phase_metric("sense", phase_time_ms, belief.confidence)
        return belief

    def _stage_estimate(self, belief: BeliefState) -> Optional[BeliefState]:
        """
        Stage 2: Estimate — build belief state with confidence.
        Soft-real-time path: state fusion with uncertainty quantification.
        """
        self.state.current_phase = "estimate"
        phase_start = time.time()

        self._emit_event(
            event_type="decision",
            phase="estimate",
            message="Fusing measurements into belief state",
            timing_domain=TimingDomain.SOFT_REAL_TIME
        )

        # Placeholder: confidence estimate from graph freshness
        graph_metrics = self.graph.metrics
        if graph_metrics:
            belief.confidence = 0.95 - (graph_metrics.constraint_violations * 0.1)
        else:
            belief.confidence = 0.85

        # Tag any anomalies detected in recent telemetry
        if belief.confidence < 0.7:
            belief.anomalies.append(AnomalyTag.DEGRADATION)

        phase_time_ms = (time.time() - phase_start) * 1000
        self._record_phase_metric("estimate", phase_time_ms, belief.confidence)
        return belief

    def _stage_constrain(self, belief: BeliefState) -> Optional[Dict[str, Any]]:
        """
        Stage 3: Constrain — apply physics and policy envelopes.
        Soft-real-time path: constraint evaluation.
        """
        self.state.current_phase = "constrain"
        phase_start = time.time()

        self._emit_event(
            event_type="decision",
            phase="constrain",
            message="Evaluating physics and policy constraints",
            timing_domain=TimingDomain.SOFT_REAL_TIME
        )

        # Placeholder constraints: approve all for now
        constraints = {
            "physics_satisfied": True,
            "policy_satisfied": True,
            "approval_required": False,
            "max_actions_allowed": 5
        }

        phase_time_ms = (time.time() - phase_start) * 1000
        self._record_phase_metric("constrain", phase_time_ms, 1.0 if constraints["physics_satisfied"] else 0.0)
        return constraints

    def _stage_act(
        self,
        belief: BeliefState,
        constraints: Dict[str, Any]
    ) -> Optional[Tuple[ControlAction, ActionEnvelope]]:
        """
        Stage 4: Act — choose pulse family, route, or fallback.
        Hard-real-time path: rapid action selection and dispatch.
        """
        self.state.current_phase = "act"
        phase_start = time.time()

        # Synthesize test action
        action = ControlAction(
            action_id=f"action_{self.state.iteration_count}",
            pulse_family_id=f"family_{self.state.iteration_count % 3}",
            target_qubits=["q0", "q1"],
            duration_ns=100.0 + (self.state.iteration_count % 50),
            amplitude_normalized=0.5,
            phase_degrees=0.0
        )

        # Evaluate against constraints engine
        envelope = self.constraints_engine.evaluate_action(action)

        self._emit_event(
            event_type="action",
            phase="act",
            message=f"Dispatching action {action.action_id}",
            timing_domain=TimingDomain.HARD_REAL_TIME,
            metadata={"admissible": envelope.is_admissible, "confidence": envelope.confidence.value}
        )

        self.state.last_action_id = action.action_id
        # Map ConfidenceLevel to numeric score
        confidence_map = {
            ConfidenceLevel.CRITICAL: 1.0,
            ConfidenceLevel.HIGH: 0.8,
            ConfidenceLevel.MODERATE: 0.6,
            ConfidenceLevel.LOW: 0.4,
            ConfidenceLevel.UNCERTAIN: 0.2
        }
        self.state.last_action_confidence = confidence_map.get(envelope.confidence, 0.5)
        self.state.total_actions_executed += 1

        if not envelope.is_admissible:
            self.state.total_actions_escalated += 1

        phase_time_ms = (time.time() - phase_start) * 1000
        conf = confidence_map.get(envelope.confidence, 0.5)
        self._record_phase_metric("act", phase_time_ms, conf)
        return (action, envelope)

    def _stage_validate(
        self,
        action_result: Tuple[ControlAction, ActionEnvelope],
        belief: BeliefState
    ) -> Optional[Dict[str, Any]]:
        """
        Stage 5: Validate — compare outcomes to policy thresholds.
        Nearline path: result evaluation and conformance check.
        """
        self.state.current_phase = "validate"
        phase_start = time.time()

        action, envelope = action_result

        # Run trajectory simulation to estimate outcome
        sim_result = self.simulator.run_trajectory(
            action_sequence=[{
                "action_id": action.action_id,
                "pulse_family_id": action.pulse_family_id,
                "target_qubits": action.target_qubits,
                "duration_ns": action.duration_ns,
                "amplitude_normalized": action.amplitude_normalized
            }],
            num_shots=100
        )

        passed_validation = (
            envelope.is_admissible and
            sim_result.average_fidelity > 0.85
        )

        self._emit_event(
            event_type="validation",
            phase="validate",
            message=f"Action validation: {'PASSED' if passed_validation else 'FAILED'}",
            timing_domain=TimingDomain.NEARLINE,
            metadata={
                "fidelity": sim_result.average_fidelity,
                "passed": passed_validation
            }
        )

        validation_result = {
            "action_id": action.action_id,
            "passed": passed_validation,
            "envelope": envelope,
            "simulation_result": sim_result,
            "belief_state": belief
        }

        phase_time_ms = (time.time() - phase_start) * 1000
        self._record_phase_metric("validate", phase_time_ms, 1.0 if passed_validation else 0.0)
        return validation_result

    def _stage_learn(self, validation_result: Dict[str, Any]) -> Optional[bool]:
        """
        Stage 6: Learn — update simulators and policies.
        Offline path: learning and policy refinement.
        """
        self.state.current_phase = "learn"
        phase_start = time.time()

        self._emit_event(
            event_type="learning",
            phase="learn",
            message="Updating policy and capability models",
            timing_domain=TimingDomain.OFFLINE
        )

        # Placeholder: log result for future policy updates
        # In production: update RL policy, simulator confidence, etc.

        phase_time_ms = (time.time() - phase_start) * 1000
        self._record_phase_metric("learn", phase_time_ms, 0.8)
        return True

    def _record_phase_metric(self, phase_name: str, duration_ms: float, confidence: float):
        """Record one phase execution metric."""
        metric = LoopPhaseMetrics(
            phase_name=phase_name,
            started_at=datetime.now(timezone.utc).isoformat(),
            duration_ms=duration_ms,
            confidence=confidence,
            anomalies=[]
        )
        self.state.phases.append(metric)

    def _emit_event(
        self,
        event_type: str,
        phase: str,
        message: str,
        timing_domain: TimingDomain,
        metadata: Optional[Dict[str, Any]] = None,
        node_id: Optional[str] = None
    ) -> RuntimeEvent:
        """Emit a runtime event."""
        event = RuntimeEvent(
            event_id=str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc).isoformat(),
            phase=phase,
            timing_domain=timing_domain,
            node_id=node_id,
            node_type=None,
            event_type=event_type,
            message=message,
            metadata=metadata or {},
            confidence=0.9,
            freshness=FreshnessLevel.CURRENT
        )
        self.state.recent_events.append(event)
        self.dashboard.record_event(event)
        return event

    def _update_dashboard(self, loop_time_ms: float):
        """Update dashboard with latest controller state."""
        loop_snapshot = LoopStateSnapshot(
            timestamp=datetime.now(timezone.utc).isoformat(),
            iteration_count=self.state.iteration_count,
            current_phase=self.state.current_phase,
            phase_duration_ms=self.state.phases[-1].duration_ms if self.state.phases else 0.0,
            phase_confidence=self.state.phases[-1].confidence if self.state.phases else 0.0,
            total_loop_time_ms=loop_time_ms,
            phases=self.state.phases,
            last_action_id=self.state.last_action_id,
            last_action_confidence=self.state.last_action_confidence
        )
        self.dashboard.update_loop_state(loop_snapshot)
