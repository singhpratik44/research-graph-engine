#!/usr/bin/env python3
"""Test suite for gf2.py: GF(2) linear algebra primitives."""

import unittest

import gf2


class TestRank(unittest.TestCase):
    def test_identity_has_full_rank(self):
        m = gf2.to_matrix([[1, 0, 0], [0, 1, 0], [0, 0, 1]])
        self.assertEqual(gf2.rank(m), 3)

    def test_repetition_parity_check_rank_two(self):
        m = gf2.to_matrix([[1, 1, 0], [0, 1, 1]])
        self.assertEqual(gf2.rank(m), 2)

    def test_dependent_row_does_not_add_rank(self):
        m = gf2.to_matrix([[1, 1, 0, 0], [0, 1, 1, 0], [1, 0, 1, 0]])  # row3 = row1 xor row2
        self.assertEqual(gf2.rank(m), 2)

    def test_zero_matrix_has_zero_rank(self):
        self.assertEqual(gf2.rank(gf2.zeros(3, 4)), 0)


class TestNullspace(unittest.TestCase):
    def test_repetition_code_nullspace_is_all_ones(self):
        h = gf2.to_matrix([[1, 1, 0], [0, 1, 1]])
        ns = gf2.nullspace(h)
        self.assertEqual(len(ns), 1)
        self.assertEqual(ns[0], (1, 1, 1))
        for v in ns:
            self.assertTrue(gf2.is_zero_vector(gf2.matvec(h, v)))

    def test_identity_nullspace_is_empty(self):
        m = gf2.to_matrix([[1, 0, 0], [0, 1, 0], [0, 0, 1]])
        self.assertEqual(gf2.nullspace(m), [])

    def test_nullspace_dimension_matches_rank_nullity_theorem(self):
        m = gf2.to_matrix([[1, 1, 0, 0], [0, 1, 1, 0], [1, 0, 1, 0]])
        n_cols = 4
        self.assertEqual(len(gf2.nullspace(m)) + gf2.rank(m), n_cols)

    def test_every_basis_vector_is_actually_in_the_kernel(self):
        m = gf2.to_matrix([[1, 0, 1, 1], [0, 1, 1, 0]])
        for v in gf2.nullspace(m):
            self.assertTrue(gf2.is_zero_vector(gf2.matvec(m, v)))

    def test_zero_matrix_nullspace_is_the_whole_space(self):
        m = gf2.zeros(2, 3)
        ns = gf2.nullspace(m)
        self.assertEqual(len(ns), 3)


class TestVectorOps(unittest.TestCase):
    def test_add_is_xor(self):
        self.assertEqual(gf2.add((1, 1, 0), (0, 1, 1)), (1, 0, 1))

    def test_add_length_mismatch_raises(self):
        with self.assertRaises(ValueError):
            gf2.add((1, 0), (1, 0, 0))

    def test_dot_is_parity_of_and(self):
        self.assertEqual(gf2.dot((1, 1, 1), (1, 0, 1)), 0)  # 1+0+1 = 2 mod 2 = 0
        self.assertEqual(gf2.dot((1, 1, 0), (1, 0, 0)), 1)

    def test_weight_counts_nonzero_entries(self):
        self.assertEqual(gf2.weight((1, 0, 1, 1, 0)), 3)
        self.assertEqual(gf2.weight((0, 0, 0)), 0)


class TestMatrixOps(unittest.TestCase):
    def test_matmul_matches_hand_computation(self):
        a = gf2.to_matrix([[1, 1], [0, 1]])
        b = gf2.to_matrix([[1, 0], [1, 1]])
        # a @ b = [[1^1, 0^1], [1, 1]] = [[0, 1], [1, 1]]
        self.assertEqual(gf2.matmul(a, b), ((0, 1), (1, 1)))

    def test_transpose_swaps_rows_and_columns(self):
        m = gf2.to_matrix([[1, 0, 1], [0, 1, 1]])
        self.assertEqual(gf2.transpose(m), ((1, 0), (0, 1), (1, 1)))

    def test_matvec_shape_mismatch_raises(self):
        m = gf2.to_matrix([[1, 0, 1]])
        with self.assertRaises(ValueError):
            gf2.matvec(m, (1, 0))


class TestIdentity(unittest.TestCase):
    def test_identity_three(self):
        self.assertEqual(gf2.identity(3), ((1, 0, 0), (0, 1, 0), (0, 0, 1)))

    def test_identity_matmul_is_a_no_op(self):
        m = gf2.to_matrix([[1, 1, 0], [0, 1, 1]])
        self.assertEqual(gf2.matmul(m, gf2.identity(3)), m)


class TestKron(unittest.TestCase):
    def test_two_by_two_kron_identity(self):
        a = gf2.to_matrix([[1, 0], [1, 1]])
        result = gf2.kron(a, gf2.identity(2))
        # a (x) I_2 should place a copy of I_2 wherever a has a 1, zeros elsewhere
        expected = gf2.to_matrix([
            [1, 0, 0, 0],
            [0, 1, 0, 0],
            [1, 0, 1, 0],
            [0, 1, 0, 1],
        ])
        self.assertEqual(result, expected)

    def test_kron_shape(self):
        a = gf2.to_matrix([[1, 0, 1], [0, 1, 1]])  # 2x3
        b = gf2.identity(4)  # 4x4
        result = gf2.kron(a, b)
        self.assertEqual(len(result), 2 * 4)
        self.assertEqual(len(result[0]), 3 * 4)

    def test_kron_with_empty_matrix_is_empty(self):
        self.assertEqual(gf2.kron(tuple(), gf2.identity(2)), tuple())


class TestHstack(unittest.TestCase):
    def test_concatenates_columns(self):
        a = gf2.to_matrix([[1, 0], [0, 1]])
        b = gf2.to_matrix([[1, 1], [0, 0]])
        self.assertEqual(gf2.hstack(a, b), ((1, 0, 1, 1), (0, 1, 0, 0)))

    def test_mismatched_row_counts_raise(self):
        a = gf2.to_matrix([[1, 0]])
        b = gf2.to_matrix([[1, 0], [0, 1]])
        with self.assertRaises(ValueError):
            gf2.hstack(a, b)

    def test_empty_matrices_are_skipped(self):
        a = gf2.to_matrix([[1, 0], [0, 1]])
        self.assertEqual(gf2.hstack(a, tuple()), a)


class TestReduceAgainstRows(unittest.TestCase):
    def test_matches_row_space_contains(self):
        m = gf2.to_matrix([[1, 1, 0], [0, 1, 1]])
        reduced, pivots = gf2.row_reduce(m)
        for v in [(1, 1, 0), (1, 0, 1), (1, 0, 0), (0, 0, 0)]:
            residual = gf2.reduce_against_rows(reduced, pivots, v)
            self.assertEqual(gf2.is_zero_vector(residual), gf2.row_space_contains(m, v))


class TestSolve(unittest.TestCase):
    def test_finds_a_valid_solution(self):
        a = gf2.to_matrix([[1, 1, 0], [0, 1, 1]])
        c = gf2.solve(a, (1, 0))
        self.assertIsNotNone(c)
        self.assertEqual(gf2.matvec(a, c), (1, 0))

    def test_inconsistent_system_returns_none(self):
        a = gf2.to_matrix([[1, 0], [1, 0]])
        self.assertIsNone(gf2.solve(a, (0, 1)))

    def test_consistent_system_with_dependent_rows_solves(self):
        a = gf2.to_matrix([[1, 0], [1, 0]])
        c = gf2.solve(a, (1, 1))
        self.assertIsNotNone(c)
        self.assertEqual(gf2.matvec(a, c), (1, 1))

    def test_empty_matrix_with_zero_target_solves_trivially(self):
        self.assertEqual(gf2.solve(tuple(), tuple()), tuple())


class TestRowSpaceContains(unittest.TestCase):
    def test_row_itself_is_contained(self):
        m = gf2.to_matrix([[1, 1, 0], [0, 1, 1]])
        self.assertTrue(gf2.row_space_contains(m, (1, 1, 0)))

    def test_combination_of_rows_is_contained(self):
        m = gf2.to_matrix([[1, 1, 0], [0, 1, 1]])
        self.assertTrue(gf2.row_space_contains(m, (1, 0, 1)))  # row0 xor row1

    def test_independent_vector_is_not_contained(self):
        m = gf2.to_matrix([[1, 1, 0], [0, 1, 1]])
        self.assertFalse(gf2.row_space_contains(m, (1, 0, 0)))

    def test_zero_vector_is_contained_in_empty_matrix(self):
        self.assertTrue(gf2.row_space_contains(tuple(), (0, 0, 0)))


if __name__ == "__main__":
    unittest.main()
