#!/usr/bin/env python3
"""
Phase 13b: `make conformance` -- validates a whole Scheduler run

Six checks a completed TaskDAG run must pass, any one of which failing means
the observability the survey asked for (a span for every handoff) has a hole
in it, not just that a task happened to fail:

  1. every task has exactly one span (no missing, no duplicate)
  2. every span's status matches its task's final status
  3. every span's started_at <= ended_at
  4. completed/failed/skipped partition the DAG's tasks exactly
     (no overlaps, nothing left uncounted)
  5. the DAG itself has zero dependency cycles
  6. every COMPLETED span recorded a confidence value (a task that "succeeded"
     with no confidence is a worker that didn't actually report anything)

Run directly (`python3 task_conformance.py` / `make conformance`) to execute
a demo TaskDAG and validate it end to end; exits non-zero on any failure so
it's usable as a CI gate, not just a human-read report.
"""

import sys
from dataclasses import dataclass, field
from typing import List

from task_graph import RunResult, Scheduler, TaskDAG, TaskStatus


@dataclass
class ConformanceCheck:
    name: str
    passed: bool
    detail: str = ""


@dataclass
class ConformanceReport:
    checks: List[ConformanceCheck] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return all(c.passed for c in self.checks)

    def render(self) -> str:
        lines = [f"CONFORMANCE: {'PASS' if self.passed else 'FAIL'} "
                 f"({sum(c.passed for c in self.checks)}/{len(self.checks)} checks)"]
        for c in self.checks:
            lines.append(f"  [{'PASS' if c.passed else 'FAIL'}] {c.name}")
            if not c.passed:
                lines.append(f"         {c.detail}")
        return "\n".join(lines)


def check_conformance(dag: TaskDAG, result: RunResult) -> ConformanceReport:
    checks: List[ConformanceCheck] = []

    # 1. every task has exactly one span
    span_counts: dict = {}
    for span in result.spans:
        span_counts[span.task_id] = span_counts.get(span.task_id, 0) + 1
    missing = sorted(set(dag.nodes) - set(span_counts))
    duplicated = sorted(t for t, n in span_counts.items() if n > 1)
    ok = not missing and not duplicated
    checks.append(ConformanceCheck(
        "every task has exactly one span", ok,
        f"missing={missing} duplicated={duplicated}" if not ok else "",
    ))

    # 2. span status matches the task's final status
    mismatches = [
        span.task_id for span in result.spans
        if span.task_id in dag.nodes and span.status != dag.nodes[span.task_id].status
    ]
    checks.append(ConformanceCheck(
        "span status matches task's final status", not mismatches,
        f"mismatched: {mismatches}" if mismatches else "",
    ))

    # 3. started_at <= ended_at
    bad_timing = [s.task_id for s in result.spans if s.ended_at is not None and s.started_at > s.ended_at]
    checks.append(ConformanceCheck(
        "every span started at or before it ended", not bad_timing,
        f"backwards timing: {bad_timing}" if bad_timing else "",
    ))

    # 4. completed/failed/skipped partition dag.nodes exactly
    all_tasks = set(dag.nodes)
    accounted = result.completed | result.failed | result.skipped
    overlap = (result.completed & result.failed) | (result.completed & result.skipped) | (result.failed & result.skipped)
    unaccounted = all_tasks - accounted
    extra = accounted - all_tasks
    ok = not overlap and not unaccounted and not extra
    checks.append(ConformanceCheck(
        "completed/failed/skipped exactly partition the DAG's tasks", ok,
        f"overlap={sorted(overlap)} unaccounted={sorted(unaccounted)} extra={sorted(extra)}" if not ok else "",
    ))

    # 5. DAG has no cycles
    cycles = dag.detect_cycles()
    checks.append(ConformanceCheck(
        "task DAG has no dependency cycles", not cycles,
        f"cycle found: {cycles[0]}" if cycles else "",
    ))

    # 6. every COMPLETED span recorded a confidence
    completed_without_confidence = [
        s.task_id for s in result.spans
        if s.status == TaskStatus.COMPLETED.value and s.confidence is None
    ]
    checks.append(ConformanceCheck(
        "every completed span recorded a confidence", not completed_without_confidence,
        f"no confidence recorded: {completed_without_confidence}" if completed_without_confidence else "",
    ))

    return ConformanceReport(checks=checks)


def _demo_dag() -> TaskDAG:
    dag = TaskDAG()
    dag.add_task("extract_claims", "Extract claims", agent_id="claim_extractor")
    dag.add_task("extract_concepts", "Extract concepts", agent_id="concept_extractor")
    dag.add_task("merge", "Merge results", agent_id="collector")
    dag.add_dependency("merge", depends_on="extract_claims")
    dag.add_dependency("merge", depends_on="extract_concepts")
    return dag


if __name__ == "__main__":
    dag = _demo_dag()
    result = Scheduler(dag).run(lambda task_id: {"confidence": 0.9})
    report = check_conformance(dag, result)
    print(report.render())
    sys.exit(0 if report.passed else 1)
