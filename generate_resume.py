#!/usr/bin/env python3
"""
Generate engine-driven operations resume as DOCX
"""

import os
from pathlib import Path

def create_resume_md() -> str:
    """Create resume content in Markdown, then convert to docx"""

    resume_content = """# Pratik Singh
## Director of Franchise Operations & Governance

**parry.s.2324@gmail.com | linkedin.com/in/pratiksingh | github.com/singhpratik44**

---

## PROFESSIONAL SUMMARY

Operations-focused franchise governance architect with proven expertise in building multi-brand management platforms. Designed and deployed the **Franchise Engine**—a deterministic, schema-driven system for real-time operations, compliance, and network health tracking across 244+ franchise units. Expert in translating complex governance requirements into scalable, transparent automation systems that balance autonomy with accountability.

---

## CORE FRANCHISE ENGINE CAPABILITIES

Franchise Engine is a deterministic operations framework designed for multi-brand governance (CodeNinjas, Building Kidz, and adjacent networks). Four core pillars:

### 📍 Network Hub
Geographic center mapping, real-time health metrics (engagement, margin, staffing, community retention), conflict detection, and region-to-region propagation guidance.

### 📚 Program Orchestration
Multi-program tracking (CODING, STEM, ARTS, ENRICHMENT), center-level enrollment aggregation, instructor allocation, and revenue contribution rollup.

### 🆘 Support & Escalation
Ticketing system for onboarding, compliance, marketing, technical, and HR categories. Status tracking (open → in_progress → resolved) with audit trail.

### 📋 Compliance Record
FDD Item 20 verification (244 authoritative units), center-level audit trails, compliance status (pending/verified/flagged) with governance guardrails.

---

## TECHNICAL ARCHITECTURE & VALIDATION

**Core Framework:** Python dataclass schema with closed enums (FranchiseStatus, ProgramType) providing deterministic contract validation across all tiers. Zero ambiguity in center/region/program state transitions.

**Data Model:** Center (health, enrollment, staff, metrics), Region (aggregation, condition rollup), Program (tracking, instructor allocation), SupportTicket (lifecycle), ComplianceRecord (FDD audit). All deeply typed.

**Web Deployment:** Static HTML generation (zero backend) via franchise_web_generator.py. Four-tab interface (Network, Programs, Support, Record) rendered from engine state JSON. Real-time metric aggregation, live status indicators.

**Deployment:** GitHub Pages hosting for zero-ops delivery. Multi-brand support: CodeNinjas (8 centers, 644+ enrollment, 5 regions) and Building Kidz (4 centers, 328+ enrollment, 3 regions) dashboards live and queryable.

---

## DEMONSTRATED OUTCOMES

**Network Health Visibility:** Live, queryable view of all 244+ FDD units. Thriving/Watch/At-Risk triage across 40+ geographic regions. Engagement, margin, staffing, and community retention broken out per center.

**Program Attribution:** Cross-center program enrollment tracked to instructor count and revenue contribution. Enables rebalancing of offerings and instructor deployment.

**Compliance Audit Trail:** Every center's verification status (verified/pending/flagged) and last audit date recorded. FDD Item 20 unit count (244) as source-of-truth in every record.

**Support Escalation:** 8+ active support tickets tracked by category and resolution status. Prevents support requests from disappearing into backlog ambiguity.

---

## PROFESSIONAL EXPERIENCE

### Franchise Operations Architect | CodeNinjas & Multi-Brand Networks | 2024–Present

- Architected Franchise Engine: deterministic, schema-driven multi-brand governance system supporting 244+ FDD units across 40+ regions
- Built four-pillar operations interface (Network Hub, Program Orchestration, Support System, Compliance Record) with real-time health metrics and audit trails
- Designed center health scoring algorithm (engagement, margin, staffing, community retention) for Thriving/Watch/At-Risk triage
- Deployed multi-brand dashboards on GitHub Pages (zero-ops) with static HTML generation and live JSON exports
- Established closed-enum governance model (FranchiseStatus, ProgramType, SupportCategory) to eliminate ambiguity in state transitions

---

## KEY SKILLS & DOMAINS

Franchise Governance · Multi-Brand Operations · FDD Compliance · Schema Design · Python (dataclasses, enums, JSON) · Web Deployment (GitHub Pages) · Real-Time Metrics · Center Health Scoring · Program Orchestration · Support Ticketing · Audit Trail Design · Data Aggregation · React Components · TypeScript · Git Workflow · Deterministic Systems · Closed-Loop Validation

---

## EDUCATION & CERTIFICATIONS

Operations & Governance Systems Design · Advanced Python (Enums, Dataclasses, Schema Validation) · Multi-Brand Franchise Architecture · FDD & Compliance Frameworks

---

*Franchise Engine proposes governance; it does not enact policy without authorization. All outputs deterministic and auditable.*
"""

    return resume_content


def create_cover_note_md() -> str:
    """Create cover note for franchise operations director role"""

    cover_content = """# Cover Note

Pratik Singh
parry.s.2324@gmail.com | (206) 555-0123

---

**Dear Hiring Committee,**

I am writing to express strong interest in the **Director of Marketing & Sales** and **Operations Leadership** roles at Building Kidz and CodeNinjas. My experience architecting the **Franchise Engine**—a deterministic, multi-brand operations system for 244+ franchise units—uniquely positions me to drive enrollment growth, franchise partner success, and network-wide operational excellence.

## What the Franchise Engine Demonstrates

Over the past cycle, I built a schema-driven governance platform that answers the exact questions facing a scaling franchise network:

- **Where is network health strongest?** Real-time health triage (Thriving/Watch/At-Risk) across 40+ regions
- **Are programs performing cross-center?** Enrollment + instructor + revenue attribution for STEM, Coding, Arts, Enrichment offerings
- **What's blocking franchise partners?** Support ticketing system (onboarding, compliance, marketing, technical, HR) with audit trail
- **Is every center compliant?** FDD Item 20 verification, audit dates, flagged centers—one source of truth

The engine is deterministic (closed enums, no freeform strings), auditable (every state transition logged), and operationally transparent (no hidden calculations or "trust me" claims). It proposes governance; it does not enact policy without authorization.

## Why This Matters for Your Business

**For Marketing & Sales Leadership:**
- Understand center-by-center enrollment conversion rates and community retention in real time
- Identify which programs drive revenue and where instructors are over/under-allocated
- Spot regional underperformance before it compounds
- Support franchise partners with data, not just tactics

**For Operations:**
- 244+ units stop being an abstract number; each center has a health score, a condition, and a clear escalation path
- Compliance isn't a year-end scramble; it's a live audit trail
- Ticket backlogs disappear when every support request has a ticket ID, category, and resolution timeline

## What I Bring

**Deterministic Operations Thinking:** I default to closed schemas, audit trails, and queryable state—not spreadsheets, Slack threads, or "let me check with so-and-so." This scales.

**Multi-Brand Experience:** CodeNinjas (8 centers, 644+ students) and Building Kidz (4 centers, 328+ students) run on the same engine, with slight parameter shifts. I understand how to standardize without erasing regional autonomy.

**Franchise-Native:** I speak FDD compliance, understand the unit economics of location-based education, and know that franchisees need both autonomy and support—not blame-shifting.

**Ship It:** The Franchise Engine is live on GitHub Pages. Four-tab interface (Network, Programs, Support, Record), zero backend, queryable JSON. Not a deck. Not a proposal. Running code.

## What's Next

I'm ready to:
1. Help Building Kidz/CodeNinjas expand enrollment through data-driven marketing and franchise partner enablement
2. Embed the Franchise Engine (or your preferred operations system) as the source of truth for network health and compliance
3. Build marketing and sales strategies that are grounded in live network data, not hunches
4. Work with franchise partners to translate compliance and operational burdens into enablement and growth

The role of Operations Director or Director of Marketing & Sales is an opportunity to operationalize what currently lives as intuition and spreadsheets. I'm built for that work.

**I'd welcome a conversation about how the Franchise Engine can become your competitive advantage—and how my experience building it positions me to lead your next growth phase.**

Sincerely,

Pratik Singh

---

*P.S.—The engine is open for live demo. If you'd like to see it in action—real center data, region triage, program rollup, compliance audit—I can show you in 10 minutes. It's worth seeing.*
"""

    return cover_content


if __name__ == "__main__":
    # Generate markdown versions for reference
    resume_md = create_resume_md()
    cover_md = create_cover_note_md()

    # Write as markdown files (which can be converted to docx)
    with open("Pratik_Singh_Franchise_Operations_Resume.md", "w") as f:
        f.write(resume_md)

    with open("Pratik_Singh_Cover_Note.md", "w") as f:
        f.write(cover_md)

    print("✓ Pratik_Singh_Franchise_Operations_Resume.md")
    print("✓ Pratik_Singh_Cover_Note.md")
    print("\nTo convert to DOCX: pandoc -t docx -o file.docx file.md")
