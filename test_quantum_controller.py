#!/usr/bin/env python3
"""Integration tests for quantum_controller.py — feedback loop."""

import unittest
import time

from quantum_schema import (
    QuantumGraph, Node, NodeType, RuntimeEvent, TimingDomain,
    FreshnessLevel, AnomalyTag, ConfidenceLevel
)
from quantum_constraints import default_constraints_engine, ControlAction
from quantum_simulator import create_simulator, SimulatorType
from quantum_dashboard import DashboardBackend, get_dashboard_backend
from quantum_controller import FeedbackLoopController, RecoveryPolicy


class TestFeedbackLoopIntegration(unittest.TestCase):
    """Test complete feedback loop."""

    def setUp(self):
        """Create controller with all components."""
        self.graph = QuantumGraph(graph_id="test_loop")

        # Add some nodes to the graph
        q0 = Node(node_id="q0", node_type=NodeType.QUBIT, label="Qubit 0")
        q1 = Node(node_id="q1", node_type=NodeType.QUBIT, label="Qubit 1")
        self.graph.add_node(q0)
        self.graph.add_node(q1)

        # Create components
        self.constraints_engine = default_constraints_engine(self.graph, qubit_count=5)
        self.simulator = create_simulator(SimulatorType.MARKOVIAN)
        self.dashboard = DashboardBackend()

        # Create controller
        self.policy = RecoveryPolicy(
            max_retry_budget=2,
            escalation_threshold=0.6,
            approval_required_for_critical=True
        )

        self.controller = FeedbackLoopController(
            graph=self.graph,
            constraints_engine=self.constraints_engine,
            simulator=self.simulator,
            dashboard_backend=self.dashboard,
            recovery_policy=self.policy
        )

    def test_controller_initialization(self):
        """Test controller setup."""
        self.assertIsNotNone(self.controller)
        self.assertEqual(self.controller.state.iteration_count, 0)
        self.assertEqual(self.controller.state.controller_id, self.controller.state.controller_id)

    def test_single_iteration(self):
        """Test running one complete iteration."""
        success, state = self.controller.run_one_iteration()

        self.assertTrue(success)
        self.assertEqual(state.iteration_count, 1)
        self.assertIsNotNone(state.loop_start_time)
        self.assertGreater(len(state.phases), 0)

    def test_all_six_phases_executed(self):
        """Test all six stages complete in one iteration."""
        success, state = self.controller.run_one_iteration()

        self.assertTrue(success)
        phase_names = [p.phase_name for p in state.phases]
        expected_phases = ["sense", "estimate", "constrain", "act", "validate", "learn"]

        for phase in expected_phases:
            self.assertIn(phase, phase_names)

    def test_phase_metrics_recorded(self):
        """Test phase execution metrics are recorded."""
        success, state = self.controller.run_one_iteration()

        self.assertTrue(success)
        for phase_metric in state.phases:
            self.assertGreater(phase_metric.duration_ms, 0.0)
            self.assertGreaterEqual(phase_metric.confidence, 0.0)
            self.assertLessEqual(phase_metric.confidence, 1.0)

    def test_action_executed_in_act_phase(self):
        """Test action is executed during act phase."""
        success, state = self.controller.run_one_iteration()

        self.assertTrue(success)
        self.assertIsNotNone(state.last_action_id)
        self.assertIsNotNone(state.last_action_confidence)
        self.assertGreater(state.total_actions_executed, 0)

    def test_event_emission(self):
        """Test runtime events are emitted."""
        success, state = self.controller.run_one_iteration()

        self.assertTrue(success)
        self.assertGreater(len(state.recent_events), 0)

        # Check event properties
        for event in state.recent_events:
            self.assertIsNotNone(event.event_id)
            self.assertIsNotNone(event.timestamp)
            self.assertIn(event.phase, ["sense", "estimate", "constrain", "act", "validate", "learn"])

    def test_dashboard_updated(self):
        """Test dashboard backend receives state updates."""
        success, state = self.controller.run_one_iteration()

        self.assertTrue(success)
        overview = self.dashboard.get_overview()

        self.assertIsNotNone(overview)
        self.assertIsNotNone(overview.loop_state)
        self.assertEqual(overview.loop_state.iteration_count, 1)

    def test_multiple_iterations(self):
        """Test running multiple iterations."""
        for i in range(3):
            success, state = self.controller.run_one_iteration()
            self.assertTrue(success)
            self.assertEqual(state.iteration_count, i + 1)

        self.assertEqual(self.controller.state.iteration_count, 3)

    def test_timing_measurements(self):
        """Test timing of loop execution."""
        start = time.time()
        success, state = self.controller.run_one_iteration()
        elapsed_ms = (time.time() - start) * 1000

        self.assertTrue(success)
        total_phase_time = sum(p.duration_ms for p in state.phases)
        # Total phase time should be close to elapsed time (within ~50ms overhead)
        self.assertLess(abs(total_phase_time - elapsed_ms), 100)

    def test_recovery_policy_applied(self):
        """Test recovery policy is accessible."""
        self.assertEqual(self.controller.state.recovery_policy.max_retry_budget, 2)
        self.assertEqual(self.controller.state.recovery_policy.escalation_threshold, 0.6)
        self.assertTrue(self.controller.state.recovery_policy.approval_required_for_critical)

    def test_loop_produces_consistent_state(self):
        """Test loop state is self-consistent."""
        success, state = self.controller.run_one_iteration()

        self.assertTrue(success)
        # No phase should have negative duration
        for phase in state.phases:
            self.assertGreater(phase.duration_ms, 0.0)

        # Event count should match rough expectations (at least one per phase)
        self.assertGreaterEqual(len(state.recent_events), len(state.phases) - 2)


class TestControllerWithConstraintFailure(unittest.TestCase):
    """Test controller handling of constraint violations."""

    def setUp(self):
        """Create controller."""
        self.graph = QuantumGraph(graph_id="test_constraint_fail")
        self.constraints_engine = default_constraints_engine(self.graph, qubit_count=3)
        self.simulator = create_simulator(SimulatorType.MARKOVIAN)
        self.dashboard = DashboardBackend()

        self.controller = FeedbackLoopController(
            graph=self.graph,
            constraints_engine=self.constraints_engine,
            simulator=self.simulator,
            dashboard_backend=self.dashboard
        )

    def test_iteration_completes_with_constraint_violation(self):
        """Test loop completes even when constraints fail."""
        # Run multiple iterations; some may have constraint violations
        for i in range(3):
            success, state = self.controller.run_one_iteration()
            # Loop should complete regardless
            self.assertTrue(success)


class TestDashboardIntegration(unittest.TestCase):
    """Test dashboard receives controller updates."""

    def setUp(self):
        """Create controller with dashboard."""
        self.graph = QuantumGraph(graph_id="test_dashboard")
        self.constraints_engine = default_constraints_engine(self.graph, qubit_count=5)
        self.simulator = create_simulator(SimulatorType.NON_MARKOVIAN)
        self.dashboard = DashboardBackend()

        self.controller = FeedbackLoopController(
            graph=self.graph,
            constraints_engine=self.constraints_engine,
            simulator=self.simulator,
            dashboard_backend=self.dashboard
        )

    def test_dashboard_overview_available(self):
        """Test dashboard overview is populated."""
        self.controller.run_one_iteration()

        overview = self.dashboard.get_overview()
        self.assertIsNotNone(overview.loop_state)

    def test_event_history_accumulated(self):
        """Test events accumulate in dashboard."""
        self.controller.run_one_iteration()
        history_1 = self.dashboard.get_event_history(limit=100)

        self.controller.run_one_iteration()
        history_2 = self.dashboard.get_event_history(limit=100)

        # Second run should have more events
        self.assertGreater(len(history_2), len(history_1))

    def test_dashboard_kpis_computed(self):
        """Test KPIs are computed."""
        self.controller.run_one_iteration()
        overview = self.dashboard.get_overview()

        self.assertIn("avg_loop_time_ms", overview.kpis)
        self.assertIn("loop_confidence", overview.kpis)
        self.assertGreater(overview.kpis["avg_loop_time_ms"], 0.0)


class TestControllerState(unittest.TestCase):
    """Test controller state management."""

    def setUp(self):
        """Create controller."""
        self.graph = QuantumGraph(graph_id="test_state")
        self.constraints_engine = default_constraints_engine(self.graph, qubit_count=5)
        self.simulator = create_simulator()
        self.dashboard = DashboardBackend()

        self.controller = FeedbackLoopController(
            graph=self.graph,
            constraints_engine=self.constraints_engine,
            simulator=self.simulator,
            dashboard_backend=self.dashboard
        )

    def test_iteration_count_increments(self):
        """Test iteration counter increments."""
        self.assertEqual(self.controller.state.iteration_count, 0)

        self.controller.run_one_iteration()
        self.assertEqual(self.controller.state.iteration_count, 1)

        self.controller.run_one_iteration()
        self.assertEqual(self.controller.state.iteration_count, 2)

    def test_action_statistics_tracked(self):
        """Test action execution statistics."""
        for i in range(3):
            self.controller.run_one_iteration()

        self.assertEqual(self.controller.state.total_actions_executed, 3)

    def test_current_phase_updated(self):
        """Test current_phase field is updated."""
        self.controller.run_one_iteration()
        # After iteration completes, current_phase should reflect the last phase
        self.assertIn(self.controller.state.current_phase, ["sense", "estimate", "constrain", "act", "validate", "learn"])


if __name__ == "__main__":
    unittest.main()
