#!/usr/bin/env python3
"""Test suite for workflow_engine.py: the chained AQEC -> capability -> routing
-> calibration -> verification pipeline."""

import random
import unittest

import device_graph as dg
import hardware_control as hc
import workflow_engine as we


class TestRunGraphopsWorkflow(unittest.TestCase):
    """
    Every test here starts the AQEC search from the trivial [[1]] base code
    (as autonomous_loop's own tests do) and sizes candidate devices at 18
    qubits -- matching code_search.DEFAULT_MAX_QUBITS_FOR_SEARCH, the AQEC
    search's own qubit ceiling -- so the search never converges on a code
    bigger than any candidate device could possibly host.
    """

    def test_runs_all_five_stages(self):
        devices = {
            "chain_18": dg.linear_chain(18, qubit_error_rate=0.001, edge_error_rate=0.01),
        }
        report = we.run_graphops_workflow(
            [[1]], devices, max_rounds=5, stall_rounds=3, rng=random.Random(1))
        self.assertEqual(len(report.stage_log), 5)
        for i in range(1, 6):
            self.assertIn(f"stage {i}", report.stage_log[i - 1])

    def test_chosen_device_is_one_of_the_candidates(self):
        devices = {
            "chain_18": dg.linear_chain(18, qubit_error_rate=0.001, edge_error_rate=0.01),
            "grid_4x5": dg.grid(4, 5, qubit_error_rate=0.001, edge_error_rate=0.01),
        }
        report = we.run_graphops_workflow(
            [[1]], devices, max_rounds=5, stall_rounds=3, rng=random.Random(1))
        self.assertIn(report.chosen_device_name, devices)

    def test_routing_comparison_has_both_strategies_when_code_has_stabilizers(self):
        devices = {"chain_18": dg.linear_chain(18, qubit_error_rate=0.001, edge_error_rate=0.01)}
        report = we.run_graphops_workflow(
            [[1]], devices, max_rounds=5, stall_rounds=3, rng=random.Random(1))
        if report.routing_comparison:
            self.assertEqual(set(report.routing_comparison), {"swap", "teleportation"})

    def test_calibration_covers_every_qubit_of_the_chosen_device(self):
        devices = {"chain_18": dg.linear_chain(18, qubit_error_rate=0.001, edge_error_rate=0.01)}
        report = we.run_graphops_workflow(
            [[1]], devices, max_rounds=5, stall_rounds=3, rng=random.Random(1))
        chosen = devices[report.chosen_device_name]
        self.assertEqual(set(report.calibration.qubit_error_rate), set(chosen.qubits))

    def test_verification_ran_with_positive_trials_when_code_has_logical_qubits(self):
        devices = {"chain_18": dg.linear_chain(18, qubit_error_rate=0.001, edge_error_rate=0.01)}
        report = we.run_graphops_workflow(
            [[1]], devices, max_rounds=5, stall_rounds=3,
            verify_trials=50, rng=random.Random(1))
        if report.aqec_report.final_code.k > 0:
            self.assertEqual(report.verification.trials, 50)

    def test_no_fitting_device_raises_workflow_error(self):
        devices = {"tiny": dg.linear_chain(1)}
        with self.assertRaises(we.WorkflowError):
            we.run_graphops_workflow(
                [[1]], devices, max_rounds=5, stall_rounds=3, rng=random.Random(1))

    def test_custom_control_adapter_factory_is_actually_used(self):
        calls = []

        def factory(device):
            calls.append(device)
            return hc.SimulatedControlAdapter(device, rng=random.Random(0))

        devices = {"chain_18": dg.linear_chain(18, qubit_error_rate=0.001, edge_error_rate=0.01)}
        we.run_graphops_workflow(
            [[1]], devices, max_rounds=5, stall_rounds=3,
            control_adapter_factory=factory, rng=random.Random(1))
        self.assertEqual(len(calls), 1)

    def test_same_seed_is_reproducible(self):
        devices = {"chain_18": dg.linear_chain(18, qubit_error_rate=0.001, edge_error_rate=0.01)}
        report_a = we.run_graphops_workflow(
            [[1]], devices, max_rounds=5, stall_rounds=3, rng=random.Random(42))
        report_b = we.run_graphops_workflow(
            [[1]], devices, max_rounds=5, stall_rounds=3, rng=random.Random(42))
        self.assertEqual(report_a.stage_log, report_b.stage_log)

    def test_summary_returns_the_stage_log_joined(self):
        devices = {"chain_18": dg.linear_chain(18, qubit_error_rate=0.001, edge_error_rate=0.01)}
        report = we.run_graphops_workflow(
            [[1]], devices, max_rounds=5, stall_rounds=3, rng=random.Random(1))
        self.assertEqual(report.summary(), "\n".join(report.stage_log))


if __name__ == "__main__":
    unittest.main()
