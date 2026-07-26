#!/usr/bin/env python3
"""
Test suite for graph_roadmap.py: the rollup answering gap_roadmap_queries from
literature_corpus.py itself -- proving the survey's own most-cited gap
(multi-dimensional review, 5 papers) surfaces correctly.
"""

import unittest

import golden_fixtures as gf
import literature_corpus as corpus
from research_graph_schema import NodeType
import graph_roadmap as roadmap


class TestRoadmapSummary(unittest.TestCase):
    def setUp(self):
        self.graph = corpus.build_corpus_graph()

    def test_four_gap_rows_returned(self):
        rows = roadmap.roadmap_summary(self.graph, NodeType.GAP)
        self.assertEqual(len(rows), 4)

    def test_sorted_by_paper_count_descending(self):
        rows = roadmap.roadmap_summary(self.graph, NodeType.GAP)
        counts = [r["paper_count"] for r in rows]
        self.assertEqual(counts, sorted(counts, reverse=True))

    def test_multidim_review_is_the_best_attested_gap(self):
        rows = roadmap.roadmap_summary(self.graph, NodeType.GAP)
        top = rows[0]
        self.assertEqual(top["id"], "gap_multidim_review")
        self.assertEqual(top["paper_count"], 5)

    def test_roadmap_queries_gap_has_exactly_its_own_paper(self):
        rows = roadmap.roadmap_summary(self.graph, NodeType.GAP)
        row = next(r for r in rows if r["id"] == "gap_roadmap_queries")
        self.assertEqual(row["paper_count"], 1)
        self.assertEqual(row["papers"], [("paper_2605_15011",
                                           "The Scientific Contribution Graph: "
                                           "Automated Literature-based Technological Roadmapping at Scale")])

    def test_attribution_walks_claim_back_to_producing_paper(self):
        rows = roadmap.roadmap_summary(self.graph, NodeType.GAP)
        row = next(r for r in rows if r["id"] == "gap_claim_source_verify")
        paper_ids = {pid for pid, _ in row["papers"]}
        self.assertEqual(paper_ids, {"paper_2607_04043", "paper_2605_03042"})

    def test_unknown_node_type_rejected(self):
        with self.assertRaises(ValueError):
            roadmap.roadmap_summary(self.graph, NodeType.PAPER)


class TestFullRoadmap(unittest.TestCase):
    def test_only_includes_node_types_present_in_graph(self):
        full = roadmap.full_roadmap(corpus.build_corpus_graph())
        self.assertEqual(set(full.keys()), {NodeType.GAP.value})

    def test_empty_graph_yields_empty_roadmap(self):
        empty = gf.build_fixture_graph()  # no GAP/METHOD/DOMAIN/BENCHMARK nodes
        self.assertEqual(roadmap.full_roadmap(empty), {})


class TestRenderRoadmapReport(unittest.TestCase):
    def test_report_mentions_top_gap_and_its_count(self):
        report = roadmap.render_roadmap_report(corpus.build_corpus_graph())
        self.assertIn("[5] gap_multidim_review", report)

    def test_report_on_empty_graph_says_so(self):
        report = roadmap.render_roadmap_report(gf.build_fixture_graph())
        self.assertIn("no GAP/METHOD/DOMAIN/BENCHMARK nodes", report)


if __name__ == "__main__":
    unittest.main()
