#!/usr/bin/env python3
"""
Test suite for graph_memory.py. For every record_* function: a positive test
(the right node/edge shape lands in the graph, and graph.validate() still
passes with zero errors afterward), plus at least one deliberate-break test
per function proving a real defect would be caught -- not just that the
happy path returns something.
"""

import json
import unittest

import golden_fixtures as gf
import graph_memory as mem
import research_graph_gates as gates
import action_policy as ap
from graph_queries import _to_gate_node
from research_graph_schema import (
    EdgeType, ExtractionMethod, ExtractionType, MemoryKind, Node, NodeType, Provenance,
    ResearchGraph, export_json_schema, validate_node,
)
from task_graph import TaskSpan


def _graph():
    return gf.build_fixture_graph()


# ===========================================================================
# record_task_outcome
# ===========================================================================

class TestRecordTaskOutcome(unittest.TestCase):
    def test_records_completed_span_and_validates(self):
        g = _graph()
        span = TaskSpan(task_id="extract_claims", agent_id="claim_extractor",
                         parent_task_id=None, status="completed", confidence=0.87,
                         started_at="2026-07-26T10:00:00+00:00",
                         ended_at="2026-07-26T10:00:05+00:00")
        node = mem.record_task_outcome(g, span)

        self.assertEqual(node.type, NodeType.MEMORY_RECORD.value)
        self.assertEqual(node.properties["memory_kind"], MemoryKind.TASK_OUTCOME.value)
        self.assertEqual(node.properties["details"]["status"], "completed")
        self.assertEqual(node.provenance.extraction_method, ExtractionMethod.MEMORY_WRITE.value)
        self.assertIn(node, g.nodes)
        self.assertTrue(g.validate().valid, g.validate().to_dict())

    def test_no_dangling_edge_when_task_id_is_not_a_graph_node(self):
        """A task_graph task_id with no corresponding graph node must not produce
        a dangling DERIVED_FROM edge -- that would fail validation."""
        g = _graph()
        span = TaskSpan(task_id="some_task_dag_id_not_in_graph", agent_id="worker",
                         parent_task_id=None, status="completed", confidence=0.5,
                         started_at="t0", ended_at="t1")
        node = mem.record_task_outcome(g, span)
        derived_edges = [e for e in g.edges if e.type == EdgeType.DERIVED_FROM.value
                          and e.source == node.id]
        self.assertEqual(derived_edges, [])
        self.assertTrue(g.validate().valid)

    def test_derived_from_edge_added_when_task_id_matches_a_graph_node(self):
        g = _graph()
        span = TaskSpan(task_id="job_2606_claims_001", agent_id="claim_extractor",
                         parent_task_id=None, status="completed", confidence=0.9,
                         started_at="t0", ended_at="t1")
        node = mem.record_task_outcome(g, span)
        derived = [e for e in g.edges if e.type == EdgeType.DERIVED_FROM.value
                   and e.source == node.id]
        self.assertEqual(len(derived), 1)
        self.assertEqual(derived[0].target, "job_2606_claims_001")

    def test_failed_span_confidence_none_does_not_break_validation(self):
        """A failed task has no confidence -- must be recordable without tripping
        the OUT_OF_RANGE check that a real regression could introduce."""
        g = _graph()
        span = TaskSpan(task_id="extract_claims", agent_id="claim_extractor",
                         parent_task_id=None, status="failed", confidence=None,
                         started_at="t0", ended_at="t1", error="boom")
        node = mem.record_task_outcome(g, span)
        self.assertIsNone(node.properties["confidence"])
        r = validate_node(node)
        self.assertTrue(r.valid, r.to_dict())


# ===========================================================================
# record_claim_decision (accept + reject)
# ===========================================================================

class TestRecordClaimDecision(unittest.TestCase):
    def test_accepted_claim_gets_supported_by_edge(self):
        g = _graph()
        node = mem.record_claim_decision(
            g, "claim_2606_001", accepted=True,
            reviewed_by="parry.s.2324@gmail.com", reason="confirmed against abstract")

        self.assertEqual(node.properties["memory_kind"], MemoryKind.CLAIM_ACCEPTED.value)
        edges = [e for e in g.edges if e.type == EdgeType.SUPPORTED_BY.value]
        self.assertEqual(len(edges), 1)
        self.assertEqual(edges[0].source, "claim_2606_001")
        self.assertEqual(edges[0].target, node.id)
        self.assertTrue(g.validate().valid, g.validate().to_dict())

    def test_rejected_claim_gets_rejected_because_edge(self):
        g = _graph()
        node = mem.record_claim_decision(
            g, "claim_2701_014", accepted=False,
            reviewed_by="parry.s.2324@gmail.com", reason="citation does not entail the claim")

        self.assertEqual(node.properties["memory_kind"], MemoryKind.CLAIM_REJECTED.value)
        edges = [e for e in g.edges if e.type == EdgeType.REJECTED_BECAUSE.value]
        self.assertEqual(len(edges), 1)
        self.assertEqual(edges[0].source, "claim_2701_014")
        self.assertEqual(edges[0].target, node.id)
        self.assertTrue(g.validate().valid, g.validate().to_dict())

    def test_unknown_claim_id_raises(self):
        g = _graph()
        with self.assertRaises(KeyError):
            mem.record_claim_decision(g, "claim_does_not_exist", accepted=True,
                                       reviewed_by="x", reason="y")

    def test_edge_endpoint_contract_would_catch_a_wrong_direction(self):
        """Prove the new EDGE_ENDPOINT_CONTRACT entries actually constrain
        SUPPORTED_BY/REJECTED_BECAUSE -- reversing source/target must fail
        validation, not silently pass."""
        from research_graph_schema import Edge, validate_edge
        g = _graph()
        node = mem.record_claim_decision(g, "claim_2606_001", accepted=True,
                                          reviewed_by="x", reason="y")
        backwards = Edge(node.id, "claim_2606_001", EdgeType.SUPPORTED_BY.value)
        self.assertFalse(validate_edge(backwards, g.index()).valid)

    def test_confidence_defaults_to_the_claims_own_confidence(self):
        g = _graph()
        claim = g.index()["claim_2606_001"]
        node = mem.record_claim_decision(g, "claim_2606_001", accepted=True,
                                          reviewed_by="x", reason="y")
        self.assertEqual(node.properties["confidence"], claim.provenance.confidence)


# ===========================================================================
# record_disagreement
# ===========================================================================

class TestRecordDisagreement(unittest.TestCase):
    def test_records_disagreement_and_links_disagreed_on(self):
        g = _graph()
        node = mem.record_disagreement(
            g, "claim_2701_014", reviewer_a="alice", verdict_a="accept",
            reviewer_b="bob", verdict_b="reject", note="scope-dependent, per alice")

        self.assertEqual(node.properties["memory_kind"], MemoryKind.REVIEWER_DISAGREEMENT.value)
        self.assertEqual(node.properties["details"]["reviewer_a"], "alice")
        self.assertEqual(node.properties["details"]["verdict_b"], "reject")
        edges = [e for e in g.edges if e.type == EdgeType.DISAGREED_ON.value]
        self.assertEqual(len(edges), 1)
        self.assertEqual(edges[0].source, node.id)
        self.assertEqual(edges[0].target, "claim_2701_014")
        self.assertTrue(g.validate().valid, g.validate().to_dict())

    def test_unknown_node_id_raises(self):
        g = _graph()
        with self.assertRaises(KeyError):
            mem.record_disagreement(g, "nope", "alice", "accept", "bob", "reject")

    def test_disagreement_can_target_any_node_type(self):
        """DISAGREED_ON deliberately has no EDGE_ENDPOINT_CONTRACT entry -- prove
        it works against a non-claim node type (an extraction_job here)."""
        g = _graph()
        node = mem.record_disagreement(g, "job_2606_claims_001", "alice", "hold",
                                        "bob", "approve")
        self.assertTrue(g.validate().valid)
        self.assertEqual(g.index()[node.id].type, NodeType.MEMORY_RECORD.value)


# ===========================================================================
# record_confidence_divergence / confidence_divergence_for
# ===========================================================================

class TestRecordConfidenceDivergence(unittest.TestCase):
    def test_records_divergence_and_links_derived_from(self):
        g = _graph()
        node = mem.record_confidence_divergence(
            g, "claim_2606_001", derivation_confidence=0.91,
            validation_confidence=0.4, note="re-run scored much lower")

        self.assertEqual(node.properties["memory_kind"],
                         MemoryKind.CONFIDENCE_DIVERGENCE.value)
        self.assertEqual(node.properties["details"]["derivation_confidence"], 0.91)
        self.assertEqual(node.properties["details"]["validation_confidence"], 0.4)
        self.assertAlmostEqual(node.properties["confidence"], 0.4)
        edges = [e for e in g.edges if e.type == EdgeType.DERIVED_FROM.value
                and e.source == node.id]
        self.assertEqual(len(edges), 1)
        self.assertEqual(edges[0].target, "claim_2606_001")
        self.assertTrue(g.validate().valid, g.validate().to_dict())

    def test_unknown_node_id_raises(self):
        g = _graph()
        with self.assertRaises(KeyError):
            mem.record_confidence_divergence(g, "nope", 0.9, 0.2)


class TestConfidenceDivergenceFor(unittest.TestCase):
    def test_finds_recorded_divergence(self):
        g = _graph()
        mem.record_confidence_divergence(g, "claim_2606_001", 0.91, 0.4)
        found = mem.confidence_divergence_for(g, "claim_2606_001")
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0].properties["memory_kind"],
                         MemoryKind.CONFIDENCE_DIVERGENCE.value)

    def test_does_not_return_other_memory_kinds_sharing_derived_from(self):
        """DERIVED_FROM is shared with TASK_OUTCOME/BLOCKED_REASON/REPAIR_PATTERN --
        confidence_divergence_for must filter by memory_kind, not just edge type,
        or it would silently return unrelated records pointed at the same node."""
        g = _graph()
        mem.record_task_outcome(g, TaskSpan(
            task_id="claim_2606_001", agent_id="a", parent_task_id=None,
            status="completed", confidence=0.8,
            started_at="2026-07-27T00:00:00+00:00", ended_at="2026-07-27T00:00:01+00:00",
        ))
        found = mem.confidence_divergence_for(g, "claim_2606_001")
        self.assertEqual(found, [])

    def test_no_divergence_recorded_returns_empty(self):
        g = _graph()
        self.assertEqual(mem.confidence_divergence_for(g, "claim_2606_001"), [])


# ===========================================================================
# record_blocked_reason
# ===========================================================================

class TestRecordBlockedReason(unittest.TestCase):
    def _blocked_decision(self, graph):
        gate = gates.WorkflowGate(confidence_threshold=0.7, require_human_review=True)
        return gate.should_unlock_next_stage(
            _to_gate_node(graph.index()["job_2606_concepts_001"]), graph)

    def test_persists_reason_and_links_derived_from(self):
        g = _graph()
        decision = self._blocked_decision(g)
        self.assertFalse(decision.can_proceed)  # sanity: fixture 2 really is blocked

        node = mem.record_blocked_reason(g, decision)
        self.assertEqual(node.properties["memory_kind"], MemoryKind.BLOCKED_REASON.value)
        self.assertEqual(node.properties["details"]["reason_code"],
                         gates.GateReasonCode.LOW_CONFIDENCE.value)
        edges = [e for e in g.edges if e.type == EdgeType.DERIVED_FROM.value
                 and e.source == node.id]
        self.assertEqual(len(edges), 1)
        self.assertEqual(edges[0].target, "job_2606_concepts_001")
        self.assertTrue(g.validate().valid, g.validate().to_dict())

    def test_allowed_decision_raises_instead_of_recording_nothing(self):
        """A GateDecision that actually passed must not be recorded as a
        'blocked reason' -- that would be a silently wrong memory record."""
        g = _graph()
        gate = gates.WorkflowGate()
        decision = gate.should_unlock_next_stage(_to_gate_node(gf.auto_pass_job()))
        self.assertTrue(decision.can_proceed)
        with self.assertRaises(ValueError):
            mem.record_blocked_reason(g, decision)

    def test_confidence_pulled_from_the_confidence_check_evidence(self):
        g = _graph()
        decision = self._blocked_decision(g)
        node = mem.record_blocked_reason(g, decision)
        self.assertEqual(node.properties["confidence"], 0.59)


# ===========================================================================
# record_repair_pattern
# ===========================================================================

class TestRecordRepairPattern(unittest.TestCase):
    def test_links_repaired_via_and_derived_from(self):
        g = _graph()
        node = mem.record_repair_pattern(
            g, description="re-extracted with a tighter confidence floor",
            before_node_id="job_2606_concepts_001", after_node_id="job_2606_claims_001")

        self.assertEqual(node.properties["memory_kind"], MemoryKind.REPAIR_PATTERN.value)
        repaired = [e for e in g.edges if e.type == EdgeType.REPAIRED_VIA.value]
        self.assertEqual(len(repaired), 1)
        self.assertEqual(repaired[0].source, "job_2606_claims_001")
        self.assertEqual(repaired[0].target, node.id)

        derived = [e for e in g.edges if e.type == EdgeType.DERIVED_FROM.value
                   and e.source == node.id]
        self.assertEqual(len(derived), 1)
        self.assertEqual(derived[0].target, "job_2606_concepts_001")
        self.assertTrue(g.validate().valid, g.validate().to_dict())

    def test_unknown_after_node_raises(self):
        g = _graph()
        with self.assertRaises(KeyError):
            mem.record_repair_pattern(g, "desc", "job_2606_concepts_001", "nope")

    def test_before_node_id_need_not_exist_in_graph(self):
        """A repair might reference a before-state that was never itself a
        surviving graph node (e.g. a rejected envelope that was never admitted).
        Must not raise, and must not create a dangling edge."""
        g = _graph()
        node = mem.record_repair_pattern(
            g, description="fixed", before_node_id="envelope_never_admitted",
            after_node_id="job_2606_claims_001")
        dangling = [e for e in g.edges if e.target == "envelope_never_admitted"]
        self.assertEqual(dangling, [])
        self.assertTrue(g.validate().valid)


# ===========================================================================
# Read functions
# ===========================================================================

class TestReadFunctions(unittest.TestCase):
    def test_memory_records_for_finds_only_matching_subject(self):
        g = _graph()
        mem.record_claim_decision(g, "claim_2606_001", accepted=True,
                                   reviewed_by="x", reason="y")
        mem.record_claim_decision(g, "claim_2701_014", accepted=False,
                                   reviewed_by="x", reason="z")
        found = mem.memory_records_for(g, "claim_2606_001")
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0].properties["subject_ref"], "claim_2606_001")

    def test_prior_disagreements_on_returns_only_disagreements_on_that_node(self):
        g = _graph()
        mem.record_disagreement(g, "claim_2701_014", "alice", "accept", "bob", "reject")
        mem.record_disagreement(g, "job_2606_claims_001", "alice", "hold", "bob", "approve")
        found = mem.prior_disagreements_on(g, "claim_2701_014")
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0].properties["details"]["reviewer_a"], "alice")
        self.assertEqual(found[0].properties["details"]["node_id"], "claim_2701_014")

    def test_prior_disagreements_on_empty_when_none_recorded(self):
        g = _graph()
        self.assertEqual(mem.prior_disagreements_on(g, "claim_2606_001"), [])

    def test_repair_patterns_for_filters_by_after_node_type(self):
        g = _graph()
        mem.record_repair_pattern(g, "fixed a job", "job_2606_concepts_001",
                                   "job_2606_claims_001")
        mem.record_repair_pattern(g, "fixed a claim", "claim_2701_014", "claim_2606_001")

        jobs_only = mem.repair_patterns_for(g, NodeType.EXTRACTION_JOB.value)
        claims_only = mem.repair_patterns_for(g, NodeType.CLAIM.value)
        everything = mem.repair_patterns_for(g)

        self.assertEqual(len(jobs_only), 1)
        self.assertEqual(len(claims_only), 1)
        self.assertEqual(len(everything), 2)
        self.assertEqual(jobs_only[0].properties["details"]["after_node_id"],
                         "job_2606_claims_001")

    def test_repair_patterns_for_would_catch_a_wrong_filter(self):
        """Deliberately ask for the wrong node type and prove the filter
        actually excludes, rather than always returning everything."""
        g = _graph()
        mem.record_repair_pattern(g, "fixed a job", "job_2606_concepts_001",
                                   "job_2606_claims_001")
        self.assertEqual(mem.repair_patterns_for(g, NodeType.CONCEPT.value), [])

    def test_read_functions_never_mutate_the_graph(self):
        g = _graph()
        mem.record_disagreement(g, "claim_2606_001", "alice", "accept", "bob", "reject")

        def _snapshot(graph):
            # generated_at is a call-time timestamp, not graph state -- exclude it.
            d = graph.to_dict()
            d.pop("generated_at", None)
            return json.dumps(d, sort_keys=True)

        before = _snapshot(g)
        mem.memory_records_for(g, "claim_2606_001")
        mem.prior_disagreements_on(g, "claim_2606_001")
        mem.repair_patterns_for(g)
        after = _snapshot(g)
        self.assertEqual(before, after)


# ===========================================================================
# specialist_trust_scores / trust_score_for
# ===========================================================================

class TestRecordActionPolicyDecision(unittest.TestCase):
    def _decision(self, verdict=ap.PolicyVerdict.BLOCKED):
        action = ap.ProposedAction("paper_x", ExtractionType.CLAIMS)
        return ap.PolicyDecision(verdict=verdict, reason="test reason",
                                 rule_name="test_rule", action=action)

    def test_records_without_requiring_subject_to_exist(self):
        """A BLOCKED action never produces a node -- unlike every other
        record_* function, subject_ref must NOT be required to already
        exist in the graph."""
        g = ResearchGraph()
        node = mem.record_action_policy_decision(g, "action_synthetic_id", self._decision())
        self.assertEqual(node.properties["memory_kind"], MemoryKind.ACTION_POLICY_DECISION.value)
        self.assertEqual(node.properties["details"]["verdict"], "blocked")
        self.assertTrue(g.validate().valid, g.validate().to_dict())
        # No DERIVED_FROM edge, since the subject never existed.
        self.assertEqual([e for e in g.edges if e.type == EdgeType.DERIVED_FROM.value], [])

    def test_links_derived_from_when_subject_resolves_to_a_real_node(self):
        g = _graph()
        node = mem.record_action_policy_decision(
            g, "job_2606_claims_001", self._decision(ap.PolicyVerdict.ALLOWED))
        edges = [e for e in g.edges if e.type == EdgeType.DERIVED_FROM.value
                and e.source == node.id]
        self.assertEqual(len(edges), 1)
        self.assertEqual(edges[0].target, "job_2606_claims_001")


class TestActionPolicyDecisionsFor(unittest.TestCase):
    def test_finds_recorded_decision(self):
        g = ResearchGraph()
        decision = ap.PolicyDecision(
            verdict=ap.PolicyVerdict.ESCALATED, reason="r", rule_name="rule",
            action=ap.ProposedAction("paper_x", ExtractionType.CLAIMS))
        mem.record_action_policy_decision(g, "action_1", decision)
        found = mem.action_policy_decisions_for(g, "action_1")
        self.assertEqual(len(found), 1)

    def test_no_recorded_decision_returns_empty(self):
        g = ResearchGraph()
        self.assertEqual(mem.action_policy_decisions_for(g, "nope"), [])


class TestSpecialistTrustScores(unittest.TestCase):
    def test_role_whose_verdict_matched_the_eventual_outcome_gets_full_trust(self):
        g = _graph()
        # job_2606_claims_001's status is "completed" per golden_fixtures.
        mem.record_disagreement(g, "job_2606_claims_001",
                                reviewer_a="schema_validator", verdict_a="pass",
                                reviewer_b="conflict_checker", verdict_b="fail")
        scores = mem.specialist_trust_scores(g)
        self.assertEqual(scores["schema_validator"]["agreements"], 1)
        self.assertEqual(scores["schema_validator"]["disagreements"], 0)
        self.assertAlmostEqual(scores["schema_validator"]["trust_score"], 1.0)
        self.assertEqual(scores["conflict_checker"]["disagreements"], 1)
        self.assertAlmostEqual(scores["conflict_checker"]["trust_score"], 0.0)
        self.assertEqual(mem.trust_score_for(g, "schema_validator"), 1.0)

    def test_undecided_outcome_never_falsely_counts_as_a_disagreement(self):
        """job_2606_concepts_001's status is "held" -- not completed/approved/
        failed/rejected -- so neither reviewer should be blamed or credited
        before the outcome actually exists."""
        g = _graph()
        mem.record_disagreement(g, "job_2606_concepts_001",
                                reviewer_a="schema_validator", verdict_a="pass",
                                reviewer_b="conflict_checker", verdict_b="fail")
        scores = mem.specialist_trust_scores(g)
        self.assertEqual(scores["schema_validator"]["agreements"], 0)
        self.assertEqual(scores["schema_validator"]["disagreements"], 0)
        self.assertEqual(scores["schema_validator"]["undecided"], 1)
        self.assertIsNone(scores["schema_validator"]["trust_score"])
        self.assertIsNone(mem.trust_score_for(g, "conflict_checker"))

    def test_unknown_role_returns_none_not_a_key_error(self):
        g = _graph()
        self.assertIsNone(mem.trust_score_for(g, "nobody_ever_recorded"))


# ===========================================================================
# provenance_trust_weight_for / provenance_bound_confidence
# ===========================================================================

class TestProvenanceTrustWeight(unittest.TestCase):
    def test_human_annotation_gets_full_weight(self):
        node = Node("n1", "claim", "x",
                    Provenance("p", ExtractionMethod.HUMAN_ANNOTATION.value, 0.9, "t"))
        self.assertEqual(mem.provenance_trust_weight_for(node), 1.0)

    def test_memory_write_gets_a_low_weight(self):
        node = Node("n1", "claim", "x",
                    Provenance("p", ExtractionMethod.MEMORY_WRITE.value, 0.9, "t"))
        self.assertEqual(mem.provenance_trust_weight_for(node), 0.3)

    def test_missing_provenance_gets_the_conservative_default_not_full_trust(self):
        node = Node("n1", "claim", "x", None)
        self.assertEqual(mem.provenance_trust_weight_for(node),
                          mem._DEFAULT_PROVENANCE_TRUST_WEIGHT)

    def test_unmapped_extraction_method_gets_the_conservative_default(self):
        node = Node("n1", "claim", "x", Provenance("p", "some_future_method", 0.9, "t"))
        self.assertEqual(mem.provenance_trust_weight_for(node),
                          mem._DEFAULT_PROVENANCE_TRUST_WEIGHT)


class TestProvenanceBoundConfidence(unittest.TestCase):
    def test_caps_self_reported_confidence_by_source_weight(self):
        node = Node("n1", "claim", "x",
                    Provenance("p", ExtractionMethod.STRUCTURED_LLM.value, 0.9, "t"))
        self.assertAlmostEqual(mem.provenance_bound_confidence(node), 0.63)  # 0.9 * 0.7

    def test_human_annotation_confidence_is_effectively_unbounded(self):
        node = Node("n1", "claim", "x",
                    Provenance("p", ExtractionMethod.HUMAN_ANNOTATION.value, 0.9, "t"))
        self.assertAlmostEqual(mem.provenance_bound_confidence(node), 0.9)

    def test_no_confidence_reading_returns_none_not_zero(self):
        node = Node("n1", "claim", "x",
                    Provenance("p", ExtractionMethod.HUMAN_ANNOTATION.value, None, "t"))
        self.assertIsNone(mem.provenance_bound_confidence(node))


# ===========================================================================
# provenance_weighted_trust_scores
# ===========================================================================

class TestProvenanceWeightedTrustScores(unittest.TestCase):
    def test_weight_matches_the_disputed_nodes_own_provenance(self):
        # job_2606_claims_001's provenance defaults to ExtractionMethod.JOB_SPAWN
        # (weight 0.3, golden_fixtures._prov's default) and its status is
        # completed -- schema_validator's "pass" verdict matches that outcome.
        g = _graph()
        mem.record_disagreement(g, "job_2606_claims_001",
                                reviewer_a="schema_validator", verdict_a="pass",
                                reviewer_b="conflict_checker", verdict_b="fail")
        scores = mem.provenance_weighted_trust_scores(g)
        self.assertAlmostEqual(scores["schema_validator"]["weighted_agreements"], 0.3)
        self.assertAlmostEqual(scores["schema_validator"]["weighted_trust_score"], 1.0)
        self.assertAlmostEqual(scores["conflict_checker"]["weighted_disagreements"], 0.3)
        self.assertAlmostEqual(scores["conflict_checker"]["weighted_trust_score"], 0.0)

    def test_does_not_change_specialist_trust_scores_own_arithmetic(self):
        g = _graph()
        mem.record_disagreement(g, "job_2606_claims_001",
                                reviewer_a="schema_validator", verdict_a="pass",
                                reviewer_b="conflict_checker", verdict_b="fail")
        flat = mem.specialist_trust_scores(g)
        self.assertEqual(flat["schema_validator"]["agreements"], 1)
        self.assertAlmostEqual(flat["schema_validator"]["trust_score"], 1.0)

    def test_undecided_outcome_is_not_weighted_either_way(self):
        g = _graph()
        mem.record_disagreement(g, "job_2606_concepts_001",
                                reviewer_a="schema_validator", verdict_a="pass",
                                reviewer_b="conflict_checker", verdict_b="fail")
        scores = mem.provenance_weighted_trust_scores(g)
        self.assertEqual(scores["schema_validator"]["undecided"], 1)
        self.assertIsNone(scores["schema_validator"]["weighted_trust_score"])


# ===========================================================================
# retract_memory_record / is_retracted / active_memory_records_for
# ===========================================================================

class TestRetractMemoryRecord(unittest.TestCase):
    def test_retraction_links_derived_from_and_validates(self):
        g = _graph()
        record = mem.record_disagreement(g, "job_2606_claims_001", "alice", "accept", "bob", "reject")
        retraction = mem.retract_memory_record(g, record.id, retracted_by="carol",
                                               reason="source later found poisoned")
        self.assertEqual(retraction.properties["memory_kind"], MemoryKind.MEMORY_RETRACTED.value)
        derived = [e for e in g.edges if e.type == EdgeType.DERIVED_FROM.value
                   and e.source == retraction.id]
        self.assertEqual(len(derived), 1)
        self.assertEqual(derived[0].target, record.id)
        self.assertTrue(g.validate().valid, g.validate().to_dict())

    def test_unknown_record_id_raises(self):
        g = _graph()
        with self.assertRaises(KeyError):
            mem.retract_memory_record(g, "no_such_record", "carol", "reason")

    def test_non_memory_record_node_raises(self):
        g = _graph()
        with self.assertRaises(ValueError):
            mem.retract_memory_record(g, "job_2606_claims_001", "carol", "reason")

    def test_original_record_is_never_mutated(self):
        g = _graph()
        record = mem.record_disagreement(g, "job_2606_claims_001", "alice", "accept", "bob", "reject")
        original_props = dict(record.properties)
        mem.retract_memory_record(g, record.id, "carol", "reason")
        self.assertEqual(record.properties, original_props)


class TestIsRetracted(unittest.TestCase):
    def test_false_before_retraction(self):
        g = _graph()
        record = mem.record_disagreement(g, "job_2606_claims_001", "alice", "accept", "bob", "reject")
        self.assertFalse(mem.is_retracted(g, record.id))

    def test_true_after_retraction(self):
        g = _graph()
        record = mem.record_disagreement(g, "job_2606_claims_001", "alice", "accept", "bob", "reject")
        mem.retract_memory_record(g, record.id, "carol", "reason")
        self.assertTrue(mem.is_retracted(g, record.id))

    def test_unrelated_derived_from_edge_does_not_falsely_flag_retraction(self):
        """A CONFIDENCE_DIVERGENCE record also uses DERIVED_FROM -- retraction
        detection must filter by memory_kind, not just edge type/target."""
        g = _graph()
        record = mem.record_disagreement(g, "job_2606_claims_001", "alice", "accept", "bob", "reject")
        mem.record_confidence_divergence(g, "job_2606_claims_001", 0.5, 0.9)
        self.assertFalse(mem.is_retracted(g, record.id))


class TestActiveMemoryRecordsFor(unittest.TestCase):
    def test_excludes_retracted_records(self):
        g = _graph()
        record = mem.record_disagreement(g, "job_2606_claims_001", "alice", "accept", "bob", "reject")
        mem.retract_memory_record(g, record.id, "carol", "reason")
        active = mem.active_memory_records_for(g, "job_2606_claims_001")
        self.assertNotIn(record, active)

    def test_includes_non_retracted_records(self):
        g = _graph()
        record = mem.record_disagreement(g, "job_2606_claims_001", "alice", "accept", "bob", "reject")
        active = mem.active_memory_records_for(g, "job_2606_claims_001")
        self.assertIn(record, active)


class TestRetractionExcludedFromTrustScores(unittest.TestCase):
    def test_retracted_disagreement_no_longer_counts(self):
        g = _graph()
        record = mem.record_disagreement(g, "job_2606_claims_001",
                                         reviewer_a="schema_validator", verdict_a="pass",
                                         reviewer_b="conflict_checker", verdict_b="fail")
        mem.retract_memory_record(g, record.id, "carol", "source later found poisoned")
        self.assertNotIn("schema_validator", mem.specialist_trust_scores(g))
        self.assertNotIn("schema_validator", mem.provenance_weighted_trust_scores(g))


# ===========================================================================
# Everything together: a graph that has recorded all five/six memory kinds
# still validates cleanly, and the published JSON schema matches.
# ===========================================================================

class TestFullMemoryGraphValidates(unittest.TestCase):
    def test_all_recording_functions_together_leave_a_valid_graph(self):
        g = _graph()
        span = TaskSpan(task_id="job_2606_claims_001", agent_id="claim_extractor",
                         parent_task_id=None, status="completed", confidence=0.9,
                         started_at="t0", ended_at="t1")
        mem.record_task_outcome(g, span)
        mem.record_claim_decision(g, "claim_2606_001", accepted=True,
                                   reviewed_by="x", reason="confirmed")
        mem.record_claim_decision(g, "claim_2701_014", accepted=False,
                                   reviewed_by="x", reason="not entailed")
        mem.record_disagreement(g, "claim_2701_014", "alice", "accept", "bob", "reject")
        gate = gates.WorkflowGate()
        decision = gate.should_unlock_next_stage(
            _to_gate_node(g.index()["job_2606_concepts_001"]), g)
        mem.record_blocked_reason(g, decision)
        mem.record_repair_pattern(g, "re-extracted", "job_2606_concepts_001",
                                   "job_2606_claims_001")

        result = g.validate()
        self.assertTrue(result.valid, json.dumps(result.to_dict(), indent=2))
        memory_nodes = [n for n in g.nodes if n.type == NodeType.MEMORY_RECORD.value]
        self.assertEqual(len(memory_nodes), 6)

    def test_a_broken_memory_node_would_be_caught(self):
        """Prove validate() would catch a real defect: an invalid memory_kind."""
        g = _graph()
        node = mem.record_claim_decision(g, "claim_2606_001", accepted=True,
                                          reviewed_by="x", reason="y")
        node.properties["memory_kind"] = "not_a_real_kind"
        result = g.validate()
        self.assertFalse(result.valid)
        self.assertIn("NOT_IN_ENUM", result.codes)


class TestPublishedSchemaCoversNewTypes(unittest.TestCase):
    def test_new_edge_types_appear_in_exported_schema(self):
        schema = export_json_schema()
        edge_enum = schema["definitions"]["edge"]["properties"]["type"]["enum"]
        for et in ("supported_by", "rejected_because", "disagreed_on",
                   "repaired_via", "derived_from"):
            self.assertIn(et, edge_enum)

    def test_new_node_type_appears_in_exported_schema(self):
        schema = export_json_schema()
        node_enum = schema["definitions"]["node"]["properties"]["type"]["enum"]
        self.assertIn(NodeType.MEMORY_RECORD.value, node_enum)
        self.assertIn("props_memory_record", schema["definitions"])

    def test_endpoint_contract_exported_for_the_new_memory_control_edges(self):
        schema = export_json_schema()
        contract = schema["x-edge-endpoint-contract"]
        self.assertEqual(contract["supported_by"],
                         {"source": ["claim"], "target": ["memory_record"]})
        self.assertEqual(contract["rejected_because"],
                         {"source": ["claim"], "target": ["memory_record"]})
        # Deliberately not constrained -- any node type can be disagreed on/repaired.
        self.assertNotIn("disagreed_on", contract)
        self.assertNotIn("repaired_via", contract)
        self.assertNotIn("derived_from", contract)


if __name__ == "__main__":
    unittest.main(verbosity=2)
