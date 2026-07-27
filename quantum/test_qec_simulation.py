#!/usr/bin/env python3
"""Test suite for qec_simulation.py."""

import random
import unittest

import css_codes
import gf2
import qec_simulation as sim

HAMMING_7_4_3 = [
    [1, 0, 1, 0, 1, 0, 1],
    [0, 1, 1, 0, 0, 1, 1],
    [0, 0, 0, 1, 1, 1, 1],
]


class TestBuildSyndromeTable(unittest.TestCase):
    def test_zero_syndrome_maps_to_the_zero_error(self):
        table = sim.build_syndrome_table(gf2.to_matrix(HAMMING_7_4_3), n=7)
        self.assertEqual(table[(0, 0, 0)], (0,) * 7)

    def test_every_recorded_error_actually_produces_its_syndrome(self):
        h = gf2.to_matrix(HAMMING_7_4_3)
        table = sim.build_syndrome_table(h, n=7)
        for syndrome, error in table.items():
            self.assertEqual(gf2.matvec(h, error), syndrome)

    def test_covers_every_reachable_syndrome_for_a_full_rank_check_matrix(self):
        h = gf2.to_matrix(HAMMING_7_4_3)
        table = sim.build_syndrome_table(h, n=7)
        self.assertEqual(len(table), 1 << gf2.rank(h))

    def test_entries_are_minimum_weight_for_low_weight_syndromes(self):
        """Every single-bit-flip error is, by definition, the unique
        minimum-weight (weight 1) coset leader for its own syndrome --
        a real check on the table, not just internal bookkeeping."""
        h = gf2.to_matrix(HAMMING_7_4_3)
        table = sim.build_syndrome_table(h, n=7)
        for bit in range(7):
            error = tuple(1 if i == bit else 0 for i in range(7))
            syndrome = gf2.matvec(h, error)
            self.assertEqual(gf2.weight(table[syndrome]), 1)


class TestSimulateLogicalErrorRate(unittest.TestCase):
    def setUp(self):
        self.code = css_codes.build_css_code(HAMMING_7_4_3, HAMMING_7_4_3)

    def test_zero_physical_error_rate_never_fails(self):
        result = sim.simulate_logical_error_rate(
            self.code, 0.0, trials=200, rng=random.Random(1))
        self.assertEqual(result.logical_failures, 0)
        self.assertEqual(result.logical_error_rate, 0.0)

    def test_same_seed_is_reproducible(self):
        a = sim.simulate_logical_error_rate(self.code, 0.1, trials=300, rng=random.Random(42))
        b = sim.simulate_logical_error_rate(self.code, 0.1, trials=300, rng=random.Random(42))
        self.assertEqual(a.logical_failures, b.logical_failures)

    def test_higher_physical_error_rate_gives_a_higher_logical_error_rate(self):
        low = sim.simulate_logical_error_rate(
            self.code, 0.02, trials=2000, rng=random.Random(7))
        high = sim.simulate_logical_error_rate(
            self.code, 0.35, trials=2000, rng=random.Random(7))
        self.assertGreater(high.logical_error_rate, low.logical_error_rate)

    def test_invalid_probability_raises(self):
        with self.assertRaises(ValueError):
            sim.simulate_logical_error_rate(self.code, 1.5, trials=10)
        with self.assertRaises(ValueError):
            sim.simulate_logical_error_rate(self.code, -0.1, trials=10)

    def test_result_fields_are_consistent(self):
        result = sim.simulate_logical_error_rate(
            self.code, 0.05, trials=500, rng=random.Random(3))
        self.assertEqual(result.trials, 500)
        self.assertAlmostEqual(result.logical_error_rate,
                               result.logical_failures / result.trials)

    def test_zero_logical_qubit_code_never_reports_a_logical_failure(self):
        """A code with k=0 has no logical qubits to corrupt -- every
        residual error, by definition, lands back in the stabilizer
        group, at any physical error rate."""
        code = css_codes.build_css_code([[1, 0, 0], [0, 1, 0], [0, 0, 1]], [])
        result = sim.simulate_logical_error_rate(code, 0.5, trials=200, rng=random.Random(9))
        self.assertEqual(result.logical_failures, 0)


if __name__ == "__main__":
    unittest.main()
