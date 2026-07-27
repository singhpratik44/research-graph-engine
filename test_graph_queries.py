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
from research_graph_schema import (
    Edge, EdgeType, ExtractionMethod, Node, NodeType, Provenance, ResearchGraph,
)
import graph_queries as q


def _job(job_id: str) -> Node:
    return Node(job_id, NodeType.EXTRACTION_JOB.value, job_id)


def _blocked_by_edge(source: str, target: str) -> Edge:
    return Edge(source, target, EdgeType.BLOCKED_BY.value)


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


class TestAttributedPositionsFor(unittest.TestCase):
    def setUp(self):
        self.graph = gf.build_fixture_graph()

    def test_returns_every_claim_sharing_subject_and_object(self):
        positions = q.attributed_positions_for(
            self.graph, "hierarchical orchestration", "coordination overhead")
        self.assertEqual({p["claim_id"] for p in positions},
                         {"claim_2606_001", "claim_2701_014"})

    def test_each_position_carries_its_own_source_and_relation(self):
        positions = q.attributed_positions_for(
            self.graph, "hierarchical orchestration", "coordination overhead")
        by_id = {p["claim_id"]: p for p in positions}
        self.assertEqual(by_id["claim_2606_001"]["relation"], "reduces")
        self.assertEqual(by_id["claim_2701_014"]["relation"], "increases")
        self.assertNotEqual(by_id["claim_2606_001"]["source_paper"],
                            by_id["claim_2701_014"]["source_paper"])
        self.assertAlmostEqual(by_id["claim_2606_001"]["confidence"], 0.91)

    def test_no_shared_subject_object_returns_empty(self):
        positions = q.attributed_positions_for(self.graph, "nobody", "nothing")
        self.assertEqual(positions, [])

    def test_non_claim_nodes_are_never_returned(self):
        """Sanity: even if some other node type happened to carry matching
        subject/object properties, only CLAIM nodes qualify."""
        positions = q.attributed_positions_for(
            self.graph, "hierarchical orchestration", "coordination overhead")
        for p in positions:
            node = q.get_node(self.graph, p["claim_id"])
            self.assertEqual(node.type, NodeType.CLAIM.value)

    def test_never_mutates_the_graph(self):
        before = len(self.graph.nodes)
        q.attributed_positions_for(self.graph, "hierarchical orchestration", "coordination overhead")
        self.assertEqual(len(self.graph.nodes), before)


class TestRankedAttributedPositionsFor(unittest.TestCase):
    def setUp(self):
        self.graph = gf.build_fixture_graph()

    def test_ties_on_recency_break_on_confidence(self):
        """Both fixture claims share the same extracted_at -- the higher-
        confidence one (claim_2606_001, 0.91 vs 0.87) must win the tie."""
        ranked = q.ranked_attributed_positions_for(
            self.graph, "hierarchical orchestration", "coordination overhead")
        self.assertEqual(ranked[0]["claim_id"], "claim_2606_001")
        self.assertTrue(ranked[0]["is_most_recent"])
        self.assertFalse(ranked[1]["is_most_recent"])

    def test_more_recent_extracted_at_wins_over_higher_confidence(self):
        newer = Node(
            "claim_newer", NodeType.CLAIM.value, "newer claim",
            provenance=Provenance("paper_new", ExtractionMethod.STRUCTURED_LLM.value,
                                  0.5, "2027-01-01T00:00:00+00:00"),
            properties={"text": "A later claim.", "subject": "hierarchical orchestration",
                       "relation": "reduces", "object": "coordination overhead"},
        )
        self.graph.nodes.append(newer)
        ranked = q.ranked_attributed_positions_for(
            self.graph, "hierarchical orchestration", "coordination overhead")
        self.assertEqual(ranked[0]["claim_id"], "claim_newer")
        self.assertTrue(ranked[0]["is_most_recent"])

    def test_exactly_one_position_is_most_recent(self):
        ranked = q.ranked_attributed_positions_for(
            self.graph, "hierarchical orchestration", "coordination overhead")
        self.assertEqual(sum(1 for p in ranked if p["is_most_recent"]), 1)

    def test_missing_extracted_at_sorts_as_oldest_not_first(self):
        no_date = Node(
            "claim_no_date", NodeType.CLAIM.value, "undated claim",
            provenance=None,
            properties={"text": "An undated claim.", "subject": "hierarchical orchestration",
                       "relation": "reduces", "object": "coordination overhead"},
        )
        self.graph.nodes.append(no_date)
        ranked = q.ranked_attributed_positions_for(
            self.graph, "hierarchical orchestration", "coordination overhead")
        self.assertFalse(next(p for p in ranked if p["claim_id"] == "claim_no_date")["is_most_recent"])

    def test_empty_when_no_shared_subject_object(self):
        self.assertEqual(q.ranked_attributed_positions_for(self.graph, "nobody", "nothing"), [])

    def test_never_mutates_the_graph(self):
        before = len(self.graph.nodes)
        q.ranked_attributed_positions_for(
            self.graph, "hierarchical orchestration", "coordination overhead")
        self.assertEqual(len(self.graph.nodes), before)


class TestPossibleImplicitStalenessFor(unittest.TestCase):
    def setUp(self):
        self.graph = gf.build_fixture_graph()

    def test_already_explicitly_conflicting_pair_is_excluded(self):
        """claim_2606_001/claim_2701_014 already have a ConflictEdge --
        explicit conflict detection already caught this pair, so it must
        not also show up as an 'implicit' staleness candidate."""
        candidates = q.possible_implicit_staleness_for(
            self.graph, "hierarchical orchestration", "coordination overhead")
        self.assertEqual(candidates, [])

    def test_a_pair_without_an_explicit_conflict_edge_surfaces(self):
        third = Node(
            "claim_third", NodeType.CLAIM.value, "a third position",
            provenance=Provenance("paper_third", ExtractionMethod.STRUCTURED_LLM.value,
                                  0.6, "2027-01-01T00:00:00+00:00"),
            properties={"text": "A later, unrelated-in-conflict-terms position.",
                       "subject": "hierarchical orchestration",
                       "relation": "has no measurable effect on",
                       "object": "coordination overhead"},
        )
        self.graph.nodes.append(third)
        candidates = q.possible_implicit_staleness_for(
            self.graph, "hierarchical orchestration", "coordination overhead")
        pairs = {(c["newer_claim_id"], c["older_claim_id"]) for c in candidates}
        self.assertIn(("claim_third", "claim_2606_001"), pairs)
        self.assertIn(("claim_third", "claim_2701_014"), pairs)
        # The already-conflicting original pair is still excluded.
        self.assertNotIn(("claim_2606_001", "claim_2701_014"), pairs)
        self.assertNotIn(("claim_2701_014", "claim_2606_001"), pairs)

    def test_empty_with_fewer_than_two_positions(self):
        self.assertEqual(q.possible_implicit_staleness_for(self.graph, "nobody", "nothing"), [])

    def test_never_mutates_the_graph(self):
        before_nodes = len(self.graph.nodes)
        before_conflicts = len(self.graph.conflicts)
        q.possible_implicit_staleness_for(
            self.graph, "hierarchical orchestration", "coordination overhead")
        self.assertEqual(len(self.graph.nodes), before_nodes)
        self.assertEqual(len(self.graph.conflicts), before_conflicts)


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
        self.assertEqual(summary["nodes_by_type"][NodeType.PAPER.value], 29)
        self.assertEqual(summary["nodes_by_type"][NodeType.GAP.value], 5)


class TestDetectJobDependencyCycles(unittest.TestCase):
    def test_acyclic_chain_has_no_cycles(self):
        graph = ResearchGraph(
            nodes=[_job("job_a"), _job("job_b"), _job("job_c")],
            edges=[_blocked_by_edge("job_a", "job_b"), _blocked_by_edge("job_b", "job_c")],
        )
        self.assertEqual(q.detect_job_dependency_cycles(graph), [])

    def test_direct_two_cycle_detected(self):
        graph = ResearchGraph(
            nodes=[_job("job_a"), _job("job_b")],
            edges=[_blocked_by_edge("job_a", "job_b"), _blocked_by_edge("job_b", "job_a")],
        )
        cycles = q.detect_job_dependency_cycles(graph)
        self.assertEqual(len(cycles), 1)
        self.assertIn("job_a", cycles[0])
        self.assertIn("job_b", cycles[0])
        self.assertEqual(cycles[0][0], cycles[0][-1])  # closed cycle

    def test_longer_cycle_detected(self):
        graph = ResearchGraph(
            nodes=[_job(n) for n in ("job_a", "job_b", "job_c")],
            edges=[
                _blocked_by_edge("job_a", "job_b"),
                _blocked_by_edge("job_b", "job_c"),
                _blocked_by_edge("job_c", "job_a"),
            ],
        )
        cycles = q.detect_job_dependency_cycles(graph)
        self.assertEqual(len(cycles), 1)
        self.assertEqual(set(cycles[0]), {"job_a", "job_b", "job_c"})

    def test_self_loop_detected(self):
        graph = ResearchGraph(
            nodes=[_job("job_a")],
            edges=[_blocked_by_edge("job_a", "job_a")],
        )
        cycles = q.detect_job_dependency_cycles(graph)
        self.assertEqual(cycles, [["job_a", "job_a"]])

    def test_non_blocked_by_edges_are_ignored(self):
        graph = ResearchGraph(
            nodes=[_job("job_a"), _job("job_b")],
            edges=[Edge("job_a", "job_b", EdgeType.UNLOCKS.value),
                   Edge("job_b", "job_a", EdgeType.PRODUCES.value)],
        )
        self.assertEqual(q.detect_job_dependency_cycles(graph), [])

    def test_golden_fixture_graph_has_no_cycles(self):
        # Real-world sanity check: the shipped fixture graph must not deadlock.
        graph = gf.build_fixture_graph()
        self.assertEqual(q.detect_job_dependency_cycles(graph), [])


class TestDerivationMechanismFor(unittest.TestCase):
    def _prov(self, method):
        return Provenance("paper_x", method.value, 0.9, "2026-07-27T00:00:00+00:00")

    def test_full_triple_is_structured_relational(self):
        node = Node("c1", "claim", "x reduces y", self._prov(ExtractionMethod.STRUCTURED_LLM),
                   {"text": "x reduces y", "subject": "x", "relation": "reduces", "object": "y"})
        self.assertEqual(q.derivation_mechanism_for(node), "structured_relational")

    def test_memory_record_is_memory_synthesis(self):
        node = Node("m1", "memory_record", "a memory", self._prov(ExtractionMethod.MEMORY_WRITE),
                   {"memory_kind": "task_outcome", "summary": "s", "recorded_at": "t",
                    "subject_ref": "x"})
        self.assertEqual(q.derivation_mechanism_for(node), "memory_synthesis")

    def test_human_annotated_takes_precedence_over_triple_shape(self):
        node = Node("c2", "claim", "x reduces y", self._prov(ExtractionMethod.HUMAN_ANNOTATION),
                   {"text": "x reduces y", "subject": "x", "relation": "reduces", "object": "y"})
        self.assertEqual(q.derivation_mechanism_for(node), "human_annotated")

    def test_partial_triple_with_text_falls_through_to_structured_named_not_relational(self):
        """A node with only `subject` set (no relation/object) must not be
        over-claimed as a full relational triple -- proves the function
        doesn't guess "relational" from a fragment."""
        node = Node("c3", "claim", "x", self._prov(ExtractionMethod.STRUCTURED_LLM),
                   {"text": "x", "subject": "x"})
        self.assertEqual(q.derivation_mechanism_for(node), "structured_named")

    def test_no_text_and_no_triple_is_unclassified(self):
        node = Node("c4", "concept", "", self._prov(ExtractionMethod.KEYWORD), {})
        self.assertEqual(q.derivation_mechanism_for(node), "unclassified")

    def test_no_provenance_still_classifies_from_properties(self):
        node = Node("c5", "concept", "orchestration", None, {"text": "orchestration"})
        self.assertEqual(q.derivation_mechanism_for(node), "structured_named")


class TestDerivationMechanismBreakdown(unittest.TestCase):
    def test_counts_each_class(self):
        prov = Provenance("paper_x", ExtractionMethod.STRUCTURED_LLM.value, 0.9,
                          "2026-07-27T00:00:00+00:00")
        graph = ResearchGraph(nodes=[
            Node("c1", "claim", "x reduces y", prov,
                {"text": "x reduces y", "subject": "x", "relation": "reduces", "object": "y"}),
            Node("c2", "concept", "orchestration", prov, {"text": "orchestration"}),
        ])
        breakdown = q.derivation_mechanism_breakdown(graph)
        self.assertEqual(breakdown["structured_relational"], 1)
        self.assertEqual(breakdown["structured_named"], 1)


if __name__ == "__main__":
    unittest.main()
