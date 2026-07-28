# 🎨 Building Kidz Worldwide — Operations & Franchise Growth Engine

**Mission**: Inspire creativity, confidence, and a love of learning in young children through integrated academics and performing arts.

A deterministic, schema-driven operations platform for managing the Building Kidz franchise network. Real-time health tracking, program orchestration, franchise partner support, and compliance auditing—all queryable, auditable, and deployable with zero backend.

## Current Network

| Metric | Value |
|--------|-------|
| **Active Centers** | 11 locations across 5 US regions |
| **Total Enrollment** | 1,250+ students |
| **Monthly Revenue** | $418,400 |
| **Network Health** | 79.4/100 (3 Thriving, 8 Watch/At-Risk) |
| **Open Tickets** | 6 support requests across 6 categories |

## Regions & Centers

### 📍 Mid-Atlantic (2 centers)
- **Building Kidz — Washington DC** — Health: 88/100 (Thriving) | 127 students | 11 staff
- **Building Kidz — Baltimore** — Health: 74/100 (Watch) | 89 students | 8 staff

### 📍 Southeast (4 centers)
- **Building Kidz — Atlanta** — Health: 82/100 (Thriving) | 145 students | 13 staff
- **Building Kidz — Charlotte** — Health: 76/100 (Watch) | 103 students | 9 staff
- **Building Kidz — Charleston** — Health: 58/100 (At-Risk) | 62 students | 6 staff
- *Growth opportunity: Charleston needs curriculum support and staff retention strategy*

### 📍 Midwest (2 centers)
- **Building Kidz — Chicago** — Health: 86/100 (Thriving) | 156 students | 14 staff
- **Building Kidz — Ann Arbor** — Health: 79/100 (Watch) | 95 students | 9 staff

### 📍 Southwest (2 centers)
- **Building Kidz — Austin** — Health: 84/100 (Thriving) | 138 students | 12 staff
- **Building Kidz — Phoenix** — Health: 72/100 (Watch) | 81 students | 7 staff

### 📍 West Coast (1 center)
- **Building Kidz — San Francisco Bay Area** — Health: 87/100 (Thriving) | 142 students | 13 staff
- **Building Kidz — Seattle** — Health: 80/100 (Watch) | 112 students | 10 staff

## Program Portfolio

### 🎨 Creative Arts Foundation
- **Enrollment**: 1,015 students (81% of network)
- **Available**: All 11 centers
- **Monthly Revenue**: $320,000
- **Description**: Core program integrating visual arts, music, dance, and creative expression across Toddler, Preschool, and Pre-K

### 🎭 Performing Arts Integration
- **Enrollment**: 187 students
- **Available**: DC, Chicago, Bay Area (3 centers)
- **Monthly Revenue**: $58,000
- **Description**: Integrated theater, movement, and performance focusing on confidence and public speaking

### 🔬 STEM Integration Workshop
- **Enrollment**: 142 students
- **Available**: Atlanta, Chicago, Austin, Bay Area (4 centers)
- **Monthly Revenue**: $43,000
- **Description**: Creative arts + STEM combined approach (coding, robotics, design thinking)

### 📚 Enrichment Workshops
- **Enrollment**: 268 students
- **Available**: 6 centers
- **Monthly Revenue**: $82,000
- **Description**: Specialized workshops in music production, video creation, digital design

## Dashboard & Engine

### Live Dashboard
- **URL**: docs/index.html
- **Features**:
  - Network Hub: Real-time health triage (Thriving/Watch/At-Risk)
  - Program Orchestration: Enrollment, instructor allocation, revenue rollup
  - Support System: Ticketing with lifecycle tracking
  - Compliance Record: FDD verification and audit dates

### Data Export
- **JSON**: docs/building-kidz-network.json (queryable full state)

## Core Metrics

### Health Scoring (0-100)
Components:
- **Enrollment Conversion**: Lead-to-enrollment rate (0-1 scaled)
- **Parent Satisfaction**: Survey/feedback score (0-100)
- **Team Cohesion**: Staff retention, collaboration, morale (0-100)
- **Instructor Retention**: Year-over-year staff retention rate (0-100)

Interpretation:
- **Thriving** (80+): Stable enrollment, high parent satisfaction, strong team
- **Watch** (60-79): Growth opportunity; needs targeted support
- **At-Risk** (<60): Requires intervention (curriculum, staffing, operations)

### Enrollment Conversion Rates (by Center)
| Center | Conversion | Target | Gap |
|--------|------------|--------|-----|
| Washington DC | 76% | 75% | ✓ On target |
| Austin | 74% | 75% | -1% |
| Bay Area | 77% | 75% | ✓ Exceeding |
| Chicago | 75% | 75% | ✓ On target |
| Charlotte | 65% | 75% | -10% |
| Charleston | 52% | 75% | -23% **ACTION** |
| Phoenix | 62% | 75% | -13% |

### Monthly Revenue per Center (Targets: $35k-$50k)
| Center | Revenue | Performance |
|--------|---------|-------------|
| Chicago | $51,200 | ✓ Exceeding |
| Bay Area | $49,700 | ✓ Exceeding |
| DC | $42,500 | ✓ On target |
| Atlanta | $48,900 | ✓ Exceeding |
| Austin | $46,800 | ✓ On target |
| Seattle | $38,200 | ✓ On target |
| Ann Arbor | $32,100 | ⚠ Below target |
| Charlotte | $34,700 | ⚠ Below target |
| Baltimore | $28,300 | ⚠ Below target |
| Phoenix | $27,500 | ⚠ Below target |
| Charleston | $18,500 | ⚠ Critical |

## Support Tickets (Current)

| Ticket | Center | Category | Status | Priority |
|--------|--------|----------|--------|----------|
| BK-1001 | DC | Curriculum | Resolved | Medium |
| BK-1002 | Baltimore | Staff | In Progress | High |
| BK-1003 | Charleston | Operations | Open | Critical |
| BK-1004 | Chicago | Technology | Resolved | Low |
| BK-1005 | Austin | Compliance | Open | Medium |
| BK-1006 | Phoenix | Curriculum | In Progress | High |

### Support Categories
- **Curriculum**: Program development, arts integration, STEM implementation
- **Operations**: Enrollment strategy, center management, supply chains
- **Staff**: Training, retention, development, hiring
- **Technology**: Enrollment systems, communication platforms, curriculum tools
- **Compliance**: FDD requirements, licensing, documentation

## Compliance & Governance

### Verification Status (All 11 Centers)
- ✓ **Verified** (10): DC, Baltimore, Atlanta, Charlotte, Chicago, Ann Arbor, Austin, Phoenix, Bay Area, Seattle
- ⚠ **Flagged** (1): Charleston (remediation in progress, last audit 2024-03-15)

### FDD Item 20 Audit Trail
- All centers tracked
- Annual audit schedule maintained
- Remediation tracking for flagged centers
- Governance documentation per center

## Quick Start Guide

### For Franchise Leaders
1. **Check Network Health**: View `docs/index.html` for real-time triage
2. **Identify Growth Areas**: Sort by health score; prioritize Watch/At-Risk
3. **Analyze Programs**: Track enrollment, revenue, instructor allocation cross-center
4. **Manage Support**: Track support tickets by category and resolution timeline

### For Franchise Partners (Center Managers)
1. View your center's enrollment and parent satisfaction metrics
2. Submit support requests via ticketing system
3. Track curriculum and operational needs
4. Receive quarterly compliance verification

### For Operations Team
1. Monitor open support tickets daily
2. Maintain audit trail and compliance documentation
3. Aggregate regional metrics for monthly review
4. Flag at-risk centers for executive escalation

## Architecture

### Data Model
```python
BuildingKidzCenter(
    name, region, state, health (0-100),
    enrollment, age_groups, staff_count,
    conversion_rate, parent_satisfaction,
    team_cohesion, instructor_retention,
    monthly_revenue, margin_percentage,
    programs_offered, verified, last_audit
)
```

### Programs
```python
BuildingKidzProgram:
  - CREATIVE_ARTS_FOUNDATION
  - PERFORMING_ARTS
  - STEM_INTEGRATION
  - ENRICHMENT_WORKSHOPS
```

### Support Tickets
```python
SupportTicket(
    ticket_id, center_name, category,
    status (open/in_progress/resolved),
    created_at, resolved_at, notes
)
```

## Growth Roadmap

### Phase 1: Stabilize (Now)
- Resolve Charleston escalation (currently At-Risk)
- Support Baltimore and Phoenix growth (Watch → Thriving)
- Rollout Performing Arts to 3 additional centers

### Phase 2: Expand (Q4 2024)
- Add 5 new centers (target: 16 total)
- Expand STEM Integration to 6+ centers
- Achieve 75%+ network average on enrollment conversion

### Phase 3: Scale (2025)
- Achieve 25+ centers across 8+ regions
- Launch franchise partner portal (self-service metrics)
- Implement predictive analytics for at-risk center early warning

## Files & Modules

### Core Engine
- **`building_kidz_engine.py`** — Data model, metrics, business logic
- **`building_kidz_demo.py`** — Sample network with 11 real-like centers

### Web & Dashboards
- **`franchise_web_generator.py`** — Static HTML generation
- **`generate_building_kidz_site.py`** — Dashboard builder

### Outputs
- **`docs/index.html`** — Main dashboard (live)
- **`docs/landing.html`** — Landing page
- **`docs/building-kidz-network.json`** — Data export

### Documentation
- **`Pratik_Singh_BuildingKidz_Resume.docx`** — Operations-focused resume
- **`Pratik_Singh_BuildingKidz_CoverNote.docx`** — Leadership pitch
- **`BUILDING_KIDZ_README.md`** — This document

## Design Principles

### Deterministic
No hidden calculations. Every health score, revenue number, and support status is explicit, auditable, and traceable.

### Schema-First
Closed enums prevent ambiguity. Centers must have clear status (Thriving/Watch/At-Risk), programs are explicitly tracked, support categories are standardized.

### Transparent
Every metric is defined and queryable. Regional aggregation is visible. No black-box magic.

### Compliance-Native
FDD verification, audit dates, and governance documentation are first-class. Not an afterthought.

### Zero-Backend
Static HTML + embedded JSON. Deployed on GitHub Pages. No database, no servers, no ops overhead.

## Contact & Support

**Operations Director**: Pratik Singh  
**Email**: parry.s.2324@gmail.com  
**GitHub**: [singhpratik44/research-graph-engine](https://github.com/singhpratik44/research-graph-engine)

---

**Building Kidz Worldwide Operations Engine v1.0**  
Deterministic, auditable, scalable franchise management platform.  
Ready to support growth from 11 to 244+ centers.
