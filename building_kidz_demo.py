#!/usr/bin/env python3
"""
Building Kidz Worldwide — Demo Network Data
Sample franchise network with realistic centers across US regions
"""

from building_kidz_engine import (
    BuildingKidzEngine, BuildingKidzCenter, Program, BuildingKidzProgram,
    SupportTicket, ComplianceRecord
)
from datetime import datetime, timedelta


def create_building_kidz_network() -> BuildingKidzEngine:
    """Create a comprehensive Building Kidz franchise network"""
    engine = BuildingKidzEngine()

    # Regional Structure
    regions_data = {
        "mid_atlantic": "Mid-Atlantic (DC, MD, VA)",
        "southeast": "Southeast (GA, NC, SC)",
        "midwest": "Midwest (IL, MI, OH)",
        "southwest": "Southwest (TX, AZ)",
        "west_coast": "West Coast (CA, WA)",
    }

    for region_id, region_name in regions_data.items():
        engine.add_region(region_id, region_name)

    # ========== MID-ATLANTIC CENTERS ==========
    engine.add_center(
        "mid_atlantic",
        BuildingKidzCenter(
            name="Building Kidz — Washington DC",
            region="mid_atlantic",
            state="DC",
            address="2100 Pennsylvania Ave NW, Washington, DC 20037",
            health=88.0,
            total_enrollment=127,
            age_groups_served=3,
            staff_count=11,
            instructor_experience_avg=6.2,
            team_cohesion=86.0,
            enrollment_conversion=0.76,
            average_class_size=12.5,
            parent_satisfaction=92.0,
            instructor_retention=94.0,
            monthly_revenue=42500.0,
            margin_percentage=18.5,
            programs_offered=[
                BuildingKidzProgram.CREATIVE_ARTS_FOUNDATION,
                BuildingKidzProgram.PERFORMING_ARTS,
                BuildingKidzProgram.ENRICHMENT_WORKSHOPS,
            ],
            verified=True,
            last_audit="2024-06-15",
        ),
    )

    engine.add_center(
        "mid_atlantic",
        BuildingKidzCenter(
            name="Building Kidz — Baltimore",
            region="mid_atlantic",
            state="MD",
            health=74.0,
            total_enrollment=89,
            staff_count=8,
            instructor_experience_avg=4.1,
            team_cohesion=72.0,
            enrollment_conversion=0.68,
            average_class_size=11.0,
            parent_satisfaction=85.0,
            instructor_retention=80.0,
            monthly_revenue=28300.0,
            margin_percentage=14.2,
            programs_offered=[BuildingKidzProgram.CREATIVE_ARTS_FOUNDATION],
            verified=True,
            last_audit="2024-05-20",
        ),
    )

    # ========== SOUTHEAST CENTERS ==========
    engine.add_center(
        "southeast",
        BuildingKidzCenter(
            name="Building Kidz — Atlanta",
            region="southeast",
            state="GA",
            health=82.0,
            total_enrollment=145,
            staff_count=13,
            instructor_experience_avg=5.8,
            team_cohesion=84.0,
            enrollment_conversion=0.73,
            average_class_size=13.0,
            parent_satisfaction=89.0,
            instructor_retention=88.0,
            monthly_revenue=48900.0,
            margin_percentage=17.8,
            programs_offered=[
                BuildingKidzProgram.CREATIVE_ARTS_FOUNDATION,
                BuildingKidzProgram.STEM_INTEGRATION,
                BuildingKidzProgram.ENRICHMENT_WORKSHOPS,
            ],
            verified=True,
            last_audit="2024-07-01",
        ),
    )

    engine.add_center(
        "southeast",
        BuildingKidzCenter(
            name="Building Kidz — Charlotte",
            region="southeast",
            state="NC",
            health=76.0,
            total_enrollment=103,
            staff_count=9,
            instructor_experience_avg=3.5,
            team_cohesion=75.0,
            enrollment_conversion=0.65,
            average_class_size=11.5,
            parent_satisfaction=83.0,
            instructor_retention=82.0,
            monthly_revenue=34700.0,
            margin_percentage=15.1,
            programs_offered=[
                BuildingKidzProgram.CREATIVE_ARTS_FOUNDATION,
                BuildingKidzProgram.ENRICHMENT_WORKSHOPS,
            ],
            verified=True,
            last_audit="2024-06-10",
        ),
    )

    engine.add_center(
        "southeast",
        BuildingKidzCenter(
            name="Building Kidz — Charleston",
            region="southeast",
            state="SC",
            health=58.0,
            total_enrollment=62,
            staff_count=6,
            instructor_experience_avg=2.3,
            team_cohesion=62.0,
            enrollment_conversion=0.52,
            average_class_size=9.5,
            parent_satisfaction=75.0,
            instructor_retention=68.0,
            monthly_revenue=18500.0,
            margin_percentage=8.5,
            programs_offered=[BuildingKidzProgram.CREATIVE_ARTS_FOUNDATION],
            verified=False,
            last_audit="2024-03-15",
        ),
    )

    # ========== MIDWEST CENTERS ==========
    engine.add_center(
        "midwest",
        BuildingKidzCenter(
            name="Building Kidz — Chicago",
            region="midwest",
            state="IL",
            health=86.0,
            total_enrollment=156,
            staff_count=14,
            instructor_experience_avg=6.7,
            team_cohesion=87.0,
            enrollment_conversion=0.75,
            average_class_size=13.5,
            parent_satisfaction=91.0,
            instructor_retention=92.0,
            monthly_revenue=51200.0,
            margin_percentage=19.2,
            programs_offered=[
                BuildingKidzProgram.CREATIVE_ARTS_FOUNDATION,
                BuildingKidzProgram.PERFORMING_ARTS,
                BuildingKidzProgram.STEM_INTEGRATION,
                BuildingKidzProgram.ENRICHMENT_WORKSHOPS,
            ],
            verified=True,
            last_audit="2024-07-08",
        ),
    )

    engine.add_center(
        "midwest",
        BuildingKidzCenter(
            name="Building Kidz — Ann Arbor",
            region="midwest",
            state="MI",
            health=79.0,
            total_enrollment=95,
            staff_count=9,
            instructor_experience_avg=4.4,
            team_cohesion=78.0,
            enrollment_conversion=0.70,
            average_class_size=12.0,
            parent_satisfaction=87.0,
            instructor_retention=85.0,
            monthly_revenue=32100.0,
            margin_percentage=16.3,
            programs_offered=[
                BuildingKidzProgram.CREATIVE_ARTS_FOUNDATION,
                BuildingKidzProgram.ENRICHMENT_WORKSHOPS,
            ],
            verified=True,
            last_audit="2024-06-22",
        ),
    )

    # ========== SOUTHWEST CENTERS ==========
    engine.add_center(
        "southwest",
        BuildingKidzCenter(
            name="Building Kidz — Austin",
            region="southwest",
            state="TX",
            health=84.0,
            total_enrollment=138,
            staff_count=12,
            instructor_experience_avg=5.5,
            team_cohesion=83.0,
            enrollment_conversion=0.74,
            average_class_size=12.8,
            parent_satisfaction=90.0,
            instructor_retention=89.0,
            monthly_revenue=46800.0,
            margin_percentage=18.1,
            programs_offered=[
                BuildingKidzProgram.CREATIVE_ARTS_FOUNDATION,
                BuildingKidzProgram.STEM_INTEGRATION,
                BuildingKidzProgram.ENRICHMENT_WORKSHOPS,
            ],
            verified=True,
            last_audit="2024-07-05",
        ),
    )

    engine.add_center(
        "southwest",
        BuildingKidzCenter(
            name="Building Kidz — Phoenix",
            region="southwest",
            state="AZ",
            health=72.0,
            total_enrollment=81,
            staff_count=7,
            instructor_experience_avg=3.2,
            team_cohesion=70.0,
            enrollment_conversion=0.62,
            average_class_size=11.0,
            parent_satisfaction=80.0,
            instructor_retention=76.0,
            monthly_revenue=27500.0,
            margin_percentage=12.8,
            programs_offered=[BuildingKidzProgram.CREATIVE_ARTS_FOUNDATION],
            verified=True,
            last_audit="2024-04-30",
        ),
    )

    # ========== WEST COAST CENTERS ==========
    engine.add_center(
        "west_coast",
        BuildingKidzCenter(
            name="Building Kidz — San Francisco Bay Area",
            region="west_coast",
            state="CA",
            health=87.0,
            total_enrollment=142,
            staff_count=13,
            instructor_experience_avg=6.1,
            team_cohesion=85.0,
            enrollment_conversion=0.77,
            average_class_size=13.2,
            parent_satisfaction=93.0,
            instructor_retention=91.0,
            monthly_revenue=49700.0,
            margin_percentage=19.5,
            programs_offered=[
                BuildingKidzProgram.CREATIVE_ARTS_FOUNDATION,
                BuildingKidzProgram.PERFORMING_ARTS,
                BuildingKidzProgram.STEM_INTEGRATION,
            ],
            verified=True,
            last_audit="2024-07-12",
        ),
    )

    engine.add_center(
        "west_coast",
        BuildingKidzCenter(
            name="Building Kidz — Seattle",
            region="west_coast",
            state="WA",
            health=80.0,
            total_enrollment=112,
            staff_count=10,
            instructor_experience_avg=5.0,
            team_cohesion=81.0,
            enrollment_conversion=0.71,
            average_class_size=12.0,
            parent_satisfaction=88.0,
            instructor_retention=86.0,
            monthly_revenue=38200.0,
            margin_percentage=16.9,
            programs_offered=[
                BuildingKidzProgram.CREATIVE_ARTS_FOUNDATION,
                BuildingKidzProgram.ENRICHMENT_WORKSHOPS,
            ],
            verified=True,
            last_audit="2024-06-28",
        ),
    )

    # ========== PROGRAMS ==========
    programs = [
        Program(
            program_id="BK-101",
            name="Creative Arts Foundation",
            program_type=BuildingKidzProgram.CREATIVE_ARTS_FOUNDATION,
            age_groups=["Toddler", "Preschool", "PreK"],
            centers_offering=[
                "Building Kidz — Washington DC",
                "Building Kidz — Baltimore",
                "Building Kidz — Atlanta",
                "Building Kidz — Charlotte",
                "Building Kidz — Charleston",
                "Building Kidz — Chicago",
                "Building Kidz — Ann Arbor",
                "Building Kidz — Austin",
                "Building Kidz — Phoenix",
                "Building Kidz — San Francisco Bay Area",
                "Building Kidz — Seattle",
            ],
            total_enrollment=1015,
            instructor_count=93,
            monthly_revenue=320000.0,
        ),
        Program(
            program_id="BK-201",
            name="Performing Arts Integration",
            program_type=BuildingKidzProgram.PERFORMING_ARTS,
            age_groups=["Preschool", "PreK"],
            centers_offering=[
                "Building Kidz — Washington DC",
                "Building Kidz — Chicago",
                "Building Kidz — San Francisco Bay Area",
            ],
            total_enrollment=187,
            instructor_count=18,
            monthly_revenue=58000.0,
        ),
        Program(
            program_id="BK-301",
            name="STEM Integration Workshop",
            program_type=BuildingKidzProgram.STEM_INTEGRATION,
            age_groups=["Preschool", "PreK"],
            centers_offering=[
                "Building Kidz — Atlanta",
                "Building Kidz — Chicago",
                "Building Kidz — Austin",
                "Building Kidz — San Francisco Bay Area",
            ],
            total_enrollment=142,
            instructor_count=16,
            monthly_revenue=43000.0,
        ),
        Program(
            program_id="BK-401",
            name="Enrichment Workshops",
            program_type=BuildingKidzProgram.ENRICHMENT_WORKSHOPS,
            age_groups=["Toddler", "Preschool", "PreK"],
            centers_offering=[
                "Building Kidz — Washington DC",
                "Building Kidz — Charlotte",
                "Building Kidz — Chicago",
                "Building Kidz — Ann Arbor",
                "Building Kidz — Austin",
                "Building Kidz — Seattle",
            ],
            total_enrollment=268,
            instructor_count=28,
            monthly_revenue=82000.0,
        ),
    ]

    for program in programs:
        engine.add_program(program)

    # ========== SUPPORT TICKETS ==========
    now = datetime.now()
    support_data = [
        ("Building Kidz — Washington DC", "curriculum", "Need resources for seasonal arts integration", "resolved", -3),
        ("Building Kidz — Baltimore", "staff", "Instructor development workshop needed", "in_progress", 0),
        ("Building Kidz — Charleston", "operations", "Enrollment marketing strategy review", "open", 0),
        ("Building Kidz — Chicago", "technology", "Platform update for registration system", "resolved", -5),
        ("Building Kidz — Austin", "compliance", "Updated FDD documentation review", "open", 0),
        ("Building Kidz — Phoenix", "curriculum", "STEM program expansion consultation", "in_progress", 0),
    ]

    for center_name, category, notes, status, days_ago in support_data:
        ticket = engine.create_support_ticket(center_name, category, notes)
        ticket.status = status
        if days_ago < 0:
            ticket.resolved_at = (now + timedelta(days=days_ago)).isoformat()

    # ========== COMPLIANCE RECORDS ==========
    compliance_data = [
        ("Building Kidz — Washington DC", "verified", "2024-06-15"),
        ("Building Kidz — Baltimore", "verified", "2024-05-20"),
        ("Building Kidz — Atlanta", "verified", "2024-07-01"),
        ("Building Kidz — Charlotte", "verified", "2024-06-10"),
        ("Building Kidz — Charleston", "flagged", "2024-03-15"),
        ("Building Kidz — Chicago", "verified", "2024-07-08"),
        ("Building Kidz — Ann Arbor", "verified", "2024-06-22"),
        ("Building Kidz — Austin", "verified", "2024-07-05"),
        ("Building Kidz — Phoenix", "verified", "2024-04-30"),
        ("Building Kidz — San Francisco Bay Area", "verified", "2024-07-12"),
        ("Building Kidz — Seattle", "verified", "2024-06-28"),
    ]

    for center_name, status, audit_date in compliance_data:
        record = ComplianceRecord(
            center_name=center_name,
            verification_status=status,
            last_audit=audit_date,
            fdd_item_details="Building Kidz franchise operations verified under FDD Item 20",
            notes="Full compliance audit completed" if status == "verified" else "Remediation in progress"
        )
        engine.compliance_records.append(record)

    return engine


if __name__ == "__main__":
    engine = create_building_kidz_network()
    print("Building Kidz Network Summary:")
    print(engine.network_summary())
