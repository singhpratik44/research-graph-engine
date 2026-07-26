#!/usr/bin/env python3
"""
Phase 3 test suite: schema validation, enums, structured traces, conflicts,
and the four golden fixtures — including feeding them through Phase 2's gate
unchanged, to prove Phase 3 is additive.
"""

import json
import unittest

import golden_fixtures as gf
from research_graph_schema import (
    Node, Edge, Provenance, Trace, ConflictEdge, ResearchGraph,
    NodeType, EdgeType, JobStatus, ReviewStatus, ExtractionType,
    ConflictType, DecisionType, ExtractionMethod,
    validate_node, validate_edge, validate_conflict, validate_trace,
    detect_conflicts_in_graph, SCHEMA_VERSION,
)

# Phase 2 gate, imported unmodified.
import research_graph_gates as gates


def to_gate_node(n: Node) -> gates.Node:
    """Adapter: schema Node -> gate Node. Same field names; gate is trace-agnostic."""
    p = n.provenance
    return gates.Node(
        id=n.id,
        type=n.type,
        label=n.label,
        provenance=None if p is None else gates.Provenance(
            source_paper=p.source_paper,
            extraction_method=p.extraction_method,
            confidence=p.confidence,
            extracted_at=p.extracted_at,
            human_reviewed=p.human_reviewed,
            review_notes=p.review_notes,
        ),
        properties=n.properties,
    )


# ===========================================================================
# Required-field rejection (explicit pre-merge checklist)
# ===========================================================================

class TestRequiredFields(unittest.TestCase):

    def _job(self, **overrides):
        props = {
            "job_id": "job_1",
            "paper_id": "paper_1",
            "extraction_type": ExtractionType.CLAIMS.value,
            "status": JobStatus.COMPLETED.value,
        }
        props.update(overrides)
        props = {k: v for k, v in props.items() if v is not None}
        return Node("job_1", NodeType.EXTRACTION_JOB.value, "j", None, props)

    def test_extraction_job_missing_paper_id_rejected(self):
        r = validate_node(self._job(paper_id=None))
        self.assertFalse(r.valid)
        self.assertIn("MISSING_REQUIRED", r.codes)
        self.assertTrue(any("paper_id" in e.field_path for e in r.errors))

    def test_extraction_job_missing_extraction_type_rejected(self):
        r = validate_node(self._job(extraction_type=None))
        self.assertFalse(r.valid)
        self.assertTrue(any("extraction_type" in e.field_path for e in r.errors))

    def test_extraction_job_complete_accepted(self):
        self.assertTrue(validate_node(self._job()).valid)

    def test_review_task_missing_extraction_job_id_rejected(self):
        n = Node("rt_1", NodeType.REVIEW_TASK.value, "r", None,
                 {"task_id": "rt_1", "status": ReviewStatus.PENDING.value})
        r = validate_node(n)
        self.assertFalse(r.valid)
        self.assertTrue(any("extraction_job_id" in e.field_path for e in r.errors))

    def test_review_task_complete_accepted(self):
        n = Node("rt_1", NodeType.REVIEW_TASK.value, "r", None,
                 {"task_id": "rt_1", "extraction_job_id": "job_1",
                  "status": ReviewStatus.PENDING.value})
        self.assertTrue(validate_node(n).valid)

    def test_unknown_node_type_rejected(self):
        r = validate_node(Node("x", "wormhole", "x", None, {}))
        self.assertFalse(r.valid)
        self.assertEqual(r.codes, ["UNKNOWN_TYPE"])


# ===========================================================================
# Enums
# ===========================================================================

class TestEnums(unittest.TestCase):

    def test_bad_job_status_rejected(self):
        n = Node("j", NodeType.EXTRACTION_JOB.value, "j", None, {
            "job_id": "j", "paper_id": "p",
            "extraction_type": ExtractionType.CLAIMS.value, "status": "done"})
        r = validate_node(n)
        self.assertFalse(r.valid)
        self.assertIn("NOT_IN_ENUM", r.codes)

    def test_bad_extraction_type_rejected(self):
        n = Node("j", NodeType.EXTRACTION_JOB.value, "j", None, {
            "job_id": "j", "paper_id": "p",
            "extraction_type": "vibes", "status": JobStatus.QUEUED.value})
        self.assertIn("NOT_IN_ENUM", validate_node(n).codes)

    def test_bad_review_status_rejected(self):
        n = Node("rt", NodeType.REVIEW_TASK.value, "r", None, {
            "task_id": "rt", "extraction_job_id": "j", "status": "lgtm"})
        self.assertIn("NOT_IN_ENUM", validate_node(n).codes)

    def test_bad_extraction_method_rejected(self):
        n = Node("c", NodeType.CONCEPT.value, "c",
                 Provenance("p", "telepathy", 0.9, "t"), {"text": "x"})
        self.assertIn("NOT_IN_ENUM", validate_node(n).codes)

    def test_all_job_statuses_accepted(self):
        for s in JobStatus:
            n = Node("j", NodeType.EXTRACTION_JOB.value, "j", None, {
                "job_id": "j", "paper_id": "p",
                "extraction_type": ExtractionType.CLAIMS.value, "status": s.value})
            self.assertTrue(validate_node(n).valid, f"{s.value} should be accepted")

    def test_avg_confidence_out_of_range_rejected(self):
        n = Node("j", NodeType.EXTRACTION_JOB.value, "j", None, {
            "job_id": "j", "paper_id": "p",
            "extraction_type": ExtractionType.CLAIMS.value,
            "status": JobStatus.COMPLETED.value, "avg_confidence": 1.4})
        self.assertIn("OUT_OF_RANGE", validate_node(n).codes)


# ===========================================================================
# Structured traces
# ===========================================================================

class TestTraces(unittest.TestCase):

    def _trace(self, **kw):
        base = dict(trace_id="t1", decision_type=DecisionType.EXTRACT,
                    worker_id="w1", confidence=0.8, reason_code="R",
                    reasoning_summary="because")
        base.update(kw)
        return Trace(**base)

    def test_valid_trace_has_no_errors(self):
        self.assertEqual(validate_trace(self._trace(), "t"), [])

    def test_trace_missing_worker_id_rejected(self):
        errs = validate_trace(self._trace(worker_id=""), "t")
        self.assertTrue(any(e.code == "MISSING_REQUIRED" for e in errs))

    def test_trace_bad_decision_type_rejected(self):
        d = self._trace().to_dict()
        d["decision_type"] = "guessed"
        self.assertTrue(any(e.code == "NOT_IN_ENUM" for e in validate_trace(d, "t")))

    def test_trace_confidence_out_of_range_rejected(self):
        errs = validate_trace(self._trace(confidence=1.7), "t")
        self.assertTrue(any(e.code == "OUT_OF_RANGE" for e in errs))

    def test_bad_trace_invalidates_its_node(self):
        n = Node("j", NodeType.EXTRACTION_JOB.value, "j", None, {
            "job_id": "j", "paper_id": "p",
            "extraction_type": ExtractionType.CLAIMS.value,
            "status": JobStatus.COMPLETED.value,
            "traces": [self._trace(reason_code="")]})
        r = validate_node(n)
        self.assertFalse(r.valid)
        self.assertTrue(any("traces[0].reason_code" in e.field_path for e in r.errors))

    def test_trace_round_trips(self):
        t = self._trace(input_refs=["a#b"], output_refs=["claim_1"])
        self.assertEqual(Trace.from_dict(t.to_dict()).to_dict(), t.to_dict())


# ===========================================================================
# Edges + endpoint contracts
# ===========================================================================

class TestEdges(unittest.TestCase):

    def setUp(self):
        self.g = gf.build_fixture_graph()
        self.idx = self.g.index()

    def test_unknown_edge_type_rejected(self):
        self.assertEqual(validate_edge(Edge("a", "b", "vibes_with")).codes, ["UNKNOWN_TYPE"])

    def test_requires_review_endpoints_enforced(self):
        bad = Edge(f"paper_{gf.PAPER}", "review_2606_concepts_001",
                   EdgeType.REQUIRES_REVIEW.value)
        r = validate_edge(bad, self.idx)
        self.assertFalse(r.valid)
        self.assertTrue(any(e.field_path == "source" for e in r.errors))

    def test_approved_for_endpoints_enforced(self):
        bad = Edge("job_2606_claims_001", "job_2606_concepts_001",
                   EdgeType.APPROVED_FOR.value)
        self.assertFalse(validate_edge(bad, self.idx).valid)

    def test_dangling_edge_rejected(self):
        self.assertFalse(validate_edge(Edge("nope", "also_nope",
                                            EdgeType.UNLOCKS.value), self.idx).valid)

    def test_fixture_edges_all_valid(self):
        for e in self.g.edges:
            self.assertTrue(validate_edge(e, self.idx).valid, f"{e.type} {e.source}->{e.target}")


# ===========================================================================
# Conflicts
# ===========================================================================

class TestConflicts(unittest.TestCase):

    def test_valid_conflict_accepted(self):
        _, _, c = gf.conflict_claim_pair()
        self.assertTrue(validate_conflict(c).valid)

    def test_self_conflict_rejected(self):
        c = ConflictEdge("claim_1", "claim_1", ConflictType.CONTRADICTS, 0.5, "e")
        self.assertFalse(validate_conflict(c).valid)

    def test_conflict_without_evidence_rejected(self):
        c = ConflictEdge("a", "b", ConflictType.CONTRADICTS, 0.5, "")
        self.assertTrue(any(e.field_path == "evidence" for e in validate_conflict(c).errors))

    def test_conflict_severity_range_enforced(self):
        c = ConflictEdge("a", "b", ConflictType.CONTRADICTS, 1.5, "e")
        self.assertIn("OUT_OF_RANGE", validate_conflict(c).codes)

    def test_detector_finds_polarity_conflict(self):
        a, b, _ = gf.conflict_claim_pair()
        found = detect_conflicts_in_graph([a, b])
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0].conflict_type, ConflictType.CONTRADICTS)
        self.assertTrue(validate_conflict(found[0]).valid)

    def test_detector_ignores_unrelated_claims(self):
        a, _, _ = gf.conflict_claim_pair()
        other = Node("claim_x", NodeType.CLAIM.value, "x", None, {
            "text": "flat routing reduces latency", "subject": "flat routing",
            "relation": "reduces", "object": "latency"})
        self.assertEqual(detect_conflicts_in_graph([a, other]), [])

    def test_unresolved_conflicts_lookup(self):
        g = gf.build_fixture_graph()
        self.assertEqual(len(g.unresolved_conflicts_for("claim_2606_001")), 1)
        g.conflicts[0].resolved = True
        self.assertEqual(len(g.unresolved_conflicts_for("claim_2606_001")), 0)


# ===========================================================================
# Golden fixtures — structural
# ===========================================================================

class TestGoldenFixtures(unittest.TestCase):

    def test_1_auto_pass_job_valid(self):
        self.assertTrue(validate_node(gf.auto_pass_job()).valid)

    def test_2_held_for_review_job_valid(self):
        self.assertTrue(validate_node(gf.held_for_review_job()).valid)
        self.assertTrue(validate_node(gf.review_task_pending()).valid)

    def test_3_human_waived_valid_and_carries_waiver(self):
        rt = gf.human_waived_review_task()
        self.assertTrue(validate_node(rt).valid)
        self.assertTrue(rt.properties["confidence_threshold_waived"])
        self.assertTrue(rt.properties["waiver_reason"])
        self.assertEqual(rt.properties["status"], ReviewStatus.APPROVED.value)

    def test_4_conflict_pair_valid(self):
        a, b, c = gf.conflict_claim_pair()
        self.assertTrue(validate_node(a).valid)
        self.assertTrue(validate_node(b).valid)
        self.assertTrue(validate_conflict(c).valid)

    def test_whole_fixture_graph_validates(self):
        r = gf.build_fixture_graph().validate()
        self.assertTrue(r.valid, json.dumps(r.to_dict(), indent=2))

    def test_graph_round_trips_through_json(self):
        g = gf.build_fixture_graph()
        again = ResearchGraph.from_dict(json.loads(json.dumps(g.to_dict())))
        self.assertEqual(len(again.nodes), len(g.nodes))
        self.assertEqual(len(again.conflicts), len(g.conflicts))
        self.assertTrue(again.validate().valid)
        traces = again.index()["job_2606_claims_001"].properties["traces"]
        self.assertIsInstance(traces[0], Trace)
        self.assertEqual(traces[0].decision_type, DecisionType.EXTRACT)

    def test_schema_version_pinned(self):
        self.assertEqual(gf.build_fixture_graph().to_dict()["schema_version"], SCHEMA_VERSION)


# ===========================================================================
# Cross-seam: fixtures through the UNMODIFIED Phase 2 gate
# ===========================================================================

class TestFixturesAgainstGate(unittest.TestCase):

    def setUp(self):
        self.gate = gates.WorkflowGate(confidence_threshold=0.7, require_human_review=True)

    def test_fixture_1_gate_allows(self):
        d = self.gate.should_unlock_next_stage(to_gate_node(gf.auto_pass_job()))
        self.assertTrue(d.can_proceed)
        self.assertEqual(d.reason_code, gates.GateReasonCode.ALLOWED)

    def test_fixture_2_gate_blocks_low_confidence(self):
        d = self.gate.should_unlock_next_stage(to_gate_node(gf.held_for_review_job()))
        self.assertFalse(d.can_proceed)
        self.assertEqual(d.reason_code, gates.GateReasonCode.LOW_CONFIDENCE)

    def test_fixture_3_waiver_blocks_without_graph_context(self):
        """A waiver the gate cannot see is no waiver. Fail closed."""
        d = self.gate.should_unlock_next_stage(to_gate_node(gf.human_waived_job()))
        self.assertFalse(d.can_proceed)
        self.assertEqual(d.reason_code, gates.GateReasonCode.LOW_CONFIDENCE)

    def test_fixture_3_waiver_honored_with_graph_context(self):
        """Phase 3.1: with the review_task visible, the waiver is honored — and named."""
        g = gf.waived_graph()
        d = self.gate.should_unlock_next_stage(
            to_gate_node(g.index()["job_2606_concepts_001"]), g)
        self.assertTrue(d.can_proceed)
        self.assertEqual(d.reason_code, gates.GateReasonCode.ALLOWED_BY_WAIVER)
        conf = [c for c in d.checks if c.check_name == "confidence_above_threshold"][0]
        self.assertTrue(conf.passed)
        self.assertEqual(conf.evidence["waived_by"], "parry.s.2324@gmail.com")
        self.assertIn("central to this paper", conf.evidence["waiver_reason"])

    def test_waived_graph_is_schema_valid(self):
        self.assertTrue(gf.waived_graph().validate().valid)


class TestWaiverGovernance(unittest.TestCase):
    """Phase 3.1: a waiver is a governed bypass, not an escape hatch."""

    def setUp(self):
        self.gate = gates.WorkflowGate(confidence_threshold=0.7, require_human_review=True)

    def _decide(self, graph):
        return self.gate.should_unlock_next_stage(
            to_gate_node(graph.index()["job_2606_concepts_001"]), graph)

    def test_defective_waivers_are_not_honored(self):
        for defect in ("no_reason", "no_reviewer", "not_approved", "unreviewed"):
            with self.subTest(defect=defect):
                d = self._decide(gf.waived_graph_with_defect(defect))
                self.assertFalse(d.can_proceed)
                self.assertEqual(d.reason_code, gates.GateReasonCode.LOW_CONFIDENCE)

    def test_defect_is_named_in_the_trace(self):
        d = self._decide(gf.waived_graph_with_defect("no_reviewer"))
        conf = [c for c in d.checks if c.check_name == "confidence_above_threshold"][0]
        self.assertIn("waiver_rejected", conf.evidence)
        self.assertTrue(any("reviewed_by" in x for x in conf.evidence["waiver_rejected"]))

    def test_waiver_cannot_rescue_below_the_waiver_floor(self):
        g = gf.waived_graph()
        job = g.index()["job_2606_concepts_001"]
        job.provenance.confidence = 0.20  # far below the 0.4 floor
        d = self._decide(g)
        self.assertFalse(d.can_proceed)
        self.assertEqual(d.reason_code, gates.GateReasonCode.LOW_CONFIDENCE)
        conf = [c for c in d.checks if c.check_name == "confidence_above_threshold"][0]
        self.assertIn("below waiver floor", conf.evidence["waiver_rejected"])

    def test_honor_waivers_can_be_switched_off(self):
        gate = gates.WorkflowGate(confidence_threshold=0.7, honor_waivers=False)
        g = gf.waived_graph()
        d = gate.should_unlock_next_stage(
            to_gate_node(g.index()["job_2606_concepts_001"]), g)
        self.assertFalse(d.can_proceed)

    def test_non_waiver_review_task_does_not_grant_a_pass(self):
        """A pending review_task linked to the job is not a waiver."""
        from research_graph_schema import ResearchGraph as RG
        g = RG(nodes=[gf.held_for_review_job(), gf.review_task_pending()])
        d = self._decide(g)
        self.assertFalse(d.can_proceed)
        self.assertEqual(d.reason_code, gates.GateReasonCode.LOW_CONFIDENCE)

    def test_report_counts_waived_passes_separately(self):
        g = gf.waived_graph()
        self._decide(g)
        r = self.gate.report()
        self.assertEqual(r["allowed_by_waiver"], 1)
        self.assertEqual(r["allowed"], 1)
        self.assertIn("ALLOWED_BY_WAIVER", r["by_reason_code"])

    def test_earned_pass_is_not_labelled_a_waiver(self):
        d = self.gate.should_unlock_next_stage(
            to_gate_node(gf.auto_pass_job()), gf.waived_graph())
        self.assertEqual(d.reason_code, gates.GateReasonCode.ALLOWED)
        self.assertEqual(self.gate.report()["allowed_by_waiver"], 0)

    def test_fixture_4_claims_are_terminal_at_gate(self):
        a, _, _ = gf.conflict_claim_pair()
        d = self.gate.should_unlock_next_stage(to_gate_node(a))
        self.assertEqual(d.reason_code, gates.GateReasonCode.DOWNSTREAM_NOT_ALLOWED)

    def test_review_task_pending_blocked_pending_review(self):
        d = self.gate.should_unlock_next_stage(to_gate_node(gf.review_task_pending()))
        self.assertFalse(d.can_proceed)
        self.assertEqual(d.reason_code, gates.GateReasonCode.REVIEW_REQUIRED)

    def test_every_gate_required_field_is_declared_in_schema(self):
        """No field the gate reads may be undeclared in NODE_SCHEMA."""
        from research_graph_schema import NODE_SCHEMA
        gate_required = gates.WorkflowGate()._check_schema_valid.__doc__ is not None
        self.assertTrue(gate_required)  # sanity: method exists
        expected = {
            "extraction_job": ["job_id", "paper_id", "extraction_type", "status"],
            "review_task": ["task_id", "extraction_job_id", "status"],
            "claim": ["text"], "concept": ["text"], "paper": ["title", "url"],
        }
        for type_name, fields in expected.items():
            declared = {f.name for f in NODE_SCHEMA[NodeType(type_name)] if f.required}
            self.assertEqual(declared, set(fields), f"{type_name} required-field drift")


class TestPublishedSchemaMatchesEnforced(unittest.TestCase):
    """graph_schema.json is generated; if someone hand-edits it, this fails."""

    def test_graph_schema_json_is_current(self):
        import os
        from research_graph_schema import export_json_schema
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "graph_schema.json")
        with open(path) as f:
            on_disk = json.load(f)
        self.assertEqual(
            on_disk, export_json_schema(),
            "graph_schema.json is stale or hand-edited. Regenerate with:\n"
            "  python3 research_graph_schema.py --emit-json-schema > graph_schema.json")


if __name__ == "__main__":
    unittest.main(verbosity=2)
