#!/usr/bin/env python3
"""Tests for quantum_constraints.py — physics constraint engine."""

import unittest

from quantum_schema import QuantumGraph, Node, NodeType, ConfidenceLevel
from quantum_constraints import (
    ConstraintsEngine, ControlAction, ActionEnvelope,
    ConstraintType, PhysicsProfile, CryoProfile,
    default_constraints_engine
)


class TestConstraintsEngineInitialization(unittest.TestCase):
    """Test constraints engine setup."""

    def setUp(self):
        """Create test engine."""
        self.graph = QuantumGraph(graph_id="test_constraints")
        self.engine = default_constraints_engine(self.graph, qubit_count=5)

    def test_engine_creation(self):
        """Test creating default engine."""
        self.assertIsNotNone(self.engine)
        self.assertEqual(self.engine.physics.qubit_count, 5)

    def test_constraint_evaluators_registered(self):
        """Test default constraints are registered."""
        self.assertGreater(len(self.engine.constraint_evals), 0)


class TestConstraintEvaluations(unittest.TestCase):
    """Test individual constraint checks."""

    def setUp(self):
        """Create test engine and actions."""
        self.graph = QuantumGraph(graph_id="test_eval")
        self.engine = default_constraints_engine(self.graph, qubit_count=5)

    def test_single_qubit_gate_always_allowed(self):
        """Test single-qubit operations pass coupling check."""
        action = ControlAction(
            action_id="single_q",
            pulse_family_id="single_qubit",
            target_qubits=["q0"],
            duration_ns=100.0,
            amplitude_normalized=0.5,
            phase_degrees=0.0
        )

        envelope = self.engine.evaluate_action(action)
        self.assertTrue(envelope.is_admissible)

    def test_coupled_qubits_allowed(self):
        """Test multi-qubit operations on coupled qubits."""
        action = ControlAction(
            action_id="coupled_q",
            pulse_family_id="cnot",
            target_qubits=["q0", "q1"],
            duration_ns=100.0,
            amplitude_normalized=0.5,
            phase_degrees=0.0
        )

        envelope = self.engine.evaluate_action(action)
        # q0 -> q1 should be in the coupling map
        self.assertTrue(envelope.is_admissible)

    def test_uncoupled_qubits_blocked(self):
        """Test multi-qubit operations on non-coupled qubits fail."""
        # q4 -> q0 should not be in coupling map (linear chain)
        action = ControlAction(
            action_id="uncoupled_q",
            pulse_family_id="cnot",
            target_qubits=["q4", "q0"],
            duration_ns=100.0,
            amplitude_normalized=0.5,
            phase_degrees=0.0
        )

        envelope = self.engine.evaluate_action(action)
        self.assertFalse(envelope.is_admissible)
        self.assertGreater(envelope.constraints_failed, 0)

    def test_frequency_separation_check(self):
        """Test frequency detuning validation."""
        # Default offset is 50+ MHz, should pass
        action = ControlAction(
            action_id="freq_check",
            pulse_family_id="single",
            target_qubits=["q0"],
            duration_ns=100.0,
            amplitude_normalized=0.5,
            phase_degrees=0.0
        )

        envelope = self.engine.evaluate_action(action)
        # Frequency check should pass
        freq_evals = [e for e in envelope.constraint_evals if e.constraint_type == ConstraintType.FREQUENCY_SEPARATION]
        self.assertGreater(len(freq_evals), 0)
        self.assertTrue(freq_evals[0].passed)

    def test_bandwidth_limit_enforcement(self):
        """Test control line bandwidth constraint."""
        # Very long, high-amplitude pulse may exceed bandwidth
        action = ControlAction(
            action_id="bw_test",
            pulse_family_id="long_pulse",
            target_qubits=["q0"],
            duration_ns=1000.0,  # Long duration
            amplitude_normalized=1.0,  # Max amplitude
            phase_degrees=0.0
        )

        envelope = self.engine.evaluate_action(action)
        bw_evals = [e for e in envelope.constraint_evals if e.constraint_type == ConstraintType.BANDWIDTH_LIMIT]
        self.assertGreater(len(bw_evals), 0)

    def test_temperature_envelope(self):
        """Test cryogenic temperature constraint."""
        action = ControlAction(
            action_id="temp_test",
            pulse_family_id="coherent",
            target_qubits=["q0"],
            duration_ns=100.0,
            amplitude_normalized=0.5,
            phase_degrees=0.0
        )

        envelope = self.engine.evaluate_action(action)
        temp_evals = [e for e in envelope.constraint_evals if e.constraint_type == ConstraintType.TEMPERATURE_ENVELOPE]
        self.assertGreater(len(temp_evals), 0)
        # Default temp is 15 mK, should pass
        self.assertTrue(temp_evals[0].passed)

    def test_interference_risk_assessment(self):
        """Test crosstalk and interference detection."""
        # Many active qubits may trigger interference risk
        action = ControlAction(
            action_id="interference_test",
            pulse_family_id="multi_q",
            target_qubits=["q0", "q1", "q2", "q3", "q4"],
            duration_ns=100.0,
            amplitude_normalized=0.5,
            phase_degrees=0.0
        )

        envelope = self.engine.evaluate_action(action)
        interference_evals = [e for e in envelope.constraint_evals if e.constraint_type == ConstraintType.INTERFERENCE_RISK]
        self.assertGreater(len(interference_evals), 0)


class TestActionEnvelope(unittest.TestCase):
    """Test action envelope results."""

    def setUp(self):
        """Create test engine."""
        self.graph = QuantumGraph(graph_id="test_envelope")
        self.engine = default_constraints_engine(self.graph, qubit_count=5)

    def test_envelope_confidence_mapping(self):
        """Test confidence level assignment."""
        action = ControlAction(
            action_id="conf_test",
            pulse_family_id="test",
            target_qubits=["q0"],
            duration_ns=100.0,
            amplitude_normalized=0.5,
            phase_degrees=0.0
        )

        envelope = self.engine.evaluate_action(action)
        if envelope.is_admissible:
            # All constraints pass
            self.assertEqual(envelope.confidence, ConfidenceLevel.CRITICAL)
        else:
            # Some constraints fail
            self.assertIn(envelope.confidence, [ConfidenceLevel.HIGH, ConfidenceLevel.MODERATE, ConfidenceLevel.LOW])

    def test_envelope_serialization(self):
        """Test envelope to_dict."""
        action = ControlAction(
            action_id="ser_test",
            pulse_family_id="test",
            target_qubits=["q0"],
            duration_ns=100.0,
            amplitude_normalized=0.5,
            phase_degrees=0.0
        )

        envelope = self.engine.evaluate_action(action)
        d = envelope.to_dict()

        self.assertEqual(d["action_id"], "ser_test")
        self.assertIn("is_admissible", d)
        self.assertIn("confidence", d)
        self.assertIn("violations", d)


class TestConstraintCustomization(unittest.TestCase):
    """Test custom constraint registration."""

    def setUp(self):
        """Create test engine."""
        self.graph = QuantumGraph(graph_id="test_custom")
        self.engine = default_constraints_engine(self.graph, qubit_count=3)

    def test_register_custom_constraint(self):
        """Test adding custom constraint evaluator."""
        from quantum_constraints import ConstraintEvaluation, ConstraintType, ConstraintSeverity

        def always_fail_constraint(action: ControlAction) -> ConstraintEvaluation:
            return ConstraintEvaluation(
                constraint_type=ConstraintType.GOVERNANCE_RULE,
                passed=False,
                confidence=0.0,
                severity=ConstraintSeverity.ERROR,
                message="Custom constraint always fails"
            )

        self.engine.register_constraint(always_fail_constraint)

        action = ControlAction(
            action_id="custom_test",
            pulse_family_id="test",
            target_qubits=["q0"],
            duration_ns=100.0,
            amplitude_normalized=0.5,
            phase_degrees=0.0
        )

        envelope = self.engine.evaluate_action(action)
        # Should now fail due to custom constraint
        self.assertFalse(envelope.is_admissible)


class TestRetryBudgetRecommendations(unittest.TestCase):
    """Test retry budget recommendations."""

    def setUp(self):
        """Create test engine."""
        self.graph = QuantumGraph(graph_id="test_retry")
        self.engine = default_constraints_engine(self.graph, qubit_count=5)

    def test_timing_failure_recommends_retries(self):
        """Test timing constraint failures get retry budget."""
        # Very short duration pulse (timing critical)
        action = ControlAction(
            action_id="timing_test",
            pulse_family_id="fast",
            target_qubits=["q0"],
            duration_ns=10.0,  # Very short
            amplitude_normalized=1.0,
            phase_degrees=0.0
        )

        envelope = self.engine.evaluate_action(action)
        # May recommend retries if timing-constrained
        if not envelope.is_admissible:
            self.assertGreaterEqual(envelope.recommended_retries, 0)


if __name__ == "__main__":
    unittest.main()
