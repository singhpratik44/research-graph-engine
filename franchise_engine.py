"""
Franchise Engine Generator — Core Data Model & Operations
Supports CodeNinjas, Building Kidz, and multi-brand franchise networks
"""

from dataclasses import dataclass, asdict, field
from enum import Enum
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import json


class FranchiseStatus(Enum):
    THRIVING = "thriving"
    WATCH = "watch"
    AT_RISK = "at_risk"


class ProgramType(Enum):
    CODING = "coding"
    ARTS = "arts"
    STEM = "stem"
    ENRICHMENT = "enrichment"


@dataclass
class Center:
    """Individual franchise center/location"""
    name: str
    region: str
    state: str
    address: Optional[str] = None
    health: float = 75.0  # 0-100 score
    enrollment: int = 0
    staff_count: int = 0
    conversion_rate: float = 0.0  # avg conversions
    chemistry: float = 0.0  # team cohesion 0-100
    revenue_margin: float = 0.0  # EB (earnings before) 0-20
    retention: float = 0.0  # parent/student retention 0-100
    verified: bool = False
    programs: List[ProgramType] = field(default_factory=lambda: [ProgramType.CODING])
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def condition(self) -> FranchiseStatus:
        """Derive operational condition from health score"""
        if self.health >= 80:
            return FranchiseStatus.THRIVING
        elif self.health >= 60:
            return FranchiseStatus.WATCH
        else:
            return FranchiseStatus.AT_RISK


@dataclass
class Region:
    """Geographic region aggregating multiple centers"""
    region_id: str
    label: str
    centers: List[Center] = field(default_factory=list)

    def avg_health(self) -> float:
        if not self.centers:
            return 0.0
        return sum(c.health for c in self.centers) / len(self.centers)

    def condition(self) -> FranchiseStatus:
        avg = self.avg_health()
        if avg >= 80:
            return FranchiseStatus.THRIVING
        elif avg >= 60:
            return FranchiseStatus.WATCH
        else:
            return FranchiseStatus.AT_RISK

    def metrics(self) -> Dict:
        """Aggregate metrics across region"""
        n = len(self.centers)
        if n == 0:
            return {"engagement": 0, "margin": 0, "staffing": 0, "community": 0}

        return {
            "engagement": sum(c.conversion_rate for c in self.centers) / n,
            "margin": sum(c.revenue_margin for c in self.centers) / n,
            "staffing": sum(c.chemistry for c in self.centers) / n,
            "community": sum(c.retention for c in self.centers) / n,
        }


@dataclass
class Program:
    """Training/service program offered by centers"""
    program_id: str
    name: str
    program_type: ProgramType
    centers_offering: List[str] = field(default_factory=list)  # center names
    enrollment: int = 0
    instructor_count: int = 0
    revenue_contribution: float = 0.0


@dataclass
class SupportTicket:
    """Operational support request"""
    ticket_id: str
    center_name: str
    category: str  # "onboarding", "compliance", "marketing", "technical", "hr"
    status: str  # "open", "in_progress", "resolved"
    created_at: str
    resolved_at: Optional[str] = None
    notes: str = ""


@dataclass
class ComplianceRecord:
    """FDD & regulatory compliance tracking"""
    center_name: str
    fdd_item_20: int = 244  # canonical count
    verification_status: str = "pending"  # pending, verified, flagged
    last_audit: Optional[str] = None
    notes: str = ""


class FranchiseEngine:
    """Core franchise operations engine"""

    def __init__(self, brand_name: str = "CodeNinjas"):
        self.brand_name = brand_name
        self.regions: Dict[str, Region] = {}
        self.programs: Dict[str, Program] = {}
        self.support_tickets: List[SupportTicket] = []
        self.compliance_records: List[ComplianceRecord] = []
        self.created_at = datetime.now().isoformat()

    def add_region(self, region_id: str, label: str) -> Region:
        """Add a region to the network"""
        region = Region(region_id=region_id, label=label)
        self.regions[region_id] = region
        return region

    def add_center(self, region_id: str, center: Center) -> Center:
        """Add a center to a region"""
        if region_id not in self.regions:
            self.add_region(region_id, region_id.upper())
        self.regions[region_id].centers.append(center)
        return center

    def add_program(self, program: Program) -> Program:
        """Register a program"""
        self.programs[program.program_id] = program
        return program

    def create_support_ticket(
        self, center_name: str, category: str, notes: str = ""
    ) -> SupportTicket:
        """Create a support request"""
        ticket_id = f"TKT-{len(self.support_tickets) + 1000:04d}"
        ticket = SupportTicket(
            ticket_id=ticket_id,
            center_name=center_name,
            category=category,
            status="open",
            created_at=datetime.now().isoformat(),
            notes=notes,
        )
        self.support_tickets.append(ticket)
        return ticket

    def resolve_ticket(self, ticket_id: str, notes: str = "") -> Optional[SupportTicket]:
        """Mark ticket as resolved"""
        for ticket in self.support_tickets:
            if ticket.ticket_id == ticket_id:
                ticket.status = "resolved"
                ticket.resolved_at = datetime.now().isoformat()
                if notes:
                    ticket.notes = notes
                return ticket
        return None

    def network_summary(self) -> Dict:
        """High-level network overview"""
        total_centers = sum(len(r.centers) for r in self.regions.values())
        total_enrollment = sum(
            sum(c.enrollment for c in r.centers) for r in self.regions.values()
        )
        avg_health = (
            sum(r.avg_health() for r in self.regions.values()) / len(self.regions)
            if self.regions
            else 0
        )

        return {
            "brand": self.brand_name,
            "total_regions": len(self.regions),
            "total_centers": total_centers,
            "total_enrollment": total_enrollment,
            "avg_network_health": round(avg_health, 2),
            "thriving_count": sum(
                1 for r in self.regions.values()
                if r.condition() == FranchiseStatus.THRIVING
            ),
            "watch_count": sum(
                1 for r in self.regions.values()
                if r.condition() == FranchiseStatus.WATCH
            ),
            "at_risk_count": sum(
                1 for r in self.regions.values()
                if r.condition() == FranchiseStatus.AT_RISK
            ),
            "open_support_tickets": sum(
                1 for t in self.support_tickets if t.status == "open"
            ),
        }

    def to_dict(self) -> Dict:
        """Serialize engine state to dict"""
        # Helper to convert dataclass to dict with enum support
        def dataclass_to_dict(obj):
            d = asdict(obj)
            # Convert enums to their values
            for key, value in d.items():
                if isinstance(value, Enum):
                    d[key] = value.value
                elif isinstance(value, list) and value and isinstance(value[0], Enum):
                    d[key] = [v.value if isinstance(v, Enum) else v for v in value]
            return d

        return {
            "brand_name": self.brand_name,
            "created_at": self.created_at,
            "regions": {
                rid: {
                    "label": r.label,
                    "centers": [dataclass_to_dict(c) for c in r.centers],
                    "metrics": r.metrics(),
                }
                for rid, r in self.regions.items()
            },
            "programs": {
                pid: dataclass_to_dict(p) for pid, p in self.programs.items()
            },
            "support_tickets": [dataclass_to_dict(t) for t in self.support_tickets],
            "compliance_records": [dataclass_to_dict(c) for c in self.compliance_records],
        }

    def to_json(self) -> str:
        """Export as JSON"""
        return json.dumps(self.to_dict(), indent=2, default=str)
