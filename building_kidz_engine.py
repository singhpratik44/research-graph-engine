#!/usr/bin/env python3
"""
Building Kidz Worldwide — Franchise Operations Engine
Schema and operations for the Building Kidz creative arts & STEM network
"""

from dataclasses import dataclass, asdict, field
from enum import Enum
from typing import Dict, List, Optional
from datetime import datetime
import json


class FranchiseStatus(Enum):
    THRIVING = "thriving"
    WATCH = "watch"
    AT_RISK = "at_risk"


class BuildingKidzProgram(Enum):
    """Building Kidz core program offerings"""
    CREATIVE_ARTS_FOUNDATION = "creative_arts_foundation"
    STEM_INTEGRATION = "stem_integration"
    PERFORMING_ARTS = "performing_arts"
    ENRICHMENT_WORKSHOPS = "enrichment_workshops"


@dataclass
class BuildingKidzCenter:
    """Individual Building Kidz franchise center"""
    name: str
    region: str
    state: str
    address: Optional[str] = None

    # Operational health metrics (0-100)
    health: float = 75.0

    # Enrollment & capacity
    total_enrollment: int = 0
    age_groups_served: int = 3  # Typically Toddler, Preschool, PreK

    # Team & operations
    staff_count: int = 0
    instructor_experience_avg: float = 0.0  # years
    team_cohesion: float = 0.0  # 0-100, "chemistry"

    # Performance metrics
    enrollment_conversion: float = 0.0  # 0-1, lead to enrollment
    average_class_size: float = 0.0
    parent_satisfaction: float = 0.0  # 0-100
    instructor_retention: float = 0.0  # 0-100

    # Financial
    monthly_revenue: float = 0.0
    margin_percentage: float = 0.0

    # Programs & curriculum
    programs_offered: List[BuildingKidzProgram] = field(
        default_factory=lambda: [BuildingKidzProgram.CREATIVE_ARTS_FOUNDATION]
    )

    # Governance
    verified: bool = False
    last_audit: Optional[str] = None
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
    """Geographic region aggregating centers"""
    region_id: str
    label: str
    centers: List[BuildingKidzCenter] = field(default_factory=list)

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
            return {
                "enrollment_conversion": 0,
                "parent_satisfaction": 0,
                "team_cohesion": 0,
                "instructor_retention": 0,
            }

        return {
            "enrollment_conversion": sum(c.enrollment_conversion for c in self.centers) / n,
            "parent_satisfaction": sum(c.parent_satisfaction for c in self.centers) / n,
            "team_cohesion": sum(c.team_cohesion for c in self.centers) / n,
            "instructor_retention": sum(c.instructor_retention for c in self.centers) / n,
        }


@dataclass
class Program:
    """Building Kidz program offering"""
    program_id: str
    name: str
    program_type: BuildingKidzProgram
    age_groups: List[str] = field(default_factory=list)  # e.g., ["Toddler", "Preschool"]
    centers_offering: List[str] = field(default_factory=list)
    total_enrollment: int = 0
    instructor_count: int = 0
    monthly_revenue: float = 0.0


@dataclass
class SupportTicket:
    """Franchise partner support request"""
    ticket_id: str
    center_name: str
    category: str  # "curriculum", "operations", "marketing", "staff", "compliance", "technology"
    status: str  # "open", "in_progress", "resolved"
    created_at: str
    resolved_at: Optional[str] = None
    notes: str = ""


@dataclass
class ComplianceRecord:
    """FDD & regulatory compliance tracking"""
    center_name: str
    verification_status: str = "pending"  # pending, verified, flagged
    last_audit: Optional[str] = None
    fdd_item_details: str = ""  # FDD-specific notes
    notes: str = ""


class BuildingKidzEngine:
    """Core operations engine for Building Kidz Worldwide"""

    def __init__(self):
        self.brand_name = "Building Kidz Worldwide"
        self.mission = "Inspire creativity, confidence, and a love of learning in young children through integrated academics and performing arts."
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

    def add_center(self, region_id: str, center: BuildingKidzCenter) -> BuildingKidzCenter:
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
        ticket_id = f"BK-{len(self.support_tickets) + 1000:04d}"
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
            sum(c.total_enrollment for c in r.centers) for r in self.regions.values()
        )
        total_revenue = sum(
            sum(c.monthly_revenue for c in r.centers) for r in self.regions.values()
        )
        avg_health = (
            sum(r.avg_health() for r in self.regions.values()) / len(self.regions)
            if self.regions
            else 0
        )

        return {
            "brand": self.brand_name,
            "mission": self.mission,
            "total_regions": len(self.regions),
            "total_centers": total_centers,
            "total_enrollment": total_enrollment,
            "total_monthly_revenue": round(total_revenue, 2),
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

        def dataclass_to_dict(obj):
            d = asdict(obj)
            for key, value in d.items():
                if isinstance(value, Enum):
                    d[key] = value.value
                elif isinstance(value, list) and value and isinstance(value[0], Enum):
                    d[key] = [v.value if isinstance(v, Enum) else v for v in value]
            return d

        return {
            "brand_name": self.brand_name,
            "mission": self.mission,
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
