#!/usr/bin/env python3
"""
Monte Carlo logical error rate simulation for a CSSCode -- the "sense"
step of this package's autonomous control loop (autonomous_loop.py): given
a code and a physical per-qubit error rate, how often does error
correction actually fail to protect the encoded logical qubits?

CSS codes decouple X and Z error correction: X (bit-flip) errors are
detected by Z-stabilizer syndromes and corrected using H_Z; Z (phase-flip)
errors are detected by X-stabilizer syndromes and corrected using H_X.
Both channels are simulated independently here (a simple, symmetric
depolarizing-like noise model: each qubit independently gets an X error
and, independently, a Z error, each with probability `physical_error_rate`).

Decoding uses an exact coset-leader (minimum-weight) syndrome table,
built once per code and reused across all trials -- exact and correct for
small demo-scale codes, but built by brute-force enumeration, so it shares
the same small-code-only scope as `css_codes.compute_distance`.
"""

import itertools
import random
from dataclasses import dataclass, field
from typing import Dict, Optional

import gf2
from css_codes import CSSCode
from gf2 import Matrix, Vector


def build_syndrome_table(check_matrix: Matrix, n: int, max_weight: Optional[int] = None) -> Dict[Vector, Vector]:
    """
    Coset-leader decoding table: for every syndrome `check_matrix` can
    produce, the minimum-Hamming-weight error pattern that produces it --
    built by enumerating error patterns in increasing weight order (0, 1,
    2, ...) and keeping the first (hence minimum-weight) error seen for
    each syndrome, stopping early once every reachable syndrome
    (2^len(check_matrix) of them at most) has been covered.

    Exact for weights up to `max_weight` (default `n`, i.e. exhaustive
    coverage); table construction is exponential in the worst case, so
    this targets the same small demo-code scale as
    `css_codes.compute_distance` (n in the tens of qubits, not thousands).
    """
    if max_weight is None:
        max_weight = n
    r = len(check_matrix)
    total_syndromes = 1 << r
    table: Dict[Vector, Vector] = {(0,) * r: (0,) * n}
    if len(table) >= total_syndromes:
        return table

    for w in range(1, max_weight + 1):
        for positions in itertools.combinations(range(n), w):
            error = [0] * n
            for p in positions:
                error[p] = 1
            error_vec = tuple(error)
            syndrome = gf2.matvec(check_matrix, error_vec)
            if syndrome not in table:
                table[syndrome] = error_vec
        if len(table) >= total_syndromes:
            break
    return table


@dataclass
class SimulationResult:
    physical_error_rate: float
    trials: int
    logical_failures: int
    logical_error_rate: float = field(init=False)

    def __post_init__(self):
        self.logical_error_rate = self.logical_failures / self.trials if self.trials else 0.0


def simulate_logical_error_rate(
    code: CSSCode,
    physical_error_rate: float,
    trials: int = 1000,
    rng: Optional[random.Random] = None,
    max_decoder_weight: Optional[int] = None,
) -> SimulationResult:
    """
    Monte Carlo estimate of how often error correction fails at a given
    physical error rate. For each trial: sample independent X and Z error
    vectors (each qubit independently errs with probability
    `physical_error_rate` in each channel), decode each channel via its
    syndrome table, and check whether the residual (error XOR correction)
    is a nontrivial logical operator -- a logical failure -- rather than a
    trivial stabilizer element (a successfully corrected error).

    The residual is *always* in the relevant kernel by construction (the
    correction is chosen to have the same syndrome as the error, so their
    XOR has zero syndrome) -- what varies is only whether that residual
    happens to also lie in the stabilizer's row space (success) or not
    (a logical error slipped through uncorrected).

    `rng` is injectable (same pattern as `llm_worker.py`'s `call_model` and
    `arxiv_ingest.py`'s `http_get`) so a caller can seed it for
    reproducible results; omitting it uses a fresh, unseeded `Random()`.
    """
    if not 0.0 <= physical_error_rate <= 1.0:
        raise ValueError(f"physical_error_rate must be in [0, 1], got {physical_error_rate}")
    rng = rng if rng is not None else random.Random()

    table_x = build_syndrome_table(code.h_z, code.n, max_decoder_weight)  # decodes X errors
    table_z = build_syndrome_table(code.h_x, code.n, max_decoder_weight)  # decodes Z errors
    reduced_hx, pivots_hx = gf2.row_reduce(code.h_x)
    reduced_hz, pivots_hz = gf2.row_reduce(code.h_z)

    logical_failures = 0
    for _ in range(trials):
        error_x = tuple(1 if rng.random() < physical_error_rate else 0 for _ in range(code.n))
        error_z = tuple(1 if rng.random() < physical_error_rate else 0 for _ in range(code.n))

        syndrome_x = gf2.matvec(code.h_z, error_x)
        correction_x = table_x.get(syndrome_x, (0,) * code.n)
        residual_x = gf2.add(error_x, correction_x)

        syndrome_z = gf2.matvec(code.h_x, error_z)
        correction_z = table_z.get(syndrome_z, (0,) * code.n)
        residual_z = gf2.add(error_z, correction_z)

        x_is_logical = not gf2.is_zero_vector(
            gf2.reduce_against_rows(reduced_hx, pivots_hx, residual_x))
        z_is_logical = not gf2.is_zero_vector(
            gf2.reduce_against_rows(reduced_hz, pivots_hz, residual_z))

        if x_is_logical or z_is_logical:
            logical_failures += 1

    return SimulationResult(physical_error_rate=physical_error_rate, trials=trials,
                            logical_failures=logical_failures)
