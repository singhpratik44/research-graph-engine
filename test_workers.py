#!/usr/bin/env python3
"""
Phase 4 test suite: the worker envelope contract and the end-to-end loop.

The bulk of these are adversarial — a worker that lies, over-claims, or under-traces
must be rejected, and rejected *whole*.
"""

import unittest

from research_graph_schema import (
    Node, Provenance, Trace, ResearchGraph, ValidationError,
    NodeType, JobStatus, ReviewStatus, ExtractionType, DecisionType, ExtractionMethod,
)
import research_graph_gates as gates
from research_graph_workers import (
    WorkerSpawner, ReferenceWorker, ResultEnvelope, ExtractionDirective,
    PRODUCES_NODE_TYPE, classify_rejection,
)

PAPER = "paper_2606.13707"
ABSTRACT = ("Hierarchical orchestration reduces coordination overhead. "
            "Flat routing increases latency at scale.")


def spawner(**gate_kw):
    g = ResearchGraph()
    return WorkerSpawner(g, gates.WorkflowGate(**gate_kw)), g


class TestHappyPath(unittest.TestCase):

    def setUp(self):
        self.sp, self.g = spawner(confidence_threshold=0.7)
        self.job, self.d = self.sp.spawn(PAPER, ExtractionType.CLAIMS)
        self.env = ReferenceWorker().run(self.d, ABSTRACT)

    def test_directive_is_self_contained(self):
        d = self.d.to_dict()
        self.assertEqual(d["extraction_type"], "claims")
        self.assertEqual(d["target_node_type"], "claim")
        self.assertEqual(d["gate_confidence_threshold"], 0.7)
        self.assertIn("reason_code", d["required_trace_fields"])

    def test_spawned_job_is_schema_valid_and_queued(self):
        from research_graph_schema import validate_node
        self.assertTrue(validate_node(self.job).valid)
        self.assertEqual(self.job.properties["status"], JobStatus.QUEUED.value)

    def test_reference_worker_produces_traced_output(self):
        self.assertEqual(len(self.env.nodes), 2)
        extracted = [t for t in self.env.traces if t.decision_type == DecisionType.EXTRACT]
        self.assertEqual(len(extracted), 2)
        self.assertTrue(all(t.output_refs for t in extracted))

    def test_admission_holds_for_review_not_auto_advance(self):
        r = self.sp.admit(self.d, self.env)
        self.assertTrue(r.admitted)
        self.assertEqual(r.nodes_admitted, 2)
        self.assertEqual(r.job_node.properties["status"], JobStatus.HELD.value)
        self.assertEqual(r.gate_decision.reason_code, gates.GateReasonCode.REVIEW_REQUIRED)
        self.assertIsNotNone(r.review_task)

    def test_admitted_graph_is_valid(self):
        self.sp.admit(self.d, self.env)
        res = self.g.validate()
        self.assertTrue(res.valid, res.to_dict())

    def test_avg_confidence_recorded_on_job(self):
        r = self.sp.admit(self.d, self.env)
        self.assertAlmostEqual(r.job_node.properties["avg_confidence"], 0.85, places=3)
        self.assertAlmostEqual(r.job_node.provenance.confidence, 0.85, places=3)

    def test_traces_persist_on_the_job_node(self):
        r = self.sp.admit(self.d, self.env)
        stored = r.job_node.properties["traces"]
        self.assertEqual(len(stored), len(self.env.traces))
        self.assertIsInstance(stored[0], Trace)

    def test_approval_unlocks(self):
        r = self.sp.admit(self.d, self.env)
        decision = self.sp.approve_review(r.review_task.id, "parry.s.2324@gmail.com",
                                          "Both triples check out")
        self.assertTrue(decision.can_proceed)
        self.assertEqual(decision.reason_code, gates.GateReasonCode.ALLOWED)
        self.assertEqual(r.job_node.properties["status"], JobStatus.APPROVED.value)

    def test_approval_marks_produced_nodes_reviewed(self):
        r = self.sp.admit(self.d, self.env)
        self.sp.approve_review(r.review_task.id, "reviewer@example.com")
        claims = [n for n in self.g.nodes if n.type == NodeType.CLAIM.value]
        self.assertTrue(claims and all(n.provenance.human_reviewed for n in claims))

    def test_rejection_marks_job_rejected(self):
        r = self.sp.admit(self.d, self.env)
        job = self.sp.reject_review(r.review_task.id, "reviewer@example.com", "bad parse")
        self.assertEqual(job.properties["status"], JobStatus.REJECTED.value)


class TestUntrustedWorker(unittest.TestCase):
    """A worker is untrusted. Each of these must be rejected — and rejected whole."""

    def setUp(self):
        self.sp, self.g = spawner()
        self.job, self.d = self.sp.spawn(PAPER, ExtractionType.CONCEPTS)

    def _env(self, nodes, traces, **kw):
        return ResultEnvelope(self.d.job_id, "w1", nodes, traces, **kw)

    def _concept(self, nid="concept_x", conf=0.9, source=PAPER, reviewed=False):
        return Node(nid, NodeType.CONCEPT.value, "x",
                    Provenance(source, ExtractionMethod.KEYWORD.value, conf,
                               "2026-07-26T00:00:00+00:00", human_reviewed=reviewed),
                    {"text": "x"})

    def _trace(self, refs=("concept_x",), **kw):
        base = dict(trace_id="t1", decision_type=DecisionType.EXTRACT, worker_id="w1",
                    confidence=0.9, reason_code="R", reasoning_summary="s",
                    output_refs=list(refs))
        base.update(kw)
        return Trace(**base)

    def _assert_rejected(self, env, needle=None):
        before = len(self.g.nodes)
        r = self.sp.admit(self.d, env)
        self.assertFalse(r.admitted)
        self.assertEqual(r.job_node.properties["status"], JobStatus.FAILED.value)
        self.assertEqual(len(self.g.nodes), before,
                         "rejected envelope must not leave nodes in the graph")
        self.assertEqual(r.nodes_admitted, 0)
        if needle:
            self.assertTrue(any(needle in e.message for e in r.errors),
                            f"{needle!r} not in {[e.message for e in r.errors]}")
        return r

    def test_wrong_node_type_rejected(self):
        bad = Node("claim_x", NodeType.CLAIM.value, "x",
                   Provenance(PAPER, ExtractionMethod.KEYWORD.value, 0.9, "t"), {"text": "x"})
        self._assert_rejected(self._env([bad], [self._trace(refs=["claim_x"])]),
                              "directive requires 'concept'")

    def test_untraced_node_rejected(self):
        self._assert_rejected(self._env([self._concept()], [self._trace(refs=[])]),
                              "no EXTRACT trace")

    def test_trace_claiming_phantom_output_rejected(self):
        self._assert_rejected(
            self._env([self._concept()],
                      [self._trace(), self._trace(trace_id="t2", refs=["concept_ghost"])]),
            "not in the envelope")

    def test_source_paper_spoofing_rejected(self):
        self._assert_rejected(
            self._env([self._concept(source="paper_someone_else")], [self._trace()]),
            "directive is for")

    def test_worker_cannot_mark_own_output_reviewed(self):
        self._assert_rejected(self._env([self._concept(reviewed=True)], [self._trace()]),
                              "may not mark its own output human_reviewed")

    def test_below_directive_floor_rejected(self):
        self.d.confidence_floor = 0.6
        self._assert_rejected(self._env([self._concept(conf=0.3)], [self._trace()]),
                              "should have been SKIPped")

    def test_exceeding_max_results_rejected(self):
        self.d.max_results = 1
        env = self._env([self._concept("concept_a"), self._concept("concept_b")],
                        [self._trace(refs=["concept_a"]),
                         self._trace(trace_id="t2", refs=["concept_b"])])
        self._assert_rejected(env, "exceeds max_results")

    def test_duplicate_node_ids_rejected(self):
        env = self._env([self._concept("concept_a"), self._concept("concept_a")],
                        [self._trace(refs=["concept_a"])])
        self._assert_rejected(env, "duplicate node id")

    def test_trace_worker_id_mismatch_rejected(self):
        self._assert_rejected(self._env([self._concept()],
                                        [self._trace(worker_id="someone_else")]),
                              "!= envelope")

    def test_malformed_trace_rejected(self):
        self._assert_rejected(self._env([self._concept()], [self._trace(reason_code="")]),
                              "reason_code")

    def test_schema_invalid_node_rejected(self):
        bad = Node("concept_y", NodeType.CONCEPT.value, "y",
                   Provenance(PAPER, ExtractionMethod.KEYWORD.value, 0.9, "t"), {})
        self._assert_rejected(self._env([bad], [self._trace(refs=["concept_y"])]),
                              "requires 'text'")

    def test_job_id_mismatch_rejected(self):
        env = ResultEnvelope("job_not_mine", "w1", [self._concept()], [self._trace()])
        self._assert_rejected(env, "!= directive")

    def test_id_collision_with_existing_graph_node_rejected(self):
        self.g.nodes.append(self._concept("concept_x"))
        self._assert_rejected(self._env([self._concept("concept_x")], [self._trace()]),
                              "already in graph")

    def test_worker_reported_failure_marks_job_failed(self):
        env = ResultEnvelope(self.d.job_id, "w1", worker_status="failed", error="timeout")
        r = self.sp.admit(env=env, directive=self.d)
        self.assertFalse(r.admitted)
        self.assertEqual(r.job_node.properties["status"], JobStatus.FAILED.value)

    def test_all_errors_reported_not_just_first(self):
        r = self.sp.admit(self.d, self._env(
            [self._concept(source="wrong", reviewed=True)], [self._trace()]))
        self.assertGreaterEqual(len(r.errors), 2)

    def test_admit_unknown_job_raises(self):
        d = ExtractionDirective("job_nope", PAPER, ExtractionType.CONCEPTS, NodeType.CONCEPT)
        with self.assertRaises(KeyError):
            self.sp.admit(d, ResultEnvelope("job_nope", "w1"))


class TestAdaptiveRetry(unittest.TestCase):
    """
    gap_adaptive_recovery: a rejected envelope can be retried with a
    diagnose-and-regenerate function instead of failing wholesale. Bounded by
    max_retries, and every attempt -- successful or not -- stays on the job's
    record (retry_attempts / retry_count / original_failure), not silently
    overwritten. retry_with=None (the default) must reproduce today's
    fail-whole-on-first-rejection behavior exactly.
    """

    def setUp(self):
        self.sp, self.g = spawner()
        self.job, self.d = self.sp.spawn(PAPER, ExtractionType.CONCEPTS)
        self.d.confidence_floor = 0.6

    def _concept(self, nid="concept_x", conf=0.9):
        return Node(nid, NodeType.CONCEPT.value, "x",
                    Provenance(PAPER, ExtractionMethod.KEYWORD.value, conf,
                              "2026-07-26T00:00:00+00:00"),
                    {"text": "x"})

    def _trace(self, refs=("concept_x",), **kw):
        base = dict(trace_id="t1", decision_type=DecisionType.EXTRACT, worker_id="w1",
                    confidence=0.9, reason_code="R", reasoning_summary="s",
                    output_refs=list(refs))
        base.update(kw)
        return Trace(**base)

    def _below_floor_env(self):
        # conf=0.3 < floor 0.6 -- rejected with the "should have been SKIPped" error.
        return ResultEnvelope(self.d.job_id, "w1", [self._concept(conf=0.3)], [self._trace()])

    # -- retry succeeds -----------------------------------------------------

    def test_retry_with_is_called_with_the_actual_validation_errors(self):
        calls = []

        def retry_with(directive, errors):
            calls.append(errors)
            return ResultEnvelope(directive.job_id, "w1",
                                  [self._concept(conf=0.9)], [self._trace()])

        r = self.sp.admit(self.d, self._below_floor_env(), retry_with=retry_with)
        self.assertTrue(r.admitted)
        self.assertEqual(len(calls), 1, "retry_with must be called exactly once here")
        # It saw *why* the first attempt was rejected, not just that it failed.
        self.assertTrue(any("should have been SKIPped" in e.message for e in calls[0]),
                        [e.message for e in calls[0]])

    def test_successful_retry_records_original_failure_and_retry_count(self):
        def retry_with(directive, errors):
            return ResultEnvelope(directive.job_id, "w1",
                                  [self._concept(conf=0.9)], [self._trace()])

        r = self.sp.admit(self.d, self._below_floor_env(), retry_with=retry_with)
        self.assertTrue(r.admitted)
        self.assertEqual(r.job_node.properties["retry_count"], 1)
        self.assertEqual(len(r.job_node.properties["retry_attempts"]), 1)
        original = r.job_node.properties["original_failure"]
        self.assertTrue(any("should have been SKIPped" in e["message"] for e in original))

    def test_admitted_graph_after_a_successful_retry_is_valid(self):
        def retry_with(directive, errors):
            return ResultEnvelope(directive.job_id, "w1",
                                  [self._concept(conf=0.9)], [self._trace()])

        r = self.sp.admit(self.d, self._below_floor_env(), retry_with=retry_with)
        self.assertTrue(r.admitted)
        self.assertEqual(r.nodes_admitted, 1)
        self.assertTrue(self.g.validate().valid)

    # -- retries are bounded --------------------------------------------

    def test_retries_are_bounded_and_still_fail_when_exhausted(self):
        calls = []

        def always_bad_retry(directive, errors):
            calls.append(errors)
            return ResultEnvelope(directive.job_id, "w1",
                                  [self._concept(conf=0.1)], [self._trace()])

        r = self.sp.admit(self.d, self._below_floor_env(),
                          retry_with=always_bad_retry, max_retries=2)
        self.assertFalse(r.admitted)
        self.assertEqual(len(calls), 2,
                         "retry_with must be called exactly max_retries times, not infinitely")
        self.assertEqual(r.job_node.properties["status"], JobStatus.FAILED.value)
        self.assertEqual(r.job_node.properties["retry_count"], 2)
        self.assertEqual(len(r.job_node.properties["retry_attempts"]), 3)
        self.assertEqual(r.nodes_admitted, 0)
        self.assertEqual(len(self.g.nodes), 1, "no nodes from any failed attempt leak into the graph")

    def test_default_max_retries_of_one_stops_after_a_single_retry(self):
        calls = []

        def always_bad_retry(directive, errors):
            calls.append(errors)
            return ResultEnvelope(directive.job_id, "w1",
                                  [self._concept(conf=0.1)], [self._trace()])

        r = self.sp.admit(self.d, self._below_floor_env(), retry_with=always_bad_retry)
        self.assertFalse(r.admitted)
        self.assertEqual(len(calls), 1, "max_retries defaults to 1")
        self.assertEqual(r.job_node.properties["retry_count"], 1)

    # -- retry_with=None is byte-for-byte today's behavior ------------------

    def test_default_admit_has_no_retry_bookkeeping_and_fails_on_first_attempt(self):
        r = self.sp.admit(self.d, self._below_floor_env())
        self.assertFalse(r.admitted)
        self.assertEqual(r.job_node.properties["status"], JobStatus.FAILED.value)
        self.assertEqual(r.job_node.properties["result_count"], 0)
        for key in ("retry_attempts", "retry_count", "original_failure"):
            self.assertNotIn(key, r.job_node.properties,
                             f"{key!r} must not appear when retry_with is not supplied")

    def test_retry_with_not_invoked_when_first_attempt_already_succeeds(self):
        good_env = ResultEnvelope(self.d.job_id, "w1", [self._concept(conf=0.9)], [self._trace()])
        calls = []

        def retry_with(directive, errors):
            calls.append(errors)
            return good_env

        r = self.sp.admit(self.d, good_env, retry_with=retry_with)
        self.assertTrue(r.admitted)
        self.assertEqual(calls, [], "retry_with must not be called when nothing failed")
        self.assertNotIn("retry_count", r.job_node.properties)

    def test_every_existing_untrusted_worker_case_is_unchanged_by_default(self):
        """Re-run one of TestUntrustedWorker's adversarial cases through the same
        spawner/job, with no retry_with, and confirm it is rejected exactly as
        before -- proving the new parameter is opt-in, not a behavior change."""
        bad = Node("claim_x", NodeType.CLAIM.value, "x",
                  Provenance(PAPER, ExtractionMethod.KEYWORD.value, 0.9, "t"), {"text": "x"})
        env = ResultEnvelope(self.d.job_id, "w1", [bad], [self._trace(refs=["claim_x"])])
        r = self.sp.admit(self.d, env)
        self.assertFalse(r.admitted)
        self.assertEqual(r.job_node.properties["status"], JobStatus.FAILED.value)
        self.assertTrue(any("directive requires 'concept'" in e.message for e in r.errors))


class TestDirectiveIsHonoredByReferenceWorker(unittest.TestCase):

    def test_worker_respects_confidence_floor_and_traces_the_skip(self):
        sp, _ = spawner()
        _, d = sp.spawn(PAPER, ExtractionType.CONCEPTS, confidence_floor=0.9)
        env = ReferenceWorker().run(d, ABSTRACT)
        r = sp.admit(d, env)
        self.assertTrue(r.admitted)
        self.assertTrue(any(t.decision_type == DecisionType.SKIP for t in env.traces))
        self.assertTrue(all(n.provenance.confidence >= 0.9 for n in env.nodes))

    def test_worker_respects_max_results_and_traces_the_abstain(self):
        sp, _ = spawner()
        _, d = sp.spawn(PAPER, ExtractionType.CONCEPTS, max_results=3)
        env = ReferenceWorker().run(d, ABSTRACT)
        self.assertLessEqual(len(env.nodes), 3)
        self.assertTrue(any(t.decision_type == DecisionType.ABSTAIN for t in env.traces))
        self.assertTrue(sp.admit(d, env).admitted)

    def test_unsupported_extraction_type_fails_cleanly(self):
        sp, _ = spawner()
        _, d = sp.spawn(PAPER, ExtractionType.METHODS)
        env = ReferenceWorker().run(d, ABSTRACT)
        self.assertEqual(env.worker_status, "failed")
        self.assertFalse(sp.admit(d, env).admitted)

    def test_every_extraction_type_has_a_target_node_type(self):
        for et in ExtractionType:
            self.assertIn(et, PRODUCES_NODE_TYPE)


class TestBenchmarkExtraction(unittest.TestCase):
    """ReferenceWorker.BENCHMARKS: two deliberately dumb signals -- a
    '...Bench' suffix (strong) and a '<Name> benchmark' phrase (weaker)."""

    TEXT = ("We evaluate on SWE-Bench and MLR-Bench. "
            "The PRISM benchmark was also used, alongside LEGOBench.")

    def test_suffix_matches_extracted_at_high_confidence(self):
        sp, _ = spawner()
        _, d = sp.spawn(PAPER, ExtractionType.BENCHMARKS)
        env = ReferenceWorker().run(d, self.TEXT)
        names = {n.properties["text"] for n in env.nodes}
        self.assertIn("SWE-Bench", names)
        self.assertIn("MLR-Bench", names)
        self.assertIn("LEGOBench", names)
        suffix_nodes = [n for n in env.nodes if n.properties["text"] in
                        {"SWE-Bench", "MLR-Bench", "LEGOBench"}]
        self.assertTrue(all(n.provenance.confidence == 0.8 for n in suffix_nodes))

    def test_phrase_match_extracted_at_lower_confidence(self):
        sp, _ = spawner()
        _, d = sp.spawn(PAPER, ExtractionType.BENCHMARKS)
        env = ReferenceWorker().run(d, self.TEXT)
        prism = next(n for n in env.nodes if n.properties["text"] == "PRISM")
        self.assertEqual(prism.provenance.confidence, 0.6)

    def test_admits_cleanly_and_produces_benchmark_nodes(self):
        sp, _ = spawner()
        _, d = sp.spawn(PAPER, ExtractionType.BENCHMARKS)
        env = ReferenceWorker().run(d, self.TEXT)
        result = sp.admit(d, env)
        self.assertTrue(result.admitted)
        self.assertTrue(all(n.type == NodeType.BENCHMARK.value for n in env.nodes))

    def test_confidence_floor_filters_out_the_weaker_phrase_match(self):
        sp, _ = spawner()
        _, d = sp.spawn(PAPER, ExtractionType.BENCHMARKS, confidence_floor=0.7)
        env = ReferenceWorker().run(d, self.TEXT)
        names = {n.properties["text"] for n in env.nodes}
        self.assertNotIn("PRISM", names)
        self.assertIn("SWE-Bench", names)

    def test_no_benchmark_mentions_yields_nothing(self):
        sp, _ = spawner()
        _, d = sp.spawn(PAPER, ExtractionType.BENCHMARKS)
        env = ReferenceWorker().run(d, "This text has no benchmark names in it at all.")
        self.assertEqual(env.nodes, [])


class TestConflictsAndWaiverEndToEnd(unittest.TestCase):

    def test_contradicting_papers_produce_a_conflict(self):
        sp, g = spawner()
        _, d1 = sp.spawn("paper_A", ExtractionType.CLAIMS)
        r1 = sp.admit(d1, ReferenceWorker("w_a").run(
            d1, "Hierarchical orchestration reduces coordination overhead."))
        self.assertEqual(r1.conflicts_found, 0)

        _, d2 = sp.spawn("paper_B", ExtractionType.CLAIMS)
        r2 = sp.admit(d2, ReferenceWorker("w_b").run(
            d2, "Hierarchical orchestration increases coordination overhead."))
        self.assertEqual(r2.conflicts_found, 1)
        self.assertEqual(len(g.conflicts), 1)
        self.assertTrue(g.validate().valid)

    def test_unresolved_conflict_blocks_the_producing_job(self):
        """A job answers for what it produced: approval isn't enough while a
        contradiction it introduced is still open."""
        sp, g = spawner()
        _, d1 = sp.spawn("paper_A", ExtractionType.CLAIMS)
        r1 = sp.admit(d1, ReferenceWorker("w_a").run(
            d1, "Hierarchical orchestration reduces coordination overhead."))
        sp.approve_review(r1.review_task.id, "reviewer@example.com", "fine")

        _, d2 = sp.spawn("paper_B", ExtractionType.CLAIMS)
        r2 = sp.admit(d2, ReferenceWorker("w_b").run(
            d2, "Hierarchical orchestration increases coordination overhead."))
        decision = sp.approve_review(r2.review_task.id, "reviewer@example.com", "also fine")

        self.assertFalse(decision.can_proceed)
        self.assertEqual(decision.reason_code, gates.GateReasonCode.CONFLICT_UNRESOLVED)

        g.conflicts[0].resolved = True
        g.conflicts[0].resolution_note = "Scope-dependent: A is small-fleet, B is at scale."
        again = sp.gate.should_unlock_next_stage(r2.job_node, g)
        self.assertTrue(again.can_proceed)

    def test_conflict_check_can_be_disabled(self):
        """detect_conflicts=False makes the check inert, and says so in the trace."""
        sp, g = spawner(detect_conflicts=False)
        _, d1 = sp.spawn("paper_A", ExtractionType.CLAIMS)
        r1 = sp.admit(d1, ReferenceWorker("w_a").run(
            d1, "Hierarchical orchestration reduces coordination overhead."))
        sp.approve_review(r1.review_task.id, "r@example.com")
        _, d2 = sp.spawn("paper_B", ExtractionType.CLAIMS)
        r2 = sp.admit(d2, ReferenceWorker("w_b").run(
            d2, "Hierarchical orchestration increases coordination overhead."))

        self.assertEqual(len(g.conflicts), 1, "detector still records the conflict")
        decision = sp.approve_review(r2.review_task.id, "r@example.com")
        self.assertTrue(decision.can_proceed, "gate was told not to enforce it")
        check = [c for c in decision.checks if c.check_name == "no_conflicts"][0]
        self.assertFalse(check.evidence["checked"])

    def test_low_confidence_job_can_be_waived_through(self):
        sp, g = spawner(confidence_threshold=0.9)  # forces the claims (0.85) below threshold
        _, d = sp.spawn(PAPER, ExtractionType.CLAIMS)
        r = sp.admit(d, ReferenceWorker().run(d, ABSTRACT))
        self.assertEqual(r.job_node.properties["status"], JobStatus.HELD.value)

        decision = sp.approve_review(r.review_task.id, "parry.s.2324@gmail.com",
                                     "Triples verified by hand",
                                     waive_confidence=True,
                                     waiver_reason="0.85 reflects parser caution, "
                                                   "not doubt about the claims")
        self.assertTrue(decision.can_proceed)
        self.assertEqual(decision.reason_code, gates.GateReasonCode.ALLOWED_BY_WAIVER)
        self.assertEqual(sp.gate.report()["allowed_by_waiver"], 1)
        self.assertTrue(g.validate().valid)

    def test_waiver_without_reason_refused_at_the_api(self):
        sp, _ = spawner(confidence_threshold=0.9)
        _, d = sp.spawn(PAPER, ExtractionType.CLAIMS)
        r = sp.admit(d, ReferenceWorker().run(d, ABSTRACT))
        with self.assertRaises(ValueError):
            sp.approve_review(r.review_task.id, "someone@example.com", waive_confidence=True)

    def test_plain_approval_does_not_clear_low_confidence(self):
        sp, _ = spawner(confidence_threshold=0.9)
        _, d = sp.spawn(PAPER, ExtractionType.CLAIMS)
        r = sp.admit(d, ReferenceWorker().run(d, ABSTRACT))
        decision = sp.approve_review(r.review_task.id, "someone@example.com", "looks fine")
        self.assertFalse(decision.can_proceed)
        self.assertEqual(decision.reason_code, gates.GateReasonCode.LOW_CONFIDENCE)
        self.assertEqual(r.job_node.properties["status"], JobStatus.HELD.value)


class TestClassifyRejection(unittest.TestCase):
    """
    classify_rejection: pure function, not wired into admit() -- feeds canned
    ValidationError lists covering every one of _verify_envelope's known
    rejection shapes and confirms the fixed precedence table's output.
    """

    def test_worker_status_failure_is_worker_reported_failure(self):
        errors = [ValidationError("worker_status", "BAD_TYPE", "worker reported failure")]
        self.assertEqual(classify_rejection(errors), "worker_reported_failure")

    def test_max_results_exceeded_is_capacity_violation(self):
        errors = [ValidationError("nodes", "OUT_OF_RANGE", "3 results exceeds max_results 2")]
        self.assertEqual(classify_rejection(errors), "capacity_violation")

    def test_confidence_below_floor_is_capacity_violation(self):
        errors = [ValidationError("nodes[0].provenance.confidence", "OUT_OF_RANGE",
                                  "confidence 0.1 below directive floor 0.5")]
        self.assertEqual(classify_rejection(errors), "capacity_violation")

    def test_job_id_mismatch_is_structural_mismatch(self):
        errors = [ValidationError("job_id", "BAD_TYPE", "envelope job_id != directive")]
        self.assertEqual(classify_rejection(errors), "structural_mismatch")

    def test_missing_worker_id_is_structural_mismatch(self):
        errors = [ValidationError("worker_id", "MISSING_REQUIRED", "envelope has no worker_id")]
        self.assertEqual(classify_rejection(errors), "structural_mismatch")

    def test_wrong_node_type_is_structural_mismatch(self):
        errors = [ValidationError("nodes[0].type", "BAD_TYPE", "directive requires 'claim'")]
        self.assertEqual(classify_rejection(errors), "structural_mismatch")

    def test_duplicate_node_id_in_envelope_is_structural_mismatch(self):
        errors = [ValidationError("nodes[0].id", "BAD_TYPE", "duplicate node id")]
        self.assertEqual(classify_rejection(errors), "structural_mismatch")

    def test_node_id_collision_with_graph_is_structural_mismatch(self):
        errors = [ValidationError("nodes", "BAD_TYPE", "node ids already in graph")]
        self.assertEqual(classify_rejection(errors), "structural_mismatch")

    def test_missing_traces_entirely_is_trace_integrity(self):
        errors = [ValidationError("traces", "MISSING_REQUIRED", "no traces")]
        self.assertEqual(classify_rejection(errors), "trace_integrity")

    def test_duplicate_trace_id_is_trace_integrity(self):
        errors = [ValidationError("traces[0].trace_id", "BAD_TYPE", "duplicate trace_id")]
        self.assertEqual(classify_rejection(errors), "trace_integrity")

    def test_orphaned_node_with_no_extract_trace_is_trace_integrity(self):
        errors = [ValidationError("traces", "MISSING_REQUIRED", "node emitted with no EXTRACT trace")]
        self.assertEqual(classify_rejection(errors), "trace_integrity")

    def test_missing_provenance_is_reparable_field_error(self):
        errors = [ValidationError("nodes[0].provenance", "MISSING_REQUIRED", "no provenance")]
        self.assertEqual(classify_rejection(errors), "reparable_field_error")

    def test_spoofed_source_paper_is_reparable_field_error(self):
        errors = [ValidationError("nodes[0].provenance.source_paper", "BAD_TYPE", "wrong source")]
        self.assertEqual(classify_rejection(errors), "reparable_field_error")

    def test_self_marked_human_reviewed_is_reparable_field_error(self):
        errors = [ValidationError("nodes[0].provenance.human_reviewed", "BAD_TYPE",
                                  "worker may not mark its own output reviewed")]
        self.assertEqual(classify_rejection(errors), "reparable_field_error")

    def test_generic_schema_field_error_is_reparable_field_error(self):
        errors = [ValidationError("nodes[0].properties.text", "MISSING_REQUIRED", "missing text")]
        self.assertEqual(classify_rejection(errors), "reparable_field_error")

    def test_no_errors_is_unclassified(self):
        self.assertEqual(classify_rejection([]), "unclassified")

    def test_worker_reported_failure_takes_precedence_over_other_errors(self):
        errors = [ValidationError("nodes[0].type", "BAD_TYPE", "wrong type"),
                  ValidationError("worker_status", "BAD_TYPE", "worker reported failure")]
        self.assertEqual(classify_rejection(errors), "worker_reported_failure")

    def test_is_a_pure_function_not_wired_into_admit(self):
        """admit()'s own rejection behavior is completely unaffected by this
        function existing -- confirmed by re-running an existing adversarial
        case and checking admit()'s AdmissionResult is unchanged."""
        sp, g = spawner()
        _, d = sp.spawn(PAPER, ExtractionType.CLAIMS)
        bad_env = ResultEnvelope(d.job_id, "w1", nodes=[
            Node("claim_bad", "concept", "wrong type",
                 Provenance(PAPER, ExtractionMethod.STRUCTURED_LLM.value, 0.9,
                           "2026-07-26T00:00:00+00:00"),
                 {"text": "wrong type"})
        ], traces=[])
        r = sp.admit(d, bad_env)
        self.assertFalse(r.admitted)
        # classify_rejection can be called independently on the same errors --
        # admit() never calls it itself.
        label = classify_rejection(r.errors)
        self.assertEqual(label, "structural_mismatch")


if __name__ == "__main__":
    unittest.main(verbosity=2)
