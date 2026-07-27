#!/usr/bin/env python3
"""
Test suite for css_codes.py, checked against well-known textbook stabilizer
codes -- not just internal consistency, but real, independently-verifiable
[[n, k, d]] parameters (the Steane code's [[7,1,3]] is a standard result
in any quantum error correction reference).
"""

import unittest

import gf2
import css_codes

# Standard [7,4,3] Hamming code parity-check matrix. The Steane code is the
# CSS code built from H_X = H_Z = this matrix (it satisfies H @ H^T = 0,
# i.e. the classical Hamming code is weakly self-dual).
HAMMING_7_4_3 = [
    [1, 0, 1, 0, 1, 0, 1],
    [0, 1, 1, 0, 0, 1, 1],
    [0, 0, 0, 1, 1, 1, 1],
]


class TestSteaneCode(unittest.TestCase):
    """The [[7, 1, 3]] Steane code -- real, independently-checkable parameters."""

    def setUp(self):
        self.code = css_codes.build_css_code(HAMMING_7_4_3, HAMMING_7_4_3)

    def test_seven_physical_one_logical_qubit(self):
        self.assertEqual(self.code.n, 7)
        self.assertEqual(self.code.k, 1)

    def test_distance_is_three(self):
        self.assertEqual(css_codes.compute_distance(self.code), 3)

    def test_parameters_string_before_distance_computed(self):
        self.assertEqual(self.code.parameters(), "[[7, 1, ?]]")

    def test_parameters_string_after_distance_computed(self):
        css_codes.compute_distance(self.code)
        self.assertEqual(self.code.parameters(), "[[7, 1, 3]]")

    def test_logical_operators_symplectically_paired(self):
        lx, lz = self.code.logical_x[0], self.code.logical_z[0]
        self.assertEqual(gf2.dot(lx, lz), 1)

    def test_logical_x_commutes_with_every_z_stabilizer(self):
        lx = self.code.logical_x[0]
        for row in self.code.h_z:
            self.assertEqual(gf2.dot(lx, row), 0)

    def test_logical_z_commutes_with_every_x_stabilizer(self):
        lz = self.code.logical_z[0]
        for row in self.code.h_x:
            self.assertEqual(gf2.dot(lz, row), 0)

    def test_logical_operator_is_not_itself_a_stabilizer(self):
        self.assertFalse(gf2.row_space_contains(self.code.h_x, self.code.logical_x[0]))

    def test_rate(self):
        self.assertAlmostEqual(self.code.rate, 1 / 7)

    def test_distance_is_cached_after_first_call(self):
        d1 = css_codes.compute_distance(self.code)
        self.assertIs(self.code.distance, d1)
        d2 = css_codes.compute_distance(self.code)  # should hit the cache, not recompute
        self.assertEqual(d1, d2)


class TestMultiLogicalQubitDuality(unittest.TestCase):
    """A hand-built n=4, k=2 code -- checks the symplectic pairing holds
    correctly ACROSS distinct logical qubits, not just the k=1 diagonal case."""

    def setUp(self):
        self.code = css_codes.build_css_code([[1, 1, 0, 0]], [[0, 0, 1, 1]])

    def test_parameters(self):
        self.assertEqual((self.code.n, self.code.k), (4, 2))

    def test_full_pairing_matrix_is_the_identity(self):
        for i, lx in enumerate(self.code.logical_x):
            for j, lz in enumerate(self.code.logical_z):
                expected = 1 if i == j else 0
                self.assertEqual(gf2.dot(lx, lz), expected,
                                 f"logical_x[{i}] . logical_z[{j}] should be {expected}")


class TestDegenerateEdgeCases(unittest.TestCase):
    def test_empty_h_z_is_a_valid_degenerate_code(self):
        code = css_codes.build_css_code([[1, 1, 0], [0, 1, 1]], [])
        self.assertEqual((code.n, code.k), (3, 1))
        self.assertEqual(len(code.logical_x), 1)
        self.assertEqual(len(code.logical_z), 1)

    def test_zero_logical_qubits_gives_empty_logical_operator_lists(self):
        code = css_codes.build_css_code([[1, 0, 0], [0, 1, 0], [0, 0, 1]], [])
        self.assertEqual(code.k, 0)
        self.assertEqual(code.logical_x, [])
        self.assertEqual(code.logical_z, [])

    def test_distance_undefined_for_zero_logical_qubits(self):
        code = css_codes.build_css_code([[1, 0, 0], [0, 1, 0], [0, 0, 1]], [])
        with self.assertRaises(ValueError):
            css_codes.compute_distance(code)


class TestInvalidConstructions(unittest.TestCase):
    def test_non_commuting_stabilizers_raise(self):
        with self.assertRaises(css_codes.InvalidCSSConstructionError):
            css_codes.build_css_code([[1, 0, 0]], [[1, 0, 0]])

    def test_mismatched_qubit_counts_raise(self):
        with self.assertRaises(css_codes.InvalidCSSConstructionError):
            css_codes.build_css_code([[1, 0, 0]], [[1, 0]])


class TestComputeDistanceBounds(unittest.TestCase):
    def test_refuses_large_codes_by_default(self):
        code = css_codes.build_css_code(HAMMING_7_4_3, HAMMING_7_4_3)
        with self.assertRaises(ValueError):
            css_codes.compute_distance(code, max_n=3)  # n=7 > max_n=3


if __name__ == "__main__":
    unittest.main()
