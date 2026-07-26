#!/usr/bin/env python3
"""
Stress-test corpus: Jason Padgett's "Quantum Information Holography" (QIH)

A real-world adversarial test for the gate: a document that mixes genuinely
well-established, peer-reviewed physics (holography, black hole
thermodynamics) with self-published, uncited-in-fact speculation (light
angles deriving GR, consciousness from geometry), formatted with identical
confidence and citation styling throughout -- exactly the case where a naive
extraction pipeline would treat every claim as equally trustworthy because
they all *look* equally well-supported.

Confidence here is NOT the source document's self-assessment (its own
"Research Status" column is part of what's under test) -- it's this
session's independently fact-checked assessment, verified via live web
search against the actual cited arXiv IDs and the actual current state of
each research question:

  - Holography (Maldacena, Hawking) : real, foundational, correctly cited -- HIGH
  - Quantum geometry (Rovelli/LQG)  : real, active, genuinely unresolved     -- MEDIUM
  - Orch-OR consciousness           : real theory, but mainstream
                                       neuroscience largely rejects it      -- LOW,
                                       and CONTRADICTS a claim recording that rejection
  - Light-angle-derives-GR          : no supporting literature found at all;
                                       the citations QIH offers for it don't
                                       address the mechanism                -- VERY LOW,
                                       and CONTRADICTS a claim recording that absence
  - The 10 quantum-workflow papers  : real, verified papers -- HIGH on their
                                       own content; but the "QIH validates
                                       this" annotation bolted onto each one
                                       is an unsupported analogy, not a
                                       finding in the paper -- LOW

Two genuine CONTRADICTS conflicts are encoded (light-angle, consciousness),
not invented for effect -- both came out of this session's actual research.
"""

from research_graph_schema import (
    Node, Edge, Provenance, ConflictEdge, ResearchGraph,
    NodeType, EdgeType, ExtractionMethod, ConflictType,
)

TS = "2026-07-26T20:00:00+00:00"


def _prov(source_paper: str, conf: float, notes: str) -> Provenance:
    return Provenance(
        source_paper=source_paper,
        extraction_method=ExtractionMethod.HUMAN_ANNOTATION.value,
        confidence=conf,
        extracted_at=TS,
        human_reviewed=True,
        review_notes=notes,
    )


def _paper(pid: str, title: str, url: str, published: str) -> Node:
    return Node(
        id=pid,
        type=NodeType.PAPER.value,
        label=title,
        provenance=_prov(pid, 1.0, "Metadata; existence and authorship verified via live search this session."),
        properties={"title": title, "url": url, "published": published},
    )


def _claim(cid: str, paper_id: str, text: str, conf: float, subject: str,
           relation: str, obj: str, notes: str) -> Node:
    return Node(
        id=cid,
        type=NodeType.CLAIM.value,
        label=text,
        provenance=_prov(paper_id, conf, notes),
        properties={"text": text, "subject": subject, "relation": relation, "object": obj},
    )


# ---------------------------------------------------------------------------
# Papers
# ---------------------------------------------------------------------------

PAPER_MALDACENA = _paper(
    "paper_hep_th_9711200",
    "Large N Field Theories, String Theory and Gravity",
    "https://arxiv.org/abs/hep-th/9711200", "1997",
)
PAPER_HAWKING = _paper(
    "paper_hawking_1974",
    "Black hole explosions?",
    "https://www.nature.com/articles/248030a0", "1974",
)
PAPER_ROVELLI = _paper(
    "paper_rovelli_2008",
    "Quantum gravity",
    "https://arxiv.org/abs/0705.2222", "2008",
)
PAPER_ORCH_OR = _paper(
    "paper_penrose_hameroff_2014",
    "Consciousness in the universe: A review of the 'Orch OR' theory",
    "https://www.sciencedirect.com/science/article/pii/S1571064513001188", "2014",
)
PAPER_QIH = _paper(
    "paper_qih_padgett_2026",
    "Quantum Information Holography (QIH): Complete Research Guide",
    "https://medium.com/@jasonpadgett_76068", "2026-07",
)
PAPER_NWQWORKFLOW = _paper(
    "paper_2601_15521",
    "NWQWorkflow: The Northwest Quantum Workflow",
    "https://arxiv.org/abs/2601.15521", "2026-01",
)
PAPER_PILOT_QUANTUM = _paper(
    "paper_2412_18519",
    "Pilot-Quantum: A Quantum-HPC Middleware for Resource, Workload and Task Management",
    "https://arxiv.org/abs/2412.18519", "2024-12",
)

PAPERS = [PAPER_MALDACENA, PAPER_HAWKING, PAPER_ROVELLI, PAPER_ORCH_OR,
          PAPER_QIH, PAPER_NWQWORKFLOW, PAPER_PILOT_QUANTUM]


# ---------------------------------------------------------------------------
# Claims -- confidence is this session's independent fact-check, not QIH's own
# ---------------------------------------------------------------------------

CLAIM_HOLOGRAPHY = _claim(
    "claim_holography_established", PAPER_MALDACENA.id,
    "The holographic principle (AdS/CFT correspondence) is established, "
    "peer-reviewed theoretical physics.",
    0.97, "holographic principle", "is_established_in", "theoretical physics",
    "Verified: Maldacena 1997 is real, foundational, correctly characterized "
    "by the source document.",
)

CLAIM_BH_THERMO = _claim(
    "claim_bh_thermo_established", PAPER_HAWKING.id,
    "Black hole thermodynamics and Hawking radiation as an information "
    "carrier is established physics.",
    0.95, "Hawking radiation", "is_established_in", "black hole physics",
    "Verified: Hawking 1974 is real and correctly characterized.",
)

CLAIM_QUANTUM_GEOMETRY = _claim(
    "claim_quantum_geometry_active", PAPER_ROVELLI.id,
    "Quantum geometry / Planck-scale spacetime discreteness (loop quantum "
    "gravity, causal dynamical triangulation) is active, unresolved research.",
    0.65, "quantum geometry", "is_active_research_in", "quantum gravity",
    "Verified: real, ongoing research program, not experimentally settled "
    "either way -- fair characterization by the source document.",
)

CLAIM_ORCH_OR = _claim(
    "claim_consciousness_orch_or", PAPER_ORCH_OR.id,
    "Consciousness emerges from quantum coherence sustained in neuronal "
    "microtubules (Orchestrated Objective Reduction).",
    0.25, "microtubule quantum coherence", "produces", "consciousness",
    "Real theory, real authors, but the source document's '⚠ Debated' label "
    "undersells how marginalized this view is in mainstream neuroscience.",
)
CLAIM_ORCH_OR_REJECTED = _claim(
    "claim_orch_or_mainstream_rejection", "independent_factcheck_2026_07",
    "Mainstream neuroscience considers Orch-OR largely unsupported: brains "
    "are too warm/wet/noisy for the required coherence times, it offers no "
    "independently testable predictions, and microtubule-disabling drugs do "
    "not abolish consciousness.",
    0.85, "warm-wet-noisy decoherence objection", "undermines", "Orch-OR",
    "This session's fact-check finding, sourced from independent search "
    "results on Orch-OR's reception, not from the QIH document.",
)

CLAIM_LIGHT_ANGLE = _claim(
    "claim_light_angle_derives_gr", PAPER_QIH.id,
    "The angle θ of light relative to a Planck-scale lattice encodes "
    "velocity, gravity, and quantum state, and Einstein's field equations "
    "can be derived from the statistical distribution of these angles.",
    0.08, "light angle distributions", "derives", "Einstein's field equations",
    "QIH's central novel claim, marked '✗ Currently untested' in its own "
    "document. Held at very low confidence pending the review below.",
)
CLAIM_LIGHT_ANGLE_UNSUPPORTED = _claim(
    "claim_light_angle_unsupported", "independent_factcheck_2026_07",
    "No peer-reviewed paper independently supports deriving general "
    "relativity from light-angle statistics on a Planck lattice; the "
    "citations QIH offers for this claim (generic conformal-field-theory and "
    "emergent-gravity reviews) do not address this specific mechanism.",
    0.9, "QIH's cited support", "does_not_address", "the angle-to-GR mechanism",
    "This session's fact-check: searched directly for the claimed derivation "
    "and for the specific content of QIH's own cited sources; found neither.",
)

CLAIM_QIH_NOT_INSTITUTIONAL = _claim(
    "claim_qih_self_published", PAPER_QIH.id,
    "QIH is a self-published framework (TikTok, Medium, personal blog, a "
    "Zenodo self-deposit) with no identified institutional academic "
    "affiliation or peer review, despite the source document listing named "
    "physicists as an 'advisory board.'",
    0.9, "QIH", "lacks", "institutional academic backing",
    "This session's fact-check: found no evidence connecting Rovelli, "
    "Strominger, Maldacena, or Harlow to this work.",
)

CLAIM_NWQWORKFLOW_REAL = _claim(
    "claim_nwqworkflow_real", PAPER_NWQWORKFLOW.id,
    "NWQWorkflow is a real, verified end-to-end quantum software stack "
    "spanning programming, compilation, error correction, and hardware "
    "control, developed at PNNL.",
    0.95, "NWQWorkflow", "is", "a real, verified quantum software stack",
    "Verified: arXiv 2601.15521 exists, matches the described content and "
    "authorship (Ang Li, PNNL).",
)

CLAIM_WORKFLOW_QIH_LINK_UNSUPPORTED = _claim(
    "claim_workflow_qih_link_unsupported", PAPER_QIH.id,
    "The claim that NWQWorkflow's modular components 'validate' or "
    "'directly support' QIH's holographic-boundary-encoding principle is an "
    "analogy asserted by the QIH document, not a finding stated in "
    "NWQWorkflow itself.",
    0.15, "the QIH-validates-workflow-engineering analogy", "is_unsupported_by", PAPER_NWQWORKFLOW.id,
    "This session's fact-check: NWQWorkflow's own text makes no reference "
    "to holography, QIH, or Padgett; the connection exists only in the "
    "second (synthesis) document.",
)

CLAIMS = [
    CLAIM_HOLOGRAPHY, CLAIM_BH_THERMO, CLAIM_QUANTUM_GEOMETRY,
    CLAIM_ORCH_OR, CLAIM_ORCH_OR_REJECTED,
    CLAIM_LIGHT_ANGLE, CLAIM_LIGHT_ANGLE_UNSUPPORTED,
    CLAIM_QIH_NOT_INSTITUTIONAL,
    CLAIM_NWQWORKFLOW_REAL, CLAIM_WORKFLOW_QIH_LINK_UNSUPPORTED,
]

# (claim, its paper) -- for the PRODUCES edges
CLAIM_PAPER_PAIRS = [
    (CLAIM_HOLOGRAPHY, PAPER_MALDACENA),
    (CLAIM_BH_THERMO, PAPER_HAWKING),
    (CLAIM_QUANTUM_GEOMETRY, PAPER_ROVELLI),
    (CLAIM_ORCH_OR, PAPER_ORCH_OR),
    (CLAIM_ORCH_OR_REJECTED, PAPER_QIH),   # the rebuttal is filed against the document that repeats the claim
    (CLAIM_LIGHT_ANGLE, PAPER_QIH),
    (CLAIM_LIGHT_ANGLE_UNSUPPORTED, PAPER_QIH),
    (CLAIM_QIH_NOT_INSTITUTIONAL, PAPER_QIH),
    (CLAIM_NWQWORKFLOW_REAL, PAPER_NWQWORKFLOW),
    (CLAIM_WORKFLOW_QIH_LINK_UNSUPPORTED, PAPER_QIH),
]

# Genuine conflicts found during fact-checking -- not invented for effect.
CONFLICTS = [
    ConflictEdge(
        source_claim_id=CLAIM_LIGHT_ANGLE.id,
        target_claim_id=CLAIM_LIGHT_ANGLE_UNSUPPORTED.id,
        conflict_type=ConflictType.CONTRADICTS,
        severity=0.9,
        evidence="QIH asserts the derivation exists as a research target; independent "
                 "search found no literature supporting the specific mechanism, "
                 "including in QIH's own cited sources.",
    ),
    ConflictEdge(
        source_claim_id=CLAIM_ORCH_OR.id,
        target_claim_id=CLAIM_ORCH_OR_REJECTED.id,
        conflict_type=ConflictType.CONTRADICTS,
        severity=0.75,
        evidence="Orch-OR proposes microtubule quantum coherence as the seat of "
                 "consciousness; mainstream neuroscience's decoherence and "
                 "pharmacological objections directly contradict its viability.",
    ),
]


def build_stress_graph() -> ResearchGraph:
    edges = []
    for claim, paper in CLAIM_PAPER_PAIRS:
        edges.append(Edge(paper.id, claim.id, EdgeType.PRODUCES.value,
                          _prov(paper.id, 1.0, "")))
    return ResearchGraph(nodes=PAPERS + CLAIMS, edges=edges, conflicts=CONFLICTS)


if __name__ == "__main__":
    import graph_inspector
    print(graph_inspector.render_report(build_stress_graph()))
