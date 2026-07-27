"""Constraint Validator for Quantum Control

Pre-execution validation of control signals against physics constraints.
5 pluggable checks ensure control signals won't violate quantum physics:

1. RF Power Limit — trap loading is power-limited
2. Timing Constraint — atoms must stay in trap during gates
3. Temperature Limit — heating beyond trap depth loses atoms
4. Measurement Latency — measurement must complete before next gate
5. Crosstalk Prevention — neighboring qubits must not couple

This module is the "safety check" layer: every control signal is validated
BEFORE it's sent to electronics. If a signal would violate constraints,
it's rejected with a reason code.
"""

from dataclasses import dataclass
from enum import Enum
from typing import List, Tuple, Callable
from abc import ABC, abstractmethod


class ConstraintCheckTypeEnum(Enum):
    """Types of constraint checks"""
    RF_POWER_LIMIT = "rf_power_limit"
    TIMING_CONSTRAINT = "timing_constraint"
    TEMPERATURE_LIMIT = "temperature_limit"
    MEASUREMENT_LATENCY = "measurement_latency"
    CROSSTALK_PREVENTION = "crosstalk_prevention"


class ConstraintCheckResultEnum(Enum):
    """Result of a constraint check"""
    PASS = "pass"
    FAIL = "fail"
    WARN = "warn"  # Warning but not blocking


@dataclass
class ConstraintCheckResult:
    """Result of a single constraint check"""
    check_type: ConstraintCheckTypeEnum
    result: ConstraintCheckResultEnum
    reason: str
    severity: str = "error"  # "error", "warn", "info"


class ConstraintCheck(ABC):
    """Base class for constraint checks"""

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description

    @abstractmethod
    def validate(self, **kwargs) -> ConstraintCheckResult:
        """
        Validate constraints.
        Returns: ConstraintCheckResult
        """
        pass


class RFPowerLimitCheck(ConstraintCheck):
    """Check 1: RF power must be within safe limits"""

    # RF parameters for neutral atom trap
    MAX_RF_POWER_W = 100.0  # Max RF power for trap loading
    MAX_RF_GATE_POWER_W = 10.0  # Max RF power for moving traps (gates)
    MIN_RF_POWER_W = 0.1  # Min power must be non-zero

    def __init__(self):
        super().__init__(
            name="RF Power Limit",
            description="RF power must be <100W for loading, <10W for gates",
        )

    def validate(self, signal_type: str, power_watts: float, **kwargs) -> ConstraintCheckResult:
        if signal_type == "rf_trap_load":
            if power_watts < self.MIN_RF_POWER_W or power_watts > self.MAX_RF_POWER_W:
                return ConstraintCheckResult(
                    check_type=ConstraintCheckTypeEnum.RF_POWER_LIMIT,
                    result=ConstraintCheckResultEnum.FAIL,
                    reason=f"RF loading power {power_watts}W out of range [{self.MIN_RF_POWER_W}, {self.MAX_RF_POWER_W}]W",
                )
        elif signal_type == "rf_trap_move":
            if power_watts < self.MIN_RF_POWER_W or power_watts > self.MAX_RF_GATE_POWER_W:
                return ConstraintCheckResult(
                    check_type=ConstraintCheckTypeEnum.RF_POWER_LIMIT,
                    result=ConstraintCheckResultEnum.FAIL,
                    reason=f"RF gate power {power_watts}W out of range [{self.MIN_RF_POWER_W}, {self.MAX_RF_GATE_POWER_W}]W",
                )

        return ConstraintCheckResult(
            check_type=ConstraintCheckTypeEnum.RF_POWER_LIMIT,
            result=ConstraintCheckResultEnum.PASS,
            reason="RF power within limits",
        )


class TimingConstraintCheck(ConstraintCheck):
    """Check 2: Gate duration must respect atom dwell time in trap"""

    MAX_GATE_DURATION_US = 1.0  # Max gate duration before atom heats too much
    MIN_GATE_DURATION_US = 0.05  # Min gate duration (physical limit of interaction strength)

    def __init__(self):
        super().__init__(
            name="Timing Constraint",
            description="Gate duration must be between 50ns and 1μs",
        )

    def validate(self, signal_type: str, duration_us: float, **kwargs) -> ConstraintCheckResult:
        if signal_type in ["rydberg_gate", "cz_gate"]:
            if duration_us < self.MIN_GATE_DURATION_US:
                return ConstraintCheckResult(
                    check_type=ConstraintCheckTypeEnum.TIMING_CONSTRAINT,
                    result=ConstraintCheckResultEnum.FAIL,
                    reason=f"Gate duration {duration_us}μs < minimum {self.MIN_GATE_DURATION_US}μs",
                )
            if duration_us > self.MAX_GATE_DURATION_US:
                return ConstraintCheckResult(
                    check_type=ConstraintCheckTypeEnum.TIMING_CONSTRAINT,
                    result=ConstraintCheckResultEnum.WARN,
                    reason=f"Gate duration {duration_us}μs > typical {self.MAX_GATE_DURATION_US}μs (heating risk)",
                    severity="warn",
                )

        return ConstraintCheckResult(
            check_type=ConstraintCheckTypeEnum.TIMING_CONSTRAINT,
            result=ConstraintCheckResultEnum.PASS,
            reason="Gate duration within limits",
        )


class TemperatureLimitCheck(ConstraintCheck):
    """Check 3: Trap temperature must stay below trap depth"""

    MAX_TEMPERATURE_UK = 100.0  # Trap depth limit in μK
    HEATING_PER_GATE_MK = 0.1  # Heating per gate in μK
    CRITICAL_TEMPERATURE_UK = 80.0  # Start warning at 80μK

    def __init__(self):
        super().__init__(
            name="Temperature Limit",
            description="Trap temperature must stay below 100μK (trap depth)",
        )

    def validate(self, current_temp_uk: float, num_gates_applied: int = 0, **kwargs) -> ConstraintCheckResult:
        projected_temp = current_temp_uk + num_gates_applied * self.HEATING_PER_GATE_MK

        if projected_temp > self.MAX_TEMPERATURE_UK:
            return ConstraintCheckResult(
                check_type=ConstraintCheckTypeEnum.TEMPERATURE_LIMIT,
                result=ConstraintCheckResultEnum.FAIL,
                reason=f"Projected temperature {projected_temp:.1f}μK > trap depth {self.MAX_TEMPERATURE_UK}μK (atom loss)",
            )

        if projected_temp > self.CRITICAL_TEMPERATURE_UK:
            return ConstraintCheckResult(
                check_type=ConstraintCheckTypeEnum.TEMPERATURE_LIMIT,
                result=ConstraintCheckResultEnum.WARN,
                reason=f"High temperature: {projected_temp:.1f}μK > critical {self.CRITICAL_TEMPERATURE_UK}μK",
                severity="warn",
            )

        return ConstraintCheckResult(
            check_type=ConstraintCheckTypeEnum.TEMPERATURE_LIMIT,
            result=ConstraintCheckResultEnum.PASS,
            reason=f"Temperature OK: {projected_temp:.1f}μK < {self.MAX_TEMPERATURE_UK}μK",
        )


class MeasurementLatencyCheck(ConstraintCheck):
    """Check 4: Measurement must complete before next gate"""

    PHOTON_COLLECTION_TIME_US = 10.0  # Time to collect photons
    ELECTRONICS_LATENCY_US = 2.0  # Electronics decision latency
    MAX_MEASUREMENT_LATENCY_US = PHOTON_COLLECTION_TIME_US + ELECTRONICS_LATENCY_US

    def __init__(self):
        super().__init__(
            name="Measurement Latency",
            description="Measurement must complete within 12μs (collection + electronics)",
        )

    def validate(self, measurement_latency_us: float, next_gate_start_us: float = None, **kwargs) -> ConstraintCheckResult:
        if measurement_latency_us > self.MAX_MEASUREMENT_LATENCY_US:
            return ConstraintCheckResult(
                check_type=ConstraintCheckTypeEnum.MEASUREMENT_LATENCY,
                result=ConstraintCheckResultEnum.FAIL,
                reason=f"Measurement latency {measurement_latency_us}μs > max {self.MAX_MEASUREMENT_LATENCY_US}μs",
            )

        # If next gate start time known, check it has time
        if next_gate_start_us is not None and measurement_latency_us > next_gate_start_us:
            return ConstraintCheckResult(
                check_type=ConstraintCheckTypeEnum.MEASUREMENT_LATENCY,
                result=ConstraintCheckResultEnum.FAIL,
                reason=f"Measurement won't complete ({measurement_latency_us}μs) before next gate ({next_gate_start_us}μs)",
            )

        return ConstraintCheckResult(
            check_type=ConstraintCheckTypeEnum.MEASUREMENT_LATENCY,
            result=ConstraintCheckResultEnum.PASS,
            reason=f"Measurement latency OK: {measurement_latency_us:.2f}μs < {self.MAX_MEASUREMENT_LATENCY_US}μs",
        )


class CrosstalkPreventionCheck(ConstraintCheck):
    """Check 5: Neighboring qubits must not couple (spatial separation required)"""

    MIN_TRAP_SEPARATION_UM = 1.6  # Minimum spacing between traps (2λ for 0.8μm light)
    LASER_WAVELENGTH_UM = 0.8  # Rydberg laser wavelength

    def __init__(self):
        super().__init__(
            name="Crosstalk Prevention",
            description="Trap separation must be >1.6μm to prevent coupling",
        )

    def validate(self, trap_separation_um: float, **kwargs) -> ConstraintCheckResult:
        if trap_separation_um < self.MIN_TRAP_SEPARATION_UM:
            return ConstraintCheckResult(
                check_type=ConstraintCheckTypeEnum.CROSSTALK_PREVENTION,
                result=ConstraintCheckResultEnum.FAIL,
                reason=f"Trap separation {trap_separation_um}μm < minimum {self.MIN_TRAP_SEPARATION_UM}μm (coupling risk)",
            )

        return ConstraintCheckResult(
            check_type=ConstraintCheckTypeEnum.CROSSTALK_PREVENTION,
            result=ConstraintCheckResultEnum.PASS,
            reason=f"Trap separation OK: {trap_separation_um}μm > {self.MIN_TRAP_SEPARATION_UM}μm",
        )


class ConstraintValidator:
    """
    Pre-execution constraint validator.
    Checks all 5 constraints before allowing control signal to hardware.
    """

    def __init__(self):
        self.checks: List[ConstraintCheck] = [
            RFPowerLimitCheck(),
            TimingConstraintCheck(),
            TemperatureLimitCheck(),
            MeasurementLatencyCheck(),
            CrosstalkPreventionCheck(),
        ]

        # Track validation history
        self.validation_results: List[ConstraintCheckResult] = []

    def validate_control_signal(self, **signal_params) -> Tuple[bool, List[ConstraintCheckResult]]:
        """
        Validate a control signal against all constraints.
        Returns: (all_checks_pass, list_of_results)
        """
        results = []
        all_pass = True

        for check in self.checks:
            result = check.validate(**signal_params)
            results.append(result)
            self.validation_results.append(result)

            if result.result == ConstraintCheckResultEnum.FAIL:
                all_pass = False

        return all_pass, results

    def print_validation_report(self) -> str:
        """Print validation report"""
        lines = ["Constraint Validation Report:\n"]
        lines.append("Check Type             | Status | Reason")
        lines.append("-" * 75)

        # Group by check type
        check_types = {}
        for result in self.validation_results:
            if result.check_type not in check_types:
                check_types[result.check_type] = result

        for check_type, result in check_types.items():
            status = "✓" if result.result == ConstraintCheckResultEnum.PASS else "✗" if result.result == ConstraintCheckResultEnum.FAIL else "⚠"
            lines.append(f"{check_type.value:22s} | {status:6s} | {result.reason[:50]}")

        # Summary
        failures = sum(1 for r in self.validation_results if r.result == ConstraintCheckResultEnum.FAIL)
        warnings = sum(1 for r in self.validation_results if r.result == ConstraintCheckResultEnum.WARN)
        lines.append(f"\nSummary: {len(self.checks)} checks, {failures} failures, {warnings} warnings")

        return "\n".join(lines)
