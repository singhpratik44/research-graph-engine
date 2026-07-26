#!/usr/bin/env python3
"""
Test suite for claim_verification.py and WorkflowGate's new claim-entailment
check (`_check_claim_entailed`, `GateReasonCode.CLAIM_NOT_ENTAILED`).

Three things this suite has to prove:
  1. The check is a true no-op by default -- every golden fixture and
     qih_stress_corpus decision written before this check existed comes out
     identical when `entailment_checker` isn't configured. This is the single
     most important guarantee here: it's what keeps ~300 pre-existing tests
     green.
  2. `keyword_overlap_entailment_checker` is a real, discriminating scorer,
     not a function that always returns the same thing -- including a
     deliberately-broken-expectation case in the style of
     test_graph_evals.py's TestQueryEvalsCatchARealBreak.
  3. The whole seam actually catches the real case that motivated it:
     qih_stress_corpus.py's claim_light_angle_derives_gr, which cites two
     real sources that don't address the mechanism it claims.
"""

import unittest
from datetime import datetime

import claim_verification as cv
import research_graph_gates as gates
import qih_stress_corpus as qih
import golden_fixtures as gf
from research_graph_schema import (
    Node, Provenance, ResearchGraph, NodeType, ExtractionMethod,
)


def _paper(pid, title, extra_text=""):
    props = {"title": title, "url": f"https://example.org/{pid}"}
    if extra_text:
        props["text"] = extra_text
    return Node(
        id=pid, type=NodeType.PAPER.value, label=title,
        provenance=Provenance(pid, ExtractionMethod.METADATA.value, 1.0,
                              datetime.now().isoformat(), human_reviewed=True),
        properties=props,
    )


def _claim(cid, paper_id, text, subject, relation, obj, conf=0.9):
    return Node(
        id=cid, type=NodeType.CLAIM.value, label=text,
        provenance=Provenance(paper_id, ExtractionMethod.STRUCTURED_LLM.value, conf,
                              datetime.now().isoformat(), human_reviewed=True),
        properties={"text": text, "subject": subject, "relation": relation, "object": obj},
    )


# ===========================================================================
# word_overlap_score / keyword_overlap_entailment_checker: unit-level
# ===========================================================================

class TestWordOverlapScore(unittest.TestCase):

    def test_plainly_matching_claim_scores_high(self):
        paper = _paper(
            "paper_orch", "Hierarchical Orchestration for Multi-Agent Fleets",
            extra_text="We show hierarchical orchestration reduces coordination "
                       "overhead across large multi-agent fleets.",
        )
        claim = _claim(
            "claim_orch", "paper_orch",
            "Hierarchical orchestration reduces coordination overhead.",
            "hierarchical orchestration", "reduces", "coordination overhead",
        )
        graph = ResearchGraph(nodes=[paper, claim])
        score = cv.word_overlap_score(claim, graph)
        self.assertGreaterEqual(score, 0.15)

    def test_light_angle_claim_scores_low_against_its_real_cited_paper(self):
        """The real case that motivated this module: QIH's central claim cites
        a real paper, but the paper is just a title with no vocabulary in
        common with the specific mechanism the claim asserts."""
        graph = qih.build_stress_graph()
        claim = graph.index()["claim_light_angle_derives_gr"]
        score = cv.word_overlap_score(claim, graph)
        self.assertLess(score, 0.15)

    def test_unrelated_claim_and_paper_score_zero(self):
        paper = _paper("paper_unrelated", "Photosynthesis in Alpine Lichen Species")
        claim = _claim(
            "claim_unrelated", "paper_unrelated",
            "Distributed consensus protocols tolerate Byzantine failures.",
            "distributed consensus", "tolerates", "Byzantine failures",
        )
        graph = ResearchGraph(nodes=[paper, claim])
        self.assertEqual(cv.word_overlap_score(claim, graph), 0.0)

    def test_missing_paper_in_graph_scores_zero_not_crash(self):
        claim = _claim(
            "claim_orphan", "paper_does_not_exist",
            "Some claim text with plenty of content words in it.",
            "subject words", "relation", "object words",
        )
        graph = ResearchGraph(nodes=[claim])  # cited paper absent
        self.assertEqual(cv.word_overlap_score(claim, graph), 0.0)

    def test_no_graph_scores_zero_not_crash(self):
        claim = _claim(
            "claim_no_graph", "paper_x",
            "Some claim text with plenty of content words in it.",
            "subject words", "relation", "object words",
        )
        self.assertEqual(cv.word_overlap_score(claim, None), 0.0)

    def test_empty_claim_text_scores_zero(self):
        claim = Node(
            id="claim_empty", type=NodeType.CLAIM.value, label="",
            provenance=Provenance("paper_x", ExtractionMethod.STRUCTURED_LLM.value, 0.9,
                                  datetime.now().isoformat(), human_reviewed=True),
            properties={"text": ""},
        )
        paper = _paper("paper_x", "Anything At All")
        graph = ResearchGraph(nodes=[claim, paper])
        self.assertEqual(cv.word_overlap_score(claim, graph), 0.0)

    def test_scorer_discriminates_not_hardcoded(self):
        """Deliberately-broken-expectation check (test_graph_evals.py style): a
        scorer that always returned e.g. 1.0 or 0.0 would pass a naive 'it runs'
        test. Prove it actually varies with real input by checking the matching
        and non-matching cases land on opposite sides of the same threshold."""
        matching_paper = _paper(
            "paper_match", "Hierarchical Orchestration Reduces Coordination Overhead",
        )
        matching_claim = _claim(
            "claim_match", "paper_match",
            "Hierarchical orchestration reduces coordination overhead.",
            "hierarchical orchestration", "reduces", "coordination overhead",
        )
        nonmatching_paper = _paper("paper_nomatch", "Photosynthesis in Alpine Lichen")
        nonmatching_claim = _claim(
            "claim_nomatch", "paper_nomatch",
            "Hierarchical orchestration reduces coordination overhead.",
            "hierarchical orchestration", "reduces", "coordination overhead",
        )
        graph = ResearchGraph(nodes=[matching_paper, matching_claim,
                                     nonmatching_paper, nonmatching_claim])
        self.assertGreater(
            cv.word_overlap_score(matching_claim, graph),
            cv.word_overlap_score(nonmatching_claim, graph),
        )


class TestKeywordOverlapEntailmentChecker(unittest.TestCase):

    def test_checker_passes_above_threshold(self):
        paper = _paper("paper_x", "Distributed Consensus Tolerates Byzantine Failures")
        claim = _claim(
            "claim_x", "paper_x",
            "Distributed consensus protocols tolerate Byzantine failures.",
            "distributed consensus", "tolerates", "Byzantine failures",
        )
        graph = ResearchGraph(nodes=[paper, claim])
        self.assertTrue(cv.keyword_overlap_entailment_checker(claim, graph))

    def test_checker_fails_below_threshold(self):
        paper = _paper("paper_y", "Photosynthesis in Alpine Lichen Species")
        claim = _claim(
            "claim_y", "paper_y",
            "Distributed consensus protocols tolerate Byzantine failures.",
            "distributed consensus", "tolerates", "Byzantine failures",
        )
        graph = ResearchGraph(nodes=[paper, claim])
        self.assertFalse(cv.keyword_overlap_entailment_checker(claim, graph))

    def test_custom_threshold_can_flip_the_verdict(self):
        """Proves threshold is a real, live parameter -- not decorative."""
        paper = _paper("paper_z", "Byzantine Failures in Distributed Systems")
        claim = _claim(
            "claim_z", "paper_z",
            "Distributed consensus protocols tolerate Byzantine failures reliably "
            "at scale across many independent regions and datacenters.",
            "distributed consensus", "tolerates", "Byzantine failures",
        )
        graph = ResearchGraph(nodes=[paper, claim])
        score = cv.word_overlap_score(claim, graph)
        self.assertTrue(cv.keyword_overlap_entailment_checker(claim, graph, threshold=score))
        self.assertFalse(cv.keyword_overlap_entailment_checker(claim, graph, threshold=score + 0.01))


# ===========================================================================
# WorkflowGate integration: the real light-angle case, positive/negative
# ===========================================================================

class TestGateCatchesTheLightAngleCase(unittest.TestCase):
    """Demonstrates the actual fix: configured with the new checker, the gate
    now holds qih_stress_corpus's central unsupported claim on entailment
    grounds -- something the pre-existing six checks could never do."""

    def setUp(self):
        self.graph = qih.build_stress_graph()
        self.claim = self.graph.index()["claim_light_angle_derives_gr"]

    def test_default_gate_does_not_catch_it_only_confidence_does(self):
        """Baseline: without the new check configured, this is exactly today's
        behavior -- held on LOW_CONFIDENCE (a human-set 0.08), not on any
        finding about the citation itself."""
        gate = gates.WorkflowGate()
        decision = gate.should_unlock_next_stage(self.claim, self.graph)
        self.assertEqual(decision.reason_code, gates.GateReasonCode.LOW_CONFIDENCE)

    def test_configured_gate_catches_it_on_entailment_grounds(self):
        """The fix: with keyword_overlap_entailment_checker configured, the gate
        now blocks this claim on CLAIM_NOT_ENTAILED -- and it does so before
        even reaching the confidence check, since entailment is checked
        earlier in the sequence."""
        gate = gates.WorkflowGate(entailment_checker=cv.keyword_overlap_entailment_checker)
        decision = gate.should_unlock_next_stage(self.claim, self.graph)
        self.assertFalse(decision.can_proceed)
        self.assertEqual(decision.reason_code, gates.GateReasonCode.CLAIM_NOT_ENTAILED)
        checked_names = [c.check_name for c in decision.checks]
        self.assertIn("claim_entailed", checked_names)
        self.assertNotIn("confidence_above_threshold", checked_names)

    def test_reverse_case_well_supported_claim_passes_entailment(self):
        """The other direction: a claim whose text plainly matches its cited
        source's content passes the entailment check (whatever else it does
        or doesn't pass)."""
        paper = _paper(
            "paper_supported",
            "Hierarchical Orchestration Reduces Coordination Overhead",
            extra_text="This paper demonstrates that hierarchical orchestration "
                       "reduces coordination overhead in large multi-agent fleets.",
        )
        claim = _claim(
            "claim_supported", "paper_supported",
            "Hierarchical orchestration reduces coordination overhead.",
            "hierarchical orchestration", "reduces", "coordination overhead",
            conf=0.9,
        )
        graph = ResearchGraph(nodes=[paper, claim])

        gate = gates.WorkflowGate(entailment_checker=cv.keyword_overlap_entailment_checker)
        decision = gate.should_unlock_next_stage(claim, graph)
        entail_check = [c for c in decision.checks if c.check_name == "claim_entailed"][0]
        self.assertTrue(entail_check.passed)
        # Claims are still terminal at the gate -- passing entailment doesn't
        # mean the overall decision is ALLOWED, just that this check didn't block it.
        self.assertEqual(decision.reason_code, gates.GateReasonCode.DOWNSTREAM_NOT_ALLOWED)


# ===========================================================================
# Backward compatibility: default (entailment_checker=None) is a true no-op
# ===========================================================================

class TestEntailmentCheckIsNoOpByDefault(unittest.TestCase):
    """The single most important guarantee in this change: every fixture and
    every qih_stress_corpus decision computed BEFORE this check existed must
    come out byte-for-byte identical when entailment_checker isn't set."""

    def test_new_check_appears_and_always_passes_when_unconfigured(self):
        gate = gates.WorkflowGate()
        for claim in [n for n in qih.build_stress_graph().nodes if n.type == NodeType.CLAIM.value]:
            graph = qih.build_stress_graph()
            decision = gate.should_unlock_next_stage(graph.index()[claim.id], graph)
            entail_checks = [c for c in decision.checks if c.check_name == "claim_entailed"]
            self.assertEqual(len(entail_checks), 1)
            self.assertTrue(entail_checks[0].passed)
            self.assertEqual(entail_checks[0].evidence.get("checked"), False)

    def test_non_claim_node_types_are_never_run_through_the_checker_even_if_configured(self):
        """A checker configured for claims must not be invoked for other node
        types -- covers the type-scoping, not just the None-default path."""
        calls = []

        def spy_checker(node, graph):
            calls.append(node.id)
            return False

        gate = gates.WorkflowGate(entailment_checker=spy_checker)
        paper = gf.build_fixture_graph().index()["paper_2606.13707"]
        decision = gate.should_unlock_next_stage(paper, gf.build_fixture_graph())
        entail_check = [c for c in decision.checks if c.check_name == "claim_entailed"][0]
        self.assertTrue(entail_check.passed)
        self.assertEqual(calls, [])  # checker never called for a non-claim node

    def test_qih_stress_corpus_reason_codes_unchanged_without_a_checker(self):
        """Re-assert every reason code test_qih_stress_corpus.py already
        expects, this time explicitly constructing the gate with
        entailment_checker=None to make the opt-in nature unmistakable."""
        graph = qih.build_stress_graph()
        gate = gates.WorkflowGate(entailment_checker=None)
        expected = {
            "claim_holography_established": gates.GateReasonCode.DOWNSTREAM_NOT_ALLOWED,
            "claim_bh_thermo_established": gates.GateReasonCode.DOWNSTREAM_NOT_ALLOWED,
            "claim_qih_self_published": gates.GateReasonCode.DOWNSTREAM_NOT_ALLOWED,
            "claim_nwqworkflow_real": gates.GateReasonCode.DOWNSTREAM_NOT_ALLOWED,
            "claim_consciousness_orch_or": gates.GateReasonCode.LOW_CONFIDENCE,
            "claim_light_angle_derives_gr": gates.GateReasonCode.LOW_CONFIDENCE,
            "claim_workflow_qih_link_unsupported": gates.GateReasonCode.LOW_CONFIDENCE,
            "claim_quantum_geometry_active": gates.GateReasonCode.LOW_CONFIDENCE,
            "claim_light_angle_unsupported": gates.GateReasonCode.CONFLICT_UNRESOLVED,
            "claim_orch_or_mainstream_rejection": gates.GateReasonCode.CONFLICT_UNRESOLVED,
        }
        idx = graph.index()
        for claim_id, reason in expected.items():
            decision = gate.should_unlock_next_stage(idx[claim_id], graph)
            self.assertEqual(decision.reason_code, reason, f"{claim_id} regressed")

    def test_golden_fixtures_reason_codes_unchanged_without_a_checker(self):
        """Same guarantee against golden_fixtures.py's four canonical states
        (mirrors test_schema.py's TestFixturesAgainstGate, explicit about the
        entailment_checker=None default this time)."""
        gate = gates.WorkflowGate(confidence_threshold=0.7, require_human_review=True,
                                  entailment_checker=None)

        d1 = gate.should_unlock_next_stage(gf.auto_pass_job())
        self.assertTrue(d1.can_proceed)
        self.assertEqual(d1.reason_code, gates.GateReasonCode.ALLOWED)

        d2 = gate.should_unlock_next_stage(gf.held_for_review_job())
        self.assertFalse(d2.can_proceed)
        self.assertEqual(d2.reason_code, gates.GateReasonCode.LOW_CONFIDENCE)

        d3 = gate.should_unlock_next_stage(gf.human_waived_job())
        self.assertFalse(d3.can_proceed)
        self.assertEqual(d3.reason_code, gates.GateReasonCode.LOW_CONFIDENCE)

        g = gf.waived_graph()
        d3b = gate.should_unlock_next_stage(g.index()["job_2606_concepts_001"], g)
        self.assertTrue(d3b.can_proceed)
        self.assertEqual(d3b.reason_code, gates.GateReasonCode.ALLOWED_BY_WAIVER)

        a, _, _ = gf.conflict_claim_pair()
        d4 = gate.should_unlock_next_stage(a)
        self.assertEqual(d4.reason_code, gates.GateReasonCode.DOWNSTREAM_NOT_ALLOWED)


# ===========================================================================
# atomic_entailment_checker / atomic_entailment_report: decomposed scoring
# ===========================================================================

class TestAtomicEntailmentChecker(unittest.TestCase):

    def test_a_single_unsupported_clause_fails_even_though_whole_text_would_pass(self):
        """Deliberate-break case, in the style of test_graph_evals.py's
        TestQueryEvalsCatchARealBreak: a compound claim where the first clause
        overlaps heavily with its source (whole-text score clears 0.15) but
        the second clause shares nothing with it -- keyword_overlap_entailment_checker
        passes this claim; atomic_entailment_checker must not."""
        paper = _paper("paper_x", "Hierarchical Orchestration Reduces Coordination "
                                  "Overhead In Distributed Systems")
        claim = _claim(
            "claim_x", "paper_x",
            "Hierarchical orchestration reduces coordination overhead in distributed "
            "systems, and quantum entanglement explains dark matter halos in spiral galaxies.",
            "hierarchical orchestration", "reduces", "coordination overhead",
        )
        g = ResearchGraph(nodes=[paper, claim])

        self.assertGreaterEqual(cv.word_overlap_score(claim, g), 0.15)
        self.assertTrue(cv.keyword_overlap_entailment_checker(claim, g))
        self.assertFalse(cv.atomic_entailment_checker(claim, g))

    def test_light_angle_claim_still_fails_under_atomic_scoring(self):
        """Parity case: the claim keyword_overlap_entailment_checker was built
        to catch must still fail under the decomposed checker, not just the
        holistic one."""
        graph = qih.build_stress_graph()
        claim = graph.index()["claim_light_angle_derives_gr"]
        self.assertFalse(cv.atomic_entailment_checker(claim, graph))

    def test_a_uniformly_well_supported_claim_passes(self):
        paper = _paper("paper_y", "Flat Routing Increases Latency At Scale")
        claim = _claim("claim_y", "paper_y",
                       "Flat routing increases latency at scale.",
                       "flat routing", "increases", "latency")
        g = ResearchGraph(nodes=[paper, claim])
        self.assertTrue(cv.atomic_entailment_checker(claim, g))

    def test_claim_with_no_atoms_is_unsupported_not_vacuously_true(self):
        claim = Node("claim_empty", NodeType.CLAIM.value, "",
                     provenance=Provenance("paper_x", ExtractionMethod.STRUCTURED_LLM.value,
                                          0.9, datetime.now().isoformat()),
                     properties={"text": ""})
        self.assertFalse(cv.atomic_entailment_checker(claim, ResearchGraph()))

    def test_custom_atom_threshold_can_flip_the_verdict(self):
        paper = _paper("paper_x", "Hierarchical Orchestration Reduces Coordination "
                                  "Overhead In Distributed Systems")
        claim = _claim(
            "claim_x", "paper_x",
            "Hierarchical orchestration reduces coordination overhead in distributed "
            "systems, and quantum entanglement explains dark matter halos in spiral galaxies.",
            "hierarchical orchestration", "reduces", "coordination overhead",
        )
        g = ResearchGraph(nodes=[paper, claim])
        # A near-zero atom_threshold lets even the weak clause through.
        self.assertTrue(cv.atomic_entailment_checker(claim, g, atom_threshold=0.0))


class TestAtomicEntailmentReport(unittest.TestCase):

    def test_report_shape_and_lengths_match(self):
        paper = _paper("paper_x", "Hierarchical Orchestration Reduces Coordination "
                                  "Overhead In Distributed Systems")
        claim = _claim(
            "claim_x", "paper_x",
            "Hierarchical orchestration reduces coordination overhead in distributed "
            "systems, and quantum entanglement explains dark matter halos in spiral galaxies.",
            "hierarchical orchestration", "reduces", "coordination overhead",
        )
        g = ResearchGraph(nodes=[paper, claim])
        report = cv.atomic_entailment_report(claim, g)
        self.assertEqual(set(report.keys()),
                         {"atoms", "scores", "atom_threshold", "weakest_atom",
                          "weakest_score", "entailed"})
        self.assertEqual(len(report["atoms"]), len(report["scores"]))
        self.assertFalse(report["entailed"])
        self.assertIn("quantum entanglement", report["weakest_atom"])
        self.assertEqual(report["weakest_score"], 0.0)

    def test_report_on_a_claim_with_no_atoms_has_none_weakest(self):
        claim = Node("claim_empty", NodeType.CLAIM.value, "",
                     provenance=Provenance("paper_x", ExtractionMethod.STRUCTURED_LLM.value,
                                          0.9, datetime.now().isoformat()),
                     properties={"text": ""})
        report = cv.atomic_entailment_report(claim, ResearchGraph())
        self.assertEqual(report["atoms"], [])
        self.assertIsNone(report["weakest_atom"])
        self.assertIsNone(report["weakest_score"])
        self.assertFalse(report["entailed"])


class TestAtomicCheckerPluggedIntoGate(unittest.TestCase):
    """atomic_entailment_checker is a drop-in Callable[[Node, Graph], bool],
    same as keyword_overlap_entailment_checker -- no research_graph_gates.py
    change needed for the CLAIM_NOT_ENTAILED-before-LOW_CONFIDENCE ordering
    to hold, since that ordering is a property of should_unlock_next_stage's
    fixed check sequence, not of which checker is configured."""

    def test_configured_gate_catches_the_compound_claim_on_entailment_grounds(self):
        paper = _paper("paper_x", "Hierarchical Orchestration Reduces Coordination "
                                  "Overhead In Distributed Systems")
        claim = _claim(
            "claim_x", "paper_x",
            "Hierarchical orchestration reduces coordination overhead in distributed "
            "systems, and quantum entanglement explains dark matter halos in spiral galaxies.",
            "hierarchical orchestration", "reduces", "coordination overhead",
            conf=0.9,
        )
        g = ResearchGraph(nodes=[paper, claim])
        gate = gates.WorkflowGate(entailment_checker=cv.atomic_entailment_checker)
        decision = gate.should_unlock_next_stage(claim, g)

        self.assertFalse(decision.can_proceed)
        self.assertEqual(decision.reason_code, gates.GateReasonCode.CLAIM_NOT_ENTAILED)
        checked_names = [c.check_name for c in decision.checks]
        self.assertIn("claim_entailed", checked_names)
        self.assertNotIn("confidence_above_threshold", checked_names)


if __name__ == "__main__":
    unittest.main(verbosity=2)
