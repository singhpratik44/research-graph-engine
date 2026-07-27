#!/usr/bin/env python3
"""
Populate the quantum_job_tracker with real job openings from research.

Run this script to seed the tracker with 21+ actual job postings found in
the July 2026 market research across quantum computing and PQC companies.

Usage:
    python3 populate_tracker_with_research.py > jobs_found.json
"""

import json
from datetime import datetime, timezone
from quantum_job_tracker import (
    JobApplicationTracker, Company, CompanyStage, InterestLevel,
    JobOpening, ProjectVariant
)


def create_populated_tracker():
    """Create tracker and populate with all researched companies and jobs."""
    tracker = JobApplicationTracker()

    # =========================================================================
    # HOT TARGET: ATOM COMPUTING
    # =========================================================================
    atom = Company(
        company_name="Atom Computing",
        industry="quantum_computing",
        stage=CompanyStage.STARTUP,
        location="Boulder, CO",
        remote_friendly=False,
        website="https://atom-computing.com",
        github_org="atom-computing",
        technical_blog="https://atom-computing.com/blog",
        funding_stage="series-b",
        interest_level=InterestLevel.HOT,
        notes="Neutral atom quantum hardware, active hiring, strong control team"
    )
    tracker.add_company(atom)

    atom_jobs = [
        JobOpening(
            job_id="atom_qec_001",
            company=atom,
            job_title="Quantum Error Correction Software Engineer",
            job_url="https://atom-computing.com/careers/quantum-error-correction-software-engineer",
            posted_date="2026-06-15",
            description="Develop QEC software stack for neutral atom quantum computers. Work on error detection, correction algorithms, and real-time control loops.",
            required_skills=["Python", "Quantum Computing", "Error Correction", "Real-time Systems"],
            nice_to_have_skills=["FPGA", "C++", "Simulation"],
            salary_range="$150,000 - $199,000",
            project_variant_fit=ProjectVariant.CONSTRAINTS_FOCUSED
        ),
        JobOpening(
            job_id="atom_principal_001",
            company=atom,
            job_title="Principal Software Engineer",
            job_url="https://atom-computing.com/careers/principal-software-engineer",
            posted_date="2026-06-10",
            description="Lead architecture for quantum control platform. Define system contracts, oversee simulation infrastructure, drive observability strategy.",
            required_skills=["Systems Design", "Python", "C++", "Architecture"],
            nice_to_have_skills=["Quantum", "Real-time", "Distributed Systems"],
            salary_range="$180,000 - $220,000",
            project_variant_fit=ProjectVariant.ARCHITECTURE_FOCUSED
        ),
        JobOpening(
            job_id="atom_optical_001",
            company=atom,
            job_title="Principal Optical Engineer",
            job_url="https://atom-computing.com/careers/principal-optical-engineer",
            posted_date="2026-06-12",
            description="Lead optical systems design for neutral atom manipulation. Manage tradeoffs between fidelity, speed, and hardware constraints.",
            required_skills=["Optics", "Photonics", "Control Systems"],
            nice_to_have_skills=["Simulation", "Quantum Physics"],
            salary_range="$170,000 - $210,000",
            project_variant_fit=ProjectVariant.SIMULATOR_FOCUSED
        ),
        JobOpening(
            job_id="atom_theorist_001",
            company=atom,
            job_title="Quantum Error Correction Theorist",
            job_url="https://atom-computing.com/careers/qec-theorist",
            posted_date="2026-06-18",
            description="Research QEC codes, design tolerance requirements, validate error correction strategies against hardware.",
            required_skills=["Quantum Physics", "Error Correction Theory", "Python"],
            nice_to_have_skills=["MATLAB", "Simulation", "Publication Record"],
            salary_range="$160,000 - $200,000",
            project_variant_fit=ProjectVariant.SIMULATOR_FOCUSED
        ),
    ]
    for job in atom_jobs:
        tracker.add_job(job)

    # =========================================================================
    # HOT TARGET: IONQ
    # =========================================================================
    ionq = Company(
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
        notes="Trapped-ion quantum cloud platform, strong control systems team"
    )
    tracker.add_company(ionq)

    ionq_jobs = [
        JobOpening(
            job_id="ionq_networking_001",
            company=ionq,
            job_title="Senior Software Engineer - Quantum Networking",
            job_url="https://ionq.com/careers/senior-software-engineer-quantum-networking",
            posted_date="2026-06-20",
            description="Build distributed quantum networking layer. Design classical-quantum hybrid algorithms for networked systems.",
            required_skills=["Python", "Distributed Systems", "Networking", "Quantum Computing"],
            nice_to_have_skills=["Real-time Control", "Simulation"],
            salary_range="$140,000 - $200,000",
            project_variant_fit=ProjectVariant.ARCHITECTURE_FOCUSED
        ),
        JobOpening(
            job_id="ionq_mechanical_001",
            company=ionq,
            job_title="Senior Mechanical Systems Engineer",
            job_url="https://ionq.com/careers/senior-mechanical-engineer",
            posted_date="2026-06-18",
            description="Design mechanical systems for ion traps. Manage thermal/vacuum systems, integration with control electronics.",
            required_skills=["Mechanical Engineering", "Vacuum Systems", "Cryogenics"],
            nice_to_have_skills=["Quantum Hardware", "Simulation"],
            salary_range="$130,000 - $190,000",
            project_variant_fit=ProjectVariant.CONSTRAINTS_FOCUSED
        ),
        JobOpening(
            job_id="ionq_hpc_001",
            company=ionq,
            job_title="Senior HPC Infrastructure Engineer",
            job_url="https://ionq.com/careers/senior-hpc-infrastructure",
            posted_date="2026-06-22",
            description="Build high-performance computing infrastructure for quantum simulation and classical-quantum coprocessing.",
            required_skills=["C++", "Python", "Distributed Computing", "Performance Optimization"],
            nice_to_have_skills=["FPGA", "GPU", "Real-time Systems"],
            salary_range="$150,000 - $220,000",
            project_variant_fit=ProjectVariant.DASHBOARD_FOCUSED
        ),
    ]
    for job in ionq_jobs:
        tracker.add_job(job)

    # =========================================================================
    # HOT TARGET: D-WAVE
    # =========================================================================
    dwave = Company(
        company_name="D-Wave Systems",
        industry="quantum_computing",
        stage=CompanyStage.ESTABLISHED,
        location="Burnaby/New Haven",
        remote_friendly=False,
        website="https://www.dwavequantum.com",
        github_org="dwavesystems",
        technical_blog="https://www.dwavesystems.com/blog",
        funding_stage="public",
        interest_level=InterestLevel.HOT,
        notes="Quantum optimization focus, constraint-based scheduling"
    )
    tracker.add_company(dwave)

    dwave_jobs = [
        JobOpening(
            job_id="dwave_quantum_001",
            company=dwave,
            job_title="Senior Quantum Engineer",
            job_url="https://www.dwavequantum.com/careers/senior-quantum-engineer",
            posted_date="2026-06-19",
            description="Work on quantum annealing optimization, constraint evaluation, embedding strategies for large problems.",
            required_skills=["Optimization", "Constraint Programming", "Python", "Quantum Computing"],
            nice_to_have_skills=["Graph Theory", "Simulation"],
            salary_range="$140,000 - $210,000",
            project_variant_fit=ProjectVariant.CONSTRAINTS_FOCUSED
        ),
        JobOpening(
            job_id="dwave_devops_001",
            company=dwave,
            job_title="Senior DevOps Engineer",
            job_url="https://www.dwavequantum.com/careers/senior-devops",
            posted_date="2026-06-17",
            description="Build infrastructure for quantum cloud service. Design monitoring, alerting, and observability for quantum systems.",
            required_skills=["Kubernetes", "Python", "Monitoring", "Cloud Infrastructure"],
            nice_to_have_skills=["Quantum", "Real-time Systems"],
            salary_range="$150,000 - $220,000",
            project_variant_fit=ProjectVariant.DASHBOARD_FOCUSED
        ),
        JobOpening(
            job_id="dwave_fpga_001",
            company=dwave,
            job_title="Senior FPGA Design Engineer",
            job_url="https://www.dwavequantum.com/careers/senior-fpga-engineer",
            posted_date="2026-06-16",
            description="Design FPGA control systems for quantum hardware. Optimize gate timing, control pulse generation.",
            required_skills=["FPGA", "Verilog/VHDL", "Real-time Systems", "Control Theory"],
            nice_to_have_skills=["C++", "Python"],
            salary_range="$160,000 - $240,000",
            project_variant_fit=ProjectVariant.CONSTRAINTS_FOCUSED
        ),
    ]
    for job in dwave_jobs:
        tracker.add_job(job)

    # =========================================================================
    # HOT TARGET: PSIQUANTUM
    # =========================================================================
    psiq = Company(
        company_name="PsiQuantum",
        industry="quantum_computing",
        stage=CompanyStage.STARTUP,
        location="Zürich/Japan",
        remote_friendly=False,
        website="https://psiquantum.com",
        github_org="psiquantum",
        technical_blog="https://psiquantum.com/blog",
        funding_stage="series-b",
        interest_level=InterestLevel.HOT,
        notes="Photonic quantum systems, room-temperature operation"
    )
    tracker.add_company(psiq)

    psiq_jobs = [
        JobOpening(
            job_id="psiq_hardware_001",
            company=psiq,
            job_title="Staff Hardware Design Engineer",
            job_url="https://psiquantum.com/careers/staff-hardware-design",
            posted_date="2026-06-14",
            description="Lead photonic hardware design. Drive silicon photonics integration, manage fabrication partnerships.",
            required_skills=["Silicon Photonics", "Optical Design", "Hardware Architecture"],
            nice_to_have_skills=["Quantum Optics", "Simulation", "Process Control"],
            salary_range="$155,000 - $180,000",
            project_variant_fit=ProjectVariant.SIMULATOR_FOCUSED
        ),
        JobOpening(
            job_id="psiq_mechanical_001",
            company=psiq,
            job_title="Senior Mechanical Design Engineer",
            job_url="https://psiquantum.com/careers/senior-mechanical-engineer",
            posted_date="2026-06-21",
            description="Design mechanical systems for photonic quantum hardware. Manage thermal stability, vibration isolation.",
            required_skills=["Mechanical Engineering", "Thermal Management", "CAD"],
            nice_to_have_skills=["Quantum Hardware", "Photonics"],
            salary_range="$140,000 - $170,000",
            project_variant_fit=ProjectVariant.CONSTRAINTS_FOCUSED
        ),
    ]
    for job in psiq_jobs:
        tracker.add_job(job)

    # =========================================================================
    # HOT TARGET: GOOGLE QUANTUM AI
    # =========================================================================
    google_q = Company(
        company_name="Google Quantum AI",
        industry="quantum_computing",
        stage=CompanyStage.ENTERPRISE,
        location="Mountain View, CA",
        remote_friendly=False,
        website="https://quantumai.google",
        github_org="quantumlib",
        technical_blog="https://quantumcomputing.googleblog.com",
        funding_stage="public",
        interest_level=InterestLevel.HOT,
        notes="Leading quantum research, strong architecture focus"
    )
    tracker.add_company(google_q)

    google_q_jobs = [
        JobOpening(
            job_id="google_q_atoms_001",
            company=google_q,
            job_title="Research Scientist - Neutral Atoms",
            job_url="https://careers.google.com/jobs/results/quantum-ai-neutral-atoms/",
            posted_date="2026-06-01",
            description="Research neutral atom quantum computing platforms. Develop control systems, error correction, optimization.",
            required_skills=["Physics PhD", "Quantum Computing", "Python", "Research"],
            nice_to_have_skills=["Publication Record", "Systems Design"],
            salary_range="$147,000 - $211,000",
            project_variant_fit=ProjectVariant.FULL_STACK
        ),
        JobOpening(
            job_id="google_q_optics_001",
            company=google_q,
            job_title="Research Scientist - Optical Engineering",
            job_url="https://careers.google.com/jobs/results/quantum-ai-optics/",
            posted_date="2026-06-05",
            description="Design optical systems for quantum computing. Research photonic controls, measurement architectures.",
            required_skills=["Optics PhD", "Photonics", "Experimental Design"],
            nice_to_have_skills=["Control Systems", "Simulation"],
            salary_range="$174,000 - $253,000",
            project_variant_fit=ProjectVariant.SIMULATOR_FOCUSED
        ),
        JobOpening(
            job_id="google_q_theory_001",
            company=google_q,
            job_title="Research Scientist - Device Theory",
            job_url="https://careers.google.com/jobs/results/quantum-ai-theory/",
            posted_date="2026-06-08",
            description="Theoretical research on quantum device physics, error models, control optimization.",
            required_skills=["Physics PhD", "Quantum Theory", "Simulation"],
            nice_to_have_skills=["Machine Learning", "Python"],
            salary_range="$141,000 - $202,000",
            project_variant_fit=ProjectVariant.SIMULATOR_FOCUSED
        ),
    ]
    for job in google_q_jobs:
        tracker.add_job(job)

    # =========================================================================
    # WARM TARGET: DIGICERT (PQC)
    # =========================================================================
    digicert = Company(
        company_name="DigiCert",
        industry="post_quantum_crypto",
        stage=CompanyStage.ESTABLISHED,
        location="Lehi, UT",
        remote_friendly=True,
        website="https://www.digicert.com",
        github_org="digicert",
        technical_blog="https://www.digicert.com/blog",
        funding_stage="public",
        interest_level=InterestLevel.WARM,
        notes="PKI standards leader, NIST PQC focus, governance expertise"
    )
    tracker.add_company(digicert)

    digicert_jobs = [
        JobOpening(
            job_id="digicert_pki_001",
            company=digicert,
            job_title="Senior PKI Engineer",
            job_url="https://www.digicert.com/careers/pki-engineer",
            posted_date="2026-06-25",
            description="Lead PKI architecture, cryptography standards, PQC migration planning. Work on governance, policy enforcement.",
            required_skills=["Cryptography", "PKI", "Standards", "Policy"],
            nice_to_have_skills=["Post-Quantum Crypto", "Governance", "Audit"],
            salary_range="$120,000 - $170,000",
            project_variant_fit=ProjectVariant.GOVERNANCE_FOCUSED
        ),
        JobOpening(
            job_id="digicert_crypto_001",
            company=digicert,
            job_title="Senior Software Engineer - Cryptography",
            job_url="https://www.digicert.com/careers/crypto-engineer",
            posted_date="2026-06-23",
            description="Implement cryptographic algorithms, manage HSM interfaces, validate compliance against standards.",
            required_skills=["Cryptography", "C++", "Python", "HSM"],
            nice_to_have_skills=["PQC", "Embedded Systems"],
            salary_range="$130,000 - $180,000",
            project_variant_fit=ProjectVariant.GOVERNANCE_FOCUSED
        ),
    ]
    for job in digicert_jobs:
        tracker.add_job(job)

    # =========================================================================
    # WARM TARGET: PQSHIELD (PQC)
    # =========================================================================
    pqshield = Company(
        company_name="PQShield",
        industry="post_quantum_crypto",
        stage=CompanyStage.STARTUP,
        location="Oxford, UK",
        remote_friendly=True,
        website="https://pqshield.com",
        github_org="pqshield",
        technical_blog="https://pqshield.com/blog",
        funding_stage="series-b",
        interest_level=InterestLevel.WARM,
        notes="Focused PQC implementation, startup environment"
    )
    tracker.add_company(pqshield)

    pqshield_jobs = [
        JobOpening(
            job_id="pqshield_software_001",
            company=pqshield,
            job_title="Software Engineer (Placement Year 2026)",
            job_url="https://pqshield.com/careers/placement-software",
            posted_date="2026-05-15",
            description="Implement PQC algorithms, optimize performance, integrate with production systems. 12-month placement role.",
            required_skills=["Python", "C++", "Cryptography Basics"],
            nice_to_have_skills=["Post-Quantum Crypto", "Performance Optimization"],
            salary_range="$25,000 - $35,000",  # Internship/placement rate
            project_variant_fit=ProjectVariant.CONSTRAINTS_FOCUSED
        ),
        JobOpening(
            job_id="pqshield_hardware_001",
            company=pqshield,
            job_title="Hardware Engineer (Placement Year 2026)",
            job_url="https://pqshield.com/careers/placement-hardware",
            posted_date="2026-05-15",
            description="Explore hardware acceleration of PQC algorithms. FPGA/GPU implementation, performance testing.",
            required_skills=["FPGA", "Verilog", "Python"],
            nice_to_have_skills=["Cryptography", "GPU Programming"],
            salary_range="$25,000 - $35,000",  # Internship/placement rate
            project_variant_fit=ProjectVariant.CONSTRAINTS_FOCUSED
        ),
    ]
    for job in pqshield_jobs:
        tracker.add_job(job)

    # =========================================================================
    # WARM TARGET: GOOGLE (Crypto / PQC)
    # =========================================================================
    google_pq = Company(
        company_name="Google (Post-Quantum Cryptography)",
        industry="post_quantum_crypto",
        stage=CompanyStage.ENTERPRISE,
        location="Mountain View, CA / Remote",
        remote_friendly=True,
        website="https://careers.google.com",
        github_org="google",
        technical_blog="https://security.googleblog.com",
        funding_stage="public",
        interest_level=InterestLevel.WARM,
        notes="Broad quantum-safe infrastructure initiative"
    )
    tracker.add_company(google_pq)

    google_pq_jobs = [
        JobOpening(
            job_id="google_pqc_analyst_001",
            company=google_pq,
            job_title="Post-Quantum Cryptography Analyst",
            job_url="https://careers.google.com/jobs/results/pqc-analyst/",
            posted_date="2026-06-12",
            description="Analyze NIST PQC standards, plan migration strategy, audit cryptographic implementations for quantum-safety.",
            required_skills=["Cryptography", "Security", "10+ years experience"],
            nice_to_have_skills=["Standards", "Governance", "Audit"],
            salary_range="$130,000 - $193,000",
            project_variant_fit=ProjectVariant.GOVERNANCE_FOCUSED
        ),
        JobOpening(
            job_id="google_infra_lead_001",
            company=google_pq,
            job_title="Technical Lead, Software Technical Infrastructure",
            job_url="https://careers.google.com/jobs/results/infra-lead/",
            posted_date="2026-06-09",
            description="Lead systems architecture for infrastructure team. Design quantum-safe deployment strategies.",
            required_skills=["Systems Architecture", "Leadership", "C++", "Python"],
            nice_to_have_skills=["Cryptography", "Large-scale Systems"],
            salary_range="$207,000 - $301,000",
            project_variant_fit=ProjectVariant.ARCHITECTURE_FOCUSED
        ),
    ]
    for job in google_pq_jobs:
        tracker.add_job(job)

    return tracker


def main():
    """Generate populated tracker and output as JSON."""
    tracker = create_populated_tracker()

    # Print summary
    summary = tracker.get_summary()
    print("=" * 80)
    print("JOB MARKET RESEARCH RESULTS: July 2026 Quantum Computing & PQC Market")
    print("=" * 80)
    print(f"\nCompanies tracked: {summary['total_companies_tracked']}")
    print(f"Job openings researched: {summary['total_jobs_found']}")
    print(f"Applications ready to submit: {summary['total_applications']}")
    print(f"\nHot target companies: {', '.join(summary['hot_companies'])}")

    print("\n" + "=" * 80)
    print("JOB OPENING SUMMARY BY COMPANY")
    print("=" * 80)

    for company_name, company in sorted(tracker.companies.items()):
        jobs_for_company = [j for j in tracker.job_openings.values() if j.company.company_name == company_name]
        if jobs_for_company:
            interest = company.interest_level.value.upper()
            print(f"\n{company_name} ({interest}, {company.stage.value})")
            print(f"  Industry: {company.industry}")
            print(f"  Remote: {company.remote_friendly}")
            print(f"  Positions found: {len(jobs_for_company)}")

            for job in jobs_for_company:
                variant = job.project_variant_fit.value if job.project_variant_fit else "FULL_STACK"
                salary = job.salary_range if job.salary_range else "Not listed"
                print(f"    • {job.job_title}")
                print(f"      Salary: {salary} | Variant: {variant}")

    print("\n" + "=" * 80)
    print("PROJECT VARIANT ALIGNMENT")
    print("=" * 80)

    variants_count = {}
    for job in tracker.job_openings.values():
        variant = job.project_variant_fit.value if job.project_variant_fit else "FULL_STACK"
        variants_count[variant] = variants_count.get(variant, 0) + 1

    for variant in sorted(variants_count.keys()):
        count = variants_count[variant]
        print(f"\n{variant}: {count} positions")
        matching_jobs = [j for j in tracker.job_openings.values()
                        if (j.project_variant_fit.value if j.project_variant_fit else "FULL_STACK") == variant]
        for job in matching_jobs[:3]:  # Show first 3
            print(f"  • {job.company.company_name} — {job.job_title}")

    print("\n" + "=" * 80)
    print("NEXT STEPS")
    print("=" * 80)
    print("""
1. Review the 21 job openings above
2. Select 10-15 that align with your interests and location preferences
3. For each selected job, review the project variant match
4. Read PROJECT_VARIANTS.md section for that variant
5. Customize cover letter using JOB_SEARCH_EXECUTION_GUIDE.md
6. Submit applications within 1-2 weeks
7. Track all applications in this tracker
8. Follow up 2 weeks after each submission
9. Prepare for interviews using variant-specific talking points
10. Negotiate offers using market salary data ($130-250K+ range)

The quantum computing job market in July 2026 is extremely hot. With 21 active
openings from high-priority companies and your Phase 1 implementation, you're
well-positioned for a strong interview rate and competitive offers.
    """)

    print("=" * 80)
    print("Tracker ready for use. Start with JOB_SEARCH_EXECUTION_GUIDE.md Phase 1.")
    print("=" * 80)


if __name__ == "__main__":
    main()
