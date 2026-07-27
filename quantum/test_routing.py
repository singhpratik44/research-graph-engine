#!/usr/bin/env python3
"""Test suite for routing.py: SWAP-based vs. teleportation-based routing."""

import unittest

import device_graph as dg
import routing


class TestRouteSwapBased(unittest.TestCase):
    def setUp(self):
        self.chain = dg.linear_chain(5, qubit_error_rate=0.01, edge_error_rate=0.02)

    def test_adjacent_interaction_needs_no_swaps(self):
        result = routing.route_swap_based(self.chain, [(0, 1)])
        r = result.routed[0]
        self.assertEqual(r.distance, 1)
        self.assertEqual(r.primitive_operations, 1)  # just the gate itself

    def test_distant_interaction_needs_swaps_plus_gate(self):
        result = routing.route_swap_based(self.chain, [(0, 4)])
        r = result.routed[0]
        self.assertEqual(r.distance, 4)
        self.assertEqual(r.primitive_operations, 4)  # 3 swaps + 1 gate

    def test_mapping_mutates_after_routing(self):
        result = routing.route_swap_based(self.chain, [(0, 4)])
        # logical qubit 0 physically ends up adjacent to logical qubit 4's site
        self.assertEqual(result.final_mapping[4], 4)
        self.assertNotEqual(result.final_mapping[0], 0)
        self.assertEqual(self.chain.distance(result.final_mapping[0], result.final_mapping[4]), 1)

    def test_second_interaction_uses_updated_mapping(self):
        # After routing (0, 4), logical 0 has moved. A second interaction
        # (0, 1) must route from 0's *new* physical location, not its start.
        result = routing.route_swap_based(self.chain, [(0, 4), (0, 1)])
        self.assertEqual(len(result.routed), 2)
        # logical qubit 0's final physical site after the first interaction
        # is the second-to-last node on its path (it ends up adjacent to 4,
        # which stays put at path[-1]).
        moved_location = result.routed[0].physical_path[-2]
        second_interaction_start = result.routed[1].physical_path[0]
        self.assertEqual(moved_location, second_interaction_start)

    def test_estimated_error_is_zero_on_a_noiseless_device(self):
        noiseless = dg.linear_chain(4)
        result = routing.route_swap_based(noiseless, [(0, 3)])
        self.assertEqual(result.routed[0].estimated_error, 0.0)

    def test_estimated_error_positive_on_a_noisy_device(self):
        result = routing.route_swap_based(self.chain, [(0, 4)])
        self.assertGreater(result.routed[0].estimated_error, 0.0)

    def test_disconnected_device_raises(self):
        disconnected = dg.DeviceGraph(qubits=(0, 1, 2), edges=((0, 1),))
        with self.assertRaises(routing.RoutingError):
            routing.route_swap_based(disconnected, [(0, 2)])

    def test_unknown_logical_qubit_raises(self):
        with self.assertRaises(routing.RoutingError):
            routing.route_swap_based(self.chain, [(0, 99)])

    def test_custom_initial_mapping_is_respected(self):
        result = routing.route_swap_based(self.chain, [(0, 1)], initial_mapping={0: 3, 1: 4})
        self.assertEqual(result.routed[0].physical_path, [3, 4])


class TestRouteTeleportationBased(unittest.TestCase):
    def setUp(self):
        self.chain = dg.linear_chain(5, qubit_error_rate=0.01, edge_error_rate=0.02)

    def test_needs_one_entangling_op_per_edge(self):
        result = routing.route_teleportation_based(self.chain, [(0, 4)])
        r = result.routed[0]
        self.assertEqual(r.distance, 4)
        self.assertEqual(r.primitive_operations, 4)

    def test_mapping_never_mutates(self):
        mapping = {0: 0, 4: 4}
        result = routing.route_teleportation_based(self.chain, [(0, 4), (0, 4)], mapping=mapping)
        self.assertEqual(result.final_mapping, {0: 0, 4: 4})
        for r in result.routed:
            self.assertEqual(r.physical_path, [0, 1, 2, 3, 4])

    def test_ignores_qubit_error_unlike_swap_based(self):
        """Teleportation-based routing charges only edge (entangling) error,
        never per-qubit local error -- the whole point of the comparison."""
        noisy_qubits_only = dg.linear_chain(5, qubit_error_rate=0.5, edge_error_rate=0.0)
        result = routing.route_teleportation_based(noisy_qubits_only, [(0, 4)])
        self.assertEqual(result.routed[0].estimated_error, 0.0)

    def test_same_physical_qubit_raises(self):
        with self.assertRaises(routing.RoutingError):
            routing.route_teleportation_based(self.chain, [(0, 0)])

    def test_disconnected_device_raises(self):
        disconnected = dg.DeviceGraph(qubits=(0, 1, 2), edges=((0, 1),))
        with self.assertRaises(routing.RoutingError):
            routing.route_teleportation_based(disconnected, [(0, 2)])


class TestCompareRoutingStrategies(unittest.TestCase):
    def test_returns_both_strategies(self):
        chain = dg.linear_chain(5, qubit_error_rate=0.01, edge_error_rate=0.02)
        results = routing.compare_routing_strategies(chain, [(0, 4)])
        self.assertEqual(set(results.keys()), {"swap", "teleportation"})
        self.assertEqual(results["swap"].strategy, "swap")
        self.assertEqual(results["teleportation"].strategy, "teleportation")

    def test_runs_are_independent(self):
        """Routing with 'swap' must not mutate the mapping teleportation-based
        routing then also uses -- both start from the same initial_mapping."""
        chain = dg.linear_chain(5, qubit_error_rate=0.01, edge_error_rate=0.02)
        results = routing.compare_routing_strategies(chain, [(0, 4), (0, 1)])
        self.assertEqual(results["teleportation"].routed[1].physical_path, [0, 1])

    def test_swap_based_accumulates_more_error_when_qubit_noise_dominates(self):
        """With high per-qubit (not edge) noise, SWAP-based routing (which
        transits qubits) should show higher error than teleportation-based
        (which does not) for the same distant interaction."""
        chain = dg.linear_chain(5, qubit_error_rate=0.2, edge_error_rate=0.001)
        results = routing.compare_routing_strategies(chain, [(0, 4)])
        self.assertGreater(
            results["swap"].total_estimated_error,
            results["teleportation"].total_estimated_error)

    def test_summary_mentions_strategy_and_totals(self):
        chain = dg.linear_chain(3)
        result = routing.route_swap_based(chain, [(0, 2)])
        text = result.summary()
        self.assertIn("swap", text)
        self.assertIn(str(result.total_primitive_operations), text)


if __name__ == "__main__":
    unittest.main()
