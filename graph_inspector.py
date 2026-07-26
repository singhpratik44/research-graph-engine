#!/usr/bin/env python3
"""
Phase 5: Inspection surface (human-facing, read-only)

A direct human view over the graph -- papers, claims, conflicts, extraction jobs,
held/review-required jobs, and *why* a gate blocked each one -- without reading raw
JSON. This is the prerequisite the roadmap calls for before agent query behavior:
you need to be able to eyeball correctness, blocked states, and missing links
before anything asks or answers questions on top of the graph.

Runs the real gate (WorkflowGate.should_unlock_next_stage) rather than replaying a
stored gate_reason string, so "why blocked" reflects the graph's current state --
including waivers applied after the job was first held -- not a spawn-time snapshot.

This module never mutates a graph; it only reports on one.
"""

from typing import List, Optional

from research_graph_schema import Node, ResearchGraph, NodeType, JobStatus, ReviewStatus
import research_graph_gates as gates


def _to_gate_node(n: Node) -> gates.Node:
    """schema Node -> gate Node adapter. Same field names; the gate is trace-agnostic."""
    p = n.provenance
    return gates.Node(
        id=n.id,
        type=n.type,
        label=n.label,
        provenance=None if p is None else gates.Provenance(
            source_paper=p.source_paper,
            extraction_method=p.extraction_method,
            confidence=p.confidence,
            extracted_at=p.extracted_at,
            human_reviewed=p.human_reviewed,
            review_notes=p.review_notes,
        ),
        properties=n.properties,
    )


def _section(title: str, rows: List[str]) -> List[str]:
    header = f"{title} ({len(rows)})"
    out = [header, "-" * len(header)]
    out.extend(f"  {r}" for r in rows) if rows else out.append("  (none)")
    return out


def render_report(graph: ResearchGraph, gate: Optional[gates.WorkflowGate] = None) -> str:
    """Render the full inspection report for `graph` as plain text."""
    gate = gate or gates.WorkflowGate()

    papers = [n for n in graph.nodes if n.type == NodeType.PAPER.value]
    claims = [n for n in graph.nodes if n.type == NodeType.CLAIM.value]
    jobs = [n for n in graph.nodes if n.type == NodeType.EXTRACTION_JOB.value]
    review_tasks = [n for n in graph.nodes if n.type == NodeType.REVIEW_TASK.value]

    held_statuses = {JobStatus.HELD.value, JobStatus.QUEUED.value, JobStatus.RUNNING.value}
    held_jobs = [n for n in jobs if n.properties.get("status") in held_statuses]
    pending_reviews = [r for r in review_tasks
                        if r.properties.get("status") == ReviewStatus.PENDING.value]

    lines: List[str] = [
        f"RESEARCH GRAPH REPORT (schema {graph.schema_version})",
        f"{len(graph.nodes)} nodes, {len(graph.edges)} edges, {len(graph.conflicts)} conflicts",
    ]

    lines.append("")
    lines += _section("PAPERS", [
        f"{p.id}: {p.properties.get('title', p.label)}  ({p.properties.get('url', 'no url')})"
        for p in papers
    ])

    lines.append("")
    lines += _section("CLAIMS", [
        f"{c.id}: {c.properties.get('subject', '?')} {c.properties.get('relation', '?')} "
        f"{c.properties.get('object', '?')}  "
        f"(confidence={c.provenance.confidence if c.provenance else '?'}, "
        f"reviewed={c.provenance.human_reviewed if c.provenance else '?'})"
        for c in claims
    ])

    lines.append("")
    lines += _section("CONFLICTS", [
        f"{'[RESOLVED]' if c.resolved else '[UNRESOLVED]'} "
        f"{c.source_claim_id} <-> {c.target_claim_id}  "
        f"type={c.conflict_type.value if hasattr(c.conflict_type, 'value') else c.conflict_type} "
        f"severity={c.severity:.2f} -- {c.evidence}"
        for c in graph.conflicts
    ])

    lines.append("")
    lines += _section("EXTRACTION JOBS", [
        f"{j.id}: type={j.properties.get('extraction_type', '?')} "
        f"status={j.properties.get('status', '?')} "
        f"avg_confidence={j.properties.get('avg_confidence', '?')} "
        f"results={j.properties.get('result_count', '?')}"
        for j in jobs
    ])

    lines.append("")
    lines += _section("HELD / REVIEW-REQUIRED", [
        f"job {j.id} status={j.properties.get('status')}" for j in held_jobs
    ] + [
        f"review {r.id} pending on {r.properties.get('extraction_job_id')}: "
        f"{r.properties.get('gate_reason', '')}"
        for r in pending_reviews
    ])

    blocked: List[str] = []
    for j in jobs:
        decision = gate.should_unlock_next_stage(_to_gate_node(j), graph)
        if not decision.can_proceed:
            failed = next((c for c in decision.checks if not c.passed), None)
            failed_note = f"  (failed check: {failed.check_name})" if failed else ""
            blocked.append(f"{j.id}: [{decision.reason_code.value}] {decision.reason}{failed_note}")
    lines.append("")
    lines += _section("WHY A GATE BLOCKED PROGRESSION", blocked)

    return "\n".join(lines)


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        import json
        with open(sys.argv[1]) as f:
            g = ResearchGraph.from_dict(json.load(f))
    else:
        import golden_fixtures as gf
        import literature_corpus as corpus

        fixture_graph = gf.build_fixture_graph()
        corpus_graph = corpus.build_corpus_graph()
        g = ResearchGraph(
            nodes=fixture_graph.nodes + corpus_graph.nodes,
            edges=fixture_graph.edges + corpus_graph.edges,
            conflicts=fixture_graph.conflicts + corpus_graph.conflicts,
        )

    print(render_report(g))
