#!/usr/bin/env python3
"""
Test suite for task_conformance.py. Each check needs a positive case (a real
run passes it) and a negative case (a deliberately corrupted run fails it) --
a conformance checker that can't fail is decorative, not a gate.
"""

import unittest

from task_graph import RunResult, Scheduler, TaskDAG, TaskSpan, TaskStatus
from task_conformance import check_conformance, _demo_dag


def _clean_run():
    dag = _demo_dag()
    result = Scheduler(dag).run(lambda task_id: {"confidence": 0.9})
    return dag, result


class TestCleanRunPassesEverything(unittest.TestCase):
    def test_demo_dag_is_fully_conformant(self):
        dag, result = _clean_run()
        report = check_conformance(dag, result)
        self.assertTrue(report.passed, [c.name for c in report.checks if not c.passed])
        self.assertEqual(len(report.checks), 6)

    def test_render_includes_pass_count(self):
        dag, result = _clean_run()
        report = check_conformance(dag, result)
        self.assertIn("6/6", report.render())


class TestMissingAndDuplicateSpans(unittest.TestCase):
    def test_missing_span_fails_that_check_only(self):
        dag, result = _clean_run()
        result.spans = [s for s in result.spans if s.task_id != "merge"]
        report = check_conformance(dag, result)
        failing = {c.name for c in report.checks if not c.passed}
        self.assertIn("every task has exactly one span", failing)
        self.assertFalse(report.passed)

    def test_duplicate_span_fails_that_check(self):
        dag, result = _clean_run()
        result.spans.append(result.spans[0])
        report = check_conformance(dag, result)
        failing = {c.name for c in report.checks if not c.passed}
        self.assertIn("every task has exactly one span", failing)


class TestStatusMismatch(unittest.TestCase):
    def test_span_status_disagreeing_with_task_status_is_caught(self):
        dag, result = _clean_run()
        # Corrupt one span's status without touching the task node's real status.
        corrupted = result.spans[0]
        result.spans[0] = TaskSpan(
            task_id=corrupted.task_id, agent_id=corrupted.agent_id,
            parent_task_id=corrupted.parent_task_id, status=TaskStatus.FAILED.value,
            confidence=corrupted.confidence, started_at=corrupted.started_at,
            ended_at=corrupted.ended_at,
        )
        report = check_conformance(dag, result)
        failing = {c.name for c in report.checks if not c.passed}
        self.assertIn("span status matches task's final status", failing)


class TestTimingCheck(unittest.TestCase):
    def test_backwards_timing_is_caught(self):
        dag, result = _clean_run()
        s = result.spans[0]
        result.spans[0] = TaskSpan(
            task_id=s.task_id, agent_id=s.agent_id, parent_task_id=s.parent_task_id,
            status=s.status, confidence=s.confidence,
            started_at="2026-01-01T00:00:10", ended_at="2026-01-01T00:00:00",
        )
        report = check_conformance(dag, result)
        failing = {c.name for c in report.checks if not c.passed}
        self.assertIn("every span started at or before it ended", failing)


class TestPartitionCheck(unittest.TestCase):
    def test_task_missing_from_every_bucket_is_caught(self):
        dag, result = _clean_run()
        result.completed.discard("merge")
        report = check_conformance(dag, result)
        failing = {c.name for c in report.checks if not c.passed}
        self.assertIn("completed/failed/skipped exactly partition the DAG's tasks", failing)

    def test_task_in_two_buckets_is_caught(self):
        dag, result = _clean_run()
        result.failed.add("merge")  # merge is already in completed
        report = check_conformance(dag, result)
        failing = {c.name for c in report.checks if not c.passed}
        self.assertIn("completed/failed/skipped exactly partition the DAG's tasks", failing)


class TestCycleCheck(unittest.TestCase):
    def test_cyclic_dag_fails_the_cycle_check(self):
        dag = TaskDAG()
        dag.add_task("a", "a")
        dag.add_task("b", "b")
        dag.add_dependency("a", depends_on="b")
        dag.add_dependency("b", depends_on="a")
        # Can't run a cyclic DAG through the real scheduler (it raises), so
        # build a RunResult by hand to test this check in isolation.
        result = RunResult()
        report = check_conformance(dag, result)
        failing = {c.name for c in report.checks if not c.passed}
        self.assertIn("task DAG has no dependency cycles", failing)


class TestConfidenceCheck(unittest.TestCase):
    def test_completed_span_with_no_confidence_is_caught(self):
        dag = TaskDAG()
        dag.add_task("a", "a")
        result = Scheduler(dag).run(lambda task_id: {})  # no confidence reported
        report = check_conformance(dag, result)
        failing = {c.name for c in report.checks if not c.passed}
        self.assertIn("every completed span recorded a confidence", failing)

    def test_failed_span_with_no_confidence_does_not_trip_this_check(self):
        dag = TaskDAG()
        dag.add_task("a", "a")

        def failing_executor(task_id):
            raise RuntimeError("boom")

        result = Scheduler(dag).run(failing_executor)
        report = check_conformance(dag, result)
        # The failure itself fails the run overall, but not via this specific check.
        confidence_check = next(c for c in report.checks
                                if c.name == "every completed span recorded a confidence")
        self.assertTrue(confidence_check.passed)


if __name__ == "__main__":
    unittest.main()
