#!/usr/bin/env python3
"""
Phase 13: Task DAG + scheduler + structured trace spans

The first production-grade step from this turn's survey: represent work as
explicit nodes and edges, then instrument every handoff with a structured
span, rather than starting from "many chatting agents." This module is
domain-agnostic on purpose -- it doesn't know about papers, claims, or
extraction jobs. graph_orchestrator.py's paper fan-out could be re-expressed
as a TaskDAG later; this module doesn't require that yet.

Four pieces:
  TaskNode / TaskEdge -- the work DAG (typed, closed-enum status)
  TaskSpan            -- one task's execution record: task_id, agent_id,
                         parent_task_id, status, confidence, started_at,
                         ended_at -- the observability unit the survey calls for
  Scheduler            -- runs all dependency-free ("ready") tasks in each
                         round concurrently via a real thread pool, waiting
                         at a merge barrier before computing the next round

Why real threads here (unlike graph_orchestrator.Orchestrator, which stays
sequential): TaskDAG/Scheduler are a fresh, purpose-built structure with a
lock around every shared mutation (task status transitions, the spans list),
so concurrent execution is actually safe here -- not just logically
independent, as it is for the paper fan-out over the single-writer
ResearchGraph. The executor function each task runs is caller-supplied and
receives only the task_id; if that function itself touches a non-thread-safe
resource, thread-safety of that resource is the caller's problem, not this
scheduler's.
"""

import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Callable, Dict, List, Optional, Set

import graph_algorithms


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"      # never ran because a dependency failed


class TaskEdgeType(str, Enum):
    DEPENDS_ON = "depends_on"


@dataclass
class TaskNode:
    task_id: str
    label: str
    agent_id: str = ""
    parent_task_id: Optional[str] = None
    status: str = TaskStatus.PENDING.value


@dataclass
class TaskEdge:
    source: str    # this task...
    target: str    # ...depends on this one
    type: str = TaskEdgeType.DEPENDS_ON.value


@dataclass
class TaskSpan:
    """One task's execution record -- the per-task trace span the survey asks for."""
    task_id: str
    agent_id: str
    parent_task_id: Optional[str]
    status: str
    confidence: Optional[float]
    started_at: str
    ended_at: Optional[str] = None
    error: str = ""

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class RunResult:
    spans: List[TaskSpan] = field(default_factory=list)
    completed: Set[str] = field(default_factory=set)
    failed: Set[str] = field(default_factory=set)
    skipped: Set[str] = field(default_factory=set)

    @property
    def all_succeeded(self) -> bool:
        return not self.failed and not self.skipped


class TaskDAG:
    """The work graph: TaskNodes plus DEPENDS_ON TaskEdges. No execution logic here."""

    def __init__(self):
        self.nodes: Dict[str, TaskNode] = {}
        self.edges: List[TaskEdge] = []

    def add_task(self, task_id: str, label: str, agent_id: str = "",
                 parent_task_id: Optional[str] = None) -> TaskNode:
        if task_id in self.nodes:
            raise ValueError(f"duplicate task_id {task_id!r}")
        node = TaskNode(task_id=task_id, label=label, agent_id=agent_id,
                        parent_task_id=parent_task_id)
        self.nodes[task_id] = node
        return node

    def add_dependency(self, task_id: str, depends_on: str) -> None:
        for tid in (task_id, depends_on):
            if tid not in self.nodes:
                raise KeyError(f"unknown task_id {tid!r} -- add_task() first")
        self.edges.append(TaskEdge(source=task_id, target=depends_on))

    def dependencies_of(self, task_id: str) -> List[str]:
        return [e.target for e in self.edges if e.source == task_id]

    def detect_cycles(self) -> List[List[str]]:
        adjacency: Dict[str, List[str]] = {}
        for e in self.edges:
            adjacency.setdefault(e.source, []).append(e.target)
        return graph_algorithms.detect_cycles(adjacency)

    def ready_tasks(self, completed: Set[str], remaining: Set[str]) -> List[str]:
        """Tasks in `remaining` whose every dependency is already in `completed`."""
        return [t for t in remaining if all(d in completed for d in self.dependencies_of(t))]


class Scheduler:
    """Runs a TaskDAG to completion, one merge-barrier round at a time."""

    def __init__(self, dag: TaskDAG, max_workers: int = 4):
        self.dag = dag
        self.max_workers = max_workers

    def run(self, executor: Callable[[str], Optional[Dict]]) -> RunResult:
        """
        `executor(task_id)` runs one task and may return {"confidence": float}
        (or nothing). Raising marks the task FAILED and skips everything that
        transitively depends on it -- it is never silently ignored.
        """
        cycles = self.dag.detect_cycles()
        if cycles:
            raise ValueError(f"task DAG has a dependency cycle: {cycles[0]}")

        result = RunResult()
        lock = threading.Lock()

        def run_one(task_id: str) -> None:
            node = self.dag.nodes[task_id]
            started = _now()
            with lock:
                node.status = TaskStatus.RUNNING.value
            try:
                outcome = executor(task_id) or {}
                confidence = outcome.get("confidence")
                status, error = TaskStatus.COMPLETED.value, ""
            except Exception as exc:
                confidence, status, error = None, TaskStatus.FAILED.value, repr(exc)

            span = TaskSpan(task_id=task_id, agent_id=node.agent_id,
                            parent_task_id=node.parent_task_id, status=status,
                            confidence=confidence, started_at=started, ended_at=_now(),
                            error=error)
            with lock:
                node.status = status
                result.spans.append(span)
                (result.completed if status == TaskStatus.COMPLETED.value else result.failed).add(task_id)

        remaining: Set[str] = set(self.dag.nodes)
        while remaining:
            ready = self.dag.ready_tasks(result.completed, remaining)
            if not ready:
                # Cycles are already ruled out, so every remaining task must be
                # unreachable because something it (transitively) depends on failed.
                for task_id in remaining:
                    node = self.dag.nodes[task_id]
                    node.status = TaskStatus.SKIPPED.value
                    result.spans.append(TaskSpan(
                        task_id=task_id, agent_id=node.agent_id, parent_task_id=node.parent_task_id,
                        status=TaskStatus.SKIPPED.value, confidence=None,
                        started_at=_now(), ended_at=_now(),
                        error="unreachable: a dependency failed",
                    ))
                    result.skipped.add(task_id)
                break

            with ThreadPoolExecutor(max_workers=self.max_workers) as pool:
                list(pool.map(run_one, ready))

            remaining -= set(ready)

        return result


if __name__ == "__main__":
    import time

    dag = TaskDAG()
    dag.add_task("extract_claims", "Extract claims", agent_id="claim_extractor")
    dag.add_task("extract_concepts", "Extract concepts", agent_id="concept_extractor")
    dag.add_task("merge", "Merge results", agent_id="collector")
    dag.add_dependency("merge", depends_on="extract_claims")
    dag.add_dependency("merge", depends_on="extract_concepts")

    def demo_executor(task_id: str) -> Dict:
        time.sleep(0.05)
        return {"confidence": 0.9}

    result = Scheduler(dag).run(demo_executor)
    for span in result.spans:
        print(f"{span.task_id}: {span.status} (agent={span.agent_id}, "
              f"confidence={span.confidence})")
    print(f"\nall_succeeded={result.all_succeeded}")
