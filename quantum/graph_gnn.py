#!/usr/bin/env python3
"""
Graph intelligence layer: a real Graph Convolutional Network (GCN) forward
pass -- Kipf & Welling's symmetric-normalized message-passing rule --
implemented from scratch over pure Python floats, with zero numpy/torch
dependency, applied to this package's own `DeviceGraph`/interaction-graph
structures. This is the concrete expression of the "graph-native ML"
research pillar (the QGNN literature this package's research is informed
by) this package's GraphOps modules are built around.

Said as plainly as this package says it everywhere else something is a
simplification: this module implements the GCN layer's real forward-pass
*mathematics*, hand-verified against manually-computed small examples --
but it is architecture only. There is no training loop, no loss function,
no gradient computation, and no dataset here. Every layer's weights are
either supplied directly by the caller or drawn from a seedable RNG for
demonstration -- never learned. Calling this a trained model, or claiming
it has learned anything about quantum devices or codes, would be false;
it is offered honestly as the one piece of this pillar that is real and
checkable without a training pipeline this package doesn't have.

The GCN propagation rule for one layer, given adjacency matrix A (n x n),
self-loop-augmented A_hat = A + I, degree matrix D (diagonal, from A_hat),
node feature matrix H (n x in_dim), weight matrix W (in_dim x out_dim),
and bias b (out_dim):

    H' = activation( D^(-1/2) @ A_hat @ D^(-1/2) @ H @ W + b )

`build_normalized_adjacency` computes D^(-1/2) @ A_hat @ D^(-1/2) once
(from `device_graph.DeviceGraph` or a plain edge list); `GCNLayer.forward`
applies the linear transform, bias, and activation on top of it.
"""

import math
import random
from dataclasses import dataclass, field
from typing import Callable, List, Optional, Sequence, Tuple

from device_graph import DeviceGraph

Matrix = List[List[float]]


def zeros(rows: int, cols: int) -> Matrix:
    return [[0.0 for _ in range(cols)] for _ in range(rows)]


def matmul(a: Matrix, b: Matrix) -> Matrix:
    if not a or not b:
        return []
    if len(a[0]) != len(b):
        raise ValueError(f"shape mismatch: {len(a)}x{len(a[0])} @ {len(b)}x{len(b[0]) if b else 0}")
    rows_a, cols_a, cols_b = len(a), len(a[0]), len(b[0])
    result = zeros(rows_a, cols_b)
    for i in range(rows_a):
        for k in range(cols_a):
            aik = a[i][k]
            if aik == 0.0:
                continue
            row_b = b[k]
            row_result = result[i]
            for j in range(cols_b):
                row_result[j] += aik * row_b[j]
    return result


def add_bias(h: Matrix, bias: Sequence[float]) -> Matrix:
    if h and len(h[0]) != len(bias):
        raise ValueError(f"shape mismatch: {len(h[0])} columns vs. {len(bias)} bias entries")
    return [[value + bias[j] for j, value in enumerate(row)] for row in h]


def relu(h: Matrix) -> Matrix:
    return [[max(0.0, value) for value in row] for row in h]


def identity_activation(h: Matrix) -> Matrix:
    """The no-op activation -- useful for tests that want to check the
    linear part of a layer in isolation from any nonlinearity."""
    return [[value for value in row] for row in h]


def _qubit_index_order(device: DeviceGraph) -> List[int]:
    """A stable, deterministic node ordering for a DeviceGraph's (possibly
    arbitrary, non-contiguous) qubit ids -- sorted ascending."""
    return sorted(device.qubits)


def build_normalized_adjacency(
    n: int,
    edges: Sequence[Tuple[int, int]],
) -> Matrix:
    """
    D^(-1/2) @ A_hat @ D^(-1/2), where A_hat = A + I (self-loops added) and
    D is A_hat's diagonal degree matrix -- the standard GCN normalization,
    computed directly from an edge list over node indices `0..n-1`. Use
    `device_graph_to_normalized_adjacency` to build this from a
    `DeviceGraph` whose qubit ids may not already be a contiguous `0..n-1`
    range.
    """
    if n <= 0:
        raise ValueError("n must be positive")
    a_hat = zeros(n, n)
    for i in range(n):
        a_hat[i][i] = 1.0
    for u, v in edges:
        if not (0 <= u < n) or not (0 <= v < n):
            raise ValueError(f"edge ({u}, {v}) out of range for n={n} nodes")
        a_hat[u][v] = 1.0
        a_hat[v][u] = 1.0

    degree = [sum(row) for row in a_hat]
    d_inv_sqrt = [1.0 / math.sqrt(d) if d > 0 else 0.0 for d in degree]

    normalized = zeros(n, n)
    for i in range(n):
        for j in range(n):
            if a_hat[i][j] != 0.0:
                normalized[i][j] = d_inv_sqrt[i] * a_hat[i][j] * d_inv_sqrt[j]
    return normalized


def device_graph_to_normalized_adjacency(device: DeviceGraph) -> Tuple[Matrix, List[int]]:
    """
    Build the normalized adjacency for `device`'s connectivity graph.
    Returns `(normalized_adjacency, qubit_order)` where `qubit_order[i]` is
    the original device qubit id that row/column `i` of the matrix
    corresponds to (device qubit ids need not be a contiguous `0..n-1`
    range, so this mapping is necessary to interpret the output).
    """
    qubit_order = _qubit_index_order(device)
    index_of = {q: i for i, q in enumerate(qubit_order)}
    edges = [(index_of[a], index_of[b]) for a, b in device.edges]
    normalized = build_normalized_adjacency(len(qubit_order), edges)
    return normalized, qubit_order


@dataclass
class GCNLayer:
    """
    One GCN layer: `forward(normalized_adjacency, node_features)` computes
    `activation(normalized_adjacency @ node_features @ weight + bias)`.
    `weight` is `in_dim x out_dim`, `bias` has `out_dim` entries. Construct
    directly with hand-chosen weights for a fully deterministic, hand-
    verifiable test, or via `random_gcn_layer` for an untrained
    demonstration layer.
    """
    weight: Matrix
    bias: List[float]
    activation: Callable[[Matrix], Matrix] = field(default=relu)

    @property
    def in_dim(self) -> int:
        return len(self.weight)

    @property
    def out_dim(self) -> int:
        return len(self.bias)

    def forward(self, normalized_adjacency: Matrix, node_features: Matrix) -> Matrix:
        if node_features and len(node_features[0]) != self.in_dim:
            raise ValueError(
                f"node_features has {len(node_features[0])} feature columns, "
                f"layer expects in_dim={self.in_dim}")
        aggregated = matmul(normalized_adjacency, node_features)
        transformed = matmul(aggregated, self.weight)
        biased = add_bias(transformed, self.bias)
        return self.activation(biased)


def random_gcn_layer(
    in_dim: int,
    out_dim: int,
    rng: Optional[random.Random] = None,
    scale: float = 0.1,
    activation: Callable[[Matrix], Matrix] = relu,
) -> GCNLayer:
    """
    A `GCNLayer` with weights drawn uniformly from `[-scale, scale]` and a
    zero bias -- explicitly *not* a trained layer, just a seedable way to
    get a demonstration-shaped weight matrix without hand-writing one.
    """
    rng = rng if rng is not None else random.Random()
    weight = [[rng.uniform(-scale, scale) for _ in range(out_dim)] for _ in range(in_dim)]
    bias = [0.0] * out_dim
    return GCNLayer(weight=weight, bias=bias, activation=activation)


def run_gcn_forward(
    normalized_adjacency: Matrix,
    node_features: Matrix,
    layers: Sequence[GCNLayer],
) -> Matrix:
    """Chain multiple GCN layers, each layer's output feeding the next
    layer's input -- the same `normalized_adjacency` (the graph's fixed
    topology) is reused at every layer, only the node features change."""
    h = node_features
    for layer in layers:
        h = layer.forward(normalized_adjacency, h)
    return h


if __name__ == "__main__":
    import device_graph

    demo_device = device_graph.linear_chain(3)
    normalized, order = device_graph_to_normalized_adjacency(demo_device)
    print(f"qubit order: {order}")
    for row in normalized:
        print(["%.4f" % v for v in row])

    demo_layer = random_gcn_layer(in_dim=2, out_dim=4, rng=random.Random(2026))
    demo_features = [[1.0, 0.0], [0.0, 1.0], [1.0, 1.0]]
    output = run_gcn_forward(normalized, demo_features, [demo_layer])
    print("layer output (untrained, random weights):")
    for row in output:
        print(["%.4f" % v for v in row])
