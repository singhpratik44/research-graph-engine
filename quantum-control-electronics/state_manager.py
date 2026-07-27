"""State Manager for Quantum Control

Maintains classical simulation of quantum state to:
1. Predict measurement outcomes before measurement
2. Detect measurement errors (prediction != actual)
3. Trigger corrective control when state diverges from prediction
4. Enable closed-loop feedback control

This module enables deterministic quantum control: we always know what
state we expect, we measure to verify, and we correct if needed.
"""

from dataclasses import dataclass, field
from typing import List, Tuple, Dict
from enum import Enum


class MeasurementResultEnum(Enum):
    """Measurement outcome"""
    ZERO = 0
    ONE = 1
    ERROR = -1  # Couldn't measure (trap empty, etc)


@dataclass
class QuantumState:
    """Classical representation of quantum state for one qubit"""
    qubit_id: int
    predicted_state: int  # 0 or 1
    confidence: float  # 0.0 to 1.0 (fidelity)
    last_measurement: int = -1  # -1 = no measurement yet
    measurement_time_us: float = 0.0
    measurement_error_count: int = 0  # Times prediction != measurement


@dataclass
class FeedbackAction:
    """Corrective action when prediction diverges from measurement"""
    action_id: int
    qubit_id: int
    action_type: str  # "bit_flip", "phase_correction", "reinit", "discard"
    timestamp_us: float
    reason: str
    success: bool = False


class StateManager:
    """
    Manages predicted quantum state and closed-loop feedback.

    Key insight: Classic simulation tells us what state we *expect*.
    Measurement tells us what we *actually got*.
    If they differ, something went wrong and we need corrective action.
    """

    def __init__(self, num_qubits: int = 100):
        self.num_qubits = num_qubits
        self.states: List[QuantumState] = [
            QuantumState(qubit_id=i, predicted_state=0, confidence=0.99) for i in range(num_qubits)
        ]

        # Track measurement history
        self.measurement_history: Dict[int, List[Tuple[int, float]]] = {
            i: [] for i in range(num_qubits)
        }

        # Track state divergences
        self.divergence_events: List[Dict] = []

        # Feedback actions taken
        self.feedback_actions: List[FeedbackAction] = []

        # Current time
        self.time_us = 0.0

    def set_predicted_state(self, qubit_id: int, state: int, confidence: float) -> None:
        """Set the predicted state (result of classical simulation)"""
        self.states[qubit_id].predicted_state = state
        self.states[qubit_id].confidence = min(1.0, max(0.0, confidence))

    def record_measurement(
        self, qubit_id: int, measured_state: int, measurement_time_us: float
    ) -> Tuple[bool, str]:
        """
        Record actual measurement outcome and compare to prediction.
        Returns: (prediction_matched, feedback_needed)
        """
        state = self.states[qubit_id]
        state.last_measurement = measured_state
        state.measurement_time_us = measurement_time_us

        # Record in history
        self.measurement_history[qubit_id].append((measured_state, measurement_time_us))

        # Check: does measurement match prediction?
        prediction_correct = measured_state == state.predicted_state
        if not prediction_correct:
            state.measurement_error_count += 1

            # Log divergence event
            self.divergence_events.append(
                {
                    "qubit_id": qubit_id,
                    "predicted": state.predicted_state,
                    "actual": measured_state,
                    "time_us": measurement_time_us,
                    "error_count": state.measurement_error_count,
                    "confidence": state.confidence,
                }
            )

            # Trigger feedback if error rate high
            needs_feedback = state.measurement_error_count >= 3  # 3 consecutive errors
            feedback_msg = f"Measurement divergence: predicted {state.predicted_state}, got {measured_state}"
            return False, feedback_msg if needs_feedback else "Divergence logged"

        return True, "Measurement matches prediction"

    def update_confidence_from_measurement(self, qubit_id: int, measured_state: int) -> None:
        """
        Update confidence based on measurement.
        If measurement matches prediction, confidence increases.
        If measurement differs, confidence decreases.
        """
        state = self.states[qubit_id]
        if measured_state == state.predicted_state:
            # Measurement confirms prediction
            state.confidence = min(1.0, state.confidence + 0.01)
        else:
            # Measurement contradicts prediction
            state.confidence = max(0.0, state.confidence - 0.05)

    def trigger_corrective_action(
        self, qubit_id: int, reason: str, action_id: int = 0
    ) -> FeedbackAction:
        """
        Trigger corrective action when state diverges from prediction.
        Common actions: bit flip, phase correction, reinit, discard qubit
        """
        state = self.states[qubit_id]
        error_count = state.measurement_error_count

        # Decide action based on error pattern
        if error_count >= 5:
            action_type = "discard"  # Too many errors, abandon this qubit
            reason += " (too many errors, discarding qubit)"
        elif error_count >= 3:
            # Try corrective action
            if state.predicted_state != state.last_measurement:
                action_type = "bit_flip"  # Flip to match measurement
                reason += f" (flipping state from {state.predicted_state} to {state.last_measurement})"
            else:
                action_type = "phase_correction"
                reason += " (applying phase correction)"
        else:
            action_type = "reinit"
            reason += " (reinitializing qubit)"

        action = FeedbackAction(
            action_id=action_id or len(self.feedback_actions),
            qubit_id=qubit_id,
            action_type=action_type,
            timestamp_us=self.time_us,
            reason=reason,
        )

        # Apply action
        if action_type == "bit_flip":
            state.predicted_state = 1 - state.predicted_state
            state.measurement_error_count = 0  # Reset error counter
            action.success = True

        elif action_type == "phase_correction":
            # Phase correction keeps state same but improves coherence
            state.confidence = min(1.0, state.confidence + 0.03)
            state.measurement_error_count = max(0, state.measurement_error_count - 1)
            action.success = True

        elif action_type == "reinit":
            # Reinitialize qubit to |0⟩
            state.predicted_state = 0
            state.confidence = 0.95
            state.measurement_error_count = 0
            action.success = True

        elif action_type == "discard":
            # Mark qubit as unusable for this experiment
            state.confidence = 0.0
            action.success = False

        self.feedback_actions.append(action)
        return action

    def get_state_fidelity(self, qubit_id: int) -> float:
        """Get fidelity of a specific qubit"""
        return self.states[qubit_id].confidence

    def get_average_fidelity(self) -> float:
        """Get average fidelity across all qubits"""
        if not self.states:
            return 0.0
        return sum(s.confidence for s in self.states) / len(self.states)

    def get_error_statistics(self) -> Dict[str, float]:
        """Get error statistics"""
        if not self.divergence_events:
            return {"divergence_count": 0, "error_rate": 0.0}

        total_measurements = sum(len(h) for h in self.measurement_history.values())
        divergence_count = len(self.divergence_events)
        error_rate = divergence_count / total_measurements if total_measurements > 0 else 0.0

        return {
            "divergence_count": divergence_count,
            "total_measurements": total_measurements,
            "error_rate": error_rate,
            "average_fidelity": self.get_average_fidelity(),
            "qubits_with_errors": len(set(e["qubit_id"] for e in self.divergence_events)),
        }

    def print_state_summary(self) -> str:
        """Print summary of quantum state"""
        lines = ["Quantum State Summary:\n"]
        lines.append("Qubit | Predicted | Confidence | Last Meas | Errors | Status")
        lines.append("-" * 65)

        for state in self.states[:20]:  # Print first 20 qubits
            status = "✓" if state.confidence > 0.95 else "⚠" if state.confidence > 0.8 else "✗"
            lines.append(
                f"{state.qubit_id:5d} | "
                f"{state.predicted_state:9d} | "
                f"{state.confidence:10.2f} | "
                f"{state.last_measurement:9d} | "
                f"{state.measurement_error_count:6d} | "
                f"{status}"
            )

        if len(self.states) > 20:
            lines.append(f"... ({len(self.states) - 20} more qubits)")

        # Statistics
        stats = self.get_error_statistics()
        lines.append("\nStatistics:")
        lines.append(f"  Divergence events: {stats['divergence_count']}")
        lines.append(f"  Total measurements: {stats['total_measurements']}")
        lines.append(f"  Error rate: {stats['error_rate']:.4f}")
        lines.append(f"  Average fidelity: {stats['average_fidelity']:.4f}")
        lines.append(f"  Qubits with errors: {stats['qubits_with_errors']}")

        return "\n".join(lines)


@dataclass
class ClosedLoopFeedbackControl:
    """
    Closed-loop feedback control: measure → compare to prediction → correct if needed
    """

    state_manager: StateManager
    max_correction_attempts: int = 3
    error_threshold: float = 0.05  # Trigger feedback if error rate > 5%

    def control_loop_iteration(self, qubit_id: int, measured_state: int, time_us: float) -> Tuple[bool, str]:
        """
        One iteration of closed-loop control.
        Returns: (converged, status)
        """
        self.state_manager.time_us = time_us

        # Step 1: Record measurement and check against prediction
        prediction_ok, feedback_msg = self.state_manager.record_measurement(
            qubit_id, measured_state, time_us
        )

        if prediction_ok:
            # Measurement matches prediction, no correction needed
            self.state_manager.update_confidence_from_measurement(qubit_id, measured_state)
            return True, "Measurement OK, no correction needed"

        # Step 2: Measurement diverged, trigger corrective action
        state = self.state_manager.states[qubit_id]
        if state.measurement_error_count >= self.max_correction_attempts:
            action = self.state_manager.trigger_corrective_action(
                qubit_id, reason="Max correction attempts exceeded"
            )
            return action.success, f"Applied correction: {action.action_type}"

        # Step 3: Try to correct
        action = self.state_manager.trigger_corrective_action(qubit_id, reason="Measurement divergence")
        return action.success, f"Correction triggered: {action.action_type}"

    def estimate_experiment_fidelity(self, num_qubits: int) -> float:
        """
        Estimate fidelity of a quantum computation on N qubits.
        Overall fidelity = product of individual fidelities
        """
        if num_qubits > len(self.state_manager.states):
            return 0.0
        return (
            self.state_manager.get_average_fidelity() ** num_qubits
        )  # Multiplicative fidelity scaling
