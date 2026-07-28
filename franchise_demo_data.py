"""
Demo/Sample Data Generator for Franchise Engine
Provides realistic CodeNinjas and Building Kidz network data
"""

from franchise_engine import (
    FranchiseEngine, Center, Program, ProgramType, SupportTicket, ComplianceRecord
)
from datetime import datetime, timedelta


def create_codeninja_engine() -> FranchiseEngine:
    """Create a demo CodeNinjas franchise network"""
    engine = FranchiseEngine(brand_name="CodeNinjas")

    # Add sample centers across multiple regions
    regions_data = {
        "ca": "California",
        "tx": "Texas",
        "ny": "New York",
        "fl": "Florida",
        "co": "Colorado",
    }

    for region_id, region_name in regions_data.items():
        engine.add_region(region_id, region_name)

    # California Centers
    ca_centers = [
        Center(
            name="CodeNinjas San Francisco",
            region="ca",
            state="CA",
            address="123 Market St, SF, CA 94102",
            health=92.0,
            enrollment=145,
            staff_count=8,
            conversion_rate=0.78,
            chemistry=88.0,
            revenue_margin=8.5,
            retention=92.0,
            verified=True,
            programs=[ProgramType.CODING, ProgramType.STEM],
        ),
        Center(
            name="CodeNinjas Los Angeles",
            region="ca",
            state="CA",
            address="456 Wilshire Blvd, LA, CA 90010",
            health=85.0,
            enrollment=112,
            staff_count=6,
            conversion_rate=0.72,
            chemistry=80.0,
            revenue_margin=7.2,
            retention=88.0,
            verified=True,
            programs=[ProgramType.CODING, ProgramType.ENRICHMENT],
        ),
    ]

    for center in ca_centers:
        engine.add_center("ca", center)

    # Texas Centers
    tx_centers = [
        Center(
            name="CodeNinjas Austin",
            region="tx",
            state="TX",
            health=88.0,
            enrollment=98,
            staff_count=5,
            conversion_rate=0.75,
            chemistry=85.0,
            revenue_margin=7.8,
            retention=90.0,
            verified=True,
            programs=[ProgramType.CODING],
        ),
        Center(
            name="CodeNinjas Houston",
            region="tx",
            state="TX",
            health=72.0,
            enrollment=67,
            staff_count=4,
            conversion_rate=0.62,
            chemistry=70.0,
            revenue_margin=5.5,
            retention=78.0,
            verified=False,
            programs=[ProgramType.CODING],
        ),
    ]

    for center in tx_centers:
        engine.add_center("tx", center)

    # New York Centers
    ny_centers = [
        Center(
            name="CodeNinjas Manhattan",
            region="ny",
            state="NY",
            health=89.0,
            enrollment=134,
            staff_count=7,
            conversion_rate=0.81,
            chemistry=87.0,
            revenue_margin=9.2,
            retention=91.0,
            verified=True,
            programs=[ProgramType.CODING, ProgramType.STEM, ProgramType.ARTS],
        ),
        Center(
            name="CodeNinjas Brooklyn",
            region="ny",
            state="NY",
            health=58.0,
            enrollment=41,
            staff_count=3,
            conversion_rate=0.55,
            chemistry=62.0,
            revenue_margin=3.8,
            retention=65.0,
            verified=False,
            programs=[ProgramType.CODING],
        ),
    ]

    for center in ny_centers:
        engine.add_center("ny", center)

    # Florida Centers
    fl_centers = [
        Center(
            name="CodeNinjas Miami",
            region="fl",
            state="FL",
            health=80.0,
            enrollment=87,
            staff_count=5,
            conversion_rate=0.68,
            chemistry=78.0,
            revenue_margin=6.8,
            retention=82.0,
            verified=True,
            programs=[ProgramType.CODING, ProgramType.ENRICHMENT],
        ),
    ]

    for center in fl_centers:
        engine.add_center("fl", center)

    # Colorado Centers
    co_centers = [
        Center(
            name="CodeNinjas Denver",
            region="co",
            state="CO",
            health=81.0,
            enrollment=105,
            staff_count=6,
            conversion_rate=0.74,
            chemistry=82.0,
            revenue_margin=7.5,
            retention=85.0,
            verified=True,
            programs=[ProgramType.CODING, ProgramType.STEM],
        ),
    ]

    for center in co_centers:
        engine.add_center("co", center)

    # Add Programs
    programs_data = [
        Program(
            program_id="CN-101",
            name="Coding 101: Python Fundamentals",
            program_type=ProgramType.CODING,
            centers_offering=["CodeNinjas San Francisco", "CodeNinjas Austin", "CodeNinjas Manhattan"],
            enrollment=245,
            instructor_count=6,
            revenue_contribution=45000.0,
        ),
        Program(
            program_id="CN-102",
            name="Web Development Bootcamp",
            program_type=ProgramType.CODING,
            centers_offering=["CodeNinjas San Francisco", "CodeNinjas Los Angeles", "CodeNinjas Manhattan"],
            enrollment=187,
            instructor_count=5,
            revenue_contribution=38000.0,
        ),
        Program(
            program_id="CN-201",
            name="STEM Robotics Advanced",
            program_type=ProgramType.STEM,
            centers_offering=["CodeNinjas San Francisco", "CodeNinjas Denver", "CodeNinjas Manhattan"],
            enrollment=92,
            instructor_count=4,
            revenue_contribution=22000.0,
        ),
        Program(
            program_id="CN-301",
            name="Game Development 3D",
            program_type=ProgramType.ENRICHMENT,
            centers_offering=["CodeNinjas Los Angeles", "CodeNinjas Miami"],
            enrollment=68,
            instructor_count=3,
            revenue_contribution=18000.0,
        ),
    ]

    for program in programs_data:
        engine.add_program(program)

    # Add Support Tickets
    now = datetime.now()
    tickets_data = [
        ("CodeNinjas San Francisco", "marketing", "Need help with social media strategy for Q3", "resolved"),
        ("CodeNinjas Houston", "compliance", "FDD audit follow-up documentation needed", "in_progress"),
        ("CodeNinjas Brooklyn", "hr", "Instructor onboarding process review", "open"),
        ("CodeNinjas Manhattan", "technical", "Website CMS upgrade required", "resolved"),
        ("CodeNinjas Denver", "onboarding", "Initial franchise setup documentation", "completed"),
    ]

    for center_name, category, notes, status in tickets_data:
        ticket = engine.create_support_ticket(center_name, category, notes)
        ticket.status = status
        if status in ["resolved", "completed"]:
            ticket.resolved_at = (now - timedelta(days=2)).isoformat()

    # Add Compliance Records
    compliance_data = [
        ("CodeNinjas San Francisco", "verified", "2024-06-15"),
        ("CodeNinjas Los Angeles", "verified", "2024-05-20"),
        ("CodeNinjas Austin", "verified", "2024-07-01"),
        ("CodeNinjas Houston", "flagged", "2024-04-10"),
        ("CodeNinjas Manhattan", "verified", "2024-06-22"),
        ("CodeNinjas Brooklyn", "pending", None),
        ("CodeNinjas Miami", "verified", "2024-07-08"),
        ("CodeNinjas Denver", "verified", "2024-06-30"),
    ]

    for center_name, status, audit_date in compliance_data:
        record = ComplianceRecord(
            center_name=center_name,
            verification_status=status,
            last_audit=audit_date,
            notes="Per FDD Item 20: 244 authoritative units" if status == "verified" else "",
        )
        engine.compliance_records.append(record)

    return engine


def create_building_kidz_engine() -> FranchiseEngine:
    """Create a demo Building Kidz franchise network"""
    engine = FranchiseEngine(brand_name="Building Kidz")

    # Add regions
    regions_data = {
        "mid_atlantic": "Mid-Atlantic",
        "southeast": "Southeast",
        "midwest": "Midwest",
    }

    for region_id, region_name in regions_data.items():
        engine.add_region(region_id, region_name)

    # Mid-Atlantic Centers
    ma_centers = [
        Center(
            name="Building Kidz DC",
            region="mid_atlantic",
            state="DC",
            health=86.0,
            enrollment=76,
            staff_count=5,
            conversion_rate=0.71,
            chemistry=83.0,
            revenue_margin=7.1,
            retention=87.0,
            verified=True,
            programs=[ProgramType.ARTS, ProgramType.ENRICHMENT],
        ),
    ]

    for center in ma_centers:
        engine.add_center("mid_atlantic", center)

    # Southeast Centers
    se_centers = [
        Center(
            name="Building Kidz Atlanta",
            region="southeast",
            state="GA",
            health=82.0,
            enrollment=91,
            staff_count=6,
            conversion_rate=0.69,
            chemistry=81.0,
            revenue_margin=6.9,
            retention=84.0,
            verified=True,
            programs=[ProgramType.ARTS, ProgramType.ENRICHMENT],
        ),
        Center(
            name="Building Kidz Charlotte",
            region="southeast",
            state="NC",
            health=75.0,
            enrollment=58,
            staff_count=4,
            conversion_rate=0.64,
            chemistry=75.0,
            revenue_margin=5.9,
            retention=76.0,
            verified=True,
            programs=[ProgramType.ARTS],
        ),
    ]

    for center in se_centers:
        engine.add_center("southeast", center)

    # Midwest Centers
    mw_centers = [
        Center(
            name="Building Kidz Chicago",
            region="midwest",
            state="IL",
            health=84.0,
            enrollment=103,
            staff_count=6,
            conversion_rate=0.70,
            chemistry=84.0,
            revenue_margin=7.2,
            retention=86.0,
            verified=True,
            programs=[ProgramType.ARTS, ProgramType.STEM, ProgramType.ENRICHMENT],
        ),
    ]

    for center in mw_centers:
        engine.add_center("midwest", center)

    # Add Programs
    programs_data = [
        Program(
            program_id="BK-101",
            name="Creative Arts Foundation",
            program_type=ProgramType.ARTS,
            centers_offering=["Building Kidz DC", "Building Kidz Atlanta", "Building Kidz Charlotte", "Building Kidz Chicago"],
            enrollment=198,
            instructor_count=5,
            revenue_contribution=32000.0,
        ),
        Program(
            program_id="BK-201",
            name="STEM + Arts Integration",
            program_type=ProgramType.STEM,
            centers_offering=["Building Kidz Chicago"],
            enrollment=45,
            instructor_count=2,
            revenue_contribution=12000.0,
        ),
    ]

    for program in programs_data:
        engine.add_program(program)

    return engine


if __name__ == "__main__":
    # For testing
    cn_engine = create_codeninja_engine()
    print("CodeNinjas Network Summary:", cn_engine.network_summary())

    bk_engine = create_building_kidz_engine()
    print("Building Kidz Network Summary:", bk_engine.network_summary())
