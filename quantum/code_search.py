#!/usr/bin/env python3
"""
Structured search over classical base codes for hypergraph_product.py --
the demo-scale stand-in for the LLM-guided evolutionary code discovery
this package's research is informed by (two independent 2026 groups, Max
Planck Institute for the Science of Light and IBM, both used an LLM as the
mutation operator in an open-ended structural search over qLDPC code
families, discovering constructions beating known baselines). This module
provides the pure, stateless building blocks -- mutation and scoring --
that `autonomous_loop.py` composes into an actual multi-round search
process; this module itself runs no loop and holds no state.

`mutate_base_code` is the default mutation operator: a bounded random
perturbation (flip a bit / add or remove a row / add or remove a column)
of a classical parity-check matrix. It is a deliberately simple,
deterministic-given-a-seed stand-in for what the cited research actually
uses (an LLM proposing structured mutations informed by the code's
algebraic properties) -- said plainly, the same "this heuristic proves
the loop closes, it is not the sophisticated thing itself" posture
`research_graph_workers.ReferenceWorker` takes in the main engine this
package is deliberately kept separate from. `evaluate_candidate`'s
`propose_mutation` parameter is the injection point: a caller with a real
LLM (see the main repo's `llm_worker.py` for the same injectable-call
pattern) can pass a smarter mutation operator without changing anything
else in this module or in `autonomous_loop.py`.
"""

import random
from typing import Callable, Optional, Tuple

import css_codes
import gf2
import hypergraph_product as hgp
from css_codes import CSSCode
from gf2 import Matrix

MutationOperator = Callable[[Matrix, random.Random], Matrix]

DEFAULT_MAX_QUBITS_FOR_SEARCH = 18  # keeps brute-force distance search fast across many rounds


def mutate_base_code(
    h: Matrix,
    rng: random.Random,
    min_rows: int = 1,
    min_cols: int = 1,
    max_rows: int = 4,
    max_cols: int = 4,
) -> Matrix:
    """
    One random, bounded perturbation of a classical parity-check matrix:
    flip a single bit, add or remove a row, or add or remove a column --
    chosen uniformly among whichever moves keep the result within
    [min_rows, max_rows] x [min_cols, max_cols]. Bounded so the resulting
    hypergraph-product code (n = n_c^2 + m^2 qubits) stays within this
    package's demo-scale qubit budget across many search rounds.
    """
    rows = [list(r) for r in h]
    m = len(rows)
    n_c = len(rows[0]) if rows else 0
    if m == 0 or n_c == 0:
        raise ValueError("h must be a non-empty m x n_c matrix")

    moves = ["flip_bit"]
    if m < max_rows:
        moves.append("add_row")
    if m > min_rows:
        moves.append("remove_row")
    if n_c < max_cols:
        moves.append("add_col")
    if n_c > min_cols:
        moves.append("remove_col")

    move = rng.choice(moves)
    if move == "flip_bit":
        i, j = rng.randrange(m), rng.randrange(n_c)
        rows[i][j] ^= 1
    elif move == "add_row":
        rows.append([rng.randint(0, 1) for _ in range(n_c)])
    elif move == "remove_row":
        del rows[rng.randrange(m)]
    elif move == "add_col":
        for row in rows:
            row.append(rng.randint(0, 1))
    elif move == "remove_col":
        j = rng.randrange(n_c)
        for row in rows:
            del row[j]

    return gf2.to_matrix(rows)


def score_code(code: CSSCode, distance: int) -> float:
    """
    A single, explicit, deliberately simple scoring heuristic balancing
    rate (k/n, useful logical qubits per physical qubit spent) and
    distance (error-correcting strength): k * d / n. This is NOT a claim
    that this is the objective real qLDPC code search should optimize --
    the cited research targets specific rate/distance tradeoffs and real
    hardware constraints this demo doesn't model. It exists so the search
    loop has one concrete, honestly-documented number to compare
    candidates by. 0.0 for a code with no logical qubits (k=0) -- nothing
    to protect, so no rate/distance tradeoff to score.
    """
    if code.k == 0 or code.n == 0:
        return 0.0
    return (code.k * distance) / code.n


def evaluate_candidate(
    h: Matrix,
    max_qubits: int = DEFAULT_MAX_QUBITS_FOR_SEARCH,
) -> Optional[Tuple[CSSCode, int, float]]:
    """
    Build the hypergraph-product quantum code for classical base code `h`
    and score it. Returns `None` (not an exception) for a candidate this
    module declines to fully evaluate: an invalid CSS construction, or one
    whose qubit count exceeds `max_qubits` (brute-force distance search is
    exponential; this keeps a many-round search loop fast rather than
    stalling on one oversized candidate). A `k=0` code is a valid,
    evaluable candidate -- it just scores 0.0, since `compute_distance`
    itself is undefined for it.
    """
    try:
        code = hgp.hypergraph_product_code(h)
    except (ValueError, css_codes.InvalidCSSConstructionError):
        return None
    if code.n > max_qubits:
        return None
    if code.k == 0:
        return code, 0, 0.0
    distance = css_codes.compute_distance(code, max_n=max_qubits)
    return code, distance, score_code(code, distance)
