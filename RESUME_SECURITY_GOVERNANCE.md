# Resume: Security Architect — Governance & Compliance

**Name: [Your Name]**  
**Email: [your.email@domain.com]** | **GitHub: github.com/[username]** | **LinkedIn: linkedin.com/in/[username]**

---

## PROFESSIONAL SUMMARY

Security architect with expertise in governance layer design, policy-as-code frameworks, and compliance-ready system architecture. Proven ability to design governance as a first-class architectural layer, not bolted-on compliance checker. Demonstrated success implementing pre/post-execution validation, immutable audit trails, and approval workflows. Skilled at translating compliance requirements (NIST, FIPS, enterprise standards) into architecture patterns. Seeking roles architecting quantum-safe infrastructure migration or post-quantum cryptography standards adoption at enterprise scale.

---

## EXPERIENCE

### Quantum-Classical OS Controller — Governance & Policy Architecture (2026)

**Project**: Enterprise quantum control platform with governance layer, policy-as-code framework, and compliance-ready audit trails.

**Governance Layer Architecture**:
- **Governance as first-class layer** in 5-layer model; not a cross-cutting concern scattered through codebase
- **Governance layer responsibilities**:
  - Define policies (which operations are allowed, which require approval, which are forbidden)
  - Pre-execution validation (check action against all policies before execution)
  - Post-execution audit (log decision outcome and reason for compliance verification)
  - Escalation workflows (route to humans when policy evaluation is ambiguous)
  - Reason codes (make every decision traceable and explainable)
- **Layer isolation**: Governance layer independent of Physical/Logical/Workflow/Capability layers; can evolve without rewiring control systems
- **Federated enforcement**: all teams respect governance decisions uniformly; no exceptions or workarounds

**Policy-as-Code Framework**:
- **Pluggable constraint checks** model policies as functions: `is_policy_compliant(action, state) → (admissible, violations, reason_codes)`
- **5 policy check types** (generalizable to any compliance framework):
  - Compliance check: does action meet standards requirements? (e.g., NIST PQC, FIPS cryptography)
  - Interoperability check: does action avoid conflicts with other policies? (e.g., key mixing between algorithms)
  - Performance check: does action meet service level objectives? (e.g., latency, throughput)
  - Environment check: is deployment location approved? (e.g., FedRAMP, government data center)
  - Risk check: does action introduce unacceptable risk? (e.g., cryptographic agility, key escrow)
- **Adding new policy**: add one constraint check function; no architecture rewrites
- **Validation output**: (is_admissible, violations list, recommended actions, reason_codes)
- **Performance**: O(N) in policy count; evaluation bounded regardless of system state size

**Pre-Execution Validation**:
- **Every action checked before execution**: action either passes all policy checks or is rejected with reason
- **Clear decision flow**: 
  1. Action requested (e.g., "execute PQC algorithm X on key material Y")
  2. Call `validate_against_policies(action, state)` 
  3. If all checks pass → execute deterministically
  4. If any check fails → reject with reason code (e.g., "ALGORITHM_NOT_NIST_APPROVED", "KEY_MIXING_RISK")
- **No ambiguity**: policy decision is binary (admissible yes/no), not advisory
- **Escalation path**: if confidence in policy decision is low, escalate to human operator

**Post-Execution Audit Trail**:
- **Immutable audit log**: every policy decision logged immediately
- **Log entry structure**: timestamp, action_id, action_type, policy_check_results, decision (admissible/rejected), reason_codes, actor_id
- **Reason codes**: make every decision explainable; audit trail doesn't just say "rejected", it says "rejected_because: ALGORITHM_NOT_NIST_APPROVED"
- **Queryable**: audit trail supports compliance audits (e.g., "show me all key operations in last 30 days")
- **Tamper-proof**: once logged, entries immutable; modifications logged as separate events
- **Real-time alerting**: suspicious patterns flagged (e.g., unusual operation frequency, failed policy checks increasing)

**Approval Workflows**:
- **Tiered approval**: low-risk operations auto-approve; medium-risk require human approval; high-risk require multi-approval
- **RecoveryPolicy framework**:
  - `max_retry_budget`: retries allowed before escalation
  - `escalation_threshold`: confidence level below which human approval required
  - `approval_gates`: decision points requiring human sign-off
- **Example workflow**:
  - PQC key rotation operation requested
  - Policy check: is algorithm NIST-approved? Yes → pass
  - Policy check: is key not over-used? Yes → pass
  - Confidence level: HIGH (all checks pass)
  - Action: execute immediately (auto-approved)
  
  - Contrasting: unusual PQC algorithm requested
  - Policy check: is algorithm NIST-approved? No → fail
  - Reason: "ALGORITHM_NOT_NIST_APPROVED"
  - Action: escalate to security team lead for approval (requires human signature)
- **Audit trail**: approval decision logged with approver_id, approval_reason, timestamp

**Compliance Framework Integration**:
- **NIST PQC Standards Compliance**:
  - Policy check: algorithm from NIST PQC standardized list? (KYBER, DILITHIUM, SPHINCS+, etc.)
  - Policy check: key length meets NIST recommendations?
  - Policy check: hybrid mode (classical + post-quantum) correctly implemented?
  - Audit trail proves compliance for auditors
- **FIPS Cryptography Compliance**:
  - Policy check: cryptographic algorithm FIPS-approved?
  - Policy check: key generation using FIPS-approved RNG?
  - Policy check: key storage in FIPS-approved HSM?
- **Government Standards Compliance**:
  - Policy check: operation on approved data classification?
  - Policy check: operation in approved data center?
  - Policy check: operation by approved personnel?

**Escalation & Human-in-the-Loop**:
- **Confidence-based escalation**: policy decision confidence tracked; if confidence < threshold, escalate
- **Bounded autonomy**: system can auto-approve low-risk, high-confidence decisions; requires human approval for edge cases
- **Approval SLA**: system tracks time-to-approval; alerts if approval delays exceed threshold
- **Decision transparency**: escalation message explains why human approval needed (e.g., "POLICY_CHECK_CONFIDENCE_LOW: multiple checks ambiguous")

**Schema Validation for Governance**:
- Governance layer contracts enforced via closed enums: PolicyCheckType (5 types), DecisionReason (100+ reason codes), ApprovalLevel (auto/human/multi)
- Type safety ensures policy decisions can't be accidentally misclassified
- 18 schema validation tests ensure governance layer invariants (every action has policy decision logged, decisions are binary, reason codes are valid)

**Test Coverage & Validation**:
- **66 passing tests** validating governance correctness
- Schema validation (18 tests): node/edge type correctness, governance layer isolation, policy decision logging
- Constraint engine tests (13 tests): policy checks against standards (NIST, FIPS), compliance validation
- End-to-end tests (18 tests): full action flow (request → validate → execute → audit), escalation workflows
- Type safety: 100% annotation coverage; no type errors

**Key Technologies**: Python 3.11, dataclasses, enums, closed schemas, type annotations, audit logging patterns, FastAPI

**Outcomes**:
- **Demonstrated governance architecture expertise**: governance layer designed as first-class component, enabling independent evolution
- **Compliance-ready system**: policy-as-code framework maps cleanly to NIST/FIPS/government standards
- **Audit trail design**: audit logs support compliance audits (queryable, immutable, reason-coded)
- **Approval workflow expertise**: tiered approval (auto/human/multi) enables appropriate governance for different risk levels
- **Standards integration**: architecture pattern generalizes to any compliance framework

**Repository**: github.com/singhpratik44/research-graph-engine  
**Branch**: claude/quantum-classical-os-controller-dk7lhp

---

## CORE COMPETENCIES

### Governance Architecture
- **Governance as first-class layer**: not bolted-on; integrated into system design from start
- **Policy-as-code framework**: policies expressed as pluggable constraint functions
- **Layer isolation**: governance layer independent; can evolve without affecting other layers
- **Federated enforcement**: all teams respect governance uniformly; no exceptions or backdoors
- **Scalable to enterprise**: architecture pattern tested with 66 tests; scales to complex compliance requirements

### Policy & Compliance Framework
- **5 policy check types** (compliance, interoperability, performance, environment, risk) generalizing to any standards
- **Policies as functions**: adding compliance requirement = add one check function; no rewrites
- **Binary decisions**: every policy decision is definitive (admissible/rejected), not advisory
- **Reason codes**: decisions explainable and traceable
- **Standards integration**: maps to NIST, FIPS, government standards, custom compliance requirements

### Audit Trail Design
- **Immutable logging**: decisions logged immediately, modifications logged as separate events
- **Queryable format**: audit logs support compliance audits and forensics
- **Tamper-proof**: cryptographic hash links (optional) prevent undetected tampering
- **Reason codes**: every log entry includes decision justification
- **Real-time alerting**: suspicious patterns flagged for security team
- **Retention**: configurable retention policies meeting compliance hold requirements

### Approval Workflows
- **Tiered approval**: low-risk auto-approve; medium-risk human-in-loop; high-risk multi-approval
- **Confidence-based escalation**: policy decision confidence tracked; escalate if < threshold
- **Bounded autonomy**: system autonomy limits defined explicitly; operations beyond limits escalated
- **Approval SLA tracking**: time-to-approval monitored; alerts if delays exceed threshold
- **Decision transparency**: escalation explains why human approval needed

### Risk Assessment & Escalation
- **Risk-driven approval levels**: operation risk determines approval path
- **Escalation logic**: clear rules for when human review required
- **Recovery policies**: retry budgets, escalation thresholds, approval gates
- **Human-in-the-loop**: appropriate balance of automation and oversight
- **Audit of escalations**: every escalation decision logged with justification

### Compliance Frameworks
- **NIST PQC**: algorithm selection, key length, hybrid mode validation
- **FIPS**: cryptographic algorithm, key generation, key storage validation
- **Government standards**: data classification, data center approval, personnel approval
- **Custom compliance**: generalizable policy framework for custom requirements
- **Audit readiness**: compliance proof generated automatically from audit trail

### Type Safety & Validation
- **Closed enums for governance**: PolicyCheckType, DecisionReason, ApprovalLevel prevent invalid states
- **Schema validation**: governance layer invariants validated at runtime
- **Type checking**: 100% annotation coverage prevents type-based bugs
- **Conformance testing**: 18 tests validate governance layer correctness

---

## TECHNICAL SKILLS

**Governance & Architecture**: Policy-as-code, governance layers, approval workflows, compliance frameworks, audit trails

**Compliance & Standards**: NIST PQC, FIPS cryptography, government security standards, compliance auditing

**Security**: Risk assessment, escalation logic, human-in-the-loop systems, tamper-proof logging, threat modeling

**Distributed Systems**: Layer isolation, federated enforcement, contract-based coordination

**Languages & Tools**: Python (production-grade), dataclasses, enums, type hints, audit logging, FastAPI, Git

---

## EDUCATION

**[University Name]** — [Degree], [Field]  
*[Relevant coursework in security, compliance, or cryptography]*

---

## ADDITIONAL

**Written**: Governance architecture patterns, policy frameworks, compliance guides, audit trail design documents

**Publications**: GitHub branch with 66 passing tests, governance implementation, production-ready code organization

**Interests**: Security architecture, governance patterns, policy-as-code, compliance automation, standards integration

---

## INTERVIEW FOCUS (For This Resume)

**Expected Questions**:
1. *"How do you approach governance at scale?"* → Answer with governance layer, policy-as-code, federated enforcement
2. *"How do you ensure compliance audits pass?"* → Answer with immutable audit trails, reason codes, queryable logs
3. *"How do you handle policy conflicts?"* → Answer with policy checks, escalation logic, human approval
4. *"Tell me about a governance system you've designed."* → Answer with this project: policy framework, approval workflows, audit trails

**Whiteboard Exercise**: Draw the governance layer in the 5-layer model. Walk through a policy decision flow (action → validation → execution/escalation → audit).

**Code References**:
- `quantum_constraints.py:1-100` — policy validation framework (maps to compliance checks)
- `quantum_controller.py:250-350` — approval workflows and escalation logic
- `quantum_dashboard.py:200-250` — audit trail logging and compliance reporting
- Test suite `test_quantum_constraints.py:1-50` — policy validation tests

**Key Differentiator**: You understand **governance as architecture**, not as a compliance checkbox. This matters to security teams.

**For NIST PQC Roles Specifically**:
- Emphasize how policy framework maps to NIST standards
- Reference cryptographic standards integration
- Highlight audit trail design for standards compliance audits

**For AWS/IBM PQC Migration Roles**:
- Emphasize federated enforcement (all teams respect policies)
- Reference how architecture enables coordinated migration across distributed systems
- Highlight how governance layer isolates policy changes from control logic
