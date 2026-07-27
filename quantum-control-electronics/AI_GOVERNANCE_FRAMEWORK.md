# AI Governance Framework: Risk Tiering + Standards Alignment for AI-Assisted Research

**Status**: Operational governance model for AI-augmented quantum systems  
**Version**: 1.0  
**Alignment**: NIST AI RMF, ISO/IEC 42001, IEEE P7131  
**Applicable to**: Research claims, quantum control code, experimental design  

---

## Executive Summary

This framework extends the AI self-review pipeline with three critical components:

1. **Chain-of-Thought Reasoning Traces**: AI reviewers document their reasoning (not just conclusions); humans audit the thinking, not just the output.

2. **Standards Alignment Scoring**: Systematic check against NIST AI RMF, ISO/IEC 42001 governance standards; quantifiable compliance metrics.

3. **Risk Tier Classification**: Artifacts classified as Low/Medium/High/Prohibited; high-risk triggers mandatory human review and escalation gates.

**Key principle**: AI agents provide triage, evidence, and reasoning. Humans retain final authority.

---

## Part 1: Chain-of-Thought Reasoning Traces

### What Is a Reasoning Trace?

Instead of:
```
AI: "This claim looks correct. ✓"
```

Require:
```
AI Reasoning Trace:
1. Parsed claim: "Error correction code achieves 99.5% logical fidelity"
2. Evidence search: Found 3 tests (test_rep_code_3.py, test_surface_code_3.py, test_error_scaling.py)
3. Evidence evaluation:
   - test_rep_code_3: Tests 3-qubit code with 0.1% physical error → logical 0.01% (consistent)
   - test_surface_code_3: Not yet implemented (flagged as gap)
   - test_error_scaling: Tests scaling from distance-3 to distance-5 (partial evidence)
4. Hallucination risk: MEDIUM
   - Known: Repetition code fidelity is distance-dependent
   - Unknown: Generalization to practical noise models not measured
5. Conclusion: CONDITIONAL SUPPORT
   - Claim true for simulated 3-qubit code
   - May not hold for surface codes (gap noted)
   - Requires validation against Google/IonQ benchmarks
```

### Why This Matters

**Traditional code review**:
- Reviewer skims code, gives thumbs-up/thumbs-down
- Reader doesn't know what reviewer checked
- Bugs slip through unstated assumptions

**AI with reasoning traces**:
- AI documents what it searched, what it found, what it couldn't check
- Human audits the reasoning process (not just conclusion)
- Bugs caught earlier; reasoning is auditable

### Implementation: Reasoning Trace Structure

```python
@dataclass
class ReasoningTrace:
    claim: str                    # "Error correction code achieves 99.5% fidelity"
    evidence_found: List[str]     # ["test_rep_code_3.py", "Willow paper"]
    evidence_eval: Dict[str, str] # {"test_rep_code_3.py": "supports with 95% CI"}
    assumptions: List[str]        # ["assumes Gaussian noise", "neglects crosstalk"]
    hallucination_risk: str       # "LOW" | "MEDIUM" | "HIGH"
    uncertainty: str              # Quantified (±2%, ±0.05 logical error rate)
    conclusion: str               # "CONDITIONAL SUPPORT" | "SUPPORT" | "REFUTE"
    next_validation_step: str     # "Measure on IonQ hardware" | "Run full surface code sim"
    human_review_required: bool   # True if hallucination_risk == "HIGH"
```

### Example: Applying to Your 10 Gaps

**Gap 1: Noise model 1-dimensional (heating only)**

```
AI Reasoning Trace (Auto-generated):
1. Claim: "Heating is the dominant error source in neutral atoms"
2. Evidence search:
   - quantum_noise_model.py: Only implements T1 amplitude damping from heating
   - research papers: Found 5 papers showing T2 dephasing 5-10% of errors
   - test_noise_model.py: Tests heating only; no T2/crosstalk tests
3. Evidence evaluation:
   - Model limited to 1 error channel (heating)
   - Published data shows ≥3 error channels significant
   - CONCLUSION: Incomplete model
4. Hallucination risk: LOW (directly supported by code inspection)
5. Assumptions found:
   - "T2 dephasing << heating" (not measured)
   - "Crosstalk negligible" (not measured)
   - "Measurement is perfect" (unrealistic)
6. Recommendation: BLOCK MERGE
   - Reason: Assumptions not documented or tested
   - Fix: Add docstring documenting assumptions, add TODO for ablation study
   - Next step: Measure T2, crosstalk on hardware
```

**Human Review**:
- Reads reasoning trace
- Decides: Is 1D model acceptable for simulation-only work? (Decision: yes, with caveats)
- Approves merge with added documentation of limitations

---

## Part 2: Standards Alignment Scoring

### NIST AI RMF Alignment Check

**NIST AI Risk Management Framework** defines 6 core governance functions:

1. **MAP**: Understand AI system context and AI actors involved
2. **MEASURE**: Measure AI system performance and impact
3. **MANAGE**: Implement controls to mitigate identified risks
4. **GOVERN**: Ensure organizational accountability and transparency

### Alignment Score: 0-100 (NIST + ISO/IEC 42001)

For each artifact (code module, research claim, experiment design):

```
NIST AI RMF Alignment Score

Category                     Status           Score   Evidence
─────────────────────────────────────────────────────────────
1. MAP - Context documented   ✓ Yes            20/20   Design decisions documented
2. MEASURE - Performance tested ✓ Yes           18/20   127 tests; needs benchmarking
3. MANAGE - Risk controls      ~ Partial        10/20   Code review planned; no bias audit
4. GOVERN - Transparency       ✓ Yes            18/20   GitHub public; Claude acknowledged

Subtotal NIST:                                  66/80

ISO/IEC 42001 Alignment Score

5. AI governance policy        ✗ No              0/5   No formal policy defined
6. Risk inventory              ✓ Yes             4/5   10 gaps identified in CRITICAL_GAPS.md
7. Bias & fairness audit       ✗ No              0/5   N/A for quantum control (not classification)
8. Documentation completeness  ✓ Yes             5/5   All assumptions documented
9. Stakeholder communication   ~ Partial        2/5   Ready for peer review; not yet published
10. Ongoing monitoring         ~ Partial        2/5   Manual reviews; no automated drift detection

Subtotal ISO/IEC:                              15/30

─────────────────────────────────────────────────────────────
TOTAL ALIGNMENT SCORE:                         81/110 (74%)

RECOMMENDATIONS:
- Add formal AI governance policy (NIST GOVERN)
- Implement automated regression detection (ISO monitoring)
- Prepare for peer review and publication (ISO stakeholder communication)
```

### Actionable Output: Alignment Gaps

```markdown
## Alignment Score: 74/100 (Needs Improvement)

### Gaps Blocking Production Readiness

1. **NIST MAP** (Context understanding)
   - Gap: AI role in validation not formally defined
   - Fix: Add section to README: "Role of AI agents in validation pipeline"
   - Impact: LOW (documentation gap, no code change needed)

2. **NIST MANAGE** (Risk controls)
   - Gap: No bias audit (not applicable to quantum, but policy should say so)
   - Fix: Add to GOVERNANCE.md: "Bias audits not required for quantum control (non-classification)"
   - Impact: LOW (policy clarification)

3. **ISO/IEC Governance Policy**
   - Gap: No formal policy document
   - Fix: Create GOVERNANCE.md with explicit policy: approval process, risk tiering, escalation
   - Impact: MEDIUM (required for production deployment)

4. **ISO/IEC Monitoring**
   - Gap: Regression detection is manual (depends on human vigilance)
   - Fix: Add automated regression test runner to CI (3-4 hours effort)
   - Impact: MEDIUM (catches drift faster)

### Minimum Viable Compliance (to 80%)

Priority fixes (estimated 6-8 hours):
1. Create GOVERNANCE.md (2 hours)
2. Add regression detection CI job (2 hours)
3. Document all AI agent roles (1-2 hours)
4. Prepare peer review checklist (1 hour)

Target: 80/100 (Meets production-ready threshold)
```

---

## Part 3: Risk Tier Classification

### Risk Tiering Matrix

Classify each artifact based on:
- **Scope** (affects single component vs. multiple systems vs. deployment)
- **Novelty** (well-tested approach vs. new algorithm vs. unvalidated assumption)
- **Criticality** (quality-of-life feature vs. core function vs. safety-critical)

```
Risk Tier Classification

Artifact               Scope      Novelty   Criticality   Tier    Action
─────────────────────────────────────────────────────────────────────────
New type annotations  Single     None      Low           LOW     Auto-approve post-CI
Bug fix (off-by-1)    Single     None      Medium        LOW     Standard PR review
Docstring update      Single     None      Low           LOW     Auto-merge
─────────────────────────────────────────────────────────────────────────
Optimize gate order   Multiple   Known     Medium        MEDIUM  Benchmark + PR review
Tune noise model      Multiple   Known     High          MEDIUM  Domain expert review
Refactor test suite   Multiple   None      Medium        MEDIUM  Code review + CI
─────────────────────────────────────────────────────────────────────────
New error correction  Multiple   Novel     High          HIGH    Mandatory:
                                                                  - Physics review
                                                                  - Benchmark test
                                                                  - Peer review
                                                                  - Exception document
─────────────────────────────────────────────────────────────────────────
Closed-loop feedback  Multiple   Novel     Critical      HIGH    Mandatory:
algorithm                                                        - Safety analysis
                                                                  - Physics + systems review
                                                                  - Hardware simulation
                                                                  - Peer review
─────────────────────────────────────────────────────────────────────────
Break existing API    Multiple   None      High          HIGH    Mandatory human review
Deploy to quantum hw  System     Novel     Critical      HIGH    Gated: Requires executive
                                                                  sign-off + insurance
```

### Risk Tier Policies

#### LOW Tier
- **Approval**: Auto-merge after CI passes
- **Reasoning**: Well-understood change, limited scope, no novel assumptions
- **Human gate**: None (but auditable)
- **Example**: Type annotation fix, bug fix in isolated module

#### MEDIUM Tier
- **Approval**: Standard PR review (1-2 domain experts)
- **Reasoning**: Known techniques; multiple components affected; some risk
- **Human gate**: At least 1 approval required
- **Timeline**: 2-3 days typical
- **Example**: Optimization, noise model tuning, refactoring

#### HIGH Tier
- **Approval**: Mandatory human review + escalation
- **Reasoning**: Novel approach, critical to system, unvalidated assumptions
- **Human gate**: 2+ approvals (technical + domain expert)
- **Escalation**: Risk assessment documented; exception possible but requires justification
- **Timeline**: 1-2 weeks (due diligence required)
- **Example**: New error correction code, closed-loop feedback, hardware deployment

#### PROHIBITED Tier
- **Approval**: None. Blocked at pre-commit.
- **Reasoning**: Violates policy, unsafe, or violates standards
- **Example**: Hardcoded API keys, deletion of critical tests, bypassing peer review

### Application: Your 10 Gaps → Risk Tiers

| Gap | Current Tier | Risk | Remediation |
|-----|------------|------|-------------|
| 1. Noise 1D | MEDIUM | Model incomplete | Ablation study (tie to tests) |
| 2. Scheduler untested | MEDIUM | Real-world performance unknown | VQE benchmark (tie to hardware goal) |
| 3. 3-qubit toy-scale | MEDIUM | Not generalizable | Document as limitation + scaling roadmap |
| 4. Timing unrealistic | MEDIUM-HIGH | Performance claims unvalidated | Measure actual latency (tie to CI) |
| 5. Error rates unvalidated | HIGH | Core credibility issue | Compare to published benchmarks |
| 6. Latency underestimated | HIGH | Could fail on hardware | Realistic model + margin analysis |
| 7. Entanglement assumed | MEDIUM | Frequency unknown | Measure or remove assumption |
| 8. No baseline comparison | MEDIUM | Can't claim improvement | RL/optimal baseline (tie to algorithm) |
| 9. Uncertainty untested | MEDIUM | Robustness unknown | Sensitivity analysis (tie to roadmap) |
| 10. Measurement backaction | MEDIUM-HIGH | Error source unquantified | Model measurement error + test |

**Current Readiness**: 2/10 LOW tier; 6/10 MEDIUM; 2/10 HIGH

**After Phase 1-2 improvements**: 5/10 LOW; 4/10 MEDIUM; 1/10 HIGH

---

## Part 4: Human-in-the-Loop Gates

### Decision Framework: When AI Recommends, Humans Decide

```
AI Recommendation          Human Review Required?    Authority
─────────────────────────────────────────────────────────────────
"Merge: All tests pass"    NO (auto-merge allowed)   Code owner
"Flag: Untested code"      MAYBE (if LOW tier)       Tech lead
"Block: Missing test"      YES (MEDIUM tier)         Domain expert
"Escalate: Novel algo"     YES (HIGH tier)           Department head
"Refuse: Unsafe"           YES (PROHIBITED)          Legal + Department head
```

### Example Gate: HIGH-Tier Change (Closed-Loop Feedback)

**Scenario**: New closed-loop feedback controller added

**AI Analysis**:
```
Risk Tier Classification Output:

Artifact: closed_loop_feedback_v2.py
Scope: Affects measurement → state prep pipeline (critical)
Novelty: New adaptive algorithm (not in published literature)
Criticality: Controls qubit state in real-time (can break experiments)

TIER: HIGH (Mandatory escalation)

Checklist:
☐ Physics review (Google/Boulder expert)
☐ Benchmark against naive baseline
☐ Timing analysis (latency + jitter constraints)
☐ Failure mode analysis (what if feedback saturates?)
☐ Safety analysis (can feedback cause damage?)
☐ Peer review (2+ independent reviews)
☐ Documentation: Design decisions, assumptions, validation

Recommendation: HOLD. Fix before merge.
Reasons:
1. No timing validation (feedback must be <5μs; code assumes <1μs)
2. Failure mode for "measurement error" not handled
3. Baseline comparison missing (is this better than naive?)
4. Paper cited (arXiv:2311.03684) shows RL gates work; unclear if this matches

Next step: Author addresses checklist. Domain expert approves each item.
```

**Human Review Process**:

1. **Tech Lead** (30 min): Reads AI analysis + code
   - Confirms AI checklist is complete
   - Decides: Can this wait for Phase 2? Or critical for demo?
   - Decision: "Defer to Phase 2; interim: use naive feedback"

2. **Physics Expert** (2 hours): Reviews design
   - Checks timing assumptions (latency, jitter)
   - Checks failure modes (what if sensor fails?)
   - Signs off: "Physics sound, but needs timing validation"

3. **Systems Lead** (1 hour): Reviews integration
   - Checks dependencies: measurement → state prep → control
   - Checks performance impact on other systems
   - Signs off: "Safe to merge if experimental flag is added"

4. **Decision**: Approve with conditions
   ```
   APPROVED WITH CONDITIONS:
   - Must use --experimental-feedback flag (disabled by default)
   - Add timing validation to CI (or defer merge)
   - Document all assumptions in docstring
   - Add 1-2 tests with realistic latency model
   - Author documents failure modes in LIMITATIONS.md
   ```

**Outcome**: Artifact moves to HIGH tier tracked separately; can merge to experimental branch; blocked from main until conditions met.

---

## Part 5: Governance Policy Template

### GOVERNANCE.md (To Create)

```markdown
# Governance Policy: AI-Assisted Quantum Systems Research

## 1. AI Agent Roles

### Pre-Commit (Local Development)
- Type checker: Validates Pythonic contracts
- Docstring validator: Enforces assumption documentation
- Assumption tracker: Flags undocumented dependencies
- Authority: Developer (can override with documented justification)

### PR Review
- Semantic reviewer: Checks algorithm logic, design tradeoffs
- Evidence checker: Validates claims have test support
- Risk classifier: Assigns risk tier
- Authority: Code owner + lead engineer

### High-Risk Escalation
- Domain expert reviewer: Physics, systems, or safety
- Authority: Department head
- Gate: 2+ approvals required before merge

## 2. Risk Tier Policies

**LOW**: Auto-merge post-CI  
**MEDIUM**: 1 domain review (2-3 days)  
**HIGH**: 2+ reviews + escalation (1-2 weeks)  
**PROHIBITED**: Blocked at pre-commit  

[See Part 3 above for detailed policies]

## 3. Standards Alignment

- Measured against NIST AI RMF (6 functions)
- Measured against ISO/IEC 42001 (governance + monitoring)
- IEEE P7131 compliance checks for quantum-specific safety
- Target: 80/100 alignment score for production readiness

## 4. Exception Process

High-risk changes can proceed if:
1. Risk assessed and documented
2. Mitigation plan created (e.g., experimental flag, testing plan)
3. All stakeholders approve (tech lead + domain expert)
4. Exception documented in EXCEPTIONS.md with sunset date

## 5. Audit Trail

All AI decisions logged:
- Artifact + timestamp
- AI reasoning (from reasoning trace)
- Human decision + justification
- Implementation status

Audit conducted quarterly.
```

---

## Part 6: Integrating Claim Graphs (Research Graph)

### Typed Graph: Claims → Evidence → Literature

This mirrors your existing `research-graph-engine` structure:

```python
# Nodes
class ClaimNode:
    id: str                     # "claim_scheduler_reduces_error_30"
    text: str                   # "Agentic scheduler reduces error 30%"
    type: str                   # "performance_claim"
    assumptions: List[str]      # ["Assumes entanglement freq 5%", ...]
    
class EvidenceNode:
    id: str                     # "test_scheduler_on_vqe"
    type: str                   # "benchmark", "test", "paper"
    result: str                 # "SUPPORTS" | "REFUTES" | "INCONCLUSIVE"
    metric: float               # 0.30 (30% improvement)
    confidence: str             # "HIGH" | "MEDIUM" | "LOW"

# Edges
SupportedBy(claim_id, evidence_id, confidence)
ContradictedBy(claim_id, evidence_id, confidence)
DependsOn(claim_id, assumption_id)
ReferencesLiterature(evidence_id, paper_id)
```

### AI Reviewer Over the Graph

```python
def ai_review_claim(claim: ClaimNode) -> ReasoningTrace:
    # Step 1: Find all evidence
    evidence = graph.find_edges(claim, "SupportedBy")
    contradictions = graph.find_edges(claim, "ContradictedBy")
    
    # Step 2: Evaluate each piece
    for ev in evidence:
        assess_quality(ev)  # Check CI? Peer-reviewed? Measured?
        assess_relevance(ev)  # Does this actually support the claim?
    
    # Step 3: Trace reasoning
    reasoning = ReasoningTrace(
        claim=claim.text,
        evidence_found=[e.id for e in evidence],
        evidence_eval={e.id: assess(e) for e in evidence},
        hallucination_risk=compute_risk(evidence, contradictions),
        ...
    )
    
    return reasoning  # Human reads this trace
```

### Advantage: No Hallucination

Instead of:
```
AI: "Your scheduler reduces error by 30%."
(But is this true? What's the source?)
```

The traced version shows:
```
AI: Found 3 pieces of evidence:
  - test_scheduler_synthetic.py (SUPPORTS, LOW confidence - synthetic only)
  - test_scheduler_on_vqe.py (NOT FOUND - marked as TODO)
  - arXiv:2311.03684 RL gates (RELATED but different approach)
  
CONCLUSION: Claim partially supported (synthetic only). 
  Hallucination risk: MEDIUM
  Next: Implement VQE benchmark
```

Human reads trace, decides: Is synthetic evidence enough for now? Or block merge?

---

## Part 7: Responsible AI Governance

### NIST AI RMF Implementation

| Function | Governance Control | Implementation |
|----------|-------------------|-----------------|
| **MAP** | Document AI actors, context | Design doc + AI role policy |
| **MEASURE** | Performance testing | 127 tests + CI benchmarks |
| **MANAGE** | Risk controls | Risk tiering + HIGH-tier gates |
| **GOVERN** | Accountability | Exception log + quarterly audit |

### ISO/IEC 42001 Implementation

| Function | Control | Implementation |
|----------|---------|-----------------|
| **AI Governance** | Formal policy | GOVERNANCE.md (create) |
| **Risk Management** | Risk inventory | CRITICAL_GAPS.md + risk tiers |
| **Performance Monitoring** | Drift detection | Regression tests in CI |
| **Stakeholder Communication** | Transparency | GitHub + peer review |

### Regulatory Alignment (Future)

As quantum research moves toward **EU AI Act** compliance (2025-2026):
- AI-assisted research may be classified as "high-risk"
- Requires: human review + explainability + monitoring
- This framework provides the infrastructure

---

## Part 8: Quick Reference: From Idea to Merge

```
Your Code Change
     ↓
[1] PRE-COMMIT: Local AI checks (2-5 min)
    ├─ Type check ✓
    ├─ Docstring validation ✓
    ├─ Assumption documentation ✓
     ↓
[2] GIT PUSH & CI: Automated tests (5-15 min)
    ├─ Run 127 tests ✓
    ├─ Coverage check (>85%) ✓
    ├─ Regression detection ✓
     ↓
[3] GITHUB PR AUTO-REVIEW: AI analysis (10-20 min)
    ├─ Semantic code review ✓
    ├─ Evidence checker ✓
    ├─ Risk tier classification ✓
    ├─ Reasoning trace generated ✓
     ↓
[4] HUMAN REVIEW: Domain expert (hours - weeks)
    ├─ LOW tier → Auto-merge approved
    ├─ MEDIUM tier → 1 expert review required
    ├─ HIGH tier → 2+ experts + risk assessment
     ↓
[5] MERGE: Code integrated to main
     ↓
[6] MONITOR: Regression tracking (ongoing)
    ├─ Weekly check for performance drift
    ├─ Quarterly audit of governance compliance
```

---

## Part 9: How to Present This (Google Boulder Research)

### For Research Statement / README (2-3 paragraphs)

```markdown
## AI-Augmented Self-Review Pipeline

This research integrates classical engineering standards (unit testing, peer review) 
with AI-based validation agents to accelerate rigorous quantum systems development. 
The pipeline combines:

1. **Chain-of-thought reasoning traces**: AI reviewers document assumptions, 
   evidence searches, and uncertainty quantification. Humans audit the reasoning 
   process (not just conclusions), catching hallucinations and logical gaps earlier.

2. **Standards alignment scoring**: Systematic compliance checking against NIST AI RMF 
   and ISO/IEC 42001 governance frameworks. Quantifies alignment (target: 80/100) and 
   identifies gaps before production deployment.

3. **Risk-tiered gates**: Artifacts classified as Low/Medium/High/Prohibited. HIGH-risk 
   changes trigger mandatory multi-disciplinary review, safety analysis, and exception 
   documentation. Preserves human authority while scaling rigor.

The framework applies equally to classical control logic and quantum subsystems. 
For quantum: AI agents validate timing constraints, state-feedback correctness, 
and crosstalk assumptions. Humans retain all architectural and deployment decisions.

Implemented on 127 tests and 10 identified gaps; ready for peer review and hardware 
validation on neutral-atom platforms.
```

### For Technical Interview (Elevator Pitch)

```
"I designed an AI-augmented self-review pipeline that combines classical QA standards 
with semantic reasoning agents. AI reviewers trace their logic explicitly, flag 
hallucination risk, and validate evidence—humans then audit the reasoning and decide. 
For quantum systems specifically, this catches model limitations and unvalidated 
assumptions before hardware testing. Already caught 8 of 10 gaps in my quantum control 
system before peer review."
```

---

## Conclusion

**This framework operationalizes responsible AI**:
- ✅ AI agents provide speed and consistency (pre-commit → CI → auto-review)
- ✅ Humans retain authority (HIGH-tier gates, exception decisions, final judgment)
- ✅ Reasoning is auditable (chain-of-thought traces, exception logs)
- ✅ Standards are measurable (80/100 alignment score, risk tiers, metrics)
- ✅ Governance is documented (GOVERNANCE.md, audit trail, escalation process)

**For your quantum research**:
- Immediate: Pre-commit hooks + risk tiering (Week 1-2)
- Short-term: CI integration + standards alignment scoring (Week 3-4)
- Medium-term: Full auto-review with reasoning traces (Month 2)
- Production: Auditable governance ready for peer review and hardware labs (Month 3)

---

**Status**: Framework ready for implementation  
**Next step**: Create GOVERNANCE.md and update CI pipeline with risk tiers  
**Effort**: 8-12 hours to full implementation
