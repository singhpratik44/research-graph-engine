# Roadmap

One task at a time. Whoever picks this up — human or Claude — works the item
under `## Next` and nothing else, opens/updates a PR against it, and only
moves to the next item after `make validate` is green and a human has merged.

## Done

- Schema + validation (`research_graph_schema.py`)
- Gate (`research_graph_gates.py`)
- Worker loop + envelope contract (`research_graph_workers.py`)
- Deterministic conflict detection (`detect_conflicts_in_graph`)
- Inspection surface (`graph_inspector.py`)
- Agent query layer (`graph_queries.py`)
- Roadmap rollup by paper support (`graph_roadmap.py`)
- Evaluation subsystem: query evals, gate audits, extraction precision/recall,
  regression cases (`graph_evals.py`)
- Web UI: overview, blocked jobs, conflicts, paper drilldown, review queue,
  query box (`webapp.py`)
- Real arXiv ingestion, idempotent (`arxiv_ingest.py`)
- Literature survey corpus, 20 papers / 5 gaps (`literature_corpus.py`)
- CLAUDE.md / this file / Makefile / `run_report.py` — the process governance
  layer itself
- Orchestrator: fan-out over one paper to claim/concept/benchmark extractors,
  collected into one `OrchestrationReport`, still gated by the unchanged
  `WorkerSpawner`/`WorkflowGate` path (`graph_orchestrator.py`); benchmark
  extraction added to `ReferenceWorker` to make the fan-out real, not stubbed;
  `detect_job_dependency_cycles()` added to `graph_queries.py` (cycle
  detection over `BLOCKED_BY` edges, previously declared in the schema but
  unconsumed) — inserted ahead of the queued item below per explicit
  follow-up direction from a second research round on multi-agent graph
  architecture.
- Task DAG + scheduler + structured trace spans + conformance check
  (`task_graph.py`, `task_conformance.py`, `make conformance`). `TaskDAG`/
  `TaskEdge` model work as an explicit, cycle-checked DAG; `Scheduler` runs
  dependency-free tasks concurrently for real (a genuine thread pool, unlike
  `graph_orchestrator.Orchestrator`'s deliberately-sequential fan-out over
  the single-writer `ResearchGraph`) with merge barriers between rounds;
  every task gets one `TaskSpan` (`task_id`, `agent_id`, `parent_task_id`,
  `status`, `confidence`, `started_at`, `ended_at`); `task_conformance.py`
  validates a whole run against six checks. `run_report.py` now runs the
  demo DAG through the real scheduler and reports tasks/completed/failed/
  skipped alongside tests/evals. `graph_algorithms.py` factored out so the
  cycle-detection algorithm isn't duplicated between this and
  `graph_queries.detect_job_dependency_cycles`.
- QIH stress-test corpus (`qih_stress_corpus.py`, ad hoc, not part of the
  sequenced roadmap). Models a real adversarial case -- a document mixing
  well-established physics with self-published, unsupported speculation at
  identical citation confidence -- as 7 papers / 10 claims / 2 genuine
  conflicts, with confidence set from this session's independent fact-check
  rather than the source document's own self-rating. Confirms the gate
  separates claims by *reason code*: solid uncontested claims hit
  `DOWNSTREAM_NOT_ALLOWED` (passed everything, just terminal), genuinely
  under-supported claims hit `LOW_CONFIDENCE`, and both sides of an active
  dispute correctly hit `CONFLICT_UNRESOLVED` until a human resolves it.
  Deliberately kept out of `webapp.py`'s default demo graph (a portfolio UI
  shouldn't silently surface adversarial content about a real named
  individual without context).

## Next

- [ ] Graph memory. Persist, as structured graph data (not flattened
      transcripts): prior task outcomes, accepted claims, rejected claims,
      reviewer disagreements, blocked reasons, and successful repair
      patterns — so future runs get better routing and better review
      decisions. Likely subsumes `gap_typed_provenance_edges` below: a
      memory node needs typed edges (`SUPPORTED_BY`, `REJECTED`,
      `DISAGREED_ON`, ...) to be more than a flat log, so design that
      typing once, here, rather than twice.

## Backlog (in order)

- [ ] Specialist agent split: extractor, conflict checker, schema
      validator, reviewer/judge — bounded specialists with explicit
      handoffs over the task DAG, not many freely-chatting agents. Comes
      *after* graph memory is stable, per this turn's explicit sequencing
      (DAG + traces + memory first).
- [ ] Typed provenance edges (`gap_typed_provenance_edges`, 4 papers in the
      corpus) — see the note under graph memory above; design once as part
      of that work rather than as a separate pass.
- [ ] Claim-source verification gate (`gap_claim_source_verify`, 4 papers).
      `_check_provenance_present` only checks a `source_paper` field is
      non-empty. Add a real entailment/verification check and a new
      `GateReasonCode` (e.g. `CLAIM_NOT_ENTAILED`).
- [ ] Adaptive recovery loop for `WorkerSpawner.admit()` (`gap_adaptive_recovery`,
      2 papers) and for `Scheduler` (a failed task's dependents are currently
      SKIPPED, never retried). A rejected envelope/failed task should support
      a diagnose-and-retarget retry path, not just fail wholesale.
- [ ] Hugging Face Papers / LangChain Blog ingestion — currently documented
      `NotImplementedError` stubs in `arxiv_ingest.py` because neither source
      has a stable public API. Revisit if either publishes a feed.
- [ ] Re-run `arxiv_ingest.py` for real once `export.arxiv.org` is reachable
      from wherever this repo is being worked on (blocked by this session's
      egress policy when last attempted).

## Rules for working an item

1. One bounded item per run — the one under `## Next`, not the whole backlog.
2. Work only on a branch. Never push directly to `main`.
3. Before calling an item done, run `make validate` (tests + evals) and, for
   anything schema/gate-shaped, `make inspect` and `make roadmap` too — see
   `CLAUDE.md`.
4. Every run ends with `python3 run_report.py` (or `make report`) so the
   result is a structured artifact, not a claim.
5. A human reviews and merges. Moving the checked item from `## Next` to
   `## Done` and promoting the next backlog item is part of that merge, not
   something to do preemptively on the same branch.
