#!/usr/bin/env python3
"""
DeviceGraph: a quantum device's qubit-connectivity topology represented as
an actual graph -- the foundation every other GraphOps module in this
package builds on. This is the concrete expression of this package's
"strongest build thesis": represent the quantum operation stack as a
graph, then let other layers (routing, capability scoring, the agentic
workflow engine) optimize over that graph, rather than each layer
re-deriving its own private notion of "which qubits are near which."

A DeviceGraph is deliberately simple and real, not a toy: qubits are
nodes, native two-qubit couplings are edges, and both carry per-component
error rates (an honest, if simplified, stand-in for a real device's
calibration data -- no real hardware is reachable from this sandbox, so
these rates are supplied by the caller or a constructor, never measured).
`routing.py` uses shortest paths over this graph to route non-adjacent
two-qubit interactions; `capability_router.py` uses its shape and noise
profile to score how well a device suits a given code's own interaction
graph.

Two canonical constructors are provided (`linear_chain`, `grid`) because
they are the two device topologies most real superconducting-qubit
hardware actually ships as (a 1-D chain, or a 2-D nearest-neighbor grid,
per the connectivity constraints surveyed in the routing-on-graphs
literature this package's GraphOps modules are informed by) -- not
because this module claims to model any specific real chip.
"""

from collections import deque
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


class InvalidDeviceGraphError(ValueError):
    """Edges reference qubits that don't exist, or are otherwise malformed."""


Edge = Tuple[int, int]


def _canonical_edge(a: int, b: int) -> Edge:
    """Undirected edges are keyed by their sorted endpoints throughout this
    module, so (a, b) and (b, a) are always the same dictionary key."""
    return (a, b) if a <= b else (b, a)


@dataclass
class DeviceGraph:
    """
    A quantum device's connectivity graph. Construct via `DeviceGraph(...)`
    directly for a custom topology, or via `linear_chain`/`grid` for the
    two canonical topologies this module ships. `qubit_error_rate` and
    `edge_error_rate` default missing entries to 0.0 (noiseless) rather
    than raising -- a caller modeling only some components' noise doesn't
    have to fill in every qubit and edge.
    """
    qubits: Tuple[int, ...]
    edges: Tuple[Edge, ...]
    qubit_error_rate: Dict[int, float] = field(default_factory=dict)
    edge_error_rate: Dict[Edge, float] = field(default_factory=dict)
    _adjacency: Dict[int, List[int]] = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        qubit_set = set(self.qubits)
        if len(qubit_set) != len(self.qubits):
            raise InvalidDeviceGraphError("duplicate qubit ids")
        canonical_edges = []
        seen_edges = set()
        for a, b in self.edges:
            if a == b:
                raise InvalidDeviceGraphError(f"self-loop edge ({a}, {b}) is not allowed")
            if a not in qubit_set or b not in qubit_set:
                raise InvalidDeviceGraphError(
                    f"edge ({a}, {b}) references a qubit not in {self.qubits}")
            edge = _canonical_edge(a, b)
            if edge in seen_edges:
                raise InvalidDeviceGraphError(f"duplicate edge {edge}")
            seen_edges.add(edge)
            canonical_edges.append(edge)
        self.edges = tuple(canonical_edges)

        for q in self.qubit_error_rate:
            if q not in qubit_set:
                raise InvalidDeviceGraphError(
                    f"qubit_error_rate references qubit {q} not in {self.qubits}")
        for e in self.edge_error_rate:
            if _canonical_edge(*e) not in seen_edges:
                raise InvalidDeviceGraphError(
                    f"edge_error_rate references edge {e} not in this graph's edges")

        adjacency: Dict[int, List[int]] = {q: [] for q in self.qubits}
        for a, b in self.edges:
            adjacency[a].append(b)
            adjacency[b].append(a)
        self._adjacency = adjacency

    def neighbors(self, qubit: int) -> List[int]:
        if qubit not in self._adjacency:
            raise InvalidDeviceGraphError(f"qubit {qubit} is not in this graph")
        return list(self._adjacency[qubit])

    def qubit_noise(self, qubit: int) -> float:
        return self.qubit_error_rate.get(qubit, 0.0)

    def edge_noise(self, a: int, b: int) -> float:
        return self.edge_error_rate.get(_canonical_edge(a, b), 0.0)

    def has_edge(self, a: int, b: int) -> bool:
        return _canonical_edge(a, b) in set(self.edges)

    def shortest_path(self, start: int, end: int) -> Optional[List[int]]:
        """
        BFS shortest path (by hop count, not weighted by noise -- routing.py
        is where noise-aware path choice belongs) from `start` to `end`,
        inclusive of both endpoints. Returns `None` if no path exists
        (the two qubits are in different connected components) rather than
        raising -- a disconnected device is a valid, if degenerate, graph.
        """
        if start not in self._adjacency or end not in self._adjacency:
            raise InvalidDeviceGraphError(
                f"both {start} and {end} must be qubits in this graph")
        if start == end:
            return [start]
        visited = {start}
        parent: Dict[int, int] = {}
        queue = deque([start])
        while queue:
            current = queue.popleft()
            for neighbor in self._adjacency[current]:
                if neighbor in visited:
                    continue
                visited.add(neighbor)
                parent[neighbor] = current
                if neighbor == end:
                    path = [end]
                    while path[-1] != start:
                        path.append(parent[path[-1]])
                    return list(reversed(path))
                queue.append(neighbor)
        return None

    def distance(self, start: int, end: int) -> Optional[int]:
        """Hop count of the shortest path, or `None` if disconnected."""
        path = self.shortest_path(start, end)
        return None if path is None else len(path) - 1

    def is_connected(self) -> bool:
        if not self.qubits:
            return True
        start = self.qubits[0]
        visited = {start}
        queue = deque([start])
        while queue:
            current = queue.popleft()
            for neighbor in self._adjacency[current]:
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)
        return len(visited) == len(self.qubits)

    def diameter(self) -> int:
        """
        The graph diameter: the longest shortest path between any pair of
        qubits. Raises if the graph is disconnected (undefined -- some
        pair has no finite distance) or empty (no pairs to measure).
        """
        if len(self.qubits) < 2:
            raise ValueError("diameter is undefined for fewer than 2 qubits")
        if not self.is_connected():
            raise ValueError("diameter is undefined for a disconnected graph")
        best = 0
        for i, a in enumerate(self.qubits):
            for b in self.qubits[i + 1:]:
                d = self.distance(a, b)
                assert d is not None  # connected, so every pair has a finite distance
                best = max(best, d)
        return best


def linear_chain(
    n: int,
    qubit_error_rate: float = 0.0,
    edge_error_rate: float = 0.0,
) -> DeviceGraph:
    """A 1-D nearest-neighbor chain of `n` qubits (0 -- 1 -- 2 -- ... -- n-1),
    the connectivity many trapped-ion and some superconducting devices ship
    as. Uniform per-qubit and per-edge error rates for simplicity."""
    if n < 1:
        raise ValueError("n must be at least 1")
    qubits = tuple(range(n))
    edges = tuple((i, i + 1) for i in range(n - 1))
    return DeviceGraph(
        qubits=qubits, edges=edges,
        qubit_error_rate={q: qubit_error_rate for q in qubits},
        edge_error_rate={e: edge_error_rate for e in edges},
    )


def grid(
    rows: int,
    cols: int,
    qubit_error_rate: float = 0.0,
    edge_error_rate: float = 0.0,
) -> DeviceGraph:
    """A 2-D nearest-neighbor grid of `rows * cols` qubits, indexed
    row-major (qubit id = row * cols + col) -- the connectivity most
    real superconducting-qubit devices ship as. Uniform per-qubit and
    per-edge error rates for simplicity."""
    if rows < 1 or cols < 1:
        raise ValueError("rows and cols must each be at least 1")

    def qid(r: int, c: int) -> int:
        return r * cols + c

    qubits = tuple(range(rows * cols))
    edges: List[Edge] = []
    for r in range(rows):
        for c in range(cols):
            if c + 1 < cols:
                edges.append(_canonical_edge(qid(r, c), qid(r, c + 1)))
            if r + 1 < rows:
                edges.append(_canonical_edge(qid(r, c), qid(r + 1, c)))
    return DeviceGraph(
        qubits=qubits, edges=tuple(edges),
        qubit_error_rate={q: qubit_error_rate for q in qubits},
        edge_error_rate={e: edge_error_rate for e in edges},
    )


if __name__ == "__main__":
    device = grid(2, 3, qubit_error_rate=0.001, edge_error_rate=0.01)
    print(f"grid(2, 3): {len(device.qubits)} qubits, {len(device.edges)} edges, "
          f"diameter={device.diameter()}")
    print(f"shortest path 0 -> 5: {device.shortest_path(0, 5)}")
