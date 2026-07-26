#!/usr/bin/env python3
"""
Phase 8: Evaluation subsystem (quality, not just correctness)

Unit tests answer "does the code behave as written." This answers a different
question: "how good are the graph's answers, right now, against a corpus of
known expectations" -- a number that can regress even while every unit test
still passes (e.g. an extraction worker quietly gets shyer about what it emits).

Four eval categories, each a plain dataclass with nothing framework-shaped
about it, so a new case is one more line in a registry:

  QUERY_EVALS         -- a graph_queries function returns the expected answer
  GATE_AUDIT_CASES    -- WorkflowGate's can_proceed/reason_code matches the
                         expected verdict for a known graph state ("blocked/
                         unblocked decision audits")
  EXTRACTION_CHECKS   -- ReferenceWorker's output vs a hand-labeled ground
                         truth, scored as precision/recall
  REGRESSION_CASES    -- specific defect scenarios that must never silently
                         start passing the gate again; seeded from
                         golden_fixtures.waived_graph_with_defect(), the one
                         place this repo already encodes "this used to be
                         a bug, keep proving it's fixed."

run_all() executes every case and returns an EvalReport; render_report()
turns that into the same kind of plain-text summary graph_inspector.py gives
for graph state, but for eval quality instead.
"""

from dataclasses import dataclass, field
from typing import Any, Callable, List, Optional, Set, Tuple

import golden_fixtures as gf
import literature_corpus as corpus
import graph_queries as q
import graph_roadmap as roadmap
import research_graph_gates as gates
from research_graph_schema import ExtractionType, NodeType, ResearchGraph
from research_graph_workers import ReferenceWorker, WorkerSpawner


@dataclass
class EvalResult:
    name: str
    category: str
    passed: bool
    detail: str = ""
    score: Optional[float] = None  # precision/recall-style cases set this; pass/fail cases leave it None


@dataclass
class EvalReport:
    results: List[EvalResult]

    @property
    def passed(self) -> int:
        return sum(1 for r in self.results if r.passed)

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def all_passed(self) -> bool:
        return self.passed == self.total

    def failures(self) -> List[EvalResult]:
        return [r for r in self.results if not r.passed]

    def by_category(self, category: str) -> List[EvalResult]:
        return [r for r in self.results if r.category == category]


# ============================================================================
# 1. Query-answer evals
# ============================================================================

@dataclass
class QueryEvalCase:
    name: str
    check: Callable[[], Tuple[bool, str]]


def _eval_claims_for_paper() -> Tuple[bool, str]:
    graph = gf.build_fixture_graph()
    found = {c.id for c in q.claims_for_paper(graph, "paper_2606.13707")}
    expected = {"claim_2606_001"}
    return found == expected, f"got {found}, expected {expected}"


def _eval_contradicting_claims() -> Tuple[bool, str]:
    graph = gf.build_fixture_graph()
    found = {c.id for c in q.contradicting_claims(graph, "claim_2606_001")}
    expected = {"claim_2701_014"}
    return found == expected, f"got {found}, expected {expected}"


def _eval_why_blocked_reason() -> Tuple[bool, str]:
    graph = gf.build_fixture_graph()
    decision = q.why_blocked(graph, "job_2606_concepts_001")
    ok = decision.reason_code == gates.GateReasonCode.LOW_CONFIDENCE
    return ok, f"reason_code={decision.reason_code}"


def _eval_search_finds_corpus_paper() -> Tuple[bool, str]:
    graph = corpus.build_corpus_graph()
    found = {n.id for n in q.search(graph, "adversarial")}
    ok = "paper_2605_03042" in found
    return ok, f"found={found}"


def _eval_roadmap_top_gap() -> Tuple[bool, str]:
    graph = corpus.build_corpus_graph()
    rows = roadmap.roadmap_summary(graph, NodeType.GAP)
    ok = bool(rows) and rows[0]["id"] == "gap_multidim_review"
    return ok, f"top={rows[0]['id'] if rows else None}"


QUERY_EVALS: List[QueryEvalCase] = [
    QueryEvalCase("claims_for_paper returns exactly the paper's claim", _eval_claims_for_paper),
    QueryEvalCase("contradicting_claims is the fixture conflict's other side", _eval_contradicting_claims),
    QueryEvalCase("why_blocked reports LOW_CONFIDENCE for the held job", _eval_why_blocked_reason),
    QueryEvalCase("search finds ARIS via 'adversarial'", _eval_search_finds_corpus_paper),
    QueryEvalCase("roadmap's best-attested gap is gap_multidim_review", _eval_roadmap_top_gap),
]


def run_query_evals() -> List[EvalResult]:
    results = []
    for case in QUERY_EVALS:
        try:
            ok, detail = case.check()
        except Exception as exc:  # an eval case erroring out is a failure, not a crash
            ok, detail = False, f"raised {exc!r}"
        results.append(EvalResult(case.name, "query", ok, detail))
    return results


# ============================================================================
# 2. Gate-decision audits ("blocked/unblocked decision audits")
# ============================================================================

@dataclass
class GateAuditCase:
    name: str
    graph: ResearchGraph
    node_id: str
    expected_can_proceed: bool
    expected_reason_code: gates.GateReasonCode
    # True for cases that exist specifically because a defective waiver once had
    # to be rejected on purpose -- these double as the regression set below.
    is_regression: bool = False


def _gate_audit_cases() -> List[GateAuditCase]:
    # Built lazily (not at import time) so each case gets its own fresh fixture graph.
    return [
        GateAuditCase("auto-pass job proceeds", gf.build_fixture_graph(),
                       "job_2606_claims_001", True, gates.GateReasonCode.ALLOWED),
        GateAuditCase("low-confidence job is held", gf.build_fixture_graph(),
                       "job_2606_concepts_001", False, gates.GateReasonCode.LOW_CONFIDENCE),
        GateAuditCase("waived job proceeds by waiver", gf.waived_graph(),
                       "job_2606_concepts_001", True, gates.GateReasonCode.ALLOWED_BY_WAIVER),
        GateAuditCase("waiver missing reason stays blocked", gf.waived_graph_with_defect("no_reason"),
                       "job_2606_concepts_001", False, gates.GateReasonCode.LOW_CONFIDENCE,
                       is_regression=True),
        GateAuditCase("waiver missing reviewer stays blocked", gf.waived_graph_with_defect("no_reviewer"),
                       "job_2606_concepts_001", False, gates.GateReasonCode.LOW_CONFIDENCE,
                       is_regression=True),
        GateAuditCase("unapproved waiver stays blocked", gf.waived_graph_with_defect("not_approved"),
                       "job_2606_concepts_001", False, gates.GateReasonCode.LOW_CONFIDENCE,
                       is_regression=True),
        GateAuditCase("unreviewed waiver stays blocked", gf.waived_graph_with_defect("unreviewed"),
                       "job_2606_concepts_001", False, gates.GateReasonCode.LOW_CONFIDENCE,
                       is_regression=True),
    ]


def _evaluate_gate_case(case: GateAuditCase) -> EvalResult:
    try:
        decision = q.why_blocked(case.graph, case.node_id)
        ok = (decision.can_proceed == case.expected_can_proceed
              and decision.reason_code == case.expected_reason_code)
        detail = f"can_proceed={decision.can_proceed} reason_code={decision.reason_code.value}"
    except Exception as exc:
        ok, detail = False, f"raised {exc!r}"
    return EvalResult(case.name, "gate_audit", ok, detail)


def run_gate_audits() -> List[EvalResult]:
    return [_evaluate_gate_case(c) for c in _gate_audit_cases()]


# ============================================================================
# 3. Extraction precision/recall spot checks
# ============================================================================

@dataclass
class ExtractionSpotCheck:
    name: str
    extraction_type: ExtractionType
    text: str
    expected_texts: Set[str]
    confidence_floor: float = 0.0
    max_results: Optional[int] = None


EXTRACTION_CHECKS: List[ExtractionSpotCheck] = [
    ExtractionSpotCheck(
        name="claims: two relation sentences extracted, one non-claim skipped",
        extraction_type=ExtractionType.CLAIMS,
        text="Hierarchical orchestration reduces coordination overhead. "
             "The weather was pleasant during the workshop. "
             "Caching improves throughput significantly.",
        expected_texts={
            "Hierarchical orchestration reduces coordination overhead",
            "Caching improves throughput significantly",
        },
    ),
    ExtractionSpotCheck(
        name="claims: no relation verbs yields nothing",
        extraction_type=ExtractionType.CLAIMS,
        text="This section introduces the dataset. It has no comparative claims.",
        expected_texts=set(),
    ),
]


def run_extraction_check(case: ExtractionSpotCheck) -> EvalResult:
    graph = ResearchGraph()
    spawner = WorkerSpawner(graph)
    _, directive = spawner.spawn("paper_eval_synthetic", case.extraction_type,
                                  confidence_floor=case.confidence_floor,
                                  max_results=case.max_results)
    worker = ReferenceWorker(worker_id="eval_reference_worker")
    env = worker.run(directive, case.text)

    produced = {n.properties.get("text", "") for n in env.nodes}
    true_positives = produced & case.expected_texts

    precision = len(true_positives) / len(produced) if produced else 1.0
    recall = len(true_positives) / len(case.expected_texts) if case.expected_texts else 1.0
    # The reference worker is deterministic; anything short of an exact match is a real miss.
    ok = precision == 1.0 and recall == 1.0
    detail = f"precision={precision:.2f} recall={recall:.2f} produced={sorted(produced)}"
    return EvalResult(case.name, "extraction", ok, detail, score=min(precision, recall))


def run_extraction_checks() -> List[EvalResult]:
    return [run_extraction_check(c) for c in EXTRACTION_CHECKS]


# ============================================================================
# 4. Regression cases
# ============================================================================
# Each entry is a defect scenario a defective waiver must never be allowed to
# slip past again (see golden_fixtures.waived_graph_with_defect docstring).
# Sourced from the `is_regression` cases above -- one definition of "what a
# defective waiver must do," not two copies that can drift apart.

def run_regression_cases() -> List[EvalResult]:
    results = []
    for case in _gate_audit_cases():
        if not case.is_regression:
            continue
        r = _evaluate_gate_case(case)
        results.append(EvalResult(case.name, "regression", r.passed, r.detail))
    return results


# ============================================================================
# Runner
# ============================================================================

def run_all() -> EvalReport:
    results: List[EvalResult] = []
    results += run_query_evals()
    results += run_gate_audits()
    results += run_extraction_checks()
    results += run_regression_cases()
    return EvalReport(results)


def render_report(report: Optional[EvalReport] = None) -> str:
    report = report or run_all()
    lines = [f"EVAL REPORT: {report.passed}/{report.total} passed"]
    for category in ("query", "gate_audit", "extraction", "regression"):
        rows = report.by_category(category)
        if not rows:
            continue
        header = f"\n{category.upper()} ({sum(r.passed for r in rows)}/{len(rows)})"
        lines += [header, "-" * len(header.strip())]
        for r in rows:
            mark = "PASS" if r.passed else "FAIL"
            score = f"  score={r.score:.2f}" if r.score is not None else ""
            lines.append(f"  [{mark}] {r.name}{score}")
            if not r.passed:
                lines.append(f"         {r.detail}")
    return "\n".join(lines)


if __name__ == "__main__":
    print(render_report())
