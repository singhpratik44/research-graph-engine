#!/usr/bin/env python3
"""
Phase 9: Web UI (human-facing, read-only)

Makes the engine legible to someone who will never read the Python files.
Deliberately positioned as a *governed workflow engine* demo, not a
research-only tool: the schema/gate/query/roadmap/eval pattern underneath
this UI is domain-agnostic (papers-and-claims here; requirements-and-
decisions, tickets-and-approvals, or anything else with the same
extract -> gate -> review shape elsewhere). The research literature corpus
is this repo's one worked example, not the ceiling of what the engine does.

Every route is a thin wrapper over graph_queries.py / graph_roadmap.py /
graph_evals.py -- no query logic lives here twice. This module renders;
it never mutates the graph, matching the read-only contract those modules
already established.

Run: uvicorn webapp:app --reload
"""

import html
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse, JSONResponse

import golden_fixtures as gf
import graph_evals as evals
import graph_queries as q
import graph_roadmap as roadmap
import research_graph_gates as gates
import literature_corpus as corpus
from research_graph_schema import NodeType, ReviewStatus, JobStatus, ResearchGraph

app = FastAPI(title="Governed Workflow Engine")

GATE = gates.WorkflowGate()


def load_demo_graph() -> ResearchGraph:
    """
    The one worked example this engine ships with: golden fixtures (the four
    canonical gate states) plus the literature survey corpus. Swap this for
    ResearchGraph.from_dict(json.load(...)) to point the UI at any other
    governed graph -- nothing else in this module is research-specific.
    """
    fixtures = gf.build_fixture_graph()
    lit = corpus.build_corpus_graph()
    return ResearchGraph(
        nodes=fixtures.nodes + lit.nodes,
        edges=fixtures.edges + lit.edges,
        conflicts=fixtures.conflicts + lit.conflicts,
    )


GRAPH = load_demo_graph()


# ============================================================================
# HTML shell
# ============================================================================

_NAV = [
    ("/", "Overview"),
    ("/blocked", "Blocked Jobs"),
    ("/conflicts", "Conflicts"),
    ("/papers", "Papers"),
    ("/review-queue", "Review Queue"),
    ("/query", "Query"),
]

_STYLE = """
<style>
  :root { color-scheme: light dark; }
  body { font-family: ui-monospace, "SF Mono", Menlo, Consolas, monospace;
         max-width: 960px; margin: 2rem auto; padding: 0 1rem; line-height: 1.5; }
  nav { margin-bottom: 1.5rem; border-bottom: 1px solid #8888; padding-bottom: .75rem; }
  nav a { margin-right: 1.25rem; text-decoration: none; }
  nav a:hover { text-decoration: underline; }
  h1 { font-size: 1.3rem; }
  h2 { font-size: 1.05rem; margin-top: 2rem; }
  table { border-collapse: collapse; width: 100%; margin: .75rem 0 1.5rem; }
  th, td { text-align: left; padding: .35rem .6rem; border-bottom: 1px solid #8884; vertical-align: top; }
  th { font-weight: 600; }
  code, .mono { font-family: inherit; }
  .tag { display: inline-block; padding: .05rem .4rem; border-radius: .3rem;
         border: 1px solid #8888; font-size: .85em; }
  .bad { color: #c0392b; } .good { color: #27ae60; }
  form.query { display: flex; gap: .5rem; margin-bottom: 1rem; }
  input[type=text] { flex: 1; font-family: inherit; padding: .4rem .5rem; }
  button { font-family: inherit; padding: .4rem .8rem; }
  .subtitle { opacity: .75; font-size: .9em; margin-top: -.5rem; }
  .empty { opacity: .6; font-style: italic; }
</style>
"""


def _page(title: str, body: str) -> HTMLResponse:
    nav = " ".join(f'<a href="{href}">{label}</a>' for href, label in _NAV)
    return HTMLResponse(
        f"<!doctype html><html><head><meta charset='utf-8'>"
        f"<title>{html.escape(title)} — Governed Workflow Engine</title>{_STYLE}</head>"
        f"<body><nav>{nav}</nav><h1>{html.escape(title)}</h1>{body}</body></html>"
    )


def _table(headers: List[str], rows: List[List[str]], empty_message: str = "(none)") -> str:
    if not rows:
        return f'<p class="empty">{html.escape(empty_message)}</p>'
    head = "".join(f"<th>{html.escape(h)}</th>" for h in headers)
    body = "".join(
        "<tr>" + "".join(f"<td>{cell}</td>" for cell in row) + "</tr>"
        for row in rows
    )
    return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"


def _paper_link(paper_id: str) -> str:
    safe = html.escape(paper_id)
    return f'<a href="/papers/{safe}">{safe}</a>'


# ============================================================================
# Pages
# ============================================================================

@app.get("/", response_class=HTMLResponse)
def overview():
    summary = q.status_summary(GRAPH)
    eval_report = evals.run_all()

    node_rows = [[html.escape(t), str(n)] for t, n in sorted(summary["nodes_by_type"].items())]
    job_rows = [[html.escape(s), str(n)] for s, n in sorted(summary["job_status"].items())]
    review_rows = [[html.escape(s), str(n)] for s, n in sorted(summary["review_status"].items())]

    body = f"""
    <p class="subtitle">Demo domain: research literature (papers &rarr; claims &rarr; gates).
    The schema/gate/query/roadmap/eval pattern underneath is domain-agnostic.</p>

    <h2>Nodes by type</h2>
    {_table(["type", "count"], node_rows)}

    <h2>Extraction job status</h2>
    {_table(["status", "count"], job_rows)}

    <h2>Review task status</h2>
    {_table(["status", "count"], review_rows)}

    <h2>At a glance</h2>
    {_table(["metric", "value"], [
        ["unresolved conflicts", str(summary["unresolved_conflicts"])],
        ["eval suite", f"{eval_report.passed}/{eval_report.total} passed"],
    ])}
    """
    return _page("Overview", body)


@app.get("/blocked", response_class=HTMLResponse)
def blocked_jobs_page():
    decisions = q.blocked_jobs(GRAPH, GATE)
    rows = []
    for d in decisions:
        failed = next((c for c in d.checks if not c.passed), None)
        rows.append([
            html.escape(d.node_id),
            f'<span class="tag bad">{html.escape(d.reason_code.value)}</span>',
            html.escape(d.reason),
            html.escape(failed.check_name if failed else ""),
        ])
    body = _table(["job", "reason code", "reason", "failed check"], rows,
                   empty_message="Nothing is currently blocked.")
    return _page("Blocked Jobs", body)


@app.get("/conflicts", response_class=HTMLResponse)
def conflicts_page():
    conflicts = q.unresolved_conflicts(GRAPH)
    rows = [
        [
            html.escape(c.source_claim_id),
            html.escape(c.target_claim_id),
            html.escape(c.conflict_type.value if hasattr(c.conflict_type, "value") else str(c.conflict_type)),
            f"{c.severity:.2f}",
            html.escape(c.evidence),
        ]
        for c in conflicts
    ]
    body = _table(["claim A", "claim B", "type", "severity", "evidence"], rows,
                   empty_message="No unresolved conflicts.")
    return _page("Unresolved Conflicts", body)


@app.get("/papers", response_class=HTMLResponse)
def papers_page():
    papers = [n for n in GRAPH.nodes if n.type == NodeType.PAPER.value]
    rows = [
        [_paper_link(p.id), html.escape(p.properties.get("title", p.label)),
         html.escape(p.properties.get("published", ""))]
        for p in sorted(papers, key=lambda p: p.properties.get("published", ""), reverse=True)
    ]
    body = _table(["id", "title", "published"], rows)
    return _page("Papers", body)


@app.get("/papers/{paper_id}", response_class=HTMLResponse)
def paper_drilldown(paper_id: str):
    paper = q.get_node(GRAPH, paper_id)
    if paper is None or paper.type != NodeType.PAPER.value:
        return _page("Not Found", f'<p class="empty">No paper with id {html.escape(paper_id)!r}.</p>')

    claims = q.claims_for_paper(GRAPH, paper_id)
    claim_rows = []
    for c in claims:
        gaps = q.neighbors(GRAPH, c.id, direction="out")
        gap_texts = [g.label for g in gaps if g.type == NodeType.GAP.value]
        claim_rows.append([
            html.escape(c.id),
            html.escape(c.properties.get("text", c.label)),
            f"{c.provenance.confidence:.2f}" if c.provenance and c.provenance.confidence is not None else "?",
            "yes" if c.provenance and c.provenance.human_reviewed else "no",
            html.escape("; ".join(gap_texts)),
        ])

    body = f"""
    <p><strong>{html.escape(paper.properties.get('title', paper.label))}</strong><br>
    <a href="{html.escape(paper.properties.get('url', '#'))}">{html.escape(paper.properties.get('url', ''))}</a></p>
    <h2>Claims produced</h2>
    {_table(["claim id", "text", "confidence", "reviewed", "addresses gap"], claim_rows,
             empty_message="This paper has produced no claims yet.")}
    """
    return _page(f"Paper: {paper_id}", body)


@app.get("/review-queue", response_class=HTMLResponse)
def review_queue_page():
    tasks = [n for n in GRAPH.nodes if n.type == NodeType.REVIEW_TASK.value
             and n.properties.get("status") == ReviewStatus.PENDING.value]
    rows = [
        [html.escape(t.id), html.escape(t.properties.get("extraction_job_id", "")),
         html.escape(t.properties.get("gate_reason", "")), html.escape(t.properties.get("created_at", ""))]
        for t in tasks
    ]
    body = f"""
    <p class="subtitle">Read-only view. Approving or waiving a review still goes through
    WorkerSpawner/WorkflowGate directly, so every gate decision stays traced and auditable.</p>
    {_table(["review task", "extraction job", "gate reason", "created at"], rows,
             empty_message="Nothing is waiting on human review.")}
    """
    return _page("Review Queue", body)


# ============================================================================
# Query box
# ============================================================================

_QUERY_HELP = """
search &lt;text&gt;                          -- nodes whose label/text/subject/relation/object contain text
claims_for &lt;paper_id&gt;                    -- claims a paper produced
contradicting &lt;claim_id&gt;                 -- claims that conflict with this one
why_blocked &lt;node_id&gt;                    -- live gate decision for this node
neighbors &lt;node_id&gt; [edge_type] [in|out|both]  -- one-hop traversal
status                                   -- node/job/review counts
""".strip()


def _node_summary(n) -> Dict[str, Any]:
    return {"id": n.id, "type": n.type, "label": n.label,
            "confidence": n.provenance.confidence if n.provenance else None}


def execute_query(graph: ResearchGraph, raw: str) -> List[Dict[str, Any]]:
    """Dispatches a query-box string to the real graph_queries functions. Raises ValueError on bad input."""
    parts = raw.strip().split()
    if not parts:
        raise ValueError("empty query")
    verb, args = parts[0].lower(), parts[1:]

    if verb == "search":
        if not args:
            raise ValueError("search requires text, e.g. 'search adversarial'")
        return [_node_summary(n) for n in q.search(graph, " ".join(args))]

    if verb == "claims_for":
        if not args:
            raise ValueError("claims_for requires a paper id")
        return [_node_summary(n) for n in q.claims_for_paper(graph, args[0])]

    if verb == "contradicting":
        if not args:
            raise ValueError("contradicting requires a claim id")
        return [_node_summary(n) for n in q.contradicting_claims(graph, args[0])]

    if verb == "why_blocked":
        if not args:
            raise ValueError("why_blocked requires a node id")
        d = q.why_blocked(graph, args[0], GATE)
        return [{"node_id": d.node_id, "can_proceed": d.can_proceed,
                 "reason_code": d.reason_code.value, "reason": d.reason}]

    if verb == "neighbors":
        if not args:
            raise ValueError("neighbors requires a node id")
        node_id = args[0]
        edge_type = args[1] if len(args) > 1 else None
        direction = args[2] if len(args) > 2 else "out"
        return [_node_summary(n) for n in q.neighbors(graph, node_id, edge_type, direction)]

    if verb == "status":
        return [q.status_summary(graph)]

    raise ValueError(f"unknown query verb {verb!r}. Try: search, claims_for, "
                      f"contradicting, why_blocked, neighbors, status")


@app.get("/query", response_class=HTMLResponse)
def query_page(q_str: Optional[str] = Query(default=None, alias="q")):
    result_html = ""
    if q_str:
        try:
            rows = execute_query(GRAPH, q_str)
            if rows and isinstance(rows[0], dict):
                headers = list(rows[0].keys())
                table_rows = [[html.escape(str(row.get(h, ""))) for h in headers] for row in rows]
                result_html = f"<h2>Results</h2>{_table(headers, table_rows)}"
            else:
                result_html = "<h2>Results</h2><p class='empty'>No matches.</p>"
        except ValueError as exc:
            result_html = f'<p class="bad">Error: {html.escape(str(exc))}</p>'

    body = f"""
    <form class="query" method="get" action="/query">
      <input type="text" name="q" placeholder="e.g. search adversarial" value="{html.escape(q_str or '')}">
      <button type="submit">Run</button>
    </form>
    <details {"open" if not q_str else ""}><summary>Supported queries</summary><pre>{_QUERY_HELP}</pre></details>
    {result_html}
    """
    return _page("Query", body)


@app.get("/api/query", response_class=JSONResponse)
def query_api(q_str: str = Query(alias="q")):
    try:
        return {"ok": True, "results": execute_query(GRAPH, q_str)}
    except ValueError as exc:
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=400)
