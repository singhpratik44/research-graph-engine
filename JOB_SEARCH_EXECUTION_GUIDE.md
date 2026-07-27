# Job Search Execution Guide

This guide walks through executing the quantum computing job search strategy using the tracker, recruiter strategy, and project variants.

**Timeline**: Phases 1-3 over 4 weeks  
**Target**: 15-20 applications to hot/warm targets  
**Success criteria**: 25% interview rate, 50% offer-to-interview conversion, $130K+ salary

---

## Phase 1: Research & Targeting (Week 1-2)

### Step 1.1: Populate Target Companies

Use `quantum_job_tracker.py` to add target companies from RECRUITER_STRATEGY.md:

```python
from quantum_job_tracker import JobApplicationTracker, Company, CompanyStage, InterestLevel

tracker = JobApplicationTracker()

# Hot targets
tracker.add_company(Company(
    company_name="IonQ",
    industry="quantum_computing",
    stage=CompanyStage.SCALE_UP,
    location="College Park, MD",
    remote_friendly=True,
    website="https://www.ionq.com",
    github_org="ionq",
    technical_blog="https://ionq.com/blog",
    funding_stage="public",
    interest_level=InterestLevel.HOT,
    notes="Trapped-ion quantum cloud. Actively hiring control engineers."
))

# ... repeat for other targets
```

**Companies to add:**
- Atom Computing (hot)
- IonQ (hot)
- D-Wave (hot)
- PsiQuantum (hot)
- Google Quantum AI (hot)
- IBM Quantum (warm)
- Microsoft Azure Quantum (warm)
- Rigetti (warm)
- Keysight Technologies (warm)
- DigiCert (warm, PQC focus)
- PQShield (warm, PQC focus)
- Google Cloud (crypto team, warm)
- AWS (quantum + crypto, warm)
- Cloudflare (crypto, warm)

### Step 1.2: Research Job Openings

For each company, visit:
- Company careers page (e.g., `{company_url}/careers`)
- LinkedIn Jobs (search company name + "quantum" or "cryptography")
- Indeed (search company name + role keywords)
- GitHub Jobs (if company posts there)
- AngelList (for startups)

**Search keywords by company type:**

*Quantum Computing Companies*:
- "Quantum Engineer"
- "Quantum Software Engineer"
- "Control Systems Engineer"
- "Quantum Control"
- "Quantum Hardware"
- "Systems Engineer"

*Post-Quantum Cryptography Companies*:
- "Cryptography Engineer"
- "PKI Engineer"
- "Standards Engineer"
- "Compliance Engineer"
- "Security Engineer"

*Cloud/Major Tech*:
- "Quantum" (for quantum initiatives)
- "Cryptography" + "standards" (for crypto teams)
- "Post-quantum" or "PQC"

### Step 1.3: Add Job Openings to Tracker

For each job opening found, add to tracker:

```python
from quantum_job_tracker import JobOpening, ProjectVariant

job = JobOpening(
    job_id="ionq_engineer_001",
    company=tracker.companies["IonQ"],
    job_title="Quantum Software Engineer",
    job_url="https://ionq.com/careers/job/...",
    posted_date="2026-06-15",
    description="Develop control software for trapped-ion quantum systems. Work on real-time feedback loops, simulation interfaces, and quantum-classical integration.",
    required_skills=["Python", "Systems Design", "Real-time Systems"],
    nice_to_have_skills=["Quantum Computing", "Control Theory", "Simulation"],
    salary_range="$130,000 - $200,000",
    project_variant_fit=ProjectVariant.CONSTRAINTS_FOCUSED
)
tracker.add_job(job)
```

**Expected outcome of Phase 1**: 20+ job openings tracked, categorized by company and role type.

---

## Phase 2: Application Prep (Week 2-3)

### Step 2.1: Develop Core Application Materials

Create tailored versions of these materials:

#### A. Resume (1-2 pages)

**Project section** (2-3 lines):
```
Quantum-Classical OS Controller (2026)
Architected a modular quantum control platform: 5-layer graph model, 
6-stage real-time feedback loop, physics constraint engine, pluggable 
simulators, observability dashboard. 66 tests validating end-to-end 
system integrity. Python, systems design, real-time control.
```

**Skills section**:
- Systems Design & Architecture
- Python (production-grade)
- Real-time Control Systems
- Constraint Optimization
- Simulator Design & Modeling
- Observability & Monitoring
- Governance & Policy Enforcement
- Test-Driven Development

#### B. Project Variant Summaries

For each of the 5 variants (see PROJECT_VARIANTS.md), prepare a 1-paragraph elevator pitch:

**Control Engineer variant (for IonQ, Atom Computing)**:
> "Built a 6-stage quantum feedback loop with hardware-aware constraint filtering and confidence-driven decision making. Demonstrates real-time control systems architecture: sense→estimate→constrain→act→validate→learn, with phase timing metrics and bounded autonomy recovery policies."

**Architecture variant (for IBM, Google, Microsoft, Rigetti)**:
> "Designed a 5-layer graph model separating physical hardware topology, logical circuits, workflow scheduling, device capability, and governance policies. Service contracts enable independent team ownership of layers. 66 tests validate integration across all layers."

*[Create similar 1-paragraph summaries for Governance, Observability, and Simulator variants]*

#### C. Cover Letter Template

```
[Company] is building [their quantum system / crypto infrastructure].

I built a quantum-classical OS controller that demonstrates my approach 
to [their core challenge]:

1. [Architecture concept relevant to their system]
2. [Real-time control or constraint evaluation relevant to their needs]
3. [Observability or governance relevant to their scale/domain]

The project shows [specific competency they're hiring for]. I'm ready to 
apply this to your [production environment / team / challenge].

[Optional: Reference a recent blog post, paper, or GitHub repo from their team]

---
[Standard closing]
```

#### D. Project Links

Prepare these for inclusion in applications:
- GitHub branch: `https://github.com/singhpratik44/research-graph-engine/tree/claude/quantum-classical-os-controller-dk7lhp`
- Key modules:
  - Controls & constraints: `quantum_controller.py` + `quantum_constraints.py`
  - Architecture: `quantum_schema.py` (5-layer model)
  - Simulators: `quantum_simulator.py` (Markovian + non-Markovian)
  - Observability: `quantum_dashboard.py` (event streaming + metrics)
- Run report: Run `python3 quantum_run_report.py` to generate Phase 1 summary
- Tests: 66 passing tests across 4 test modules (run with `python3 -m unittest discover -p "test_quantum_*.py"`)

### Step 2.2: Map Variants to Job Openings

For each job opening in the tracker, update `project_variant_fit`:

```python
# Example mappings:

# IonQ "Quantum Software Engineer" → Control Engineer variant
tracker.job_openings["ionq_engineer_001"].project_variant_fit = ProjectVariant.CONSTRAINTS_FOCUSED

# IBM "Quantum Architect" → Architecture variant  
tracker.job_openings["ibm_architect_001"].project_variant_fit = ProjectVariant.ARCHITECTURE_FOCUSED

# DigiCert "PKI Standards Engineer" → Governance variant
tracker.job_openings["digicert_pki_001"].project_variant_fit = ProjectVariant.GOVERNANCE_FOCUSED
```

**Mapping heuristics:**

| Job Title Keywords | Variant | Emphasis |
|---|---|---|
| Control, feedback, real-time | CONSTRAINTS_FOCUSED | Loop, timing, confidence |
| Architect, design, system | ARCHITECTURE_FOCUSED | Layers, contracts, schema |
| Policy, governance, audit, compliance | GOVERNANCE_FOCUSED | Approval workflows, audit trail |
| Dashboard, observability, metrics, SRE | DASHBOARD_FOCUSED | Events, anomaly detection, phases |
| Simulation, physics, fidelity, error | SIMULATOR_FOCUSED | Models, robustness metrics, degradation |
| Anything else (balanced skill set) | FULL_STACK | Entire project, all five competencies |

### Step 2.3: Draft Customizations

For each variant/company pair, note any customizations:

```python
application = Application(
    application_id="app_ionq_001",
    job=tracker.job_openings["ionq_engineer_001"],
    application_date="TBD",
    status=JobStatus.PROSPECT,
    project_variant_used=ProjectVariant.CONSTRAINTS_FOCUSED,
    customizations_made=[
        "Emphasize phase timing metrics and real-time loop performance",
        "Reference IonQ's trapped-ion control architecture in cover letter",
        "Highlight recovery escalation policy for high-reliability scenarios",
        "Mention confidence-driven decision making as inverse of traditional threshold-based control"
    ]
)
tracker.submit_application(application)
```

**Expected outcome of Phase 2**: Resume, cover letter template, 5 project variant pitches, applications drafted for 15-20 target jobs.

---

## Phase 3: Bulk Applications (Week 3-4)

### Step 3.1: Customize & Submit Applications

For each job in the tracker:

1. **Check status**: Is it `PROSPECT`? If `REJECTED` or `WITHDRAWN`, skip.
2. **Select variant**: Use `project_variant_fit` to pick positioning.
3. **Customize cover letter**: Use template + customizations for this company.
4. **Assemble materials**:
   - Resume (1-page, unchanged across applications)
   - Cover letter (company-specific, 1 page)
   - Project summary (variant-specific, 2-3 paragraphs from PROJECT_VARIANTS.md)
   - GitHub branch link + test report
5. **Submit**: Record in tracker with `JobStatus.APPLIED` and today's date.
6. **Log details**: Add customizations, materials sent, any follow-up notes.

```python
from datetime import datetime, timezone

application.status = JobStatus.APPLIED
application.application_date = datetime.now(timezone.utc).isoformat()
application.submitted_materials = ["resume", "cover_letter", "project_summary", "github_link"]
application.project_variant_used = ProjectVariant.CONSTRAINTS_FOCUSED
application.customizations_made = [
    "Emphasized real-time loop performance",
    "Mentioned trapped-ion hardware context"
]
tracker.submit_application(application)
```

### Step 3.2: Set Follow-Up Reminders

For each submitted application, schedule a 2-week follow-up:

```python
from datetime import datetime, timedelta, timezone

follow_up_date = (datetime.now(timezone.utc) + timedelta(days=14)).isoformat()
application.follow_up_dates.append(follow_up_date)
```

### Step 3.3: Track Status Updates

As responses arrive:

- **Interview scheduled**: Update `status = JobStatus.INTERVIEW_SCHEDULED`, add interview date to tracker.
- **Rejected**: Update `status = JobStatus.REJECTED`, note reason if provided.
- **Offer received**: Update `status = JobStatus.OFFER_RECEIVED`, record offer details.
- **Offer accepted**: Update `status = JobStatus.OFFER_ACCEPTED`, note details (salary, start date, role).

```python
# Example: Interview scheduled
interview = InterviewPrep(
    company_name="IonQ",
    interview_date="2026-08-15",
    interview_type="technical",
    technical_topics=["real-time control", "confidence scoring", "constraint evaluation"],
    prepared_examples=[
        "Phase timing metrics implementation",
        "Bandwidth constraint check algorithm",
        "Confidence level mapping in action envelopes"
    ],
    questions_for_interviewer=[
        "How do you handle timing skew across control nodes?",
        "What's your confidence model for action validation?"
    ]
)
tracker.add_interview_prep(interview)
```

**Expected outcome of Phase 3**: 15-20 applications submitted within 2 weeks, with documented customizations and follow-up schedule.

---

## Phase 4: Interview Prep (Ongoing as invites arrive)

### For each interview scheduled:

1. **Review the variant**: Re-read the relevant section in PROJECT_VARIANTS.md.
2. **Prepare talking points**: From the variant's "Interview Talking Points" section.
3. **Know the code**: Review the referenced code modules (have them open during interview).
4. **Research the company**: Read recent blog posts, GitHub repos, papers, job postings.
5. **Prepare examples**: Be ready with 2-3 concrete examples from the implementation.
6. **Ask smart questions**: Use "questions_for_interviewer" from the variant section.

**Mock interview prep**:
- Practice 30-60 second elevator pitch for each variant
- Answer "Why this company?" by connecting project to their architecture
- Be ready for "What would you change?" — prepare thoughtful answers
- Practice explaining tradeoffs in design decisions

---

## Phase 5: Offer Negotiation & Decision (Month 2-3)

### When offers arrive:

1. **Log offer details**:
```python
application.status = JobStatus.OFFER_RECEIVED
application.offer_details = {
    "salary": 165000,
    "equity": "0.05%",
    "location": "College Park, MD or Remote",
    "start_date": "2026-09-01",
    "bonus": "20% annual",
    "benefits": "Full health + 401k + relocation"
}
```

2. **Compare against decision criteria**:
   - Role type: Control engineer? Architect? Crypto?
   - Company stage: Startup (equity upside)? Established (stability)?
   - Growth: Expanding quantum team? New department?
   - Values: Hiring for quantum/crypto future?
   - Salary: Market rate for $130-200K+ quantum roles

3. **Negotiate**:
   - Salary: Use market data (quantum engineers command $130-200K+ base)
   - Start date: Needed for wrap-up on current projects?
   - Role clarity: Is this truly the role you interviewed for?
   - Equity: For startups, understand vesting schedule and runway

4. **Decide**: Which offer best aligns with your long-term goals?

---

## Using the Tracker

### Querying Applications

```python
# Get all applications by status
applied = tracker.get_applications_by_status(JobStatus.APPLIED)
interviews = tracker.get_applications_by_status(JobStatus.INTERVIEW_SCHEDULED)
offers = tracker.get_applications_by_status(JobStatus.OFFER_RECEIVED)

# Get hot companies  
hot = tracker.get_hot_companies()
print(f"Target {len(hot)} hot companies: {[c.company_name for c in hot]}")

# Get summary
summary = tracker.get_summary()
print(f"Total applications: {summary['total_applications']}")
print(f"Hot companies: {summary['hot_companies']}")
print(f"Upcoming interviews: {summary['upcoming_interviews']}")
```

### Exporting Results

```python
import json

# Save tracker to JSON for record-keeping
with open("job_tracker_backup.json", "w") as f:
    json.dump(tracker.to_dict(), f, indent=2)

# Batch export for review
applied_apps = tracker.get_applications_by_status(JobStatus.APPLIED)
print(json.dumps([a.to_dict() for a in applied_apps], indent=2))
```

---

## Success Metrics

Check progress weekly:

**Week 1-2 (Research & Targeting)**:
- ✓ 15-20 target companies added to tracker
- ✓ 20-30 job openings researched and logged
- ✓ Companies sorted by interest level (hot/warm/cool)

**Week 2-3 (Application Prep)**:
- ✓ Resume finalized (1-2 pages, project section crisp)
- ✓ Cover letter template created
- ✓ 5 project variant summaries drafted
- ✓ Applications drafted for 15-20 jobs with customizations noted

**Week 3-4 (Bulk Applications)**:
- ✓ 15-20 applications submitted within 2 weeks
- ✓ All customizations + materials logged in tracker
- ✓ 2-week follow-up reminders scheduled
- ✓ Variant fit documented for each job

**Month 2+ (Interviews & Offers)**:
- ✓ Interview responses tracked (date, type, company)
- ✓ Interview prep notes recorded (topics, examples, company research)
- ✓ Offers logged with full details (salary, equity, start date, benefits)
- ✓ Offer comparison documented (which best fits goals?)

---

## Example: Completed Tracker Entry

```python
# Full example of a tracked application from research to offer

company = Company(
    company_name="IonQ",
    industry="quantum_computing",
    stage=CompanyStage.SCALE_UP,
    location="College Park, MD",
    remote_friendly=True,
    website="https://www.ionq.com",
    github_org="ionq",
    interest_level=InterestLevel.HOT,
    notes="Trapped-ion hardware, strong control team, active hiring"
)

job = JobOpening(
    job_id="ionq_control_001",
    company=company,
    job_title="Quantum Control Engineer",
    job_url="https://ionq.com/careers/quantum-control-engineer",
    posted_date="2026-06-20",
    description="Develop real-time control systems for trapped-ion quantum computers. Work on feedback loops, constraint evaluation, and hardware optimization.",
    required_skills=["Python", "Real-time Systems", "Control Theory"],
    nice_to_have_skills=["Quantum Computing", "FPGA", "C++"],
    salary_range="$130,000 - $190,000",
    project_variant_fit=ProjectVariant.CONSTRAINTS_FOCUSED
)

application = Application(
    application_id="app_ionq_control_001",
    job=job,
    application_date="2026-07-28",
    status=JobStatus.INTERVIEW_SCHEDULED,
    submitted_materials=["resume", "cover_letter", "project_summary"],
    project_variant_used=ProjectVariant.CONSTRAINTS_FOCUSED,
    customizations_made=[
        "Emphasized confidence-driven decision making",
        "Highlighted phase timing metrics and real-time performance",
        "Mentioned trapped-ion hardware context"
    ],
    follow_up_dates=["2026-08-11"],  # 2 weeks post-application
    interview_notes="Technical interview scheduled 2026-08-15, 1hr. Discussing real-time control loop design, constraint evaluation, and system architecture.",
    offer_details=None,
    outcome=""
)

interview_prep = InterviewPrep(
    company_name="IonQ",
    interview_date="2026-08-15",
    interview_type="technical",
    technical_topics=["real-time feedback loop", "confidence scoring", "constraint evaluation", "recovery policies"],
    prepared_examples=[
        "6-stage loop with LoopPhaseMetrics tracking",
        "Bandwidth constraint check algorithm and why single-qubit gates pass",
        "Confidence level mapping from ConfidenceLevel enum to numeric scores for decision-making"
    ],
    questions_for_interviewer=[
        "How do you handle timing skew across your control node network?",
        "What's your current confidence model for action validation?",
        "How many constraint checks does your real hardware evaluate per control cycle?"
    ],
    mock_interview_score=8.5,
    notes="Strong preparation. Know the constraint math (bandwidth = amplitude * factor / duration). Be ready to discuss tradeoffs between Markovian/non-Markovian simulators."
)

# Later: after offer
application.status = JobStatus.OFFER_RECEIVED
application.offer_details = {
    "salary": 165000,
    "equity": "0.03%",
    "location": "Remote",
    "start_date": "2026-09-15",
    "bonus": "20%",
    "benefits": "Full health + 401k match + home office setup"
}
```

---

## Troubleshooting

**No responses after 2 weeks?**
- Follow up via email: "Hi [Recruiter], I applied to [job] on [date]. Would love to learn more about the role!"
- Try LinkedIn: Message the hiring manager or team members directly.
- Check application status on job board (sometimes emails get filtered).

**Interview goes poorly?**
- Reflect on what was asked; review PROJECT_VARIANTS.md again.
- For rejected interviews: document what went wrong, improve for next time.
- Ask for feedback if they offer: "What skill area should I focus on for future roles?"

**Multiple offers on same timeline?**
- Use decision criteria: role type, company stage, salary, growth opportunity.
- Don't feel obligated to accept immediately; ask for 48-72 hours to decide.
- Negotiate in parallel (don't mention other offers, but use market data).

**Imposter syndrome?**
- 66 passing tests validate the architecture. You built this.
- Companies hire for potential + competence; Phase 1 demonstrates both.
- Interview conversations are collaborative, not interrogations.
