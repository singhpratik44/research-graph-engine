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
from task_graph import TaskStatus
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


if __name__ == "__main__":
    unittest.main()
