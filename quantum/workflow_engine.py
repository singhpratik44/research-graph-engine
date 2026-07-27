#!/usr/bin/env python3
"""
The agentic workflow engine: the concrete "let agents optimize over the
graph" half of this package's stated build thesis, chaining every other
GraphOps module into one staged, autonomously-run pipeline with a full
structured audit trail -- not a prose narrative of what happened, a
`WorkflowReport` a caller can inspect stage by stage. This is the module
"Quantum Agents" and the agentic-VQC-design literature this package's
research is informed by actually describes: a task decomposed into
sense/decide/act stages chained together and run without a human picking
the next step, echoing this repo's main engine's own workflow-gate
discipline (structured records, not prose) applied here to an entirely
separate, physically-flavored pipeline.

The five stages, each reusing a module already built and tested in
isolation elsewhere in this package -- nothing new is reimplemented here,
this module is pure composition:

  1. AQEC search       (autonomous_loop.run_autonomous_qec_loop)
     -- autonomously improve a starting classical base code into a scored
        CSS code.
  2. Capability routing (capability_router.recommend_device)
     -- rank the candidate devices for the code the search converged on,
        picking the best fit.
  3. Physical routing   (routing.compare_routing_strategies)
     -- compare SWAP-based vs. teleportation-based routing of the code's
        stabilizer interaction graph on the chosen device.
  4. Hardware calibration (hardware_control.HardwareControlAdapter)
     -- calibrate the chosen device via an injectable control adapter
        (default: SimulatedControlAdapter -- no real hardware is reached).
  5. Verification        (qec_simulation.simulate_logical_error_rate)
     -- re-simulate the code's logical error rate using the *calibrated*
        device noise, not just its static baseline.

Stage 5's physical_error_rate is deliberately simplified, said plainly:
`qec_simulation` models one scalar physical error rate per code, not a
per-qubit/per-edge device profile, so this module averages the calibrated
device's qubit and edge error rates into a single number. That is a real
simplification of a real device's heterogeneous noise profile, not a
claim that a single scalar fully captures it.
"""

import random
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Tuple

import autonomous_loop
import capability_router
import qec_simulation
import routing
from autonomous_loop import AutonomousLoopReport
from capability_router import CapabilityReport
from device_graph import DeviceGraph
from hardware_control import CalibrationReport, HardwareControlAdapter, SimulatedControlAdapter
from qec_simulation import SimulationResult
from routing import RoutingResult


class WorkflowError(ValueError):
    """No candidate device can host the code the AQEC search converged on."""


ControlAdapterFactory = Callable[[DeviceGraph], HardwareControlAdapter]


def _default_control_adapter_factory(rng: random.Random) -> ControlAdapterFactory:
    return lambda device: SimulatedControlAdapter(device, rng=rng)


def _average_device_error_rate(device: DeviceGraph) -> float:
    """Mean of every qubit's and every edge's error rate on `device` -- the
    single scalar stage 5 hands to `qec_simulation`'s code-level noise
    model. 0.0 for a device with no qubits (nothing to average)."""
    rates = [device.qubit_noise(q) for q in device.qubits]
    rates += [device.edge_noise(a, b) for a, b in device.edges]
    return sum(rates) / len(rates) if rates else 0.0


@dataclass
class WorkflowReport:
    """The full, structured record of one GraphOps workflow run -- every
    stage's own result object, plus a short structured log line per stage
    (`stage_log`), not a prose summary."""
    aqec_report: AutonomousLoopReport
    capability_ranking: List[Tuple[str, CapabilityReport]]
    chosen_device_name: str
    routing_comparison: Dict[str, RoutingResult]
    calibration: CalibrationReport
    verification: SimulationResult
    stage_log: List[str]

    def summary(self) -> str:
        return "\n".join(self.stage_log)


def run_graphops_workflow(
    initial_h,
    devices: Dict[str, DeviceGraph],
    max_rounds: int = 30,
    stall_rounds: int = 8,
    verify_trials: int = 300,
    control_adapter_factory: Optional[ControlAdapterFactory] = None,
    rng: Optional[random.Random] = None,
) -> WorkflowReport:
    """
    Run the full five-stage GraphOps pipeline starting from classical base
    code `initial_h`, choosing among `devices` (name -> DeviceGraph).
    `control_adapter_factory` is the injection point for a real
    control-framework integration (default: `SimulatedControlAdapter`,
    which reaches no real hardware); it must accept a `DeviceGraph` and
    return a `HardwareControlAdapter`. Raises `WorkflowError` if no device
    in `devices` can host the code the AQEC search converges on -- there is
    nothing further to route, calibrate, or verify in that case.
    """
    rng = rng if rng is not None else random.Random()
    adapter_factory = control_adapter_factory or _default_control_adapter_factory(rng)
    stage_log: List[str] = []

    aqec_report = autonomous_loop.run_autonomous_qec_loop(
        initial_h, max_rounds=max_rounds, stall_rounds=stall_rounds, rng=rng)
    final_code = aqec_report.final_code
    stage_log.append(
        f"stage 1 (AQEC search): {final_code.parameters()} after "
        f"{len(aqec_report.rounds)} rounds, {len(aqec_report.accepted_rounds)} accepted")

    ranking = capability_router.recommend_device(devices, final_code)
    if not ranking or not ranking[0][1].fits:
        stage_log.append(f"stage 2 (capability routing): no device in {list(devices)} can host "
                          f"{final_code.parameters()} -- workflow cannot proceed")
        raise WorkflowError(
            f"no device in {list(devices)} can host a code needing {final_code.n} qubits "
            f"(stages completed: {stage_log})")
    chosen_name, chosen_report = ranking[0]
    chosen_device = devices[chosen_name]
    stage_log.append(
        f"stage 2 (capability routing): chose '{chosen_name}' (score={chosen_report.score:.4f}) "
        f"out of {len(ranking)} candidate device(s)")

    interactions = capability_router.stabilizer_interaction_graph(final_code)
    mapping = capability_router.default_mapping(final_code, chosen_device)
    if interactions:
        routing_comparison = routing.compare_routing_strategies(
            chosen_device, interactions, initial_mapping=mapping)
        stage_log.append(
            "stage 3 (physical routing): swap ops="
            f"{routing_comparison['swap'].total_primitive_operations} "
            f"(error={routing_comparison['swap'].total_estimated_error:.6f}), "
            "teleportation ops="
            f"{routing_comparison['teleportation'].total_primitive_operations} "
            f"(error={routing_comparison['teleportation'].total_estimated_error:.6f})")
    else:
        routing_comparison = {}
        stage_log.append("stage 3 (physical routing): code has no multi-qubit stabilizers to route")

    adapter = adapter_factory(chosen_device)
    calibration = adapter.calibrate(chosen_device)
    calibrated_device = DeviceGraph(
        qubits=chosen_device.qubits, edges=chosen_device.edges,
        qubit_error_rate=calibration.qubit_error_rate,
        edge_error_rate=calibration.edge_error_rate,
    )
    stage_log.append(f"stage 4 (hardware calibration): {calibration.notes}")

    physical_error_rate = _average_device_error_rate(calibrated_device)
    if final_code.k > 0:
        verification = qec_simulation.simulate_logical_error_rate(
            final_code, physical_error_rate, trials=verify_trials, rng=rng)
    else:
        verification = SimulationResult(
            physical_error_rate=physical_error_rate, trials=0, logical_failures=0)
    stage_log.append(
        f"stage 5 (verification): logical_error_rate={verification.logical_error_rate:.6f} "
        f"at physical_error_rate={physical_error_rate:.6f} over {verification.trials} trials")

    return WorkflowReport(
        aqec_report=aqec_report, capability_ranking=ranking, chosen_device_name=chosen_name,
        routing_comparison=routing_comparison, calibration=calibration,
        verification=verification, stage_log=stage_log,
    )


if __name__ == "__main__":
    import device_graph

    demo_devices = {
        "chain_7": device_graph.linear_chain(7, qubit_error_rate=0.001, edge_error_rate=0.01),
        "grid_3x3": device_graph.grid(3, 3, qubit_error_rate=0.001, edge_error_rate=0.01),
    }
    report = run_graphops_workflow(
        [[1, 1, 0], [0, 1, 1]], demo_devices, max_rounds=10, stall_rounds=5, rng=random.Random(2026))
    print(report.summary())
