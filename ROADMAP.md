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
- Three literature-informed robustness improvements (ad hoc, not part of
  the sequenced roadmap — like the QIH stress-test corpus above, these
  came from a dedicated research pass rather than from working the
  backlog in order). 10 real studies/posts from the last ~3 months,
  filtered through robustness → graph-theory → agentic-architecture
  lenses, informed three additive changes, all purely additive (every
  pre-existing test passes unmodified):
  - **Fault localization** (`task_graph.TaskDAG.failed_ancestors`). A
    SKIPPED task's span now names which upstream task(s) actually failed
    — a transitive closure over the DAG's existing `DEPENDS_ON` edges —
    replacing the generic `"unreachable: a dependency failed"` message.
    Deliberately does *not* add a second, confidence-graded edge layer
    (as one literature source proposes): a dependency here either failed
    or it didn't, so the existing single edge type is exact, not an
    approximation, and a second layer would only risk polluting
    `detect_cycles()` for no benefit.
  - **Failure-class recovery dispatch** (`task_graph.Scheduler`'s new
    `failure_classifier`/`retry_policy` params; `research_graph_workers
    .classify_rejection()`). A failure's classified label can grant a
    different retry budget than the flat `max_retries`, so different
    failure classes get different recovery budgets instead of one
    undifferentiated retry count. Both default to `None`, reproducing
    today's flat-retry behavior exactly. `classify_rejection()` is a
    standalone pure function classifying `admit()`'s 18 known rejection
    shapes into 5 broad classes — not wired into `admit()` itself, which
    is completely unchanged; a caller's own `retry_with` can consult it.
  - **Atomic claim-entailment decomposition** (`claim_verification
    .atomic_entailment_checker`/`atomic_entailment_report`). Scores each
    clause of a compound claim independently and requires the *weakest*
    to clear the bar, instead of one holistic bag-of-words score — a
    single unsupported clause in an otherwise-plausible claim can no
    longer hide behind the rest. Same drop-in `Callable[[Node, Graph],
    bool]` signature as `keyword_overlap_entailment_checker` (left
    completely unmodified); `research_graph_gates.py` is untouched, since
    the `CLAIM_NOT_ENTAILED`-before-`LOW_CONFIDENCE` short-circuit
    ordering is a property of the gate's fixed check sequence, not of
    which checker is configured. Per-atom detail lives only in the
    separate `atomic_entailment_report()` diagnostic, not in the gate's
    `CheckTrace.evidence`.

  Full suite: 441 tests passing.
- Specialist agent split: extractor, conflict checker, schema validator,
  reviewer/judge — bounded specialists with explicit handoffs over the
  task DAG, not many freely-chatting agents (`specialist_review.py`). Four
  bounded roles — extractor, schema validator, conflict checker,
  reviewer/judge — run as an explicit `task_graph.TaskDAG` (`extract` →
  `{conflict_check, schema_validate}` in parallel → `reviewer_judge`),
  each producing an independent, always-completed `SpecialistVerdict`,
  reconciled into one `SpecialistPipelineReport`. `SpecialistVerdict` is
  deliberately kept separate from `GateDecision.checks` — they answer
  different questions (one short-circuited governing verdict vs. one
  bounded role's independent read) — so `research_graph_gates.py` is
  untouched. The schema-validator and conflict-checker roles wrap the
  same pure functions (`validate_node`, `detect_conflicts_in_graph`)
  `graph_orchestrator.py`'s docstring already credited to
  `WorkerSpawner.admit()`, just surfaced as explicit verdicts instead of
  an invisible re-check; `reconcile_and_admit` records a
  `graph_memory.record_disagreement` when the two specialists disagree,
  then calls the real, unchanged `admit()` unconditionally. Purely
  additive: `research_graph_gates.py`, `research_graph_workers.py`,
  `research_graph_schema.py`, `task_graph.py`, `graph_memory.py`, and
  `graph_orchestrator.py` are all unmodified. Closes all five original
  capability gaps (`gap_typed_provenance_edges`, `gap_claim_source_verify`,
  `gap_roadmap_queries`, `gap_adaptive_recovery`, `gap_multidim_review`).
  Merged via PR #1 into `main` (merge commit `bb74dae4`).
- Repo hardening pass (ad hoc, not part of the sequenced roadmap — same
  spirit as the QIH corpus and the literature-informed improvements
  above: infrastructure/portfolio work, not a queued capability gap).
  - **`LLMWorker`** (`llm_worker.py`). A drop-in for `ReferenceWorker`
    backed by a real Claude API call instead of regex heuristics,
    satisfying the identical `ExtractionDirective`-in/`ResultEnvelope`-out
    contract — `WorkerSpawner.admit()` needs no changes to accept its
    output. `call_model` is injected (same pattern as `arxiv_ingest.py`'s
    `http_get`), so parsing/envelope-construction is fully tested (19
    tests) without a network call; the real call path needs
    `ANTHROPIC_API_KEY`, which this sandbox has never had, so it's
    written but not exercised end-to-end here — stated plainly per
    CLAUDE.md rule 5, not left implicit.
  - **`make typecheck`** (`mypy.ini`, wired into CI as a step separate
    from `make validate` — additional rigor, not a redefinition of
    CLAUDE.md's test+evals+conformance "done" contract). Fixed the real
    type-honesty gaps it surfaced: a genuine bug in `specialist_review
    .py`'s `reconcile_and_admit` return-type annotation (bare tuple
    syntax, not `Tuple[...]`); `research_graph_gates.Provenance
    .confidence` was typed `float` but already handled `None`
    defensively — now `Optional[float]`, honestly; the intentional
    `research_graph_gates.Node`/`research_graph_schema.Node` duck-typing
    bridge and `graph_memory.py`'s soft `TaskSpan` import fallback are
    now documented with explicit, reasoned `type: ignore` comments
    instead of silently mismatching or being blanket-suppressed.
  - **CI** (`.github/workflows/ci.yml`) running `make validate` and
    `make typecheck` on every push/PR — previously `make validate` only
    ever ran locally, so a PR showed zero check runs.
  - **`LICENSE`** (MIT) and **README screenshots** (`docs/webapp-*.png`,
    captured from a live `uvicorn` run against the real demo graph) —
    both closing gaps in what a reader can verify without cloning and
    running the repo themselves.
  - **Domain-pluggable `LLMWorker` prompts** (`llm_worker.py`'s
    `domain=` param — `research` (default, byte-for-byte the original
    wording), `hiring`, `ops_approval`, `compliance`, or a full
    `prompt_overrides` escape hatch). Closes a real gap between what
    README.md claims ("the same schema/gate/query pattern applies to
    hiring pipelines, ops approvals, compliance review") and what the
    one LLM-backed worker actually demonstrated: only the framing
    sentence changes per domain, the JSON field contract
    (`_field_instructions`) stays identical and domain-independent.

  Full suite: 460 tests passing; `make typecheck` clean across all 41
  modules.
- Four more literature-informed engine improvements (ad hoc, not part of
  the sequenced roadmap — same posture as the two rounds above: this came
  from a dedicated research pass over 10 more real studies/papers from the
  last ~3 months, not from working the backlog in order). All four are
  purely additive; every pre-existing test passes unmodified.
  - **Confidence divergence** (`graph_memory.record_confidence_divergence`/
    `confidence_divergence_for`; `specialist_review.check_confidence_
    divergence`, wired into `run_specialist_pipeline`'s new
    `divergence_threshold=None` param). A claim's confidence at first
    derivation vs. a later re-validation can drift; three independent
    papers converge on treating that drift as a first-class signal
    instead of silently overwriting the old reading. One new `MemoryKind`
    member (`CONFIDENCE_DIVERGENCE`, schema `3.1.0` → `3.2.0`) — zero
    `NODE_SCHEMA` structural change, since `memory_kind` was already
    enum-validated.
  - **Selective failure-class recovery** (`specialist_review
    .resumable_tasks`/`classify_specialist_failure`/
    `resume_specialist_pipeline`). Today a failed extraction cascades
    SKIPPED to all three other specialist tasks, and any retry redoes the
    whole four-role pipeline; two papers converge on selective,
    failure-class-driven recovery instead. Resuming only re-attempts
    stale tasks — if only `reviewer_judge` failed (the one partial
    pattern this DAG's code can actually produce), only it re-runs,
    reusing the prior envelope and verdicts without re-invoking the
    worker. Explicitly rejected: exposing `Scheduler`'s retry knobs
    across the whole DAG, since a naive blind retry risked a
    double-admission if `admit()` were ever reachable twice.
  - **Specialist trust scores** (`graph_memory.specialist_trust_scores`/
    `trust_score_for`). Aggregates every recorded reviewer disagreement
    into a per-role agreement/disagreement tally against the disputed
    node's own eventual outcome — no new signed-edge schema, since the
    ground truth for "who was right" already lives in the graph. An
    outcome that's still undecided never falsely counts as a
    disagreement.
  - **Derivation-mechanism classification** (`graph_queries
    .derivation_mechanism_for`/`derivation_mechanism_breakdown`). The
    thinnest-evidence feature of the four (single paper) — deliberately
    built as plain classification strings from existing node data, not a
    new `ExtractionMethod` schema member, since committing a new closed
    enum ahead of a real producer would be premature.

  Full suite: 493 tests passing.
- **Runtime action-policy enforcement** (`action_policy.py`, new module;
  ad hoc, not part of the sequenced roadmap — a research pass on
  "runtime policy enforcement for autonomous agents" surfaced a real
  architectural gap this closes). Every existing check in this repo
  (`WorkflowGate`, the specialist verdicts) evaluates a claim/node
  *after* a worker already produced it — post-hoc data validation, not
  runtime action enforcement. `ActionPolicy.authorize()` evaluates a
  *proposed* extraction (paper_id, extraction_type, confidence_floor,
  max_results) before any worker is invoked, returning ALLOWED /
  ESCALATED / BLOCKED from pluggable rules. `authorize_then_spawn()` is
  the actual enforcement point: only ALLOWED spawns immediately — both
  ESCALATED and BLOCKED hold the action, no job node created, no worker
  invoked. `approve_escalated_action()` is the only way an escalated
  action proceeds (a human decision, not automatic); a BLOCKED one
  can't be approved past at all (`ValueError` if attempted) — the
  policy said no, not "ask a human." One new `MemoryKind` member
  (`ACTION_POLICY_DECISION`, schema `3.2.0` → `3.3.0`) persists every
  decision as durable audit evidence via `graph_memory
  .record_action_policy_decision`/`action_policy_decisions_for`,
  linked to the real job node when one exists (a blocked action, by
  definition, has none to link to). Purely additive:
  `research_graph_workers.py`, `research_graph_gates.py`,
  `specialist_review.py` are all unmodified — this only calls
  `WorkerSpawner.spawn()` and the new `graph_memory` function.

  Full suite: 517 tests passing.
- **Three literature-informed hardening improvements** (ad hoc, not part of
  the sequenced roadmap — a research pass across robustness, graph-theory,
  and agentic-architecture lenses, scoped against everything already built
  this project, surfaced these as the three candidates with genuine
  multi-paper convergence and a clean fit to an existing module; weaker,
  single-paper or extrapolated candidates from the same pass were
  deliberately left undone). All three are purely additive.
  - **Closed-loop (post-execution) action-policy enforcement**
    (`action_policy.py`'s `ExecutionOutcome`/`authorize_outcome()`/
    `authorize_execute_then_admit()`/`approve_escalated_outcome()`).
    `authorize_then_spawn()` alone only ever authorizes a *declared*
    action before it runs — GAAT (arXiv 2604.05119) names exactly this
    "observe-but-do-not-act" gap in real agent telemetry.
    `authorize_execute_then_admit()` runs the worker only if the
    pre-action check is ALLOWED, then re-authorizes the *realized*
    outcome (`block_low_average_confidence_outcome`,
    `max_nodes_produced_ceiling`, `escalate_on_worker_failure`) before
    `spawner.admit()` is ever called — a worker's side effects can't be
    undone, but a blocked/escalated outcome never reaches the graph.
    `approve_escalated_outcome()` admits an already-produced, held
    envelope without re-invoking the worker. `authorize_then_spawn`/
    `approve_escalated_action` are both unchanged.
  - **Trajectory-level failure diagnosis** (`specialist_review
    .diagnose_pipeline_failure`/`PipelineFailureDiagnosis`). VerifyMAS and
    "Recognize Your Orchestrator" (ICML 2026) both find per-task failure
    classification misses errors that only show up across a DAG's full
    trajectory, and that failures concentrate at the orchestrating role
    (here, `reviewer_judge`) rather than uniformly across executors.
    `diagnose_pipeline_failure()` reads root-cause task(s), blast radius,
    and whether the failure originated at `reviewer_judge` itself
    directly off an already-completed `RunResult` — advisory only, it
    never changes what `resume_specialist_pipeline` retries.
    `classify_specialist_failure`/`resume_specialist_pipeline` are both
    unchanged.
  - **Provenance-bound trust + governed retraction** (`graph_memory
    .provenance_trust_weight_for`/`provenance_bound_confidence`/
    `provenance_weighted_trust_scores`; `retract_memory_record`/
    `is_retracted`/`active_memory_records_for`). Two independent 2026
    papers (a long-term agent-memory-security survey and a
    provenance-capped belief-updating paper) converge on capping trust
    by source provenance rather than a source's own self-reported
    confidence, and on treating "Forget & Rollback" as a first-class,
    security-relevant lifecycle phase this repo's `MemoryKind` enum
    previously had no analog for (schema `3.3.0` → `3.4.0`, one new
    member: `MEMORY_RETRACTED`). `provenance_weighted_trust_scores` is a
    new, parallel aggregation to `specialist_trust_scores` — the latter
    is otherwise unchanged in its own arithmetic, and now additionally
    skips retracted disagreements (a no-op for any graph that never
    retracts one). Retraction is itself a new, append-only memory record
    linked back to what it retracts — never a deletion or in-place edit.

  Full suite: 568 tests passing; `make typecheck` clean across all 43
  modules.
- **Eight literature-informed improvements, one full pass** (ad hoc, not
  part of the sequenced roadmap — a research pass across robustness,
  graph theory, and agentic architecture, scoped against everything
  already built, surfaced all eight below; unlike the Tier-1-only rounds
  above, this pass was built in full — Tier 2/3 candidates included, each
  with its evidentiary strength stated honestly at the time it was
  proposed). All purely additive.
  - **Obligation/dispensation + meta-policy conflict visibility**
    (`action_policy.py`'s `Obligation`/`notify_on_verdict`/
    `fulfill_obligation`/`dispense_obligation`/`pending_obligations`;
    `PolicyDecision.all_rule_verdicts`/`has_conflicting_rules`).
    AgenticRei (arXiv 2606.19464) names obligation-lifecycle management
    and governed dispensations as primitives ALLOWED/ESCALATED/BLOCKED
    alone can't represent. Every rule that fires on an action is now
    recorded, not just the one precedence picks, so a genuine conflict
    between rules (one would escalate, another would block) is a visible
    fact, not a silently-applied precedence order.
  - **Trace-level (whole-trajectory) trust** (`graph_memory
    .full_trajectory_for`/`trajectory_trust_score`). Two independent 2026
    papers ("From Agent Traces to Trust"; "AgentTrails") find trust
    judgments stopping at one claim-to-source hop miss most of an agent's
    real execution trace. Aggregates TASK_OUTCOME, CONFIDENCE_DIVERGENCE,
    ACTION_POLICY_DECISION, and REVIEWER_DISAGREEMENT records reachable
    by following subject_ref chains multiple hops deep into one weighted
    score, distinct from `specialist_trust_scores`/`provenance_weighted
    _trust_scores`'s one-hop, disagreement-only view (neither changed).
  - **Attributed-statement query view** (`graph_queries
    .attributed_positions_for`). "Provenance-Enhanced Statements in
    Knowledge Graphs" argues attribution should be a first-class,
    coexisting relation rather than forcing differently-worded or
    conflicting claims about the same subject/object into one value. No
    schema change needed — every claim already carries its own
    `Provenance.source_paper`; this is a pure, read-only query surfacing
    what already coexists in the graph.
  - **Corpus-level construction-quality checks** (`graph_evals
    .claim_field_completeness`/`duplicate_text_ratio`/
    `orphaned_node_ratio`, wired into `run_all()` as a new
    `CONSTRUCTION_QUALITY` category). KGCQual (2026) argues systemic
    extraction-pipeline issues are a corpus-level signal that per-node
    schema validation can't surface on its own.
  - **Static hazard detection for `TaskDAG`** (`task_graph.TaskDAG
    .detect_hazards`). AgentFlow (2026) performs static analysis of agent
    program dependency graphs before execution; applied here to a
    dangling `parent_task_id` and disconnected ("island") tasks — neither
    stops a `Scheduler` run on its own, so nothing else would ever catch
    them. Flagged at proposal as a partial stretch (AgentFlow analyzes
    program code, `TaskDAG` is a runtime data structure) — the general
    discipline transferred, not the specific machinery.
  - **Bi-temporal `valid_from` on retraction** (`graph_memory
    .retract_memory_record`'s new optional param). A bi-temporal
    graph-management paper argues systems conflate "when we found out"
    (`recorded_at`, already stamped on every record) with "when it
    stopped being true" — two different questions. `valid_from` lets a
    caller state the latter explicitly; omitting it changes nothing.
  - **Multi-signal graded confidence** (`claim_verification
    .multi_signal_confidence`/`multi_signal_entailment_checker`). "Beyond
    Logprobs" and SEVA (both 2026) argue a single confidence signal is
    insufficient in a high-stakes pipeline. Combines the existing
    whole-claim bag-of-words score and weakest-atom score into one graded
    report, requiring both to independently agree — same drop-in
    `Callable[[Node, Graph], bool]` contract as the other two checkers,
    neither of which is modified.
  - **Repair-pattern effectiveness check** (`graph_evals
    .repair_pattern_effectiveness`, wired into `run_all()` as a new
    `MEMORY_EFFECTIVENESS` category). LongMemEval-V2 (ICML 2026 SCALE
    workshop) asks whether accumulated agent memory actually helps, not
    just whether it's well-formed. Thin evidence (one workshop paper) —
    a narrow, honest proxy (does a recorded repair's `after_node` still
    resolve to something reusable), not a general claim that "memory
    helps."

  Full suite: 634 tests passing; `make typecheck` clean across all 43
  modules.

## Next

- [ ] Hugging Face Papers / LangChain Blog ingestion — currently documented
      `NotImplementedError` stubs in `arxiv_ingest.py` because neither source
      has a stable public API. Revisit if either publishes a feed. Promoted
      here at merge time per rule 5, but note it is currently blocked
      externally (no stable public API to ingest against) — whoever picks
      this up should re-check whether either source has published a feed
      before doing anything else, and stop and report back if not, rather
      than inventing scope to fill the slot.

## Backlog (in order)

- [ ] Re-run `arxiv_ingest.py` for real once `export.arxiv.org` is reachable
      from wherever this repo is being worked on (blocked by this session's
      egress policy when last attempted). Re-confirmed 2026-07-26: live call
      to `export.arxiv.org/api/query` still gets `403 Forbidden` at the
      proxy tunnel before any request reaches arXiv — the proxy's egress
      allowlist (`selective: false`) does not include `export.arxiv.org`.
      Same failure mode as before, no new information; do not retry until
      this environment's egress policy changes.

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
