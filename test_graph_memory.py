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
from graph_queries import _to_gate_node
from research_graph_schema import (
    EdgeType, ExtractionMethod, MemoryKind, NodeType, ResearchGraph,
    export_json_schema, validate_node,
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
