#!/usr/bin/env python3
"""
Phase 12: Orchestrator (fan-out over one paper)

The practical design straight out of the graph-theory / agentic-architecture
survey shared this turn: an orchestrator creates one extraction_job per
specialist role, fans out to parallel workers (claim extractor, concept
extractor, benchmark extractor), each writes partial outputs + traces through
the *unchanged* WorkerSpawner/gate path, and a Collector merges every job's
outcome into one OrchestrationReport.

Two of the survey's six steps were already built before this module existed,
not duplicated here:
  - "conflict checker" -- WorkerSpawner.admit() already runs
    detect_conflicts_in_graph() after every admission.
  - "schema validator checks conformance" / "gate logic decides" -- already
    inside WorkerSpawner.admit() via _verify_envelope() and WorkflowGate.
This module adds only the fan-out and the collection step around admit(),
matching the survey's own "best orchestration rule": parallelize extraction,
keep the final gate/approval centralized.

Concurrency note: "parallel" here means independent, order-doesn't-matter
fan-out branches -- a task DAG with no edges between the specialist jobs --
not literally threaded execution. ResearchGraph/WorkerSpawner are documented
as having a single writer; running real threads against a shared, unlocked
node list would silently reintroduce the races the envelope/gate design
exists to rule out. Each branch is independently schedulable; this
implementation runs them sequentially on purpose.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence

from research_graph_schema import ExtractionType, JobStatus, ResearchGraph
import research_graph_gates as gates
from research_graph_workers import AdmissionResult, ReferenceWorker, WorkerSpawner

DEFAULT_EXTRACTION_TYPES = (ExtractionType.CLAIMS, ExtractionType.CONCEPTS, ExtractionType.BENCHMARKS)


@dataclass
class OrchestrationReport:
    """The Collector's output: every specialist job's outcome, merged."""
    paper_id: str
    admissions: List[AdmissionResult] = field(default_factory=list)

    @property
    def extraction_types_run(self) -> List[str]:
        return [a.job_node.properties.get("extraction_type", "") for a in self.admissions]

    @property
    def all_admitted(self) -> bool:
        return all(a.admitted for a in self.admissions)

    @property
    def total_nodes_admitted(self) -> int:
        return sum(a.nodes_admitted for a in self.admissions)

    @property
    def total_conflicts_found(self) -> int:
        return sum(a.conflicts_found for a in self.admissions)

    @property
    def held_job_ids(self) -> List[str]:
        return [a.job_node.id for a in self.admissions
                if a.job_node.properties.get("status") == JobStatus.HELD.value]

    @property
    def failed_job_ids(self) -> List[str]:
        return [a.job_node.id for a in self.admissions if not a.admitted]

    def to_dict(self) -> Dict:
        return {
            "paper_id": self.paper_id,
            "extraction_types_run": self.extraction_types_run,
            "all_admitted": self.all_admitted,
            "total_nodes_admitted": self.total_nodes_admitted,
            "total_conflicts_found": self.total_conflicts_found,
            "held_job_ids": self.held_job_ids,
            "failed_job_ids": self.failed_job_ids,
            "admissions": [a.to_dict() for a in self.admissions],
        }


class Orchestrator:
    """
    Planner/orchestrator over WorkerSpawner. Owns no state of its own beyond
    which worker/gate to use -- the graph is still the single source of
    truth, and WorkerSpawner is still its only writer.
    """

    def __init__(
        self,
        graph: ResearchGraph,
        gate: Optional[gates.WorkflowGate] = None,
        worker: Optional[ReferenceWorker] = None,
    ):
        self.spawner = WorkerSpawner(graph, gate)
        self.worker = worker or ReferenceWorker(worker_id="orchestrator_reference_worker")

    def run_paper(
        self,
        paper_id: str,
        text: str,
        extraction_types: Sequence[ExtractionType] = DEFAULT_EXTRACTION_TYPES,
        confidence_floor: float = 0.0,
        max_results: Optional[int] = None,
    ) -> OrchestrationReport:
        """
        Fans out one extraction_job per extraction type in `extraction_types`,
        running each through the worker and admitting it via the unchanged
        WorkerSpawner/gate path, then collects every outcome into a report.
        """
        admissions: List[AdmissionResult] = []
        for extraction_type in extraction_types:
            _, directive = self.spawner.spawn(
                paper_id, extraction_type,
                confidence_floor=confidence_floor, max_results=max_results,
            )
            envelope = self.worker.run(directive, text)
            admissions.append(self.spawner.admit(directive, envelope))
        return OrchestrationReport(paper_id=paper_id, admissions=admissions)


if __name__ == "__main__":
    import sys

    text = sys.argv[1] if len(sys.argv) > 1 else (
        "Hierarchical orchestration reduces coordination overhead. "
        "We evaluate on SWE-Bench and the PRISM benchmark."
    )
    graph = ResearchGraph()
    report = Orchestrator(graph).run_paper("paper_demo_001", text)
    for a in report.admissions:
        print(f"{a.job_node.id}: admitted={a.admitted} nodes={a.nodes_admitted} "
              f"status={a.job_node.properties.get('status')}")
    print(f"\ntotal nodes admitted: {report.total_nodes_admitted}")
    print(f"held jobs: {report.held_job_ids or 'none'}")
