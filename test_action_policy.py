#!/usr/bin/env python3
"""
Test suite for action_policy.py: runtime, pre-execution policy enforcement.
Every rule gets a positive and negative case; the enforcement point itself
(authorize_then_spawn) is tested for the property that actually matters --
a BLOCKED or ESCALATED action never spawns a job or invokes a worker.
"""

import unittest

from research_graph_schema import ExtractionType, ResearchGraph
from research_graph_workers import ResultEnvelope, WorkerSpawner
import graph_memory
import action_policy as ap

PAPER = "paper_demo_001"


class _StubWorker:
    """A worker whose envelope-building logic is fully controlled by the
    test -- `envelope_fn(directive) -> ResultEnvelope` so the produced
    envelope always matches whatever directive it's actually handed
    (paper_id, job_id, target_node_type), the same way a real worker would."""
    def __init__(self, envelope_fn):
        self.envelope_fn = envelope_fn

    def run(self, directive, text):
        return self.envelope_fn(directive)


def _admissible_envelope(directive, confidences=(0.9,), status="completed"):
    """A schema-valid, fully-traced envelope guaranteed to pass
    WorkerSpawner._verify_envelope for the given directive -- so tests can
    focus on ActionPolicy's own behavior, not incidentally fail on schema
    details unrelated to what's being tested."""
    from datetime import datetime, timezone
    from research_graph_schema import DecisionType, Node, Provenance, Trace

    def _now():
        return datetime.now(timezone.utc).isoformat()

    nodes = []
    traces = []
    if status != "failed":  # a failed worker realistically produces nothing
        for i, conf in enumerate(confidences):
            node_id = f"{directive.job_id}_n{i}"
            nodes.append(Node(
                node_id, directive.target_node_type.value, f"claim {i}",
                Provenance(directive.paper_id, "structured_llm", conf, _now()),
                properties={"text": f"claim {i}"},
            ))
            traces.append(Trace(
                trace_id=f"tr_{i}", decision_type=DecisionType.EXTRACT,
                worker_id="stub_worker", confidence=conf, reason_code="STUB",
                reasoning_summary="stub", output_refs=[node_id],
            ))
    return ResultEnvelope(directive.job_id, "stub_worker", nodes=nodes,
                          traces=traces, worker_status=status)


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


class TestAuthorizeOutcome(unittest.TestCase):
    """The closed-loop half: authorize_outcome() re-evaluates what a worker
    actually produced, using the same precedence rules as authorize()."""

    def test_empty_post_execution_rules_always_allows(self):
        policy = ap.ActionPolicy()
        action = ap.ProposedAction(PAPER, ExtractionType.CLAIMS)
        outcome = ap.ExecutionOutcome(worker_status="completed", node_count=1, avg_confidence=0.9)
        decision = policy.authorize_outcome(action, outcome)
        self.assertEqual(decision.verdict, ap.PolicyVerdict.ALLOWED)
        self.assertEqual(decision.rule_name, "default")

    def test_block_low_average_confidence_outcome_blocks(self):
        policy = ap.ActionPolicy(
            post_execution_rules=[ap.block_low_average_confidence_outcome(0.7)])
        action = ap.ProposedAction(PAPER, ExtractionType.CLAIMS)
        outcome = ap.ExecutionOutcome(worker_status="completed", node_count=2, avg_confidence=0.4)
        decision = policy.authorize_outcome(action, outcome)
        self.assertEqual(decision.verdict, ap.PolicyVerdict.BLOCKED)

    def test_block_low_average_confidence_outcome_ignores_empty_results(self):
        """No nodes produced isn't itself a confidence violation."""
        policy = ap.ActionPolicy(
            post_execution_rules=[ap.block_low_average_confidence_outcome(0.7)])
        action = ap.ProposedAction(PAPER, ExtractionType.CLAIMS)
        outcome = ap.ExecutionOutcome(worker_status="completed", node_count=0, avg_confidence=0.0)
        decision = policy.authorize_outcome(action, outcome)
        self.assertEqual(decision.verdict, ap.PolicyVerdict.ALLOWED)

    def test_max_nodes_produced_ceiling_blocks_over_limit(self):
        policy = ap.ActionPolicy(post_execution_rules=[ap.max_nodes_produced_ceiling(1)])
        action = ap.ProposedAction(PAPER, ExtractionType.CLAIMS)
        outcome = ap.ExecutionOutcome(worker_status="completed", node_count=3, avg_confidence=0.9)
        decision = policy.authorize_outcome(action, outcome)
        self.assertEqual(decision.verdict, ap.PolicyVerdict.BLOCKED)

    def test_escalate_on_worker_failure_escalates(self):
        policy = ap.ActionPolicy(post_execution_rules=[ap.escalate_on_worker_failure()])
        action = ap.ProposedAction(PAPER, ExtractionType.CLAIMS)
        outcome = ap.ExecutionOutcome(worker_status="failed", node_count=0, avg_confidence=0.0)
        decision = policy.authorize_outcome(action, outcome)
        self.assertEqual(decision.verdict, ap.PolicyVerdict.ESCALATED)

    def test_block_wins_over_escalation_at_post_execution_too(self):
        policy = ap.ActionPolicy(post_execution_rules=[
            ap.escalate_on_worker_failure(),
            ap.max_nodes_produced_ceiling(1),
        ])
        action = ap.ProposedAction(PAPER, ExtractionType.CLAIMS)
        outcome = ap.ExecutionOutcome(worker_status="failed", node_count=5, avg_confidence=0.9)
        decision = policy.authorize_outcome(action, outcome)
        self.assertEqual(decision.verdict, ap.PolicyVerdict.BLOCKED)

    def test_pre_and_post_execution_decisions_share_one_audit_trail(self):
        policy = ap.ActionPolicy(post_execution_rules=[ap.max_nodes_produced_ceiling(1)])
        action = ap.ProposedAction(PAPER, ExtractionType.CLAIMS)
        policy.authorize(action)
        outcome = ap.ExecutionOutcome(worker_status="completed", node_count=5, avg_confidence=0.9)
        policy.authorize_outcome(action, outcome)
        self.assertEqual(len(policy.decisions), 2)
        self.assertEqual(policy.report()["total_decisions"], 2)


class TestAuthorizeExecuteThenAdmit(unittest.TestCase):
    def setUp(self):
        self.graph = ResearchGraph()
        self.spawner = WorkerSpawner(self.graph)

    def test_allowed_end_to_end_admits_the_envelope(self):
        worker = _StubWorker(lambda d: _admissible_envelope(d, confidences=(0.9,)))
        pre, post, admission, directive, env = ap.authorize_execute_then_admit(
            self.spawner, ap.ActionPolicy(), worker, PAPER, ExtractionType.CLAIMS, "text")
        self.assertEqual(pre.verdict, ap.PolicyVerdict.ALLOWED)
        self.assertEqual(post.verdict, ap.PolicyVerdict.ALLOWED)
        self.assertIsNotNone(admission)
        self.assertTrue(admission.admitted)
        self.assertIsNotNone(directive)
        self.assertIsNotNone(env)

    def test_pre_action_block_never_invokes_the_worker(self):
        calls = []
        class TrackedWorker:
            def run(self, directive, text):
                calls.append(1)
                return _admissible_envelope(directive)
        policy = ap.ActionPolicy(rules=[ap.deny_extraction_types({ExtractionType.CONFLICTS})])
        pre, post, admission, directive, env = ap.authorize_execute_then_admit(
            self.spawner, policy, TrackedWorker(), PAPER, ExtractionType.CONFLICTS, "text")
        self.assertEqual(pre.verdict, ap.PolicyVerdict.BLOCKED)
        self.assertIsNone(post)
        self.assertIsNone(admission)
        self.assertIsNone(directive)
        self.assertIsNone(env)
        self.assertEqual(calls, [])

    def test_post_execution_block_runs_the_worker_but_never_admits(self):
        """The load-bearing closed-loop property: the worker DOES run (its
        side effects already happened), but nothing it produced reaches the
        graph -- spawner.admit() is never called."""
        worker = _StubWorker(lambda d: _admissible_envelope(d, confidences=(0.1, 0.2)))
        policy = ap.ActionPolicy(
            post_execution_rules=[ap.block_low_average_confidence_outcome(0.7)])
        pre, post, admission, directive, env = ap.authorize_execute_then_admit(
            self.spawner, policy, worker, PAPER, ExtractionType.CLAIMS, "text")
        self.assertEqual(pre.verdict, ap.PolicyVerdict.ALLOWED)
        self.assertEqual(post.verdict, ap.PolicyVerdict.BLOCKED)
        self.assertIsNone(admission)
        self.assertIsNotNone(directive)  # held for a possible later approval
        self.assertIsNotNone(env)
        # The job node was created by the pre-action spawn, but nothing the
        # worker produced (its claim nodes) was ever admitted.
        claim_nodes = [n for n in self.graph.nodes if n.type == "claim"]
        self.assertEqual(claim_nodes, [])

    def test_post_execution_escalation_holds_admission(self):
        worker = _StubWorker(lambda d: _admissible_envelope(d, status="failed"))
        policy = ap.ActionPolicy(post_execution_rules=[ap.escalate_on_worker_failure()])
        pre, post, admission, directive, env = ap.authorize_execute_then_admit(
            self.spawner, policy, worker, PAPER, ExtractionType.CLAIMS, "text")
        self.assertEqual(post.verdict, ap.PolicyVerdict.ESCALATED)
        self.assertIsNone(admission)
        self.assertIsNotNone(directive)
        self.assertIsNotNone(env)

    def test_audit_records_both_stages_when_graph_is_given(self):
        worker = _StubWorker(lambda d: _admissible_envelope(d, confidences=(0.1,)))
        policy = ap.ActionPolicy(
            post_execution_rules=[ap.block_low_average_confidence_outcome(0.7)])
        ap.authorize_execute_then_admit(
            self.spawner, policy, worker, PAPER, ExtractionType.CLAIMS, "text", graph=self.graph)
        records = [n for n in self.graph.nodes if n.type == "memory_record"]
        # one for the ALLOWED pre-action decision, one for the BLOCKED post-execution one
        self.assertEqual(len(records), 2)
        verdicts = {r.properties["details"]["verdict"] for r in records}
        self.assertEqual(verdicts, {"allowed", "blocked"})


def _always_escalate_completed_outcome(action, outcome):
    """Test-only post-execution rule: escalate any non-empty completed
    outcome, regardless of its confidence -- used to exercise an
    ESCALATED-then-approved outcome that's actually admissible (unlike a
    worker-failure escalation, whose envelope carries no nodes and would
    never be admitted anyway, approved or not)."""
    if outcome.node_count > 0:
        return (ap.PolicyVerdict.ESCALATED, "manual review required")
    return None


class TestApproveEscalatedOutcome(unittest.TestCase):
    def setUp(self):
        self.graph = ResearchGraph()
        self.spawner = WorkerSpawner(self.graph)
        self.policy = ap.ActionPolicy(
            post_execution_rules=[("always_escalate_completed_outcome",
                                    _always_escalate_completed_outcome)])

    def test_approving_admits_the_previously_held_envelope_without_rerunning_the_worker(self):
        run_count = []
        class CountingWorker:
            def run(self, directive, text):
                run_count.append(1)
                return _admissible_envelope(directive, confidences=(0.9,))

        pre, post, admission, directive, env = ap.authorize_execute_then_admit(
            self.spawner, self.policy, CountingWorker(), PAPER, ExtractionType.CLAIMS, "text")
        self.assertIsNone(admission)
        self.assertEqual(post.verdict, ap.PolicyVerdict.ESCALATED)
        self.assertEqual(run_count, [1])

        approved = ap.approve_escalated_outcome(self.spawner, directive, env, post, "alice")
        self.assertTrue(approved.admitted)
        # The worker is never re-invoked to approve a held outcome -- the
        # envelope it already produced is what gets admitted.
        self.assertEqual(run_count, [1])

    def test_approving_records_a_human_approval_audit_entry(self):
        worker = _StubWorker(lambda d: _admissible_envelope(d, confidences=(0.9,)))
        pre, post, admission, directive, env = ap.authorize_execute_then_admit(
            self.spawner, self.policy, worker, PAPER, ExtractionType.CLAIMS, "text",
            graph=self.graph)
        approved = ap.approve_escalated_outcome(
            self.spawner, directive, env, post, "alice", graph=self.graph)
        records = graph_memory.action_policy_decisions_for(self.graph, approved.job_node.id)
        self.assertTrue(any(r.properties["details"]["rule_name"] == "human_approval"
                            for r in records))

    def test_approving_a_non_escalated_decision_raises(self):
        worker = _StubWorker(lambda d: _admissible_envelope(d, confidences=(0.9,)))
        pre, post, admission, directive, env = ap.authorize_execute_then_admit(
            self.spawner, ap.ActionPolicy(), worker, PAPER, ExtractionType.CLAIMS, "text")
        with self.assertRaises(ValueError):
            ap.approve_escalated_outcome(self.spawner, directive, env, post, "alice")


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
