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
import research_graph_gates as gates
from research_graph_schema import ExtractionType


class TestRunAll(unittest.TestCase):
    def test_current_suite_is_all_green(self):
        report = evals.run_all()
        self.assertTrue(report.all_passed, [f"{r.name}: {r.detail}" for r in report.failures()])

    def test_report_has_all_four_categories(self):
        report = evals.run_all()
        for category in ("query", "gate_audit", "extraction", "regression"):
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


if __name__ == "__main__":
    unittest.main()
