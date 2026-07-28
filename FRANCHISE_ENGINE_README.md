# 🚀 Franchise Engine — Multi-Brand Operations & Governance Platform

A deterministic, schema-driven system for managing 244+ franchise units across multiple brands (CodeNinjas, Building Kidz, and adjacent networks). Real-time health tracking, compliance auditing, program orchestration, and franchise partner support—all queryable, auditable, and deployable with zero backend.

## Features

### 📍 Network Hub
- **Geographic center mapping** with real-time health metrics (engagement, margin, staffing, community retention)
- **Condition triage**: Thriving / Watch / At-Risk for every center and region
- **Region-to-region propagation** recommendations based on health differentials
- **Conflict detection** across all 244+ units

### 📚 Program Orchestration
- **Multi-program tracking** (CODING, STEM, ARTS, ENRICHMENT)
- **Cross-center enrollment rollup** with instructor allocation
- **Revenue attribution** per program per center
- **Rebalancing guidance** based on utilization and demand

### 🆘 Support & Escalation
- **Ticketing system** for onboarding, compliance, marketing, technical, and HR
- **Lifecycle tracking**: open → in_progress → resolved
- **Audit trail** with creation date, resolution date, and notes
- **Category-based SLA** management

### 📋 Compliance Record
- **FDD Item 20 verification** (244 authoritative units)
- **Center-level audit trails** with verification status
- **Last audit date** tracking per center
- **Flagged centers** with remediation notes

## Architecture

### Core Data Model

```python
# Centers: individual franchise locations
Center(
    name, region, state, health, enrollment, staff_count,
    conversion_rate, chemistry (team cohesion), revenue_margin,
    retention, verified, programs
)

# Regions: geographic aggregation
Region(region_id, label, centers[])
  - Aggregates: avg_health(), metrics(), condition()

# Programs: offerings across centers
Program(
    program_id, name, program_type, centers_offering,
    enrollment, instructor_count, revenue_contribution
)

# Support: ticketing and escalation
SupportTicket(
    ticket_id, center_name, category, status,
    created_at, resolved_at, notes
)

# Compliance: audit and governance
ComplianceRecord(
    center_name, fdd_item_20, verification_status,
    last_audit, notes
)
```

### Schema Validation

- **Closed enums**: No freeform strings. FranchiseStatus (THRIVING, WATCH, AT_RISK), ProgramType (CODING, STEM, ARTS, ENRICHMENT), SupportCategory (onboarding, compliance, marketing, technical, hr)
- **Typed dataclasses**: Every field has a type hint
- **No ambiguity**: State transitions are deterministic and auditable

### Deployment

**Static HTML Generation**: `franchise_web_generator.py` renders the entire dashboard from `engine.to_dict()` as JSON embedded in the HTML. Zero backend, zero runtime dependencies.

**GitHub Pages**: Deploy to `docs/` directory with three entry points:
- `index.html` — CodeNinjas network dashboard
- `building-kidz.html` — Building Kidz network dashboard
- `index-landing.html` — Multi-brand landing page

## Quick Start

### Generate Dashboards

```bash
python3 generate_franchise_pages.py
```

This generates:
- `docs/index.html` (CodeNinjas)
- `docs/building-kidz.html` (Building Kidz)
- `docs/index-landing.html` (landing page)
- `docs/codeninja-data.json` (data export)
- `docs/building-kidz-data.json` (data export)

### Using the Engine Programmatically

```python
from franchise_engine import FranchiseEngine, Center, Program, ProgramType

# Create engine
engine = FranchiseEngine(brand_name="CodeNinjas")

# Add regions
engine.add_region("ca", "California")

# Add centers
center = Center(
    name="CodeNinjas San Francisco",
    region="ca",
    state="CA",
    health=92.0,
    enrollment=145,
    staff_count=8,
    conversion_rate=0.78,
    chemistry=88.0,
    revenue_margin=8.5,
    retention=92.0,
    verified=True,
    programs=[ProgramType.CODING, ProgramType.STEM],
)
engine.add_center("ca", center)

# Add programs
program = Program(
    program_id="CN-101",
    name="Coding 101: Python Fundamentals",
    program_type=ProgramType.CODING,
    centers_offering=["CodeNinjas San Francisco"],
    enrollment=245,
    instructor_count=6,
    revenue_contribution=45000.0,
)
engine.add_program(program)

# Create support tickets
ticket = engine.create_support_ticket(
    center_name="CodeNinjas San Francisco",
    category="marketing",
    notes="Need help with social media strategy"
)

# Generate HTML
from franchise_web_generator import generate_html
html = generate_html(engine)
```

### Export as JSON

```python
# Get engine state as dict
state_dict = engine.to_dict()

# Export as JSON
json_str = engine.to_json()
```

## Files

### Core Modules

- **`franchise_engine.py`** — Core data model and business logic
  - `FranchiseEngine` class with region/center/program/ticket management
  - `Center`, `Region`, `Program`, `SupportTicket`, `ComplianceRecord` dataclasses
  - `FranchiseStatus`, `ProgramType` enums
  - Metrics aggregation and health scoring

- **`franchise_web_generator.py`** — HTML generation from engine state
  - `generate_html()` function producing static, self-contained HTML
  - Four-tab interface (Network, Programs, Support, Record)
  - Embedded JavaScript for interactivity

- **`franchise_demo_data.py`** — Sample network data
  - `create_codeninja_engine()` — 8 centers, 644+ enrollment, 5 regions
  - `create_building_kidz_engine()` — 4 centers, 328+ enrollment, 3 regions

- **`generate_franchise_pages.py`** — Page generation script
  - Generates all static HTML files
  - Exports JSON data files
  - Creates landing page

### Generated Files (in `docs/`)

- **`index.html`** — CodeNinjas dashboard (live on GitHub Pages)
- **`building-kidz.html`** — Building Kidz dashboard (live on GitHub Pages)
- **`index-landing.html`** — Multi-brand landing page
- **`codeninja-data.json`** — CodeNinjas engine state (JSON)
- **`building-kidz-data.json`** — Building Kidz engine state (JSON)

### Documentation

- **`Pratik_Singh_Franchise_Operations_Resume.docx`** — Engine-driven operations resume
- **`Pratik_Singh_Cover_Note.docx`** — Cover note describing engine capabilities
- **`Pratik_Singh_Franchise_Operations_Resume.md`** — Markdown resume
- **`Pratik_Singh_Cover_Note.md`** — Markdown cover note

## Key Design Principles

### 1. Deterministic
No hidden calculations, random sampling, or "trust me" claims. Every state transition is explicit, logged, and auditable.

### 2. Schema-First
Closed enums, typed dataclasses, no freeform strings. If the schema doesn't support it, the engine doesn't do it.

### 3. Transparent
Every value can be queried. Network health isn't a "feeling"—it's `(engagement + margin + staffing + community) / 4` with clear definitions per metric.

### 4. Scalable Without Backend
Static HTML deployment. Zero database. Zero server. Everything runs client-side from embedded JSON. Scales to 1000s of centers.

### 5. Compliance-Native
FDD Item 20 verification is first-class, not an afterthought. Audit trails are built in. Compliance status (verified/pending/flagged) is queryable per center.

## Metrics Reference

### Health Scoring
- **Engagement**: Conversion rate (0–1), typically 0.6–0.8 for strong centers
- **Margin**: Revenue before expenses (0–20k), scaled to 0–1 for display
- **Staffing**: Team chemistry / cohesion score (0–100)
- **Community**: Parent/student retention rate (0–100%)

### Condition Mapping
- **Thriving**: Health ≥ 80
- **Watch**: Health 60–79
- **At-Risk**: Health < 60

### Engagement Levels
- Centers with 70%+ conversion rate + 90%+ retention + 80%+ chemistry typically score THRIVING
- Centers below 60% conversion or 70% retention typically score WATCH or AT_RISK

## Governance Principles

> **The Franchise Engine proposes; it does not enact policy without authorization.**

- The engine is a decision support system, not an autopilot
- All insights are advisory
- Escalation (flagged centers, support tickets) requires human review
- Compliance decisions (verification status) are manual, not algorithmic
- The engine tracks decisions but never enforces them unilaterally

## Future Roadmap

- [ ] Real-time sync with MyStudio / QuickBooks (live enrollment + revenue)
- [ ] Multi-brand aggregation (combine CodeNinjas + Building Kidz + third brand into one view)
- [ ] Franchise partner portal (centers can view their own metrics, submit tickets)
- [ ] Predictive center health scoring (early warning for at-risk centers)
- [ ] Program gap analysis (identify which centers are missing high-demand programs)

## Support

For questions about the Franchise Engine:
- GitHub Issues: [singhpratik44/research-graph-engine](https://github.com/singhpratik44/research-graph-engine)
- Email: parry.s.2324@gmail.com

## License

MIT License. See LICENSE file for details.

---

**Franchise Engine v1.0** — Generated 2024-07-28
