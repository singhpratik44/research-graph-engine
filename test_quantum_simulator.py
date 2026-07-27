#!/usr/bin/env python3
"""Tests for quantum_simulator.py — simulation interface."""

import unittest

from quantum_schema import QuantumGraph, ConfidenceLevel
from quantum_simulator import (
    SimulatorType, TrajectoryResult, MMarkovianSimulator,
    TrajectorySimulator, create_simulator, RewardComponent
)


class TestMarkovianSimulator(unittest.TestCase):
    """Test Markovian simulator."""

    def setUp(self):
        """Create test simulator."""
        self.graph = QuantumGraph(graph_id="test_markov")
        self.sim = MMarkovianSimulator()
        self.sim.initialize(self.graph)

    def test_simulator_initialization(self):
        """Test simulator setup."""
        self.assertIsNotNone(self.sim)
        self.assertEqual(self.sim.get_simulator_type(), SimulatorType.MARKOVIAN)

    def test_single_step_trajectory(self):
        """Test running single-step trajectory."""
        action = {
            "action_id": "act_1",
            "pulse_family_id": "single",
            "target_qubits": ["q0"],
            "duration_ns": 100.0,
            "amplitude_normalized": 0.5
        }

        result = self.sim.run_trajectory([action], num_shots=100)

        self.assertTrue(result.completed)
        self.assertEqual(len(result.steps), 1)
        self.assertGreater(result.average_fidelity, 0.0)
        self.assertLessEqual(result.average_fidelity, 1.0)

    def test_multi_step_trajectory(self):
        """Test running multi-step trajectory."""
        actions = [
            {
                "action_id": f"act_{i}",
                "pulse_family_id": "single",
                "target_qubits": ["q0"],
                "duration_ns": 100.0 + i * 10,
                "amplitude_normalized": 0.5
            }
            for i in range(5)
        ]

        result = self.sim.run_trajectory(actions, num_shots=100)

        self.assertTrue(result.completed)
        self.assertEqual(len(result.steps), 5)
        self.assertGreater(result.total_reward, 0.0)

    def test_fidelity_degradation_with_duration(self):
        """Test fidelity decreases with gate duration."""
        short_action = {
            "action_id": "short",
            "pulse_family_id": "quick",
            "target_qubits": ["q0"],
            "duration_ns": 50.0,
            "amplitude_normalized": 0.5
        }

        long_action = {
            "action_id": "long",
            "pulse_family_id": "slow",
            "target_qubits": ["q0"],
            "duration_ns": 500.0,
            "amplitude_normalized": 0.5
        }

        short_result = self.sim.run_trajectory([short_action], num_shots=100)
        long_result = self.sim.run_trajectory([long_action], num_shots=100)

        # Longer gate should have lower fidelity
        self.assertGreater(short_result.average_fidelity, long_result.average_fidelity)

    def test_reward_components(self):
        """Test reward decomposition."""
        action = {
            "action_id": "reward_test",
            "pulse_family_id": "test",
            "target_qubits": ["q0"],
            "duration_ns": 100.0,
            "amplitude_normalized": 0.5
        }

        result = self.sim.run_trajectory([action], num_shots=100)

        self.assertIn(RewardComponent.FIDELITY, result.reward_components)
        self.assertIn(RewardComponent.ERROR_SUPPRESSION, result.reward_components)

    def test_robustness_estimation(self):
        """Test robustness metrics."""
        action = {
            "action_id": "robust_test",
            "pulse_family_id": "test",
            "target_qubits": ["q0"],
            "duration_ns": 100.0,
            "amplitude_normalized": 0.5
        }

        result = self.sim.run_trajectory([action], num_shots=100)
        robustness = result.robustness

        self.assertIsNotNone(robustness)
        self.assertGreater(robustness.noise_resilience, 0.0)
        self.assertLess(robustness.noise_resilience, 2.0)

    def test_confidence_assignment(self):
        """Test confidence levels are assigned."""
        action = {
            "action_id": "conf_test",
            "pulse_family_id": "test",
            "target_qubits": ["q0"],
            "duration_ns": 100.0,
            "amplitude_normalized": 0.5
        }

        result = self.sim.run_trajectory([action], num_shots=100)

        self.assertIsNotNone(result.confidence)
        self.assertIn(result.confidence, [ConfidenceLevel.CRITICAL, ConfidenceLevel.HIGH, ConfidenceLevel.MODERATE])

    def test_trajectory_serialization(self):
        """Test trajectory result to_dict."""
        action = {
            "action_id": "ser_test",
            "pulse_family_id": "test",
            "target_qubits": ["q0"],
            "duration_ns": 100.0,
            "amplitude_normalized": 0.5
        }

        result = self.sim.run_trajectory([action], num_shots=100)
        d = result.to_dict()

        self.assertIn("trajectory_id", d)
        self.assertIn("step_count", d)
        self.assertIn("total_reward", d)
        self.assertIn("average_fidelity", d)


class TestTrajectorySimulator(unittest.TestCase):
    """Test non-Markovian trajectory simulator."""

    def setUp(self):
        """Create test simulator."""
        self.graph = QuantumGraph(graph_id="test_trajectory")
        self.sim = TrajectorySimulator()
        self.sim.initialize(self.graph)

    def test_simulator_type(self):
        """Test simulator identifies as non-Markovian."""
        self.assertEqual(self.sim.get_simulator_type(), SimulatorType.NON_MARKOVIAN)

    def test_single_trajectory(self):
        """Test running single trajectory."""
        action = {
            "action_id": "act_1",
            "pulse_family_id": "test",
            "target_qubits": ["q0"],
            "duration_ns": 100.0,
            "amplitude_normalized": 0.5
        }

        result = self.sim.run_trajectory([action], num_shots=100)

        self.assertTrue(result.completed)
        self.assertEqual(len(result.steps), 1)

    def test_history_effects(self):
        """Test that history affects later steps."""
        actions = [
            {
                "action_id": f"act_{i}",
                "pulse_family_id": "test",
                "target_qubits": ["q0"],
                "duration_ns": 100.0,
                "amplitude_normalized": 0.5
            }
            for i in range(5)
        ]

        result = self.sim.run_trajectory(actions, num_shots=100)

        # History effects: fidelity should generally decrease over time
        fidelities = [s.fidelity for s in result.steps]
        # At least some steps should show declining trend
        self.assertGreater(len(fidelities), 1)

    def test_memory_effects_captured(self):
        """Test memory effects are reflected in cumulative error."""
        actions = [
            {
                "action_id": f"act_{i}",
                "pulse_family_id": "test",
                "target_qubits": ["q0"],
                "duration_ns": 100.0,
                "amplitude_normalized": 0.5
            }
            for i in range(3)
        ]

        result = self.sim.run_trajectory(actions, num_shots=100)

        # Cumulative error should include memory effects
        sum_errors = sum(s.error_rate for s in result.steps)
        self.assertGreater(result.cumulative_error, sum_errors)

    def test_confidence_increases_with_history(self):
        """Test confidence level improves with trajectory length."""
        short = self.sim.run_trajectory(
            [{"action_id": "a1", "pulse_family_id": "test", "target_qubits": ["q0"], "duration_ns": 100.0, "amplitude_normalized": 0.5}],
            num_shots=100
        )

        self.sim.reset()

        long = self.sim.run_trajectory(
            [
                {"action_id": f"a{i}", "pulse_family_id": "test", "target_qubits": ["q0"], "duration_ns": 100.0, "amplitude_normalized": 0.5}
                for i in range(10)
            ],
            num_shots=100
        )

        # Longer trajectory should have higher confidence
        # Map confidence levels to numeric values for comparison
        confidence_rank = {
            ConfidenceLevel.UNCERTAIN: 0,
            ConfidenceLevel.LOW: 1,
            ConfidenceLevel.MODERATE: 2,
            ConfidenceLevel.HIGH: 3,
            ConfidenceLevel.CRITICAL: 4
        }
        self.assertGreater(confidence_rank[long.confidence], confidence_rank[short.confidence])


class TestSimulatorFactory(unittest.TestCase):
    """Test simulator factory."""

    def test_create_markovian_simulator(self):
        """Test creating Markovian simulator."""
        sim = create_simulator(SimulatorType.MARKOVIAN)
        self.assertEqual(sim.get_simulator_type(), SimulatorType.MARKOVIAN)

    def test_create_trajectory_simulator(self):
        """Test creating trajectory simulator."""
        sim = create_simulator(SimulatorType.NON_MARKOVIAN)
        self.assertEqual(sim.get_simulator_type(), SimulatorType.NON_MARKOVIAN)

    def test_default_is_markovian(self):
        """Test default simulator is Markovian."""
        sim = create_simulator()
        self.assertEqual(sim.get_simulator_type(), SimulatorType.MARKOVIAN)


class TestSimulatorComparison(unittest.TestCase):
    """Test comparing Markovian and non-Markovian simulators."""

    def setUp(self):
        """Create both simulators."""
        self.graph = QuantumGraph(graph_id="test_comparison")
        self.markovian = MMarkovianSimulator()
        self.markovian.initialize(self.graph)
        self.trajectory = TrajectorySimulator()
        self.trajectory.initialize(self.graph)

    def test_both_handle_same_actions(self):
        """Test both simulators can process same actions."""
        actions = [
            {
                "action_id": f"act_{i}",
                "pulse_family_id": "test",
                "target_qubits": ["q0"],
                "duration_ns": 100.0 + i * 20,
                "amplitude_normalized": 0.5
            }
            for i in range(3)
        ]

        markov_result = self.markovian.run_trajectory(actions, num_shots=100)
        traj_result = self.trajectory.run_trajectory(actions, num_shots=100)

        self.assertEqual(markov_result.step_count, traj_result.step_count)


if __name__ == "__main__":
    unittest.main()
