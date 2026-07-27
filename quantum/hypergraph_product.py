#!/usr/bin/env python3
"""
Hypergraph product codes (Tillich-Zemor, 2009) -- the real construction
that turns a single classical linear code into a family of quantum LDPC
(low-density parity-check) codes. This is the construction underlying the
"lifted-product"/"bivariate bicycle" qLDPC code families this package's
research is informed by (two independent groups, Max Planck Institute for
the Science of Light and IBM, both used LLM-guided structured search over
constructions in this same family to discover new high-performing codes in
mid-2026 -- see quantum/code_search.py, which searches over the classical
base code `H` this module consumes).

Given a single classical parity-check matrix H (shape m x n_c: m checks
over n_c bits), the hypergraph product builds a CSS quantum code on
n = n_c^2 + m^2 physical qubits, with

    H_X = [ H (x) I_{n_c}  |  I_m (x) H^T ]
    H_Z = [ I_{n_c} (x) H  |  H^T (x) I_m ]

where (x) is the Kronecker product. The commutation condition
H_X @ H_Z^T == 0 that css_codes.build_css_code checks is guaranteed by
this construction as an algebraic identity (H (x) I_{n_c} and I_{n_c} (x) H
commute for exactly the same reason a Kronecker sum's tensor factors do);
`build_css_code` re-verifies it anyway rather than trusting that claim
blindly, the same "don't take a construction's own correctness on faith"
posture the rest of this package's tests apply everywhere else.

If `H` itself is a good classical LDPC code (few 1s per row/column, i.e.
each check touches only a handful of bits), the resulting quantum code is
LDPC too -- each qubit participates in only a bounded number of stabilizer
checks, which is what makes these codes physically realizable (unlike the
naive Shor/Steane-style constructions, whose stabilizer weight grows with
code size).
"""

import css_codes
import gf2


def hypergraph_product_code(h) -> css_codes.CSSCode:
    """
    Build a CSS quantum code from a single classical parity-check matrix
    `h` (a sequence of 0/1 rows, shape m x n_c) via the hypergraph product.
    Raises ValueError if `h` is empty in either dimension -- there is no
    quantum code to build from a classical code with zero checks or zero
    bits.
    """
    h = gf2.to_matrix(h)
    m = len(h)
    n_c = len(h[0]) if h else 0
    if m == 0 or n_c == 0:
        raise ValueError("H must be a non-empty m x n_c matrix (m checks, n_c bits)")

    h_t = gf2.transpose(h)
    i_m = gf2.identity(m)
    i_nc = gf2.identity(n_c)

    h_x = gf2.hstack(gf2.kron(h, i_nc), gf2.kron(i_m, h_t))
    h_z = gf2.hstack(gf2.kron(i_nc, h), gf2.kron(h_t, i_m))

    return css_codes.build_css_code(h_x, h_z)


def physical_qubit_count(m: int, n_c: int) -> int:
    """n = n_c^2 + m^2 -- computable directly from the classical code's
    shape, without building the full quantum code, for a caller (e.g.
    code_search.py) that wants to filter candidate classical codes by
    resulting qubit budget before paying for the full construction."""
    return n_c * n_c + m * m
