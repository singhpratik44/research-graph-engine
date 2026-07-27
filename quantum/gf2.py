#!/usr/bin/env python3
"""
GF(2) linear algebra: the foundation every stabilizer/CSS quantum code
computation in this package sits on. Quantum stabilizer codes are defined
by binary matrices whose arithmetic is mod-2 (XOR for addition, AND for
multiplication) -- rank, kernel (nullspace), and row-reduction over GF(2)
are the operations needed to compute a code's number of logical qubits,
its logical operators, and its distance. This module is deliberately
independent of anything quantum-specific: it is pure binary linear algebra,
reused by css_codes.py and hypergraph_product.py.

Matrices are represented as tuples of tuples of 0/1 ints (immutable,
hashable, easy to reason about for a small module like this) rather than
numpy arrays -- this package has no numpy dependency, and these matrices
are small enough (tens of rows/columns for the demo codes this package
targets) that plain Python is both sufficient and easier to verify by hand
against textbook examples.
"""

from typing import List, Optional, Sequence, Tuple

Matrix = Tuple[Tuple[int, ...], ...]
Vector = Tuple[int, ...]


def to_matrix(rows: Sequence[Sequence[int]]) -> Matrix:
    """Normalize a sequence of 0/1 rows into the canonical Matrix type."""
    return tuple(tuple(int(x) & 1 for x in row) for row in rows)


def to_vector(values: Sequence[int]) -> Vector:
    return tuple(int(x) & 1 for x in values)


def zeros(rows: int, cols: int) -> Matrix:
    return tuple(tuple(0 for _ in range(cols)) for _ in range(rows))


def add(a: Vector, b: Vector) -> Vector:
    """XOR two vectors of equal length -- GF(2) addition."""
    if len(a) != len(b):
        raise ValueError(f"vector length mismatch: {len(a)} != {len(b)}")
    return tuple(x ^ y for x, y in zip(a, b))


def dot(a: Vector, b: Vector) -> int:
    """GF(2) inner product: parity of the bitwise-AND, i.e. sum(a_i * b_i) mod 2."""
    if len(a) != len(b):
        raise ValueError(f"vector length mismatch: {len(a)} != {len(b)}")
    return sum(x & y for x, y in zip(a, b)) % 2


def matvec(m: Matrix, v: Vector) -> Vector:
    """m @ v over GF(2)."""
    if m and len(m[0]) != len(v):
        raise ValueError(f"shape mismatch: matrix has {len(m[0])} columns, vector has {len(v)}")
    return tuple(dot(row, v) for row in m)


def matmul(a: Matrix, b: Matrix) -> Matrix:
    """a @ b over GF(2). b is provided row-major; multiplication transposes it internally."""
    if not a or not b:
        return tuple()
    if len(a[0]) != len(b):
        raise ValueError(f"shape mismatch: {len(a)}x{len(a[0])} @ {len(b)}x{len(b[0]) if b else 0}")
    b_cols = list(zip(*b))  # columns of b, as tuples
    return tuple(tuple(dot(row, col) for col in b_cols) for row in a)


def transpose(m: Matrix) -> Matrix:
    if not m:
        return tuple()
    return tuple(zip(*m))


def row_reduce(m: Matrix) -> Tuple[Matrix, List[int]]:
    """
    Row-echelon form over GF(2) via Gaussian elimination (XOR row
    operations only -- there is nothing to scale by over GF(2) besides 1).
    Returns (reduced_matrix, pivot_columns) with pivot_columns listing
    which column each successive nonzero row was pivoted on, in row order.
    Rows that reduce to all-zero are dropped, so the returned matrix's row
    count equals the matrix's rank.
    """
    if not m:
        return tuple(), []
    rows = [list(r) for r in m]
    n_cols = len(rows[0])
    pivot_row = 0
    pivots: List[int] = []
    for col in range(n_cols):
        pivot = next((r for r in range(pivot_row, len(rows)) if rows[r][col] == 1), None)
        if pivot is None:
            continue
        rows[pivot_row], rows[pivot] = rows[pivot], rows[pivot_row]
        for r in range(len(rows)):
            if r != pivot_row and rows[r][col] == 1:
                rows[r] = [a ^ b for a, b in zip(rows[r], rows[pivot_row])]
        pivots.append(col)
        pivot_row += 1
        if pivot_row == len(rows):
            break
    reduced = tuple(tuple(r) for r in rows[:pivot_row])
    return reduced, pivots


def rank(m: Matrix) -> int:
    """Rank of `m` over GF(2)."""
    reduced, _ = row_reduce(m)
    return len(reduced)


def nullspace(m: Matrix, n_cols: Optional[int] = None) -> List[Vector]:
    """
    Basis for the nullspace (kernel) of `m` over GF(2): every vector v with
    m @ v == 0. Standard approach: row-reduce to identify pivot and free
    columns, then for each free column build a basis vector by setting
    that free variable to 1, all other free variables to 0, and solving
    for the pivot variables via back-substitution over the reduced rows.

    `n_cols` lets a caller with an all-zero-rows matrix (rank 0, so
    row_reduce alone can't recover the column count) still get a full
    identity-basis nullspace back; it defaults to `len(m[0])` when `m` has
    any rows.
    """
    if n_cols is None:
        if not m:
            raise ValueError("n_cols must be given when m has no rows")
        n_cols = len(m[0])
    reduced, pivots = row_reduce(m)
    pivot_set = set(pivots)
    free_cols = [c for c in range(n_cols) if c not in pivot_set]

    basis: List[Vector] = []
    for free_col in free_cols:
        vec = [0] * n_cols
        vec[free_col] = 1
        # Back-substitute: for each pivot row (pivot at column `pivots[i]`),
        # the row equation is pivot_var + sum(other 1-entries * their var) = 0,
        # so pivot_var = sum(1-entries at free columns that are set) mod 2.
        for i, pcol in enumerate(pivots):
            row = reduced[i]
            value = 0
            for c in free_cols:
                if c != free_col and row[c] == 1:
                    value ^= vec[c]
                elif c == free_col and row[c] == 1:
                    value ^= 1
            vec[pcol] = value
        basis.append(tuple(vec))
    return basis


def is_zero_vector(v: Vector) -> bool:
    return all(x == 0 for x in v)


def weight(v: Vector) -> int:
    """Hamming weight: number of nonzero entries."""
    return sum(1 for x in v if x != 0)


def solve(a: Matrix, b: Vector):
    """
    Find some vector c with a @ c == b over GF(2), or None if no solution
    exists (the system may be underdetermined -- any one valid solution is
    returned, with free variables implicitly set to 0). Standard augmented-
    matrix Gaussian elimination: append b as an extra column, row-reduce,
    and check whether any row reduced to all-zero coefficients but a
    nonzero right-hand side (the classic "0 = 1" inconsistency signal).
    """
    if not a:
        return tuple() if is_zero_vector(b) else None
    n_cols = len(a[0])
    augmented = to_matrix([list(row) + [bit] for row, bit in zip(a, b)])
    reduced, pivots = row_reduce(augmented)
    if n_cols in pivots:  # a row's only surviving 1 is in the augmented column: 0 = 1
        return None
    c = [0] * n_cols
    for i, pcol in enumerate(pivots):
        c[pcol] = reduced[i][n_cols]
    return tuple(c)


def row_space_contains(m: Matrix, v: Vector) -> bool:
    """Whether `v` is a GF(2) linear combination of the rows of `m`
    (i.e. `v` is in the row space of `m`) -- checked by seeing whether
    appending `v` to `m` changes the rank."""
    if not m:
        return is_zero_vector(v)
    return rank(m + (v,)) == rank(m)


def identity(n: int) -> Matrix:
    return tuple(tuple(1 if i == j else 0 for j in range(n)) for i in range(n))


def kron(a: Matrix, b: Matrix) -> Matrix:
    """Kronecker (tensor) product of two matrices over GF(2) -- the core
    operation the hypergraph-product quantum code construction is built
    from. Block (i, j) of the result is `a[i][j] * b` (which, over GF(2),
    is either a copy of `b` or an all-zero block of `b`'s shape)."""
    if not a or not b:
        return tuple()
    rows_a, cols_a = len(a), len(a[0])
    rows_b, cols_b = len(b), len(b[0])
    result = []
    for i in range(rows_a):
        for bi in range(rows_b):
            row = []
            for j in range(cols_a):
                bit = a[i][j]
                for bj in range(cols_b):
                    row.append(bit & b[bi][bj])
            result.append(tuple(row))
    return tuple(result)


def hstack(*matrices: Matrix) -> Matrix:
    """Horizontally concatenate matrices that all share the same row count."""
    present = [m for m in matrices if m]
    if not present:
        return tuple()
    n_rows = len(present[0])
    for m in present:
        if len(m) != n_rows:
            raise ValueError(f"all matrices must have {n_rows} rows to hstack, "
                             f"got one with {len(m)}")
    return tuple(tuple(v for m in present for v in m[i]) for i in range(n_rows))


def reduce_against_rows(reduced_rows: Matrix, pivots: List[int], v: Vector) -> Vector:
    """
    Reduce `v` against an already-computed row-echelon form (as returned by
    `row_reduce`) using its pivot columns, returning the residual after
    eliminating every pivot-column component -- `v` is in that matrix's row
    space iff the residual is all-zero. Precomputing `(reduced_rows,
    pivots)` once and reusing this against many candidate vectors is much
    cheaper than calling `row_space_contains` (which recomputes rank from
    scratch) inside a large search loop, such as a brute-force distance
    search over every vector in a 2^n space.
    """
    residual = list(v)
    for row, pcol in zip(reduced_rows, pivots):
        if residual[pcol] == 1:
            residual = [a ^ b for a, b in zip(residual, row)]
    return tuple(residual)
