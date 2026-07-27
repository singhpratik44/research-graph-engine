#!/usr/bin/env python3
"""
Capability router: "what is my quantum computer good for?" made concrete
by comparing a specific code's own connectivity requirements against a
specific device's actual topology, rather than answering in the abstract.
A CSS code's stabilizer generators dictate which data qubits must be
reachable from a shared ancilla during syndrome extraction -- every pair
of qubits inside one stabilizer's support needs to interact, which this
module treats as a genuine graph-derived requirement (a clique over each
stabilizer's support), not a hand-waved "the code needs N qubits."

Scoring a device for a code reuses `routing.py`'s real SWAP-based router
over that requirement graph: a device that already places a code's
interacting qubits close together needs few SWAPs and accumulates little
error; a device whose topology fights the code's structure needs many.
That is an honest, checkable notion of "good fit," not a black-box score.

This module makes no claim to solve the general graph-embedding/subgraph-
isomorphism problem optimally (that's NP-hard in general) -- it uses the
simplest fair placement (the code's qubits 0..n-1 onto the device's own
qubit ids in order) unless the caller supplies a specific mapping to try
instead. `workflow_engine.py` is where a smarter placement search, if ever
added, would plug in.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from css_codes import CSSCode
from device_graph import DeviceGraph
import routing


def _canonical_pair(a: int, b: int) -> Tuple[int, int]:
    return (a, b) if a <= b else (b, a)


def stabilizer_interaction_graph(code: CSSCode) -> List[Tuple[int, int]]:
    """
    Every pair of qubits that appear together in the support of any single
    stabilizer generator (an H_X row or an H_Z row) -- the pairwise
    connectivity a real syndrome-extraction circuit needs a shared ancilla
    to bridge. Returned as a sorted, deduplicated list of (qubit, qubit)
    pairs with the lower index first.
    """
    edges = set()
    for row in list(code.h_x) + list(code.h_z):
        support = [i for i, bit in enumerate(row) if bit]
        for i in range(len(support)):
            for j in range(i + 1, len(support)):
                edges.add(_canonical_pair(support[i], support[j]))
    return sorted(edges)


@dataclass
class CapabilityReport:
    """
    Whether a device even has enough qubits to host `code` (`fits`), and if
    so, the full `RoutingResult` of actually routing every stabilizer's
    interaction requirement over that device -- `score` combines total
    primitive operations and total estimated error into one comparable
    number (lower is better); `float("inf")` for a device that doesn't fit.
    """
    fits: bool
    routing_result: Optional[routing.RoutingResult]
    score: float
    reason: str

    def summary(self) -> str:
        if not self.fits:
            return f"does not fit: {self.reason}"
        assert self.routing_result is not None
        return (f"fits, score={self.score:.4f} "
                f"(ops={self.routing_result.total_primitive_operations}, "
                f"error={self.routing_result.total_estimated_error:.6f})")


def default_mapping(code: CSSCode, device: DeviceGraph) -> Dict[int, int]:
    """The code's logical qubit ids 0..n-1 placed onto the device's own
    qubit ids in ascending order -- the simplest fair placement, used
    unless a caller supplies a specific mapping to `score_device_for_code`."""
    candidate_qubits = sorted(device.qubits)[:code.n]
    return {i: candidate_qubits[i] for i in range(code.n)}


def score_device_for_code(
    device: DeviceGraph,
    code: CSSCode,
    mapping: Optional[Dict[int, int]] = None,
    error_weight: float = 100.0,
) -> CapabilityReport:
    """
    Score how well `device` suits `code`: not enough qubits, or a
    disconnected requirement, yields `fits=False`. Otherwise, route the
    code's full stabilizer interaction graph over the device (SWAP-based --
    the relevant strategy for a fixed physical device, unlike the
    entanglement-resource question `routing.py`'s teleportation strategy
    targets) and combine total operation count with total estimated error
    (scaled by `error_weight`, since raw error is a small fraction while
    operation counts are integers -- the two would otherwise not be
    comparable on the same scale) into one score.
    """
    if code.n > len(device.qubits):
        return CapabilityReport(
            fits=False, routing_result=None, score=float("inf"),
            reason=f"code needs {code.n} qubits, device has {len(device.qubits)}")

    mapping = mapping if mapping is not None else default_mapping(code, device)
    interactions = stabilizer_interaction_graph(code)
    if not interactions:
        return CapabilityReport(
            fits=True, routing_result=routing.RoutingResult(strategy="swap", routed=[], final_mapping=mapping),
            score=0.0, reason="code has no multi-qubit stabilizers to route")

    try:
        result = routing.route_swap_based(device, interactions, initial_mapping=mapping)
    except routing.RoutingError as exc:
        return CapabilityReport(fits=False, routing_result=None, score=float("inf"), reason=str(exc))

    score = result.total_primitive_operations + error_weight * result.total_estimated_error
    return CapabilityReport(fits=True, routing_result=result, score=score, reason="")


def recommend_device(
    devices: Dict[str, DeviceGraph],
    code: CSSCode,
    mappings: Optional[Dict[str, Dict[int, int]]] = None,
) -> List[Tuple[str, CapabilityReport]]:
    """
    Score every device in `devices` for `code` and return `(name, report)`
    pairs sorted best-first (lowest score first; non-fitting devices sort
    last, in the order `float("inf")` scores tie -- still present in the
    result, never silently dropped, so a caller can see *why* a device was
    excluded via `report.reason`). `mappings` optionally supplies a
    specific placement per device name; devices not present there use
    `default_mapping`.
    """
    mappings = mappings or {}
    reports = [
        (name, score_device_for_code(device, code, mapping=mappings.get(name)))
        for name, device in devices.items()
    ]
    reports.sort(key=lambda item: item[1].score)
    return reports


def best_device(
    devices: Dict[str, DeviceGraph],
    code: CSSCode,
    mappings: Optional[Dict[str, Dict[int, int]]] = None,
) -> str:
    """The name of the single best-fitting device, or raises `ValueError`
    if none of `devices` can host `code` at all."""
    ranked = recommend_device(devices, code, mappings)
    if not ranked or not ranked[0][1].fits:
        raise ValueError(f"no device in {list(devices)} can host a code needing {code.n} qubits")
    return ranked[0][0]


if __name__ == "__main__":
    import css_codes
    import device_graph

    # Steane [[7,1,3]] code vs. two candidate device topologies.
    hamming = [
        [1, 0, 0, 1, 1, 0, 1],
        [0, 1, 0, 1, 0, 1, 1],
        [0, 0, 1, 0, 1, 1, 1],
    ]
    steane = css_codes.build_css_code(hamming, hamming)

    candidate_devices = {
        "chain_7": device_graph.linear_chain(7, edge_error_rate=0.01),
        "grid_3x3": device_graph.grid(3, 3, edge_error_rate=0.01),
    }
    for name, report in recommend_device(candidate_devices, steane):
        print(f"{name}: {report.summary()}")
