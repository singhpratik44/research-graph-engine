#!/usr/bin/env python3
"""
Test suite for hypergraph_product.py, checked against a known result:
the hypergraph product of the length-3 classical repetition code with
itself produces the standard small surface-code-like [[13, 1, 3]] quantum
code -- a real, independently-checkable result from the QEC literature,
not just internal self-consistency.
"""

import unittest

import css_codes
import gf2
import hypergraph_product as hgp

REPETITION_3 = [[1, 1, 0], [0, 1, 1]]  # length-3 repetition code, m=2 checks, n_c=3 bits


class TestHypergraphProductOfRepetitionCode(unittest.TestCase):
    def setUp(self):
        self.code = hgp.hypergraph_product_code(REPETITION_3)

    def test_thirteen_physical_one_logical_qubit(self):
        self.assertEqual((self.code.n, self.code.k), (13, 1))

    def test_distance_is_three(self):
        self.assertEqual(css_codes.compute_distance(self.code), 3)

    def test_stabilizers_commute(self):
        commutator = gf2.matmul(self.code.h_x, gf2.transpose(self.code.h_z))
        for row in commutator:
            self.assertTrue(all(bit == 0 for bit in row))

    def test_check_matrix_shapes_match_the_qubit_count(self):
        self.assertTrue(all(len(row) == self.code.n for row in self.code.h_x))
        self.assertTrue(all(len(row) == self.code.n for row in self.code.h_z))


class TestPhysicalQubitCount(unittest.TestCase):
    def test_matches_the_n_squared_plus_m_squared_formula(self):
        self.assertEqual(hgp.physical_qubit_count(2, 3), 13)
        self.assertEqual(hgp.physical_qubit_count(1, 1), 2)
        self.assertEqual(hgp.physical_qubit_count(3, 5), 34)

    def test_matches_an_actually_constructed_codes_n(self):
        code = hgp.hypergraph_product_code(REPETITION_3)
        self.assertEqual(hgp.physical_qubit_count(2, 3), code.n)


class TestTinyBaseCode(unittest.TestCase):
    def test_single_bit_single_check_code(self):
        code = hgp.hypergraph_product_code([[1]])
        self.assertEqual(code.n, 2)
        # A single classical bit with a single (trivial) check encodes no
        # protected logical qubit -- there's nothing redundant to protect.
        self.assertEqual(code.k, 0)


class TestInvalidBaseCode(unittest.TestCase):
    def test_empty_matrix_raises(self):
        with self.assertRaises(ValueError):
            hgp.hypergraph_product_code([])

    def test_empty_rows_raise(self):
        with self.assertRaises(ValueError):
            hgp.hypergraph_product_code([[]])


if __name__ == "__main__":
    unittest.main()
