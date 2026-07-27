#!/usr/bin/env python3
"""Tests for quantum_schema.py — graph model contracts."""

import unittest
from datetime import datetime, timezone

from quantum_schema import (
    NodeType, EdgeType, Node, Edge, QuantumGraph,
    RuntimeEvent, TimingDomain, FreshnessLevel, AnomalyTag,
    GraphMetrics, validate_node, validate_edge
)


class TestNodeTypes(unittest.TestCase):
    """Test node type definitions."""

    def test_all_node_types_defined(self):
        """Verify all node types exist."""
        required_types = [
            NodeType.QUBIT,
            NodeType.CIRCUIT,
            NodeType.WORKFLOW_TASK,
            NodeType.DEVICE,
            NodeType.POLICY,
            NodeType.RUNTIME_STATE
        ]
        for nt in required_types:
            self.assertIsNotNone(nt.value)

    def test_node_type_strings(self):
        """Test node type string representations."""
        self.assertEqual(NodeType.QUBIT.value, "qubit")
        self.assertEqual(NodeType.CIRCUIT.value, "circuit")


class TestEdgeTypes(unittest.TestCase):
    """Test edge type definitions."""

    def test_all_edge_types_defined(self):
        """Verify all edge types exist."""
        required_edges = [
            EdgeType.COUPLES,
            EdgeType.IMPLEMENTS,
            EdgeType.DEPENDS_ON,
            EdgeType.SUITABLE_FOR,
            EdgeType.AUTHORIZES
        ]
        for et in required_edges:
            self.assertIsNotNone(et.value)


class TestNodeValidation(unittest.TestCase):
    """Test node schema validation."""

    def test_valid_node(self):
        """Test valid node passes validation."""
        node = Node(
            node_id="q0",
            node_type=NodeType.QUBIT,
            label="Qubit 0"
        )
        valid, errors = validate_node(node)
        self.assertTrue(valid)
        self.assertEqual(len(errors), 0)

    def test_missing_node_id(self):
        """Test missing node_id fails validation."""
        node = Node(
            node_id="",
            node_type=NodeType.QUBIT,
            label="Qubit 0"
        )
        valid, errors = validate_node(node)
        self.assertFalse(valid)
        self.assertTrue(any(e.field == "node_id" for e in errors))

    def test_missing_label(self):
        """Test missing label fails validation."""
        node = Node(
            node_id="q0",
            node_type=NodeType.QUBIT,
            label=""
        )
        valid, errors = validate_node(node)
        self.assertFalse(valid)
        self.assertTrue(any(e.field == "label" for e in errors))

    def test_invalid_confidence_range(self):
        """Test confidence must be 0.0-1.0."""
        node = Node(
            node_id="q0",
            node_type=NodeType.QUBIT,
            label="Qubit",
            confidence=1.5  # Invalid
        )
        valid, errors = validate_node(node)
        self.assertFalse(valid)
        self.assertTrue(any(e.field == "confidence" for e in errors))

    def test_confidence_boundaries(self):
        """Test confidence at boundaries."""
        # 0.0 is valid
        node = Node(node_id="q0", node_type=NodeType.QUBIT, label="Q", confidence=0.0)
        valid, _ = validate_node(node)
        self.assertTrue(valid)

        # 1.0 is valid
        node = Node(node_id="q0", node_type=NodeType.QUBIT, label="Q", confidence=1.0)
        valid, _ = validate_node(node)
        self.assertTrue(valid)


class TestGraphOperations(unittest.TestCase):
    """Test QuantumGraph operations."""

    def setUp(self):
        """Create test graph."""
        self.graph = QuantumGraph(graph_id="test_graph_1")

    def test_add_valid_node(self):
        """Test adding valid node."""
        node = Node(
            node_id="q0",
            node_type=NodeType.QUBIT,
            label="Qubit 0"
        )
        success, errors = self.graph.add_node(node)
        self.assertTrue(success)
        self.assertEqual(len(errors), 0)
        self.assertIn("q0", self.graph.nodes)

    def test_add_invalid_node(self):
        """Test adding invalid node fails."""
        node = Node(
            node_id="",
            node_type=NodeType.QUBIT,
            label="Bad"
        )
        success, errors = self.graph.add_node(node)
        self.assertFalse(success)
        self.assertGreater(len(errors), 0)

    def test_add_edge(self):
        """Test adding edge with valid endpoints."""
        # Add nodes
        q0 = Node(node_id="q0", node_type=NodeType.QUBIT, label="Q0")
        q1 = Node(node_id="q1", node_type=NodeType.QUBIT, label="Q1")
        self.graph.add_node(q0)
        self.graph.add_node(q1)

        # Add edge
        edge = Edge(
            edge_id="edge_q0_q1",
            source_id="q0",
            target_id="q1",
            edge_type=EdgeType.COUPLES
        )
        success, errors = self.graph.add_edge(edge)
        self.assertTrue(success)
        self.assertIn("edge_q0_q1", self.graph.edges)

    def test_neighbors(self):
        """Test neighbor queries."""
        q0 = Node(node_id="q0", node_type=NodeType.QUBIT, label="Q0")
        q1 = Node(node_id="q1", node_type=NodeType.QUBIT, label="Q1")
        q2 = Node(node_id="q2", node_type=NodeType.QUBIT, label="Q2")

        self.graph.add_node(q0)
        self.graph.add_node(q1)
        self.graph.add_node(q2)

        edge1 = Edge(edge_id="e1", source_id="q0", target_id="q1", edge_type=EdgeType.COUPLES)
        edge2 = Edge(edge_id="e2", source_id="q0", target_id="q2", edge_type=EdgeType.COUPLES)

        self.graph.add_edge(edge1)
        self.graph.add_edge(edge2)

        neighbors = self.graph.neighbors("q0")
        self.assertEqual(len(neighbors), 2)
        self.assertIn("q1", neighbors)
        self.assertIn("q2", neighbors)

    def test_neighbors_with_edge_type_filter(self):
        """Test neighbors filtered by edge type."""
        q0 = Node(node_id="q0", node_type=NodeType.QUBIT, label="Q0")
        q1 = Node(node_id="q1", node_type=NodeType.QUBIT, label="Q1")
        self.graph.add_node(q0)
        self.graph.add_node(q1)

        edge = Edge(edge_id="e1", source_id="q0", target_id="q1", edge_type=EdgeType.COUPLES)
        self.graph.add_edge(edge)

        # Query with matching edge type
        neighbors = self.graph.neighbors("q0", edge_type=EdgeType.COUPLES)
        self.assertEqual(len(neighbors), 1)

        # Query with non-matching edge type
        neighbors = self.graph.neighbors("q0", edge_type=EdgeType.DEPENDS_ON)
        self.assertEqual(len(neighbors), 0)


class TestRuntimeEvents(unittest.TestCase):
    """Test runtime event model."""

    def test_event_creation(self):
        """Test creating runtime event."""
        event = RuntimeEvent(
            event_id="evt_1",
            timestamp=datetime.now(timezone.utc).isoformat(),
            phase="sense",
            timing_domain=TimingDomain.HARD_REAL_TIME,
            node_id=None,
            node_type=None,
            event_type="telemetry",
            message="Measurement acquired"
        )
        self.assertEqual(event.event_id, "evt_1")
        self.assertEqual(event.phase, "sense")
        self.assertEqual(event.timing_domain, TimingDomain.HARD_REAL_TIME)

    def test_event_with_anomalies(self):
        """Test event with anomaly tags."""
        event = RuntimeEvent(
            event_id="evt_2",
            timestamp=datetime.now(timezone.utc).isoformat(),
            phase="estimate",
            timing_domain=TimingDomain.SOFT_REAL_TIME,
            node_id=None,
            node_type=None,
            event_type="decision",
            message="State estimate complete",
            anomalies=[AnomalyTag.DRIFT, AnomalyTag.DEGRADATION]
        )
        self.assertEqual(len(event.anomalies), 2)
        self.assertIn(AnomalyTag.DRIFT, event.anomalies)

    def test_event_to_dict(self):
        """Test event serialization."""
        event = RuntimeEvent(
            event_id="evt_3",
            timestamp="2025-01-15T10:00:00Z",
            phase="act",
            timing_domain=TimingDomain.HARD_REAL_TIME,
            node_id=None,
            node_type=None,
            event_type="action",
            message="Action dispatched"
        )
        d = event.to_dict()
        self.assertEqual(d["event_id"], "evt_3")
        self.assertEqual(d["phase"], "act")
        self.assertIn("timestamp", d)


class TestGraphMetrics(unittest.TestCase):
    """Test graph health metrics."""

    def test_metrics_creation(self):
        """Test creating graph metrics."""
        metrics = GraphMetrics(
            total_nodes=10,
            total_edges=15,
            freshness=FreshnessLevel.FRESH,
            staleness_seconds=2.5,
            constraint_violations=1
        )
        self.assertEqual(metrics.total_nodes, 10)
        self.assertEqual(metrics.freshness, FreshnessLevel.FRESH)

    def test_metrics_to_dict(self):
        """Test metrics serialization."""
        metrics = GraphMetrics(
            total_nodes=5,
            total_edges=8,
            freshness=FreshnessLevel.CURRENT,
            staleness_seconds=0.5,
            constraint_violations=0
        )
        d = metrics.to_dict()
        self.assertEqual(d["total_nodes"], 5)
        self.assertEqual(d["freshness"], "current")


if __name__ == "__main__":
    unittest.main()
