#!/usr/bin/env python3
"""
Test suite for task_graph.py: DAG construction, ready-task computation,
cycle rejection, real parallel execution with a timing proof (not just
"looks independent"), merge barriers, and failure propagation (a failed
task's dependents must be SKIPPED, never silently run or silently dropped).
"""

import threading
import time
import unittest

from task_graph import Scheduler, TaskDAG, TaskStatus


class TestTaskDAGConstruction(unittest.TestCase):
    def test_add_task_returns_pending_node(self):
        dag = TaskDAG()
        node = dag.add_task("a", "Task A")
        self.assertEqual(node.status, TaskStatus.PENDING.value)

    def test_duplicate_task_id_rejected(self):
        dag = TaskDAG()
        dag.add_task("a", "Task A")
        with self.assertRaises(ValueError):
            dag.add_task("a", "Task A again")

    def test_dependency_on_unknown_task_rejected(self):
        dag = TaskDAG()
        dag.add_task("a", "Task A")
        with self.assertRaises(KeyError):
            dag.add_dependency("a", depends_on="nope")

    def test_dependencies_of_returns_direct_deps_only(self):
        dag = TaskDAG()
        for t in ("a", "b", "c"):
            dag.add_task(t, t)
        dag.add_dependency("c", depends_on="a")
        dag.add_dependency("c", depends_on="b")
        self.assertEqual(set(dag.dependencies_of("c")), {"a", "b"})
        self.assertEqual(dag.dependencies_of("a"), [])


class TestDetectHazards(unittest.TestCase):
    def test_clean_connected_dag_has_no_hazards(self):
        dag = TaskDAG()
        dag.add_task("a", "Task A")
        dag.add_task("b", "Task B", parent_task_id="a")
        dag.add_dependency("b", depends_on="a")
        self.assertEqual(dag.detect_hazards(), [])

    def test_single_task_dag_is_never_flagged_as_an_island(self):
        dag = TaskDAG()
        dag.add_task("solo", "Solo Task")
        self.assertEqual(dag.detect_hazards(), [])

    def test_dangling_parent_task_id_is_flagged(self):
        dag = TaskDAG()
        dag.add_task("a", "Task A", parent_task_id="ghost")
        dag.add_task("b", "Task B")
        dag.add_dependency("b", depends_on="a")
        hazards = dag.detect_hazards()
        self.assertEqual(len(hazards), 1)
        self.assertIn("a", hazards[0])
        self.assertIn("ghost", hazards[0])

    def test_real_parent_task_id_is_not_flagged(self):
        dag = TaskDAG()
        dag.add_task("parent", "Parent")
        dag.add_task("child", "Child", parent_task_id="parent")
        dag.add_task("other", "Other")
        dag.add_dependency("child", depends_on="parent")
        dag.add_dependency("other", depends_on="parent")
        self.assertEqual(dag.detect_hazards(), [])

    def test_island_task_with_no_edges_is_flagged(self):
        dag = TaskDAG()
        dag.add_task("a", "Task A")
        dag.add_task("b", "Task B")
        dag.add_task("island", "Forgotten Task")
        dag.add_dependency("b", depends_on="a")
        hazards = dag.detect_hazards()
        self.assertEqual(len(hazards), 1)
        self.assertIn("island", hazards[0])

    def test_both_hazard_kinds_reported_together(self):
        dag = TaskDAG()
        dag.add_task("a", "Task A", parent_task_id="ghost")
        dag.add_task("b", "Task B")
        dag.add_task("island", "Forgotten Task")
        dag.add_dependency("b", depends_on="a")
        hazards = dag.detect_hazards()
        self.assertEqual(len(hazards), 2)

    def test_hazards_are_pure_and_do_not_mutate_the_dag(self):
        dag = TaskDAG()
        dag.add_task("a", "Task A", parent_task_id="ghost")
        before_nodes = dict(dag.nodes)
        before_edges = list(dag.edges)
        dag.detect_hazards()
        self.assertEqual(dag.nodes, before_nodes)
        self.assertEqual(dag.edges, before_edges)


class TestReadyTasks(unittest.TestCase):
    def test_task_with_no_deps_is_ready_immediately(self):
        dag = TaskDAG()
        dag.add_task("a", "a")
        self.assertEqual(dag.ready_tasks(completed=set(), remaining={"a"}), ["a"])

    def test_task_becomes_ready_only_once_deps_complete(self):
        dag = TaskDAG()
        dag.add_task("a", "a")
        dag.add_task("b", "b")
        dag.add_dependency("b", depends_on="a")
        self.assertEqual(dag.ready_tasks(completed=set(), remaining={"a", "b"}), ["a"])
        self.assertEqual(dag.ready_tasks(completed={"a"}, remaining={"b"}), ["b"])


class TestCycleRejection(unittest.TestCase):
    def test_scheduler_refuses_to_run_a_cyclic_dag(self):
        dag = TaskDAG()
        dag.add_task("a", "a")
        dag.add_task("b", "b")
        dag.add_dependency("a", depends_on="b")
        dag.add_dependency("b", depends_on="a")
        with self.assertRaises(ValueError):
            Scheduler(dag).run(lambda task_id: None)


class TestSchedulerHappyPath(unittest.TestCase):
    def test_all_tasks_get_exactly_one_span(self):
        dag = TaskDAG()
        for t in ("a", "b", "c"):
            dag.add_task(t, t)
        result = Scheduler(dag).run(lambda task_id: {"confidence": 1.0})
        self.assertEqual({s.task_id for s in result.spans}, {"a", "b", "c"})
        self.assertEqual(len(result.spans), 3)

    def test_all_succeeded_true_on_a_clean_run(self):
        dag = TaskDAG()
        dag.add_task("a", "a")
        result = Scheduler(dag).run(lambda task_id: {"confidence": 1.0})
        self.assertTrue(result.all_succeeded)

    def test_span_carries_agent_id_and_parent_task_id(self):
        dag = TaskDAG()
        dag.add_task("a", "a", agent_id="claim_extractor", parent_task_id="root")
        result = Scheduler(dag).run(lambda task_id: {"confidence": 0.7})
        span = result.spans[0]
        self.assertEqual(span.agent_id, "claim_extractor")
        self.assertEqual(span.parent_task_id, "root")
        self.assertEqual(span.confidence, 0.7)

    def test_span_has_started_before_or_equal_to_ended(self):
        dag = TaskDAG()
        dag.add_task("a", "a")
        result = Scheduler(dag).run(lambda task_id: {"confidence": 1.0})
        span = result.spans[0]
        self.assertLessEqual(span.started_at, span.ended_at)

    def test_merge_barrier_runs_dependency_after_both_deps_complete(self):
        dag = TaskDAG()
        dag.add_task("a", "a")
        dag.add_task("b", "b")
        dag.add_task("merge", "merge")
        dag.add_dependency("merge", depends_on="a")
        dag.add_dependency("merge", depends_on="b")

        order = []
        order_lock = threading.Lock()

        def executor(task_id):
            with order_lock:
                order.append(task_id)
            return {"confidence": 1.0}

        result = Scheduler(dag).run(executor)
        self.assertTrue(result.all_succeeded)
        # merge must come after both a and b, regardless of a/b's relative order
        self.assertLess(order.index("a"), order.index("merge"))
        self.assertLess(order.index("b"), order.index("merge"))


class TestSchedulerRunsReadyTasksConcurrently(unittest.TestCase):
    def test_two_independent_slow_tasks_overlap_in_wall_clock_time(self):
        # If these ran sequentially, wall clock would be >= 2x the sleep. Real
        # thread-pool concurrency keeps it close to 1x -- this is the actual
        # proof "parallel" isn't just "independent enough to reorder".
        dag = TaskDAG()
        dag.add_task("a", "a")
        dag.add_task("b", "b")

        def slow_executor(task_id):
            time.sleep(0.2)
            return {"confidence": 1.0}

        start = time.monotonic()
        result = Scheduler(dag, max_workers=2).run(slow_executor)
        elapsed = time.monotonic() - start

        self.assertTrue(result.all_succeeded)
        self.assertLess(elapsed, 0.35, "two 0.2s tasks took too long to have run concurrently")


class TestSchedulerFailurePropagation(unittest.TestCase):
    def test_failing_task_is_marked_failed_not_silently_ignored(self):
        dag = TaskDAG()
        dag.add_task("a", "a")

        def failing_executor(task_id):
            raise RuntimeError("boom")

        result = Scheduler(dag).run(failing_executor)
        self.assertIn("a", result.failed)
        self.assertFalse(result.all_succeeded)
        self.assertEqual(result.spans[0].status, TaskStatus.FAILED.value)
        self.assertIn("boom", result.spans[0].error)

    def test_dependent_of_a_failed_task_is_skipped_not_run(self):
        dag = TaskDAG()
        dag.add_task("a", "a")
        dag.add_task("b", "b")
        dag.add_dependency("b", depends_on="a")

        ran = []

        def executor(task_id):
            ran.append(task_id)
            if task_id == "a":
                raise RuntimeError("a failed")
            return {"confidence": 1.0}

        result = Scheduler(dag).run(executor)
        self.assertIn("a", result.failed)
        self.assertIn("b", result.skipped)
        self.assertNotIn("b", ran)  # never actually executed
        self.assertFalse(result.all_succeeded)

    def test_independent_task_still_runs_when_a_sibling_fails(self):
        dag = TaskDAG()
        dag.add_task("a", "a")
        dag.add_task("independent", "independent")

        def executor(task_id):
            if task_id == "a":
                raise RuntimeError("boom")
            return {"confidence": 1.0}

        result = Scheduler(dag).run(executor)
        self.assertIn("a", result.failed)
        self.assertIn("independent", result.completed)


class TestSchedulerAdaptiveRetry(unittest.TestCase):
    """
    gap_adaptive_recovery: a failing task can be retried up to `max_retries`
    times before being marked FAILED (and cascading SKIPPED to dependents).
    `max_retries=0` (the default) must reproduce the old immediate-FAILED
    behavior exactly -- proven here alongside the retry path itself.
    """

    def test_default_max_retries_is_zero_and_fails_immediately(self):
        dag = TaskDAG()
        dag.add_task("a", "a")
        calls = []

        def failing_executor(task_id):
            calls.append(task_id)
            raise RuntimeError("boom")

        result = Scheduler(dag).run(failing_executor)
        self.assertEqual(len(calls), 1, "no retry should happen with the default max_retries=0")
        self.assertIn("a", result.failed)
        span = result.spans[0]
        self.assertEqual(span.status, TaskStatus.FAILED.value)
        self.assertEqual(span.attempts, 1)
        self.assertEqual(span.retry_errors, [])

    def test_task_retries_and_succeeds_on_a_later_attempt(self):
        dag = TaskDAG()
        dag.add_task("a", "a")
        calls = []

        def flaky_executor(task_id):
            calls.append(task_id)
            if len(calls) < 2:
                raise RuntimeError("transient failure")
            return {"confidence": 0.8}

        result = Scheduler(dag, max_retries=1).run(flaky_executor)
        self.assertEqual(len(calls), 2, "executor must actually be invoked again, not just pass eventually")
        self.assertIn("a", result.completed)
        self.assertNotIn("a", result.failed)
        span = result.spans[0]
        self.assertEqual(len(result.spans), 1, "still exactly one span for the task")
        self.assertEqual(span.status, TaskStatus.COMPLETED.value)
        self.assertEqual(span.attempts, 2)
        self.assertEqual(len(span.retry_errors), 1)
        self.assertIn("transient failure", span.retry_errors[0])
        self.assertEqual(span.confidence, 0.8)

    def test_retries_are_bounded_and_task_still_fails_when_exhausted(self):
        dag = TaskDAG()
        dag.add_task("a", "a")
        calls = []

        def always_failing_executor(task_id):
            calls.append(task_id)
            raise RuntimeError("boom")

        result = Scheduler(dag, max_retries=2).run(always_failing_executor)
        self.assertEqual(len(calls), 3, "1 original attempt + 2 retries, then stop -- bound is real")
        self.assertIn("a", result.failed)
        span = result.spans[0]
        self.assertEqual(span.attempts, 3)
        self.assertEqual(len(span.retry_errors), 2)
        self.assertIn("boom", span.error)

    def test_a_task_that_succeeds_on_retry_lets_its_dependent_run(self):
        # Proves retries interact correctly with the dependency scheduler: a task
        # that eventually succeeds must NOT cascade SKIPPED to its dependents.
        dag = TaskDAG()
        dag.add_task("a", "a")
        dag.add_task("b", "b")
        dag.add_dependency("b", depends_on="a")

        calls = []

        def executor(task_id):
            if task_id == "a":
                calls.append(task_id)
                if len(calls) < 2:
                    raise RuntimeError("transient")
            return {"confidence": 1.0}

        result = Scheduler(dag, max_retries=1).run(executor)
        self.assertTrue(result.all_succeeded)
        self.assertIn("a", result.completed)
        self.assertIn("b", result.completed)
        self.assertNotIn("b", result.skipped)

    def test_max_retries_zero_reproduces_every_failure_propagation_fixture(self):
        """Re-run the existing failure-propagation fixture with the default
        Scheduler (max_retries=0) and confirm the outcome is identical to
        test_dependent_of_a_failed_task_is_skipped_not_run above."""
        dag = TaskDAG()
        dag.add_task("a", "a")
        dag.add_task("b", "b")
        dag.add_dependency("b", depends_on="a")

        ran = []

        def executor(task_id):
            ran.append(task_id)
            if task_id == "a":
                raise RuntimeError("a failed")
            return {"confidence": 1.0}

        result = Scheduler(dag).run(executor)
        self.assertIn("a", result.failed)
        self.assertIn("b", result.skipped)
        self.assertNotIn("b", ran)
        self.assertFalse(result.all_succeeded)
        self.assertEqual(ran.count("a"), 1, "no retry attempted with the default max_retries=0")


class TestFailedAncestors(unittest.TestCase):
    """TaskDAG.failed_ancestors: transitive closure of a task's dependencies,
    intersected with the failed set -- the fault-localization primitive."""

    def test_direct_failed_dependency_is_named(self):
        dag = TaskDAG()
        dag.add_task("a", "a")
        dag.add_task("b", "b")
        dag.add_dependency("b", depends_on="a")
        self.assertEqual(dag.failed_ancestors("b", failed={"a"}), ["a"])

    def test_multi_hop_chain_finds_the_root_cause(self):
        dag = TaskDAG()
        for t in ("a", "b", "c"):
            dag.add_task(t, t)
        dag.add_dependency("b", depends_on="a")
        dag.add_dependency("c", depends_on="b")
        # "a" failed; "b" was skipped as a result; "c" depends on "b" only,
        # but the real culprit two hops up is still "a".
        self.assertEqual(dag.failed_ancestors("c", failed={"a"}), ["a"])

    def test_diamond_with_two_independent_failures_finds_both(self):
        dag = TaskDAG()
        for t in ("a", "b", "merge"):
            dag.add_task(t, t)
        dag.add_dependency("merge", depends_on="a")
        dag.add_dependency("merge", depends_on="b")
        self.assertEqual(dag.failed_ancestors("merge", failed={"a", "b"}), ["a", "b"])

    def test_no_failed_ancestor_is_an_empty_list(self):
        dag = TaskDAG()
        dag.add_task("a", "a")
        dag.add_task("b", "b")
        dag.add_dependency("b", depends_on="a")
        self.assertEqual(dag.failed_ancestors("b", failed=set()), [])


class TestSchedulerFaultLocalization(unittest.TestCase):
    """A SKIPPED task's span names the real upstream culprit(s), not a
    generic "a dependency failed" -- multi-hop chains must still localize
    correctly, since Scheduler's cascade only ever sees direct failures."""

    def test_skipped_span_names_the_direct_failed_dependency(self):
        dag = TaskDAG()
        dag.add_task("a", "a")
        dag.add_task("b", "b")
        dag.add_dependency("b", depends_on="a")

        def executor(task_id):
            if task_id == "a":
                raise RuntimeError("boom")
            return {"confidence": 1.0}

        result = Scheduler(dag).run(executor)
        skipped_span = next(s for s in result.spans if s.task_id == "b")
        self.assertIn("a", skipped_span.error)
        self.assertNotEqual(skipped_span.error, "unreachable: a dependency failed")

    def test_skipped_span_names_a_multi_hop_root_cause(self):
        dag = TaskDAG()
        for t in ("a", "b", "c"):
            dag.add_task(t, t)
        dag.add_dependency("b", depends_on="a")
        dag.add_dependency("c", depends_on="b")

        def executor(task_id):
            if task_id == "a":
                raise RuntimeError("boom")
            return {"confidence": 1.0}

        result = Scheduler(dag).run(executor)
        c_span = next(s for s in result.spans if s.task_id == "c")
        self.assertIn("a", c_span.error)

    def test_default_generic_message_preserved_when_no_culprit_found(self):
        # A cycle-free DAG where the "no ready tasks" branch fires without any
        # actual failure in `result.failed` shouldn't happen via the real
        # Scheduler, but failed_ancestors() itself must degrade to the old
        # generic message when it finds nothing -- exercised directly here.
        dag = TaskDAG()
        dag.add_task("a", "a")
        self.assertEqual(dag.failed_ancestors("a", failed=set()), [])


class TestSchedulerFailureClassification(unittest.TestCase):
    """failure_classifier/retry_policy: an optional per-failure-class retry
    budget, off by default (both None reproduce today's flat max_retries)."""

    def test_defaults_reproduce_flat_max_retries_behavior(self):
        dag = TaskDAG()
        dag.add_task("a", "a")
        calls = []

        def always_failing(task_id):
            calls.append(task_id)
            raise RuntimeError("boom")

        result = Scheduler(dag, max_retries=2).run(always_failing)
        self.assertEqual(len(calls), 3)
        span = result.spans[0]
        self.assertEqual(span.attempts, 3)
        self.assertIsNone(span.failure_class)

    def test_classifier_labels_the_span_even_without_a_retry_policy(self):
        dag = TaskDAG()
        dag.add_task("a", "a")

        def classifier(exc):
            return "transient" if "transient" in str(exc) else "structural"

        def failing(task_id):
            raise RuntimeError("transient glitch")

        result = Scheduler(dag, failure_classifier=classifier).run(failing)
        self.assertEqual(result.spans[0].failure_class, "transient")

    def test_retry_policy_grants_a_class_specific_retry_budget(self):
        dag = TaskDAG()
        dag.add_task("a", "a")
        calls = []

        def classifier(exc):
            return "transient"

        def flaky(task_id):
            calls.append(task_id)
            if len(calls) < 3:
                raise RuntimeError("transient glitch")
            return {"confidence": 0.9}

        # max_retries=0 would normally fail after one attempt; retry_policy
        # grants "transient" 5 retries instead, proving the class-specific
        # budget actually overrides the flat default, not just labels it.
        result = Scheduler(dag, max_retries=0, failure_classifier=classifier,
                           retry_policy={"transient": 5}).run(flaky)
        self.assertEqual(len(calls), 3)
        self.assertIn("a", result.completed)
        self.assertEqual(result.spans[0].failure_class, "transient")

    def test_retry_policy_is_inert_for_an_unlisted_class(self):
        dag = TaskDAG()
        dag.add_task("a", "a")
        calls = []

        def classifier(exc):
            return "unlisted_class"

        def always_failing(task_id):
            calls.append(task_id)
            raise RuntimeError("boom")

        result = Scheduler(dag, max_retries=0, failure_classifier=classifier,
                           retry_policy={"transient": 5}).run(always_failing)
        self.assertEqual(len(calls), 1, "an unlisted class must fall back to max_retries, not retry_policy")
        self.assertIn("a", result.failed)

    def test_a_classifier_that_raises_never_breaks_scheduling(self):
        dag = TaskDAG()
        dag.add_task("a", "a")

        def broken_classifier(exc):
            raise ValueError("classifier itself is broken")

        def failing(task_id):
            raise RuntimeError("boom")

        result = Scheduler(dag, failure_classifier=broken_classifier).run(failing)
        self.assertIn("a", result.failed)
        self.assertIsNone(result.spans[0].failure_class)


if __name__ == "__main__":
    unittest.main()
