#!/usr/bin/env python3
"""
Phase 2 Test Suite: Gate Logic
Tests all gate paths and reason codes.
"""

import unittest
from datetime import datetime
from research_graph_gates import (
    WorkflowGate,
    GateReasonCode,
    Node,
    Provenance,
    GateDecision
)


class TestGateLogic(unittest.TestCase):
    """Test suite for production gate logic."""

    def setUp(self):
        """Initialize gate with standard config."""
        self.gate = WorkflowGate(
            confidence_threshold=0.7,
            require_human_review=True,
            detect_conflicts=True
        )

    # ========================================================================
    # Test: LOW_CONFIDENCE Path
    # ========================================================================

    def test_low_confidence_blocks_advancement(self):
        """Confidence below threshold should block."""
        node = Node(
            id="concept_low_conf",
            type="concept",
            label="test",
            provenance=Provenance(
                source_paper="test",
                extraction_method="keyword",
                confidence=0.65,  # Below 0.7
                extracted_at=datetime.now().isoformat(),
                human_reviewed=True  # Already reviewed
            ),
            properties={"text": "test"}
        )

        decision = self.gate.should_unlock_next_stage(node)

        self.assertFalse(decision.can_proceed)
        self.assertEqual(decision.reason_code, GateReasonCode.LOW_CONFIDENCE)
        self.assertIn("65%", decision.reason)
        self.assertIn("70%", decision.reason)

    def test_confidence_at_threshold_allowed(self):
        """Confidence exactly at threshold should pass."""
        node = Node(
            id="concept_threshold",
            type="concept",
            label="test",
            provenance=Provenance(
                source_paper="test",
                extraction_method="keyword",
                confidence=0.70,  # Exactly at threshold
                extracted_at=datetime.now().isoformat(),
                human_reviewed=True
            ),
            properties={"text": "test"}
        )

        decision = self.gate.should_unlock_next_stage(node)

        # Will pass confidence check but fail downstream check (concept is terminal)
        self.assertIn(GateReasonCode.DOWNSTREAM_NOT_ALLOWED, [c.reason_code for c in decision.checks if not c.passed])

    def test_high_confidence_passes_confidence_check(self):
        """High confidence should pass the confidence check."""
        node = Node(
            id="concept_high_conf",
            type="concept",
            label="test",
            provenance=Provenance(
                source_paper="test",
                extraction_method="keyword",
                confidence=0.95,
                extracted_at=datetime.now().isoformat(),
                human_reviewed=True
            ),
            properties={"text": "test"}
        )

        decision = self.gate.should_unlock_next_stage(node)

        # Check that confidence check passed
        conf_check = [c for c in decision.checks if c.check_name == "confidence_above_threshold"][0]
        self.assertTrue(conf_check.passed)

    # ========================================================================
    # Test: REVIEW_REQUIRED Path
    # ========================================================================

    def test_unreviewed_blocks_advancement(self):
        """Unreviewed extraction should require review."""
        node = Node(
            id="concept_unreviewed",
            type="concept",
            label="test",
            provenance=Provenance(
                source_paper="test",
                extraction_method="keyword",
                confidence=0.85,  # High confidence, but...
                extracted_at=datetime.now().isoformat(),
                human_reviewed=False  # Not reviewed
            ),
            properties={"text": "test"}
        )

        decision = self.gate.should_unlock_next_stage(node)

        self.assertFalse(decision.can_proceed)
        self.assertEqual(decision.reason_code, GateReasonCode.REVIEW_REQUIRED)

    def test_reviewed_passes_review_check(self):
        """Reviewed extraction should pass review check."""
        node = Node(
            id="concept_reviewed",
            type="concept",
            label="test",
            provenance=Provenance(
                source_paper="test",
                extraction_method="keyword",
                confidence=0.85,
                extracted_at=datetime.now().isoformat(),
                human_reviewed=True,
                review_notes="Verified correct"
            ),
            properties={"text": "test"}
        )

        decision = self.gate.should_unlock_next_stage(node)

        # Check that review check passed
        review_check = [c for c in decision.checks if c.check_name == "human_reviewed"][0]
        self.assertTrue(review_check.passed)

    def test_review_not_required_if_disabled(self):
        """If require_human_review=False, should skip review check."""
        gate = WorkflowGate(require_human_review=False)
        node = Node(
            id="concept_no_review_required",
            type="concept",
            label="test",
            provenance=Provenance(
                source_paper="test",
                extraction_method="keyword",
                confidence=0.85,
                extracted_at=datetime.now().isoformat(),
                human_reviewed=False  # Not reviewed, but it's OK
            ),
            properties={"text": "test"}
        )

        decision = gate.should_unlock_next_stage(node)

        # Review check should have passed
        review_check = [c for c in decision.checks if c.check_name == "human_reviewed"][0]
        self.assertTrue(review_check.passed)

    # ========================================================================
    # Test: PROVENANCE_MISSING Path
    # ========================================================================

    def test_no_provenance_blocks(self):
        """Missing provenance should block."""
        node = Node(
            id="concept_no_provenance",
            type="concept",
            label="test",
            provenance=None,  # No provenance
            properties={"text": "test"}
        )

        decision = self.gate.should_unlock_next_stage(node)

        self.assertFalse(decision.can_proceed)
        self.assertEqual(decision.reason_code, GateReasonCode.PROVENANCE_MISSING)

    def test_missing_confidence_in_provenance_blocks(self):
        """Provenance without confidence should block."""
        node = Node(
            id="concept_no_confidence",
            type="concept",
            label="test",
            provenance=Provenance(
                source_paper="test",
                extraction_method="keyword",
                confidence=None,  # Missing confidence
                extracted_at=datetime.now().isoformat()
            ),
            properties={"text": "test"}
        )

        decision = self.gate.should_unlock_next_stage(node)

        self.assertFalse(decision.can_proceed)
        self.assertEqual(decision.reason_code, GateReasonCode.PROVENANCE_MISSING)

    # ========================================================================
    # Test: SCHEMA_INVALID Path
    # ========================================================================

    def test_missing_required_field_blocks(self):
        """Missing required schema field should block."""
        node = Node(
            id="concept_no_text",
            type="concept",
            label="test",
            provenance=Provenance(
                source_paper="test",
                extraction_method="keyword",
                confidence=0.85,
                extracted_at=datetime.now().isoformat(),
                human_reviewed=True
            ),
            properties={}  # Missing "text" field
        )

        decision = self.gate.should_unlock_next_stage(node)

        self.assertFalse(decision.can_proceed)
        self.assertEqual(decision.reason_code, GateReasonCode.SCHEMA_INVALID)

    def test_extraction_job_requires_specific_fields(self):
        """extraction_job type has different required fields."""
        node = Node(
            id="job_001",
            type="extraction_job",
            label="test extraction",
            provenance=Provenance(
                source_paper="test",
                extraction_method="job_spawn",
                confidence=1.0,
                extracted_at=datetime.now().isoformat(),
                human_reviewed=True
            ),
            properties={
                "job_id": "job_001",
                "paper_id": "paper_001",
                "extraction_type": "concept_keyword",
                "status": "completed"
            }
        )

        decision = self.gate.should_unlock_next_stage(node)

        # Schema should pass for extraction_job
        schema_check = [c for c in decision.checks if c.check_name == "schema_valid"][0]
        self.assertTrue(schema_check.passed)

    # ========================================================================
    # Test: DOWNSTREAM_NOT_ALLOWED Path
    # ========================================================================

    def test_concept_terminal_blocks_downstream(self):
        """Concepts are terminal nodes; cannot advance further."""
        node = Node(
            id="concept_terminal",
            type="concept",
            label="test",
            provenance=Provenance(
                source_paper="test",
                extraction_method="keyword",
                confidence=0.95,
                extracted_at=datetime.now().isoformat(),
                human_reviewed=True
            ),
            properties={"text": "test"}
        )

        decision = self.gate.should_unlock_next_stage(node)

        self.assertFalse(decision.can_proceed)
        self.assertEqual(decision.reason_code, GateReasonCode.DOWNSTREAM_NOT_ALLOWED)

    def test_claim_terminal_blocks_downstream(self):
        """Claims are terminal nodes; cannot advance further."""
        node = Node(
            id="claim_terminal",
            type="claim",
            label="test claim",
            provenance=Provenance(
                source_paper="test",
                extraction_method="llm",
                confidence=0.90,
                extracted_at=datetime.now().isoformat(),
                human_reviewed=True
            ),
            properties={"text": "test"}
        )

        decision = self.gate.should_unlock_next_stage(node)

        self.assertFalse(decision.can_proceed)
        self.assertEqual(decision.reason_code, GateReasonCode.DOWNSTREAM_NOT_ALLOWED)

    def test_paper_can_advance(self):
        """Papers should be allowed to advance to extraction."""
        node = Node(
            id="paper_001",
            type="paper",
            label="Test Paper",
            provenance=Provenance(
                source_paper="2606.13707",
                extraction_method="metadata",
                confidence=1.0,
                extracted_at=datetime.now().isoformat(),
                human_reviewed=True
            ),
            properties={
                "title": "Test Paper",
                "url": "https://arxiv.org/abs/2606.13707"
            }
        )

        decision = self.gate.should_unlock_next_stage(node)

        # Paper passes all checks
        downstream_check = [c for c in decision.checks if c.check_name == "downstream_allowed"][0]
        self.assertTrue(downstream_check.passed)

    # ========================================================================
    # Test: Tracing & Diagnostics
    # ========================================================================

    def test_gate_decision_includes_all_checks(self):
        """Gate decision should include all checks that ran."""
        node = Node(
            id="test_node",
            type="concept",
            label="test",
            provenance=Provenance(
                source_paper="test",
                extraction_method="keyword",
                confidence=0.85,
                extracted_at=datetime.now().isoformat(),
                human_reviewed=False
            ),
            properties={"text": "test"}
        )

        decision = self.gate.should_unlock_next_stage(node)

        # Should have run at least 4 checks before hitting review_required
        self.assertGreaterEqual(len(decision.checks), 4)

    def test_gate_reason_code_matches_first_failure(self):
        """Reason code should match the first check that failed."""
        node = Node(
            id="test_node",
            type="concept",
            label="test",
            provenance=Provenance(
                source_paper="test",
                extraction_method="keyword",
                confidence=0.60,  # Below threshold (first failure)
                extracted_at=datetime.now().isoformat(),
                human_reviewed=False  # Would also fail (second failure)
            ),
            properties={"text": "test"}
        )

        decision = self.gate.should_unlock_next_stage(node)

        # Should stop at low_confidence, not proceed to review_required
        self.assertEqual(decision.reason_code, GateReasonCode.LOW_CONFIDENCE)

    def test_gate_report_aggregates_decisions(self):
        """Gate report should aggregate statistics."""
        # Run 3 decisions
        for i, (conf, reviewed) in enumerate([(0.65, True), (0.85, True), (0.85, False)]):
            node = Node(
                id=f"test_{i}",
                type="concept",
                label="test",
                provenance=Provenance(
                    source_paper="test",
                    extraction_method="keyword",
                    confidence=conf,
                    extracted_at=datetime.now().isoformat(),
                    human_reviewed=reviewed
                ),
                properties={"text": "test"}
            )
            self.gate.should_unlock_next_stage(node)

        report = self.gate.report()

        self.assertEqual(report["total_decisions"], 3)
        self.assertGreater(report["blocked"], 0)
        self.assertIn("by_reason_code", report)

    # ========================================================================
    # Test: ALLOWED Path (All Checks Pass)
    # ========================================================================

    def test_extraction_job_can_pass_all_checks(self):
        """Extraction job with all fields and high confidence should pass."""
        node = Node(
            id="job_pass",
            type="extraction_job",
            label="Valid extraction job",
            provenance=Provenance(
                source_paper="paper_001",
                extraction_method="job_spawn",
                confidence=1.0,
                extracted_at=datetime.now().isoformat(),
                human_reviewed=True
            ),
            properties={
                "job_id": "job_pass",
                "paper_id": "paper_001",
                "extraction_type": "concept_keyword",
                "status": "completed"
            }
        )

        decision = self.gate.should_unlock_next_stage(node)

        # All checks should pass for an extraction_job
        all_passed = all(c.passed for c in decision.checks)
        self.assertTrue(all_passed)
        self.assertTrue(decision.can_proceed)
        self.assertEqual(decision.reason_code, GateReasonCode.ALLOWED)


if __name__ == "__main__":
    unittest.main(verbosity=2)
