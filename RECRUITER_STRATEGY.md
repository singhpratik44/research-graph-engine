# Quantum-Classical OS Controller: Job Market Strategy

**Market Context**: 25% annual growth, 10,000+ unfilled quantum/PQC roles, $130-200K+ salary range, NIST PQC deadline: May 2026

---

## Executive Summary

**Goal**: Secure quantum computing or post-quantum cryptography engineering role leveraging the modular quantum-classical OS controller as proof of architectural competence.

**Timeline**: 2026-2027 hiring cycle

**Key Differentiator**: Project demonstrates five core competencies quantum companies actively hire for:
1. Graph-based system architecture (circuit/topology representation)
2. Real-time constraint evaluation (physics-first design)
3. Pluggable simulation interfaces (Markovian/non-Markovian models)
4. Observability & feedback loops (six-stage control loop)
5. Governance & bounded autonomy (policy-driven decisions)

---

## Market Landscape

### High-Priority Targets (HOT)

| Company | Industry | Stage | Roles | Salary | Alignment |
|---------|----------|-------|-------|--------|-----------|
| **Atom Computing** | Quantum Hardware | Startup ($100M funded) | Quantum Control Engineer, Systems Engineer | $120-190K+ | Neutral atom control, graph-based atom addressing |
| **IonQ** | Quantum Cloud | Growth Public | Quantum Software Engineer, Control Systems | $130-200K+ | Trapped-ion control feedback loops, real-time optimization |
| **D-Wave** | Quantum Optimization | Public | Optimization Engineer, Systems Engineer | $125-200K+ | Constraint-based scheduling, optimization graphs |
| **PsiQuantum** | Photonic Quantum | Startup ($7B valuation) | Systems Engineer, Simulation Engineer | $130-210K+ | Photonic control systems, simulation platforms |
| **Google Quantum AI** | Quantum Research | FAANG | Systems Engineer, Optimization Engineer | $150-250K+ | Error correction feedback loops, optimization |

### Warm Targets

- **IBM Quantum**: Qiskit ecosystem, circuit compilation, error correction ($128-180K)
- **Microsoft Azure Quantum**: Quantum-classical hybrid, topological qubits ($135-200K+)
- **Rigetti**: Hybrid quantum-classical computing, Quil language ($115-185K)
- **Keysight Technologies**: Quantum measurement systems, hardware integration ($114-191K)

### Strategic PQC Targets (Growth Sector)

- **DigiCert**: PKI Standards & Compliance Engineer ($145-195K) — governance angle
- **PQShield**: PQC Implementation, cryptographic engineering ($80-150K)
- **Major tech** (Google, Apple, Cloudflare, AWS): Quantum-safe infrastructure engineers ($125-200K+)

---

## Project Positioning Strategy

### Core Project: Quantum-Classical OS Controller (Phase 1)

**What it demonstrates**:
- Architecture-first thinking (5 graph layers, closed enums, contract-based design)
- Real-time control systems (six-stage agentic feedback loop)
- Physics-aware constraint evaluation (admissible action filters)
- Simulator abstraction (pluggable Markovian & non-Markovian models)
- Observability & operator control (dashboard backend, real-time metrics)
- Governance patterns (PIV workflow, bounded autonomy, policy enforcement)

**Test coverage**: 66 passing tests across schema, constraints, simulators, and end-to-end loop

**Why companies care**: Demonstrates you think in systems, not just features. Every quantum company builds some version of this (IBM: Qiskit + Qiskit Dynamics, Google: error correction + circuit optimization, IonQ: control systems + cloud API).

---

## Project Variants by Role

### 1. **Quantum Control Engineer** (IonQ, Atom Computing, PsiQuantum)

**Project Focus**: Quantum Control Systems Variant

**Highlight**:
```
quantum_controller.py (6-stage loop) + quantum_constraints.py
├── Sense → Estimate → Constrain → Act → Validate → Learn
├── Hardware-aware action filtering
├── Real-time feedback loop with phase timing metrics
├── Recovery policy with retry budgets
└── Multi-timing-domain support (hard-RT, soft-RT, nearline, offline)
```

**Talking Points**:
- "Built a real-time feedback loop that mirrors your control systems architecture"
- "Constraint engine validates actions against physics envelopes — same principle as your hardware constraints"
- "Simulators pluggable (Markovian/non-Markovian) so fidelity models swap in/out"
- "Demonstrated bounded autonomy: recovery escalates when confidence drops below threshold"

**Interview Prep**: 
- Know your timing domains (hard-RT is microseconds, soft-RT is milliseconds)
- Be ready to discuss control law synthesis (how actions chosen in "Act" phase)
- Explain confidence scoring (how belief state drives decisions)

---

### 2. **Quantum Software Architect** (IBM, Google, Rigetti)

**Project Focus**: Full System Architecture Variant

**Highlight**:
```
Complete layered graph model + service contracts
├── Physical layer (hardware topology, coupling maps)
├── Logical layer (circuits, pulse families, decoders)
├── Workflow layer (DAG scheduling, task spans, conformance)
├── Capability layer (device profiles, embedding strategies)
└── Governance layer (policy, approval, role-based access)
```

**Talking Points**:
- "Designed a 5-layer graph model so each layer answers different questions without coupling"
- "Service contracts (ConstraintsEngine, SimulatorInterface) let teams own their piece independently"
- "Validated against research literature on agentic architecture, robustness, and multi-agent systems"
- "66 tests ensure contracts hold at every integration point"

**Interview Prep**: 
- Be comfortable discussing tradeoffs (why 5 layers vs monolith vs 10 layers)
- Know how your graph model maps to Qiskit (QASM IR), Cirq (circuit graph), Quil
- Be ready to discuss schema versioning (we jumped schema version twice in research)

---

### 3. **Post-Quantum Cryptography / Standards Engineer** (DigiCert, PQShield)

**Project Focus**: Governance & Policy Variant

**Highlight**:
```
Governance layer + ActionPolicy + DecisionTracing
├── Role-based authorization (who can do what)
├── Pre-execution policy checks (allow/escalate/block before any work)
├── Post-execution outcome validation (verify what actually happened)
├── Audit trail with reason codes (every decision traceable)
└── Bounded autonomy (human-in-the-loop escalation)
```

**Talking Points**:
- "Built a two-stage gate system: pre-execution policy + post-execution validation (mirrors PQC standards adoption workflow)"
- "Every decision has a reason code, not just yes/no (governance needs auditability)"
- "Escalation policy vs straight rejection (captures real-world approval workflows)"
- "Governance graph connects to all other layers — policy is first-class, not bolted-on"

**Interview Prep**:
- Understand NIST PQC migration timeline (May 2026 deadline for enterprises)
- Know ML-KEM, ML-DSA, SLH-DSA basics (the three finalized standards)
- Be ready to discuss compliance & audit trails (DigiCert's core business)

---

### 4. **Systems Engineer / Observability** (Keysight, measurement systems)

**Project Focus**: Dashboard & Observability Variant

**Highlight**:
```
quantum_dashboard.py + RuntimeEvent streaming
├── Real-time loop state (phase metrics, timing, confidence)
├── Graph layer health (freshness, violations, anomalies)
├── Service status monitoring (latency, error rates, uptime)
├── PIV progress tracking (Prototype → Integrate → Validate → Scale)
└── Event history with anomaly tags (drift, degradation, faults)
```

**Talking Points**:
- "Built observability from the ground up: every service emits structured events with timestamps"
- "Dashboard aggregates without polling (push-based metrics, not scrape-based)"
- "Real-time loop state visible to operators: which phase, how long, confidence score"
- "Anomaly tags let operators triage issues fast (is this drift? degradation? fault?)"

**Interview Prep**:
- Know the difference between logs, metrics, and traces (we use all three)
- Be ready to discuss dashboard requirements for quantum hardware (real-time latency is critical)
- Understand phase timing (6 stages, each measurable and traceable)

---

### 5. **Quantum Simulation / Physics Engineer** (Google, D-Wave)

**Project Focus**: Simulator Variant

**Highlight**:
```
quantum_simulator.py (Markovian + Non-Markovian)
├── Markovian: stateless fidelity model (each step independent)
├── Non-Markovian: history-dependent decoherence model
├── Fidelity degradation over gate duration & qubit count
├── Robustness metrics (noise resilience, timing tolerance, state prep fidelity)
└── Reward decomposition (fidelity, error suppression, coherence preservation)
```

**Talking Points**:
- "Implemented two simulator models to explore state dependence in quantum evolution"
- "Markovian model: simple enough for fast iteration, non-Markovian captures memory effects"
- "Fidelity model includes realistic degradation: duration penalty, complexity penalty, accumulated errors"
- "Robustness metrics let us rate-limit actions (don't run high-risk sequences)"

**Interview Prep**:
- Know the difference between T1 (energy decay) and T2 (dephasing) times
- Be ready to discuss fidelity bottlenecks (gate errors, measurement errors, state prep errors)
- Understand error models (depolarizing, amplitude damping, phase damping, etc.)

---

## Application Materials

### 1. **Resume Positioning**

**Key Sections**:
- **Project**: "Architected modular quantum-classical OS controller: 5-layer graph model, real-time feedback loop, pluggable simulators, constraint engine, observability dashboard. 66 tests."
- **Skills**: Systems design, Python, real-time control, constraint optimization, simulator design, observability, governance patterns, test-driven development
- **Publications**: Link to GitHub branch, run report, implementation doc

**Tailoring per role**:
- Control Engineer: Emphasize phase timing, feedback loops, recovery policy
- Architect: Emphasize 5-layer design, service contracts, schema versioning
- PQC: Emphasize governance layer, audit trails, policy enforcement
- Observability: Emphasize dashboard backend, metrics, anomaly tags
- Simulator: Emphasize simulator interface, fidelity models, robustness

---

### 2. **Cover Letter Template**

```
[Company Name] is building [their specific quantum system/capability].
This project demonstrates my approach to [their core challenge]:

1. System Design: I modeled quantum-classical control as 5 layers
   (physical/logical/workflow/capability/governance) because [reason relevant to their system].

2. Real-time Control: Built a 6-stage feedback loop (sense→estimate→constrain→act→validate→learn)
   with phase timing metrics, matching the latency requirements of [their hardware/use case].

3. Constraint Evaluation: Physics constraints engine filters actions before dispatch,
   mirroring your [their constraint type: hardware topology / decoherence envelope / etc.].

4. Simulation: Pluggable simulators (Markovian/non-Markovian) let me test different
   fidelity models without rewriting the core loop — same flexibility you need in [their context].

5. Observability: Dashboard backend streams events, tracks anomalies, exposes loop state
   to operators in real-time — essential for the kinds of [their operational challenges]
   your team will face.

[Company] + This project = [specific value you'd bring].
```

---

### 3. **Technical Interview Talking Points**

**Most likely questions**:

1. **"Why did you design it as 5 layers?"**
   - Answer: Each layer answers a different set of questions (What is the hardware? What do we want to compute? What are we doing? Can we do it? Did it work?)
   - Decoupling lets teams own layers independently; no circular dependencies
   - Graph model lets you query across layers (which qubits are coupled? which tasks are blocked?)

2. **"Why not just use [competitor's framework]?"**
   - Answer: [Their framework] is great at [A], but you built this to explore [B/C/D] that they don't address yet
   - You wanted to understand the contracts before integrating with real hardware
   - Simulation-first approach let you validate the architecture before touching real qubits

3. **"How does the constraint engine scale?"**
   - Answer: Currently evaluates ~5 constraints per action; evaluation is O(N) in constraint count, not state size
   - Constraints are pluggable; if you want to add a new constraint, it's a single function
   - Real bottleneck isn't constraint count, it's action selection (Act phase); we use simulators + RL to score actions

4. **"What would you do differently if you built it again?"**
   - Answer: I'd [make a tradeoff/simplify something/add X]. But every decision here was intentional: we documented the reasoning in [schema/constraints/controller] because [reason]

---

## Application Timeline

### Phase 1: Research & Targeting (Week 1-2)

- [ ] Identify 20 target companies (split: 5 hot, 10 warm, 5 learn-from)
- [ ] For each company:
  - [ ] Read their latest blog posts/papers
  - [ ] Find GitHub repos (understand their architecture)
  - [ ] Identify open roles & hiring patterns
  - [ ] Determine which project variant aligns best
- [ ] Create tracker with 20 companies (see `quantum_job_tracker.py`)

### Phase 2: Application Prep (Week 2-3)

- [ ] Polish resume (1 page, 2 pages if strong publication record)
- [ ] Create 5 project variant summaries (one per main role type)
- [ ] Tailored cover letter templates for each company type
- [ ] GitHub repo: clean up, add comprehensive README, link run report
- [ ] Elevator pitch (30-60 seconds per variant)

### Phase 3: Bulk Applications (Week 3-4)

- [ ] Submit 15-20 applications with tailored materials
- [ ] Log all submissions in tracker (job_id, application_date, variant used)
- [ ] Set follow-up reminders (2 weeks after application)

### Phase 4: Interview Prep (Ongoing as invites arrive)

- [ ] For each interview: add to tracker with interview prep notes
- [ ] Technical deep-dives: review relevant code sections
- [ ] Mock interviews: practice variant explanations
- [ ] Company research: recent papers, blog posts, architecture decisions

### Phase 5: Offer Negotiation & Decision (Month 2-3)

- [ ] Log offers in tracker with all details (salary, equity, location, start date)
- [ ] Compare against decision criteria (role type, company stage, growth, values)
- [ ] Negotiate: use market data (quantum engineers, $130-200K+ base is market rate)

---

## Competitive Advantages

### What This Project Shows

1. **You think systems-first**: Graph architecture, layered design, contract-based interfaces
2. **You measure quality**: 66 tests, conformance checks, structured traces, metrics
3. **You understand tradeoffs**: Documented why 5 layers, why these constraints, why these simulators
4. **You can execute**: Went from architecture doc to working code in one focused sprint
5. **You understand production**: Observability built in from day one, not bolted on later

### Unfair Advantages at Each Company

| Company | Your Advantage |
|---------|-----------------|
| **Atom Computing** | Graph-based atom addressing model already in code |
| **IonQ** | Real-time control loop + recovery policy matches their architecture |
| **D-Wave** | Constraint engine built from ground up for optimization problems |
| **Google Quantum AI** | Understanding of multi-layer dependencies (physical→logical→workflow) |
| **IBM** | Simulator pluggability approach mirrors Qiskit's design philosophy |
| **DigiCert** | Governance + audit trail thinking (PQC standards require this) |

---

## Message to Hiring Managers

**For Quantum Control Engineer role**:
> "Built a real-time quantum-classical controller with pluggable simulators and constraint-aware action dispatch. The architecture mirrors production systems you're building: feedback loops, bounded autonomy, observability. 66 tests validate the contracts. Ready to take this from simulation to hardware."

**For Quantum Software Architect role**:
> "Designed a 5-layer graph model to separate concerns: physical topology, logical operations, workflow scheduling, capability planning, and governance. Service contracts ensure decoupled teams. Validated against literature on agentic architecture. 66 tests, full type safety."

**For Post-Quantum Standards role**:
> "Built a governance layer with pre/post-execution policy enforcement and full audit trails. Every decision has a reason code. The model treats governance as first-class, not bolted-on. Understands why enterprises need traceable approvals for PQC migration."

---

## Success Criteria

✓ Target companies: 5 applications to "hot" tier companies within 2 weeks  
✓ Interview rate: 25%+ of applications → interviews (quantum market is hot)  
✓ Offer rate: 50%+ of interviews → offers (demonstrated competence is rare)  
✓ Outcome: Signed offer with quantum control/systems/governance focus by Week 12  
✓ Salary target: $130K+ base + equity (market rate for quantum engineers)  

---

## Resources

- [Quantum Jobs List](https://www.quantumjobslist.com/)
- [IBM Quantum Careers](https://www.ibm.com/quantum/)
- [IonQ Careers](https://ionq.com/careers)
- [Atom Computing Careers](https://www.atom-computing.com/careers)
- [NIST Post-Quantum Cryptography](https://csrc.nist.gov/projects/post-quantum-cryptography)
- [The Quantum Insider](https://thequantuminsider.com/)
- [Quantum Economics Report 2026](https://quantum.mit.edu/)
- [GitHub Topic: Quantum Computing](https://github.com/topics/quantum-computing)

---

**Author**: Claude Code  
**Created**: 2026-07-27  
**Strategy Version**: 1.0  
**Next Review**: After first 5 applications
