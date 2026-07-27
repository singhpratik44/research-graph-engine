"""Neutral Atom Trap Physics Model

Represents the physics of neutral atom quantum computers:
- Optical tweezers trap individual atoms in potential wells
- Rydberg laser gates perform 2-qubit gates between nearby atoms
- Photon detection measures qubit state (|0⟩ or |1⟩)
- Trap dynamics limit gate speed, heating limits qubit lifetime

This module defines physics constraints that control electronics must respect.
"""

from dataclasses import dataclass
from enum import Enum
from typing import List, Tuple
import math


class TrapStateEnum(Enum):
    """State of a single trap site (holds one atom)"""
    EMPTY = "empty"
    LOADED = "loaded"
    EXCITED = "excited"  # Rydberg state (excited atom)
    MEASURED = "measured"


class ControlSignalType(Enum):
    """Types of electronic control signals"""
    RF_TRAP_LOAD = "rf_trap_load"  # RF to load atom into trap
    RF_TRAP_MOVE = "rf_trap_move"  # RF to move trap (entangling gates)
    LASER_RYDBERG = "laser_rydberg"  # Rydberg laser (single-qubit gates)
    LASER_DEPUMP = "laser_depump"  # Depumping laser (measurement)
    PHOTON_DETECT = "photon_detect"  # Photon detector (measure |0⟩ vs |1⟩)


@dataclass
class ControlSignal:
    """A single electronic control signal applied to trap/laser system"""
    signal_type: ControlSignalType
    power_watts: float  # RF/laser power in watts
    duration_us: float  # Duration in microseconds
    start_time_us: float  # When to start (absolute time)
    frequency_ghz: float = 0.0  # For RF signals (trap frequency)
    intensity_fraction: float = 1.0  # Laser intensity (fraction of max)


@dataclass
class NeutralAtomTrap:
    """A single trap holding one atom (one qubit)"""
    trap_id: int
    state: TrapStateEnum = TrapStateEnum.EMPTY
    temperature_uk: float = 1.0  # Temperature in microkelvin (heating during gates)
    fidelity: float = 1.0  # State fidelity (degrades due to heating/dephasing)
    predicted_state_binary: int = 0  # Predicted state: 0 or 1


class NeutralAtomPhysics:
    """Physics constraints for neutral atom quantum computer"""

    # Trap physics parameters
    TRAP_FREQUENCY_MHZ = 5.0  # Frequency of optical tweezers
    TRAP_DEPTH_UK = 500.0  # Depth of trap in microkelvin
    TRAP_LOADING_TIME_US = 1000.0  # Time to load atom into trap

    # Gate parameters
    RYDBERG_GATE_TIME_US = 0.1  # Rydberg gate duration (fast)
    RYDBERG_LASER_MAX_POWER_W = 1.0  # Max laser power for Rydberg gates
    ENTANGLING_GATE_TIME_US = 0.5  # 2-qubit gate duration

    # Measurement parameters
    PHOTON_COLLECTION_TIME_US = 10.0  # Time to collect photon and detect
    MEASUREMENT_READOUT_LATENCY_US = 2.0  # Electronics latency for measurement

    # Heating rates
    HEATING_RATE_MK_PER_GATE = 0.1  # Heating per gate (trap motion)
    RYDBERG_HEATING_MK_PER_GATE = 0.05  # Heating from Rydberg laser

    # Fidelity degradation
    FIDELITY_LOSS_PER_UK_HEATING = 0.001  # Fidelity loss per μK of heating
    DEPHASING_TIME_CONSTANT_US = 1000.0  # T2 coherence time

    def __init__(self, num_qubits: int = 100):
        """Initialize trap array"""
        self.num_qubits = num_qubits
        self.traps: List[NeutralAtomTrap] = [
            NeutralAtomTrap(trap_id=i) for i in range(num_qubits)
        ]
        self.time_us = 0.0

    def validate_rf_signal(self, signal: ControlSignal) -> Tuple[bool, str]:
        """Validate RF control signal against physics constraints"""
        if signal.signal_type in [ControlSignalType.RF_TRAP_LOAD, ControlSignalType.RF_TRAP_MOVE]:
            # RF power limits
            if signal.power_watts > 100.0:
                return False, f"RF power {signal.power_watts}W exceeds 100W limit"

            # RF duration limits (trap stability)
            if signal.signal_type == ControlSignalType.RF_TRAP_LOAD:
                if signal.duration_us > self.TRAP_LOADING_TIME_US * 2:
                    return False, f"Trap loading time {signal.duration_us}μs exceeds {self.TRAP_LOADING_TIME_US*2}μs"

            # Frequency must match trap frequency
            if abs(signal.frequency_ghz * 1000 - self.TRAP_FREQUENCY_MHZ) > 0.1:
                return False, f"RF frequency {signal.frequency_ghz}GHz != trap frequency {self.TRAP_FREQUENCY_MHZ}MHz"

        return True, "RF signal valid"

    def validate_laser_signal(self, signal: ControlSignal) -> Tuple[bool, str]:
        """Validate laser control signal"""
        if signal.signal_type == ControlSignalType.LASER_RYDBERG:
            # Laser power limits
            if signal.power_watts > self.RYDBERG_LASER_MAX_POWER_W:
                return False, f"Rydberg laser power {signal.power_watts}W exceeds {self.RYDBERG_LASER_MAX_POWER_W}W"

            # Gate time must respect Rydberg interaction strength
            if signal.duration_us < self.RYDBERG_GATE_TIME_US * 0.5:
                return False, f"Gate too fast {signal.duration_us}μs (min {self.RYDBERG_GATE_TIME_US*0.5}μs)"

            if signal.duration_us > self.RYDBERG_GATE_TIME_US * 10:
                return False, f"Gate too slow {signal.duration_us}μs (max {self.RYDBERG_GATE_TIME_US*10}μs)"

        return True, "Laser signal valid"

    def validate_measurement_sequence(self, photon_collect_us: float) -> Tuple[bool, str]:
        """Validate measurement timing"""
        if photon_collect_us < self.PHOTON_COLLECTION_TIME_US:
            return False, f"Photon collection time {photon_collect_us}μs too short (min {self.PHOTON_COLLECTION_TIME_US}μs)"

        return True, "Measurement sequence valid"

    def apply_heating(self, trap_id: int, heating_amount_uk: float) -> None:
        """Apply heating to a trap (increases temperature, degrades fidelity)"""
        trap = self.traps[trap_id]
        trap.temperature_uk += heating_amount_uk

        # Cap temperature at trap depth (atom is lost if too hot)
        if trap.temperature_uk > self.TRAP_DEPTH_UK:
            trap.state = TrapStateEnum.EMPTY
            trap.temperature_uk = self.TRAP_DEPTH_UK

        # Fidelity degradation due to heating
        trap.fidelity -= heating_amount_uk * self.FIDELITY_LOSS_PER_UK_HEATING
        trap.fidelity = max(0.0, min(1.0, trap.fidelity))

    def apply_dephasing(self, trap_id: int, time_elapsed_us: float) -> None:
        """Apply dephasing due to qubit coherence time"""
        trap = self.traps[trap_id]
        dephasing_factor = math.exp(-time_elapsed_us / self.DEPHASING_TIME_CONSTANT_US)
        fidelity_loss = (1.0 - dephasing_factor) * 0.1  # 10% fidelity loss per T2
        trap.fidelity -= fidelity_loss
        trap.fidelity = max(0.0, min(1.0, trap.fidelity))

    def simulate_rydberg_gate(self, control_qubit: int, target_qubit: int) -> Tuple[bool, float]:
        """
        Simulate 2-qubit Rydberg gate between control and target qubits.
        Returns: (success, fidelity)
        """
        trap_c = self.traps[control_qubit]
        trap_t = self.traps[target_qubit]

        # Check both qubits are loaded
        if trap_c.state != TrapStateEnum.LOADED or trap_t.state != TrapStateEnum.LOADED:
            return False, 0.0

        # Gate heating
        heating = self.RYDBERG_HEATING_MK_PER_GATE
        self.apply_heating(control_qubit, heating)
        self.apply_heating(target_qubit, heating)

        # Dephasing during gate
        self.apply_dephasing(control_qubit, self.RYDBERG_GATE_TIME_US)
        self.apply_dephasing(target_qubit, self.RYDBERG_GATE_TIME_US)

        # Gate fidelity limited by temperature and coherence
        gate_fidelity = min(trap_c.fidelity, trap_t.fidelity) * 0.99  # 99% gate fidelity in ideal case
        return True, gate_fidelity

    def measure_qubit(self, trap_id: int) -> Tuple[int, float]:
        """
        Measure qubit state. Returns: (measured_state, fidelity)
        Measurement outcome = predicted state + error probability based on fidelity
        """
        trap = self.traps[trap_id]

        if trap.state != TrapStateEnum.LOADED:
            return -1, 0.0  # Can't measure empty trap

        # Measurement outcome depends on predicted state + fidelity
        error_prob = 1.0 - trap.fidelity
        measured_state = trap.predicted_state_binary
        if error_prob > 0.5 and error_prob > 0:
            # Randomly flip outcome with probability proportional to error
            import random
            if random.random() < error_prob:
                measured_state = 1 - measured_state

        return measured_state, trap.fidelity

    def reset_trap_cooling(self, trap_id: int) -> None:
        """Cool trap back to initial temperature (between experimental runs)"""
        trap = self.traps[trap_id]
        trap.temperature_uk = 1.0  # Reset to cold temperature
        trap.fidelity = 0.99  # Slight degradation from cooling process


# Physics constraint checks used by control system

def check_rf_power_limit(signal: ControlSignal) -> Tuple[bool, str]:
    """RF power must be <100W for trap loading"""
    if signal.power_watts > 100.0:
        return False, f"RF power exceeds limit: {signal.power_watts}W > 100W"
    return True, "RF power OK"


def check_timing_constraint(signal: ControlSignal, trap_dwell_time_us: float = 10.0) -> Tuple[bool, str]:
    """Gate duration must allow atom to stay in trap"""
    if signal.duration_us > trap_dwell_time_us:
        return False, f"Gate duration {signal.duration_us}μs exceeds dwell time {trap_dwell_time_us}μs"
    return True, "Timing OK"


def check_temperature_limit(current_temp_uk: float, max_temp_uk: float = 100.0) -> Tuple[bool, str]:
    """Trap temperature must stay below depth limit"""
    if current_temp_uk > max_temp_uk:
        return False, f"Temperature {current_temp_uk}μK exceeds limit {max_temp_uk}μK"
    return True, "Temperature OK"


def check_measurement_latency(latency_us: float, photon_collection_us: float = 10.0) -> Tuple[bool, str]:
    """Measurement must complete before next gate"""
    if latency_us > photon_collection_us:
        return False, f"Measurement latency {latency_us}μs > collection time {photon_collection_us}μs"
    return True, "Measurement latency OK"


def check_crosstalk_prevention(trap_separation_um: float, laser_wavelength_um: float = 0.8) -> Tuple[bool, str]:
    """Neighboring traps must not couple (minimum separation)"""
    min_separation = laser_wavelength_um * 2  # Rough 2λ minimum
    if trap_separation_um < min_separation:
        return False, f"Trap separation {trap_separation_um}μm < minimum {min_separation}μm (coupling risk)"
    return True, "Trap separation OK"
