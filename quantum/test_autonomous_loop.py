#!/usr/bin/env python3
"""Test suite for autonomous_loop.py: the sense-decide-optimize-verify-reconfigure loop."""

import random
import unittest

import autonomous_loop as al
import code_search
import gf2


class TestRunAutonomousQECLoop(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Expensive (many rounds of brute-force distance search up to
        # n~17-18) -- computed once and shared read-only across every test
        # method below that only inspects this same report, rather than
        # each test independently re-running its own 40-round search.
        cls.weak_start_report = al.run_autonomous_qec_loop(
            [[1]], max_rounds=40, stall_rounds=15, max_qubits=14, rng=random.Random(7))

    def test_runs_and_returns_a_report(self):
        report = al.run_autonomous_qec_loop(
            [[1, 1, 0], [0, 1, 1]], max_rounds=10, stall_rounds=10, rng=random.Random(1))
        self.assertGreater(len(report.rounds), 0)
        self.assertIsNotNone(report.final_code)

    def test_final_score_never_regresses_below_initial(self):
        """The loop only ever adopts a strictly better candidate -- the
        final score can never be worse than where it started."""
        report = self.weak_start_report
        self.assertGreaterEqual(report.final_score, report.initial_score)

    def test_weak_starting_point_actually_improves(self):
        """A deliberately trivial (k=0, score-0) starting point should be
        improved on by at least one accepted round within a reasonable
        search budget -- otherwise the loop isn't doing anything."""
        report = self.weak_start_report
        self.assertTrue(report.improved)
        self.assertGreater(len(report.accepted_rounds), 0)

    def test_accepted_rounds_are_monotonically_non_decreasing_in_score(self):
        scores = [r.candidate_score for r in self.weak_start_report.accepted_rounds]
        self.assertEqual(scores, sorted(scores))

    def test_every_accepted_round_carries_a_verified_simulation_result(self):
        """Verification (the Monte Carlo re-simulation) must actually have
        run for every accepted round -- acceptance is never based on the
        [[n,k,d]] score alone."""
        for r in self.weak_start_report.accepted_rounds:
            self.assertIsNotNone(r.sensed_logical_error_rate)
            self.assertGreaterEqual(r.sensed_logical_error_rate, 0.0)

    def test_rejected_rounds_never_carry_a_simulation_result(self):
        """Verification is only worth paying for on a candidate that would
        actually be adopted -- a rejected candidate's simulation is never run."""
        report = al.run_autonomous_qec_loop(
            [[1, 1, 0], [0, 1, 1]], max_rounds=15, stall_rounds=15, rng=random.Random(3))
        for r in report.rounds:
            if not r.accepted:
                self.assertIsNone(r.sensed_logical_error_rate)

    def test_stops_after_stall_rounds_of_no_improvement(self):
        report = al.run_autonomous_qec_loop(
            [[1, 1, 0], [0, 1, 1]], max_rounds=100, stall_rounds=5, rng=random.Random(1))
        self.assertLessEqual(len(report.rounds), 100)
        if len(report.rounds) < 100:
            self.assertIn("stalled", report.stopped_reason)
            # the last `stall_rounds` rounds must all be rejections
            for r in report.rounds[-5:]:
                self.assertFalse(r.accepted)

    def test_stops_at_max_rounds_when_never_stalling_that_long(self):
        report = al.run_autonomous_qec_loop(
            [[1, 1, 0], [0, 1, 1]], max_rounds=3, stall_rounds=1000, rng=random.Random(1))
        self.assertEqual(len(report.rounds), 3)
        self.assertIn("max_rounds", report.stopped_reason)

    def test_same_seed_is_fully_reproducible(self):
        report_a = al.run_autonomous_qec_loop(
            [[1]], max_rounds=15, stall_rounds=8, max_qubits=14, rng=random.Random(2026))
        report_b = al.run_autonomous_qec_loop(
            [[1]], max_rounds=15, stall_rounds=8, max_qubits=14, rng=random.Random(2026))
        self.assertEqual(
            [(r.candidate_h, r.accepted, r.candidate_score) for r in report_a.rounds],
            [(r.candidate_h, r.accepted, r.candidate_score) for r in report_b.rounds])

    def test_invalid_initial_h_raises(self):
        with self.assertRaises(ValueError):
            al.run_autonomous_qec_loop([], max_rounds=5, rng=random.Random(0))

    def test_custom_mutation_operator_is_actually_used(self):
        """The injectable propose_mutation hook (the LLM-swap-in point)
        must genuinely be called, not silently ignored in favor of the
        default -- proven by a custom operator that always returns the
        exact same, easily-recognizable candidate."""
        calls = []
        fixed_candidate = gf2.to_matrix([[1, 1, 1], [1, 1, 0]])

        def always_same(h, rng):
            calls.append(h)
            return fixed_candidate

        report = al.run_autonomous_qec_loop(
            [[1, 1, 0], [0, 1, 1]], max_rounds=3, stall_rounds=3,
            propose_mutation=always_same, rng=random.Random(0))
        self.assertEqual(len(calls), 3)
        for r in report.rounds:
            self.assertEqual(r.candidate_h, fixed_candidate)

    def test_summary_mentions_initial_and_final_scores(self):
        report = al.run_autonomous_qec_loop(
            [[1, 1, 0], [0, 1, 1]], max_rounds=5, stall_rounds=5, rng=random.Random(1))
        text = report.summary()
        self.assertIn(f"{report.initial_score:.4f}", text)
        self.assertIn(f"{report.final_score:.4f}", text)


if __name__ == "__main__":
    unittest.main()
