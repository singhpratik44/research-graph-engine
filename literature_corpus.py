#!/usr/bin/env python3
"""
Literature corpus — 20 studies (Apr-Jul 2026, two survey rounds) surveyed to
decide what this repo should build next, entered as real graph data instead
of a memo.

Each paper PRODUCES one CLAIM capturing why it's relevant to this engine, and
that claim ADDRESSES one of the five capability GAPs the survey turned up:

  gap_typed_provenance_edges  — provenance is a flat record; no typed relations
                                 (derivation/contradiction/support) between nodes.
  gap_claim_source_verify     — the gate checks a source *exists*, not that the
                                 claim actually follows from it.
  gap_multidim_review         — ReviewStatus/confidence is scalar; no adversarial
                                 or multi-dimensional reviewer reconciliation.
  gap_roadmap_queries         — no read-side query that rolls GAP/METHOD nodes
                                 up into a contribution/roadmap view.
                                 (closed by graph_roadmap.py -- kept here so the
                                 corpus still explains its own history.)
  gap_adaptive_recovery       — WorkerSpawner.admit() fails a rejected envelope
                                 wholesale; there's no diagnose-and-retarget
                                 recovery loop the way an adaptive pipeline has.

Dogfoods the schema: every node here is built the same way research_graph_workers.py
would build one from a real extraction job, and the whole graph is expected to pass
ResearchGraph.validate() with zero errors (see test_literature_corpus.py).
"""

from research_graph_schema import (
    Node, Edge, Provenance, ResearchGraph,
    NodeType, EdgeType, ExtractionMethod,
)

TS = "2026-07-26T18:00:00+00:00"


def _human_prov(source_paper: str, notes: str) -> Provenance:
    return Provenance(
        source_paper=source_paper,
        extraction_method=ExtractionMethod.HUMAN_ANNOTATION.value,
        confidence=1.0,
        extracted_at=TS,
        human_reviewed=True,
        review_notes=notes,
    )


# ---------------------------------------------------------------------------
# The four capability gaps this survey was run to inform
# ---------------------------------------------------------------------------

GAPS = [
    ("gap_typed_provenance_edges",
     "Provenance/Trace is a flat record with no typed relation (derivation, "
     "support, contradiction, invalidation) between the nodes it connects."),
    ("gap_claim_source_verify",
     "The provenance gate checks that a source_paper reference exists, not "
     "that the claim's text is actually entailed by that source."),
    ("gap_multidim_review",
     "ReviewStatus and confidence are single scalars; there is no reconciliation "
     "of multiple independent or adversarial reviewer signals before a waiver."),
    ("gap_roadmap_queries",
     "There is no read-side query that aggregates GAP/METHOD/DOMAIN nodes into "
     "a rolled-up scientific-contribution or roadmap view."),
    ("gap_adaptive_recovery",
     "WorkerSpawner.admit() fails a rejected envelope wholesale; there is no "
     "diagnose-the-failure-and-retarget-extraction recovery loop."),
]


def build_gap_nodes():
    return [
        Node(
            id=gap_id,
            type=NodeType.GAP.value,
            label=text.split(".")[0],
            provenance=_human_prov("survey_2026_07", "Identified during Jul 2026 literature survey."),
            properties={"text": text},
        )
        for gap_id, text in GAPS
    ]


# ---------------------------------------------------------------------------
# 10 papers: (id, title, url, published, relevance claim, addressed gap)
# ---------------------------------------------------------------------------

PAPERS = [
    dict(
        id="paper_2606_04990",
        title="From Agent Traces to Trust: Evidence Tracing and Execution Provenance in LLM Agents",
        url="https://arxiv.org/abs/2606.04990",
        published="2026-06",
        claim="Provenance should be modeled as typed relations (support, derivation, "
              "dependency, contradiction, invalidation) between tasks, tools, documents, "
              "and claims, not a single flat record.",
        subject="typed provenance relations",
        relation="improve_on",
        object="flat Provenance/Trace records",
        gap="gap_typed_provenance_edges",
    ),
    dict(
        id="paper_2605_15011",
        title="The Scientific Contribution Graph: Automated Literature-based Technological Roadmapping at Scale",
        url="https://arxiv.org/abs/2605.15011",
        published="2026-05",
        claim="Aggregating GAP/METHOD-like nodes across a corpus into a roadmap graph "
              "surfaces technological trends that no single-paper extraction shows.",
        subject="literature-based roadmapping",
        relation="motivates",
        object="a roadmap rollup query over GAP/METHOD nodes",
        gap="gap_roadmap_queries",
    ),
    dict(
        id="paper_2606_19749",
        title="Benchmarking Agentic Review Systems",
        url="https://arxiv.org/abs/2606.19749",
        published="2026-06",
        claim="Automated review agents need a dedicated benchmark harness, since "
              "outcome-only evaluation hides intermediate reasoning failures.",
        subject="agentic review benchmarking",
        relation="stress_tests",
        object="WorkflowGate review-required behavior",
        gap="gap_multidim_review",
    ),
    dict(
        id="paper_2606_21005",
        title="Building Agent Harnesses for Scientific Curation from Multimodal Sources",
        url="https://arxiv.org/abs/2606.21005",
        published="2026-06",
        claim="A curation harness needs explicit orchestration and assurance layers "
              "as first-class components, not gate checks bolted onto a worker loop.",
        subject="curation harness assurance layers",
        relation="parallels",
        object="research_graph_gates.WorkflowGate design",
        gap="gap_multidim_review",
    ),
    dict(
        id="paper_2605_14790",
        title="Graphs of Research: Citation Evolution Graphs as Supervision for Research Idea Generation",
        url="https://arxiv.org/abs/2605.14790",
        published="2026-05",
        claim="Citation evolution over time is itself a useful edge type, distinct "
              "from a static one-shot BUILDS_ON/CITES link.",
        subject="citation evolution edges",
        relation="extends",
        object="static EdgeType.CITES/BUILDS_ON",
        gap="gap_typed_provenance_edges",
    ),
    dict(
        id="paper_2607_04043",
        title="Claim2Source at CheckThat! 2026: Improving Multilingual Scientific Claim-Source Retrieval with Verification-based Re-Ranking",
        url="https://arxiv.org/abs/2607.04043",
        published="2026-07",
        claim="A verification-based re-ranking step over candidate sources materially "
              "improves whether a retrieved source actually supports a claim.",
        subject="verification-based re-ranking",
        relation="strengthens",
        object="the _check_provenance_present gate",
        gap="gap_claim_source_verify",
    ),
    dict(
        id="paper_2605_26730",
        title="PRISM: A Multi-Dimensional Benchmark for Evaluating LLM Peer Reviewers",
        url="https://arxiv.org/abs/2605.26730",
        published="2026-05",
        claim="Reviewer quality is multi-dimensional (rigor, novelty assessment, "
              "actionability), so collapsing it to one confidence score loses signal.",
        subject="multi-dimensional reviewer scoring",
        relation="argues_against",
        object="a single scalar ReviewStatus/confidence field",
        gap="gap_multidim_review",
    ),
    dict(
        id="paper_2605_29815",
        title="PRAIB: Peer Review AI Benchmark of Behaviour of LLM-Assisted Reviewing",
        url="https://arxiv.org/abs/2605.29815",
        published="2026-05",
        claim="Reviewer agents should be evaluated on behavior (do they actually "
              "exercise waivers/escalation correctly), not just review-decision accuracy.",
        subject="reviewer behavior evaluation",
        relation="tests",
        object="human_reviewed / waiver gate paths",
        gap="gap_multidim_review",
    ),
    dict(
        id="paper_2606_13349",
        title="From Passive Generation to Investigation: A Proactive Scientific Peer Review Agent",
        url="https://arxiv.org/abs/2606.13349",
        published="2026-06",
        claim="A reviewer agent that actively investigates ambiguous evidence outperforms "
              "one that only accepts or rejects the extraction as given.",
        subject="proactive investigative review",
        relation="upgrades",
        object="the passive REVIEW_TASK/ReviewStatus.PENDING path",
        gap="gap_multidim_review",
    ),
    dict(
        id="paper_2605_03042",
        title="ARIS: Autonomous Research via Adversarial Multi-Agent Collaboration",
        url="https://arxiv.org/abs/2605.03042",
        published="2026-05",
        claim="Cross-model adversarial review (a different model family checking the "
              "executor) catches correlated errors that same-model self-review misses.",
        subject="cross-model adversarial review",
        relation="suggests",
        object="a new GateReasonCode.ADVERSARIAL_UNVERIFIED check",
        gap="gap_claim_source_verify",
    ),

    # -- Round 2 (Jul 2026 follow-up survey) --------------------------------
    dict(
        id="paper_2606_22342",
        title="How Does Research Evolve? Tracing Cross-Domain Trajectories in NLP, ML, and CV with Claim-Grounded Typed Citations",
        url="https://arxiv.org/pdf/2606.22342",
        published="2026-06",
        claim="Typed citation edges, gated by claim-entailment verification per relation "
              "type, trace research evolution more precisely than a single CITES/BUILDS_ON edge.",
        subject="claim-grounded typed citations",
        relation="reinforces",
        object="the case for new EdgeType values beyond CITES/BUILDS_ON",
        gap="gap_typed_provenance_edges",
    ),
    dict(
        id="paper_2604_06170",
        title="Paper Circle: An Open-source Multi-agent Research Discovery and Analysis Framework",
        url="https://arxiv.org/pdf/2604.06170",
        published="2026-04",
        claim="A dedicated Verification Layer that checks extracted graph facts against "
              "source text, separate from the Ingestion/Graph-Builder layers, is what "
              "gives full traceability.",
        subject="a dedicated verification layer",
        relation="parallels",
        object="the missing claim-to-source verification step in the gate",
        gap="gap_claim_source_verify",
    ),
    dict(
        id="paper_2606_15246",
        title="Provenance-Enhanced Statements in Knowledge Graphs",
        url="https://arxiv.org/html/2606.15246",
        published="2026-06",
        claim="Documented provenance is not enough on its own; automated verification "
              "that the documented source actually supports the asserted fact is required.",
        subject="automated provenance verification",
        relation="reinforces",
        object="the gap between source_paper existing and a claim being entailed by it",
        gap="gap_claim_source_verify",
    ),
    dict(
        id="paper_2606_11127",
        title="Provenance-Grounded Gating and Adaptive Recovery in Synthetic Post-Training Data Curation",
        url="https://arxiv.org/abs/2606.11127",
        published="2026-06",
        claim="An adaptive recovery pipeline -- diagnose why an item was rejected, then "
              "regenerate a targeted fix -- recovers far more usable data than a flat "
              "accept/reject gate.",
        subject="diagnose-and-regenerate adaptive recovery",
        relation="suggests",
        object="a recovery loop for WorkerSpawner.admit() rejections",
        gap="gap_adaptive_recovery",
    ),
    dict(
        id="paper_2605_27204",
        title="GraphReview: Scientific Paper Evaluation via LLM-Based Graph Message Passing",
        url="https://arxiv.org/pdf/2605.27204",
        published="2026-05",
        claim="Modeling reviewer reasoning as message passing over a graph of evidence "
              "produces a richer verdict than a single pass/fail review decision.",
        subject="graph message-passing review",
        relation="extends",
        object="the single-pass ReviewStatus decision on a review_task",
        gap="gap_multidim_review",
    ),
    dict(
        id="paper_2605_05476",
        title="A Unified Benchmark for Evaluating Knowledge Graph Construction Methods and Graph Neural Networks",
        url="https://arxiv.org/html/2605.05476v1",
        published="2026-05",
        claim="Benchmarking knowledge graph construction methods on whether they preserve "
              "typed relations, not just node/edge counts, is what actually differentiates them.",
        subject="typed-relation-aware KG construction benchmarking",
        relation="supports",
        object="typed EdgeType values as a measurable, not cosmetic, improvement",
        gap="gap_typed_provenance_edges",
    ),
    dict(
        id="paper_langchain_deep_agents_benchmark",
        title="How We Benchmark Deep Agents",
        url="https://www.langchain.com/blog/how-we-benchmark-deep-agents",
        published="2026-07",
        claim="Agent evaluation has shifted from small unit-style tests to end-to-end "
              "evals, because long-horizon agent tasks fail in ways unit tests don't catch.",
        subject="end-to-end agent evals",
        relation="argues_for",
        object="evaluating the whole extraction-to-review loop, not each gate check in isolation",
        gap="gap_multidim_review",
    ),
    dict(
        id="paper_2605_26079",
        title="Toward More Reliable Agent Evaluation: A Component-Based Benchmark Auditing Pipeline",
        url="https://arxiv.org/pdf/2605.26079",
        published="2026-05",
        claim="Auditing a benchmark's components (not just running agents against it) "
              "surfaces evaluation flaws that outcome-only scoring hides.",
        subject="component-based benchmark auditing",
        relation="strengthens",
        object="the case for reviewer/gate behavioral audits, not just pass-rate metrics",
        gap="gap_multidim_review",
    ),
    dict(
        id="paper_openreview_piml_automl2026",
        title="PiML: Automated Machine Learning Workflow Optimization using LLM Agents",
        url="https://openreview.net/forum?id=Nw1qBpsjZz",
        published="2026 (AutoML 2026 Methods Track)",
        claim="Iterative reasoning with systematic debugging on failure -- not a single "
              "generate-and-check pass -- is what let this agent beat a non-iterative baseline.",
        subject="iterative reasoning with systematic debugging",
        relation="suggests",
        object="a retry-with-diagnosis loop instead of WorkerSpawner's single admit-or-reject pass",
        gap="gap_adaptive_recovery",
    ),
    dict(
        id="paper_2604_24955",
        title="BenchGuard: Who Guards the Benchmarks? Automated Auditing of LLM Agent Benchmarks",
        url="https://arxiv.org/html/2604.24955v1",
        published="2026-04",
        claim="Benchmarks themselves need automated auditing for issues, since a flawed "
              "benchmark silently invalidates every agent evaluation run against it.",
        subject="automated benchmark integrity auditing",
        relation="reinforces",
        object="the need for behavioral, not just outcome, review auditing",
        gap="gap_multidim_review",
    ),
]


def build_paper_nodes_and_edges():
    nodes = []
    edges = []
    for p in PAPERS:
        paper = Node(
            id=p["id"],
            type=NodeType.PAPER.value,
            label=p["title"],
            provenance=_human_prov(p["id"], f"Surveyed {p['published']} for the Jul 2026 roadmap review."),
            properties={"title": p["title"], "url": p["url"], "published": p["published"]},
        )
        claim = Node(
            id=f"claim_{p['id']}_relevance",
            type=NodeType.CLAIM.value,
            label=p["claim"],
            provenance=_human_prov(p["id"], "Relevance takeaway for this repo, human-curated."),
            properties={
                "text": p["claim"],
                "subject": p["subject"],
                "relation": p["relation"],
                "object": p["object"],
            },
        )
        nodes.extend([paper, claim])
        edges.append(Edge(paper.id, claim.id, EdgeType.PRODUCES.value,
                           _human_prov(p["id"], "")))
        edges.append(Edge(claim.id, p["gap"], EdgeType.ADDRESSES.value,
                           _human_prov(p["id"], "")))
    return nodes, edges


def build_corpus_graph() -> ResearchGraph:
    gap_nodes = build_gap_nodes()
    paper_nodes, edges = build_paper_nodes_and_edges()
    return ResearchGraph(nodes=gap_nodes + paper_nodes, edges=edges)


if __name__ == "__main__":
    graph = build_corpus_graph()
    result = graph.validate()
    print(f"nodes={len(graph.nodes)} edges={len(graph.edges)} valid={result.valid}")
    for err in result.errors:
        print(f"  {err.field_path}: {err.code} {err.message}")
