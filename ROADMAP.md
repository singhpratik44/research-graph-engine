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
- Three backlog items built in parallel (isolated git worktrees, one agent
  each, merged with zero file conflicts since each was scoped to distinct
  files) — closing four of the five original capability gaps:
  - **Graph memory** (`graph_memory.py`, schema bumped 3.0.0 → 3.1.0). A new
    `NodeType.MEMORY_RECORD` (with a closed `MemoryKind` enum: task_outcome,
    claim_accepted, claim_rejected, reviewer_disagreement, blocked_reason,
    repair_pattern) plus five new typed `EdgeType` values (`SUPPORTED_BY`,
    `REJECTED_BECAUSE`, `DISAGREED_ON`, `REPAIRED_VIA`, `DERIVED_FROM`) —
    this closes `gap_typed_provenance_edges` as designed once, here, rather
    than as a separate pass. `graph_memory.py` is the one legitimate writer
    besides `research_graph_workers.py`; every other query/inspector/roadmap/
    evals module stays read-only.
  - **Claim-source verification gate** (`claim_verification.py`, new
    `GateReasonCode.CLAIM_NOT_ENTAILED`, new `_check_claim_entailed` check
    in `WorkflowGate`). Closes `gap_claim_source_verify`. Pluggable via
    `entailment_checker=None` by default (a true no-op, so every
    pre-existing test is unaffected); `keyword_overlap_entailment_checker`
    is the deterministic default, explicitly documented as a heuristic
    proxy, not real NLP entailment. Directly demonstrated against the real
    case that motivated it: `qih_stress_corpus.py`'s light-angle claim now
    fails on `CLAIM_NOT_ENTAILED` (score ≈0.053 vs. a 0.15 threshold)
    instead of only being caught by hand-assigned low confidence.
  - **Adaptive recovery loop** (`WorkerSpawner.admit(..., retry_with=,
    max_retries=)`, `Scheduler(..., max_retries=)`). Closes
    `gap_adaptive_recovery`. Both default to today's exact one-attempt
    behavior (`retry_with=None` / `max_retries=0`) — every pre-existing
    test passes unmodified. `TaskSpan` gained `attempts`/`retry_errors`
    fields, one span per task updated in place (not one span per attempt),
    so `task_conformance.py`'s six checks needed zero changes.

  Only `gap_multidim_review` (12 papers, the corpus's best-attested gap)
  remains open — and it's exactly what the specialist agent split below
  addresses. Full suite: 365 tests passing.

## Next

- [x] Specialist agent split: extractor, conflict checker, schema
      validator, reviewer/judge — bounded specialists with explicit
      handoffs over the task DAG, not many freely-chatting agents. Now
      unblocked: DAG + traces (`task_graph.py`) and memory
      (`graph_memory.py`) are both stable, per this turn's explicit
      sequencing (DAG + traces + memory, then agents). Closes the last
      open gap, `gap_multidim_review` — reconciling multiple specialist
      verdicts on one node is the multi-dimensional review the corpus's
      12 papers on this gap all argue for, replacing today's single
      scalar `ReviewStatus`/confidence.

      Built as `specialist_review.py`: four bounded roles — extractor,
      schema validator, conflict checker, reviewer/judge — run as an
      explicit `task_graph.TaskDAG` (`extract` → `{conflict_check,
      schema_validate}` in parallel → `reviewer_judge`), each producing an
      independent, always-completed `SpecialistVerdict`, reconciled into
      one `SpecialistPipelineReport`. `SpecialistVerdict` is deliberately
      kept separate from `GateDecision.checks` — they answer different
      questions (one short-circuited governing verdict vs. one bounded
      role's independent read) — so `research_graph_gates.py` is
      untouched. The schema-validator and conflict-checker roles wrap the
      same pure functions (`validate_node`, `detect_conflicts_in_graph`)
      `graph_orchestrator.py`'s docstring already credited to
      `WorkerSpawner.admit()`, just surfaced as explicit verdicts instead
      of an invisible re-check; `reconcile_and_admit` records a
      `graph_memory.record_disagreement` when the two specialists
      disagree, then calls the real, unchanged `admit()` unconditionally.
      Purely additive: `research_graph_gates.py`,
      `research_graph_workers.py`, `research_graph_schema.py`,
      `task_graph.py`, `graph_memory.py`, and `graph_orchestrator.py` are
      all unmodified. Closes all five original capability gaps
      (`gap_typed_provenance_edges`, `gap_claim_source_verify`,
      `gap_roadmap_queries`, `gap_adaptive_recovery`,
      `gap_multidim_review`). Moving this to `## Done` and promoting the
      next backlog item happens at merge time (rule 5 below), not on this
      branch.

## Backlog (in order)

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
