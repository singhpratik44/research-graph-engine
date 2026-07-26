# research-graph-engine

A **governed workflow engine**: extract → gate → review → query, with every step
traced and every gate decision auditable. Papers go in; validated, provenance-
tracked claims and concepts come out — and nothing advances a stage without
passing a deterministic gate that records *why*.

Research literature is this repo's one worked example, not its ceiling. The
same schema/gate/query/roadmap/eval pattern applies to anything shaped like
*extract a claim from a source, decide if it's trustworthy enough to act on,
let a human override that decision on the record* — hiring pipelines, ops
approvals, compliance review, or any other domain where "why was this
allowed through" has to be an answerable question, not a shrug.

The point isn't the extraction. It's that every node in the graph can answer:
who produced me, from what source, with what confidence, which checks did I
pass, and if a human waived one of those checks — who, and on what grounds.

## The pipeline

| Layer | File | What it does |
|---|---|---|
| Schema | `research_graph_schema.py` | Closed node/edge types, structured traces, validation with reason codes — not a bare bool |
| Gate | `research_graph_gates.py` | `WorkflowGate.should_unlock_next_stage()` — six deterministic checks, every verdict traced |
| Workers | `research_graph_workers.py` | `ExtractionDirective` in, `ResultEnvelope` out; `WorkerSpawner` is the only writer to the graph, and treats every worker as untrusted |
| Conflict detection | `research_graph_schema.detect_conflicts_in_graph()` | Deterministic heuristics first — same subject/object, opposed relation |
| Inspection | `graph_inspector.py` | Plain-text report: papers, claims, conflicts, jobs, held/review-required, and *why* a gate blocked each one (re-runs the live gate, not a cached string) |
| Query layer | `graph_queries.py` | `get_node`, `neighbors`, `claims_for_paper`, `contradicting_claims`, `why_blocked`, `search` — structured answers, not text to parse |
| Roadmap | `graph_roadmap.py` | Rolls GAP/METHOD/DOMAIN/BENCHMARK nodes up by how many papers substantiate each one |
| Evaluation | `graph_evals.py` | Quality, not just correctness: query-answer evals, gate-decision audits, extraction precision/recall, and a regression set that must never silently start passing again |
| Web UI | `webapp.py` | FastAPI: graph overview, blocked jobs, unresolved conflicts, paper → claims drilldown, review queue, and a small query box over the graph |
| Live ingestion | `arxiv_ingest.py` | Real calls to the public arXiv API, converted into schema-conforming PAPER nodes, idempotent against re-running the same query |
| Worked example | `literature_corpus.py` | 20 real papers (two survey rounds) entered as graph data, each `ADDRESSES` a capability gap this repo used to decide what to build next — the repo dogfooding its own schema to plan itself |
| Run reporting | `run_report.py` | Structured per-run output — files changed, tests, evals, risks, next step — computed for real from git and the actual test/eval runners, not a prose summary |

Process is governed the same way the graph is: `CLAUDE.md` sets the rules an
autonomous run works under (one bounded roadmap item, branch-only, full
validation before done, structured report at the end), and `ROADMAP.md`
sequences what's next one item at a time rather than as an open pile.

## Quickstart

```bash
pip install -r requirements.txt

# run everything
make test              # == python3 -m unittest discover -p "test_*.py"

# see the graph, as a human would
make inspect            # == python3 graph_inspector.py

# ask it questions
make roadmap             # == python3 graph_roadmap.py

# check quality, not just correctness
make evals               # == python3 graph_evals.py

# tests + evals together -- the one thing a run must pass before it's done
make validate

# the web UI
make web                 # == uvicorn webapp:app --reload
# then open http://127.0.0.1:8000

# real arXiv ingestion (needs export.arxiv.org reachable)
python3 arxiv_ingest.py "all:knowledge graph provenance"

# structured summary of this run: files changed, tests, evals, next step
make report              # == python3 run_report.py
```

## Why "governed"

Every claim that reaches this graph can be traced back through:
1. **What produced it** — a `Trace` with a `worker_id`, a `confidence`, and a `reason_code`, not just a result.
2. **What gate it passed** — `WorkflowGate` records six checks per decision (schema validity, provenance, confidence threshold, human review, conflicts, downstream eligibility), and a decision that only passed because of a human waiver is reported as `ALLOWED_BY_WAIVER`, never silently merged with an earned `ALLOWED`.
3. **Who overrode what, and why** — a waiver without a reviewer, a reason, or an approved status is rejected at the gate, not just at the UI.

That's the artifact worth showing: not the extraction quality, but that the
system can always answer *why* something got through — and the four pieces
above (inspection, queries, evals, and now a UI and live ingestion) all exist
to make that answerable by someone who will never read the Python.
