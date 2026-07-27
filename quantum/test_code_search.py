#!/usr/bin/env python3
"""Test suite for code_search.py: the mutation/scoring/evaluation primitives."""

import random
import unittest

import css_codes
import code_search as cs
import gf2
import hypergraph_product as hgp

REPETITION_3 = [[1, 1, 0], [0, 1, 1]]


class TestMutateBaseCode(unittest.TestCase):
    def test_result_is_still_a_valid_binary_matrix(self):
        rng = random.Random(0)
        h = gf2.to_matrix(REPETITION_3)
        for _ in range(20):
            h = cs.mutate_base_code(h, rng)
            for row in h:
                self.assertTrue(all(bit in (0, 1) for bit in row))
            self.assertGreaterEqual(len(h), 1)
            self.assertGreaterEqual(len(h[0]), 1)

    def test_respects_row_and_column_bounds(self):
        rng = random.Random(3)
        h = gf2.to_matrix(REPETITION_3)
        for _ in range(50):
            h = cs.mutate_base_code(h, rng, min_rows=1, max_rows=3, min_cols=1, max_cols=3)
            self.assertLessEqual(len(h), 3)
            self.assertLessEqual(len(h[0]), 3)
            self.assertGreaterEqual(len(h), 1)
            self.assertGreaterEqual(len(h[0]), 1)

    def test_same_seed_is_reproducible(self):
        rng_a = random.Random(99)
        rng_b = random.Random(99)
        h = gf2.to_matrix(REPETITION_3)
        seq_a = [cs.mutate_base_code(h, rng_a)]
        seq_b = [cs.mutate_base_code(h, rng_b)]
        self.assertEqual(seq_a, seq_b)

    def test_empty_matrix_raises(self):
        with self.assertRaises(ValueError):
            cs.mutate_base_code(tuple(), random.Random(0))

    def test_single_cell_matrix_can_still_be_mutated(self):
        rng = random.Random(1)
        result = cs.mutate_base_code(gf2.to_matrix([[1]]), rng, max_rows=1, max_cols=1)
        self.assertEqual(result, ((0,),))  # only possible move is flip_bit


class TestScoreCode(unittest.TestCase):
    def test_zero_logical_qubits_scores_zero(self):
        code = hgp.hypergraph_product_code([[1]])
        self.assertEqual(code.k, 0)
        self.assertEqual(cs.score_code(code, distance=0), 0.0)

    def test_score_matches_k_times_d_over_n(self):
        code = hgp.hypergraph_product_code(REPETITION_3)
        d = css_codes.compute_distance(code)
        self.assertAlmostEqual(cs.score_code(code, d), (code.k * d) / code.n)


class TestEvaluateCandidate(unittest.TestCase):
    def test_evaluates_a_real_code(self):
        result = cs.evaluate_candidate(REPETITION_3)
        self.assertIsNotNone(result)
        code, distance, score = result
        self.assertEqual((code.n, code.k), (13, 1))
        self.assertEqual(distance, 3)
        self.assertGreater(score, 0.0)

    def test_oversized_candidate_returns_none(self):
        # A 4x5 base code -> n = 25 + 16 = 41 qubits, over the small default budget.
        big_h = [[1, 0, 0, 0, 1], [0, 1, 0, 0, 1], [0, 0, 1, 0, 1], [0, 0, 0, 1, 1]]
        self.assertIsNone(cs.evaluate_candidate(big_h, max_qubits=18))

    def test_zero_k_candidate_still_evaluates_with_zero_score(self):
        result = cs.evaluate_candidate([[1]])
        self.assertIsNotNone(result)
        code, distance, score = result
        self.assertEqual(code.k, 0)
        self.assertEqual(distance, 0)
        self.assertEqual(score, 0.0)

    def test_empty_input_returns_none_not_a_crash(self):
        self.assertIsNone(cs.evaluate_candidate([]))


if __name__ == "__main__":
    unittest.main()
