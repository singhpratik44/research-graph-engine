#!/usr/bin/env python3
"""
Test suite for specialist_review.py: the four bounded specialist roles
(extractor, schema validator, conflict checker, reviewer/judge), their
verdict builders, reconciliation, DAG shape, and the end-to-end pipeline.

Each verdict builder gets a positive and a negative case -- a specialist
that can't fail is decorative, same testing bar as task_conformance.py.
"""

import unittest

from research_graph_schema import (
    ConflictType, ExtractionMethod, ExtractionType, Node, Provenance,
    ResearchGraph,
)
import research_graph_gates as gates
from research_graph_workers import ReferenceWorker, ResultEnvelope, WorkerSpawner
from task_graph import RunResult, TaskSpan, TaskStatus
import graph_memory
import specialist_review as sr

PAPER = "paper_demo_001"


def _claim(node_id, subject, relation, obj, conf=0.9, paper=PAPER):
    return Node(
        id=node_id, type="claim", label=f"{subject} {relation} {obj}",
        provenance=Provenance(paper, ExtractionMethod.STRUCTURED_LLM.value, conf,
                              "2026-07-26T00:00:00+00:00", human_reviewed=False),
        properties={"text": f"{subject} {relation} {obj}", "subject": subject,
                    "relation": relation, "object": obj},
    )


# ============================================================================
# Verdict builders
# ============================================================================

class TestVerdictFromExtraction(unittest.TestCase):
    def test_failed_worker_status_fails_the_verdict(self):
        env = ResultEnvelope("job_1", "w1", worker_status="failed", error="boom")
        v = sr.verdict_from_extraction(env)
        self.assertEqual(v.role, sr.ROLE_EXTRACTOR)
        self.assertFalse(v.passed)
        self.assertIn("boom", v.detail)

    def test_completed_worker_with_nodes_passes_and_averages_confidence(self):
        nodes = [_claim("c1", "a", "reduces", "b", conf=0.8),
                 _claim("c2", "a", "reduces", "c", conf=0.6)]
        env = ResultEnvelope("job_1", "w1", nodes=nodes)
        v = sr.verdict_from_extraction(env)
        self.assertTrue(v.passed)
        self.assertAlmostEqual(v.confidence, 0.7)
        self.assertEqual(v.evidence["nodes_produced"], 2)

    def test_completed_worker_with_no_nodes_still_passes_with_no_confidence(self):
        env = ResultEnvelope("job_1", "w1", nodes=[])
        v = sr.verdict_from_extraction(env)
        self.assertTrue(v.passed)
        self.assertIsNone(v.confidence)


class TestVerdictFromSchemaValidation(unittest.TestCase):
    def test_valid_nodes_pass(self):
        nodes = [_claim("c1", "a", "reduces", "b")]
        v = sr.verdict_from_schema_validation(nodes)
        self.assertEqual(v.role, sr.ROLE_SCHEMA_VALIDATOR)
        self.assertTrue(v.passed)
        self.assertEqual(v.evidence["errors"], [])

    def test_missing_required_field_fails(self):
        bad = Node(id="c_bad", type="claim", label="broken",
                   provenance=Provenance(PAPER, ExtractionMethod.STRUCTURED_LLM.value, 0.9,
                                        "2026-07-26T00:00:00+00:00"),
                   properties={})  # missing required 'text'
        v = sr.verdict_from_schema_validation([bad])
        self.assertFalse(v.passed)
        self.assertEqual(len(v.evidence["errors"]), 1)
        self.assertEqual(v.evidence["errors"][0]["code"], "MISSING_REQUIRED")

    def test_unknown_node_type_fails(self):
        bad = Node(id="c_bad", type="not_a_type", label="broken", properties={"text": "x"})
        v = sr.verdict_from_schema_validation([bad])
        self.assertFalse(v.passed)

    def test_empty_node_list_passes_vacuously(self):
        v = sr.verdict_from_schema_validation([])
        self.assertTrue(v.passed)


class TestVerdictFromConflictCheck(unittest.TestCase):
    def test_no_conflicts_passes(self):
        candidates = [_claim("c1", "x", "reduces", "y")]
        v = sr.verdict_from_conflict_check(candidates, existing_nodes=[])
        self.assertEqual(v.role, sr.ROLE_CONFLICT_CHECKER)
        self.assertTrue(v.passed)
        self.assertEqual(v.evidence["conflicts"], [])

    def test_conflict_touching_candidate_batch_fails(self):
        existing = [_claim("c_existing", "x", "increases", "y")]
        candidates = [_claim("c_new", "x", "reduces", "y")]
        v = sr.verdict_from_conflict_check(candidates, existing_nodes=existing)
        self.assertFalse(v.passed)
        self.assertEqual(len(v.evidence["conflicts"]), 1)

    def test_conflict_entirely_among_existing_nodes_does_not_count(self):
        existing = [_claim("c_a", "x", "increases", "y"),
                    _claim("c_b", "x", "reduces", "y")]
        candidates = [_claim("c_new", "p", "improves", "q")]
        v = sr.verdict_from_conflict_check(candidates, existing_nodes=existing)
        self.assertTrue(v.passed, v.evidence)


class TestCheckConfidenceDivergence(unittest.TestCase):
    def test_id_match_with_large_confidence_gap_is_recorded(self):
        graph = ResearchGraph()
        existing = _claim("c1", "x", "reduces", "y", conf=0.9)
        graph.nodes.append(existing)
        candidate = _claim("c1", "x", "reduces", "y", conf=0.3)  # same id, re-derived
        divergences = sr.check_confidence_divergence(graph, [candidate], [existing], threshold=0.2)
        self.assertEqual(len(divergences), 1)
        self.assertEqual(divergences[0].properties["details"]["derivation_confidence"], 0.9)
        self.assertEqual(divergences[0].properties["details"]["validation_confidence"], 0.3)

    def test_gap_below_threshold_is_not_recorded(self):
        graph = ResearchGraph()
        existing = _claim("c1", "x", "reduces", "y", conf=0.9)
        graph.nodes.append(existing)
        candidate = _claim("c1", "x", "reduces", "y", conf=0.85)
        divergences = sr.check_confidence_divergence(graph, [candidate], [existing], threshold=0.2)
        self.assertEqual(divergences, [])

    def test_no_id_match_is_not_a_divergence(self):
        graph = ResearchGraph()
        existing = _claim("c1", "x", "reduces", "y", conf=0.9)
        graph.nodes.append(existing)
        candidate = _claim("c2", "p", "improves", "q", conf=0.1)  # different id
        divergences = sr.check_confidence_divergence(graph, [candidate], [existing], threshold=0.2)
        self.assertEqual(divergences, [])


# ============================================================================
# Reconciliation
# ============================================================================

class TestReconcileAndAdmit(unittest.TestCase):
    def setUp(self):
        self.graph = ResearchGraph()
        self.spawner = WorkerSpawner(self.graph, gates.WorkflowGate())
        self.job, self.directive = self.spawner.spawn(PAPER, ExtractionType.CLAIMS)
        self.env = ReferenceWorker().run(self.directive, "Hierarchical orchestration reduces coordination overhead.")

    def test_agreeing_verdicts_record_no_disagreement(self):
        agree_pass = sr.SpecialistVerdict(role=sr.ROLE_SCHEMA_VALIDATOR, passed=True, detail="ok")
        agree_pass2 = sr.SpecialistVerdict(role=sr.ROLE_CONFLICT_CHECKER, passed=True, detail="ok")
        admission, disagreements = sr.reconcile_and_admit(
            self.graph, self.spawner, self.directive, self.env, agree_pass, agree_pass2)
        self.assertEqual(disagreements, [])
        self.assertTrue(admission.admitted)

    def test_disagreeing_verdicts_record_a_memory_disagreement(self):
        schema_v = sr.SpecialistVerdict(role=sr.ROLE_SCHEMA_VALIDATOR, passed=True, detail="ok")
        conflict_v = sr.SpecialistVerdict(role=sr.ROLE_CONFLICT_CHECKER, passed=False, detail="conflict found")
        admission, disagreements = sr.reconcile_and_admit(
            self.graph, self.spawner, self.directive, self.env, schema_v, conflict_v)
        self.assertEqual(len(disagreements), 1)
        record = disagreements[0]
        self.assertEqual(record.properties["memory_kind"], "reviewer_disagreement")
        self.assertEqual(record.properties["subject_ref"], self.directive.job_id)

    def test_disagreement_is_queryable_via_graph_memory(self):
        schema_v = sr.SpecialistVerdict(role=sr.ROLE_SCHEMA_VALIDATOR, passed=False, detail="bad")
        conflict_v = sr.SpecialistVerdict(role=sr.ROLE_CONFLICT_CHECKER, passed=True, detail="clean")
        sr.reconcile_and_admit(self.graph, self.spawner, self.directive, self.env, schema_v, conflict_v)
        found = graph_memory.prior_disagreements_on(self.graph, self.directive.job_id)
        self.assertEqual(len(found), 1)

    def test_admit_is_always_called_regardless_of_disagreement(self):
        schema_v = sr.SpecialistVerdict(role=sr.ROLE_SCHEMA_VALIDATOR, passed=False, detail="bad")
        conflict_v = sr.SpecialistVerdict(role=sr.ROLE_CONFLICT_CHECKER, passed=True, detail="clean")
        admission, _ = sr.reconcile_and_admit(
            self.graph, self.spawner, self.directive, self.env, schema_v, conflict_v)
        self.assertTrue(admission.admitted)
        self.assertIn(self.directive.job_id, self.graph.index())

    def test_track_verdict_agreement_off_by_default_records_nothing_extra(self):
        agree = sr.SpecialistVerdict(role=sr.ROLE_SCHEMA_VALIDATOR, passed=True, detail="ok")
        agree2 = sr.SpecialistVerdict(role=sr.ROLE_CONFLICT_CHECKER, passed=True, detail="ok")
        sr.reconcile_and_admit(self.graph, self.spawner, self.directive, self.env, agree, agree2)
        comparisons = [n for n in self.graph.nodes
                      if n.properties.get("memory_kind") == "verdict_comparison"]
        self.assertEqual(comparisons, [])

    def test_track_verdict_agreement_records_even_on_agreement(self):
        agree = sr.SpecialistVerdict(role=sr.ROLE_SCHEMA_VALIDATOR, passed=True, detail="ok")
        agree2 = sr.SpecialistVerdict(role=sr.ROLE_CONFLICT_CHECKER, passed=True, detail="ok")
        sr.reconcile_and_admit(self.graph, self.spawner, self.directive, self.env, agree, agree2,
                               track_verdict_agreement=True)
        comparisons = [n for n in self.graph.nodes
                      if n.properties.get("memory_kind") == "verdict_comparison"]
        self.assertEqual(len(comparisons), 1)
        self.assertTrue(comparisons[0].properties["details"]["agreed"])

    def test_track_verdict_agreement_records_on_disagreement_too(self):
        schema_v = sr.SpecialistVerdict(role=sr.ROLE_SCHEMA_VALIDATOR, passed=True, detail="ok")
        conflict_v = sr.SpecialistVerdict(role=sr.ROLE_CONFLICT_CHECKER, passed=False, detail="bad")
        sr.reconcile_and_admit(self.graph, self.spawner, self.directive, self.env,
                               schema_v, conflict_v, track_verdict_agreement=True)
        comparisons = [n for n in self.graph.nodes
                      if n.properties.get("memory_kind") == "verdict_comparison"]
        self.assertEqual(len(comparisons), 1)
        self.assertFalse(comparisons[0].properties["details"]["agreed"])
        # Both records exist: the disagreement AND the comparison, distinct kinds.
        disagreements = [n for n in self.graph.nodes
                         if n.properties.get("memory_kind") == "reviewer_disagreement"]
        self.assertEqual(len(disagreements), 1)


# ============================================================================
# DAG shape
# ============================================================================

class TestSpecialistDAGShape(unittest.TestCase):
    def setUp(self):
        self.dag = sr._build_dag()

    def test_all_four_roles_are_tasks(self):
        self.assertEqual(set(self.dag.nodes), {"extract", "conflict_check",
                                                 "schema_validate", "reviewer_judge"})

    def test_conflict_check_and_schema_validate_depend_only_on_extract(self):
        self.assertEqual(self.dag.dependencies_of("conflict_check"), ["extract"])
        self.assertEqual(self.dag.dependencies_of("schema_validate"), ["extract"])

    def test_reviewer_judge_depends_on_both_specialists(self):
        deps = set(self.dag.dependencies_of("reviewer_judge"))
        self.assertEqual(deps, {"conflict_check", "schema_validate"})

    def test_extract_has_no_dependencies(self):
        self.assertEqual(self.dag.dependencies_of("extract"), [])

    def test_dag_has_no_cycles(self):
        self.assertEqual(self.dag.detect_cycles(), [])

    def test_conflict_check_and_schema_validate_are_mutually_independent(self):
        # Neither is reachable from the other -- this is what makes them a
        # single concurrent round under task_graph.Scheduler (whose own
        # thread-pool concurrency is proven in test_task_graph.py); re-testing
        # wall-clock overlap here would just be a flakier copy of that proof.
        deps_of_conflict = set(self.dag.dependencies_of("conflict_check"))
        deps_of_schema = set(self.dag.dependencies_of("schema_validate"))
        self.assertNotIn("schema_validate", deps_of_conflict)
        self.assertNotIn("conflict_check", deps_of_schema)


# ============================================================================
# SpecialistPipelineReport
# ============================================================================

class TestSpecialistPipelineReport(unittest.TestCase):
    def _report(self):
        return sr.SpecialistPipelineReport(
            paper_id=PAPER, job_id="job_x", extraction_type="claims",
            verdicts=[
                sr.SpecialistVerdict(role=sr.ROLE_EXTRACTOR, passed=True, detail="ok"),
                sr.SpecialistVerdict(role=sr.ROLE_SCHEMA_VALIDATOR, passed=True, detail="ok"),
            ],
        )

    def test_verdict_for_finds_the_right_role(self):
        r = self._report()
        v = r.verdict_for(sr.ROLE_EXTRACTOR)
        self.assertIsNotNone(v)
        self.assertEqual(v.role, sr.ROLE_EXTRACTOR)

    def test_verdict_for_missing_role_is_none(self):
        r = self._report()
        self.assertIsNone(r.verdict_for(sr.ROLE_REVIEWER_JUDGE))

    def test_all_specialist_checks_passed_true_when_all_pass(self):
        r = self._report()
        self.assertTrue(r.all_specialist_checks_passed)

    def test_all_specialist_checks_passed_false_on_any_failure(self):
        r = self._report()
        r.verdicts.append(sr.SpecialistVerdict(role=sr.ROLE_CONFLICT_CHECKER,
                                               passed=False, detail="nope"))
        self.assertFalse(r.all_specialist_checks_passed)

    def test_all_specialist_checks_passed_false_with_no_verdicts(self):
        r = sr.SpecialistPipelineReport(paper_id=PAPER, job_id="job_x", extraction_type="claims")
        self.assertFalse(r.all_specialist_checks_passed)

    def test_held_for_review_false_without_admission(self):
        r = self._report()
        self.assertFalse(r.held_for_review)

    def test_has_disagreement_reflects_disagreements_list(self):
        r = self._report()
        self.assertFalse(r.has_disagreement)
        r.disagreements.append(_claim("mem1", "a", "reduces", "b"))
        self.assertTrue(r.has_disagreement)

    def test_to_dict_is_json_shaped(self):
        r = self._report()
        d = r.to_dict()
        self.assertEqual(d["paper_id"], PAPER)
        self.assertEqual(len(d["verdicts"]), 2)
        self.assertIn("all_specialist_checks_passed", d)


# ============================================================================
# End-to-end pipeline
# ============================================================================

class TestRunSpecialistPipelineEndToEnd(unittest.TestCase):
    def test_happy_path_produces_all_four_verdicts_in_role_order(self):
        graph = ResearchGraph()
        report = sr.run_specialist_pipeline(graph, PAPER,
            "Hierarchical orchestration reduces coordination overhead.")
        self.assertEqual([v.role for v in report.verdicts], list(sr.ROLES))

    def test_happy_path_admits_and_holds_for_review_by_default_gate(self):
        # Reference worker's claim confidence (0.85) is below the default gate's
        # require_human_review, so the job holds -- same behavior as
        # WorkerSpawner.admit() unwrapped (see test_workers.py).
        graph = ResearchGraph()
        report = sr.run_specialist_pipeline(graph, PAPER,
            "Hierarchical orchestration reduces coordination overhead.")
        self.assertTrue(report.admission.admitted)
        self.assertTrue(report.held_for_review)
        judge = report.verdict_for(sr.ROLE_REVIEWER_JUDGE)
        self.assertTrue(judge.passed)  # held-for-review is not a specialist failure

    def test_run_result_has_exactly_one_span_per_task(self):
        graph = ResearchGraph()
        report = sr.run_specialist_pipeline(graph, PAPER,
            "Hierarchical orchestration reduces coordination overhead.")
        task_ids = [s.task_id for s in report.run_result.spans]
        self.assertEqual(sorted(task_ids),
                         ["conflict_check", "extract", "reviewer_judge", "schema_validate"])
        self.assertEqual(len(task_ids), len(set(task_ids)))

    def test_all_tasks_complete_on_the_happy_path(self):
        graph = ResearchGraph()
        report = sr.run_specialist_pipeline(graph, PAPER,
            "Hierarchical orchestration reduces coordination overhead.")
        statuses = {s.task_id: s.status for s in report.run_result.spans}
        self.assertTrue(all(v == TaskStatus.COMPLETED.value for v in statuses.values()), statuses)

    def test_unsupported_extraction_type_fails_extractor_and_cascades_skips(self):
        graph = ResearchGraph()
        report = sr.run_specialist_pipeline(graph, PAPER, "text",
                                            extraction_type=ExtractionType.METHODS)
        extractor_verdict = report.verdict_for(sr.ROLE_EXTRACTOR)
        self.assertFalse(extractor_verdict.passed)
        self.assertIsNone(report.verdict_for(sr.ROLE_CONFLICT_CHECKER))
        self.assertIsNone(report.verdict_for(sr.ROLE_SCHEMA_VALIDATOR))
        self.assertIsNone(report.verdict_for(sr.ROLE_REVIEWER_JUDGE))
        self.assertIn("schema_validate", report.run_result.skipped)
        self.assertIn("conflict_check", report.run_result.skipped)
        self.assertIn("reviewer_judge", report.run_result.skipped)
        self.assertIsNone(report.admission)

    def test_conflicting_batch_records_disagreement_and_still_admits(self):
        graph = ResearchGraph()
        existing = _claim("claim_existing", "hierarchical orchestration", "increases",
                          "coordination overhead")
        graph.nodes.append(existing)
        report = sr.run_specialist_pipeline(graph, PAPER,
            "Hierarchical orchestration reduces coordination overhead.")
        conflict_verdict = report.verdict_for(sr.ROLE_CONFLICT_CHECKER)
        self.assertFalse(conflict_verdict.passed)
        self.assertTrue(report.admission.admitted)

    def test_clean_run_without_human_review_requirement_is_allowed_without_holding(self):
        # Prove the reviewer_judge verdict tracks admission across BOTH outcomes
        # (held and clean-allowed), not just the held path exercised above.
        graph = ResearchGraph()
        gate = gates.WorkflowGate(require_human_review=False)
        report = sr.run_specialist_pipeline(
            graph, PAPER, "Hierarchical orchestration reduces coordination overhead.",
            gate=gate)
        self.assertFalse(report.held_for_review)
        judge = report.verdict_for(sr.ROLE_REVIEWER_JUDGE)
        self.assertTrue(judge.passed)

    def test_graph_ends_up_schema_valid_after_a_full_run(self):
        graph = ResearchGraph()
        sr.run_specialist_pipeline(graph, PAPER,
            "Hierarchical orchestration reduces coordination overhead.")
        self.assertTrue(graph.validate().valid, graph.validate().to_dict())

    def test_divergence_threshold_none_default_never_records_even_with_huge_gap(self):
        graph = ResearchGraph()
        text = "Hierarchical orchestration reduces coordination overhead."
        first = sr.run_specialist_pipeline(graph, PAPER, text)
        first.envelope.nodes[0].provenance.confidence = 0.05  # simulate a big prior drift
        second = sr.run_specialist_pipeline(graph, PAPER, text)  # divergence_threshold=None
        self.assertEqual(second.confidence_divergences, [])
        self.assertFalse(second.has_confidence_divergence)

    def test_divergence_threshold_set_records_a_real_gap(self):
        graph = ResearchGraph()
        text = "Hierarchical orchestration reduces coordination overhead."
        first = sr.run_specialist_pipeline(graph, PAPER, text)
        first.envelope.nodes[0].provenance.confidence = 0.05
        second = sr.run_specialist_pipeline(graph, PAPER, text, divergence_threshold=0.2)
        self.assertEqual(len(second.confidence_divergences), 1)
        self.assertTrue(second.has_confidence_divergence)
        record = second.confidence_divergences[0]
        self.assertAlmostEqual(record.properties["details"]["derivation_confidence"], 0.05)

    def test_track_verdict_agreement_off_by_default_end_to_end(self):
        graph = ResearchGraph()
        sr.run_specialist_pipeline(graph, PAPER, "Hierarchical orchestration reduces coordination overhead.")
        comparisons = [n for n in graph.nodes
                      if n.properties.get("memory_kind") == "verdict_comparison"]
        self.assertEqual(comparisons, [])

    def test_track_verdict_agreement_records_end_to_end_when_enabled(self):
        graph = ResearchGraph()
        report = sr.run_specialist_pipeline(
            graph, PAPER, "Hierarchical orchestration reduces coordination overhead.",
            track_verdict_agreement=True)
        comparisons = graph_memory.memory_records_for(graph, report.job_id)
        comparisons = [n for n in comparisons
                      if n.properties.get("memory_kind") == "verdict_comparison"]
        self.assertEqual(len(comparisons), 1)


# ============================================================================
# Selective failure-class recovery
# ============================================================================

class TestResumableTasks(unittest.TestCase):
    def test_failed_and_skipped_are_stale(self):
        dag = sr._build_dag()
        run_result = RunResult(failed={"extract"},
                               skipped={"conflict_check", "schema_validate", "reviewer_judge"})
        self.assertEqual(sr.resumable_tasks(dag, run_result),
                         {"extract", "conflict_check", "schema_validate", "reviewer_judge"})

    def test_downstream_of_a_stale_task_is_also_stale(self):
        dag = sr._build_dag()
        run_result = RunResult(failed={"extract"})
        self.assertEqual(sr.resumable_tasks(dag, run_result),
                         {"extract", "conflict_check", "schema_validate", "reviewer_judge"})

    def test_task_with_no_stale_dependency_is_not_marked_stale(self):
        dag = sr._build_dag()
        run_result = RunResult(failed={"reviewer_judge"})
        self.assertEqual(sr.resumable_tasks(dag, run_result), {"reviewer_judge"})


class TestDiagnosePipelineFailure(unittest.TestCase):
    def _span(self, task_id, status, error=""):
        return TaskSpan(task_id=task_id, agent_id="a", parent_task_id=None,
                        status=status, confidence=None,
                        started_at="2026-07-27T00:00:00+00:00", error=error)

    def test_fully_succeeded_run_returns_none(self):
        dag = sr._build_dag()
        run_result = RunResult(completed={"extract", "conflict_check",
                                          "schema_validate", "reviewer_judge"})
        self.assertIsNone(sr.diagnose_pipeline_failure(dag, run_result))

    def test_extract_failure_cascade_is_not_orchestrator_originated(self):
        dag = sr._build_dag()
        run_result = RunResult(
            failed={"extract"},
            skipped={"conflict_check", "schema_validate", "reviewer_judge"},
            spans=[self._span("extract", TaskStatus.FAILED.value, error="RuntimeError('boom')")],
        )
        diagnosis = sr.diagnose_pipeline_failure(dag, run_result)
        self.assertEqual(diagnosis.root_cause_task_ids, ["extract"])
        self.assertEqual(diagnosis.blast_radius["extract"],
                         sorted(["conflict_check", "schema_validate", "reviewer_judge"]))
        self.assertFalse(diagnosis.orchestrator_originated)
        self.assertEqual(diagnosis.failure_classes["extract"], "worker_reported_failure")
        self.assertIn("extract", diagnosis.summary)

    def test_reviewer_judge_failure_alone_is_orchestrator_originated(self):
        """No downstream tasks to skip -- reviewer_judge has no dependents in
        this DAG -- but the failure still originated at the orchestrating
        role itself, which the diagnosis must surface distinctly from a
        cascade."""
        dag = sr._build_dag()
        run_result = RunResult(
            failed={"reviewer_judge"},
            spans=[self._span("reviewer_judge", TaskStatus.FAILED.value, error="KeyError('nope')")],
        )
        diagnosis = sr.diagnose_pipeline_failure(dag, run_result)
        self.assertEqual(diagnosis.root_cause_task_ids, ["reviewer_judge"])
        self.assertEqual(diagnosis.blast_radius["reviewer_judge"], [])
        self.assertTrue(diagnosis.orchestrator_originated)
        self.assertIn("orchestrating role", diagnosis.summary)

    def test_custom_classifier_is_used_for_root_causes(self):
        dag = sr._build_dag()
        run_result = RunResult(
            failed={"extract"},
            skipped={"conflict_check", "schema_validate", "reviewer_judge"},
            spans=[self._span("extract", TaskStatus.FAILED.value, error="boom")],
        )
        diagnosis = sr.diagnose_pipeline_failure(
            dag, run_result, classifier=lambda span: "custom_label")
        self.assertEqual(diagnosis.failure_classes["extract"], "custom_label")

    def test_to_dict_is_json_shaped(self):
        dag = sr._build_dag()
        run_result = RunResult(
            failed={"extract"},
            skipped={"conflict_check", "schema_validate", "reviewer_judge"},
            spans=[self._span("extract", TaskStatus.FAILED.value, error="boom")],
        )
        d = sr.diagnose_pipeline_failure(dag, run_result).to_dict()
        self.assertEqual(d["root_cause_task_ids"], ["extract"])
        self.assertIn("blast_radius", d)
        self.assertIn("failure_classes", d)
        self.assertIn("summary", d)
        self.assertIn("rationale", d)
        self.assertIn("attribution_confidence", d)

    def test_rationale_names_the_actual_error_for_each_root_cause(self):
        dag = sr._build_dag()
        run_result = RunResult(
            failed={"extract"},
            skipped={"conflict_check", "schema_validate", "reviewer_judge"},
            spans=[self._span("extract", TaskStatus.FAILED.value, error="RuntimeError('boom')")],
        )
        diagnosis = sr.diagnose_pipeline_failure(dag, run_result)
        self.assertIn("extract", diagnosis.rationale)
        self.assertIn("boom", diagnosis.rationale["extract"])

    def test_attribution_confidence_is_full_certainty_in_this_dags_shape(self):
        dag = sr._build_dag()
        run_result = RunResult(
            failed={"reviewer_judge"},
            spans=[self._span("reviewer_judge", TaskStatus.FAILED.value, error="KeyError('nope')")],
        )
        diagnosis = sr.diagnose_pipeline_failure(dag, run_result)
        self.assertEqual(diagnosis.attribution_confidence, {"reviewer_judge": 1.0})

    def test_rationale_and_confidence_cover_every_root_cause_not_just_one(self):
        """Two genuinely simultaneous root causes (not producible by this
        DAG's own code, but the function must not assume exactly one)."""
        dag = sr._build_dag()
        run_result = RunResult(
            failed={"conflict_check", "schema_validate"},
            spans=[
                self._span("conflict_check", TaskStatus.FAILED.value, error="boom1"),
                self._span("schema_validate", TaskStatus.FAILED.value, error="boom2"),
            ],
        )
        diagnosis = sr.diagnose_pipeline_failure(dag, run_result)
        self.assertEqual(set(diagnosis.rationale), {"conflict_check", "schema_validate"})
        self.assertEqual(set(diagnosis.attribution_confidence), {"conflict_check", "schema_validate"})

    def test_diagnoses_a_real_scheduler_produced_run_result(self):
        """Same real DAG, same real Scheduler run this module's own
        end-to-end tests exercise -- not just a hand-built RunResult."""
        graph = ResearchGraph()
        report = sr.run_specialist_pipeline(graph, PAPER, "text",
                                            extraction_type=ExtractionType.METHODS)
        diagnosis = sr.diagnose_pipeline_failure(sr._build_dag(), report.run_result)
        self.assertEqual(diagnosis.root_cause_task_ids, ["extract"])
        self.assertFalse(diagnosis.orchestrator_originated)
        self.assertEqual(set(diagnosis.blast_radius["extract"]),
                         {"conflict_check", "schema_validate", "reviewer_judge"})


class TestClassifySpecialistFailure(unittest.TestCase):
    def _span(self, task_id, status=TaskStatus.FAILED.value, error=""):
        return TaskSpan(task_id=task_id, agent_id="a", parent_task_id=None,
                        status=status, confidence=None,
                        started_at="2026-07-27T00:00:00+00:00", error=error)

    def test_unsupported_extraction_type(self):
        span = self._span("extract", error="RuntimeError('unsupported extraction_type methods')")
        self.assertEqual(sr.classify_specialist_failure(span), "unsupported_extraction_type")

    def test_other_extract_failure_is_worker_reported(self):
        span = self._span("extract", error="RuntimeError('boom')")
        self.assertEqual(sr.classify_specialist_failure(span), "worker_reported_failure")

    def test_non_extract_failure_is_specialist_internal_error(self):
        span = self._span("reviewer_judge", error="KeyError('nope')")
        self.assertEqual(sr.classify_specialist_failure(span), "specialist_internal_error")

    def test_non_failed_span_is_unclassified(self):
        span = self._span("extract", status=TaskStatus.COMPLETED.value)
        self.assertEqual(sr.classify_specialist_failure(span), "unclassified")


class _AlwaysFailsWorker:
    def run(self, directive, text):
        return ResultEnvelope(directive.job_id, "flaky_worker", worker_status="failed",
                              error="simulated transient failure")


class TestResumeSpecialistPipeline(unittest.TestCase):
    TEXT = "Hierarchical orchestration reduces coordination overhead."

    def _completed_up_to_reviewer_judge(self, graph):
        """Build a previous_report as if extract/schema_validate/conflict_check
        all completed successfully but reviewer_judge failed -- the one
        realistic partial-staleness pattern this DAG's code can produce
        (conflict_check/schema_validate never raise on valid input)."""
        spawner = WorkerSpawner(graph)
        job, directive = spawner.spawn(PAPER, ExtractionType.CLAIMS)
        env = ReferenceWorker().run(directive, self.TEXT)
        extractor_v = sr.verdict_from_extraction(env)
        schema_v = sr.verdict_from_schema_validation(env.nodes)
        conflict_v = sr.verdict_from_conflict_check(env.nodes, [])
        ts = "2026-07-27T00:00:00+00:00"
        run_result = RunResult(
            spans=[
                TaskSpan("extract", sr.ROLE_EXTRACTOR, None, TaskStatus.COMPLETED.value,
                        extractor_v.confidence, ts),
                TaskSpan("schema_validate", sr.ROLE_SCHEMA_VALIDATOR, None,
                        TaskStatus.COMPLETED.value, None, ts),
                TaskSpan("conflict_check", sr.ROLE_CONFLICT_CHECKER, None,
                        TaskStatus.COMPLETED.value, None, ts),
                TaskSpan("reviewer_judge", sr.ROLE_REVIEWER_JUDGE, None,
                        TaskStatus.FAILED.value, None, ts, error="KeyError('simulated')"),
            ],
            completed={"extract", "schema_validate", "conflict_check"},
            failed={"reviewer_judge"},
        )
        return sr.SpecialistPipelineReport(
            paper_id=PAPER, job_id=directive.job_id, extraction_type=ExtractionType.CLAIMS.value,
            verdicts=[extractor_v, schema_v, conflict_v],
            admission=None, disagreements=[], run_result=run_result, envelope=env,
        )

    def test_selective_resume_only_reruns_reviewer_judge(self):
        graph = ResearchGraph()
        previous = self._completed_up_to_reviewer_judge(graph)
        resumed = sr.resume_specialist_pipeline(graph, PAPER, self.TEXT, previous)
        self.assertEqual({s.task_id for s in resumed.run_result.spans}, {"reviewer_judge"})
        self.assertTrue(resumed.admission.admitted)
        self.assertIsNotNone(resumed.verdict_for(sr.ROLE_EXTRACTOR))
        self.assertIsNotNone(resumed.verdict_for(sr.ROLE_SCHEMA_VALIDATOR))
        self.assertIsNotNone(resumed.verdict_for(sr.ROLE_CONFLICT_CHECKER))

    def test_classifier_excluding_the_failure_class_skips_retry_entirely(self):
        graph = ResearchGraph()
        previous = self._completed_up_to_reviewer_judge(graph)
        resumed = sr.resume_specialist_pipeline(
            graph, PAPER, self.TEXT, previous,
            classifier=sr.classify_specialist_failure,
            retryable_classes={"worker_reported_failure"},  # excludes specialist_internal_error
        )
        self.assertIs(resumed, previous)

    def test_classifier_allowing_the_failure_class_still_retries(self):
        graph = ResearchGraph()
        previous = self._completed_up_to_reviewer_judge(graph)
        resumed = sr.resume_specialist_pipeline(
            graph, PAPER, self.TEXT, previous,
            classifier=sr.classify_specialist_failure,
            retryable_classes={"specialist_internal_error"},
        )
        self.assertEqual({s.task_id for s in resumed.run_result.spans}, {"reviewer_judge"})

    def test_fully_succeeded_run_returns_previous_report_unchanged(self):
        graph = ResearchGraph()
        report = sr.run_specialist_pipeline(graph, PAPER, self.TEXT)
        resumed = sr.resume_specialist_pipeline(graph, PAPER, self.TEXT, report)
        self.assertIs(resumed, report)

    def test_selective_resume_without_envelope_raises_clearly(self):
        graph = ResearchGraph()
        previous = self._completed_up_to_reviewer_judge(graph)
        previous.envelope = None
        with self.assertRaises(ValueError):
            sr.resume_specialist_pipeline(graph, PAPER, self.TEXT, previous)

    def test_extract_failure_redoes_the_whole_pipeline_and_can_then_succeed(self):
        graph = ResearchGraph()
        report = sr.run_specialist_pipeline(graph, PAPER, self.TEXT, worker=_AlwaysFailsWorker())
        self.assertIsNone(report.admission)
        self.assertIn("conflict_check", report.run_result.skipped)

        resumed = sr.resume_specialist_pipeline(graph, PAPER, self.TEXT, report)
        self.assertEqual({s.task_id for s in resumed.run_result.spans},
                         {"extract", "conflict_check", "schema_validate", "reviewer_judge"})
        self.assertTrue(resumed.admission.admitted)


if __name__ == "__main__":
    unittest.main()
