#!/usr/bin/env python3
"""
Test suite for graph_orchestrator.py: the fan-out/collect layer must produce
one job per requested extraction type, each admitted through the real,
unchanged WorkerSpawner/gate/conflict-detection path -- no shortcuts, no
parallel reimplementation of what admit() already does.
"""

import unittest

from research_graph_schema import ExtractionType, JobStatus, NodeType, ResearchGraph
import research_graph_gates as gates
from graph_orchestrator import DEFAULT_EXTRACTION_TYPES, Orchestrator, OrchestrationReport

TEXT = ("Hierarchical orchestration reduces coordination overhead. "
        "We evaluate on SWE-Bench and the PRISM benchmark.")


class TestOrchestratorFanOut(unittest.TestCase):
    def setUp(self):
        self.graph = ResearchGraph()
        self.orchestrator = Orchestrator(self.graph)

    def test_one_job_spawned_per_extraction_type(self):
        report = self.orchestrator.run_paper("paper_x", TEXT)
        self.assertEqual(len(report.admissions), len(DEFAULT_EXTRACTION_TYPES))
        job_types = {a.job_node.properties["extraction_type"] for a in report.admissions}
        self.assertEqual(job_types, {et.value for et in DEFAULT_EXTRACTION_TYPES})

    def test_every_job_actually_admitted(self):
        report = self.orchestrator.run_paper("paper_x", TEXT)
        self.assertTrue(report.all_admitted)

    def test_nodes_of_each_requested_type_land_in_the_graph(self):
        report = self.orchestrator.run_paper("paper_x", TEXT)
        # Every requested extraction type actually ran, whether or not it found
        # anything -- that's what "fan-out ran all branches" means, not "every
        # branch produced output" (concept extraction may reasonably find none).
        job_types_run = {a.job_node.properties["extraction_type"] for a in report.admissions}
        self.assertEqual(job_types_run, {et.value for et in DEFAULT_EXTRACTION_TYPES})

        types_produced = {n.type for n in self.graph.nodes
                          if n.type not in (NodeType.EXTRACTION_JOB.value, NodeType.REVIEW_TASK.value)}
        # Concept extraction is frequency-based over every non-stopword in the text,
        # so it reliably produces something too -- all three requested types show up.
        self.assertEqual(types_produced, {NodeType.CLAIM.value, NodeType.BENCHMARK.value, NodeType.CONCEPT.value})

    def test_restricting_extraction_types_only_spawns_those(self):
        report = self.orchestrator.run_paper("paper_x", TEXT, extraction_types=[ExtractionType.CLAIMS])
        self.assertEqual(len(report.admissions), 1)
        self.assertEqual(report.admissions[0].job_node.properties["extraction_type"],
                         ExtractionType.CLAIMS.value)

    def test_fresh_extraction_is_held_pending_human_review_by_default(self):
        # Matches the existing worker contract (test_workers.py's
        # test_admission_holds_for_review_not_auto_advance): a worker can never
        # mark its own output human_reviewed, so a fresh orchestrator run always
        # lands held, regardless of confidence, until a human reviews it.
        report = self.orchestrator.run_paper("paper_x", TEXT)
        self.assertTrue(all(
            a.job_node.properties.get("status") == JobStatus.HELD.value
            for a in report.admissions
        ))
        self.assertEqual(set(report.held_job_ids),
                         {a.job_node.id for a in report.admissions})

    def test_conflict_detection_still_runs_automatically(self):
        # Orchestrator adds no conflict-detection logic of its own -- this proves
        # admit()'s existing detect_conflicts_in_graph() call is still exercised
        # when claims land through the fan-out path.
        graph = ResearchGraph()
        orch = Orchestrator(graph)
        orch.run_paper("paper_a", "Hierarchical orchestration reduces coordination overhead.",
                       extraction_types=[ExtractionType.CLAIMS])
        report_b = orch.run_paper(
            "paper_b", "Hierarchical orchestration increases coordination overhead.",
            extraction_types=[ExtractionType.CLAIMS])
        self.assertGreater(report_b.total_conflicts_found, 0)
        self.assertEqual(len(graph.conflicts), report_b.total_conflicts_found)


class TestOrchestrationReport(unittest.TestCase):
    def test_total_nodes_admitted_sums_across_jobs(self):
        graph = ResearchGraph()
        report = Orchestrator(graph).run_paper("paper_x", TEXT)
        self.assertEqual(report.total_nodes_admitted, sum(a.nodes_admitted for a in report.admissions))
        self.assertGreater(report.total_nodes_admitted, 0)

    def test_to_dict_is_json_shaped(self):
        graph = ResearchGraph()
        report = Orchestrator(graph).run_paper("paper_x", TEXT)
        d = report.to_dict()
        self.assertEqual(d["paper_id"], "paper_x")
        self.assertIn("admissions", d)
        self.assertIsInstance(d["admissions"], list)

    def test_failed_job_ids_empty_on_a_clean_run(self):
        graph = ResearchGraph()
        report = Orchestrator(graph).run_paper("paper_x", TEXT)
        self.assertEqual(report.failed_job_ids, [])


class TestOrchestratorRespectsGateConfig(unittest.TestCase):
    def test_custom_gate_is_used_not_a_default_one(self):
        graph = ResearchGraph()
        lenient_gate = gates.WorkflowGate(require_human_review=False, confidence_threshold=0.0)
        orch = Orchestrator(graph, gate=lenient_gate)
        report = orch.run_paper("paper_x", TEXT, extraction_types=[ExtractionType.CLAIMS])
        # With review not required and no confidence floor, the claim job should
        # clear the gate outright instead of landing held.
        self.assertEqual(report.held_job_ids, [])


if __name__ == "__main__":
    unittest.main()
