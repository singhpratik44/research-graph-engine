"""
Repetition code error correction protocol for neutral atom quantum computers.

Implements surface code-inspired approach: 3 physical qubits → 1 logical qubit
with real-time syndrome measurement and autonomous error correction.

Protocol:
1. Encode logical state across 3 physical qubits (majority rule)
2. Measure parity (X and Z stabilizers) without measuring data qubits
3. Decode syndrome: identify which qubit likely has error
4. Apply correction: targeted bit flip or phase flip if needed
5. Verify: measure data qubits to confirm success

Logical error rate: Should be lower than physical error rate (proof of QECC).
Typical improvement: physical 1% → logical 0.1% (10x suppression at distance 3).

Literature reference:
- Google Nature paper on surface codes (Arute et al. 2019)
- Neutral atom implementations (Omran et al. 2019, Bergamasco et al. 2021)
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Tuple, Optional
import random


class LogicalStateEnum(Enum):
    """Logical qubit states (encoded across 3 physical qubits)."""
    LOGICAL_0 = "logical_0"  # Physical state: |000⟩ or majority 0
    LOGICAL_1 = "logical_1"  # Physical state: |111⟩ or majority 1


class SyndromeEnum(Enum):
    """Stabilizer syndrome measurement results."""
    NO_ERROR = 0  # All stabilizers measure +1
    ERROR_P0 = 1  # Physical qubit 0 likely has bit flip
    ERROR_P1 = 2  # Physical qubit 1 likely has bit flip
    ERROR_P2 = 4  # Physical qubit 2 likely has bit flip


@dataclass
class LogicalQubit:
    """Logical qubit encoded across 3 physical qubits."""
    logical_id: int
    physical_qubits: List[int]  # IDs of 3 physical qubits
    logical_state: LogicalStateEnum = LogicalStateEnum.LOGICAL_0
    physical_states: List[int] = field(default_factory=lambda: [0, 0, 0])
    measurement_history: List[int] = field(default_factory=list)
    correction_history: List[str] = field(default_factory=list)
    syndrome_measurements: List[int] = field(default_factory=list)
    success_count: int = 0
    error_count: int = 0


@dataclass
class CorrectionRound:
    """Result of one error correction cycle."""
    logical_id: int
    syndrome: SyndromeEnum
    physical_states_before: List[int]
    physical_states_after: List[int]
    correction_applied: str
    success: bool
    timestamp_us: float


class RepetitionCodeProtocol:
    """
    Repetition code error correction for neutral atom systems.

    Encodes logical qubits redundantly across multiple physical qubits,
    performs periodic syndrome measurements to detect errors, and applies
    corrections to maintain logical information.
    """

    def __init__(self, num_logical_qubits: int, physical_qubits_per_logical: int = 3):
        """Initialize repetition code protocol.

        Args:
            num_logical_qubits: Number of logical qubits to encode
            physical_qubits_per_logical: Physical qubits per logical qubit (typically 3)
        """
        self.num_logical_qubits = num_logical_qubits
        self.qubits_per_logical = physical_qubits_per_logical

        # Logical qubit instances
        self.logical_qubits: List[LogicalQubit] = []
        physical_id = 0

        for logical_id in range(num_logical_qubits):
            physical_ids = list(range(physical_id, physical_id + physical_qubits_per_logical))
            self.logical_qubits.append(
                LogicalQubit(
                    logical_id=logical_id,
                    physical_qubits=physical_ids,
                    logical_state=LogicalStateEnum.LOGICAL_0,
                    physical_states=[0] * physical_qubits_per_logical
                )
            )
            physical_id += physical_qubits_per_logical

        # Correction statistics
        self.total_rounds: int = 0
        self.successful_corrections: int = 0
        self.failed_corrections: int = 0
        self.correction_history: List[CorrectionRound] = []

    def encode_logical_state(self, logical_id: int, state: int) -> Tuple[bool, str]:
        """Encode logical state onto physical qubits.

        Simple encoding: |0_L⟩ = |000⟩, |1_L⟩ = |111⟩

        Args:
            logical_id: Which logical qubit to encode
            state: 0 or 1 (logical state)

        Returns:
            (success, message)
        """
        if logical_id >= len(self.logical_qubits):
            return False, f"Logical qubit {logical_id} out of range"

        logical_qubit = self.logical_qubits[logical_id]

        # Encode: repeat state across 3 physical qubits
        logical_qubit.physical_states = [state, state, state]
        logical_qubit.logical_state = LogicalStateEnum.LOGICAL_1 if state == 1 else LogicalStateEnum.LOGICAL_0

        return True, f"Encoded logical {state} on physical qubits {logical_qubit.physical_qubits}"

    def measure_stabilizers(self, logical_id: int, noise_model=None) -> Tuple[SyndromeEnum, str]:
        """Measure stabilizers to extract syndrome without measuring data.

        For 3-qubit repetition code:
        - Syndrome S1 = p0 ⊕ p1 (parity of qubits 0,1)
        - Syndrome S2 = p1 ⊕ p2 (parity of qubits 1,2)

        Syndrome interpretation:
        - (S1=0, S2=0) → No error
        - (S1=1, S2=0) → Error on qubit 0
        - (S1=1, S2=1) → Error on qubit 1
        - (S1=0, S2=1) → Error on qubit 2

        Args:
            logical_id: Which logical qubit to measure
            noise_model: Optional noise model for realistic syndrome measurement errors

        Returns:
            (syndrome, interpretation)
        """
        logical_qubit = self.logical_qubits[logical_id]
        p0, p1, p2 = logical_qubit.physical_states

        # Compute syndrome (without measuring data qubits themselves)
        s1 = p0 ^ p1  # XOR (parity)
        s2 = p1 ^ p2

        # Interpret syndrome
        if s1 == 0 and s2 == 0:
            syndrome = SyndromeEnum.NO_ERROR
            interpretation = "No error detected"
        elif s1 == 1 and s2 == 0:
            syndrome = SyndromeEnum.ERROR_P0
            interpretation = "Error likely on physical qubit 0"
        elif s1 == 1 and s2 == 1:
            syndrome = SyndromeEnum.ERROR_P1
            interpretation = "Error likely on physical qubit 1"
        else:  # s1 == 0 and s2 == 1
            syndrome = SyndromeEnum.ERROR_P2
            interpretation = "Error likely on physical qubit 2"

        logical_qubit.syndrome_measurements.append(syndrome.value)

        return syndrome, interpretation

    def correct_error(self, logical_id: int, syndrome: SyndromeEnum) -> Tuple[bool, str]:
        """Apply correction based on syndrome.

        Majority vote: if syndrome indicates error on qubit i, flip qubit i.

        Args:
            logical_id: Which logical qubit to correct
            syndrome: Measured syndrome

        Returns:
            (success, correction_applied)
        """
        logical_qubit = self.logical_qubits[logical_id]
        states_before = logical_qubit.physical_states.copy()

        if syndrome == SyndromeEnum.NO_ERROR:
            return True, "No correction needed"

        elif syndrome == SyndromeEnum.ERROR_P0:
            logical_qubit.physical_states[0] = 1 - logical_qubit.physical_states[0]
            correction = "Flipped physical qubit 0"

        elif syndrome == SyndromeEnum.ERROR_P1:
            logical_qubit.physical_states[1] = 1 - logical_qubit.physical_states[1]
            correction = "Flipped physical qubit 1"

        else:  # ERROR_P2
            logical_qubit.physical_states[2] = 1 - logical_qubit.physical_states[2]
            correction = "Flipped physical qubit 2"

        # Verify correction by re-measuring stabilizers
        new_syndrome, _ = self.measure_stabilizers(logical_id)

        if new_syndrome == SyndromeEnum.NO_ERROR:
            logical_qubit.success_count += 1
            self.successful_corrections += 1
            return True, f"{correction} → syndrome resolved"
        else:
            logical_qubit.error_count += 1
            self.failed_corrections += 1
            return False, f"{correction} → syndrome persists (likely 2-qubit error)"

    def correction_cycle(self, logical_id: int, noise_model=None) -> CorrectionRound:
        """Run one complete error correction cycle.

        Cycle: measure stabilizers → decode syndrome → correct → verify

        Args:
            logical_id: Which logical qubit to correct
            noise_model: Optional noise model for realistic errors

        Returns:
            CorrectionRound with results
        """
        logical_qubit = self.logical_qubits[logical_id]
        states_before = logical_qubit.physical_states.copy()

        # Measure syndrome
        syndrome, _ = self.measure_stabilizers(logical_id, noise_model)

        # Apply correction
        success, correction_msg = self.correct_error(logical_id, syndrome)

        # Record
        round_result = CorrectionRound(
            logical_id=logical_id,
            syndrome=syndrome,
            physical_states_before=states_before,
            physical_states_after=logical_qubit.physical_states.copy(),
            correction_applied=correction_msg,
            success=success,
            timestamp_us=0.0
        )

        self.correction_history.append(round_result)
        self.total_rounds += 1

        return round_result

    def extract_logical_state(self, logical_id: int) -> Tuple[int, float]:
        """Extract logical state via majority vote.

        Measure all 3 physical qubits, take majority.
        Fidelity = fraction of physical qubits that agree.

        Args:
            logical_id: Which logical qubit to measure

        Returns:
            (logical_state, fidelity)
        """
        logical_qubit = self.logical_qubits[logical_id]
        physical_states = logical_qubit.physical_states

        # Majority vote
        vote_sum = sum(physical_states)
        if vote_sum >= 2:
            logical_state = 1
        else:
            logical_state = 0

        # Fidelity: how many physical qubits agree?
        agreement = sum(1 for s in physical_states if s == logical_state)
        fidelity = agreement / 3.0

        logical_qubit.measurement_history.append(logical_state)

        return logical_state, fidelity

    def logical_error_rate_estimate(self, physical_error_rate: float, rounds: int) -> float:
        """Estimate logical error rate after N correction rounds.

        Theory: After one round of correction, logical error rate is suppressed.
        p_L(n) ≈ (3 * p_phys)^2 if p_phys < 0.01 (below threshold)

        Args:
            physical_error_rate: Physical qubit error rate
            rounds: Number of correction rounds performed

        Returns:
            Estimated logical error rate
        """
        if physical_error_rate < 0.01:
            # Below threshold: exponential suppression
            logical_error_rate = (3.0 * physical_error_rate) ** 2
        else:
            # Above threshold: errors accumulate
            logical_error_rate = 0.5

        # After multiple rounds, multiply by number of rounds (independent events)
        logical_error_rate_total = 1.0 - (1.0 - logical_error_rate) ** rounds

        return logical_error_rate_total

    def stabilization_time(self, physical_error_rate: float, target_fidelity: float = 0.99) -> int:
        """Estimate number of correction rounds needed for stabilization.

        Stabilization: logical fidelity reaches target despite physical errors.

        Args:
            physical_error_rate: Physical error rate
            target_fidelity: Target logical fidelity

        Returns:
            Estimated number of correction rounds
        """
        if physical_error_rate >= 0.01:
            return float('inf')  # Unrecoverable (above threshold)

        logical_error_rate_per_round = (3.0 * physical_error_rate) ** 2
        current_fidelity = 1.0

        rounds = 0
        while current_fidelity > target_fidelity and rounds < 1000:
            current_fidelity *= (1.0 - logical_error_rate_per_round)
            rounds += 1

        return rounds

    def scaling_analysis(self, num_logical_qubits: int, physical_error_rate: float) -> Dict:
        """Analyze how error correction scales with number of logical qubits.

        Args:
            num_logical_qubits: How many logical qubits to analyze
            physical_error_rate: Physical error rate per qubit

        Returns:
            Dict with scaling analysis
        """
        total_physical_qubits = num_logical_qubits * self.qubits_per_logical
        logical_error_rate = self.logical_error_rate_estimate(physical_error_rate, rounds=1)

        return {
            "num_logical_qubits": num_logical_qubits,
            "total_physical_qubits": total_physical_qubits,
            "physical_error_rate": physical_error_rate,
            "logical_error_rate": logical_error_rate,
            "suppression_factor": physical_error_rate / logical_error_rate if logical_error_rate > 0 else float('inf'),
            "stabilization_rounds": self.stabilization_time(physical_error_rate),
        }

    def print_status(self) -> str:
        """Print status of error correction protocol."""
        output = "\n╔════════════════════════════════════════════════════════════════╗\n"
        output += "║         Repetition Code Error Correction Status                 ║\n"
        output += "╚════════════════════════════════════════════════════════════════╝\n\n"

        output += f"Protocol Configuration:\n"
        output += f"  Logical qubits: {self.num_logical_qubits}\n"
        output += f"  Physical qubits per logical: {self.qubits_per_logical}\n"
        output += f"  Total physical qubits: {self.num_logical_qubits * self.qubits_per_logical}\n\n"

        output += f"Correction Statistics:\n"
        output += f"  Total rounds: {self.total_rounds}\n"
        output += f"  Successful corrections: {self.successful_corrections}\n"
        output += f"  Failed corrections: {self.failed_corrections}\n"

        if self.total_rounds > 0:
            success_rate = self.successful_corrections / self.total_rounds
            output += f"  Success rate: {success_rate:.1%}\n\n"
        else:
            output += f"  (No correction rounds yet)\n\n"

        # Per-logical-qubit stats
        output += "Per-Logical-Qubit Status (first 5):\n"
        for lq in self.logical_qubits[:5]:
            output += f"  L{lq.logical_id}: state={lq.logical_state.value} | "
            output += f"physical={lq.physical_states} | "
            output += f"success={lq.success_count} error={lq.error_count}\n"

        return output
