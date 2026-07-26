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

from typing import Any, Dict, List, Optional, Set
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


# ============================================================================
# ATOMIC CLAIM-ENTAILMENT DECOMPOSITION
#
# word_overlap_score() above flattens a claim's whole text+subject+object into
# ONE bag of words before scoring -- a claim with several sub-assertions
# joined by "and" can have a single well-supported clause carry the whole
# claim's score past threshold while a completely unsupported clause rides
# along unnoticed. The functions below score each clause independently and
# require the WEAKEST one to clear the bar, so one unsupported atom in an
# otherwise-plausible run-on sentence can't hide behind the others.
#
# Purely additive: word_overlap_score/keyword_overlap_entailment_checker above
# are completely unmodified. research_graph_gates.py is untouched too -- the
# CLAIM_NOT_ENTAILED-before-LOW_CONFIDENCE short-circuit ordering is a
# property of WorkflowGate.should_unlock_next_stage's fixed check sequence,
# independent of which bool-returning checker is configured, so no gate
# change is needed for atomic_entailment_checker to plug in the same way
# keyword_overlap_entailment_checker does. Per-atom detail is exposed only
# via the separate atomic_entailment_report() diagnostic below, not wired
# into the gate's CheckTrace.evidence -- CheckTrace is one-per-check with a
# fixed evidence shape every existing test relies on; richer detail belongs
# in a function a caller (evals, a review UI) can call directly instead.
# ============================================================================

_ATOM_SPLIT_RE = re.compile(r"\s*;\s*|,?\s+(?:and|but|or)\s+", re.IGNORECASE)


def _split_atoms(text: str) -> List[str]:
    """
    Deliberately dumb clause splitter -- same dumbness level as
    ReferenceWorker's regex-based extraction in research_graph_workers.py.
    Splits only on semicolons and coordinating conjunctions (and/but/or);
    no real parsing, no clause-boundary detection beyond that.
    """
    if not text:
        return []
    return [p.strip() for p in _ATOM_SPLIT_RE.split(text) if p and p.strip()]


def _claim_atoms(node: Any) -> List[str]:
    """
    A claim's atomic pieces: its text split into clauses, plus its subject
    and object each as their own atom -- the same three properties
    _claim_tokens() already flattens into one bag, just kept separate here.
    """
    props = getattr(node, "properties", None) or {}
    atoms = _split_atoms(props.get("text", ""))
    for extra in (props.get("subject", ""), props.get("object", "")):
        if extra:
            atoms.append(extra)
    return atoms


def _atom_scores(node: Any, graph: Any = None) -> List[float]:
    """Per-atom word-overlap score against the cited paper's tokens -- reuses
    the same _tokenize/_find_paper/_paper_tokens/_source_paper_id helpers
    word_overlap_score() uses, just applied once per atom instead of once
    over the whole claim."""
    paper = _find_paper(graph, _source_paper_id(node))
    paper_words = _paper_tokens(paper)
    scores = []
    for atom in _claim_atoms(node):
        atom_words = _tokenize(atom)
        if not atom_words or not paper_words:
            scores.append(0.0)
        else:
            scores.append(len(atom_words & paper_words) / len(atom_words))
    return scores


def atomic_entailment_checker(node: Any, graph: Any = None, threshold: float = 0.15,
                              atom_threshold: Optional[float] = None) -> bool:
    """
    Same Callable[[Node, Graph], bool] signature as
    keyword_overlap_entailment_checker -- drop-in for
    WorkflowGate(entailment_checker=...). Aggregation is the MINIMUM atom
    score against `atom_threshold` (defaulting to `threshold` when not given
    explicitly) -- stricter than keyword_overlap_entailment_checker's
    single-bag average, so a single unsupported clause in an otherwise
    plausible sentence can't hide behind the rest. A claim with no atoms at
    all (empty text, no subject/object) is unsupported, not vacuously true.
    """
    bar = threshold if atom_threshold is None else atom_threshold
    scores = _atom_scores(node, graph)
    return bool(scores) and min(scores) >= bar


def atomic_entailment_report(node: Any, graph: Any = None, threshold: float = 0.15,
                             atom_threshold: Optional[float] = None) -> Dict[str, Any]:
    """
    Pure diagnostic -- NOT wired into WorkflowGate. Callers who want to know
    WHICH specific part of a claim failed to match its cited source (evals,
    a future review UI) call this directly; the gate itself only ever sees
    atomic_entailment_checker's single bool via _check_claim_entailed.
    """
    bar = threshold if atom_threshold is None else atom_threshold
    atoms = _claim_atoms(node)
    scores = _atom_scores(node, graph)
    weakest_index = scores.index(min(scores)) if scores else None
    return {
        "atoms": atoms,
        "scores": scores,
        "atom_threshold": bar,
        "weakest_atom": atoms[weakest_index] if weakest_index is not None else None,
        "weakest_score": min(scores) if scores else None,
        "entailed": bool(scores) and min(scores) >= bar,
    }
