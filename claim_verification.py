#!/usr/bin/env python3
"""
Claim-source verification: a pluggable entailment check for WorkflowGate.

`research_graph_gates.WorkflowGate._check_provenance_present` only checks that
a claim declares a non-empty `source_paper` -- it says nothing about whether
the claim's *text* is actually supported by that source. That gap is exactly
what qih_stress_corpus.py's fact-check surfaced for real:
`claim_light_angle_derives_gr` cites two real, correctly-formatted sources,
and neither one, on inspection, addresses the specific mechanism the claim
asserts. Today's gate can't catch that on its own -- the claim is only held
in that corpus because a human set its confidence to 0.08 by hand after
independent research. `WorkflowGate._check_claim_entailed` (with an
`entailment_checker` configured) is the check that closes this gap at the
gate itself, not just in a human's notes.

`keyword_overlap_entailment_checker` below is the real, deterministic default
implementation for that seam, in the same spirit as `ReferenceWorker` in
research_graph_workers.py: deliberately dumb, proves the contract, doesn't
need a model. It scores a claim's text/subject/object against its cited
paper's available text (title, plus `text`/`summary`/`abstract` properties
when present) by word overlap, and thresholds it.

Be honest about what this is and is not:
  - It IS a real, working seam: WorkflowGate(entailment_checker=...) will
    actually hold a claim on CLAIM_NOT_ENTAILED when the checker says no, and
    it demonstrably catches the light-angle case this module was written for
    (see test_claim_verification.py).
  - It is NOT entailment detection. Word overlap is a crude proxy: a claim
    can share every word with its source and still misrepresent it (e.g.
    negate a finding), or use different vocabulary and still be a faithful
    paraphrase. A real implementation of this seam is an NLP/LLM-based
    entailment model; this heuristic exists so that seam has a working
    default and a concrete test of the contract, not so this scoring method
    should be trusted as ground truth.
"""

from typing import Any, Optional, Set
import re

# Small, deliberately generic function-word list -- enough to keep the overlap
# score from being dominated by "the/of/and", not a real NLP stopword corpus.
_STOPWORDS: Set[str] = {
    "the", "a", "an", "of", "to", "in", "and", "or", "that", "this", "these",
    "those", "on", "for", "with", "as", "by", "from", "at", "be", "is", "are",
    "was", "were", "can", "could", "will", "would", "its", "it", "not", "no",
    "than", "then", "into", "onto", "over", "under", "such", "any", "all",
    "which", "who", "whom", "their", "there", "here", "has", "have", "had",
    "but", "if", "so", "do", "does", "did", "up", "out", "about", "per",
}


def _tokenize(text: str) -> Set[str]:
    """Lowercase word tokens, function words and 1-2 letter tokens dropped."""
    if not text:
        return set()
    words = re.findall(r"[a-zA-Z0-9]+", text.lower())
    return {w for w in words if len(w) > 2 and w not in _STOPWORDS}


def _claim_tokens(node: Any) -> Set[str]:
    """Content words from a claim node's text/subject/object properties."""
    props = getattr(node, "properties", None) or {}
    parts = [props.get("text", ""), props.get("subject", ""), props.get("object", "")]
    return _tokenize(" ".join(p for p in parts if p))


def _source_paper_id(node: Any) -> Optional[str]:
    prov = getattr(node, "provenance", None)
    return getattr(prov, "source_paper", None) if prov is not None else None


def _find_paper(graph: Any, paper_id: Optional[str]) -> Optional[Any]:
    """Look up the cited paper node by id in `graph.nodes` (duck-typed)."""
    if graph is None or not paper_id:
        return None
    for n in getattr(graph, "nodes", None) or []:
        if getattr(n, "id", None) == paper_id:
            return n
    return None


def _paper_tokens(paper_node: Any) -> Set[str]:
    """Content words from whatever text a paper node actually carries -- most
    paper nodes in this repo only have a `title`; some may also carry `text`,
    `summary`, or `abstract` properties. Whatever's missing contributes nothing,
    it doesn't error."""
    if paper_node is None:
        return set()
    props = getattr(paper_node, "properties", None) or {}
    parts = [props.get("title", ""), props.get("text", ""),
             props.get("summary", ""), props.get("abstract", "")]
    return _tokenize(" ".join(p for p in parts if p))


def word_overlap_score(node: Any, graph: Any = None) -> float:
    """
    Fraction of the claim's content words (from text/subject/object) that also
    appear in its cited source's available text (title, and text/summary/
    abstract when present).

    Returns 0.0 -- "unsupported" -- when:
      - the claim has no content words at all,
      - `graph` is None or doesn't contain the cited `source_paper` id, or
      - the cited paper node has no usable text (e.g. title-only metadata that
        shares no vocabulary with the claim).
    An unverifiable claim scores as unsupported rather than passing by default;
    silently treating "can't check" as "fine" would defeat the point of this
    check.
    """
    claim_words = _claim_tokens(node)
    if not claim_words:
        return 0.0
    paper = _find_paper(graph, _source_paper_id(node))
    paper_words = _paper_tokens(paper)
    if not paper_words:
        return 0.0
    overlap = claim_words & paper_words
    return len(overlap) / len(claim_words)


def keyword_overlap_entailment_checker(node: Any, graph: Any = None, threshold: float = 0.15) -> bool:
    """
    Deterministic entailment proxy, usable directly as
    `WorkflowGate(entailment_checker=keyword_overlap_entailment_checker)`.

    NOT real entailment detection -- see the module docstring. This is a
    tripwire for claims that share essentially no vocabulary with what their
    citation actually says, not a certificate that anything clearing the
    threshold is genuinely supported. `threshold` defaults to 0.15 (calibrated
    against the light-angle case this module exists to catch, which scores
    well under that); pass a different value via `functools.partial` or a
    small wrapper lambda if a deployment needs a stricter or looser bar.
    """
    return word_overlap_score(node, graph) >= threshold
