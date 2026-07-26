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

## Next

- [ ] Typed provenance edges (`gap_typed_provenance_edges`, 4 papers in the
      corpus). Today `Provenance` is one flat record. Add typed `EdgeType`
      values (e.g. `DERIVED_FROM`, `SUPERSEDES`) to `research_graph_schema.py`,
      regenerate `graph_schema.json` via `export_json_schema()`, and prove the
      gate still evaluates identically on the existing golden fixtures before
      touching anything downstream.

## Backlog (in order)

- [ ] Claim-source verification gate (`gap_claim_source_verify`, 4 papers).
      `_check_provenance_present` only checks a `source_paper` field is
      non-empty. Add a real entailment/verification check and a new
      `GateReasonCode` (e.g. `CLAIM_NOT_ENTAILED`).
- [ ] Adaptive recovery loop for `WorkerSpawner.admit()` (`gap_adaptive_recovery`,
      2 papers). A rejected envelope fails the job wholesale today; add a
      diagnose-and-retarget retry path.
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
