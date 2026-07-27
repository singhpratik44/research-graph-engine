#!/usr/bin/env python3
"""Test suite for capability_router.py: device-suitability scoring for a CSS code."""

import unittest

import capability_router as cr
import css_codes
import device_graph as dg


STEANE_H = [
    [1, 0, 0, 1, 1, 0, 1],
    [0, 1, 0, 1, 0, 1, 1],
    [0, 0, 1, 0, 1, 1, 1],
]


class TestStabilizerInteractionGraph(unittest.TestCase):
    def test_hand_verified_small_code(self):
        # H_X = [[1, 1, 0, 0]] -> stabilizer touches qubits {0, 1} -> one edge.
        # H_Z = [[0, 0, 1, 1]] -> stabilizer touches qubits {2, 3} -> one edge.
        # No column overlap between the two rows, so H_X @ H_Z^T == 0 (commute).
        code = css_codes.build_css_code([[1, 1, 0, 0]], [[0, 0, 1, 1]])
        edges = cr.stabilizer_interaction_graph(code)
        self.assertEqual(edges, [(0, 1), (2, 3)])

    def test_weight_one_stabilizer_contributes_no_edge(self):
        # A weight-1 stabilizer has no pair within its own support.
        code = css_codes.build_css_code([[1, 0, 0]], [[0, 1, 0]])
        edges = cr.stabilizer_interaction_graph(code)
        self.assertEqual(edges, [])

    def test_duplicate_pairs_across_rows_deduplicated(self):
        code = css_codes.build_css_code([[1, 1, 0]], [[1, 1, 0]])
        edges = cr.stabilizer_interaction_graph(code)
        self.assertEqual(edges, [(0, 1)])

    def test_steane_code_interaction_graph_edge_count(self):
        code = css_codes.build_css_code(STEANE_H, STEANE_H)
        edges = cr.stabilizer_interaction_graph(code)
        # 3 X-rows each weight 4 -> C(4,2)=6 edges each = 18, same 18 for Z rows,
        # deduplicated since H_X == H_Z here -> at most 18 distinct edges.
        self.assertLessEqual(len(edges), 18)
        self.assertGreater(len(edges), 0)
        for a, b in edges:
            self.assertLess(a, b)


class TestScoreDeviceForCode(unittest.TestCase):
    def setUp(self):
        self.code = css_codes.build_css_code(STEANE_H, STEANE_H)

    def test_too_few_qubits_does_not_fit(self):
        tiny = dg.linear_chain(3)
        report = cr.score_device_for_code(tiny, self.code)
        self.assertFalse(report.fits)
        self.assertEqual(report.score, float("inf"))
        self.assertIn("qubits", report.reason)

    def test_enough_qubits_fits(self):
        chain = dg.linear_chain(7, edge_error_rate=0.01)
        report = cr.score_device_for_code(chain, self.code)
        self.assertTrue(report.fits)
        self.assertIsNotNone(report.routing_result)
        self.assertGreater(report.score, 0.0)

    def test_disconnected_device_does_not_fit(self):
        disconnected = dg.DeviceGraph(qubits=tuple(range(7)), edges=((0, 1), (2, 3)))
        report = cr.score_device_for_code(disconnected, self.code)
        self.assertFalse(report.fits)

    def test_code_with_no_multiqubit_stabilizers_scores_zero(self):
        trivial_code = css_codes.build_css_code([[1, 0, 0]], [[0, 1, 0]])
        device = dg.linear_chain(3)
        report = cr.score_device_for_code(device, trivial_code)
        self.assertTrue(report.fits)
        self.assertEqual(report.score, 0.0)

    def test_custom_mapping_is_respected(self):
        chain = dg.linear_chain(7, edge_error_rate=0.01)
        identity_report = cr.score_device_for_code(chain, self.code)
        reversed_mapping = {i: 6 - i for i in range(7)}
        reversed_report = cr.score_device_for_code(chain, self.code, mapping=reversed_mapping)
        # A symmetric chain under a mirrored mapping should score identically.
        self.assertAlmostEqual(identity_report.score, reversed_report.score, places=9)

    def test_a_noisier_device_scores_worse(self):
        clean = dg.linear_chain(7, edge_error_rate=0.001)
        noisy = dg.linear_chain(7, edge_error_rate=0.1)
        clean_report = cr.score_device_for_code(clean, self.code)
        noisy_report = cr.score_device_for_code(noisy, self.code)
        self.assertGreater(noisy_report.score, clean_report.score)


class TestRecommendDevice(unittest.TestCase):
    def setUp(self):
        self.code = css_codes.build_css_code(STEANE_H, STEANE_H)

    def test_ranks_devices_best_first(self):
        devices = {
            "clean_chain": dg.linear_chain(7, edge_error_rate=0.001),
            "noisy_chain": dg.linear_chain(7, edge_error_rate=0.2),
        }
        ranked = cr.recommend_device(devices, self.code)
        self.assertEqual([name for name, _ in ranked], ["clean_chain", "noisy_chain"])

    def test_non_fitting_devices_are_still_present_with_a_reason(self):
        devices = {
            "too_small": dg.linear_chain(3),
            "big_enough": dg.linear_chain(7, edge_error_rate=0.01),
        }
        ranked = cr.recommend_device(devices, self.code)
        names = [name for name, _ in ranked]
        self.assertIn("too_small", names)
        too_small_report = dict(ranked)["too_small"]
        self.assertFalse(too_small_report.fits)
        self.assertNotEqual(too_small_report.reason, "")

    def test_best_device_returns_top_name(self):
        devices = {
            "clean_chain": dg.linear_chain(7, edge_error_rate=0.001),
            "noisy_chain": dg.linear_chain(7, edge_error_rate=0.2),
        }
        self.assertEqual(cr.best_device(devices, self.code), "clean_chain")

    def test_best_device_raises_when_none_fit(self):
        devices = {"too_small": dg.linear_chain(3)}
        with self.assertRaises(ValueError):
            cr.best_device(devices, self.code)


if __name__ == "__main__":
    unittest.main()
