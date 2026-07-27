#!/usr/bin/env python3
"""
Extended job tracker population with original 8 targets + 4 enterprise targets.

This script populates the tracker with both:
- Original 8 targets (startups + public quantum companies): 21 positions
- New 4 enterprise targets (AWS, Palo Alto, NXP, IBM): 12-16 positions

Total expected: 33-37 positions across 12 hot/warm target companies.

Usage:
    python3 populate_tracker_extended.py > jobs_extended.json
"""

import json
from datetime import datetime, timezone
from quantum_job_tracker import (
    JobApplicationTracker, Company, CompanyStage, InterestLevel,
    JobOpening, ProjectVariant
)


def create_extended_tracker():
    """Create tracker with original 8 + new 4 enterprise targets."""
    # Import and run the original tracker population
    from populate_tracker_with_research import create_populated_tracker
    tracker = create_populated_tracker()

    # =========================================================================
    # ENTERPRISE TIER: AWS
    # =========================================================================
    aws = Company(
        company_name="AWS - Center for Quantum Computing",
        industry="quantum_computing",
        stage=CompanyStage.ENTERPRISE,
        location="Seattle, WA / Remote",
        remote_friendly=True,
        website="https://aws.amazon.com/quantum",
        github_org="aws",
        technical_blog="https://aws.amazon.com/blogs/quantum-computing/",
        funding_stage="public",
        interest_level=InterestLevel.HOT,
        notes="Braket quantum cloud platform, hybrid classical-quantum infrastructure, large-scale"
    )
    tracker.add_company(aws)

    aws_jobs = [
        JobOpening(
            job_id="aws_tpm_quantum_001",
            company=aws,
            job_title="Technical Program Manager - Quantum Computing",
            job_url="https://aws.amazon.com/careers/",
            posted_date="2026-06-20",
            description="Lead quantum cloud platform strategy, coordinate hardware partnerships, manage quantum API roadmap, work with enterprise customers on hybrid classical-quantum architectures.",
            required_skills=["Program Management", "Quantum Computing", "Cloud Architecture", "Stakeholder Management"],
            nice_to_have_skills=["Systems Design", "Physics", "Real-time Systems"],
            salary_range="$160,000 - $250,000",
            project_variant_fit=ProjectVariant.ARCHITECTURE_FOCUSED
        ),
        JobOpening(
            job_id="aws_quantum_soft_001",
            company=aws,
            job_title="Quantum Software Engineer - Braket",
            job_url="https://aws.amazon.com/careers/",
            posted_date="2026-06-18",
            description="Build quantum simulation infrastructure, hybrid algorithms, integrate with quantum hardware partners, optimize for classical-quantum co-execution.",
            required_skills=["Python", "Quantum Computing", "Simulation", "Systems Design"],
            nice_to_have_skills=["C++", "FPGA", "Real-time Systems"],
            salary_range="$140,000 - $220,000",
            project_variant_fit=ProjectVariant.FULL_STACK
        ),
        JobOpening(
            job_id="aws_security_pqc_001",
            company=aws,
            job_title="Security Architect - Post-Quantum Cryptography",
            job_url="https://aws.amazon.com/careers/",
            posted_date="2026-06-22",
            description="Design AWS infrastructure migration to post-quantum cryptography, work with NIST standards, develop policy enforcement and compliance frameworks.",
            required_skills=["Cryptography", "Security Architecture", "AWS Infrastructure"],
            nice_to_have_skills=["PQC", "Governance", "Audit Trails"],
            salary_range="$150,000 - $230,000",
            project_variant_fit=ProjectVariant.GOVERNANCE_FOCUSED
        ),
    ]
    for job in aws_jobs:
        tracker.add_job(job)

    # =========================================================================
    # ENTERPRISE TIER: PALO ALTO NETWORKS
    # =========================================================================
    palo = Company(
        company_name="Palo Alto Networks",
        industry="post_quantum_crypto",
        stage=CompanyStage.ENTERPRISE,
        location="Santa Clara, CA / Remote",
        remote_friendly=True,
        website="https://jobs.paloaltonetworks.com",
        github_org="paloaltonetworks",
        technical_blog="https://www.paloaltonetworks.com/blog/",
        funding_stage="public",
        interest_level=InterestLevel.WARM,
        notes="Enterprise security leader, active NIST PQC migration, government customers"
    )
    tracker.add_company(palo)

    palo_jobs = [
        JobOpening(
            job_id="palo_pqc_pm_001",
            company=palo,
            job_title="Senior Program Manager - Post-Quantum Cryptography",
            job_url="https://jobs.paloaltonetworks.com/",
            posted_date="2026-06-25",
            description="Lead enterprise PQC migration program, define migration playbook, work with customers on governance and compliance, coordinate with standards bodies.",
            required_skills=["Program Management", "Cryptography", "Enterprise Architecture"],
            nice_to_have_skills=["Policy", "Governance", "NIST Standards"],
            salary_range="$140,000 - $210,000",
            project_variant_fit=ProjectVariant.GOVERNANCE_FOCUSED
        ),
        JobOpening(
            job_id="palo_crypto_eng_001",
            company=palo,
            job_title="Cryptography Engineer - Standards & Compliance",
            job_url="https://jobs.paloaltonetworks.com/",
            posted_date="2026-06-23",
            description="Implement PQC algorithms, validate against standards, manage HSM integrations, ensure compliance with government cryptographic requirements.",
            required_skills=["Cryptography", "C++", "Standards Compliance"],
            nice_to_have_skills=["PQC", "HSM", "Audit Trails"],
            salary_range="$130,000 - $190,000",
            project_variant_fit=ProjectVariant.GOVERNANCE_FOCUSED
        ),
    ]
    for job in palo_jobs:
        tracker.add_job(job)

    # =========================================================================
    # ENTERPRISE TIER: NXP
    # =========================================================================
    nxp = Company(
        company_name="NXP Semiconductors",
        industry="post_quantum_crypto",
        stage=CompanyStage.ENTERPRISE,
        location="Eindhoven, Netherlands / Remote",
        remote_friendly=False,
        website="https://www.nxp.com/company/about-nxp/careers:CAREERS",
        github_org="nxp",
        funding_stage="public",
        interest_level=InterestLevel.WARM,
        notes="Semiconductor leader, embedded PQC in microcontrollers, hardware security"
    )
    tracker.add_company(nxp)

    nxp_jobs = [
        JobOpening(
            job_id="nxp_crypto_hw_001",
            company=nxp,
            job_title="Hardware Security Architect",
            job_url="https://www.nxp.com/company/about-nxp/careers:CAREERS",
            posted_date="2026-06-16",
            description="Design post-quantum cryptography capabilities into NXP microcontrollers and SoCs, optimize for resource-constrained embedded systems.",
            required_skills=["Hardware Design", "Cryptography", "Embedded Systems"],
            nice_to_have_skills=["PQC", "Real-time Constraints", "Low-power Design"],
            salary_range="$130,000 - $200,000",
            project_variant_fit=ProjectVariant.CONSTRAINTS_FOCUSED
        ),
        JobOpening(
            job_id="nxp_project_mgr_001",
            company=nxp,
            job_title="Project Manager - Security Integration",
            job_url="https://www.nxp.com/company/about-nxp/careers:CAREERS",
            posted_date="2026-06-19",
            description="Manage PQC integration across product lines, coordinate with hardware and software teams, ensure timelines and quality metrics.",
            required_skills=["Project Management", "Security", "Cross-functional Leadership"],
            nice_to_have_skills=["Cryptography", "Embedded Systems", "Governance"],
            salary_range="$120,000 - $180,000",
            project_variant_fit=ProjectVariant.GOVERNANCE_FOCUSED
        ),
    ]
    for job in nxp_jobs:
        tracker.add_job(job)

    # =========================================================================
    # ENTERPRISE TIER: IBM
    # =========================================================================
    ibm = Company(
        company_name="IBM",
        industry="quantum_computing",
        stage=CompanyStage.ENTERPRISE,
        location="Yorktown Heights, NY / Remote",
        remote_friendly=True,
        website="https://www.ibm.com/careers",
        github_org="ibm",
        technical_blog="https://www.ibm.com/quantum/blog/",
        funding_stage="public",
        interest_level=InterestLevel.HOT,
        notes="Quantum Network leader, Qiskit ecosystem, NIST PQC standards contributor, hybrid quantum-classical"
    )
    tracker.add_company(ibm)

    ibm_jobs = [
        JobOpening(
            job_id="ibm_qiskit_001",
            company=ibm,
            job_title="Quantum Software Engineer - Qiskit",
            job_url="https://www.ibm.com/careers",
            posted_date="2026-06-14",
            description="Contribute to Qiskit ecosystem, build hybrid quantum-classical algorithms, optimize circuit compilation and mapping for real hardware.",
            required_skills=["Python", "Quantum Computing", "Algorithm Design"],
            nice_to_have_skills=["Graph-based Architecture", "Compilation", "Open Source"],
            salary_range="$140,000 - $210,000",
            project_variant_fit=ProjectVariant.ARCHITECTURE_FOCUSED
        ),
        JobOpening(
            job_id="ibm_pqc_architect_001",
            company=ibm,
            job_title="Security Architect - Post-Quantum Standards",
            job_url="https://www.ibm.com/careers",
            posted_date="2026-06-21",
            description="Lead IBM's involvement in NIST PQC standardization, design quantum-safe infrastructure, advise enterprise customers on migration strategy.",
            required_skills=["Cryptography", "Standards Development", "Security Architecture"],
            nice_to_have_skills=["PQC", "Governance", "Policy"],
            salary_range="$150,000 - $230,000",
            project_variant_fit=ProjectVariant.GOVERNANCE_FOCUSED
        ),
        JobOpening(
            job_id="ibm_observability_001",
            company=ibm,
            job_title="Infrastructure Engineer - Quantum Observability",
            job_url="https://www.ibm.com/careers",
            posted_date="2026-06-17",
            description="Build monitoring and observability for IBM Quantum cloud platform, design real-time metrics dashboards, track hardware health and performance.",
            required_skills=["Observability", "Cloud Infrastructure", "Python"],
            nice_to_have_skills=["Real-time Metrics", "Quantum", "Dashboards"],
            salary_range="$130,000 - $200,000",
            project_variant_fit=ProjectVariant.DASHBOARD_FOCUSED
        ),
    ]
    for job in ibm_jobs:
        tracker.add_job(job)

    return tracker


def main():
    """Generate extended tracker and output summary."""
    tracker = create_extended_tracker()

    summary = tracker.get_summary()

    print("=" * 80)
    print("EXTENDED JOB MARKET RESEARCH: Startup + Enterprise Quantum/PQC Market")
    print("=" * 80)
    print(f"\nTotal companies tracked: {summary['total_companies_tracked']}")
    print(f"Total job openings researched: {summary['total_jobs_found']}")
    print(f"Applications ready to submit: {summary['total_applications']}")
    print(f"\nHot target companies: {', '.join(summary['hot_companies'])}")

    print("\n" + "=" * 80)
    print("BREAKDOWN: STARTUP TIER vs. ENTERPRISE TIER")
    print("=" * 80)

    startup_companies = [c for c in tracker.companies.values()
                        if c.stage in (CompanyStage.STARTUP, CompanyStage.SCALE_UP)]
    enterprise_companies = [c for c in tracker.companies.values()
                           if c.stage in (CompanyStage.ENTERPRISE, CompanyStage.ESTABLISHED)]

    startup_jobs = sum(1 for j in tracker.job_openings.values()
                      if j.company.stage in (CompanyStage.STARTUP, CompanyStage.SCALE_UP))
    enterprise_jobs = sum(1 for j in tracker.job_openings.values()
                         if j.company.stage in (CompanyStage.ENTERPRISE, CompanyStage.ESTABLISHED))

    print(f"\nSTARTUP TIER (Quantum-focused, equity upside):")
    print(f"  Companies: {len(startup_companies)} (Atom, IonQ, D-Wave, PsiQuantum, Google Quantum AI)")
    print(f"  Positions: {startup_jobs}")
    print(f"  Salary range: $120-250K+")
    print(f"  Remote: Limited (on-site preferred)")

    print(f"\nENTERPRISE TIER (Scale, stability, program management):")
    print(f"  Companies: {len(enterprise_companies)} (AWS, Palo Alto, NXP, IBM)")
    print(f"  Positions: {enterprise_jobs}")
    print(f"  Salary range: $120-250K+")
    print(f"  Remote: Hybrid/friendly")

    print("\n" + "=" * 80)
    print("RECOMMENDATION")
    print("=" * 80)
    print("""
Apply to BOTH tiers:

STARTUP TIER (Atom, IonQ, D-Wave, PsiQuantum, Google Quantum AI):
  - Best for: Pure quantum engineering, cutting-edge research, equity upside
  - Roles: Control Engineer, Simulation Engineer, Systems Architect
  - Application count: 8-10 applications
  - Interview prep: Focus on quantum physics + real-time systems

ENTERPRISE TIER (AWS, Palo Alto, NXP, IBM):
  - Best for: Scale, stability, program management, hybrid systems
  - Roles: Program Manager, Security Architect, Infrastructure Engineer
  - Application count: 8-10 applications
  - Interview prep: Focus on governance, enterprise standards, integration

TOTAL: 16-20 applications across two tiers = optionality in decision phase

Market is hot. Both startup and enterprise teams are hiring aggressively.
Your Phase 1 project demonstrates competence for both paths.
    """)

    print("=" * 80)
    print(f"EXTENDED TRACKER READY")
    print(f"Total opportunities: {summary['total_jobs_found']} positions across {summary['total_companies_tracked']} companies")
    print(f"Expected applications: 16-20 (all companies)")
    print(f"Expected interviews (25% rate): 4-5")
    print(f"Expected offers (50% conversion): 2-3")
    print("=" * 80)


if __name__ == "__main__":
    main()
