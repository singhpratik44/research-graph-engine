#!/usr/bin/env python3
"""
Test suite for action_policy.py: runtime, pre-execution policy enforcement.
Every rule gets a positive and negative case; the enforcement point itself
(authorize_then_spawn) is tested for the property that actually matters --
a BLOCKED or ESCALATED action never spawns a job or invokes a worker.
"""

import unittest

from research_graph_schema import ExtractionType, ResearchGraph
from research_graph_workers import WorkerSpawner
import graph_memory
import action_policy as ap

PAPER = "paper_demo_001"


class TestActionPolicyRules(unittest.TestCase):
    def test_empty_policy_always_allows(self):
        policy = ap.ActionPolicy()
        action = ap.ProposedAction(PAPER, ExtractionType.CLAIMS)
        decision = policy.authorize(action)
        self.assertEqual(decision.verdict, ap.PolicyVerdict.ALLOWED)
        self.assertEqual(decision.rule_name, "default")

    def test_deny_extraction_types_blocks(self):
        policy = ap.ActionPolicy(rules=[ap.deny_extraction_types({ExtractionType.CONFLICTS})])
        decision = policy.authorize(ap.ProposedAction(PAPER, ExtractionType.CONFLICTS))
        self.assertEqual(decision.verdict, ap.PolicyVerdict.BLOCKED)

    def test_deny_extraction_types_does_not_block_other_types(self):
        policy = ap.ActionPolicy(rules=[ap.deny_extraction_types({ExtractionType.CONFLICTS})])
        decision = policy.authorize(ap.ProposedAction(PAPER, ExtractionType.CLAIMS))
        self.assertEqual(decision.verdict, ap.PolicyVerdict.ALLOWED)

    def test_require_escalation_for_escalates(self):
        policy = ap.ActionPolicy(rules=[ap.require_escalation_for({ExtractionType.BENCHMARKS})])
        decision = policy.authorize(ap.ProposedAction(PAPER, ExtractionType.BENCHMARKS))
        self.assertEqual(decision.verdict, ap.PolicyVerdict.ESCALATED)

    def test_max_results_ceiling_blocks_over_limit(self):
        policy = ap.ActionPolicy(rules=[ap.max_results_ceiling(10)])
        decision = policy.authorize(ap.ProposedAction(PAPER, ExtractionType.CLAIMS, max_results=50))
        self.assertEqual(decision.verdict, ap.PolicyVerdict.BLOCKED)

    def test_max_results_ceiling_allows_at_or_under_limit(self):
        policy = ap.ActionPolicy(rules=[ap.max_results_ceiling(10)])
        decision = policy.authorize(ap.ProposedAction(PAPER, ExtractionType.CLAIMS, max_results=10))
        self.assertEqual(decision.verdict, ap.PolicyVerdict.ALLOWED)

    def test_max_results_ceiling_ignores_none(self):
        policy = ap.ActionPolicy(rules=[ap.max_results_ceiling(10)])
        decision = policy.authorize(ap.ProposedAction(PAPER, ExtractionType.CLAIMS, max_results=None))
        self.assertEqual(decision.verdict, ap.PolicyVerdict.ALLOWED)

    def test_block_wins_regardless_of_rule_order_relative_to_escalation(self):
        """An ESCALATE rule checked before a BLOCK rule must not let the
        escalation win -- BLOCKED always overrides, from any position."""
        policy = ap.ActionPolicy(rules=[
            ap.require_escalation_for({ExtractionType.CONFLICTS}),
            ap.deny_extraction_types({ExtractionType.CONFLICTS}),
        ])
        decision = policy.authorize(ap.ProposedAction(PAPER, ExtractionType.CONFLICTS))
        self.assertEqual(decision.verdict, ap.PolicyVerdict.BLOCKED)

    def test_first_escalation_is_recorded_when_no_rule_blocks(self):
        policy = ap.ActionPolicy(rules=[
            ap.require_escalation_for({ExtractionType.BENCHMARKS}),
            ap.deny_extraction_types({ExtractionType.CONFLICTS}),  # doesn't match this action
        ])
        decision = policy.authorize(ap.ProposedAction(PAPER, ExtractionType.BENCHMARKS))
        self.assertEqual(decision.verdict, ap.PolicyVerdict.ESCALATED)
        self.assertEqual(decision.rule_name, "require_escalation_for")

    def test_report_tallies_every_decision_by_verdict(self):
        policy = ap.ActionPolicy(rules=[ap.deny_extraction_types({ExtractionType.CONFLICTS})])
        policy.authorize(ap.ProposedAction(PAPER, ExtractionType.CLAIMS))
        policy.authorize(ap.ProposedAction(PAPER, ExtractionType.CONFLICTS))
        report = policy.report()
        self.assertEqual(report["total_decisions"], 2)
        self.assertEqual(report["by_verdict"], {"allowed": 1, "blocked": 1})


class TestAuthorizeThenSpawn(unittest.TestCase):
    def setUp(self):
        self.graph = ResearchGraph()
        self.spawner = WorkerSpawner(self.graph)

    def test_allowed_action_spawns_a_real_job(self):
        policy = ap.ActionPolicy()
        decision, job, directive = ap.authorize_then_spawn(
            self.spawner, policy, PAPER, ExtractionType.CLAIMS)
        self.assertEqual(decision.verdict, ap.PolicyVerdict.ALLOWED)
        self.assertIsNotNone(job)
        self.assertIsNotNone(directive)
        self.assertIn(job.id, self.graph.index())

    def test_blocked_action_never_spawns_a_job(self):
        policy = ap.ActionPolicy(rules=[ap.deny_extraction_types({ExtractionType.CONFLICTS})])
        decision, job, directive = ap.authorize_then_spawn(
            self.spawner, policy, PAPER, ExtractionType.CONFLICTS)
        self.assertEqual(decision.verdict, ap.PolicyVerdict.BLOCKED)
        self.assertIsNone(job)
        self.assertIsNone(directive)
        self.assertEqual(len(self.graph.nodes), 0)  # nothing at all was created

    def test_escalated_action_does_not_spawn_either(self):
        """The load-bearing distinction from a cosmetic 'label but proceed
        anyway' design: ESCALATED must hold exactly like BLOCKED until a
        human explicitly approves it."""
        policy = ap.ActionPolicy(rules=[ap.require_escalation_for({ExtractionType.BENCHMARKS})])
        decision, job, directive = ap.authorize_then_spawn(
            self.spawner, policy, PAPER, ExtractionType.BENCHMARKS)
        self.assertEqual(decision.verdict, ap.PolicyVerdict.ESCALATED)
        self.assertIsNone(job)
        self.assertIsNone(directive)
        self.assertEqual(len(self.graph.nodes), 0)

    def test_audit_record_written_when_graph_is_given(self):
        policy = ap.ActionPolicy(rules=[ap.deny_extraction_types({ExtractionType.CONFLICTS})])
        decision, job, directive = ap.authorize_then_spawn(
            self.spawner, policy, PAPER, ExtractionType.CONFLICTS, graph=self.graph)
        records = [n for n in self.graph.nodes if n.type == "memory_record"]
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].properties["memory_kind"], "action_policy_decision")
        self.assertEqual(records[0].properties["details"]["verdict"], "blocked")

    def test_audit_record_links_to_the_real_job_when_allowed(self):
        policy = ap.ActionPolicy()
        decision, job, directive = ap.authorize_then_spawn(
            self.spawner, policy, PAPER, ExtractionType.CLAIMS, graph=self.graph)
        linked = graph_memory.action_policy_decisions_for(self.graph, job.id)
        self.assertEqual(len(linked), 1)

    def test_no_audit_record_without_a_graph(self):
        policy = ap.ActionPolicy(rules=[ap.deny_extraction_types({ExtractionType.CONFLICTS})])
        ap.authorize_then_spawn(self.spawner, policy, PAPER, ExtractionType.CONFLICTS)
        self.assertEqual(len(self.graph.nodes), 0)


class TestApproveEscalatedAction(unittest.TestCase):
    def setUp(self):
        self.graph = ResearchGraph()
        self.spawner = WorkerSpawner(self.graph)
        self.policy = ap.ActionPolicy(rules=[ap.require_escalation_for({ExtractionType.BENCHMARKS})])

    def test_approving_an_escalation_spawns_the_job(self):
        decision, job, directive = ap.authorize_then_spawn(
            self.spawner, self.policy, PAPER, ExtractionType.BENCHMARKS)
        self.assertIsNone(job)
        job2, directive2 = ap.approve_escalated_action(self.spawner, decision, "alice")
        self.assertIsNotNone(job2)
        self.assertIn(job2.id, self.graph.index())

    def test_approving_records_a_human_approval_audit_entry(self):
        decision, _, _ = ap.authorize_then_spawn(
            self.spawner, self.policy, PAPER, ExtractionType.BENCHMARKS, graph=self.graph)
        job, _ = ap.approve_escalated_action(self.spawner, decision, "alice", graph=self.graph)
        records = graph_memory.action_policy_decisions_for(self.graph, job.id)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].properties["details"]["rule_name"], "human_approval")
        self.assertIn("alice", records[0].properties["details"]["reason"])

    def test_approving_an_allowed_decision_raises(self):
        decision, job, directive = ap.authorize_then_spawn(
            self.spawner, ap.ActionPolicy(), PAPER, ExtractionType.CLAIMS)
        with self.assertRaises(ValueError):
            ap.approve_escalated_action(self.spawner, decision, "alice")

    def test_approving_a_blocked_decision_raises(self):
        blocking_policy = ap.ActionPolicy(rules=[ap.deny_extraction_types({ExtractionType.CONFLICTS})])
        decision, job, directive = ap.authorize_then_spawn(
            self.spawner, blocking_policy, PAPER, ExtractionType.CONFLICTS)
        with self.assertRaises(ValueError):
            ap.approve_escalated_action(self.spawner, decision, "alice")


if __name__ == "__main__":
    unittest.main()
