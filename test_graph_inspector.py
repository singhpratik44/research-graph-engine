#!/usr/bin/env python3
"""
Test suite for graph_inspector.py: the human inspection surface must surface
every section the roadmap asked for, and "why blocked" must reflect a live
gate re-evaluation -- including a waiver applied after the job was held --
not a frozen spawn-time string.
"""

import unittest

import golden_fixtures as gf
import research_graph_gates as gates
from graph_inspector import render_report, _to_gate_node


class TestGraphInspectorReport(unittest.TestCase):
    def setUp(self):
        self.graph = gf.build_fixture_graph()
        self.report = render_report(self.graph)

    def test_all_sections_present(self):
        for section in ("PAPERS", "CLAIMS", "CONFLICTS", "EXTRACTION JOBS",
                         "HELD / REVIEW-REQUIRED", "WHY A GATE BLOCKED PROGRESSION"):
            self.assertIn(section, self.report)

    def test_paper_listed_with_url(self):
        self.assertIn("paper_2606.13707", self.report)
        self.assertIn("https://arxiv.org/abs/2606.13707", self.report)

    def test_both_claims_listed(self):
        self.assertIn("claim_2606_001", self.report)
        self.assertIn("claim_2701_014", self.report)

    def test_conflict_listed_as_unresolved(self):
        self.assertIn("[UNRESOLVED]", self.report)
        self.assertIn("claim_2606_001 <-> claim_2701_014", self.report)

    def test_held_job_appears_in_held_section(self):
        self.assertIn("job_2606_concepts_001", self.report)

    def test_held_job_reason_traces_to_low_confidence(self):
        self.assertIn("job_2606_concepts_001: [LOW_CONFIDENCE]", self.report)

    def test_completed_job_not_reported_as_blocked(self):
        blocked_section = self.report.split("WHY A GATE BLOCKED PROGRESSION")[1]
        self.assertNotIn("job_2606_claims_001", blocked_section)


class TestGraphInspectorReflectsLiveState(unittest.TestCase):
    """A waiver applied after the job was held must change the report without
    regenerating any fixture -- proves the report re-runs the gate rather than
    replaying the stored gate_reason string."""

    def test_waived_job_no_longer_reported_as_blocked(self):
        waived = gf.waived_graph()
        report = render_report(waived)
        blocked_section = report.split("WHY A GATE BLOCKED PROGRESSION")[1]
        self.assertNotIn("job_2606_concepts_001", blocked_section)

    def test_defective_waiver_still_reported_as_blocked(self):
        defective = gf.waived_graph_with_defect("no_reason")
        report = render_report(defective)
        blocked_section = report.split("WHY A GATE BLOCKED PROGRESSION")[1]
        self.assertIn("job_2606_concepts_001", blocked_section)


class TestAdapterRoundTrip(unittest.TestCase):
    def test_to_gate_node_preserves_identity_and_confidence(self):
        job = gf.held_for_review_job()
        gn = _to_gate_node(job)
        self.assertIsInstance(gn, gates.Node)
        self.assertEqual(gn.id, job.id)
        self.assertEqual(gn.provenance.confidence, job.provenance.confidence)

    def test_to_gate_node_handles_missing_provenance(self):
        job = gf.held_for_review_job()
        job.provenance = None
        gn = _to_gate_node(job)
        self.assertIsNone(gn.provenance)


if __name__ == "__main__":
    unittest.main()
