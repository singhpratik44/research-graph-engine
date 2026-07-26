#!/usr/bin/env python3
"""
Test suite for graph_queries.py: the structured, agent-facing query layer built
on top of the inspection surface. Every function must return live data (nodes,
edges, gate decisions) -- not text -- and must reflect the graph's current
state, the same contract graph_inspector.py already proved for "why blocked".
"""

import unittest

import golden_fixtures as gf
import literature_corpus as corpus
import research_graph_gates as gates
from research_graph_schema import EdgeType, NodeType
import graph_queries as q


class TestGetNodeAndNeighbors(unittest.TestCase):
    def setUp(self):
        self.graph = gf.build_fixture_graph()

    def test_get_node_returns_known_node(self):
        n = q.get_node(self.graph, "claim_2606_001")
        self.assertIsNotNone(n)
        self.assertEqual(n.type, NodeType.CLAIM.value)

    def test_get_node_returns_none_for_unknown_id(self):
        self.assertIsNone(q.get_node(self.graph, "nope"))

    def test_neighbors_out_follows_produces_edge(self):
        paper_id = "paper_2606.13707"
        out = q.neighbors(self.graph, paper_id, edge_type=EdgeType.PRODUCES.value)
        self.assertIn("claim_2606_001", [n.id for n in out])

    def test_neighbors_in_is_reverse_of_out(self):
        paper_id = "paper_2606.13707"
        forward = q.neighbors(self.graph, paper_id, edge_type=EdgeType.PRODUCES.value, direction="out")
        for n in forward:
            back = q.neighbors(self.graph, n.id, edge_type=EdgeType.PRODUCES.value, direction="in")
            self.assertIn(paper_id, [b.id for b in back])

    def test_neighbors_rejects_bad_direction(self):
        with self.assertRaises(ValueError):
            q.neighbors(self.graph, "claim_2606_001", direction="sideways")


class TestClaimsForPaper(unittest.TestCase):
    def test_returns_the_papers_claims_only(self):
        graph = gf.build_fixture_graph()
        claims = q.claims_for_paper(graph, "paper_2606.13707")
        self.assertEqual({c.id for c in claims}, {"claim_2606_001"})

    def test_unknown_paper_returns_empty(self):
        graph = gf.build_fixture_graph()
        self.assertEqual(q.claims_for_paper(graph, "paper_nope"), [])


class TestConflicts(unittest.TestCase):
    def setUp(self):
        self.graph = gf.build_fixture_graph()

    def test_unresolved_conflicts_lists_the_fixture_conflict(self):
        conflicts = q.unresolved_conflicts(self.graph)
        self.assertEqual(len(conflicts), 1)
        self.assertEqual(conflicts[0].source_claim_id, "claim_2606_001")

    def test_resolved_conflict_excluded(self):
        self.graph.conflicts[0].resolved = True
        self.assertEqual(q.unresolved_conflicts(self.graph), [])

    def test_contradicting_claims_is_symmetric(self):
        a = q.contradicting_claims(self.graph, "claim_2606_001")
        b = q.contradicting_claims(self.graph, "claim_2701_014")
        self.assertEqual([n.id for n in a], ["claim_2701_014"])
        self.assertEqual([n.id for n in b], ["claim_2606_001"])

    def test_resolved_conflict_excluded_from_contradicting_claims(self):
        self.graph.conflicts[0].resolved = True
        self.assertEqual(q.contradicting_claims(self.graph, "claim_2606_001"), [])
        self.assertEqual(
            [n.id for n in q.contradicting_claims(self.graph, "claim_2606_001", include_resolved=True)],
            ["claim_2701_014"],
        )

    def test_claim_with_no_conflicts_returns_empty(self):
        graph = corpus.build_corpus_graph()
        self.assertEqual(q.contradicting_claims(graph, "claim_paper_2606_04990_relevance"), [])


class TestWhyBlockedAndBlockedJobs(unittest.TestCase):
    def test_why_blocked_on_low_confidence_job(self):
        graph = gf.build_fixture_graph()
        decision = q.why_blocked(graph, "job_2606_concepts_001")
        self.assertFalse(decision.can_proceed)
        self.assertEqual(decision.reason_code, gates.GateReasonCode.LOW_CONFIDENCE)

    def test_why_blocked_unknown_node_raises(self):
        graph = gf.build_fixture_graph()
        with self.assertRaises(KeyError):
            q.why_blocked(graph, "nonexistent")

    def test_why_blocked_reflects_waiver_applied_after_hold(self):
        waived = gf.waived_graph()
        decision = q.why_blocked(waived, "job_2606_concepts_001")
        self.assertTrue(decision.can_proceed)
        self.assertEqual(decision.reason_code, gates.GateReasonCode.ALLOWED_BY_WAIVER)

    def test_blocked_jobs_lists_only_the_held_job(self):
        graph = gf.build_fixture_graph()
        blocked = q.blocked_jobs(graph)
        self.assertEqual({d.node_id for d in blocked}, {"job_2606_concepts_001"})

    def test_blocked_jobs_empty_once_waived(self):
        waived = gf.waived_graph()
        self.assertEqual(q.blocked_jobs(waived), [])


class TestSearch(unittest.TestCase):
    def test_search_matches_paper_title(self):
        graph = corpus.build_corpus_graph()
        found = q.search(graph, "adversarial")
        ids = {n.id for n in found}
        self.assertIn("paper_2605_03042", ids)

    def test_search_is_case_insensitive(self):
        graph = corpus.build_corpus_graph()
        self.assertEqual(
            {n.id for n in q.search(graph, "ARIS")},
            {n.id for n in q.search(graph, "aris")},
        )

    def test_search_matches_claim_properties(self):
        graph = corpus.build_corpus_graph()
        found = q.search(graph, "roadmap rollup query")
        self.assertIn("claim_paper_2605_15011_relevance", {n.id for n in found})

    def test_search_no_match_returns_empty(self):
        graph = corpus.build_corpus_graph()
        self.assertEqual(q.search(graph, "quantum teleportation"), [])


class TestStatusSummary(unittest.TestCase):
    def test_counts_match_fixture_graph(self):
        graph = gf.build_fixture_graph()
        summary = q.status_summary(graph)
        self.assertEqual(summary["nodes_by_type"][NodeType.PAPER.value], 1)
        self.assertEqual(summary["nodes_by_type"][NodeType.CLAIM.value], 2)
        self.assertEqual(summary["job_status"]["completed"], 1)
        self.assertEqual(summary["job_status"]["held"], 1)
        self.assertEqual(summary["review_status"]["pending"], 1)
        self.assertEqual(summary["unresolved_conflicts"], 1)

    def test_counts_match_corpus_graph(self):
        graph = corpus.build_corpus_graph()
        summary = q.status_summary(graph)
        self.assertEqual(summary["nodes_by_type"][NodeType.PAPER.value], 20)
        self.assertEqual(summary["nodes_by_type"][NodeType.GAP.value], 5)


if __name__ == "__main__":
    unittest.main()
