#!/usr/bin/env python3
"""
Quantum Computing Job Application Tracker

Tracks job applications, project tailoring, interview prep, and company research
for quantum/post-quantum computing opportunities.

Status: Active tracker for 2026-2027 hiring cycle
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum
from datetime import datetime, timezone
import json


# ============================================================================
# ENUMS
# ============================================================================

class JobStatus(str, Enum):
    """Application lifecycle status."""
    PROSPECT = "prospect"  # Researched but not applied
    APPLIED = "applied"  # Application submitted
    INTERVIEW_SCHEDULED = "interview_scheduled"
    INTERVIEW_COMPLETED = "interview_completed"
    OFFER_RECEIVED = "offer_received"
    OFFER_ACCEPTED = "offer_accepted"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"


class ProjectVariant(str, Enum):
    """Project presentation variants for different roles."""
    FULL_STACK = "full_stack"  # Complete quantum controller
    CONSTRAINTS_FOCUSED = "constraints_focused"  # Physics constraint engine
    SIMULATOR_FOCUSED = "simulator_focused"  # Trajectory simulators
    GOVERNANCE_FOCUSED = "governance_focused"  # Policy/approval workflows
    DASHBOARD_FOCUSED = "dashboard_focused"  # Observability & control surfaces
    ARCHITECTURE_FOCUSED = "architecture_focused"  # System design & contracts


class CompanyStage(str, Enum):
    """Company maturity classification."""
    STARTUP = "startup"  # <100 employees
    SCALE_UP = "scale_up"  # 100-500 employees
    ESTABLISHED = "established"  # 500-5000 employees
    ENTERPRISE = "enterprise"  # 5000+ employees


class InterestLevel(str, Enum):
    """Company attractiveness assessment."""
    HOT = "hot"  # Highest priority
    WARM = "warm"  # Strong interest
    COOL = "cool"  # Consider if good fit
    PASS = "pass"  # Not interested


# ============================================================================
# DATA MODELS
# ============================================================================

@dataclass
class Company:
    """Target company profile."""
    company_name: str
    industry: str  # "quantum_computing", "post_quantum_crypto", "quantum_security", etc.
    stage: CompanyStage
    location: str
    remote_friendly: bool
    website: str
    github_org: Optional[str] = None
    technical_blog: Optional[str] = None
    recent_papers: List[str] = field(default_factory=list)
    funding_stage: Optional[str] = None  # "pre-seed", "seed", "series-a", etc.
    interest_level: InterestLevel = InterestLevel.COOL
    notes: str = ""

    def to_dict(self):
        return {
            "company_name": self.company_name,
            "industry": self.industry,
            "stage": self.stage.value,
            "location": self.location,
            "remote_friendly": self.remote_friendly,
            "interest_level": self.interest_level.value,
            "funding_stage": self.funding_stage,
            "notes": self.notes
        }


@dataclass
class JobOpening:
    """Individual job posting."""
    job_id: str
    company: Company
    job_title: str
    job_url: str
    posted_date: str
    description: str
    required_skills: List[str]
    nice_to_have_skills: List[str]
    salary_range: Optional[str] = None
    compensation: Dict[str, Any] = field(default_factory=dict)
    project_variant_fit: ProjectVariant = ProjectVariant.FULL_STACK
    status: JobStatus = JobStatus.PROSPECT

    def to_dict(self):
        return {
            "job_id": self.job_id,
            "company": self.company.company_name,
            "job_title": self.job_title,
            "job_url": self.job_url,
            "posted_date": self.posted_date,
            "salary_range": self.salary_range,
            "project_variant_fit": self.project_variant_fit.value,
            "status": self.status.value
        }


@dataclass
class Application:
    """Job application with timeline and notes."""
    application_id: str
    job: JobOpening
    application_date: str
    status: JobStatus
    submitted_materials: List[str] = field(default_factory=list)  # ["resume", "cover_letter", "project_summary"]
    project_variant_used: ProjectVariant = ProjectVariant.FULL_STACK
    customizations_made: List[str] = field(default_factory=list)
    follow_up_dates: List[str] = field(default_factory=list)
    interview_notes: str = ""
    offer_details: Optional[Dict[str, Any]] = None
    outcome: str = ""  # Final result/rejection reason if applicable

    def to_dict(self):
        return {
            "application_id": self.application_id,
            "company": self.job.company.company_name,
            "job_title": self.job.job_title,
            "application_date": self.application_date,
            "status": self.status.value,
            "project_variant": self.project_variant_used.value,
            "customizations": self.customizations_made,
            "interview_notes": self.interview_notes
        }


@dataclass
class InterviewPrep:
    """Interview preparation tracking."""
    company_name: str
    interview_date: str
    interview_type: str  # "phone", "technical", "behavioral", "panel", "take_home"
    technical_topics: List[str] = field(default_factory=list)
    prepared_examples: List[str] = field(default_factory=list)
    questions_for_interviewer: List[str] = field(default_factory=list)
    mock_interview_score: Optional[float] = None
    notes: str = ""

    def to_dict(self):
        return {
            "company": self.company_name,
            "interview_date": self.interview_date,
            "interview_type": self.interview_type,
            "technical_topics": self.technical_topics,
            "mock_score": self.mock_interview_score
        }


# ============================================================================
# JOB TRACKER
# ============================================================================

class JobApplicationTracker:
    """Central tracker for all job applications."""

    def __init__(self):
        self.companies: Dict[str, Company] = {}
        self.job_openings: Dict[str, JobOpening] = {}
        self.applications: Dict[str, Application] = {}
        self.interview_prep: Dict[str, InterviewPrep] = {}
        self.created_at = datetime.now(timezone.utc).isoformat()

    def add_company(self, company: Company):
        """Register target company."""
        self.companies[company.company_name] = company

    def add_job(self, job: JobOpening):
        """Add job opening to tracker."""
        self.job_openings[job.job_id] = job

    def submit_application(self, application: Application):
        """Record submitted application."""
        application.status = JobStatus.APPLIED
        application.application_date = datetime.now(timezone.utc).isoformat()
        self.applications[application.application_id] = application

    def update_status(self, application_id: str, new_status: JobStatus, notes: str = ""):
        """Update application status."""
        if application_id in self.applications:
            self.applications[application_id].status = new_status
            if notes:
                self.applications[application_id].outcome = notes

    def add_interview_prep(self, prep: InterviewPrep):
        """Add interview preparation notes."""
        self.interview_prep[f"{prep.company_name}_{prep.interview_date}"] = prep

    def get_applications_by_status(self, status: JobStatus) -> List[Application]:
        """Get all applications with specific status."""
        return [a for a in self.applications.values() if a.status == status]

    def get_hot_companies(self) -> List[Company]:
        """Get highest-priority companies."""
        return [c for c in self.companies.values() if c.interest_level == InterestLevel.HOT]

    def get_summary(self) -> Dict[str, Any]:
        """Get tracker summary."""
        applications = list(self.applications.values())
        return {
            "total_companies_tracked": len(self.companies),
            "total_jobs_found": len(self.job_openings),
            "total_applications": len(applications),
            "applications_by_status": {
                status.value: len([a for a in applications if a.status == status])
                for status in JobStatus
            },
            "hot_companies": [c.company_name for c in self.get_hot_companies()],
            "upcoming_interviews": [
                {"company": p.company_name, "date": p.interview_date, "type": p.interview_type}
                for p in self.interview_prep.values()
            ],
            "created_at": self.created_at
        }

    def to_dict(self):
        """Serialize tracker to dict."""
        return {
            "created_at": self.created_at,
            "summary": self.get_summary(),
            "companies": {name: c.to_dict() for name, c in self.companies.items()},
            "applications": [a.to_dict() for a in self.applications.values()]
        }


# ============================================================================
# DEMO TRACKER
# ============================================================================

def create_demo_tracker() -> JobApplicationTracker:
    """Create tracker with initial high-priority targets."""
    tracker = JobApplicationTracker()

    # Hot targets: quantum computing companies actively hiring
    companies_to_track = [
        Company(
            company_name="Quantum Computing Inc.",
            industry="quantum_computing",
            stage=CompanyStage.STARTUP,
            location="Remote",
            remote_friendly=True,
            website="https://quantumcomputing.com",
            github_org="quantum-computing-inc",
            interest_level=InterestLevel.HOT,
            notes="Active in quantum control & optimization. Posted Full Stack role."
        ),
        Company(
            company_name="DigiCert (Post-Quantum)",
            industry="post_quantum_crypto",
            stage=CompanyStage.ESTABLISHED,
            location="Lehi, UT",
            remote_friendly=False,
            website="https://www.digicert.com",
            github_org="digicert",
            funding_stage="public",
            interest_level=InterestLevel.WARM,
            notes="PKI standards leader. Hiring for PQC standards and compliance."
        ),
        Company(
            company_name="Keysight Technologies",
            industry="quantum_systems",
            stage=CompanyStage.ENTERPRISE,
            location="Multiple (Pasadena, Calabasas, CA)",
            remote_friendly=False,
            website="https://www.keysight.com",
            github_org="keysight",
            interest_level=InterestLevel.WARM,
            notes="Quantum measurement systems. Strong hardware integration focus."
        ),
        Company(
            company_name="UC Berkeley - Quantum Research",
            industry="quantum_research",
            stage=CompanyStage.ESTABLISHED,
            location="Berkeley, CA",
            remote_friendly=False,
            website="https://quantum.berkeley.edu",
            interest_level=InterestLevel.COOL,
            notes="Academic position in quantum systems research."
        ),
    ]

    for company in companies_to_track:
        tracker.add_company(company)

    # Sample jobs from search results
    jobs_to_track = [
        JobOpening(
            job_id="qc_softeng_001",
            company=tracker.companies["Quantum Computing Inc."],
            job_title="Software Engineer, Full Stack - Quantum Control",
            job_url="https://to.indeed.com/aad9ff4mytfc",
            posted_date="2026-05-11",
            description="Develop quantum control software stack for simulation and real hardware.",
            required_skills=["Python", "Systems Design", "Simulation"],
            nice_to_have_skills=["Quantum Computing", "Real-time Systems", "Control Theory"],
            salary_range="$113,000 - $172,000",
            project_variant_fit=ProjectVariant.FULL_STACK
        ),
        JobOpening(
            job_id="digicert_pki_001",
            company=tracker.companies["DigiCert (Post-Quantum)"],
            job_title="Senior PKI Standards & Compliance Engineer",
            job_url="https://to.indeed.com/aazzlhrqlv69",
            posted_date="2026-06-10",
            description="Lead PQC standards development and compliance certification.",
            required_skills=["Cryptography", "Standards Development", "PKI"],
            nice_to_have_skills=["Post-Quantum Crypto", "Governance", "Policy"],
            salary_range="$145,000 - $195,000",
            project_variant_fit=ProjectVariant.GOVERNANCE_FOCUSED
        ),
        JobOpening(
            job_id="keysight_tech_001",
            company=tracker.companies["Keysight Technologies"],
            job_title="Technical Writer / Product Publications, Staff Engineer",
            job_url="https://to.indeed.com/aajnbc48zp2r",
            posted_date="2026-05-06",
            description="Document quantum measurement systems and control interfaces.",
            required_skills=["Technical Writing", "Systems Documentation", "Quantum Physics"],
            nice_to_have_skills=["Measurement Systems", "Signal Processing"],
            salary_range="$114,620 - $191,030",
            project_variant_fit=ProjectVariant.CONSTRAINTS_FOCUSED
        ),
    ]

    for job in jobs_to_track:
        tracker.add_job(job)

    return tracker


if __name__ == "__main__":
    tracker = create_demo_tracker()
    print(json.dumps(tracker.to_dict(), indent=2))
