#!/usr/bin/env python3
"""
Two directly-comparable routing strategies over a `DeviceGraph`: SWAP-based
routing (the incumbent, textbook approach -- physically relocate a qubit's
state, hop by hop, until it is adjacent to its interaction partner) versus
teleportation-based routing (build a long-range entangled link across the
same path via entanglement swapping, then execute the gate remotely without
moving the data qubit at all). This module exists to make that comparison
concrete and runnable, not just cite it -- directly matching this package's
own "compare quantum-teleportation routing vs. classical SWAP-based methods
on interaction graph complexity" follow-up.

Both strategies operate over the *same* input: a `DeviceGraph` and an
ordered list of two-qubit interactions (pairs of *logical* qubit ids that
need a gate applied between them, in the order the circuit requires it).
Both produce a `RoutingResult` with the same shape, so a caller can compare
total primitive-operation counts and combined estimated error side by side.

This is a simplified cost model, said plainly, not a full physical-layer
simulation -- there is no real hardware or real entanglement-swapping
protocol running underneath. What *is* real and load-bearing is the
structural distinction the routing-on-graphs and quantum-networking
literature actually draws between the two strategies:

  - SWAP-based routing physically relocates the data qubit's own quantum
    state through every intermediate qubit on the path. Each hop's SWAP
    exposes that state to both the *edge*'s two-qubit gate error and the
    *qubit*'s own local error at each site it passes through -- the data
    qubit's coherence is on the line for the entire transit.
  - Teleportation-based routing instead consumes one entangled pair per
    edge along the path (built via entanglement swapping at each
    intermediate node) and executes the gate through that resource without
    ever physically moving the data qubit. Its cost is dominated by edge
    (entangling-link) error alone -- the data qubit's own local error is
    not incurred by the routing step itself, and its physical location
    (and thus the caller's logical-to-physical mapping) never changes.

That second property -- teleportation-based routing leaves the mapping
untouched -- is the concrete, checkable difference this module's tests
verify, alongside the operation-count and error-accumulation trade-off.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from device_graph import DeviceGraph


class RoutingError(ValueError):
    """An interaction could not be routed (e.g. disconnected qubits, or a
    logical qubit not present in the mapping)."""


@dataclass
class RoutedInteraction:
    """The outcome of routing one logical (a, b) interaction."""
    logical_pair: Tuple[int, int]
    physical_path: List[int]
    distance: int
    primitive_operations: int
    estimated_error: float  # combined failure probability for this one interaction


@dataclass
class RoutingResult:
    strategy: str  # "swap" or "teleportation"
    routed: List[RoutedInteraction]
    final_mapping: Dict[int, int]

    @property
    def total_primitive_operations(self) -> int:
        return sum(r.primitive_operations for r in self.routed)

    @property
    def total_estimated_error(self) -> float:
        """Combined failure probability across every interaction: 1 minus
        the product of each interaction's success probability."""
        success = 1.0
        for r in self.routed:
            success *= (1.0 - r.estimated_error)
        return 1.0 - success

    def summary(self) -> str:
        lines = [
            f"strategy={self.strategy}  interactions={len(self.routed)}  "
            f"total_ops={self.total_primitive_operations}  "
            f"total_estimated_error={self.total_estimated_error:.6f}",
        ]
        for r in self.routed:
            lines.append(
                f"  {r.logical_pair}: distance={r.distance} ops={r.primitive_operations} "
                f"path={r.physical_path} error={r.estimated_error:.6f}")
        return "\n".join(lines)


def _identity_mapping(device: DeviceGraph) -> Dict[int, int]:
    return {q: q for q in device.qubits}


def _resolve_path(device: DeviceGraph, pa: int, pb: int) -> List[int]:
    path = device.shortest_path(pa, pb)
    if path is None:
        raise RoutingError(f"no path between physical qubits {pa} and {pb} -- device is disconnected")
    return path


def route_swap_based(
    device: DeviceGraph,
    interactions: List[Tuple[int, int]],
    initial_mapping: Optional[Dict[int, int]] = None,
) -> RoutingResult:
    """
    Route every interaction by physically walking the first qubit of the
    pair along the shortest path toward the second, one SWAP per hop, until
    they are adjacent, then applying the two-qubit gate on that edge. The
    mapping mutates as interactions are processed -- a qubit relocated to
    satisfy one interaction stays at its new physical site for the next.
    `initial_mapping` defaults to the identity (logical qubit i starts at
    physical qubit i); pass one explicitly to start from a non-trivial
    initial placement.
    """
    mapping = dict(initial_mapping) if initial_mapping is not None else _identity_mapping(device)
    routed: List[RoutedInteraction] = []

    for logical_a, logical_b in interactions:
        if logical_a not in mapping or logical_b not in mapping:
            raise RoutingError(f"logical qubits {logical_a}, {logical_b} must both be in the mapping")
        pa, pb = mapping[logical_a], mapping[logical_b]
        path = _resolve_path(device, pa, pb)
        distance = len(path) - 1

        success = 1.0
        ops = 0
        current = pa
        for i in range(distance - 1):
            nxt = path[i + 1]
            # A SWAP moves the data qubit's state through both endpoints --
            # both sites' own local error, plus the edge's gate error, apply.
            success *= (1.0 - device.edge_noise(current, nxt))
            success *= (1.0 - device.qubit_noise(current))
            success *= (1.0 - device.qubit_noise(nxt))
            mapping[logical_a] = nxt
            current = nxt
            ops += 1

        final_pa, final_pb = mapping[logical_a], mapping[logical_b]
        success *= (1.0 - device.edge_noise(final_pa, final_pb))
        ops += 1  # the final two-qubit gate itself

        routed.append(RoutedInteraction(
            logical_pair=(logical_a, logical_b), physical_path=path,
            distance=distance, primitive_operations=ops, estimated_error=1.0 - success,
        ))

    return RoutingResult(strategy="swap", routed=routed, final_mapping=mapping)


def route_teleportation_based(
    device: DeviceGraph,
    interactions: List[Tuple[int, int]],
    mapping: Optional[Dict[int, int]] = None,
) -> RoutingResult:
    """
    Route every interaction via entanglement-swapping-based teleportation:
    build one entangled pair per edge along the shortest path (the entangling
    operations are the only source of error this model charges -- the data
    qubit's own local error is never incurred, since it is never physically
    moved), then execute the gate through that resource. `mapping` is never
    mutated by this function and is returned unchanged as `final_mapping` --
    the central, checkable claim of teleportation-based routing is that a
    qubit's physical location is untouched by the routing step itself.
    """
    mapping = dict(mapping) if mapping is not None else _identity_mapping(device)
    routed: List[RoutedInteraction] = []

    for logical_a, logical_b in interactions:
        if logical_a not in mapping or logical_b not in mapping:
            raise RoutingError(f"logical qubits {logical_a}, {logical_b} must both be in the mapping")
        pa, pb = mapping[logical_a], mapping[logical_b]
        path = _resolve_path(device, pa, pb)
        distance = len(path) - 1

        if distance == 0:
            raise RoutingError(f"logical qubits {logical_a} and {logical_b} map to the same physical qubit")

        success = 1.0
        for i in range(distance):
            success *= (1.0 - device.edge_noise(path[i], path[i + 1]))
        ops = distance  # one entangling operation per edge in the path

        routed.append(RoutedInteraction(
            logical_pair=(logical_a, logical_b), physical_path=path,
            distance=distance, primitive_operations=ops, estimated_error=1.0 - success,
        ))

    return RoutingResult(strategy="teleportation", routed=routed, final_mapping=mapping)


def compare_routing_strategies(
    device: DeviceGraph,
    interactions: List[Tuple[int, int]],
    initial_mapping: Optional[Dict[int, int]] = None,
) -> Dict[str, RoutingResult]:
    """
    Run both strategies over the identical device and interaction list and
    return both results keyed by strategy name, so a caller can compare
    `total_primitive_operations` and `total_estimated_error` directly.
    Neither run affects the other -- each starts from its own copy of
    `initial_mapping`.
    """
    return {
        "swap": route_swap_based(device, interactions, initial_mapping),
        "teleportation": route_teleportation_based(device, interactions, initial_mapping),
    }


if __name__ == "__main__":
    import device_graph

    demo_device = device_graph.linear_chain(6, qubit_error_rate=0.001, edge_error_rate=0.01)
    demo_interactions = [(0, 5), (1, 4), (0, 3)]
    results = compare_routing_strategies(demo_device, demo_interactions)
    for strategy_result in results.values():
        print(strategy_result.summary())
        print()
