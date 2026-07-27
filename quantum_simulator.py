#!/usr/bin/env python3
"""
Simulator Interface: Pluggable Markovian & Non-Markovian Environments

Defines the contract for quantum simulators backing the controller's feedback loop.
Simulators consume control actions and produce rewards, trajectories, and robustness metrics.

Two implementations provided:
- MkovianSimulator: stateless transitions, reward based on fidelity
- TrajectorySimulator: tracks history for non-Markovian properties
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum

from quantum_schema import QuantumGraph, Node, Edge, NodeType, EdgeType, ConfidenceLevel


# ============================================================================
# SIMULATION TYPES
# ============================================================================

class SimulatorType(str, Enum):
    """Simulator classification."""
    MARKOVIAN = "markovian"
    NON_MARKOVIAN = "non_markovian"
    HYBRID = "hybrid"


class RewardComponent(str, Enum):
    """Reward signal decomposition."""
    FIDELITY = "fidelity"
    GATE_SPEED = "gate_speed"
    ERROR_SUPPRESSION = "error_suppression"
    RESOURCE_EFFICIENCY = "resource_efficiency"
    COHERENCE_PRESERVATION = "coherence_preservation"


# ============================================================================
# SIMULATION RESULTS
# ============================================================================

@dataclass
class SimulationStep:
    """One step of trajectory in simulation."""
    step_id: int
    timestamp: str
    action_id: str
    state_vector: Optional[List[complex]] = None  # snapshot of qubit state
    measurement_outcomes: Dict[str, int] = field(default_factory=dict)  # qubit_id -> 0/1
    error_rate: float = 0.0  # estimated error for this step
    fidelity: float = 1.0  # 0.0 - 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self):
        return {
            "step_id": self.step_id,
            "timestamp": self.timestamp,
            "action_id": self.action_id,
            "error_rate": self.error_rate,
            "fidelity": self.fidelity,
            "measurement_outcomes": self.measurement_outcomes,
            "metadata": self.metadata
        }


@dataclass
class RobustnessMetrics:
    """Robustness of trajectory under perturbations."""
    noise_resilience: float  # 0.0 - 1.0: how robust to decoherence
    timing_tolerance_ns: float  # acceptable timing jitter
    frequency_tolerance_mhz: float  # acceptable frequency drift
    state_preparation_fidelity: float  # 0.0 - 1.0
    measurement_fidelity: float  # 0.0 - 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self):
        return {
            "noise_resilience": self.noise_resilience,
            "timing_tolerance_ns": self.timing_tolerance_ns,
            "frequency_tolerance_mhz": self.frequency_tolerance_mhz,
            "state_preparation_fidelity": self.state_preparation_fidelity,
            "measurement_fidelity": self.measurement_fidelity,
            "metadata": self.metadata
        }


@dataclass
class TrajectoryResult:
    """Complete simulation trajectory result."""
    trajectory_id: str
    simulator_type: SimulatorType
    steps: List[SimulationStep] = field(default_factory=list)

    # Aggregate metrics
    total_reward: float = 0.0
    average_fidelity: float = 1.0
    peak_error_rate: float = 0.0
    cumulative_error: float = 0.0

    # Reward decomposition
    reward_components: Dict[RewardComponent, float] = field(default_factory=dict)

    # Robustness
    robustness: Optional[RobustnessMetrics] = None

    # Metadata
    completed: bool = False
    confidence: ConfidenceLevel = ConfidenceLevel.UNCERTAIN
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def step_count(self):
        """Return number of steps in trajectory."""
        return len(self.steps)

    def to_dict(self):
        return {
            "trajectory_id": self.trajectory_id,
            "simulator_type": self.simulator_type.value,
            "step_count": self.step_count,
            "total_reward": self.total_reward,
            "average_fidelity": self.average_fidelity,
            "peak_error_rate": self.peak_error_rate,
            "cumulative_error": self.cumulative_error,
            "reward_components": {k.value: v for k, v in self.reward_components.items()},
            "robustness": self.robustness.to_dict() if self.robustness else None,
            "completed": self.completed,
            "confidence": self.confidence.value,
            "metadata": self.metadata
        }


# ============================================================================
# SIMULATOR INTERFACE
# ============================================================================

class SimulatorInterface(ABC):
    """Abstract base for quantum simulators."""

    @abstractmethod
    def initialize(self, graph: QuantumGraph) -> bool:
        """Initialize simulator with graph context."""
        pass

    @abstractmethod
    def reset(self) -> bool:
        """Reset simulator to clean state."""
        pass

    @abstractmethod
    def run_trajectory(
        self,
        action_sequence: List[Dict[str, Any]],
        initial_state: Optional[str] = None,
        num_shots: int = 1000
    ) -> TrajectoryResult:
        """Run complete trajectory and return result."""
        pass

    @abstractmethod
    def get_simulator_type(self) -> SimulatorType:
        """Return simulator classification."""
        pass

    @abstractmethod
    def estimate_robustness(self, trajectory: TrajectoryResult) -> RobustnessMetrics:
        """Estimate trajectory robustness under perturbations."""
        pass


# ============================================================================
# MARKOVIAN SIMULATOR
# ============================================================================

class MMarkovianSimulator(SimulatorInterface):
    """Stateless Markovian simulator: fidelity-based rewards."""

    def __init__(self, name: str = "markovian_sim"):
        self.name = name
        self.graph: Optional[QuantumGraph] = None
        self.step_counter = 0

    def initialize(self, graph: QuantumGraph) -> bool:
        """Initialize with graph."""
        self.graph = graph
        return True

    def reset(self) -> bool:
        """Reset step counter."""
        self.step_counter = 0
        return True

    def get_simulator_type(self) -> SimulatorType:
        return SimulatorType.MARKOVIAN

    def run_trajectory(
        self,
        action_sequence: List[Dict[str, Any]],
        initial_state: Optional[str] = None,
        num_shots: int = 1000
    ) -> TrajectoryResult:
        """Run Markovian trajectory: each step independent."""
        trajectory = TrajectoryResult(
            trajectory_id=f"markovian_{self.step_counter}",
            simulator_type=SimulatorType.MARKOVIAN,
            completed=False
        )

        self.reset()
        total_reward = 0.0
        fidelities = []
        error_rates = []

        for i, action in enumerate(action_sequence):
            # Markovian step: only current action matters
            step = self._simulate_step(i, action)
            trajectory.steps.append(step)

            total_reward += self._compute_reward(step, action)
            fidelities.append(step.fidelity)
            error_rates.append(step.error_rate)

        # Aggregate metrics
        trajectory.total_reward = total_reward
        trajectory.average_fidelity = sum(fidelities) / len(fidelities) if fidelities else 1.0
        trajectory.peak_error_rate = max(error_rates) if error_rates else 0.0
        trajectory.cumulative_error = sum(error_rates)
        trajectory.completed = True
        trajectory.confidence = ConfidenceLevel.HIGH

        # Simple reward decomposition
        trajectory.reward_components = {
            RewardComponent.FIDELITY: trajectory.average_fidelity,
            RewardComponent.ERROR_SUPPRESSION: 1.0 - trajectory.peak_error_rate,
        }

        # Robustness estimation
        trajectory.robustness = self.estimate_robustness(trajectory)

        return trajectory

    def _simulate_step(self, step_id: int, action: Dict[str, Any]) -> SimulationStep:
        """Simulate one Markovian step."""
        # Extract action params
        duration_ns = action.get("duration_ns", 100.0)
        amplitude = action.get("amplitude_normalized", 0.5)
        target_qubits = action.get("target_qubits", [])

        # Fidelity model: decreases with duration and gate complexity
        base_fidelity = 0.99
        duration_penalty = (duration_ns / 1000.0) * 0.001  # ~0.1% per microsecond
        complexity_penalty = len(target_qubits) * 0.01  # ~1% per additional qubit
        fidelity = max(0.90, base_fidelity - duration_penalty - complexity_penalty)

        # Error rate (inverse of fidelity for this model)
        error_rate = 1.0 - fidelity

        return SimulationStep(
            step_id=step_id,
            timestamp=__import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat(),
            action_id=action.get("action_id", f"action_{step_id}"),
            fidelity=fidelity,
            error_rate=error_rate,
            measurement_outcomes={f"q{i}": (i + step_id) % 2 for i in range(len(target_qubits))},
            metadata={"gate_type": action.get("pulse_family_id", "unknown")}
        )

    def _compute_reward(self, step: SimulationStep, action: Dict[str, Any]) -> float:
        """Compute reward for step."""
        # Reward is fidelity; penalty for long gates
        duration_ns = action.get("duration_ns", 100.0)
        speed_penalty = (duration_ns / 1000.0) * 0.01
        return max(0.0, step.fidelity - speed_penalty)

    def estimate_robustness(self, trajectory: TrajectoryResult) -> RobustnessMetrics:
        """Estimate Markovian robustness."""
        # Robustness based on average fidelity
        return RobustnessMetrics(
            noise_resilience=trajectory.average_fidelity,
            timing_tolerance_ns=10.0,  # Fixed for simulation
            frequency_tolerance_mhz=5.0,
            state_preparation_fidelity=0.95,
            measurement_fidelity=0.95,
            metadata={"model": "markovian_fidelity_based"}
        )


# ============================================================================
# TRAJECTORY SIMULATOR (Non-Markovian)
# ============================================================================

class TrajectorySimulator(SimulatorInterface):
    """Non-Markovian simulator: tracks full history."""

    def __init__(self, name: str = "trajectory_sim"):
        self.name = name
        self.graph: Optional[QuantumGraph] = None
        self.step_counter = 0
        self.history: List[SimulationStep] = []

    def initialize(self, graph: QuantumGraph) -> bool:
        """Initialize with graph."""
        self.graph = graph
        return True

    def reset(self) -> bool:
        """Reset state and history."""
        self.step_counter = 0
        self.history = []
        return True

    def get_simulator_type(self) -> SimulatorType:
        return SimulatorType.NON_MARKOVIAN

    def run_trajectory(
        self,
        action_sequence: List[Dict[str, Any]],
        initial_state: Optional[str] = None,
        num_shots: int = 1000
    ) -> TrajectoryResult:
        """Run non-Markovian trajectory: history affects each step."""
        trajectory = TrajectoryResult(
            trajectory_id=f"trajectory_{self.step_counter}",
            simulator_type=SimulatorType.NON_MARKOVIAN,
            completed=False
        )

        self.reset()
        total_reward = 0.0
        fidelities = []
        error_rates = []
        memory_effects = 0.0

        for i, action in enumerate(action_sequence):
            # Non-Markovian: history affects step
            step = self._simulate_step_with_history(i, action)
            trajectory.steps.append(step)
            self.history.append(step)

            total_reward += self._compute_reward_with_history(step, i)
            fidelities.append(step.fidelity)
            error_rates.append(step.error_rate)

            # Track memory effects: accumulated decoherence
            memory_effects += step.error_rate * 0.1

        # Aggregate metrics
        trajectory.total_reward = total_reward
        trajectory.average_fidelity = sum(fidelities) / len(fidelities) if fidelities else 1.0
        trajectory.peak_error_rate = max(error_rates) if error_rates else 0.0
        trajectory.cumulative_error = sum(error_rates) + memory_effects
        trajectory.completed = True

        # Confidence based on history length
        if len(self.history) >= 5:
            trajectory.confidence = ConfidenceLevel.CRITICAL
        elif len(self.history) >= 3:
            trajectory.confidence = ConfidenceLevel.HIGH
        else:
            trajectory.confidence = ConfidenceLevel.MODERATE

        # Detailed reward decomposition
        trajectory.reward_components = {
            RewardComponent.FIDELITY: trajectory.average_fidelity,
            RewardComponent.ERROR_SUPPRESSION: 1.0 - trajectory.peak_error_rate,
            RewardComponent.COHERENCE_PRESERVATION: max(0.0, 1.0 - memory_effects),
        }

        # Robustness estimation
        trajectory.robustness = self.estimate_robustness(trajectory)

        return trajectory

    def _simulate_step_with_history(self, step_id: int, action: Dict[str, Any]) -> SimulationStep:
        """Simulate step considering history."""
        # Base fidelity from action
        duration_ns = action.get("duration_ns", 100.0)
        amplitude = action.get("amplitude_normalized", 0.5)
        base_fidelity = 0.99 - (duration_ns / 1000.0) * 0.001

        # Decoherence penalty from history
        history_penalty = 0.0
        if self.history:
            # Accumulated errors from past steps reduce current fidelity
            accumulated_errors = sum(s.error_rate for s in self.history[-3:])  # Last 3 steps
            history_penalty = min(0.05, accumulated_errors * 0.01)

        fidelity = max(0.85, base_fidelity - history_penalty)
        error_rate = 1.0 - fidelity

        return SimulationStep(
            step_id=step_id,
            timestamp=__import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat(),
            action_id=action.get("action_id", f"action_{step_id}"),
            fidelity=fidelity,
            error_rate=error_rate,
            measurement_outcomes={f"q{i}": (i + step_id * 2) % 2 for i in range(len(action.get("target_qubits", [])))},
            metadata={
                "gate_type": action.get("pulse_family_id", "unknown"),
                "history_length": len(self.history),
                "memory_effects": history_penalty
            }
        )

    def _compute_reward_with_history(self, step: SimulationStep, step_id: int) -> float:
        """Compute reward considering trajectory history."""
        # Reward decreases slightly with trajectory length due to memory effects
        base_reward = step.fidelity
        length_penalty = step_id * 0.001  # Small penalty per step
        return max(0.0, base_reward - length_penalty)

    def estimate_robustness(self, trajectory: TrajectoryResult) -> RobustnessMetrics:
        """Estimate robustness accounting for non-Markovian effects."""
        # Robustness depends on peak error rate and memory effects
        memory_resilience = 1.0 - (trajectory.cumulative_error - sum(s.error_rate for s in trajectory.steps))
        return RobustnessMetrics(
            noise_resilience=trajectory.average_fidelity * memory_resilience,
            timing_tolerance_ns=8.0,  # Slightly tighter than Markovian
            frequency_tolerance_mhz=4.0,
            state_preparation_fidelity=0.94,
            measurement_fidelity=0.94,
            metadata={
                "model": "trajectory_non_markovian",
                "history_length": len(trajectory.steps),
                "memory_resilience": memory_resilience
            }
        )


# ============================================================================
# SIMULATOR FACTORY
# ============================================================================

def create_simulator(simulator_type: SimulatorType = SimulatorType.MARKOVIAN) -> SimulatorInterface:
    """Factory for creating simulator instances."""
    if simulator_type == SimulatorType.MARKOVIAN:
        return MMarkovianSimulator()
    elif simulator_type == SimulatorType.NON_MARKOVIAN:
        return TrajectorySimulator()
    else:
        # Default to Markovian
        return MMarkovianSimulator()
