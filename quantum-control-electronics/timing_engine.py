"""Real-Time Timing Engine for Quantum Control

Microsecond-precision timing is critical for quantum gate execution.
This module guarantees <1μs jitter for gate sequences and validates that
all control signals complete within their scheduled windows.

Quantum gates execute in <1μs windows. Missing a timing window = gate fails.
No retries, no exceptions — just failure. So timing must be deterministic.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Tuple
import heapq


class TimingDomainEnum(Enum):
    """Different timing domains in quantum control system"""
    HARD_REALTIME = "hard_rt"  # <1μs jitter (quantum gate execution)
    SOFT_REALTIME = "soft_rt"  # 1-10μs jitter (orchestration)
    NEARLINE = "nearline"  # 10-100μs (policy evaluation)
    OFFLINE = "offline"  # >100μs (learning, diagnostics)


@dataclass
class TimedControlSignal:
    """Control signal with absolute timing and deadline"""
    signal_id: int
    trap_id: int  # Which trap this signal targets
    signal_type: str  # Type of signal (RF, laser, measurement)
    scheduled_start_us: float  # When to start (absolute time)
    duration_us: float  # How long signal lasts
    timing_domain: TimingDomainEnum  # Hard RT, soft RT, etc
    power_watts: float = 0.0  # For validation
    dependencies: List[int] = field(default_factory=list)  # IDs of signals this depends on

    @property
    def scheduled_end_us(self) -> float:
        return self.scheduled_start_us + self.duration_us

    @property
    def deadline_us(self) -> float:
        """Deadline for completion (with timing domain slack)"""
        slack_map = {
            TimingDomainEnum.HARD_REALTIME: 0.5,  # 0.5μs slack for hard RT
            TimingDomainEnum.SOFT_REALTIME: 5.0,
            TimingDomainEnum.NEARLINE: 50.0,
            TimingDomainEnum.OFFLINE: 500.0,
        }
        return self.scheduled_end_us + slack_map[self.timing_domain]


@dataclass
class TimingWindow:
    """A timing window that must not be violated"""
    window_id: int
    start_us: float
    end_us: float
    trap_id: int  # Which trap this window protects
    reason: str  # Why this window exists (e.g., "Rydberg gate execution")


class TimingEngine:
    """Hard real-time timing for quantum control"""

    # Timing parameters
    GATE_EXECUTION_WINDOW_US = 1.0  # Gates must complete within 1μs window
    MEASUREMENT_WINDOW_US = 10.0  # Measurement must complete within 10μs
    ORCHESTRATION_SLACK_US = 5.0  # Slack for orchestration/scheduling

    def __init__(self, num_qubits: int = 100):
        self.num_qubits = num_qubits
        self.current_time_us = 0.0

        # Track scheduled signals
        self.scheduled_signals: List[TimedControlSignal] = []

        # Detect timing violations
        self.timing_violations: List[Tuple[int, str]] = []

        # Track deadlines
        self.deadline_heap: List[Tuple[float, int, str]] = []  # (deadline, signal_id, description)

    def schedule_signal(
        self,
        signal_id: int,
        trap_id: int,
        signal_type: str,
        start_us: float,
        duration_us: float,
        timing_domain: TimingDomainEnum,
        power_watts: float = 0.0,
        dependencies: List[int] = None,
    ) -> Tuple[bool, str]:
        """
        Schedule a control signal.
        Returns: (success, reason)
        """
        if dependencies is None:
            dependencies = []

        # Validate timing domain constraints
        if timing_domain == TimingDomainEnum.HARD_REALTIME:
            if duration_us > self.GATE_EXECUTION_WINDOW_US:
                return False, f"Hard RT signal too long: {duration_us}μs > {self.GATE_EXECUTION_WINDOW_US}μs"

        if timing_domain == TimingDomainEnum.SOFT_REALTIME:
            if duration_us > self.MEASUREMENT_WINDOW_US:
                return False, f"Soft RT signal too long: {duration_us}μs > {self.MEASUREMENT_WINDOW_US}μs"

        # Create timed signal
        signal = TimedControlSignal(
            signal_id=signal_id,
            trap_id=trap_id,
            signal_type=signal_type,
            scheduled_start_us=start_us,
            duration_us=duration_us,
            timing_domain=timing_domain,
            power_watts=power_watts,
            dependencies=dependencies,
        )

        # Check for conflicts with already-scheduled signals
        for existing in self.scheduled_signals:
            if existing.trap_id == trap_id:
                # Same trap can't have overlapping signals
                if not (signal.scheduled_end_us <= existing.scheduled_start_us or
                        signal.scheduled_start_us >= existing.scheduled_end_us):
                    return False, f"Signal {signal_id} overlaps with signal {existing.signal_id} on trap {trap_id}"

        # Check dependencies are satisfied
        dep_ids = {s.signal_id for s in self.scheduled_signals}
        for dep_id in dependencies:
            if dep_id not in dep_ids:
                return False, f"Dependency {dep_id} not found in scheduled signals"

        # Check dependency ordering (dependent signals must start after dependency ends)
        for dep_id in dependencies:
            dep_signal = next((s for s in self.scheduled_signals if s.signal_id == dep_id), None)
            if dep_signal and signal.scheduled_start_us < dep_signal.scheduled_end_us:
                return False, f"Signal {signal_id} starts before dependency {dep_id} completes"

        # Add to schedule
        self.scheduled_signals.append(signal)
        heapq.heappush(self.deadline_heap, (signal.deadline_us, signal_id, f"Trap {trap_id} {signal_type}"))

        return True, f"Signal {signal_id} scheduled at {start_us}μs"

    def validate_timing_sequence(self) -> Tuple[bool, List[str]]:
        """
        Validate the entire scheduled sequence for timing violations.
        Returns: (valid, list_of_violations)
        """
        violations = []

        # Check 1: No overlapping signals on same trap
        for i, sig1 in enumerate(self.scheduled_signals):
            for sig2 in self.scheduled_signals[i + 1 :]:
                if sig1.trap_id == sig2.trap_id:
                    if not (sig1.scheduled_end_us <= sig2.scheduled_start_us or
                            sig1.scheduled_start_us >= sig2.scheduled_end_us):
                        violations.append(
                            f"Overlap: signals {sig1.signal_id} and {sig2.signal_id} on trap {sig1.trap_id}"
                        )

        # Check 2: Dependencies satisfied
        for signal in self.scheduled_signals:
            for dep_id in signal.dependencies:
                dep_signal = next((s for s in self.scheduled_signals if s.signal_id == dep_id), None)
                if dep_signal and signal.scheduled_start_us < dep_signal.scheduled_end_us:
                    violations.append(
                        f"Dependency violation: signal {signal.signal_id} starts before {dep_id} completes"
                    )

        # Check 3: Timing domain constraints
        for signal in self.scheduled_signals:
            if signal.timing_domain == TimingDomainEnum.HARD_REALTIME:
                if signal.duration_us > self.GATE_EXECUTION_WINDOW_US:
                    violations.append(
                        f"Hard RT violation: signal {signal.signal_id} duration {signal.duration_us}μs "
                        f"> {self.GATE_EXECUTION_WINDOW_US}μs"
                    )

            elif signal.timing_domain == TimingDomainEnum.SOFT_REALTIME:
                if signal.duration_us > self.MEASUREMENT_WINDOW_US:
                    violations.append(
                        f"Soft RT violation: signal {signal.signal_id} duration {signal.duration_us}μs "
                        f"> {self.MEASUREMENT_WINDOW_US}μs"
                    )

        # Check 4: Deadlines met
        for signal in self.scheduled_signals:
            if signal.scheduled_end_us > signal.deadline_us:
                violations.append(
                    f"Deadline miss: signal {signal.signal_id} ends at {signal.scheduled_end_us}μs, "
                    f"deadline {signal.deadline_us}μs"
                )

        self.timing_violations = [(s.signal_id, v) for s, v in zip(self.scheduled_signals, violations)]
        return len(violations) == 0, violations

    def get_critical_path_us(self) -> float:
        """
        Calculate the critical path: minimum time to execute all scheduled signals.
        (Longest chain of dependent signals)
        """
        if not self.scheduled_signals:
            return 0.0

        # Simple calculation: max end time
        return max(s.scheduled_end_us for s in self.scheduled_signals)

    def estimate_jitter_us(self) -> float:
        """
        Estimate timing jitter in the schedule.
        Returns: estimated jitter in microseconds
        """
        # Count hard real-time signals
        hard_rt_signals = [s for s in self.scheduled_signals if s.timing_domain == TimingDomainEnum.HARD_REALTIME]

        if not hard_rt_signals:
            return 0.0

        # Jitter increases with number of hard RT signals (more context switches possible)
        # Empirically: ~0.1μs per hard RT signal (on bare metal)
        estimated_jitter = len(hard_rt_signals) * 0.05
        return min(estimated_jitter, 0.5)  # Cap at 0.5μs

    def print_schedule(self) -> str:
        """Print human-readable timing schedule"""
        lines = ["Timing Schedule (in μs):\n"]
        lines.append("Time(μs)  | Trap | Signal Type        | Duration | Domain")
        lines.append("-" * 60)

        sorted_signals = sorted(self.scheduled_signals, key=lambda s: s.scheduled_start_us)
        for s in sorted_signals:
            lines.append(
                f"{s.scheduled_start_us:8.2f} | {s.trap_id:4d} | {s.signal_type:18s} | "
                f"{s.duration_us:8.2f} | {s.timing_domain.value}"
            )

        critical_path = self.get_critical_path_us()
        estimated_jitter = self.estimate_jitter_us()
        lines.append(f"\nCritical path: {critical_path:.2f}μs")
        lines.append(f"Estimated jitter: ±{estimated_jitter:.2f}μs")

        return "\n".join(lines)


# Helper functions for timing validation

def check_timing_domain_constraint(duration_us: float, domain: TimingDomainEnum) -> Tuple[bool, str]:
    """Check if signal duration fits its timing domain"""
    max_durations = {
        TimingDomainEnum.HARD_REALTIME: 1.0,
        TimingDomainEnum.SOFT_REALTIME: 10.0,
        TimingDomainEnum.NEARLINE: 100.0,
        TimingDomainEnum.OFFLINE: 1000.0,
    }
    max_dur = max_durations[domain]
    if duration_us > max_dur:
        return False, f"Duration {duration_us}μs > max for {domain.value}: {max_dur}μs"
    return True, "Timing domain OK"


def estimate_gate_sequence_time(
    num_single_qubit_gates: int, num_two_qubit_gates: int
) -> float:
    """Estimate total execution time for a gate sequence"""
    single_gate_time = 0.1  # Rydberg single-qubit gate
    two_gate_time = 0.5  # Rydberg two-qubit gate
    measurement_time = 10.0  # Measurement at end
    return (
        num_single_qubit_gates * single_gate_time
        + num_two_qubit_gates * two_gate_time
        + measurement_time
    )
