#!/usr/bin/env python3
"""
Building Kidz Worldwide — Growth & Franchise Engine
Deterministic data models for franchisee pipeline, enrollment, launch success, and marketing ROI.
All figures based on ECE industry benchmarks: 5-min response rule, $60-150 CPI, 50-75% conversion, 60-70% Jan-Mar seasonality.
"""

from dataclasses import dataclass, asdict, field
from enum import Enum
from datetime import datetime, timedelta
from typing import List, Optional
import json


class FranchiseeStatus(Enum):
    INQUIRY = "inquiry"
    QUALIFIED = "qualified"
    NEGOTIATION = "negotiation"
    SIGNED = "signed"
    OPENING = "opening"
    OPENED = "opened"


class CenterStatus(Enum):
    PLANNING = "planning"
    LAUNCHING = "launching"
    OPERATIONAL = "operational"
    MATURE = "mature"


class LaunchStatus(Enum):
    PLANNING = "planning"
    LAUNCHING = "launching"
    ACTIVE = "active"
    CLOSED = "closed"


class MarketingChannel(Enum):
    DIGITAL = "digital"
    LOCAL = "local"
    EVENTS = "events"
    PARTNERSHIPS = "partnerships"
    FRANCHISEE_RUN = "franchisee_run"


class ProfitabilityStatus(Enum):
    PROFITABLE = "profitable"
    BREAKING_EVEN = "breaking_even"
    LOSING_MONEY = "losing_money"


class EnrollmentTrajectory(Enum):
    GROWING = "growing"
    FLAT = "flat"
    DECLINING = "declining"


@dataclass
class FranchiseeProspect:
    """Franchisee pipeline prospect from inquiry through opening"""
    prospect_id: str
    company_name: str
    contact_person: str
    status: FranchiseeStatus
    inquiry_date: str
    territory: str
    investment_capacity: str  # under_250k, 250k_500k, 500k_1m, over_1m
    experience_level: str  # franchise_novice, franchise_veteran, education_background
    projected_open_date: Optional[str] = None
    notes: Optional[str] = None
    last_communication_date: str = None

    def to_dict(self):
        return {
            **asdict(self),
            "status": self.status.value,
        }


@dataclass
class EnrollmentCenter:
    """Enrollment performance metrics for a single operating center"""
    center_id: str
    center_name: str
    state: str
    opening_date: str
    status: CenterStatus
    monthly_inquiries: int
    inquiry_to_enrollment_conversion_rate: float  # 0.0-1.0
    current_enrollment: int
    capacity: int
    monthly_tuition_revenue: float
    franchisee_satisfaction: float  # 0-10

    def to_dict(self):
        return {
            **asdict(self),
            "status": self.status.value,
        }


@dataclass
class CenterLaunch:
    """Launch success tracking for new centers"""
    center_id: str
    franchisee_id: str
    soft_opening_date: str
    grand_opening_date: str
    ninety_day_target: int
    enrollment_at_30_days: int
    enrollment_at_60_days: int
    enrollment_at_90_days: int
    vs_target_pct: float
    status: LaunchStatus

    def to_dict(self):
        return {
            **asdict(self),
            "status": self.status.value,
        }


@dataclass
class MarketingCampaign:
    """Marketing campaign ROI tracking"""
    campaign_id: str
    campaign_name: str
    channel: MarketingChannel
    budget: float
    inquiries_generated: int
    cost_per_inquiry: float
    conversions: int
    roi_pct: float

    def to_dict(self):
        return {
            **asdict(self),
            "channel": self.channel.value,
        }


@dataclass
class FranchiseePerformance:
    """Franchisee health & profitability tracking"""
    franchisee_id: str
    state: str
    months_operating: int
    enrollment_trajectory: EnrollmentTrajectory
    profitability_status: ProfitabilityStatus
    satisfaction_score: float  # 0-10
    at_risk: bool

    def to_dict(self):
        return {
            **asdict(self),
            "enrollment_trajectory": self.enrollment_trajectory.value,
            "profitability_status": self.profitability_status.value,
        }


@dataclass
class BuildingKidzGrowthEngine:
    """Franchise growth engine: tracks pipelines, launches, marketing ROI, franchisee health"""
    prospects: List[FranchiseeProspect] = field(default_factory=list)
    enrollment_centers: List[EnrollmentCenter] = field(default_factory=list)
    launches: List[CenterLaunch] = field(default_factory=list)
    marketing_campaigns: List[MarketingCampaign] = field(default_factory=list)
    franchisee_performance: List[FranchiseePerformance] = field(default_factory=list)

    def add_prospect(self, prospect: FranchiseeProspect):
        self.prospects.append(prospect)

    def add_enrollment_center(self, center: EnrollmentCenter):
        self.enrollment_centers.append(center)

    def add_launch(self, launch: CenterLaunch):
        self.launches.append(launch)

    def add_marketing_campaign(self, campaign: MarketingCampaign):
        self.marketing_campaigns.append(campaign)

    def add_franchisee_performance(self, performance: FranchiseePerformance):
        self.franchisee_performance.append(performance)

    def pipeline_summary(self):
        """Summary of franchisee pipeline"""
        by_status = {}
        for p in self.prospects:
            key = p.status.value
            by_status[key] = by_status.get(key, 0) + 1

        return {
            "total_prospects": len(self.prospects),
            "by_status": by_status,
            "signed": by_status.get("signed", 0),
            "opening": by_status.get("opening", 0),
            "opened": by_status.get("opened", 0),
        }

    def enrollment_summary(self):
        """Summary of network-wide enrollment performance"""
        total_enrolled = sum(c.current_enrollment for c in self.enrollment_centers)
        total_inquiries = sum(c.monthly_inquiries for c in self.enrollment_centers)
        avg_conversion = (
            sum(c.inquiry_to_enrollment_conversion_rate for c in self.enrollment_centers) /
            len(self.enrollment_centers) if self.enrollment_centers else 0
        )
        total_capacity = sum(c.capacity for c in self.enrollment_centers)
        total_revenue = sum(c.monthly_tuition_revenue for c in self.enrollment_centers)
        avg_satisfaction = (
            sum(c.franchisee_satisfaction for c in self.enrollment_centers) /
            len(self.enrollment_centers) if self.enrollment_centers else 0
        )

        return {
            "total_enrolled": total_enrolled,
            "total_monthly_inquiries": total_inquiries,
            "avg_conversion_rate": round(avg_conversion, 2),
            "total_capacity": total_capacity,
            "capacity_utilization_pct": round((total_enrolled / total_capacity * 100), 1) if total_capacity > 0 else 0,
            "total_monthly_revenue": total_revenue,
            "avg_franchisee_satisfaction": round(avg_satisfaction, 1),
            "number_of_centers": len(self.enrollment_centers),
        }

    def launch_summary(self):
        """Summary of launch success"""
        if not self.launches:
            return {"total_launches": 0}

        successful = sum(1 for l in self.launches if l.vs_target_pct >= 60)
        at_risk = sum(1 for l in self.launches if l.vs_target_pct < 40 and l.status != LaunchStatus.CLOSED)

        return {
            "total_launches": len(self.launches),
            "successful_launches": successful,
            "success_rate_pct": round((successful / len(self.launches) * 100), 1),
            "at_risk_launches": at_risk,
            "avg_vs_target_pct": round((sum(l.vs_target_pct for l in self.launches) / len(self.launches)), 1),
        }

    def marketing_summary(self):
        """Summary of marketing performance"""
        if not self.marketing_campaigns:
            return {"total_campaigns": 0}

        total_budget = sum(c.budget for c in self.marketing_campaigns)
        total_inquiries = sum(c.inquiries_generated for c in self.marketing_campaigns)
        avg_cpi = total_budget / total_inquiries if total_inquiries > 0 else 0
        avg_roi = sum(c.roi_pct for c in self.marketing_campaigns) / len(self.marketing_campaigns)

        by_channel = {}
        for c in self.marketing_campaigns:
            channel = c.channel.value
            if channel not in by_channel:
                by_channel[channel] = {"budget": 0, "inquiries": 0, "roi": []}
            by_channel[channel]["budget"] += c.budget
            by_channel[channel]["inquiries"] += c.inquiries_generated
            by_channel[channel]["roi"].append(c.roi_pct)

        best_channel = max(by_channel.items(), key=lambda x: sum(x[1]["roi"]) / len(x[1]["roi"])) if by_channel else None

        return {
            "total_campaigns": len(self.marketing_campaigns),
            "total_budget": total_budget,
            "total_inquiries_generated": total_inquiries,
            "avg_cost_per_inquiry": round(avg_cpi, 2),
            "avg_roi_pct": round(avg_roi, 1),
            "best_channel": best_channel[0] if best_channel else None,
            "by_channel": {
                k: {
                    "budget": v["budget"],
                    "inquiries": v["inquiries"],
                    "avg_roi_pct": round(sum(v["roi"]) / len(v["roi"]), 1),
                }
                for k, v in by_channel.items()
            }
        }

    def franchisee_health_summary(self):
        """Summary of franchisee health"""
        if not self.franchisee_performance:
            return {"total_franchisees": 0}

        profitable = sum(1 for f in self.franchisee_performance if f.profitability_status == ProfitabilityStatus.PROFITABLE)
        at_risk = sum(1 for f in self.franchisee_performance if f.at_risk)
        avg_satisfaction = sum(f.satisfaction_score for f in self.franchisee_performance) / len(self.franchisee_performance)

        return {
            "total_franchisees": len(self.franchisee_performance),
            "profitable_count": profitable,
            "profitable_pct": round((profitable / len(self.franchisee_performance) * 100), 1),
            "at_risk_count": at_risk,
            "avg_satisfaction": round(avg_satisfaction, 1),
        }

    def to_dict(self):
        return {
            "franchisee": {
                "prospects": [p.to_dict() for p in self.prospects],
                "performance": [f.to_dict() for f in self.franchisee_performance],
                "pipeline": self.pipeline_summary(),
                "health": self.franchisee_health_summary(),
            },
            "enrollment": [c.to_dict() for c in self.enrollment_centers],
            "launch": [l.to_dict() for l in self.launches],
            "marketing": [c.to_dict() for c in self.marketing_campaigns],
            "summaries": {
                "pipeline": self.pipeline_summary(),
                "enrollment": self.enrollment_summary(),
                "launch": self.launch_summary(),
                "marketing": self.marketing_summary(),
                "franchisee_health": self.franchisee_health_summary(),
            }
        }


def create_building_kidz_growth_engine() -> BuildingKidzGrowthEngine:
    """Create comprehensive Building Kidz growth engine with realistic data"""
    engine = BuildingKidzGrowthEngine()

    # ========== FRANCHISEE PIPELINE ==========
    # Based on ECE industry benchmarks: 6-9 month sales cycle, 30% inquiry-to-signed conversion
    prospects = [
        # Signed, soon to open
        FranchiseeProspect(
            prospect_id="FK-001",
            company_name="Learning Stars LLC",
            contact_person="Sarah Mitchell",
            status=FranchiseeStatus.OPENING,
            inquiry_date="2024-10-15",
            projected_open_date="2026-09-01",
            territory="TX",
            investment_capacity="500k_1m",
            experience_level="franchise_veteran",
            last_communication_date="2026-07-20",
        ),
        FranchiseeProspect(
            prospect_id="FK-002",
            company_name="Early Excellence Education",
            contact_person="Michael Chen",
            status=FranchiseeStatus.SIGNED,
            inquiry_date="2024-12-01",
            projected_open_date="2027-03-01",
            territory="CA",
            investment_capacity="500k_1m",
            experience_level="education_background",
            last_communication_date="2026-07-18",
        ),
        FranchiseeProspect(
            prospect_id="FK-003",
            company_name="Bright Futures Development",
            contact_person="Jennifer Walsh",
            status=FranchiseeStatus.SIGNED,
            inquiry_date="2025-03-10",
            projected_open_date="2027-02-15",
            territory="FL",
            investment_capacity="250k_500k",
            experience_level="franchise_novice",
            last_communication_date="2026-07-15",
        ),
        # In negotiation
        FranchiseeProspect(
            prospect_id="FK-004",
            company_name="Creative Kids Network",
            contact_person="David Rodriguez",
            status=FranchiseeStatus.NEGOTIATION,
            inquiry_date="2025-05-20",
            territory="NY",
            investment_capacity="500k_1m",
            experience_level="franchise_veteran",
            last_communication_date="2026-07-10",
        ),
        # Qualified
        FranchiseeProspect(
            prospect_id="FK-005",
            company_name="Academic Pathways Group",
            contact_person="Patricia Lee",
            status=FranchiseeStatus.QUALIFIED,
            inquiry_date="2026-02-15",
            territory="PA",
            investment_capacity="250k_500k",
            experience_level="franchise_novice",
            last_communication_date="2026-07-05",
        ),
        # Recent inquiries
        FranchiseeProspect(
            prospect_id="FK-006",
            company_name="Innovation Learning Centers",
            contact_person="Robert Thompson",
            status=FranchiseeStatus.INQUIRY,
            inquiry_date="2026-06-10",
            territory="IL",
            investment_capacity="over_1m",
            experience_level="education_background",
            last_communication_date="2026-07-01",
        ),
        FranchiseeProspect(
            prospect_id="FK-007",
            company_name="Youth Growth Foundation",
            contact_person="Amanda Martinez",
            status=FranchiseeStatus.INQUIRY,
            inquiry_date="2026-06-25",
            territory="GA",
            investment_capacity="250k_500k",
            experience_level="franchise_novice",
            last_communication_date="2026-06-28",
        ),
        # Opened recently
        FranchiseeProspect(
            prospect_id="FK-008",
            company_name="Metropolitan Education Trust",
            contact_person="James Porter",
            status=FranchiseeStatus.OPENED,
            inquiry_date="2025-01-20",
            projected_open_date="2026-03-01",
            territory="TX",
            investment_capacity="500k_1m",
            experience_level="franchise_veteran",
            last_communication_date="2026-07-20",
        ),
        FranchiseeProspect(
            prospect_id="FK-009",
            company_name="Western Star Academies",
            contact_person="Lisa Anderson",
            status=FranchiseeStatus.OPENED,
            inquiry_date="2025-02-10",
            projected_open_date="2026-05-15",
            territory="CA",
            investment_capacity="500k_1m",
            experience_level="education_background",
            last_communication_date="2026-07-21",
        ),
    ]

    for p in prospects:
        engine.add_prospect(p)

    # ========== ENROLLMENT PERFORMANCE (Currently operating centers) ==========
    # Benchmark: 30-80 students per center, $35k-$60k monthly revenue, 50-75% conversion rate
    enrollment_centers = [
        # Thriving centers
        EnrollmentCenter(
            center_id="BK-TX-001",
            center_name="Building Kidz — Austin",
            state="TX",
            opening_date="2024-09-01",
            status=CenterStatus.MATURE,
            monthly_inquiries=18,
            inquiry_to_enrollment_conversion_rate=0.72,
            current_enrollment=72,
            capacity=90,
            monthly_tuition_revenue=54000,
            franchisee_satisfaction=8.8,
        ),
        EnrollmentCenter(
            center_id="BK-CA-001",
            center_name="Building Kidz — Bay Area",
            state="CA",
            opening_date="2024-08-15",
            status=CenterStatus.MATURE,
            monthly_inquiries=22,
            inquiry_to_enrollment_conversion_rate=0.68,
            current_enrollment=78,
            capacity=95,
            monthly_tuition_revenue=58000,
            franchisee_satisfaction=8.9,
        ),
        # Growing centers
        EnrollmentCenter(
            center_id="BK-FL-001",
            center_name="Building Kidz — Miami",
            state="FL",
            opening_date="2025-03-01",
            status=CenterStatus.OPERATIONAL,
            monthly_inquiries=14,
            inquiry_to_enrollment_conversion_rate=0.62,
            current_enrollment=52,
            capacity=75,
            monthly_tuition_revenue=38000,
            franchisee_satisfaction=7.5,
        ),
        EnrollmentCenter(
            center_id="BK-NY-001",
            center_name="Building Kidz — Manhattan",
            state="NY",
            opening_date="2025-06-01",
            status=CenterStatus.OPERATIONAL,
            monthly_inquiries=16,
            inquiry_to_enrollment_conversion_rate=0.65,
            current_enrollment=48,
            capacity=80,
            monthly_tuition_revenue=36000,
            franchisee_satisfaction=7.3,
        ),
        # New launches
        EnrollmentCenter(
            center_id="BK-PA-001",
            center_name="Building Kidz — Philadelphia",
            state="PA",
            opening_date="2026-01-15",
            status=CenterStatus.LAUNCHING,
            monthly_inquiries=8,
            inquiry_to_enrollment_conversion_rate=0.55,
            current_enrollment=22,
            capacity=60,
            monthly_tuition_revenue=16000,
            franchisee_satisfaction=6.8,
        ),
        EnrollmentCenter(
            center_id="BK-IL-001",
            center_name="Building Kidz — Chicago",
            state="IL",
            opening_date="2026-04-01",
            status=CenterStatus.LAUNCHING,
            monthly_inquiries=6,
            inquiry_to_enrollment_conversion_rate=0.50,
            current_enrollment=18,
            capacity=60,
            monthly_tuition_revenue=13500,
            franchisee_satisfaction=6.5,
        ),
    ]

    for c in enrollment_centers:
        engine.add_enrollment_center(c)

    # ========== LAUNCH SUCCESS TRACKING ==========
    # Track 90-day enrollment targets for new centers
    launches = [
        CenterLaunch(
            center_id="BK-TX-001",
            franchisee_id="FK-008",
            soft_opening_date="2026-02-15",
            grand_opening_date="2026-03-01",
            ninety_day_target=65,
            enrollment_at_30_days=28,
            enrollment_at_60_days=52,
            enrollment_at_90_days=72,
            vs_target_pct=110.8,
            status=LaunchStatus.ACTIVE,
        ),
        CenterLaunch(
            center_id="BK-CA-001",
            franchisee_id="FK-009",
            soft_opening_date="2026-04-20",
            grand_opening_date="2026-05-15",
            ninety_day_target=70,
            enrollment_at_30_days=32,
            enrollment_at_60_days=61,
            enrollment_at_90_days=78,
            vs_target_pct=111.4,
            status=LaunchStatus.ACTIVE,
        ),
        CenterLaunch(
            center_id="BK-FL-001",
            franchisee_id="FK-003",
            soft_opening_date="2025-02-10",
            grand_opening_date="2025-03-01",
            ninety_day_target=60,
            enrollment_at_30_days=22,
            enrollment_at_60_days=40,
            enrollment_at_90_days=52,
            vs_target_pct=86.7,
            status=LaunchStatus.ACTIVE,
        ),
        CenterLaunch(
            center_id="BK-NY-001",
            franchisee_id="FK-004",
            soft_opening_date="2025-05-10",
            grand_opening_date="2025-06-01",
            ninety_day_target=55,
            enrollment_at_30_days=18,
            enrollment_at_60_days=35,
            enrollment_at_90_days=48,
            vs_target_pct=87.3,
            status=LaunchStatus.ACTIVE,
        ),
        CenterLaunch(
            center_id="BK-PA-001",
            franchisee_id="FK-005",
            soft_opening_date="2026-01-01",
            grand_opening_date="2026-01-15",
            ninety_day_target=50,
            enrollment_at_30_days=12,
            enrollment_at_60_days=18,
            enrollment_at_90_days=22,
            vs_target_pct=44.0,
            status=LaunchStatus.LAUNCHING,
        ),
    ]

    for l in launches:
        engine.add_launch(l)

    # ========== MARKETING CAMPAIGNS ==========
    # Benchmark: $60-150 cost per inquiry, varying ROI by channel
    campaigns = [
        # Digital: 100-120% ROI
        MarketingCampaign(
            campaign_id="MK-001",
            campaign_name="Google/Facebook Paid Search — Texas",
            channel=MarketingChannel.DIGITAL,
            budget=8000,
            inquiries_generated=68,
            cost_per_inquiry=117.65,
            conversions=44,
            roi_pct=112.5,
        ),
        MarketingCampaign(
            campaign_id="MK-002",
            campaign_name="Google/Facebook Paid Search — California",
            channel=MarketingChannel.DIGITAL,
            budget=9500,
            inquiries_generated=72,
            cost_per_inquiry=131.94,
            conversions=48,
            roi_pct=108.3,
        ),
        # Local: 80-100% ROI
        MarketingCampaign(
            campaign_id="MK-003",
            campaign_name="Local SEO + GMB Optimization",
            channel=MarketingChannel.LOCAL,
            budget=4000,
            inquiries_generated=58,
            cost_per_inquiry=68.97,
            conversions=32,
            roi_pct=94.2,
        ),
        # Events: 70-90% ROI
        MarketingCampaign(
            campaign_id="MK-004",
            campaign_name="Community Events + Sponsorships",
            channel=MarketingChannel.EVENTS,
            budget=6000,
            inquiries_generated=45,
            cost_per_inquiry=133.33,
            conversions=24,
            roi_pct=76.5,
        ),
        # Partnerships: 85-110% ROI
        MarketingCampaign(
            campaign_id="MK-005",
            campaign_name="School Partnerships + Cross-Promo",
            channel=MarketingChannel.PARTNERSHIPS,
            budget=5000,
            inquiries_generated=62,
            cost_per_inquiry=80.65,
            conversions=38,
            roi_pct=106.8,
        ),
        # Franchisee-run: 60-80% ROI (more variable)
        MarketingCampaign(
            campaign_id="MK-006",
            campaign_name="Franchisee Word-of-Mouth + Referrals",
            channel=MarketingChannel.FRANCHISEE_RUN,
            budget=2000,
            inquiries_generated=38,
            cost_per_inquiry=52.63,
            conversions=28,
            roi_pct=78.4,
        ),
    ]

    for c in campaigns:
        engine.add_marketing_campaign(c)

    # ========== FRANCHISEE PERFORMANCE & HEALTH ==========
    performance = [
        FranchiseePerformance(
            franchisee_id="FK-008",
            state="TX",
            months_operating=16,
            enrollment_trajectory=EnrollmentTrajectory.GROWING,
            profitability_status=ProfitabilityStatus.PROFITABLE,
            satisfaction_score=8.8,
            at_risk=False,
        ),
        FranchiseePerformance(
            franchisee_id="FK-009",
            state="CA",
            months_operating=14,
            enrollment_trajectory=EnrollmentTrajectory.GROWING,
            profitability_status=ProfitabilityStatus.PROFITABLE,
            satisfaction_score=8.9,
            at_risk=False,
        ),
        FranchiseePerformance(
            franchisee_id="FK-003",
            state="FL",
            months_operating=10,
            enrollment_trajectory=EnrollmentTrajectory.GROWING,
            profitability_status=ProfitabilityStatus.BREAKING_EVEN,
            satisfaction_score=7.5,
            at_risk=False,
        ),
        FranchiseePerformance(
            franchisee_id="FK-004",
            state="NY",
            months_operating=7,
            enrollment_trajectory=EnrollmentTrajectory.FLAT,
            profitability_status=ProfitabilityStatus.LOSING_MONEY,
            satisfaction_score=7.3,
            at_risk=True,
        ),
        FranchiseePerformance(
            franchisee_id="FK-005",
            state="PA",
            months_operating=2,
            enrollment_trajectory=EnrollmentTrajectory.GROWING,
            profitability_status=ProfitabilityStatus.LOSING_MONEY,
            satisfaction_score=6.8,
            at_risk=True,
        ),
    ]

    for p in performance:
        engine.add_franchisee_performance(p)

    return engine


if __name__ == "__main__":
    engine = create_building_kidz_growth_engine()

    print("\n" + "=" * 80)
    print("BUILDING KIDZ WORLDWIDE — GROWTH ENGINE SUMMARY")
    print("=" * 80)

    summaries = engine.to_dict()["summaries"]

    print("\n--- FRANCHISEE PIPELINE ---")
    print(f"Total prospects: {summaries['pipeline']['total_prospects']}")
    for status, count in summaries['pipeline']['by_status'].items():
        print(f"  {status}: {count}")

    print("\n--- ENROLLMENT PERFORMANCE ---")
    enroll = summaries['enrollment']
    print(f"Total enrolled: {enroll['total_enrolled']} students")
    print(f"Monthly inquiries: {enroll['total_monthly_inquiries']}")
    print(f"Conversion rate: {enroll['avg_conversion_rate']:.1%}")
    print(f"Capacity utilization: {enroll['capacity_utilization_pct']}%")
    print(f"Monthly revenue: ${enroll['total_monthly_revenue']:,.0f}")
    print(f"Franchisee satisfaction: {enroll['avg_franchisee_satisfaction']}/10")

    print("\n--- LAUNCH SUCCESS ---")
    launch = summaries['launch']
    print(f"Total launches: {launch['total_launches']}")
    print(f"Successful (≥60% target): {launch['successful_launches']}")
    print(f"Success rate: {launch['success_rate_pct']}%")
    print(f"At-risk launches: {launch['at_risk_launches']}")

    print("\n--- MARKETING PERFORMANCE ---")
    mkt = summaries['marketing']
    print(f"Total campaigns: {mkt['total_campaigns']}")
    print(f"Total budget: ${mkt['total_budget']:,.0f}")
    print(f"Inquiries generated: {mkt['total_inquiries_generated']}")
    print(f"Cost per inquiry: ${mkt['avg_cost_per_inquiry']}")
    print(f"Average ROI: {mkt['avg_roi_pct']}%")
    print(f"Best channel: {mkt['best_channel']}")

    print("\n--- FRANCHISEE HEALTH ---")
    health = summaries['franchisee_health']
    print(f"Total franchisees: {health['total_franchisees']}")
    print(f"Profitable: {health['profitable_count']} ({health['profitable_pct']}%)")
    print(f"At-risk: {health['at_risk_count']}")
    print(f"Average satisfaction: {health['avg_satisfaction']}/10")

    print("\n" + "=" * 80)

    # Export as JSON
    with open("docs/building-kidz-growth-engine.json", "w") as f:
        json.dump(engine.to_dict(), f, indent=2)
    print("\n✓ Exported to docs/building-kidz-growth-engine.json")
