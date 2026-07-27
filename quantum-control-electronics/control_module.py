"""Distributed Control Module for Quantum Computers

Each control module manages 100 qubits and operates independently.
This enables scaling to 1000+ qubits without central bottleneck.

Key responsibilities:
- Execute quantum gates on assigned qubits
- Maintain state (predicted and actual via measurement)
- Validate all control signals against physics constraints
- Guarantee microsecond-precision timing
- Provide closed-loop feedback control
"""

from dataclasses import dataclass
from typing import List, Tuple, Dict
from enum import Enum

from neutral_atom_physics import NeutralAtomPhysics, ControlSignal, ControlSignalType
from timing_engine import TimingEngine, TimingDomainEnum, TimedControlSignal
from state_manager import StateManager, ClosedLoopFeedbackControl
from constraint_validator import ConstraintValidator


class ControlModuleStatusEnum(Enum):
    """Status of control module"""
    IDLE = "idle"
    READY = "ready"
    EXECUTING = "executing"
    MEASURING = "measuring"
    ERROR = "error"


@dataclass
class ControlModuleStats:
    """Statistics from control module operation"""
    qubits_managed: int
    gates_executed: int
    measurements_taken: int
    measurement_errors: int
    average_fidelity: float
    timing_violations: int


class ControlModule:
    """
    Distributed control module managing one cluster of qubits (100 typical).
    Operates independently; coordinates with other modules only for entangling gates.
    """

    QUBITS_PER_MODULE = 100  # Typical: 100 qubits per module

    def __init__(self, module_id: int, num_qubits: int = QUBITS_PER_MODULE):
        self.module_id = module_id
        self.num_qubits = num_qubits
        self.status = ControlModuleStatusEnum.IDLE

        # Core subsystems
        self.physics = NeutralAtomPhysics(num_qubits)
        self.timing = TimingEngine(num_qubits)
        self.state_manager = StateManager(num_qubits)
        self.constraints = ConstraintValidator()
        self.feedback_control = ClosedLoopFeedbackControl(self.state_manager)

        # Qubit assignment (which qubits this module owns)
        self.qubit_start = module_id * num_qubits
        self.qubit_end = self.qubit_start + num_qubits

        # Statistics
        self.gates_executed = 0
        self.measurements_taken = 0
        self.measurement_errors = 0
        self.timing_violations = 0
        self.constraint_violations = 0

        # Current time
        self.time_us = 0.0
        self.next_signal_id = 0

    def load_qubits(self) -> Tuple[bool, str]:
        """
        Load atoms into traps (initialization step).
        Each qubit loads independently.
        Returns: (success, message)
        """
        self.status = ControlModuleStatusEnum.EXECUTING

        for i in range(self.num_qubits):
            trap = self.physics.traps[i]

            # Schedule RF loading signal
            signal = ControlSignal(
                signal_type=ControlSignalType.RF_TRAP_LOAD,
                power_watts=50.0,  # Mid-range RF power
                duration_us=self.physics.TRAP_LOADING_TIME_US,
                start_time_us=self.time_us,
                frequency_ghz=0.005,  # 5 MHz RF
            )

            # Validate before execution
            valid, results = self.constraints.validate_control_signal(
                signal_type="rf_trap_load",
                power_watts=signal.power_watts,
                duration_us=signal.duration_us,
            )

            if not valid:
                self.constraint_violations += 1
                return False, f"Constraint violation during load: {results}"

            # Execute
            trap.state = trap.state.__class__.LOADED
            trap.predicted_state_binary = 0  # All qubits start in |0⟩

            # Schedule timing
            self.timing.schedule_signal(
                signal_id=self.next_signal_id,
                trap_id=i,
                signal_type="rf_trap_load",
                start_us=self.time_us,
                duration_us=signal.duration_us,
                timing_domain=TimingDomainEnum.SOFT_REALTIME,
                power_watts=signal.power_watts,
            )
            self.next_signal_id += 1

        self.time_us += self.physics.TRAP_LOADING_TIME_US
        self.status = ControlModuleStatusEnum.READY
        return True, f"Loaded {self.num_qubits} qubits successfully"

    def execute_single_qubit_gate(self, qubit_id: int, gate_type: str = "X90") -> Tuple[bool, str]:
        """Execute single-qubit Rydberg gate"""
        if not (self.qubit_start <= qubit_id < self.qubit_end):
            return False, f"Qubit {qubit_id} not managed by module {self.module_id}"

        trap = self.physics.traps[qubit_id]
        if trap.state.name != "LOADED":
            return False, f"Qubit {qubit_id} not loaded"

        # Apply heating from gate
        self.physics.apply_heating(qubit_id, self.physics.RYDBERG_HEATING_MK_PER_GATE)

        # Update predicted state (X gate: flip if X90)
        if gate_type == "X90" or gate_type == "X":
            trap.predicted_state_binary = 1 - trap.predicted_state_binary

        self.state_manager.set_predicted_state(
            qubit_id, trap.predicted_state_binary, trap.fidelity
        )

        # Schedule signal
        self.timing.schedule_signal(
            signal_id=self.next_signal_id,
            trap_id=qubit_id,
            signal_type="rydberg_gate",
            start_us=self.time_us,
            duration_us=self.physics.RYDBERG_GATE_TIME_US,
            timing_domain=TimingDomainEnum.HARD_REALTIME,
            power_watts=self.physics.RYDBERG_LASER_MAX_POWER_W,
        )
        self.next_signal_id += 1

        self.gates_executed += 1
        self.time_us += self.physics.RYDBERG_GATE_TIME_US
        return True, f"Gate {gate_type} on qubit {qubit_id} scheduled"

    def measure_qubits(self, qubit_ids: List[int]) -> Tuple[bool, Dict[int, int]]:
        """Measure multiple qubits and apply closed-loop feedback"""
        self.status = ControlModuleStatusEnum.MEASURING
        results = {}

        for qubit_id in qubit_ids:
            if not (self.qubit_start <= qubit_id < self.qubit_end):
                continue

            trap = self.physics.traps[qubit_id]
            measured_state, fidelity = self.physics.measure_qubit(qubit_id)

            results[qubit_id] = measured_state
            self.measurements_taken += 1

            # Apply closed-loop feedback
            success, status = self.feedback_control.control_loop_iteration(
                qubit_id, measured_state, self.time_us
            )

            if not success:
                self.measurement_errors += 1

        self.time_us += self.physics.PHOTON_COLLECTION_TIME_US
        self.status = ControlModuleStatusEnum.READY
        return True, results

    def get_statistics(self) -> ControlModuleStats:
        """Get module statistics"""
        return ControlModuleStats(
            qubits_managed=self.num_qubits,
            gates_executed=self.gates_executed,
            measurements_taken=self.measurements_taken,
            measurement_errors=self.measurement_errors,
            average_fidelity=self.state_manager.get_average_fidelity(),
            timing_violations=self.timing_violations,
        )

    def validate_timing(self) -> Tuple[bool, List[str]]:
        """Validate timing of scheduled signals"""
        return self.timing.validate_timing_sequence()

    def print_status(self) -> str:
        """Print module status"""
        lines = [f"Control Module {self.module_id}:", ""]
        lines.append(f"Status: {self.status.value}")
        lines.append(f"Qubits: {self.qubit_start}-{self.qubit_end-1} ({self.num_qubits} total)")
        lines.append(f"Gates executed: {self.gates_executed}")
        lines.append(f"Measurements: {self.measurements_taken}")
        lines.append(f"Average fidelity: {self.state_manager.get_average_fidelity():.4f}")
        lines.append(f"Constraint violations: {self.constraint_violations}")

        return "\n".join(lines)
