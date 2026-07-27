#!/usr/bin/env python3
"""
Hardware-control integration layer: the injectable seam a real
control-framework backend (e.g. Qibolab-style pulse-level device control)
would plug into. Said plainly, the same way this package states it
elsewhere for anything touching physical qubits: there is no real quantum
hardware reachable from this sandbox, and this module does not pretend
otherwise. What it provides is the *interface* -- calibrate / apply_pulse /
read_telemetry, the three operations every real control stack this
package's research is informed by exposes -- plus one honestly-simulated
concrete implementation, `SimulatedControlAdapter`, that answers those
calls from a synthetic, seedable noise model instead of a real device.

This mirrors the injectable-call pattern already used twice elsewhere in
this codebase: the main engine's `llm_worker.py` (`call_model`) and this
package's own `autonomous_loop.py` (`propose_mutation`). A caller with real
hardware access implements `HardwareControlAdapter`'s three methods against
their own control stack and passes that adapter in wherever this module's
default is used -- no other code in this package needs to change.
"""

import random
from dataclasses import dataclass, field
from typing import Dict, Optional, Protocol

from device_graph import DeviceGraph, Edge, InvalidDeviceGraphError


@dataclass(frozen=True)
class PulseSpec:
    """A control pulse to apply to one qubit -- the parameters any real
    pulse-level control stack needs to drive a single-qubit operation."""
    frequency_ghz: float
    amplitude: float
    duration_ns: float


@dataclass(frozen=True)
class PulseResult:
    qubit: int
    success: bool
    measured_error_rate: float


@dataclass(frozen=True)
class TelemetryReading:
    qubit: int
    frequency_ghz: float
    error_rate: float


@dataclass(frozen=True)
class CalibrationReport:
    qubit_error_rate: Dict[int, float]
    edge_error_rate: Dict[Edge, float]
    notes: str


class HardwareControlAdapter(Protocol):
    """
    The three operations a real control-framework integration must supply.
    Any object implementing these three methods with these signatures can
    be passed wherever this package expects a `HardwareControlAdapter` --
    `SimulatedControlAdapter` below is one such implementation, not the
    only possible one.
    """

    def calibrate(self, device: DeviceGraph) -> CalibrationReport:
        """Re-characterize the device, returning updated per-qubit/edge
        error rates."""
        ...

    def apply_pulse(self, qubit: int, pulse: PulseSpec) -> PulseResult:
        """Drive `qubit` with `pulse`, returning whether it succeeded and
        the qubit's currently-estimated error rate."""
        ...

    def read_telemetry(self, qubit: int) -> TelemetryReading:
        """Read `qubit`'s current operating parameters without applying
        any pulse."""
        ...


class SimulatedControlAdapter:
    """
    A fully-simulated `HardwareControlAdapter` -- no real hardware is
    reached by any method here, ever. It tracks its own internal per-qubit
    frequency and error-rate state, seeded from `device`'s noise model at
    construction, and perturbs that state with a seedable RNG on each
    `calibrate()` call to stand in for real hardware drift between
    calibration runs. `apply_pulse` and `read_telemetry` answer from this
    same internal state, so results are internally consistent (a qubit
    `calibrate()` just found noisier will report a worse `error_rate` from
    `read_telemetry` too) without connecting to anything external.
    """

    def __init__(
        self,
        device: DeviceGraph,
        rng: Optional[random.Random] = None,
        drift_scale: float = 0.1,
        base_frequency_ghz: float = 5.0,
    ) -> None:
        self._device = device
        self._rng = rng if rng is not None else random.Random()
        self._drift_scale = drift_scale
        self._qubit_error_rate: Dict[int, float] = {
            q: device.qubit_noise(q) for q in device.qubits
        }
        self._edge_error_rate: Dict[Edge, float] = dict(device.edge_error_rate)
        self._frequency_ghz: Dict[int, float] = {
            q: base_frequency_ghz + 0.01 * i for i, q in enumerate(device.qubits)
        }

    def _require_known_qubit(self, qubit: int) -> None:
        if qubit not in self._qubit_error_rate:
            raise InvalidDeviceGraphError(f"qubit {qubit} is not in this adapter's device")

    def calibrate(self, device: DeviceGraph) -> CalibrationReport:
        """
        Re-sample every qubit's and edge's error rate as its current value
        perturbed by up to `drift_scale` (fractionally), clamped to
        [0.0, 1.0] -- simulated drift, not a real measurement. Updates and
        returns the adapter's own internal state; `device` is accepted (and
        must match the topology this adapter was constructed with) purely
        so a caller can pass the same device it's routing/scoring against,
        the same shape a real calibration call would take.
        """
        if set(device.qubits) != set(self._qubit_error_rate):
            raise InvalidDeviceGraphError(
                "calibrate() was called with a device whose qubits don't match "
                "the one this adapter was constructed with")
        for q in self._qubit_error_rate:
            drift = self._rng.uniform(-self._drift_scale, self._drift_scale)
            self._qubit_error_rate[q] = min(1.0, max(0.0, self._qubit_error_rate[q] * (1 + drift)))
        for e in self._edge_error_rate:
            drift = self._rng.uniform(-self._drift_scale, self._drift_scale)
            self._edge_error_rate[e] = min(1.0, max(0.0, self._edge_error_rate[e] * (1 + drift)))
        return CalibrationReport(
            qubit_error_rate=dict(self._qubit_error_rate),
            edge_error_rate=dict(self._edge_error_rate),
            notes="simulated calibration -- no real hardware was measured",
        )

    def apply_pulse(self, qubit: int, pulse: PulseSpec) -> PulseResult:
        """
        Simulate applying `pulse` to `qubit`: succeeds with probability
        `1 - current_error_rate`, drawn from this adapter's own RNG.
        """
        self._require_known_qubit(qubit)
        error_rate = self._qubit_error_rate[qubit]
        success = self._rng.random() >= error_rate
        return PulseResult(qubit=qubit, success=success, measured_error_rate=error_rate)

    def read_telemetry(self, qubit: int) -> TelemetryReading:
        self._require_known_qubit(qubit)
        return TelemetryReading(
            qubit=qubit,
            frequency_ghz=self._frequency_ghz[qubit],
            error_rate=self._qubit_error_rate[qubit],
        )


if __name__ == "__main__":
    import device_graph

    demo_device = device_graph.linear_chain(3, qubit_error_rate=0.01, edge_error_rate=0.02)
    adapter = SimulatedControlAdapter(demo_device, rng=random.Random(2026))
    print(adapter.calibrate(demo_device))
    print(adapter.apply_pulse(0, PulseSpec(frequency_ghz=5.0, amplitude=0.5, duration_ns=20.0)))
    print(adapter.read_telemetry(0))
