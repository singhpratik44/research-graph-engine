#!/usr/bin/env python3
"""
Test suite for qih_stress_corpus.py: the adversarial real-world case where a
document mixes well-established physics with self-published, unsupported
speculation at identical citation-and-formatting confidence. Proves the gate
separates them by *reason code*, not just pass/fail -- since every CLAIM node
is downstream-terminal by schema design (see test_schema.py's
test_fixture_4_claims_are_terminal_at_gate), "can_proceed" is always False
for a claim; the meaningful signal is *why*.
"""

import unittest

import graph_queries as q
import research_graph_gates as gates
from research_graph_schema import NodeType
import qih_stress_corpus as qih


class TestStressGraphIsSchemaValid(unittest.TestCase):
    def test_graph_validates_with_zero_errors(self):
        graph = qih.build_stress_graph()
        result = graph.validate()
        self.assertTrue(result.valid, [e.message for e in result.errors])

    def test_seven_papers_ten_claims(self):
        graph = qih.build_stress_graph()
        self.assertEqual(len([n for n in graph.nodes if n.type == NodeType.PAPER.value]), 7)
        self.assertEqual(len([n for n in graph.nodes if n.type == NodeType.CLAIM.value]), 10)

    def test_two_conflicts_recorded(self):
        graph = qih.build_stress_graph()
        self.assertEqual(len(graph.conflicts), 2)
        self.assertTrue(all(not c.resolved for c in graph.conflicts))


class TestGateSeparatesWellEstablishedFromSpeculative(unittest.TestCase):
    """The core claim under test: reason codes, not raw pass/fail, are what
    distinguish 'solid claim, just terminal' from 'genuinely under-supported'
    from 'active unresolved dispute.'"""

    def setUp(self):
        self.graph = qih.build_stress_graph()

    def _reason(self, claim_id):
        return q.why_blocked(self.graph, claim_id).reason_code

    def test_uncontested_high_confidence_claims_are_only_structurally_blocked(self):
        # Passed every real check (schema, provenance, confidence, review, conflicts) --
        # DOWNSTREAM_NOT_ALLOWED means "solid claim, terminal node type," not "bad claim."
        for claim_id in ("claim_holography_established", "claim_bh_thermo_established",
                         "claim_qih_self_published", "claim_nwqworkflow_real"):
            self.assertEqual(self._reason(claim_id), gates.GateReasonCode.DOWNSTREAM_NOT_ALLOWED,
                             f"{claim_id} should be blocked only by the structural check")

    def test_under_supported_claims_fail_on_confidence(self):
        for claim_id in ("claim_consciousness_orch_or", "claim_light_angle_derives_gr",
                         "claim_workflow_qih_link_unsupported"):
            self.assertEqual(self._reason(claim_id), gates.GateReasonCode.LOW_CONFIDENCE,
                             f"{claim_id} should fail on confidence, not conflict or schema")

    def test_active_research_claim_fails_on_confidence_not_conflict(self):
        # quantum_geometry has no conflict -- it's genuinely unresolved research,
        # correctly distinguished from the two claims that ARE in active disputes.
        self.assertEqual(self._reason("claim_quantum_geometry_active"), gates.GateReasonCode.LOW_CONFIDENCE)

    def test_both_sides_of_each_dispute_are_held_on_conflict(self):
        # Symmetric: a high-confidence rebuttal doesn't just override its target --
        # the gate holds it too, on CONFLICT_UNRESOLVED, until a human resolves
        # which side wins. (Its low-confidence counterpart in the same dispute,
        # claim_light_angle_derives_gr, is covered separately below: it fails
        # on confidence before the conflict check even runs.)
        self.assertEqual(self._reason("claim_light_angle_unsupported"),
                         gates.GateReasonCode.CONFLICT_UNRESOLVED)
        self.assertEqual(self._reason("claim_orch_or_mainstream_rejection"),
                         gates.GateReasonCode.CONFLICT_UNRESOLVED)

    def test_low_confidence_claim_in_a_dispute_fails_on_confidence_first(self):
        # claim_light_angle_derives_gr is both low-confidence (0.08) AND conflicted;
        # the gate's checks run in order, so confidence is caught before conflict --
        # still correctly blocked, just via the earlier-triggered check.
        self.assertEqual(self._reason("claim_light_angle_derives_gr"), gates.GateReasonCode.LOW_CONFIDENCE)


class TestQueryLayerOnAdversarialData(unittest.TestCase):
    def test_contradicting_claims_finds_the_rebuttal(self):
        graph = qih.build_stress_graph()
        found = {n.id for n in q.contradicting_claims(graph, "claim_light_angle_derives_gr")}
        self.assertEqual(found, {"claim_light_angle_unsupported"})

    def test_search_finds_qih_related_claims(self):
        graph = qih.build_stress_graph()
        found = {n.id for n in q.search(graph, "holograph")}
        self.assertIn("claim_holography_established", found)

    def test_unresolved_conflicts_lists_both(self):
        graph = qih.build_stress_graph()
        conflicts = q.unresolved_conflicts(graph)
        self.assertEqual(len(conflicts), 2)


if __name__ == "__main__":
    unittest.main()
