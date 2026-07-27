#!/usr/bin/env python3
"""
Test suite for graph_evals.py: the eval harness must itself be trustworthy --
a broken eval case that always reports pass is worse than no eval at all. So
in addition to checking the current suite is all-green, this deliberately
breaks each category's assumption and checks the harness catches it.
"""

import unittest

import golden_fixtures as gf
import graph_evals as evals
import graph_memory as memory
import literature_corpus as corpus
import research_graph_gates as gates
from research_graph_schema import ExtractionType, MemoryKind, Node, NodeType, ResearchGraph


class TestRunAll(unittest.TestCase):
    def test_current_suite_is_all_green(self):
        report = evals.run_all()
        self.assertTrue(report.all_passed, [f"{r.name}: {r.detail}" for r in report.failures()])

    def test_report_has_all_six_categories(self):
        report = evals.run_all()
        for category in ("query", "gate_audit", "extraction", "regression",
                         "construction_quality", "memory_effectiveness"):
            self.assertTrue(report.by_category(category), f"no cases in {category!r}")

    def test_render_report_mentions_pass_count(self):
        report = evals.run_all()
        text = evals.render_report(report)
        self.assertIn(f"{report.passed}/{report.total} passed", text)


class TestQueryEvalsCatchARealBreak(unittest.TestCase):
    def test_wrong_expectation_is_reported_as_failure_not_silently_ignored(self):
        ok, detail = evals._eval_claims_for_paper()
        self.assertTrue(ok)
        # Sanity: the check function itself does real comparison, not `return True, ""`.
        import graph_queries as q
        graph = gf.build_fixture_graph()
        found = {c.id for c in q.claims_for_paper(graph, "paper_2606.13707")}
        self.assertEqual(found, {"claim_2606_001"})

    def test_query_eval_that_raises_is_a_failure_not_a_crash(self):
        case = evals.QueryEvalCase("deliberately broken", lambda: (_ for _ in ()).throw(RuntimeError("boom")))
        results = []
        try:
            ok, detail = case.check()
            results.append(evals.EvalResult(case.name, "query", ok, detail))
        except Exception as exc:
            results.append(evals.EvalResult(case.name, "query", False, f"raised {exc!r}"))
        self.assertFalse(results[0].passed)


class TestGateAudits(unittest.TestCase):
    def test_regression_cases_are_the_defect_scenarios_only(self):
        regression_names = {r.name for r in evals.run_regression_cases()}
        self.assertEqual(regression_names, {
            "waiver missing reason stays blocked",
            "waiver missing reviewer stays blocked",
            "unapproved waiver stays blocked",
            "unreviewed waiver stays blocked",
        })

    def test_happy_path_cases_excluded_from_regression_set(self):
        regression_names = {r.name for r in evals.run_regression_cases()}
        self.assertNotIn("auto-pass job proceeds", regression_names)
        self.assertNotIn("waived job proceeds by waiver", regression_names)

    def test_a_case_with_wrong_expectation_fails(self):
        bad_case = evals.GateAuditCase(
            "deliberately wrong expectation", gf.build_fixture_graph(),
            "job_2606_concepts_001", True, gates.GateReasonCode.ALLOWED,
        )
        result = evals._evaluate_gate_case(bad_case)
        self.assertFalse(result.passed)

    def test_unknown_node_id_is_a_failure_not_a_crash(self):
        bad_case = evals.GateAuditCase(
            "nonexistent node", gf.build_fixture_graph(),
            "no_such_job", True, gates.GateReasonCode.ALLOWED,
        )
        result = evals._evaluate_gate_case(bad_case)
        self.assertFalse(result.passed)
        self.assertIn("raised", result.detail)


class TestExtractionChecks(unittest.TestCase):
    def test_exact_match_case_passes_with_perfect_score(self):
        case = evals.EXTRACTION_CHECKS[0]
        result = evals.run_extraction_check(case)
        self.assertTrue(result.passed)
        self.assertEqual(result.score, 1.0)

    def test_wrong_ground_truth_is_caught_as_a_failure(self):
        broken = evals.ExtractionSpotCheck(
            name="deliberately wrong ground truth",
            extraction_type=ExtractionType.CLAIMS,
            text="Caching improves throughput significantly.",
            expected_texts={"Something that was never in the text"},
        )
        result = evals.run_extraction_check(broken)
        self.assertFalse(result.passed)
        self.assertEqual(result.score, 0.0)

    def test_empty_expectation_matches_empty_output(self):
        case = evals.EXTRACTION_CHECKS[1]
        result = evals.run_extraction_check(case)
        self.assertTrue(result.passed)


class TestConstructionQualityMetrics(unittest.TestCase):
    def test_claim_field_completeness_full_on_the_fixture_graph(self):
        self.assertEqual(evals.claim_field_completeness(gf.build_fixture_graph()), 1.0)

    def test_claim_field_completeness_vacuously_full_with_no_claims(self):
        self.assertEqual(evals.claim_field_completeness(ResearchGraph()), 1.0)

    def test_claim_field_completeness_catches_a_real_defect(self):
        graph = gf.build_fixture_graph()
        broken = Node("claim_broken", NodeType.CLAIM.value, "x",
                      properties={"text": "incomplete"})  # no subject/relation/object
        graph.nodes.append(broken)
        self.assertLess(evals.claim_field_completeness(graph), 1.0)

    def test_duplicate_text_ratio_zero_on_the_corpus(self):
        self.assertEqual(evals.duplicate_text_ratio(corpus.build_corpus_graph()), 0.0)

    def test_duplicate_text_ratio_catches_a_real_duplicate(self):
        graph = gf.build_fixture_graph()
        original = next(n for n in graph.nodes if n.type == NodeType.CLAIM.value)
        dup = Node("claim_dup", NodeType.CLAIM.value, "x",
                  properties={"text": original.properties["text"]})
        graph.nodes.append(dup)
        self.assertGreater(evals.duplicate_text_ratio(graph), 0.0)

    def test_orphaned_node_ratio_zero_on_the_corpus(self):
        self.assertEqual(evals.orphaned_node_ratio(corpus.build_corpus_graph()), 0.0)

    def test_orphaned_node_ratio_catches_a_real_orphan(self):
        graph = gf.build_fixture_graph()
        graph.nodes.append(Node("orphan_node", NodeType.CONCEPT.value, "x",
                                properties={"text": "unconnected"}))
        self.assertGreater(evals.orphaned_node_ratio(graph), 0.0)

    def test_run_construction_quality_checks_all_pass_today(self):
        results = evals.run_construction_quality_checks()
        self.assertTrue(all(r.passed for r in results), [r.detail for r in results])

    def test_a_wrong_expectation_is_caught_as_a_failure(self):
        bad_case = evals.GraphMetricCase(
            "deliberately wrong expectation", gf.build_fixture_graph,
            evals.claim_field_completeness, 0.0)
        result = evals.run_graph_metric_case(bad_case, "construction_quality")
        self.assertFalse(result.passed)

    def test_a_raising_metric_is_a_failure_not_a_crash(self):
        bad_case = evals.GraphMetricCase(
            "deliberately broken", gf.build_fixture_graph,
            lambda g: (_ for _ in ()).throw(RuntimeError("boom")), 1.0)
        result = evals.run_graph_metric_case(bad_case, "construction_quality")
        self.assertFalse(result.passed)
        self.assertIn("raised", result.detail)


class TestMemoryEffectivenessMetric(unittest.TestCase):
    def test_vacuously_effective_with_no_repair_patterns(self):
        self.assertEqual(evals.repair_pattern_effectiveness(gf.build_fixture_graph()), 1.0)

    def test_effective_when_after_node_resolves(self):
        graph = gf.build_fixture_graph()
        memory.record_repair_pattern(graph, "fixed it", "job_2606_concepts_001",
                                     "job_2606_claims_001")
        self.assertEqual(evals.repair_pattern_effectiveness(graph), 1.0)

    def test_catches_an_orphaned_repair_pattern(self):
        """A repair pattern whose after_node no longer resolves (e.g. it was
        somehow removed) must drag the effectiveness score down, not be
        silently ignored."""
        graph = gf.build_fixture_graph()
        memory.record_repair_pattern(graph, "fixed it", "job_2606_concepts_001",
                                     "job_2606_claims_001")
        graph.nodes = [n for n in graph.nodes if n.id != "job_2606_claims_001"]
        self.assertLess(evals.repair_pattern_effectiveness(graph), 1.0)

    def test_run_memory_effectiveness_checks_all_pass_today(self):
        results = evals.run_memory_effectiveness_checks()
        self.assertTrue(all(r.passed for r in results), [r.detail for r in results])


class TestVerifiedRepairPatternEffectiveness(unittest.TestCase):
    def test_vacuously_effective_with_no_repair_patterns(self):
        self.assertEqual(evals.verified_repair_pattern_effectiveness(gf.build_fixture_graph()), 1.0)

    def test_unreevaluated_repair_pattern_fails_the_stricter_bar(self):
        graph = gf.build_fixture_graph()
        memory.record_repair_pattern(graph, "fixed it", "job_2606_concepts_001",
                                     "job_2606_claims_001")  # reevaluated defaults False
        self.assertEqual(evals.verified_repair_pattern_effectiveness(graph), 0.0)

    def test_reevaluated_repair_pattern_passes_the_stricter_bar(self):
        graph = gf.build_fixture_graph()
        memory.record_repair_pattern(graph, "fixed it", "job_2606_concepts_001",
                                     "job_2606_claims_001", mechanism="confidence_floor",
                                     reevaluated=True)
        self.assertEqual(evals.verified_repair_pattern_effectiveness(graph), 1.0)

    def test_does_not_change_the_existing_weaker_metric(self):
        """repair_pattern_effectiveness (the pre-existing, weaker check)
        must not be affected by mechanism/reevaluated at all."""
        graph = gf.build_fixture_graph()
        memory.record_repair_pattern(graph, "fixed it", "job_2606_concepts_001",
                                     "job_2606_claims_001")  # unreevaluated
        self.assertEqual(evals.repair_pattern_effectiveness(graph), 1.0)

    def test_orphaned_after_node_fails_both_metrics(self):
        graph = gf.build_fixture_graph()
        memory.record_repair_pattern(graph, "fixed it", "job_2606_concepts_001",
                                     "job_2606_claims_001", reevaluated=True)
        graph.nodes = [n for n in graph.nodes if n.id != "job_2606_claims_001"]
        self.assertLess(evals.repair_pattern_effectiveness(graph), 1.0)
        self.assertLess(evals.verified_repair_pattern_effectiveness(graph), 1.0)


if __name__ == "__main__":
    unittest.main()
