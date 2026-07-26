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


if __name__ == "__main__":
    unittest.main()
