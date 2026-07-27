#!/usr/bin/env python3
"""Test suite for graph_gnn.py: the from-scratch GCN forward pass."""

import math
import random
import unittest

import device_graph as dg
import graph_gnn as gnn


class TestMatrixHelpers(unittest.TestCase):
    def test_matmul_hand_verified(self):
        a = [[1.0, 2.0], [3.0, 4.0]]
        b = [[5.0, 6.0], [7.0, 8.0]]
        # [[1*5+2*7, 1*6+2*8], [3*5+4*7, 3*6+4*8]] = [[19, 22], [43, 50]]
        self.assertEqual(gnn.matmul(a, b), [[19.0, 22.0], [43.0, 50.0]])

    def test_matmul_shape_mismatch_raises(self):
        with self.assertRaises(ValueError):
            gnn.matmul([[1.0, 2.0]], [[1.0], [2.0], [3.0]])

    def test_add_bias(self):
        h = [[1.0, 2.0], [3.0, 4.0]]
        self.assertEqual(gnn.add_bias(h, [10.0, 100.0]), [[11.0, 102.0], [13.0, 104.0]])

    def test_add_bias_shape_mismatch_raises(self):
        with self.assertRaises(ValueError):
            gnn.add_bias([[1.0, 2.0]], [10.0])

    def test_relu_clips_negatives(self):
        self.assertEqual(gnn.relu([[-1.0, 0.0, 2.0]]), [[0.0, 0.0, 2.0]])

    def test_identity_activation_is_a_no_op(self):
        h = [[-1.0, 2.5]]
        self.assertEqual(gnn.identity_activation(h), h)


class TestBuildNormalizedAdjacency(unittest.TestCase):
    def test_hand_verified_three_node_path(self):
        # Path 0-1-2. A_hat degrees: deg(0)=2, deg(1)=3, deg(2)=2.
        normalized = gnn.build_normalized_adjacency(3, [(0, 1), (1, 2)])
        inv_sqrt2 = 1.0 / math.sqrt(2)
        inv_sqrt3 = 1.0 / math.sqrt(3)
        inv_sqrt6 = 1.0 / math.sqrt(6)
        self.assertAlmostEqual(normalized[0][0], inv_sqrt2 * inv_sqrt2)
        self.assertAlmostEqual(normalized[0][1], inv_sqrt6)
        self.assertAlmostEqual(normalized[0][2], 0.0)
        self.assertAlmostEqual(normalized[1][1], inv_sqrt3 * inv_sqrt3)
        self.assertAlmostEqual(normalized[1][2], inv_sqrt6)
        self.assertAlmostEqual(normalized[2][2], inv_sqrt2 * inv_sqrt2)
        # symmetric
        for i in range(3):
            for j in range(3):
                self.assertAlmostEqual(normalized[i][j], normalized[j][i])

    def test_isolated_node_has_only_self_loop_weight(self):
        # Node 2 has no edges -> A_hat degree 1 -> normalized[2][2] == 1.0
        normalized = gnn.build_normalized_adjacency(3, [(0, 1)])
        self.assertAlmostEqual(normalized[2][2], 1.0)
        self.assertAlmostEqual(normalized[2][0], 0.0)
        self.assertAlmostEqual(normalized[2][1], 0.0)

    def test_out_of_range_edge_raises(self):
        with self.assertRaises(ValueError):
            gnn.build_normalized_adjacency(2, [(0, 5)])

    def test_non_positive_n_raises(self):
        with self.assertRaises(ValueError):
            gnn.build_normalized_adjacency(0, [])


class TestDeviceGraphToNormalizedAdjacency(unittest.TestCase):
    def test_matches_manual_construction_for_a_chain(self):
        device = dg.linear_chain(3)
        normalized, order = gnn.device_graph_to_normalized_adjacency(device)
        self.assertEqual(order, [0, 1, 2])
        expected = gnn.build_normalized_adjacency(3, [(0, 1), (1, 2)])
        self.assertEqual(normalized, expected)

    def test_qubit_order_matches_sorted_non_contiguous_ids(self):
        device = dg.DeviceGraph(qubits=(5, 2, 9), edges=((2, 5), (5, 9)))
        _normalized, order = gnn.device_graph_to_normalized_adjacency(device)
        self.assertEqual(order, [2, 5, 9])


class TestGCNLayer(unittest.TestCase):
    def test_forward_with_identity_weight_recovers_row_sums(self):
        """With a 1x1 identity weight, zero bias, and the no-op activation,
        an all-ones feature vector's output at each node equals that node's
        row sum in the normalized adjacency -- a directly hand-checkable
        property of the aggregation step alone."""
        normalized = gnn.build_normalized_adjacency(3, [(0, 1), (1, 2)])
        layer = gnn.GCNLayer(weight=[[1.0]], bias=[0.0], activation=gnn.identity_activation)
        features = [[1.0], [1.0], [1.0]]
        output = layer.forward(normalized, features)
        for i in range(3):
            self.assertAlmostEqual(output[i][0], sum(normalized[i]))

    def test_forward_applies_relu_by_default(self):
        normalized = gnn.build_normalized_adjacency(2, [(0, 1)])
        # A large negative weight drives the pre-activation negative.
        layer = gnn.GCNLayer(weight=[[-10.0]], bias=[0.0])
        features = [[1.0], [1.0]]
        output = layer.forward(normalized, features)
        for row in output:
            self.assertEqual(row[0], 0.0)

    def test_in_dim_and_out_dim_properties(self):
        layer = gnn.GCNLayer(weight=[[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]], bias=[0.0, 0.0, 0.0])
        self.assertEqual(layer.in_dim, 2)
        self.assertEqual(layer.out_dim, 3)

    def test_forward_rejects_mismatched_feature_width(self):
        layer = gnn.GCNLayer(weight=[[1.0]], bias=[0.0])
        normalized = gnn.build_normalized_adjacency(2, [(0, 1)])
        with self.assertRaises(ValueError):
            layer.forward(normalized, [[1.0, 2.0], [3.0, 4.0]])


class TestRandomGCNLayer(unittest.TestCase):
    def test_shape_matches_requested_dims(self):
        layer = gnn.random_gcn_layer(3, 5, rng=random.Random(1))
        self.assertEqual(layer.in_dim, 3)
        self.assertEqual(layer.out_dim, 5)

    def test_weights_stay_within_requested_scale(self):
        layer = gnn.random_gcn_layer(4, 4, rng=random.Random(1), scale=0.2)
        for row in layer.weight:
            for value in row:
                self.assertLessEqual(abs(value), 0.2)

    def test_bias_starts_at_zero(self):
        layer = gnn.random_gcn_layer(2, 3, rng=random.Random(1))
        self.assertEqual(layer.bias, [0.0, 0.0, 0.0])

    def test_same_seed_is_reproducible(self):
        layer_a = gnn.random_gcn_layer(3, 3, rng=random.Random(99))
        layer_b = gnn.random_gcn_layer(3, 3, rng=random.Random(99))
        self.assertEqual(layer_a.weight, layer_b.weight)


class TestRunGCNForward(unittest.TestCase):
    def test_chains_layers_in_order(self):
        normalized = gnn.build_normalized_adjacency(2, [(0, 1)])
        # Layer 1: 1 -> 2 dims. Layer 2: 2 -> 1 dims. Output must be 2x1.
        layer1 = gnn.GCNLayer(weight=[[1.0, 1.0]], bias=[0.0, 0.0], activation=gnn.identity_activation)
        layer2 = gnn.GCNLayer(weight=[[1.0], [1.0]], bias=[0.0], activation=gnn.identity_activation)
        features = [[1.0], [1.0]]
        output = gnn.run_gcn_forward(normalized, features, [layer1, layer2])
        self.assertEqual(len(output), 2)
        self.assertEqual(len(output[0]), 1)

    def test_zero_layers_returns_features_unchanged(self):
        normalized = gnn.build_normalized_adjacency(2, [(0, 1)])
        features = [[1.0], [2.0]]
        output = gnn.run_gcn_forward(normalized, features, [])
        self.assertEqual(output, features)


if __name__ == "__main__":
    unittest.main()
