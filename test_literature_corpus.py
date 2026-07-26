#!/usr/bin/env python3
"""
Test suite for literature_corpus.py: the July 2026 survey corpus must be a
conforming graph like any other — schema-valid, and every claim's ADDRESSES
edge must land on a gap that actually exists.
"""

import unittest

import literature_corpus as corpus
from research_graph_schema import NodeType, EdgeType


class TestLiteratureCorpusGraph(unittest.TestCase):
    def setUp(self):
        self.graph = corpus.build_corpus_graph()

    def test_graph_is_schema_valid(self):
        result = self.graph.validate()
        self.assertTrue(result.valid, msg=[e.message for e in result.errors])

    def test_ten_papers_present(self):
        papers = [n for n in self.graph.nodes if n.type == NodeType.PAPER.value]
        self.assertEqual(len(papers), 10)

    def test_four_gaps_present(self):
        gaps = [n for n in self.graph.nodes if n.type == NodeType.GAP.value]
        self.assertEqual(len(gaps), 4)

    def test_every_paper_produces_exactly_one_claim(self):
        produces = [e for e in self.graph.edges if e.type == EdgeType.PRODUCES.value]
        self.assertEqual(len(produces), 10)
        sources = [e.source for e in produces]
        self.assertEqual(len(sources), len(set(sources)))

    def test_every_claim_addresses_a_known_gap(self):
        idx = self.graph.index()
        gap_ids = {n.id for n in self.graph.nodes if n.type == NodeType.GAP.value}
        addresses = [e for e in self.graph.edges if e.type == EdgeType.ADDRESSES.value]
        self.assertEqual(len(addresses), 10)
        for e in addresses:
            self.assertIn(e.source, idx)
            self.assertIn(e.target, gap_ids)

    def test_no_duplicate_paper_ids(self):
        paper_ids = [p["id"] for p in corpus.PAPERS]
        self.assertEqual(len(paper_ids), len(set(paper_ids)))


if __name__ == "__main__":
    unittest.main()
