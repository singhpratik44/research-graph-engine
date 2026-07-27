# Quantum-Classical OS Controller: Project Variants for Job Applications

This document provides role-specific positioning for the Phase 1 quantum-classical OS controller implementation. Each variant highlights different competencies and architecture aspects relevant to specific quantum computing roles.

**Project Foundation**: 5-layer graph model, 6-stage feedback loop, physics constraint engine, pluggable simulators, observability dashboard, 66 passing tests.

---

## 1. Quantum Control Engineer Variant

**Target Companies**: IonQ, Atom Computing, PsiQuantum, Google Quantum AI

**Core Message**: "Built a real-time quantum-classical feedback loop with hardware-aware action filtering and recovery policies, demonstrating production control system architecture."

### Key Competencies Demonstrated

1. **Real-Time Feedback Loop** (quantum_controller.py, lines 115-171)
   - Six-stage agentic loop: Sense → Estimate → Constrain → Act → Validate → Learn
   - Timing domains explicitly modeled (hard-RT < 1ms, soft-RT 1-10ms, nearline 10-100ms, offline 100+ms)
   - LoopPhaseMetrics tracking phase duration and confidence at microsecond resolution

2. **Physics-Aware Constraint Evaluation** (quantum_constraints.py)
   - Five constraint checks: coupling topology, frequency separation, bandwidth limits, temperature envelopes, interference risk
   - ControlAction dataclass specifies: pulse family, target qubits, duration_ns, amplitude_normalized, phase degrees
   - ActionEnvelope returns is_admissible flag + confidence level + recommended_retries + fallback_actions

3. **Bounded Autonomy & Recovery** (quantum_controller.py, lines 57-64)
   - RecoveryPolicy with max_retry_budget, escalation_threshold (confidence-based), approval_required_for_critical
   - Escalation when confidence drops below threshold (default 0.5)
   - Three recovery strategies: conservative, balanced, aggressive

4. **Confidence-Driven Decision Making** (quantum_schema.py, quantum_controller.py)
   - ConfidenceLevel enum (CRITICAL, HIGH, MODERATE, LOW, UNCERTAIN) mapped to numeric scores
   - Belief state with confidence float (0.0-1.0) and uncertainty_estimate
   - Actions filtered based on envelope confidence before execution

### Interview Talking Points

**"Why did you build this?"**
- Control systems at quantum companies operate in closed loops: measure → estimate state → filter admissible actions → dispatch → validate outcome → learn.
- I wanted to understand the contracts between sensing, action selection, and validation before touching real hardware.

**"How does the constraint engine scale?"**
- Currently evaluates ~5 constraints per action in O(N) time (N = constraint count, not state size).
- Constraints are pluggable: adding a new constraint is one function, no core loop changes.
- The real scaling bottleneck is action selection in the Act phase, which we address via simulators + confidence scoring.

**"What would you change if you built it again?"**
- I'd make the timing-domain model even more explicit: hard-RT paths should be provably non-blocking, validated by static analysis.
- The current simulator fidelity model is simplified; production needs a real quantum solver.
- Recovery escalation logic could use RL instead of fixed thresholds.

### Code References for Interview

- **Real-time loop structure**: quantum_controller.py:115-171 (run_one_iteration with six stages)
- **Constraint filtering**: quantum_constraints.py:160-200 (evaluate_action method)
- **Recovery policy**: quantum_controller.py:57-64 (RecoveryPolicy dataclass)
- **Confidence scoring**: quantum_controller.py:292-300 (mapping ConfidenceLevel to numeric values)
- **Test validation**: test_quantum_controller.py:18 tests covering all six stages + state consistency

---

## 2. Quantum Software Architect Variant

**Target Companies**: IBM, Google Quantum AI, Microsoft Azure Quantum, Rigetti

**Core Message**: "Designed a 5-layer graph architecture that decouples concerns so teams can own layers independently, with full type safety and 66 passing tests."

### Key Competencies Demonstrated

1. **Layered Graph Architecture** (quantum_schema.py, lines 50-120)
   ```
   Physical Layer:  Hardware topology, qubits, resonators, coupling maps
   Logical Layer:   Circuits, gates, pulse families, decoders
   Workflow Layer:  Tasks, retries, approvals, conformance checks
   Capability Layer: Device profiles, embedding strategies, workload histories
   Governance Layer: Policies, roles, approval workflows, audit trails
   ```
   - Each layer answers different questions without circular dependencies
   - Graph-based queries bridge layers (e.g., "which qubits are coupled? which tasks are blocked?")
   - NodeType closed enum (10 base types), EdgeType closed enum (25+ types)

2. **Service Contracts & Pluggability** (quantum_simulator.py, quantum_constraints.py, quantum_dashboard.py)
   - SimulatorInterface abstract base class enables swappable implementations
   - ConstraintsEngine accepts pluggable constraint functions
   - DashboardBackend with FastAPI skeleton for operator interfaces
   - Each service has well-defined input/output contracts (Dataclasses with type hints)

3. **Schema Versioning & Evolution** (quantum_schema.py)
   - Closed enums prevent runtime surprises from invalid state
   - GraphMetrics with metrics tracking (freshness, constraint_violations, confidence)
   - Validation functions (validate_node, validate_edge) return Tuple[bool, List[ValidationError]]
   - Schema extensible via adding NodeType/EdgeType members (backward-compatible if done via enum addition)

4. **Type Safety & Testability** (all modules, 66 tests)
   - Full type annotations on all public methods
   - Dataclasses with field defaults where appropriate
   - Tests verify schema contracts, gate behavior, worker integration, end-to-end loop

### Interview Talking Points

**"Why 5 layers instead of monolith vs. 10 layers?"**
- Five answers a complete set of orthogonal questions: What is the hardware? What do we compute? What are we doing? Can we do it? Did it work?
- Decoupling lets teams own layers independently; circular dependencies emerge with too many layers.
- Fewer layers means more cross-layer queries, but that's acceptable since queries are read-only.

**"How does this map to [Qiskit / Cirq / Quil]?"**
- Physical layer ↔ Qiskit's QASM IR coupling maps, Cirq's device topology
- Logical layer ↔ Qiskit's gate set / pulse schedules, Cirq's circuit graph
- Workflow layer ↔ Qiskit's job scheduling, compiler optimizations
- Capability layer ↔ Qiskit's transpiler embedding strategies
- Governance layer (new) ↔ multi-tenant restrictions, approval workflows

**"How did you validate this architecture?"**
- Literature review: read 10+ papers on agentic architecture, robustness, and multi-agent systems.
- Conformance tests: 18 tests in test_quantum_schema.py verify node/edge invariants.
- Integration tests: 18 tests in test_quantum_controller.py validate all 5 layers work together.

### Code References for Interview

- **Layered model**: quantum_schema.py:50-120 (NodeType/EdgeType definitions + QuantumGraph class)
- **Service contracts**: quantum_simulator.py:80-120 (SimulatorInterface abstract base), quantum_constraints.py:1-50 (ConstraintsEngine)
- **Schema validation**: test_quantum_schema.py:18 tests covering node/edge validation, graph operations
- **Integration**: test_quantum_controller.py:18 tests validating all 6 phases + state consistency

---

## 3. Post-Quantum Cryptography / Standards Engineer Variant

**Target Companies**: DigiCert, PQShield, Google (crypto team), Apple, AWS, Cloudflare

**Core Message**: "Built a governance layer with pre/post-execution policy enforcement and full audit trails, demonstrating policy-first system design."

### Key Competencies Demonstrated

1. **Governance as First-Class Layer** (quantum_schema.py, quantum_dashboard.py)
   - Policy and governance nodes explicitly part of graph (not bolted on after design)
   - PolicyNode type with role-based authorization (who can do what)
   - Audit trail with reason codes for every decision (traceable, not just yes/no)

2. **Pre-Execution Policy Checks** (quantum_constraints.py, quantum_controller.py:_stage_constrain)
   - ActionPolicy-like checks before any work executes
   - Decision envelope with allow/escalate/block outcomes
   - Approval required for critical actions (RecoveryPolicy.approval_required_for_critical)
   - Escalation thresholds: if confidence < 0.5, escalate to human (don't silently retry)

3. **Post-Execution Validation & Conformance** (quantum_controller.py:_stage_validate)
   - Outcome validation against policy thresholds
   - Confidence-based gating (simulation fidelity > 0.85 required)
   - Admissibility check from constraint engine before any result enters graph
   - Failed validations produce structured ValidationError with reason codes

4. **Audit Trail & Traceability** (quantum_schema.py:RuntimeEvent, quantum_dashboard.py)
   - RuntimeEvent records phase, timing_domain, node_id, event_type, message, metadata, confidence, freshness
   - Event history with anomaly tags (DRIFT, DEGRADATION, FAULT)
   - DashboardBackend.event_history for operator review
   - Structured traces enable post-mortem analysis (who approved? what was the confidence? which policy rule applied?)

### Interview Talking Points

**"PQC migration is about traceability. How does this help?"**
- NIST migration deadline (May 2026) requires enterprises to demonstrate controlled crypto transitions.
- Every decision (which algorithm? which key length? when to rotate?) must be auditable.
- This governance layer makes policy-enforcement visible: operator can query "why was action X escalated?" and get a complete reason trail.

**"How would you extend this for enterprise deployment?"**
- Add multi-tenant policy: different departments have different approval thresholds.
- Add audit log export: governance decisions queryable by compliance auditors.
- Add policy versioning: crypto standards change (ML-KEM finalized May 2024, SLH-DSA June 2024), so policies need version tracking.
- Add role-based access: policy enforcement can differ by job classification (e.g., cryptographers can modify algorithms, operators can only execute approved policies).

**"What does this teach about real-world approvals?"**
- Enterprise approval workflows aren't just yes/no; they escalate.
- If confidence is low, escalate to a human expert (not automatic rejection).
- Automated tools can handle high-confidence cases fast; ambiguous cases get expert review.
- Audit trail matters more than approval speed.

### Code References for Interview

- **Governance graph model**: quantum_schema.py:NodeType (includes POLICY), quantum_dashboard.py:PIVStageStatus (policy stages)
- **Pre-execution policy**: quantum_constraints.py:200-240 (constraint evaluation returning admissible flag)
- **Post-execution validation**: quantum_controller.py:311-363 (_stage_validate method)
- **Escalation logic**: quantum_controller.py:57-64 (RecoveryPolicy with escalation_threshold)
- **Audit trail**: quantum_schema.py:RuntimeEvent dataclass with event_type, message, metadata
- **Test coverage**: test_quantum_controller.py covering constrain + validate stages

---

## 4. Systems Engineer / Observability Variant

**Target Companies**: Keysight, Honeycomb, DataDog, major cloud providers (Google Cloud, AWS, Azure)

**Core Message**: "Built observability from day one: real-time loop state streaming, graph health metrics, structured events with anomaly tags."

### Key Competencies Demonstrated

1. **Structured Event Streaming** (quantum_schema.py:RuntimeEvent, quantum_dashboard.py)
   - RuntimeEvent with timestamp, phase, timing_domain, node_id, event_type, message, metadata
   - Events pushed to DashboardBackend (not scraped via polling)
   - Event history queryable by phase, timing domain, event type
   - Confidence and freshness tags on every event

2. **Real-Time Loop State Observability** (quantum_dashboard.py, quantum_controller.py)
   - LoopStateSnapshot captures current phase, phase_duration_ms, phase_confidence
   - total_loop_time_ms visible to operators
   - phases[] array with per-phase metrics (duration, confidence, anomalies)
   - last_action_id and last_action_confidence visible in real-time

3. **Graph Layer Health Metrics** (quantum_dashboard.py:GraphLayerSummary)
   - Per-layer node/edge counts
   - node_types and edge_types histograms (what types are in this layer?)
   - freshness (FRESH, STALE, INVALID) — is this layer current?
   - constraint_violations count (how many constraints failed in this layer?)
   - confidence aggregate (0.0-1.0 per layer)

4. **Anomaly Detection & Tagging** (quantum_schema.py:AnomalyTag enum)
   - AnomalyTag.DRIFT: slow parameter degradation
   - AnomalyTag.DEGRADATION: sudden fidelity drop
   - AnomalyTag.FAULT: hard failure
   - Anomalies recorded on RuntimeEvent and LoopPhaseMetrics
   - Operators can triage: is this drift? degradation? fault?

### Interview Talking Points

**"Real-time observability for quantum hardware is different from traditional systems. What makes this approach fit?"**
- Quantum gates take nanoseconds. Measurement takes microseconds. A control loop iteration is milliseconds.
- We can't afford traditional polling-based scraping (one poll cycle might miss multiple loop iterations).
- Push-based events (controller emits, dashboard receives) keeps latency deterministic.
- Anomaly tags let operators distinguish "expected degradation over 1 hour" (drift) from "sudden fidelity drop" (fault).

**"How does this scale to 1000 qubits?"**
- Event volume grows with loop iteration rate (10x faster loop = 10x more events), not qubit count.
- Per-layer metrics aggregate, not per-qubit: we report "Physical layer: 1000 qubits, 5000 coupling edges, confidence 0.92", not per-qubit state.
- Anomaly detection is at the layer level (freshness, constraint violations) not per-qubit.

**"What's the operator's workflow with this dashboard?"**
1. See loop state: which phase? how long? confidence dropping?
2. Check recent events: any anomaly tags? any escalations?
3. Drill into graph layers: which layer had constraint violations? which node types are stale?
4. Decide: is this expected degradation (keep running) or a fault (stop)?

### Code References for Interview

- **Event emission**: quantum_controller.py:398-423 (_emit_event method)
- **Loop state snapshots**: quantum_dashboard.py:80-120 (LoopStateSnapshot dataclass)
- **Graph layer metrics**: quantum_dashboard.py:140-180 (GraphLayerSummary dataclass)
- **Anomaly tagging**: quantum_schema.py:AnomalyTag enum
- **Dashboard backend**: quantum_dashboard.py:DashboardBackend class with event_history, loop_state tracking
- **Real-time update**: quantum_controller.py:425-438 (_update_dashboard method)
- **Test coverage**: test_quantum_controller.py:18 tests including event emission validation

---

## 5. Quantum Simulation / Physics Engineer Variant

**Target Companies**: Google Quantum AI, D-Wave, University of Waterloo, academic quantum labs

**Core Message**: "Implemented two simulator models (Markovian and non-Markovian) with fidelity degradation models and robustness metrics."

### Key Competencies Demonstrated

1. **Markovian Simulator** (quantum_simulator.py:150-300)
   - Stateless model: each gate independent
   - Fidelity degrades with gate duration and complexity
   - Formula: `base_fidelity = 0.99 - (duration_ns / 10000) * 0.02 - (complexity_factor * 0.05)`
   - Simplest model for fast iteration; assumes no memory effects

2. **Non-Markovian / Trajectory Simulator** (quantum_simulator.py:350-500)
   - History-dependent model: accumulated errors reduce future fidelity
   - Cumulative error grows with each step: `cumulative_error = sum(step_errors) + memory_factor`
   - Captures decoherence memory effects
   - Confidence increases with trajectory length (longer history = more data)

3. **Fidelity Degradation Models** (quantum_simulator.py)
   - Duration penalty: longer gates lose coherence
   - Complexity penalty: multi-qubit gates harder than single-qubit
   - Accumulated error: cascade effects over sequence
   - Realistic constraints: state prep, measurement, and gate-specific errors

4. **Robustness Metrics** (quantum_simulator.py:RobustnessMetrics)
   - noise_resilience: how much noise does action tolerate?
   - timing_tolerance_ns: how sensitive to timing variations?
   - frequency_tolerance_mhz: how sensitive to frequency drift?
   - state_prep_fidelity: initialization quality
   - measurement_fidelity: readout quality

5. **Reward Decomposition** (quantum_simulator.py:RewardComponent enum)
   - FIDELITY: gate quality
   - GATE_SPEED: execution time
   - ERROR_SUPPRESSION: noise rejection
   - RESOURCE_EFFICIENCY: hardware utilization
   - COHERENCE_PRESERVATION: T2 time management

### Interview Talking Points

**"Why implement both Markovian and non-Markovian models?"**
- Markovian (simple, fast) lets us test control strategy iteration quickly.
- Non-Markovian (realistic) captures real quantum behavior: memory effects, cascading errors.
- Both pluggable via SimulatorInterface; swapping implementations doesn't change feedback loop.

**"How does your fidelity model compare to real hardware?"**
- Simplified; production needs a real quantum solver (Qiskit's Aer + noise models, or similar).
- Duration degradation (100ns gate ≈ 0.99 fidelity, 1μs gate ≈ 0.97 fidelity) is realistic for superconducting qubits.
- Complexity penalty (two-qubit gates ≈ 10x higher error) matches literature.
- Missing: crosstalk between gates on adjacent qubits, drift of gate parameters, temperature effects.

**"How would you refine this for production?"**
- Integrate a real noise model: depolarizing, amplitude damping, dephasing (T1, T2 times from hardware characterization).
- Add gate-specific error rates: calibration data from hardware vendor.
- Extend to multi-qubit error models: how do errors on q0 affect q1 if they're coupled?
- Include measurement error model: readout fidelity per qubit (often 95-99%).

**"What insights did robustness metrics reveal?"**
- Actions with high noise_resilience tolerate manufacturing variations in hardware (frequency drift, timing jitter).
- Long-sequence actions need high timing_tolerance; one late gate cascades to all following gates.
- State prep and measurement are often bottlenecks (95-98% fidelity each) — two-qubit operations need < 99% fidelity each to break even.

### Code References for Interview

- **Markovian model**: quantum_simulator.py:150-300 (MMarkovianSimulator class)
- **Non-Markovian model**: quantum_simulator.py:350-500 (TrajectorySimulator class)
- **Fidelity calculation**: quantum_simulator.py:180-250 (simulator run_trajectory logic)
- **Robustness metrics**: quantum_simulator.py:40-80 (RobustnessMetrics dataclass)
- **Reward components**: quantum_simulator.py:RewardComponent enum
- **Test validation**: test_quantum_simulator.py:17 tests covering both simulators, fidelity degradation, robustness metrics
- **Trajectory result**: quantum_simulator.py:TrajectoryResult dataclass with full metrics

---

## How to Use These Variants

### For IonQ / Quantum Control Engineer Role
- Start with Variant 1 (Quantum Control Engineer)
- Emphasize: real-time feedback loop, confidence-driven decision making, recovery escalation
- Interview prep: know timing domains, be ready to discuss control law synthesis

### For IBM / Quantum Software Architect Role
- Start with Variant 2 (Quantum Software Architect)
- Emphasize: 5-layer graph model, service contracts, schema versioning
- Interview prep: know how layers map to Qiskit, discuss tradeoffs in design

### For DigiCert / PQC Standards Role
- Start with Variant 3 (Post-Quantum Cryptography Engineer)
- Emphasize: governance layer, policy enforcement, audit trails
- Interview prep: understand NIST PQC timeline, discuss compliance auditing

### For Keysight / Observability Role
- Start with Variant 4 (Systems Engineer/Observability)
- Emphasize: structured events, real-time metrics, anomaly detection
- Interview prep: know difference between logs/metrics/traces, discuss dashboard design

### For Google Quantum AI / Simulation Role
- Start with Variant 5 (Quantum Simulation/Physics Engineer)
- Emphasize: pluggable simulators, fidelity models, robustness metrics
- Interview prep: know T1/T2 times, discuss error models, understand quantum noise

### General Application Template

When applying to a role:

1. **Opening sentence**: "I built a quantum-classical OS controller that demonstrates [variant-specific competency]."

2. **Proof**: Link to GitHub branch, point to the specific code modules (e.g., "6-stage feedback loop in quantum_controller.py" or "5-layer graph model in quantum_schema.py").

3. **Scale**: "66 passing tests validate the architecture across schema validation, constraint evaluation, simulator integration, and end-to-end loop execution."

4. **Relevance**: Explain how the variant aligns with the job description (e.g., "IonQ's control systems architecture mirrors this loop; D-Wave's constraint optimization matches this engine").

5. **Next step**: Offer to discuss the architecture in a technical interview, with concrete talking points from the relevant variant section above.
