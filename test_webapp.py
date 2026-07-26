#!/usr/bin/env python3
"""
Test suite for webapp.py: every page must render, the query box must dispatch
to the real graph_queries functions (not some UI-only reimplementation), and
bad input must come back as a readable error, never a 500.
"""

import unittest

from fastapi.testclient import TestClient

import webapp
from webapp import execute_query, GRAPH


class TestPagesRender(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(webapp.app)

    def test_overview_page_ok(self):
        r = self.client.get("/")
        self.assertEqual(r.status_code, 200)
        self.assertIn("Nodes by type", r.text)

    def test_blocked_page_lists_the_held_job(self):
        r = self.client.get("/blocked")
        self.assertEqual(r.status_code, 200)
        self.assertIn("job_2606_concepts_001", r.text)
        self.assertIn("LOW_CONFIDENCE", r.text)

    def test_conflicts_page_lists_the_fixture_conflict(self):
        r = self.client.get("/conflicts")
        self.assertEqual(r.status_code, 200)
        self.assertIn("claim_2606_001", r.text)
        self.assertIn("claim_2701_014", r.text)

    def test_papers_page_lists_known_paper(self):
        r = self.client.get("/papers")
        self.assertEqual(r.status_code, 200)
        self.assertIn("paper_2606.13707", r.text)

    def test_paper_drilldown_shows_its_claim(self):
        r = self.client.get("/papers/paper_2606.13707")
        self.assertEqual(r.status_code, 200)
        self.assertIn("claim_2606_001", r.text)
        self.assertIn("Hierarchical orchestration", r.text)

    def test_paper_drilldown_unknown_id_is_not_found_not_500(self):
        r = self.client.get("/papers/does-not-exist")
        self.assertEqual(r.status_code, 200)
        self.assertIn("No paper with id", r.text)

    def test_review_queue_lists_pending_task(self):
        r = self.client.get("/review-queue")
        self.assertEqual(r.status_code, 200)
        self.assertIn("review_2606_concepts_001", r.text)

    def test_query_page_with_no_query_shows_help(self):
        r = self.client.get("/query")
        self.assertEqual(r.status_code, 200)
        self.assertIn("Supported queries", r.text)

    def test_query_page_runs_a_real_query(self):
        r = self.client.get("/query", params={"q": "search adversarial"})
        self.assertEqual(r.status_code, 200)
        self.assertIn("paper_2605_03042", r.text)

    def test_query_page_bad_verb_shows_error_not_500(self):
        r = self.client.get("/query", params={"q": "not_a_real_verb"})
        self.assertEqual(r.status_code, 200)
        self.assertIn("Error", r.text)


class TestQueryApi(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(webapp.app)

    def test_search_returns_matching_nodes(self):
        r = self.client.get("/api/query", params={"q": "search adversarial"})
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertTrue(body["ok"])
        self.assertIn("paper_2605_03042", {row["id"] for row in body["results"]})

    def test_why_blocked_returns_live_gate_decision(self):
        r = self.client.get("/api/query", params={"q": "why_blocked job_2606_concepts_001"})
        body = r.json()
        self.assertTrue(body["ok"])
        self.assertEqual(body["results"][0]["reason_code"], "LOW_CONFIDENCE")

    def test_unknown_verb_returns_400_not_500(self):
        r = self.client.get("/api/query", params={"q": "not_a_real_verb"})
        self.assertEqual(r.status_code, 400)
        self.assertFalse(r.json()["ok"])

    def test_status_matches_graph_queries_directly(self):
        import graph_queries as q
        r = self.client.get("/api/query", params={"q": "status"})
        api_summary = r.json()["results"][0]
        direct_summary = q.status_summary(GRAPH)
        self.assertEqual(api_summary, direct_summary)


class TestExecuteQueryDispatch(unittest.TestCase):
    """execute_query must be a thin dispatcher -- same answers as calling
    graph_queries directly, not a parallel reimplementation that can drift."""

    def test_claims_for_matches_graph_queries(self):
        import graph_queries as q
        via_ui = {r["id"] for r in execute_query(GRAPH, "claims_for paper_2606.13707")}
        via_direct = {n.id for n in q.claims_for_paper(GRAPH, "paper_2606.13707")}
        self.assertEqual(via_ui, via_direct)

    def test_contradicting_matches_graph_queries(self):
        import graph_queries as q
        via_ui = {r["id"] for r in execute_query(GRAPH, "contradicting claim_2606_001")}
        via_direct = {n.id for n in q.contradicting_claims(GRAPH, "claim_2606_001")}
        self.assertEqual(via_ui, via_direct)

    def test_neighbors_with_edge_type_and_direction(self):
        rows = execute_query(GRAPH, "neighbors paper_2606.13707 produces out")
        self.assertIn("claim_2606_001", {r["id"] for r in rows})

    def test_empty_query_raises_value_error(self):
        with self.assertRaises(ValueError):
            execute_query(GRAPH, "   ")

    def test_missing_argument_raises_value_error(self):
        with self.assertRaises(ValueError):
            execute_query(GRAPH, "search")

    def test_unknown_verb_raises_value_error(self):
        with self.assertRaises(ValueError):
            execute_query(GRAPH, "frobnicate everything")


if __name__ == "__main__":
    unittest.main()
