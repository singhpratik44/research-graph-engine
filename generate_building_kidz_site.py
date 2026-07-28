#!/usr/bin/env python3
"""
Generate Building Kidz Worldwide dashboard pages for GitHub Pages
"""

import os
import json
from building_kidz_demo import create_building_kidz_network
from franchise_web_generator import generate_html


def ensure_docs_dir():
    """Ensure docs directory exists"""
    os.makedirs("docs", exist_ok=True)


def generate_building_kidz_site():
    """Generate all Building Kidz pages"""
    ensure_docs_dir()

    print("Generating Building Kidz Worldwide dashboard...")
    engine = create_building_kidz_network()

    # Generate main dashboard
    html = generate_html(engine)
    with open("docs/index.html", "w") as f:
        f.write(html)
    print("✓ docs/index.html")

    # Export data
    with open("docs/building-kidz-network.json", "w") as f:
        json.dump(engine.to_dict(), f, indent=2, default=str)
    print("✓ docs/building-kidz-network.json")

    # Create landing page
    landing_html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Building Kidz Worldwide — Franchise Operations Dashboard</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 1000px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        }
        header {
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            color: white;
            padding: 60px 30px;
            text-align: center;
        }
        header h1 { font-size: 2.8em; margin-bottom: 10px; }
        header p { font-size: 1.1em; opacity: 0.9; margin-bottom: 20px; }
        .tagline {
            font-size: 1em;
            font-style: italic;
            opacity: 0.95;
            max-width: 600px;
            margin: 20px auto;
            line-height: 1.6;
        }
        .content { padding: 40px 30px; }
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 30px;
            margin-bottom: 40px;
        }
        .stat-card {
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            color: white;
            padding: 30px;
            border-radius: 8px;
            text-align: center;
        }
        .stat-value {
            font-size: 2.5em;
            font-weight: bold;
            margin-bottom: 5px;
        }
        .stat-label {
            font-size: 0.95em;
            opacity: 0.9;
        }
        .btn {
            display: inline-block;
            padding: 14px 32px;
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            color: white;
            text-decoration: none;
            border-radius: 6px;
            margin-top: 20px;
            transition: transform 0.3s;
            font-weight: 600;
        }
        .btn:hover { transform: translateY(-2px); }
        .features {
            background: #f8f9fa;
            padding: 40px 30px;
            border-radius: 8px;
            margin-bottom: 40px;
        }
        .features h2 {
            margin-bottom: 25px;
            color: #333;
        }
        .features-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 20px;
        }
        .feature {
            padding: 20px;
            background: white;
            border-radius: 6px;
            border-left: 4px solid #f5576c;
        }
        .feature-icon {
            font-size: 2em;
            margin-bottom: 10px;
        }
        .feature-title {
            font-weight: bold;
            color: #333;
            margin-bottom: 8px;
        }
        .feature-desc {
            font-size: 0.9em;
            color: #666;
            line-height: 1.4;
        }
        .mission {
            background: linear-gradient(135deg, #f093fb15 0%, #f5576c15 100%);
            padding: 30px;
            border-radius: 8px;
            border-left: 6px solid #f5576c;
            margin-bottom: 40px;
        }
        .mission h3 {
            color: #f5576c;
            margin-bottom: 10px;
        }
        .mission p {
            color: #333;
            line-height: 1.6;
            font-size: 1.05em;
        }
        .footer {
            text-align: center;
            padding: 30px;
            background: #f8f9fa;
            color: #666;
            border-top: 1px solid #e9ecef;
        }
        @media (max-width: 768px) {
            header h1 { font-size: 2em; }
            .grid { grid-template-columns: 1fr; }
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🎨 Building Kidz Worldwide</h1>
            <p>Franchise Operations & Network Dashboard</p>
            <div class="tagline">
                Inspire creativity, confidence, and a love of learning in young children
                through integrated academics and performing arts.
            </div>
        </header>

        <div class="content">
            <div class="mission">
                <h3>Our Mission</h3>
                <p>Building Kidz is a mission-driven organization dedicated to providing exceptional early childhood education that integrates creative arts with rigorous academics, helping children develop confidence, creativity, and a love of learning.</p>
            </div>

            <div class="grid">
                <div class="stat-card">
                    <div class="stat-value">11</div>
                    <div class="stat-label">Active Centers</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">1,100+</div>
                    <div class="stat-label">Total Enrollment</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">5</div>
                    <div class="stat-label">Regions</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">4</div>
                    <div class="stat-label">Program Tracks</div>
                </div>
            </div>

            <div class="features">
                <h2>Engine Capabilities</h2>
                <div class="features-grid">
                    <div class="feature">
                        <div class="feature-icon">📍</div>
                        <div class="feature-title">Network Hub</div>
                        <div class="feature-desc">Real-time center health, regional metrics, and performance triage (Thriving/Watch/At-Risk)</div>
                    </div>
                    <div class="feature">
                        <div class="feature-icon">👨‍🏫</div>
                        <div class="feature-title">Program Orchestration</div>
                        <div class="feature-desc">Track Creative Arts, Performing Arts, STEM, and Enrichment enrollments cross-center</div>
                    </div>
                    <div class="feature">
                        <div class="feature-icon">🆘</div>
                        <div class="feature-title">Support System</div>
                        <div class="feature-desc">Ticketing for curriculum, operations, staff, technology, and compliance</div>
                    </div>
                    <div class="feature">
                        <div class="feature-icon">✅</div>
                        <div class="feature-title">Compliance Audit</div>
                        <div class="feature-desc">FDD verification tracking, audit dates, and governance documentation</div>
                    </div>
                </div>
            </div>

            <center>
                <a href="index.html" class="btn">View Live Dashboard →</a>
            </center>

            <div style="margin-top: 50px; padding: 30px; background: #f8f9fa; border-radius: 8px;">
                <h3 style="margin-bottom: 15px; color: #333;">Network Overview</h3>
                <p style="color: #666; line-height: 1.6; margin-bottom: 15px;">
                    The Building Kidz Engine provides real-time visibility across all franchise centers.
                    Track enrollment, instructor retention, parent satisfaction, and operational health
                    with deterministic metrics that enable data-driven decision making at the network,
                    regional, and center level.
                </p>
                <p style="color: #666; line-height: 1.6;">
                    <strong>Key Metrics:</strong> Enrollment Conversion · Parent Satisfaction · Team Cohesion ·
                    Instructor Retention · Monthly Revenue · Program Participation
                </p>
            </div>
        </div>

        <div class="footer">
            <p><strong>Building Kidz Worldwide</strong> — Franchise Operations Engine</p>
            <p style="margin-top: 10px; font-size: 0.9em; opacity: 0.8;">
                Deterministic, auditable, zero-backend operations platform for franchise network management
            </p>
        </div>
    </div>
</body>
</html>"""

    with open("docs/landing.html", "w") as f:
        f.write(landing_html)
    print("✓ docs/landing.html")

    # Summary
    summary = engine.network_summary()
    print("\n" + "=" * 60)
    print("BUILDING KIDZ WORLDWIDE — NETWORK SUMMARY")
    print("=" * 60)
    print(f"Total Centers: {summary['total_centers']}")
    print(f"Total Regions: {summary['total_regions']}")
    print(f"Total Enrollment: {summary['total_enrollment']:,}")
    print(f"Total Monthly Revenue: ${summary['total_monthly_revenue']:,.0f}")
    print(f"Average Network Health: {summary['avg_network_health']:.1f}/100")
    print(f"  - Thriving: {summary['thriving_count']}")
    print(f"  - Watch: {summary['watch_count']}")
    print(f"  - At-Risk: {summary['at_risk_count']}")
    print(f"Open Support Tickets: {summary['open_support_tickets']}")
    print("=" * 60)


if __name__ == "__main__":
    generate_building_kidz_site()
