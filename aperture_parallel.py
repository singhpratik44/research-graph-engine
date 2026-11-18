"""APERTURE deterministic parallel task scheduler. No autonomous external side effects."""
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
from dataclasses import dataclass, field
from typing import Callable
import time

@dataclass(frozen=True)
class Task:
    id: str
    department: str
    dependencies: tuple[str, ...] = ()
    requires_approval: bool = False
    resource: str = ""

@dataclass
class Result:
    status: str
    value: object = None
    reason: str = ""

def run(tasks: list[Task], workers: dict[str, Callable[[Task], object]],
        approved: set[str] | None = None, max_workers: int = 4) -> dict[str, Result]:
    """Execute independent approved tasks concurrently; block descendants on failure.
    Workers must themselves enforce external-action permissions and idempotency.
    """
    if max_workers < 1:
        raise ValueError("max_workers must be positive")
    by_id = {t.id: t for t in tasks}
    if len(by_id) != len(tasks):
        raise ValueError("duplicate task ID")
    for t in tasks:
        if any(d not in by_id for d in t.dependencies):
            raise ValueError("unknown dependency")
        if t.department not in workers:
            raise ValueError("missing worker")
    remaining = set(by_id)
    results: dict[str, Result] = {}
    running = {}
    busy = set()
    approved = approved or set()
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        while remaining or running:
            progress = False
            for task_id in sorted(tuple(remaining)):
                task = by_id[task_id]
                if any(d in results and results[d].status != "completed" for d in task.dependencies):
                    results[task_id] = Result("blocked", reason="dependency not completed")
                    remaining.remove(task_id)
                    progress = True
                elif task.requires_approval and task_id not in approved:
                    results[task_id] = Result("held", reason="human approval required")
                    remaining.remove(task_id)
                    progress = True
                elif all(d in results and results[d].status == "completed" for d in task.dependencies):
                    if len(running) >= max_workers or (task.resource and task.resource in busy):
                        continue
                    future = pool.submit(workers[task.department], task)
                    running[future] = task
                    if task.resource:
                        busy.add(task.resource)
                    remaining.remove(task_id)
                    progress = True
            if running:
                finished, _ = wait(running, return_when=FIRST_COMPLETED)
                for future in finished:
                    task = running.pop(future)
                    busy.discard(task.resource)
                    try:
                        results[task.id] = Result("completed", value=future.result())
                    except Exception as exc:
                        results[task.id] = Result("failed", reason=str(exc))
            elif remaining and not progress:
                raise ValueError("dependency cycle or unschedulable tasks")
    return results
