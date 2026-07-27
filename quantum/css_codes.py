#!/usr/bin/env python3
"""
CSS (Calderbank-Shor-Steane) stabilizer quantum error-correcting codes --
real stabilizer formalism, not a toy simulation. A CSS code is built from
two classical binary parity-check matrices, H_X and H_Z, satisfying the
commutation condition H_X @ H_Z^T == 0 (mod 2): every X-type stabilizer
generator (one per row of H_X) must commute with every Z-type stabilizer
generator (one per row of H_Z), or the resulting operators wouldn't all be
simultaneously measurable -- the defining requirement of a stabilizer code.

This module computes, from H_X/H_Z alone:
  - n         the number of physical qubits
  - k         the number of encoded logical qubits (n - rank(H_X) - rank(H_Z))
  - logical_x/logical_z   k representative logical operator pairs, chosen to
              satisfy the required symplectic pairing (logical_x[i] anti-
              commutes with logical_z[i], commutes with logical_z[j] for
              i != j, and with every stabilizer generator)
  - distance  (via compute_distance, not eagerly -- it's exponential in n)
              the minimum weight of any operator that acts on the encoded
              logical qubits without being detectable by any stabilizer
              measurement -- the standard [[n, k, d]] code parameters

This is the real, standard CSS-code linear-algebra machinery described in
any stabilizer-code reference (e.g. Nielsen & Chuang; Gottesman's thesis);
`hypergraph_product.py` builds on this module to construct actual quantum
LDPC code families (the same family of construction the "LLM-discovered
qLDPC codes" research this package is informed by targets) from a single
classical base code, rather than requiring H_X/H_Z to be supplied by hand.
"""

from dataclasses import dataclass, field
from typing import List, Optional

import gf2
from gf2 import Matrix, Vector


class InvalidCSSConstructionError(ValueError):
    """H_X/H_Z don't satisfy the requirements of a valid CSS code."""


@dataclass
class CSSCode:
    """
    A CSS stabilizer code's full parameter set. Construct via
    `build_css_code(h_x, h_z)` -- this dataclass itself does no validation,
    it's just the computed result.
    """
    n: int
    k: int
    h_x: Matrix
    h_z: Matrix
    logical_x: List[Vector]
    logical_z: List[Vector]
    distance: Optional[int] = field(default=None)

    @property
    def rate(self) -> float:
        """k/n -- how much of the physical qubit budget becomes usable logical
        qubits. 0.0 for a code with no logical qubits (k=0, n>0)."""
        return self.k / self.n if self.n else 0.0

    def parameters(self) -> str:
        """The standard [[n, k, d]] notation; d shown as '?' if not yet computed."""
        d = self.distance if self.distance is not None else "?"
        return f"[[{self.n}, {self.k}, {d}]]"


def _quotient_basis(candidates: List[Vector], subspace: Matrix, k: int) -> List[Vector]:
    """
    Greedily select up to `k` vectors from `candidates` that are
    independent modulo the row space of `subspace` -- i.e. extend a basis
    for `subspace` using representatives drawn from `candidates`, keeping
    only the ones that add a genuinely new direction. Raises if fewer than
    `k` independent representatives can be found (a sign the caller's
    H_X/H_Z don't actually satisfy the CSS commutation/rank relationships
    this function assumes).
    """
    basis_rows = list(subspace)
    selected: List[Vector] = []
    for v in candidates:
        current = gf2.to_matrix(basis_rows) if basis_rows else tuple()
        if gf2.row_space_contains(current, v):
            continue
        selected.append(v)
        basis_rows.append(v)
        if len(selected) == k:
            break
    if len(selected) < k:
        raise InvalidCSSConstructionError(
            f"could not find {k} independent logical representatives "
            f"(only found {len(selected)}) -- H_X/H_Z may not satisfy a "
            f"valid CSS construction")
    return selected


def _paired_logical_z(logical_x: List[Vector], ker_h_x_basis: List[Vector]) -> List[Vector]:
    """
    For each logical_x[i], find a logical_z[i] in span(ker_h_x_basis) (so
    it automatically commutes with every X-stabilizer) satisfying the
    symplectic duality every stabilizer-code textbook requires:
    dot(logical_x[i], logical_z[j]) == (1 if i == j else 0). Solved as one
    linear system per target logical qubit via `gf2.solve`.
    """
    k = len(logical_x)
    m = len(ker_h_x_basis)
    a = gf2.to_matrix([
        [gf2.dot(lx, ker_h_x_basis[col]) for col in range(m)]
        for lx in logical_x
    ])
    logical_z: List[Vector] = []
    for j in range(k):
        target = tuple(1 if i == j else 0 for i in range(k))
        coeffs = gf2.solve(a, target)
        if coeffs is None:
            raise InvalidCSSConstructionError(
                "failed to find a symplectically-paired logical Z operator -- "
                "H_X/H_Z may not satisfy the non-degenerate pairing a valid "
                "CSS code requires")
        z = (0,) * len(ker_h_x_basis[0])
        for col, bit in enumerate(coeffs):
            if bit:
                z = gf2.add(z, ker_h_x_basis[col])
        logical_z.append(z)
    return logical_z


def build_css_code(h_x, h_z) -> CSSCode:
    """
    Construct a CSSCode from classical parity-check matrices H_X, H_Z
    (each a sequence of 0/1 rows over the same number of columns n).
    Raises InvalidCSSConstructionError if H_X/H_Z don't commute (the one
    hard physical requirement of a stabilizer code) or if the resulting
    k would be negative (over-constrained -- more independent stabilizers
    than qubits).
    """
    h_x = gf2.to_matrix(h_x)
    h_z = gf2.to_matrix(h_z)

    n_x = len(h_x[0]) if h_x else None
    n_z = len(h_z[0]) if h_z else None
    if n_x is not None and n_z is not None and n_x != n_z:
        raise InvalidCSSConstructionError(
            f"H_X has {n_x} columns but H_Z has {n_z} -- both must describe "
            f"the same number of physical qubits")
    n = n_x if n_x is not None else n_z
    if n is None:
        raise InvalidCSSConstructionError("at least one of H_X/H_Z must be non-empty")

    commutator = gf2.matmul(h_x, gf2.transpose(h_z)) if h_x and h_z else tuple()
    if any(any(bit != 0 for bit in row) for row in commutator):
        raise InvalidCSSConstructionError(
            "H_X @ H_Z^T != 0 -- these stabilizer generators do not all "
            "commute, so this is not a valid CSS code")

    rank_x = gf2.rank(h_x)
    rank_z = gf2.rank(h_z)
    k = n - rank_x - rank_z
    if k < 0:
        raise InvalidCSSConstructionError(
            f"n - rank(H_X) - rank(H_Z) = {n} - {rank_x} - {rank_z} = {k} < 0 "
            f"-- more independent stabilizers than qubits")

    if k == 0:
        return CSSCode(n=n, k=0, h_x=h_x, h_z=h_z, logical_x=[], logical_z=[])

    ker_h_z = gf2.nullspace(h_z, n_cols=n)
    logical_x = _quotient_basis(ker_h_z, h_x, k)
    ker_h_x = gf2.nullspace(h_x, n_cols=n)
    logical_z = _paired_logical_z(logical_x, ker_h_x)

    return CSSCode(n=n, k=k, h_x=h_x, h_z=h_z, logical_x=logical_x, logical_z=logical_z)


def _min_weight_nontrivial_logical(ker_check: Matrix, stabilizer_check: Matrix, n: int) -> int:
    """
    Brute-force search over every nonzero length-n binary vector for the
    minimum Hamming weight of one that (a) is in the kernel of
    `ker_check` (so it's a valid logical-type operator representative,
    commuting with the opposite stabilizer type) but (b) is NOT in the row
    space of `stabilizer_check` (so it isn't itself just a stabilizer --
    a trivial, physically undetectable-as-an-error identity operation).
    Exponential in n by construction -- there is no known efficient exact
    algorithm for general stabilizer-code minimum distance, only bounded
    approximations; this module targets small demo/teaching-sized codes.
    """
    reduced_stab, pivots = gf2.row_reduce(stabilizer_check)
    best = None
    for value in range(1, 1 << n):
        v = tuple((value >> i) & 1 for i in range(n))
        if not gf2.is_zero_vector(gf2.matvec(ker_check, v)):
            continue
        residual = gf2.reduce_against_rows(reduced_stab, pivots, v)
        if gf2.is_zero_vector(residual):
            continue  # v is just a stabilizer element -- a trivial logical operator
        w = gf2.weight(v)
        if best is None or w < best:
            best = w
    if best is None:
        raise InvalidCSSConstructionError(
            "no nontrivial logical operator found while searching for distance "
            "-- the code may have k=0 or be malformed")
    return best


DEFAULT_MAX_QUBITS_FOR_DISTANCE = 20


def compute_distance(code: CSSCode, max_n: int = DEFAULT_MAX_QUBITS_FOR_DISTANCE) -> int:
    """
    The code distance d = min(d_X, d_Z): the minimum weight of any
    nontrivial logical X-type or Z-type operator. Brute force, so bounded
    by `max_n` (default 20 physical qubits -- 2^20 candidate vectors is
    still a few seconds of pure Python; raise `max_n` explicitly if a
    caller accepts the cost for a larger code). Mutates `code.distance`
    as a cache and also returns it, so repeated calls after the first are
    free.
    """
    if code.k == 0:
        raise ValueError("distance is undefined for a code with no logical qubits (k=0)")
    if code.distance is not None:
        return code.distance
    if code.n > max_n:
        raise ValueError(
            f"brute-force distance computation is only enabled by default for "
            f"n <= {max_n} qubits (this code has n={code.n}); pass a larger "
            f"max_n explicitly if you accept the exponential (2^n) cost")
    d_x = _min_weight_nontrivial_logical(code.h_z, code.h_x, code.n)
    d_z = _min_weight_nontrivial_logical(code.h_x, code.h_z, code.n)
    code.distance = min(d_x, d_z)
    return code.distance
