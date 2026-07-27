# Architecture Track: 8-Role Positioning Guide

**Quick reference for customizing resume, cover letter, and interview prep for each role**

---

## 1. Google — Technical Lead, Software Technical Infrastructure
**Salary**: $207-301K | **Tier**: Enterprise WARM | **Apply**: Week 1-2

### Your Value
Google needs someone to architect quantum-safe infrastructure **at planet scale**. Your 5-layer model proves you think at that scale.

### Resume Keywords
- Systems architecture at scale
- Policy as code
- Governance layer design
- Audit trail architecture
- Multi-layer separation of concerns

### Cover Letter Angle
```
Google's infrastructure challenge: integrate quantum into classical systems 
without breaking existing platforms serving billions of users. My 5-layer model 
shows exactly how — separate governance from control, validate before 
execution, make every decision auditable.
```

### Interview Talking Point (30 min)
- Draw 5 layers on whiteboard
- Map to Google infrastructure: Classical cloud (workflow layer), quantum partners (physical layer), customer APIs (capability layer), PQC migration (governance layer)
- Walk through how layers don't couple: can swap quantum partner (physical) without rewriting job scheduler (workflow)
- Emphasize: governance layer makes quantum-safe deployment auditable for compliance

### Code to Reference
- `quantum_schema.py:100-150` — 5-layer model with explicit edge types
- `quantum_constraints.py:1-50` — pre-execution policy evaluation
- `quantum_dashboard.py:200-250` — audit trail tracking (every decision logged)

### Follow-up Questions to Ask
1. "How does Google currently think about layer separation in infrastructure?"
2. "What's your governance story for quantum integration?"
3. "How would you audit quantum operations for compliance?"

---

## 2. AWS — Technical Program Manager, Quantum Computing
**Salary**: $160-250K | **Tier**: Enterprise HOT | **Apply**: Week 1-2

### Your Value
AWS Braket needs to coordinate quantum hardware partnerships, cloud APIs, and enterprise customer adoption. Your architecture makes that coordination clear.

### Resume Keywords
- Technical program management
- Architecture design + coordination
- Hardware partnership strategy
- Cloud platform strategy
- Multi-team coordination

### Cover Letter Angle
```
Braket's bottleneck is architectural clarity: how do we layer classical-quantum 
without coupling? My 5-layer model answers this — separate cloud infrastructure, 
quantum control, job scheduling, device capability, and governance. Each layer 
has a clear interface. Hardware partners fit at the physical layer; cloud APIs 
at workflow; enterprise policy at governance.
```

### Interview Talking Point (45 min)
- 5-layer model as TPM tool: layers = independent teams + partnerships
- Map each layer to Braket component: AWS cloud (workflow), quantum hardware partners (physical), customer jobs (workflow), device metadata (capability), PQC compliance (governance)
- Show how layered architecture enables independent hardware partnerships (plug in IonQ, D-Wave, Atom at physical layer without rewriting APIs)
- Walk through 6-stage feedback loop as program coordination framework: Sense (hardware reports state) → Estimate (Braket infers device capabilities) → Constrain (validate customer job against device limits) → Act (schedule job) → Validate (collect results) → Learn (improve device model)

### Code to Reference
- `quantum_schema.py:150-200` — layer contracts (NodeType, EdgeType enums)
- `quantum_controller.py:1-60` — 6-stage orchestration loop (coordinates work)
- `quantum_dashboard.py:1-80` — observability architecture (cloud-ready event streaming)

### Follow-up Questions to Ask
1. "How does AWS currently model hardware partnerships?"
2. "What's your job scheduler doing today? What are the pain points?"
3. "How would you design a unified observability story for Braket + partners?"

---

## 3. Atom Computing — Principal Software Engineer
**Salary**: $180-220K | **Tier**: Startup HOT | **Apply**: Week 1-2

### Your Value
Atom is building neutral atom quantum computers. Your 6-stage feedback loop is their control system blueprint.

### Resume Keywords
- Principal systems engineer
- Real-time control systems
- Feedback loop design
- Physics constraint evaluation
- Hardware integration

### Cover Letter Angle
```
Neutral atom systems need real-time feedback on trap stability, ion temperature, 
and photon collection. My 6-stage loop handles exactly this: continuous sensing 
(trap state), Bayesian estimation (ion temperature), hard real-time constraints 
(bandwidth, coupling), deterministic actuation (pulse timing), validation (fidelity), 
and online learning (drift compensation).
```

### Interview Talking Point (60 min)
- Draw 6-stage loop on whiteboard: Sense → Estimate → Constrain → Act → Validate → Learn
- Map each stage to neutral atom control:
  - Sense: trap fluorescence photons, ion heating
  - Estimate: infer trap depth, ion temp from photon counts
  - Constrain: validate pulse timing against bandwidth limits, coupling ratios
  - Act: execute trap-changing pulses deterministically
  - Validate: measure final state, compare to expected
  - Learn: update trap model, ion mass, heating rate estimates
- Emphasize timing: Sense + Act <1ms (hard real-time), Estimate 1-10ms, Constrain nearline
- Walk through constraint engine: 5 checks (coupling, frequency, bandwidth, temperature, interference) as pluggable functions

### Code to Reference
- `quantum_controller.py:100-200` — 6-stage loop implementation
- `quantum_simulator.py:1-100` — fidelity degradation models (ion heating, spontaneous emission)
- `quantum_constraints.py:150-250` — physics constraints (coupling, frequency, bandwidth)

### Follow-up Questions to Ask
1. "What's your current control loop architecture? How do you handle feedback timing?"
2. "How do you model trap dynamics and ion heating?"
3. "How would you express constraints for trap optimization?"

---

## 4. AWS — Security Architect, Post-Quantum Cryptography
**Salary**: $150-230K | **Tier**: Enterprise HOT | **Apply**: Week 2-3

### Your Value
AWS needs to migrate infrastructure to PQC-safe cryptography. Your governance layer is the policy framework they need.

### Resume Keywords
- Security architecture
- Policy enforcement
- Compliance + audit trails
- Real-time validation
- Enterprise governance

### Cover Letter Angle
```
PQC migration at AWS scale means enforcing deployment policies across 1000+ systems. 
My governance layer shows how: define policy as code (pluggable constraint checks), 
validate every action pre-execution, log every decision for audit (immutable trail).
```

### Interview Talking Point (45 min)
- 5 constraint checks as PQC policy framework:
  - Coupling: FIPS compliance check
  - Frequency: NIST algorithm version check
  - Bandwidth: performance regression check
  - Temperature: deployment environment check
  - Interference: cryptographic interference (key sharing between algorithms)
- Walk through pre-execution validation: before any PQC algorithm runs, validate against all 5 checks
- Show audit trail: every deployment decision logged, immutable, queryable for compliance
- Connect to AWS security requirements: compliance audits need to see *why* each PQC deployment was approved

### Code to Reference
- `quantum_constraints.py:50-150` — pluggable policy checks (model as constraint functions)
- `quantum_controller.py:250-350` — validation gates + approval workflows
- `quantum_dashboard.py:200-250` — audit logging infrastructure

### Follow-up Questions to Ask
1. "How do you currently enforce PQC policies at deployment time?"
2. "What does your audit trail look like for compliance reviews?"
3. "How would you validate that a PQC deployment doesn't break existing security?"

---

## 5. IBM — Security Architect, Post-Quantum Standards
**Salary**: $150-230K | **Tier**: Enterprise HOT | **Apply**: Week 2-3

### Your Value
IBM leads NIST PQC standards work. Your governance layer is a reference implementation.

### Resume Keywords
- Security architecture
- Standards compliance
- Policy as code
- Enterprise PQC migration
- Audit trail design

### Cover Letter Angle
```
IBM's NIST PQC role needs to show enterprises how to migrate cryptographically. 
My governance layer demonstrates: policy-driven validation (pre/post-execution), 
immutable audit trails, deterministic go/no-go decisions — exactly NIST 
compliance requires.
```

### Interview Talking Point (45 min)
- Governance layer as NIST compliance reference architecture:
  - Policy layer (NIST algorithm selection)
  - Validation layer (FIPS compliance checks)
  - Audit layer (deployment trail for compliance audits)
- Walk through constraint checks as NIST requirements:
  - Algorithm check (NIST PQC standardized algorithm?)
  - Interoperability check (mixing algorithms safe?)
  - Performance check (meets service level?)
  - Environment check (approved deployment location?)
- Show how every deployment decision is justified + auditable
- Connect to IBM's standards role: enterprises need to trust the framework

### Code to Reference
- `quantum_constraints.py:1-100` — validation framework (generalizes to NIST checks)
- `quantum_dashboard.py:200-350` — audit logging (immutable trail)
- `quantum_controller.py:250-350` — validation gates (explicit approval checkpoints)

### Follow-up Questions to Ask
1. "How should enterprises validate NIST PQC compliance?"
2. "What should an audit trail look like for cryptographic migrations?"
3. "How do you prevent accidental key sharing between PQC algorithms?"

---

## 6. IBM — Quantum Software Engineer, Qiskit
**Salary**: $140-210K | **Tier**: Enterprise HOT | **Apply**: Week 3-4

### Your Value
Qiskit's architecture challenge is composable layers (IR → transpiler → scheduler → device). Your 5-layer model extends that thinking.

### Resume Keywords
- Quantum software architecture
- Layer-based design
- Cross-team contracts
- Distributed circuit compilation
- Real-time scheduling

### Cover Letter Angle
```
Qiskit's strength is layer separation: QASM IR, circuit layer, transpiler, 
scheduler. My 5-layer model extends that: add workflow layer (job scheduling), 
capability layer (device properties), governance layer (PQC policy). Each layer 
can evolve independently; teams own one layer without touching others.
```

### Interview Talking Point (50 min)
- Map Qiskit layers to 5-layer model:
  - Logical layer: QASM IR + circuit optimization (Qiskit Terra)
  - Physical layer: device topology + calibration (Qiskit Aer, real devices)
  - Workflow layer: job scheduling + resource allocation (Qiskit Runtime)
  - Capability layer: device properties + metadata (Qiskit properties)
  - Governance layer: PQC policy + compliance (new layer for IBM)
- Show how layers enable independent teams: Terra team rewrites IR without touching Runtime scheduler
- Walk through contract between layers: Physical layer reports capabilities, Logical layer reads them, Workflow schedules accordingly
- Discuss challenges: today Qiskit doesn't have explicit Governance layer — that's an opportunity

### Code to Reference
- `quantum_schema.py:50-150` — graph node/edge types (model as Qiskit layer contracts)
- `quantum_controller.py:50-100` — workflow orchestration (maps to Qiskit Runtime)
- `quantum_constraints.py:1-50` — capability validation (maps to device properties)

### Follow-up Questions to Ask
1. "How does Qiskit currently handle device property changes?"
2. "What's the contract between Terra and Runtime?"
3. "How would you add PQC governance to Qiskit?"

---

## 7. IonQ — Senior Software Engineer, Quantum Networking
**Salary**: $140-200K | **Tier**: Startup HOT | **Apply**: Week 3-4

### Your Value
IonQ's quantum networking challenge is coordinating distributed quantum devices. Your graph model handles networked systems.

### Resume Keywords
- Distributed systems architecture
- Quantum networking
- Device coordination
- Workflow-layer routing
- Federated capability reporting

### Cover Letter Angle
```
Quantum networks need to coordinate across devices with different capabilities 
and timing domains. My 5-layer graph model works for 1 device or 100: separate 
concerns (physical, logical, workflow, capability, governance) so networking 
middleware only needs to know workflow + capability layers.
```

### Interview Talking Point (50 min)
- Distributed architecture design:
  - Each device has own 5-layer graph
  - Networking happens at Workflow layer (job routing)
  - Capability layer is federated (devices report capabilities)
  - Governance layer is network-enforced (policy checks before routing)
- Walk through routing algorithm: 
  - Job arrives at network controller
  - Workflow layer routes to device (based on capability + latency)
  - Device receives job in own local 5-layer graph
  - Device executes job (Logical, Physical layers local)
  - Device returns results to controller
- Show how physical-level coupling is avoided: no qubit-level networking, only workflow-level
- Emphasize scalability: device count doesn't affect control loop complexity

### Code to Reference
- `quantum_schema.py:50-150` — node/edge types for distributed graphs
- `quantum_controller.py:350-450` — timing domain coordination (maps to device latencies)
- `quantum_dashboard.py` — federated observability (per-device state reporting)

### Follow-up Questions to Ask
1. "How do you currently handle routing across IonQ devices?"
2. "What's your capability reporting model?"
3. "How do you handle device failures in the network?"

---

## 8. PsiQuantum — Staff Hardware Design Engineer
**Salary**: $155-180K | **Tier**: Startup HOT | **Apply**: Week 4-5

### Your Value
PsiQuantum designs photonic quantum computers. Your constraint engine models hardware limits precisely.

### Resume Keywords
- Hardware-software co-design
- Constraint-driven architecture
- Physics-aware scheduling
- Photonic systems
- Real-time resource management

### Cover Letter Angle
```
Photonic systems are constraint-limited: wavelength separation, coupling ratios, 
thermal stability, detector efficiency. My constraint engine shows how to express 
these as pluggable checks (O(N) in constraint count) and make deterministic 
go/no-go decisions in real-time without rewiring control logic.
```

### Interview Talking Point (60 min)
- Constraint engine for photonics:
  - Coupling check: wavelength separation (avoid crosstalk)
  - Frequency check: resonator alignment (frequency matching)
  - Bandwidth check: modulator speed (phase modulation rate)
  - Temperature check: thermal stability (wavelength drift with temperature)
  - Interference check: photon interference (indistinguishability for entanglement)
- Walk through action validation for photonic system:
  - Operation requested (e.g., 2-photon entanglement between waveguides 3, 5)
  - Constraint check 1: wavelength separation sufficient? (avoid crosstalk)
  - Constraint check 2: resonators aligned? (frequency matching)
  - Constraint check 3: modulators fast enough? (phase control bandwidth)
  - Constraint check 4: temperature stable? (no wavelength drift during operation)
  - Constraint check 5: indistinguishability known? (interference visibility)
  - If all pass: execute deterministically
  - If any fail: reject with reason
- Emphasize: adding support for new photonic component = add 1-2 constraint checks, not rewrite loop

### Code to Reference
- `quantum_constraints.py:100-300` — 5 pluggable constraint checks (generalizes to photonic)
- `quantum_controller.py:200-250` — confidence-driven decisions (maps to photonic fidelity)
- `quantum_simulator.py:300-400` — fidelity degradation (maps to photonic loss, distinguishability)

### Follow-up Questions to Ask
1. "How do you currently model photonic system constraints?"
2. "What's your approach to temperature-dependent wavelength drift?"
3. "How would you validate indistinguishability in a real system?"

---

## Resume Sections by Role Type

### For Enterprise Roles (Google, AWS TPM, Security Architects)
```
TECHNICAL LEADERSHIP
- Designed 5-layer information architecture enabling independent team ownership
- Led multi-team governance framework (pre/post-execution policy, audit trails)
- Coordinated hardware-software integration across 4 teams without circular dependencies
```

### For Principal/Staff Roles (Atom, PsiQuantum)
```
SYSTEMS DESIGN
- Architected 6-stage real-time feedback loop for deterministic quantum control
- Designed physics-driven constraint engine (5 pluggable checks, O(N) performance)
- Engineered timing domain separation (hard-RT <1ms, soft-RT 1-10ms, nearline, offline)
```

### For Distributed/Networking Roles (Qiskit, IonQ)
```
DISTRIBUTED SYSTEMS ARCHITECTURE
- Designed layered graph model scaling from single device to distributed networks
- Architected federated capability reporting (per-device state + network-wide policy)
- Implemented layer contracts enabling independent evolution (no circular dependencies)
```

---

## Quick Decision Tree: Which Talking Point to Lead With?

**If asked "Tell me about your work"**:
- Google, AWS: Start with 5-layer model (architecture at scale)
- Atom, PsiQuantum: Start with 6-stage loop (real-time control)
- Security architects: Start with governance layer (policy architecture)
- Qiskit, IonQ: Start with layer separation (independent teams)

**If asked "How would you approach [specific problem]"**:
- Google: "I think in layers. First, separate concerns..."
- AWS TPM: "I'd model this as 5 independent layers that can evolve separately..."
- Atom: "I'd design a feedback loop. Here's the 6 stages..."
- Security: "I'd make governance a separate layer with pre/post-execution validation..."
- Qiskit: "Each team should own one layer. Here's the contract between layers..."
- IonQ: "For distributed systems, keep physical local and route at workflow level..."
- PsiQuantum: "Physics constrains the design. Here are the 5 hardware constraints..."

---

## Cover Letter Template (Customize Company Name / Role)

```
Dear [Company] [Role] hiring team,

I'm applying for the [Role Title] position. My Phase 1 project demonstrates 
the [SPECIFIC SKILL] your team needs.

YOUR CHALLENGE:
[Specific challenge from job description]

MY APPROACH:
[How your architecture solves it]

WHY I'M DIFFERENT:
- I've designed and tested this architecture (66 tests, closed enums, type safety)
- I understand [DOMAIN] constraints (physics, real-time, hardware-software co-design)
- I've coordinated [SPECIFIC PROBLEM] (layer separation, distributed systems, governance)

THE PROOF:
[Reference 2-3 code sections]

I'm ready to discuss how this architecture accelerates your [SPECIFIC GOAL].

Best,
[Your name]
```

---

## Interview Prep Checklist (Before Each Interview)

- [ ] **Understand the company's current architecture** (read tech blog, GitHub, job description)
- [ ] **Identify their pain point** (what problem does this role solve?)
- [ ] **Map your 5-layer model** (how does your architecture solve their pain point?)
- [ ] **Prepare 3 follow-up questions** (shows you've thought deeply)
- [ ] **Practice 5-layer drawing** (whiteboard sketch it cleanly in <2 min)
- [ ] **Prepare 1-2 code references** (know line numbers, be ready to explain)
- [ ] **Time your talking points** (30-45 min = tell story without over-talking)

---

## Post-Interview Template (Take Notes)

```
[Company] - [Role] - [Interviewer Name]

Their Challenge:
[What did they describe?]

My Fit:
[Which part of 5-layer model / 6-stage loop did they engage with?]

Strong Points:
[What did they ask follow-ups on?]

Weak Points:
[What did they push back on?]

Next Steps:
[Next interview? Timeline?]

Confidence Level:
[1-10]
```

---

**Key to Architecture Track Success**: You're not selling engineering experience. You're selling architectural thinking. Lead every conversation with layers, contracts, and team separation. That's what separates architects from engineers at this level.
