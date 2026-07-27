#!/usr/bin/env python3
"""Test suite for device_graph.py: qubit-connectivity topology + noise model."""

import unittest

import device_graph as dg


class TestDeviceGraphConstruction(unittest.TestCase):
    def test_valid_graph_builds(self):
        g = dg.DeviceGraph(qubits=(0, 1, 2), edges=((0, 1), (1, 2)))
        self.assertEqual(g.qubits, (0, 1, 2))
        self.assertEqual(set(g.edges), {(0, 1), (1, 2)})

    def test_edges_are_canonicalized(self):
        g = dg.DeviceGraph(qubits=(0, 1), edges=((1, 0),))
        self.assertEqual(g.edges, ((0, 1),))

    def test_self_loop_rejected(self):
        with self.assertRaises(dg.InvalidDeviceGraphError):
            dg.DeviceGraph(qubits=(0, 1), edges=((0, 0),))

    def test_edge_to_unknown_qubit_rejected(self):
        with self.assertRaises(dg.InvalidDeviceGraphError):
            dg.DeviceGraph(qubits=(0, 1), edges=((0, 5),))

    def test_duplicate_qubit_rejected(self):
        with self.assertRaises(dg.InvalidDeviceGraphError):
            dg.DeviceGraph(qubits=(0, 0, 1), edges=())

    def test_duplicate_edge_rejected_even_when_reversed(self):
        with self.assertRaises(dg.InvalidDeviceGraphError):
            dg.DeviceGraph(qubits=(0, 1), edges=((0, 1), (1, 0)))

    def test_qubit_error_rate_referencing_unknown_qubit_rejected(self):
        with self.assertRaises(dg.InvalidDeviceGraphError):
            dg.DeviceGraph(qubits=(0, 1), edges=((0, 1),), qubit_error_rate={5: 0.1})

    def test_edge_error_rate_referencing_unknown_edge_rejected(self):
        with self.assertRaises(dg.InvalidDeviceGraphError):
            dg.DeviceGraph(qubits=(0, 1, 2), edges=((0, 1),), edge_error_rate={(1, 2): 0.1})

    def test_missing_noise_entries_default_to_zero(self):
        g = dg.DeviceGraph(qubits=(0, 1), edges=((0, 1),))
        self.assertEqual(g.qubit_noise(0), 0.0)
        self.assertEqual(g.edge_noise(0, 1), 0.0)

    def test_noise_lookup_is_order_independent(self):
        g = dg.DeviceGraph(qubits=(0, 1), edges=((0, 1),), edge_error_rate={(0, 1): 0.05})
        self.assertEqual(g.edge_noise(0, 1), 0.05)
        self.assertEqual(g.edge_noise(1, 0), 0.05)


class TestDeviceGraphQueries(unittest.TestCase):
    def setUp(self):
        # 0 - 1 - 2   3 (an isolated qubit, for disconnection tests)
        self.chain_plus_isolated = dg.DeviceGraph(
            qubits=(0, 1, 2, 3), edges=((0, 1), (1, 2)))

    def test_neighbors(self):
        self.assertEqual(set(self.chain_plus_isolated.neighbors(1)), {0, 2})
        self.assertEqual(self.chain_plus_isolated.neighbors(3), [])

    def test_neighbors_of_unknown_qubit_raises(self):
        with self.assertRaises(dg.InvalidDeviceGraphError):
            self.chain_plus_isolated.neighbors(99)

    def test_has_edge(self):
        self.assertTrue(self.chain_plus_isolated.has_edge(0, 1))
        self.assertTrue(self.chain_plus_isolated.has_edge(1, 0))
        self.assertFalse(self.chain_plus_isolated.has_edge(0, 2))

    def test_shortest_path_direct(self):
        self.assertEqual(self.chain_plus_isolated.shortest_path(0, 1), [0, 1])

    def test_shortest_path_multi_hop(self):
        self.assertEqual(self.chain_plus_isolated.shortest_path(0, 2), [0, 1, 2])

    def test_shortest_path_same_node(self):
        self.assertEqual(self.chain_plus_isolated.shortest_path(0, 0), [0])

    def test_shortest_path_disconnected_returns_none(self):
        self.assertIsNone(self.chain_plus_isolated.shortest_path(0, 3))

    def test_distance_matches_path_length(self):
        self.assertEqual(self.chain_plus_isolated.distance(0, 2), 2)
        self.assertEqual(self.chain_plus_isolated.distance(0, 0), 0)

    def test_distance_disconnected_returns_none(self):
        self.assertIsNone(self.chain_plus_isolated.distance(0, 3))

    def test_shortest_path_unknown_qubit_raises(self):
        with self.assertRaises(dg.InvalidDeviceGraphError):
            self.chain_plus_isolated.shortest_path(0, 99)

    def test_is_connected_false_when_isolated_qubit_present(self):
        self.assertFalse(self.chain_plus_isolated.is_connected())

    def test_is_connected_true_for_a_real_chain(self):
        self.assertTrue(dg.linear_chain(4).is_connected())

    def test_is_connected_true_for_empty_graph(self):
        self.assertTrue(dg.DeviceGraph(qubits=(), edges=()).is_connected())

    def test_diameter_disconnected_raises(self):
        with self.assertRaises(ValueError):
            self.chain_plus_isolated.diameter()

    def test_diameter_single_qubit_raises(self):
        with self.assertRaises(ValueError):
            dg.DeviceGraph(qubits=(0,), edges=()).diameter()


class TestLinearChain(unittest.TestCase):
    def test_topology(self):
        g = dg.linear_chain(4)
        self.assertEqual(g.qubits, (0, 1, 2, 3))
        self.assertEqual(set(g.edges), {(0, 1), (1, 2), (2, 3)})

    def test_diameter_is_n_minus_1(self):
        self.assertEqual(dg.linear_chain(5).diameter(), 4)

    def test_uniform_noise_applied(self):
        g = dg.linear_chain(3, qubit_error_rate=0.01, edge_error_rate=0.02)
        for q in g.qubits:
            self.assertEqual(g.qubit_noise(q), 0.01)
        for a, b in g.edges:
            self.assertEqual(g.edge_noise(a, b), 0.02)

    def test_rejects_non_positive_n(self):
        with self.assertRaises(ValueError):
            dg.linear_chain(0)


class TestGrid(unittest.TestCase):
    def test_topology_2x3(self):
        g = dg.grid(2, 3)
        self.assertEqual(len(g.qubits), 6)
        # interior edges: 3 horizontal per row * 2 rows-worth of pairs (2 per row) + 3 vertical
        self.assertEqual(len(g.edges), 7)  # 2*(3-1) horizontal + 3*(2-1) vertical = 4 + 3

    def test_row_major_indexing(self):
        g = dg.grid(2, 3)
        # qubit (row=1, col=2) = 1*3 + 2 = 5, adjacent to (0,2)=2 and (1,1)=4
        self.assertTrue(g.has_edge(5, 2))
        self.assertTrue(g.has_edge(5, 4))

    def test_diameter_2x3(self):
        # Manhattan distance from corner (0,0)=0 to corner (1,2)=5 is (1-0)+(2-0)=3
        self.assertEqual(dg.grid(2, 3).diameter(), 3)

    def test_single_row_grid_matches_linear_chain(self):
        g = dg.grid(1, 4)
        chain = dg.linear_chain(4)
        self.assertEqual(set(g.edges), set(chain.edges))

    def test_rejects_non_positive_dimensions(self):
        with self.assertRaises(ValueError):
            dg.grid(0, 3)
        with self.assertRaises(ValueError):
            dg.grid(3, 0)


if __name__ == "__main__":
    unittest.main()
