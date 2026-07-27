# Updated Job Search Strategy: Startup + Enterprise Tier (31 Positions, 12 Companies)

**Updated**: 2026-07-27  
**Original Plan**: 21 positions, 8 companies  
**Extended Plan**: 31 positions, 12 companies  
**New**: AWS, Palo Alto Networks, NXP, IBM enterprise tier targets

---

## Executive Summary

The original 5-company hot target strategy remains strong. The addition of 4 enterprise tier companies **increases opportunity surface by 48%** (21→31 positions) while providing **strategic flexibility** in the final offer decision phase.

**Original Path**: Pure quantum engineering (startups)  
**New Path**: Scale + governance + program leadership (enterprise)  
**Recommendation**: Apply to both, decide based on offers received

---

## Market Opportunity Expansion

### Before (8 companies, 21 positions)

```
STARTUP/SCALEUP QUANTUM (5 hot):
├─ Atom Computing        (4 positions, $150-220K)
├─ IonQ                  (3 positions, $140-200K)
├─ D-Wave Systems        (3 positions, $140-240K)
├─ PsiQuantum            (2 positions, $140-180K)
└─ Google Quantum AI     (3 positions, $141-253K)

WARM TARGETS (3):
├─ DigiCert              (2 positions, $100-170K) — PQC
├─ PQShield              (2 positions, internship) — PQC
└─ Google (PQC team)     (2 positions, $130-301K) — Crypto

Total: 21 positions, average salary $140-190K
```

### After (12 companies, 31 positions)

```
STARTUP/SCALEUP TIER (same 5, now 11 positions):
├─ Atom Computing        (4 positions, $150-220K)
├─ IonQ                  (3 positions, $140-200K)
├─ D-Wave Systems        (3 positions, $140-240K)
├─ PsiQuantum            (2 positions, $140-180K)
└─ Google Quantum AI     (3 positions, $141-253K)

ENTERPRISE TIER (4 new hot, now 10+ positions):
├─ AWS Quantum           (3 positions, $160-250K) — NEW HOT
├─ Palo Alto Networks    (2 positions, $140-210K) — NEW WARM
├─ NXP Semiconductors    (2 positions, $120-200K) — NEW WARM
└─ IBM Quantum + Security (3 positions, $130-230K) — NEW HOT

PLUS: DigiCert (2), PQShield (2), Google Crypto (2)

Total: 31 positions, 12 companies, average salary $140-210K
```

---

## Strategic Flexibility

### Decision Matrix

| Factor | Startup Tier | Enterprise Tier | Better For You? |
|---|---|---|---|
| **Quantum Focus** | Primary | Secondary (hybrid) | Startups if pure quantum interests you |
| **Salary** | $140-250K | $140-250K | Comparable (enterprise slightly higher) |
| **Equity** | High upside potential | Lower/none | Startups if building wealth matters |
| **Stability** | Growing risk | Established | Enterprise if you value stability |
| **Remote** | Limited (on-site) | Hybrid/friendly | Enterprise if remote is priority |
| **Program Mgmt** | Engineering-focused | Program leadership | Enterprise if you want to manage |
| **Scale** | Team of 50-500 | Team of 500-50K | Enterprise if you want impact at scale |
| **Research** | Cutting-edge | Practical applications | Startups if research matters |
| **PQC Focus** | Emerging | Primary | Enterprise if PQC is main interest |

### By Life Stage

**If you're**: Early-career, building reputation, want quantum research  
→ **Apply to**: Startup tier (Atom, IonQ, D-Wave, PsiQuantum, Google Quantum AI)  
→ **Expected**: $140-200K base, high equity, cutting-edge quantum work  
→ **Number**: 8-10 applications

**If you're**: Mid-career, proven competence, want program leadership  
→ **Apply to**: Enterprise tier (AWS, IBM, Palo Alto, NXP)  
→ **Expected**: $160-250K base, program manager title, governance role  
→ **Number**: 8-10 applications

**If you're**: Flexible on path, want optionality  
→ **Apply to**: Both tiers  
→ **Expected**: 2-3 offers across different career paths  
→ **Number**: 16-20 total applications

---

## Application Strategy: 31 Positions, 12 Companies

### Phased Approach (4-5 weeks)

**Week 1: Research & Targeting**
- Run `python3 populate_tracker_extended.py` (shows all 31 positions)
- Research 20-25 positions (pick from both tiers based on interests)
- Read ADDITIONAL_TARGETS_RESEARCH_GUIDE.md for enterprise tier context
- Document which tier you're leaning toward

**Week 2: Application Prep**
- Polish resume (emphasize architecture OR governance OR performance depending on path)
- Draft 3-5 cover letter templates (one per project variant)
- Prepare elevator pitches for both startup and enterprise conversations

**Week 3-4: Bulk Applications**
- **STARTUP PATH** (if chosen): 8-10 applications to Atom/IonQ/D-Wave/PsiQuantum/Google Quantum
  - Emphasize: quantum physics, real-time control, innovation
  - Variant focus: CONSTRAINTS_FOCUSED, SIMULATOR_FOCUSED
  
- **ENTERPRISE PATH** (if chosen): 8-10 applications to AWS/IBM/Palo Alto/NXP
  - Emphasize: governance, scale, program leadership
  - Variant focus: ARCHITECTURE_FOCUSED, GOVERNANCE_FOCUSED
  
- **BALANCED PATH** (if chosen): 8-10 to startups + 8-10 to enterprise
  - Mix variants across all 5
  - Let offers guide final decision

**Week 5+: Interviews**
- Expected: 25% response rate = 4-5 interviews from 16-20 applications
- Prepare using PROJECT_VARIANTS.md (pick 2-3 variants matching your tier)
- If both tiers respond, interview for both (gain experience, leverage offers in negotiation)

---

## Project Variant Alignment by Tier

### Startup Tier (Quantum-focused)

**Control Engineer Variant** (best for: IonQ, Atom, PsiQuantum)
- Code: quantum_controller.py (6-stage loop)
- Emphasis: Real-time feedback, confidence-driven decisions, recovery
- Interview: Explain timing domains, control law synthesis

**Simulator Variant** (best for: Google Quantum AI, PsiQuantum)
- Code: quantum_simulator.py (Markovian + non-Markovian)
- Emphasis: Fidelity models, robustness, physics realism
- Interview: Discuss T1/T2 times, decoherence, error models

**Architecture Variant** (best for: IBM Qiskit, all startups)
- Code: quantum_schema.py (5-layer model)
- Emphasis: Layered design, service contracts, decoupling
- Interview: How layers map to their systems (Qiskit, Cirq, etc.)

### Enterprise Tier (Scale + Governance)

**Architecture Variant** (best for: AWS TPM, IBM Qiskit, Google Quantum)
- Code: quantum_schema.py (5-layer model)
- Emphasis: Enterprise-scale architecture, team ownership, contracts
- Interview: How 5 layers scale to 1000+ person organization

**Governance Variant** (best for: Palo Alto PQC, IBM Security, NXP)
- Code: quantum_constraints.py + quantum_controller.py (policy, validation)
- Emphasis: Policy enforcement, audit trails, standards compliance
- Interview: NIST PQC timeline, migration governance, compliance

**Dashboard Variant** (best for: AWS Infrastructure, IBM Observability, Palo Alto)
- Code: quantum_dashboard.py (event streaming, real-time metrics)
- Emphasis: Real-time observability, enterprise-scale monitoring, anomaly detection
- Interview: How to monitor quantum systems at enterprise scale

**Constraints Variant** (best for: NXP Hardware, D-Wave Quantum)
- Code: quantum_constraints.py (5 pluggable checks, O(N) performance)
- Emphasis: Resource constraints, hardware limits, optimization
- Interview: Embedded systems constraints, hardware-software co-design

---

## Salary & Negotiation Strategy

### Market Data (July 2026)

**Startup Tier**:
- Early-career (0-3 years): $120-160K + 0.05-0.15% equity
- Mid-career (3-7 years): $140-200K + 0.03-0.10% equity
- Senior (7+ years): $180-250K + 0.02-0.05% equity

**Enterprise Tier**:
- Senior Engineer (7-10 years): $150-220K + small bonus
- Staff Engineer: $180-260K + 15-20% bonus
- Program Manager: $140-200K + 15-20% bonus
- Senior Program Manager: $160-240K + 20%+ bonus

### Negotiation Approach

**For Startup Offers**:
- Lead with salary ($150-170K is competitive for mid-level)
- Negotiate equity (0.05-0.10% for senior roles is standard in early-stage)
- Ask about funding runway (seed companies dying is real risk)

**For Enterprise Offers**:
- Lead with total compensation (base + bonus + equity)
- Ask about program scope (you want to lead, not just manage status)
- Negotiate title (program manager vs. technical program manager matters)

**If Multiple Offers**:
- Don't pit offers against each other verbally
- Use facts: "I have another offer at $X with these benefits"
- Enterprise companies often beat startup salary but not equity
- Decide based on: career path (quantum research vs. program leadership), location preference, personal growth

---

## Success Metrics: Revised

### Application Phase

**Original (8 companies, 21 positions)**:
- Target: 15-20 applications
- Expected interviews: 25% = 4-5
- Expected offers: 50% conversion = 2-3

**Extended (12 companies, 31 positions)**:
- Target: 16-20 applications (same discipline, larger pool)
- Expected interviews: 25% = 4-5 (may get 1-2 per tier if both applied)
- Expected offers: 50% conversion = 2-3 (may get 1-2 per tier if both interviewed)

### Decision Phase

- **Startup offer(s)**: $140-200K base + 0.05-0.10% equity
- **Enterprise offer(s)**: $150-250K base + 15-20% bonus
- **Decision criteria**: Career path (research vs. leadership), salary, equity upside, role scope, location, team

---

## Key Risks & Mitigations

### Risk 1: Spreading Too Thin
**Problem**: 16-20 applications across 2 tiers might dilute message  
**Mitigation**: Use same resume/talking points, customize only cover letter per company. Phase applications (startup tier Week 3-4, enterprise tier Week 4-5) so you're not managing 20 concurrent applications.

### Risk 2: Tier Indecision
**Problem**: Getting offers from both tiers, hard to choose  
**Mitigation**: Decide your priority BEFORE you start applying. Do you want quantum or program leadership? Gravity naturally pulls you one way. Talking to people in both paths helps (find mentors at each tier, ask what they value).

### Risk 3: Enterprise Tier Isn't "Quantum Enough"
**Problem**: You want pure quantum, but enterprise roles are hybrid  
**Mitigation**: AWS and IBM roles ARE hybrid quantum-classical (exactly what you built in Phase 1). Palo Alto and NXP are more crypto than quantum. If you want pure quantum, focus on startup tier.

### Risk 4: Startup Equity Talks Are Vague
**Problem**: Company promises "0.10% equity" but doesn't specify vesting, strike price  
**Mitigation**: Ask during offer phase: 4-year vest? 1-year cliff? What's the strike price? When did SAFE convert to stock? What's current valuation? Don't accept vague equity.

---

## Revised Timeline

**Total Duration**: 4-5 weeks research + application, 8-12 weeks interviews + negotiation  
**Target**: Signed offer by Week 12-16

```
Week 1: Research (31 positions across 12 companies)
Week 2: Prep (resume, cover letters, decide tier strategy)
Week 3-4: Applications (16-20 total, phased per tier)
Week 5-8: Interviews (4-5 interviews, 1-2 per tier if both applied)
Week 9-12: Offers + Negotiation (decide based on best fit)
Week 12+: Accept + Onboard
```

---

## Decision Tree: Which Path?

```
START: Do you want to pursue quantum computing jobs?
│
├─ YES → "What's your priority?"
│   │
│   ├─ "Pure quantum research" 
│   │  → STARTUP TIER (Atom, IonQ, D-Wave, PsiQuantum, Google Quantum)
│   │  → 8-10 applications
│   │  → Expect: $140-200K + 0.05-0.10% equity
│   │
│   ├─ "Program leadership + scale"
│   │  → ENTERPRISE TIER (AWS, IBM, Palo Alto, NXP)
│   │  → 8-10 applications
│   │  → Expect: $160-250K + bonus
│   │
│   └─ "I'm flexible / want maximum options"
│      → BOTH TIERS
│      → 16-20 applications
│      → Expect: 2-3 offers across both paths
│      → Decide based on offers + conversation with teams
│
└─ NO → You're all set! Good luck with other paths.
```

---

## Files to Use

**For extended job search**:
1. `ADDITIONAL_TARGETS_RESEARCH_GUIDE.md` — Deep dive on AWS, Palo Alto, NXP, IBM
2. `populate_tracker_extended.py` — Load 31 positions across 12 companies
3. `JOB_SEARCH_EXECUTION_GUIDE.md` — Same 5-phase structure (now with 31 vs. 21 positions)
4. `RECRUITER_STRATEGY.md` — Market analysis (still valid for both tiers)
5. `PROJECT_VARIANTS.md` — Role-specific positioning (add enterprise examples)

**Updated decision framework**:
- Startup path → Focus on CONSTRAINTS, SIMULATOR, CONTROL variants
- Enterprise path → Focus on ARCHITECTURE, GOVERNANCE, DASHBOARD variants
- Balanced path → Mix all variants, interview for both, let offers guide decision

---

## Recommendation

**Execute Extended Strategy**: 16-20 applications across both tiers.

**Rationale**:
1. Same application effort (16-20 vs. 15-20)
2. Significantly larger opportunity surface (31 vs. 21 positions)
3. Strategic flexibility (don't lock into one path before seeing offers)
4. Risk mitigation (if one tier doesn't respond, other tier has options)
5. Market is hot (both startup and enterprise hiring aggressively)

**Tier Decision** can wait until Week 5-8 when you have interview invites. Then decide:
- Focus on startup interviews (lean into quantum), or
- Focus on enterprise interviews (lean into program leadership), or
- Interview for both and decide when offers arrive

Your Phase 1 project works for both paths. Use different variants to position for each.

---

**Next Step**: Run `populate_tracker_extended.py` and pick 16-20 positions to target from the 31 available.
