"""
Realistic quantum noise model for neutral atom systems.

Implements quantum channels and experimental error modes based on published
results from Google Quantum AI, IonQ, and academic neutral atom labs.

Channels:
- Amplitude damping: spontaneous emission, atom loss (thermal)
- Phase damping: dephasing, trap frequency jitter, magnetic field noise
- Depolarizing: pulse errors, crosstalk, timing errors

Experimental failure modes:
- Measurement errors: readout fidelity depends on qubit state and detection efficiency
- Heating-dependent errors: trap temperature increases error probability
- Gate errors: single-qubit gate fidelity ~99.5%, two-qubit gate ~98%
- Initialization errors: loading atoms into traps, state preparation
"""

from dataclasses import dataclass
from enum import Enum
from typing import Tuple, Dict
import math


class NoiseChannelType(Enum):
    """Supported quantum noise channels."""
    AMPLITUDE_DAMPING = "amplitude_damping"  # T1: spontaneous emission
    PHASE_DAMPING = "phase_damping"  # T2: dephasing
    DEPOLARIZING = "depolarizing"  # Bit flip + phase flip
    MEASUREMENT_ERROR = "measurement_error"  # Readout infidelity
    HEATING = "heating"  # Trap temperature affects coherence


@dataclass
class NoiseParameters:
    """Parameterization of noise for neutral atom systems.

    Based on Google Atom Computing papers and IonQ specifications.
    """
    # Spontaneous emission (amplitude damping)
    T1_us: float = 10000.0  # Lifetime of excited state ~10ms (neutral atoms very long)

    # Dephasing time (phase damping)
    T2_us: float = 1000.0  # Coherence time ~1ms (magnetic field noise, trap jitter)

    # Gate errors (Rydberg gates on neutral atoms)
    single_qubit_gate_error: float = 0.001  # 99.9% fidelity typical
    two_qubit_gate_error: float = 0.010  # 99% fidelity typical (entangling gates harder)

    # Measurement (readout) errors
    measurement_error_ground: float = 0.01  # 1% error on |0⟩ state
    measurement_error_excited: float = 0.05  # 5% error on |1⟩ state (harder to distinguish)

    # Initialization errors
    initialization_error: float = 0.001  # 99.9% fidelity loading atoms

    # Heating-dependent errors (primary error source in neutral atoms)
    heating_error_coefficient: float = 0.001  # p_err increases by 0.1% per 10μK heating

    # Spontaneous emission during gates (Rydberg state lifetime)
    rydberg_lifetime_us: float = 100.0  # ~100μs for Rydberg state
    rydberg_gate_error_per_photon: float = 0.01  # 1% loss per photon scattered


@dataclass
class QubitNoiseState:
    """State of noise affecting a single qubit."""
    qubit_id: int
    current_state: int  # 0 or 1
    cumulative_heating_uk: float  # Temperature in μK
    time_in_coherent_superposition_us: float  # Time since last measurement
    errors_detected: int  # Count of detected bit flips
    phase_errors: int  # Count of detected phase errors


class QuantumNoiseModel:
    """
    Realistic noise model for neutral atom quantum computers.

    Applies quantum channels and experimental error modes to qubit states
    based on physical operations and environmental conditions.
    """

    def __init__(self, num_qubits: int = 100, noise_params: NoiseParameters = None):
        """Initialize noise model for qubit array.

        Args:
            num_qubits: Number of qubits in system
            noise_params: Noise parameters (uses defaults if None)
        """
        self.num_qubits = num_qubits
        self.params = noise_params or NoiseParameters()

        # Per-qubit noise state
        self.noise_state: Dict[int, QubitNoiseState] = {
            i: QubitNoiseState(
                qubit_id=i,
                current_state=0,
                cumulative_heating_uk=0.0,
                time_in_coherent_superposition_us=0.0,
                errors_detected=0,
                phase_errors=0
            )
            for i in range(num_qubits)
        }

    def apply_amplitude_damping(self, qubit_id: int, time_elapsed_us: float) -> Tuple[bool, str]:
        """Apply amplitude damping (spontaneous emission) to qubit.

        Error probability: p_AD = (1 - exp(-t/T1)) * fidelity_factor

        Args:
            qubit_id: Qubit to apply damping to
            time_elapsed_us: Time elapsed since last operation (μs)

        Returns:
            (error_occurred, error_description)
        """
        state = self.noise_state[qubit_id]

        # Spontaneous emission only affects excited states
        if state.current_state == 0:
            return False, "Amplitude damping: qubit in ground state, no decay"

        # Error probability increases with time
        error_prob = 1.0 - math.exp(-time_elapsed_us / self.params.T1_us)

        # Heating increases decay rate (higher temperature → more thermal radiation)
        heating_factor = 1.0 + (state.cumulative_heating_uk / 100.0) * self.params.heating_error_coefficient
        error_prob *= heating_factor

        # Clamp to valid probability
        error_prob = min(error_prob, 1.0)

        # Probabilistic error
        import random
        if random.random() < error_prob:
            state.current_state = 0  # Collapse to ground state
            state.errors_detected += 1
            return True, f"Amplitude damping: |1⟩→|0⟩ spontaneous emission (p={error_prob:.4f})"

        return False, f"Amplitude damping: survived with p={1-error_prob:.4f}"

    def apply_phase_damping(self, qubit_id: int, time_in_superposition_us: float) -> Tuple[bool, str]:
        """Apply phase damping (dephasing) to qubit.

        Error probability: p_PD = 0.5 * (1 - exp(-t/T2)) * fidelity_factor

        Args:
            qubit_id: Qubit to apply dephasing to
            time_in_superposition_us: Time spent in superposition (μs)

        Returns:
            (error_occurred, error_description)
        """
        state = self.noise_state[qubit_id]

        # Dephasing affects superpositions
        if time_in_superposition_us == 0:
            return False, "Phase damping: no superposition time"

        # Error probability from dephasing
        error_prob = 0.5 * (1.0 - math.exp(-time_in_superposition_us / self.params.T2_us))

        # Heating increases dephasing rate (trap frequency noise, magnetic field fluctuations)
        heating_factor = 1.0 + (state.cumulative_heating_uk / 100.0) * self.params.heating_error_coefficient * 2.0
        error_prob *= heating_factor
        error_prob = min(error_prob, 1.0)

        import random
        if random.random() < error_prob:
            # Phase error: flip sign of superposition (|+⟩ → |-⟩)
            state.phase_errors += 1
            return True, f"Phase damping: dephasing error (p={error_prob:.4f})"

        return False, f"Phase damping: coherence survived (p={1-error_prob:.4f})"

    def apply_depolarizing_noise(self, qubit_id: int, gate_type: str) -> Tuple[bool, str]:
        """Apply depolarizing noise from gate execution errors.

        Error probability depends on gate type and heating.

        Args:
            qubit_id: Qubit receiving gate
            gate_type: "single_qubit" or "two_qubit"

        Returns:
            (error_occurred, error_description)
        """
        state = self.noise_state[qubit_id]

        # Base error rate from gate fidelity
        if gate_type == "single_qubit":
            error_prob = self.params.single_qubit_gate_error
        elif gate_type == "two_qubit":
            error_prob = self.params.two_qubit_gate_error
        else:
            return False, f"Depolarizing: unknown gate type {gate_type}"

        # Heating increases gate error rate (worse control, atom motion)
        heating_factor = 1.0 + (state.cumulative_heating_uk / 100.0) * self.params.heating_error_coefficient
        error_prob *= heating_factor
        error_prob = min(error_prob, 1.0)

        import random
        if random.random() < error_prob:
            # Depolarizing: random bit flip or phase flip
            flip_type = random.choice(["bit_flip", "phase_flip"])
            if flip_type == "bit_flip":
                state.current_state = 1 - state.current_state  # X error
            # Phase flip doesn't change measured state but affects subsequent gates
            state.errors_detected += 1
            return True, f"Depolarizing: {flip_type} error from gate (p={error_prob:.4f})"

        return False, f"Depolarizing: gate succeeded (p={1-error_prob:.4f})"

    def apply_measurement_error(self, qubit_id: int, true_state: int) -> Tuple[int, float]:
        """Apply measurement (readout) error.

        Error probability depends on qubit state and detection efficiency.

        Args:
            qubit_id: Qubit being measured
            true_state: True quantum state (0 or 1)

        Returns:
            (measured_state, measurement_fidelity)
        """
        state = self.noise_state[qubit_id]

        # Error rate depends on whether measuring |0⟩ or |1⟩
        if true_state == 0:
            error_prob = self.params.measurement_error_ground
        else:
            error_prob = self.params.measurement_error_excited

        # Heating reduces detection efficiency (atom motion, fluorescence reduction)
        heating_factor = 1.0 + (state.cumulative_heating_uk / 100.0) * self.params.heating_error_coefficient
        error_prob *= heating_factor
        error_prob = min(error_prob, 1.0)

        import random
        if random.random() < error_prob:
            measured_state = 1 - true_state  # Flip measurement
            measurement_fidelity = 1.0 - error_prob
        else:
            measured_state = true_state
            measurement_fidelity = 1.0 - error_prob

        return measured_state, measurement_fidelity

    def heating_increases_error_rate(self, qubit_id: int, heating_amount_uk: float) -> Dict[str, float]:
        """Quantify how heating affects error rates.

        Args:
            qubit_id: Qubit being heated
            heating_amount_uk: Additional heating (μK)

        Returns:
            Dict of error rates after heating
        """
        state = self.noise_state[qubit_id]
        state.cumulative_heating_uk += heating_amount_uk

        # Error rate as function of temperature
        base_error_rate = 0.01  # 1% base error rate
        temp_dependent_error = base_error_rate + (state.cumulative_heating_uk / 500.0) * 0.1
        temp_dependent_error = min(temp_dependent_error, 0.5)  # Cap at 50%

        return {
            "cumulative_heating_uk": state.cumulative_heating_uk,
            "amplitude_damping_rate": temp_dependent_error * 0.3,
            "phase_damping_rate": temp_dependent_error * 0.5,
            "depolarizing_rate": temp_dependent_error * 0.2,
            "total_error_rate": temp_dependent_error,
        }

    def physical_error_rate_to_logical(self, physical_error_rate: float,
                                      code_distance: int = 3) -> float:
        """Convert physical error rate to logical error rate under repetition code.

        Repetition code: logical error rate suppressed below physical for distance d:
        p_L ≈ 3 * (p_phys)^d when p_phys < threshold

        Threshold for repetition code: ~1% for depolarizing noise

        Args:
            physical_error_rate: Physical qubit error rate
            code_distance: Code distance (number of physical qubits per logical, typically 3)

        Returns:
            Estimated logical error rate (lower than physical below threshold)
        """
        THRESHOLD = 0.01  # 1% threshold for repetition codes

        if physical_error_rate < THRESHOLD:
            # Below threshold: suppression with code distance
            # For 3-qubit code: p_L ≈ 3 * p^2 (quadratic suppression)
            logical_error_rate = 3.0 * (physical_error_rate ** 2)
        else:
            # Above threshold: errors accumulate, can't correct
            logical_error_rate = 0.5

        return logical_error_rate

    def print_noise_state(self) -> str:
        """Print current noise state across all qubits."""
        output = "\n╔════════════════════════════════════════════════════════════════╗\n"
        output += "║              Quantum Noise Model State                          ║\n"
        output += "╚════════════════════════════════════════════════════════════════╝\n\n"

        # Summary statistics
        avg_heating = sum(s.cumulative_heating_uk for s in self.noise_state.values()) / len(self.noise_state)
        total_errors = sum(s.errors_detected for s in self.noise_state.values())
        total_phase_errors = sum(s.phase_errors for s in self.noise_state.values())

        output += f"System Noise Parameters:\n"
        output += f"  T1 (spontaneous emission): {self.params.T1_us:.1f} μs\n"
        output += f"  T2 (coherence time): {self.params.T2_us:.1f} μs\n"
        output += f"  Single-qubit gate error: {self.params.single_qubit_gate_error:.4f}\n"
        output += f"  Two-qubit gate error: {self.params.two_qubit_gate_error:.4f}\n\n"

        output += f"System State:\n"
        output += f"  Qubits: {self.num_qubits}\n"
        output += f"  Average heating: {avg_heating:.1f} μK\n"
        output += f"  Total bit-flip errors: {total_errors}\n"
        output += f"  Total phase errors: {total_phase_errors}\n"
        output += f"  Error density: {(total_errors + total_phase_errors) / (self.num_qubits * 100):.4f} per qubit-100ops\n\n"

        # Per-qubit details (sample first 10)
        output += "Per-Qubit Heating (first 10 qubits):\n"
        for i in range(min(10, self.num_qubits)):
            state = self.noise_state[i]
            output += f"  Q{i:2d}: {state.cumulative_heating_uk:6.1f} μK | errors={state.errors_detected:2d} | phase={state.phase_errors:2d}\n"

        return output

    def reset_heating(self):
        """Reset cumulative heating (e.g., after laser cooling)."""
        for state in self.noise_state.values():
            state.cumulative_heating_uk = 0.0
            state.time_in_coherent_superposition_us = 0.0
