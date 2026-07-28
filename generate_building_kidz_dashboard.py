#!/usr/bin/env python3
"""
Generate Building Kidz Growth Engine Dashboard — Static HTML for GitHub Pages
Converts Python engine output to static HTML using embedded data.
"""

import os
import json
from building_kidz_growth_engine import create_building_kidz_growth_engine


def ensure_docs_dir():
    os.makedirs("docs", exist_ok=True)


def generate_dashboard():
    """Generate static dashboard HTML"""
    ensure_docs_dir()

    print("Building Building Kidz Growth Engine dashboard...")
    engine = create_building_kidz_growth_engine()
    engine_data = engine.to_dict()

    # Export JSON data
    with open("docs/building-kidz-growth-engine.json", "w") as f:
        json.dump(engine_data, f, indent=2)
    print("✓ docs/building-kidz-growth-engine.json")

    # Generate HTML dashboard
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Building Kidz Worldwide — Growth Command Center</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        html {{ font-size: 14px; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif;
            background: #f5f5f5;
            color: #111;
            line-height: 1.6;
        }}
        .container {{ max-width: 1400px; margin: 0 auto; }}
        header {{
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            color: white;
            padding: 40px 20px;
            text-align: center;
        }}
        header h1 {{ font-size: 2.2em; margin-bottom: 10px; }}
        header p {{ font-size: 1.1em; opacity: 0.9; }}
        .content {{ padding: 30px 20px; }}
        .tab-nav {{
            display: flex;
            gap: 8px;
            margin-bottom: 20px;
            flex-wrap: wrap;
            border-bottom: 2px solid #ddd;
            padding-bottom: 10px;
        }}
        .tab-nav button {{
            padding: 10px 16px;
            font-size: 0.95em;
            font-weight: 600;
            border: none;
            background: #f0f0f0;
            color: #111;
            border-radius: 4px 4px 0 0;
            cursor: pointer;
            transition: all 0.2s;
        }}
        .tab-nav button.active {{
            background: #111;
            color: white;
        }}
        .tab-nav button:hover {{
            background: #ddd;
        }}
        .tab-nav button.active:hover {{
            background: #222;
        }}
        .tab-content {{ display: none; }}
        .tab-content.active {{ display: block; }}
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 16px;
            margin-bottom: 24px;
        }}
        .metric-card {{
            background: white;
            border: 1px solid #ddd;
            border-radius: 6px;
            padding: 16px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        }}
        .metric-card .label {{
            font-size: 0.8em;
            color: #666;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 8px;
        }}
        .metric-card .value {{
            font-size: 2em;
            font-weight: 800;
            margin-bottom: 4px;
        }}
        .metric-card .sublabel {{
            font-size: 0.75em;
            color: #999;
        }}
        .metric-card.success .value {{ color: #2fbf5f; }}
        .metric-card.warning .value {{ color: #d9a520; }}
        .metric-card.danger .value {{ color: #e03535; }}
        table {{
            width: 100%;
            border-collapse: collapse;
            background: white;
            border: 1px solid #ddd;
            border-radius: 6px;
            overflow: hidden;
            margin-bottom: 20px;
        }}
        table thead {{
            background: #f8f8f8;
            border-bottom: 2px solid #ddd;
        }}
        table th {{
            padding: 12px;
            text-align: left;
            font-weight: 700;
            font-size: 0.85em;
            color: #666;
            text-transform: uppercase;
            letter-spacing: 0.4px;
        }}
        table td {{
            padding: 12px;
            border-bottom: 1px solid #eee;
        }}
        table tr:hover {{ background: #f9f9f9; }}
        table tbody tr:last-child td {{ border-bottom: none; }}
        .status-badge {{
            display: inline-block;
            padding: 4px 8px;
            border-radius: 3px;
            font-size: 0.75em;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.3px;
        }}
        .status-open {{ background: #e03535; color: white; }}
        .status-qualified {{ background: #d9a520; color: white; }}
        .status-signed {{ background: #2fbf5f; color: white; }}
        .status-opening {{ background: #6fe8ff; color: #111; }}
        .status-opened {{ background: #2fbf5f; color: white; }}
        .status-profitable {{ background: #2fbf5f; color: white; }}
        .status-breaking-even {{ background: #d9a520; color: white; }}
        .status-losing-money {{ background: #e03535; color: white; }}
        .status-growing {{ color: #2fbf5f; font-weight: 700; }}
        .status-flat {{ color: #d9a520; font-weight: 700; }}
        .status-declining {{ color: #e03535; font-weight: 700; }}
        .progress-bar {{
            width: 100%;
            height: 8px;
            background: #eee;
            border-radius: 4px;
            overflow: hidden;
            margin: 6px 0;
        }}
        .progress-fill {{
            height: 100%;
            background: #2fbf5f;
            border-radius: 4px;
            transition: width 0.3s;
        }}
        .section-title {{
            font-size: 1.3em;
            font-weight: 700;
            margin-bottom: 16px;
            margin-top: 24px;
            color: #111;
            border-bottom: 2px solid #ddd;
            padding-bottom: 8px;
        }}
        .footer {{
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #ddd;
            color: #666;
            text-align: center;
            font-size: 0.9em;
        }}
        @media (max-width: 768px) {{
            header h1 {{ font-size: 1.6em; }}
            .metrics-grid {{ grid-template-columns: 1fr; }}
            table {{ font-size: 0.85em; }}
            table th, table td {{ padding: 8px; }}
        }}
    </style>
</head>
<body>
    <header>
        <h1>🎨 Building Kidz Worldwide</h1>
        <p>Franchise Growth Command Center — 100-Center Network Governance</p>
    </header>

    <div class="container">
        <div class="content">
            <div class="tab-nav">
                <button class="tab-btn active" data-tab="growth">Growth Command</button>
                <button class="tab-btn" data-tab="enrollment">Enrollment Performance</button>
                <button class="tab-btn" data-tab="launch">Launch & Marketing</button>
                <button class="tab-btn" data-tab="franchisee">Franchisee Health</button>
                <button class="tab-btn" data-tab="expansion">Expansion Strategy</button>
            </div>

            <!-- GROWTH COMMAND TAB -->
            <div id="growth" class="tab-content active">
                <h2 class="section-title">Franchisee Growth Command Center</h2>

                <div class="metrics-grid">
                    <div class="metric-card success">
                        <div class="label">Pipeline: Inquiry → Opened</div>
                        <div class="value">{engine_data["summaries"]["pipeline"]["total_prospects"]}</div>
                        <div class="sublabel">total prospects</div>
                        <div style="font-size: 0.75em; margin-top: 8px; color: #666;">
                            <span style="color: #2fbf5f; font-weight: 700;">{engine_data["summaries"]["pipeline"]["signed"]}</span> signed ·
                            <span style="color: #d9a520; font-weight: 700; margin-left: 4px;">{engine_data["summaries"]["pipeline"]["opening"]}</span> opening ·
                            <span style="font-weight: 700; margin-left: 4px;">{engine_data["summaries"]["pipeline"]["opened"]}</span> opened
                        </div>
                    </div>

                    <div class="metric-card success">
                        <div class="label">Enrollment: Inquiry→Enrollment</div>
                        <div class="value">{engine_data["summaries"]["enrollment"]["avg_conversion_rate"]:.1%}</div>
                        <div class="sublabel">network-wide conversion (target: 50-75%)</div>
                    </div>

                    <div class="metric-card success">
                        <div class="label">Launch Success: 90-Day Targets</div>
                        <div class="value">{engine_data["summaries"]["launch"]["successful_launches"]}/{engine_data["summaries"]["launch"]["total_launches"]}</div>
                        <div class="sublabel">launches hitting ≥60% target</div>
                    </div>

                    <div class="metric-card">
                        <div class="label">Marketing ROI</div>
                        <div class="value">{engine_data["summaries"]["marketing"]["avg_roi_pct"]:.0f}%</div>
                        <div class="sublabel">average across all channels</div>
                    </div>
                </div>

                <h3 class="section-title">Active Franchisee Prospects (In Pipeline)</h3>
                <table>
                    <thead>
                        <tr>
                            <th>Company</th>
                            <th>Contact</th>
                            <th>Status</th>
                            <th>Territory</th>
                            <th>Projected Open</th>
                            <th>Investment</th>
                            <th>Last Contact</th>
                        </tr>
                    </thead>
                    <tbody>
"""

    # Add prospect rows
    for prospect in engine_data["franchisee"]["prospects"]:
        status_class = f"status-{prospect['status'].lower().replace('_', '-')}"
        investment = prospect["investment_capacity"].replace("_", "-")
        projected_date = prospect.get("projected_open_date", "—")

        html += f"""                        <tr>
                            <td><strong>{prospect['company_name']}</strong></td>
                            <td>{prospect['contact_person']}</td>
                            <td><span class="status-badge {status_class}">{prospect['status']}</span></td>
                            <td>{prospect['territory']}</td>
                            <td>{projected_date}</td>
                            <td>{investment}</td>
                            <td>{prospect['last_communication_date']}</td>
                        </tr>
"""

    html += """                    </tbody>
                </table>
            </div>

            <!-- ENROLLMENT PERFORMANCE TAB -->
            <div id="enrollment" class="tab-content">
                <h2 class="section-title">Network Enrollment Performance</h2>

                <div class="metrics-grid">
"""

    enroll = engine_data["summaries"]["enrollment"]
    html += f"""                    <div class="metric-card success">
                        <div class="label">Total Enrolled</div>
                        <div class="value">{enroll['total_enrolled']}</div>
                        <div class="sublabel">students across all centers</div>
                    </div>

                    <div class="metric-card">
                        <div class="label">Monthly Inquiries</div>
                        <div class="value">{enroll['total_monthly_inquiries']}</div>
                        <div class="sublabel">parent inquiries this month</div>
                    </div>

                    <div class="metric-card">
                        <div class="label">Avg Capacity</div>
                        <div class="value">{enroll['capacity_utilization_pct']}%</div>
                        <div class="sublabel">utilization (target: 70-85%)</div>
                    </div>

                    <div class="metric-card">
                        <div class="label">Monthly Revenue</div>
                        <div class="value">${enroll['total_monthly_revenue']/1000:.0f}k</div>
                        <div class="sublabel">total tuition revenue</div>
                    </div>

                    <div class="metric-card success">
                        <div class="label">Franchisee Satisfaction</div>
                        <div class="value">{enroll['avg_franchisee_satisfaction']}/10</div>
                        <div class="sublabel">average satisfaction score</div>
                    </div>
                </div>

                <h3 class="section-title">Center-Level Enrollment Metrics</h3>
                <table>
                    <thead>
                        <tr>
                            <th>Center</th>
                            <th>Enrolled</th>
                            <th>Monthly Inquiries</th>
                            <th>Conversion %</th>
                            <th>Capacity %</th>
                            <th>Monthly Revenue</th>
                            <th>Franchisee Score</th>
                        </tr>
                    </thead>
                    <tbody>
"""

    for center in engine_data["enrollment"]:
        conversion_pct = center["inquiry_to_enrollment_conversion_rate"] * 100
        capacity_pct = (center["current_enrollment"] / center["capacity"]) * 100

        html += f"""                        <tr>
                            <td><strong>{center['center_name']}</strong></td>
                            <td>{center['current_enrollment']}</td>
                            <td>{center['monthly_inquiries']}</td>
                            <td><strong style="color: {'#2fbf5f' if conversion_pct >= 50 else '#e03535'}">{conversion_pct:.0f}%</strong></td>
                            <td>{capacity_pct:.0f}%</td>
                            <td><strong>${center['monthly_tuition_revenue']/1000:.1f}k</strong></td>
                            <td><strong style="color: {'#2fbf5f' if center['franchisee_satisfaction'] >= 7.5 else '#d9a520'}">{center['franchisee_satisfaction']}/10</strong></td>
                        </tr>
"""

    html += """                    </tbody>
                </table>
            </div>

            <!-- LAUNCH & MARKETING TAB -->
            <div id="launch" class="tab-content">
                <h2 class="section-title">Launch Success & Marketing Performance</h2>

                <div class="metrics-grid">
"""

    launch = engine_data["summaries"]["launch"]
    mkt = engine_data["summaries"]["marketing"]

    success_rate = (launch["successful_launches"] / launch["total_launches"] * 100) if launch["total_launches"] > 0 else 0
    html += f"""                    <div class="metric-card success">
                        <div class="label">Launch Success Rate</div>
                        <div class="value">{success_rate:.0f}%</div>
                        <div class="sublabel">{launch['successful_launches']}/{launch['total_launches']} launches on-track (≥60%)</div>
                    </div>

                    <div class="metric-card {'danger' if launch['at_risk_launches'] > 0 else 'success'}">
                        <div class="label">At-Risk Launches</div>
                        <div class="value">{launch['at_risk_launches']}</div>
                        <div class="sublabel">need intervention (&lt;40% target)</div>
                    </div>

                    <div class="metric-card">
                        <div class="label">Total Marketing Budget</div>
                        <div class="value">${mkt['total_budget']/1000:.0f}k</div>
                        <div class="sublabel">across all channels this period</div>
                    </div>

                    <div class="metric-card">
                        <div class="label">Cost Per Inquiry</div>
                        <div class="value">${mkt['avg_cost_per_inquiry']:.0f}</div>
                        <div class="sublabel">blended (target: $60-$150)</div>
                    </div>

                    <div class="metric-card success">
                        <div class="label">Best Channel</div>
                        <div class="value">{mkt['best_channel']}</div>
                        <div class="sublabel">highest ROI performer</div>
                    </div>
                </div>

                <h3 class="section-title">Launch Success Tracking (90-Day Targets)</h3>
                <table>
                    <thead>
                        <tr>
                            <th>Center</th>
                            <th>Grand Opening</th>
                            <th>90-Day Target</th>
                            <th>@30 Days</th>
                            <th>@60 Days</th>
                            <th>@90 Days</th>
                            <th>Vs Target</th>
                            <th>Status</th>
                        </tr>
                    </thead>
                    <tbody>
"""

    for launch_data in engine_data["launch"]:
        status_color = "#2fbf5f" if launch_data["vs_target_pct"] >= 60 else "#d9a520" if launch_data["vs_target_pct"] >= 40 else "#e03535"

        html += f"""                        <tr>
                            <td><strong>{launch_data['center_id']}</strong></td>
                            <td style="font-size: 0.8em;">{launch_data['grand_opening_date']}</td>
                            <td>{launch_data['ninety_day_target']}</td>
                            <td>{launch_data['enrollment_at_30_days']}</td>
                            <td>{launch_data['enrollment_at_60_days']}</td>
                            <td><strong>{launch_data['enrollment_at_90_days']}</strong></td>
                            <td><strong style="color: {status_color}">{launch_data['vs_target_pct']:.0f}%</strong></td>
                            <td><span class="status-badge" style="background: {status_color}; color: white;">{launch_data['status']}</span></td>
                        </tr>
"""

    html += """                    </tbody>
                </table>

                <h3 class="section-title">Marketing Campaign ROI by Channel</h3>
                <table>
                    <thead>
                        <tr>
                            <th>Campaign</th>
                            <th>Channel</th>
                            <th>Budget</th>
                            <th>Inquiries</th>
                            <th>CPI</th>
                            <th>Conversions</th>
                            <th>ROI %</th>
                        </tr>
                    </thead>
                    <tbody>
"""

    for campaign in engine_data["marketing"]:
        html += f"""                        <tr>
                            <td><strong>{campaign['campaign_name']}</strong></td>
                            <td>{campaign['channel'].replace('_', ' ').title()}</td>
                            <td>${campaign['budget']/1000:.1f}k</td>
                            <td>{campaign['inquiries_generated']}</td>
                            <td><strong>${campaign['cost_per_inquiry']:.0f}</strong></td>
                            <td>{campaign['conversions']}</td>
                            <td><strong style="color: {'#2fbf5f' if campaign['roi_pct'] > 100 else '#d9a520' if campaign['roi_pct'] > 50 else '#e03535'}">{campaign['roi_pct']:.0f}%</strong></td>
                        </tr>
"""

    html += """                    </tbody>
                </table>
            </div>

            <!-- FRANCHISEE HEALTH TAB -->
            <div id="franchisee" class="tab-content">
                <h2 class="section-title">Franchisee Health & Support</h2>

                <div class="metrics-grid">
"""

    health = engine_data["summaries"]["franchisee_health"]
    profitable_pct = (health["profitable_count"] / health["total_franchisees"] * 100) if health["total_franchisees"] > 0 else 0

    html += f"""                    <div class="metric-card">
                        <div class="label">Total Franchisees</div>
                        <div class="value">{health['total_franchisees']}</div>
                        <div class="sublabel">operating centers in network</div>
                    </div>

                    <div class="metric-card success">
                        <div class="label">Profitable</div>
                        <div class="value">{profitable_pct:.0f}%</div>
                        <div class="sublabel">{health['profitable_count']}/{health['total_franchisees']} franchisees</div>
                    </div>

                    <div class="metric-card {'danger' if health['at_risk_count'] > 0 else 'success'}">
                        <div class="label">At-Risk</div>
                        <div class="value">{health['at_risk_count']}</div>
                        <div class="sublabel">need intervention or support</div>
                    </div>

                    <div class="metric-card success">
                        <div class="label">Avg Satisfaction</div>
                        <div class="value">{health['avg_satisfaction']}/10</div>
                        <div class="sublabel">franchisee satisfaction score</div>
                    </div>
                </div>

                <h3 class="section-title">Franchisee Performance & Health Status</h3>
                <table>
                    <thead>
                        <tr>
                            <th>Franchisee ID</th>
                            <th>Territory</th>
                            <th>Months Operating</th>
                            <th>Trajectory</th>
                            <th>Profitability</th>
                            <th>Satisfaction</th>
                            <th>Status</th>
                        </tr>
                    </thead>
                    <tbody>
"""

    for perf in engine_data["franchisee"]["performance"]:
        status_text = "AT-RISK" if perf["at_risk"] else "OK"
        status_color = "#e03535" if perf["at_risk"] else "#2fbf5f"

        html += f"""                        <tr>
                            <td><strong>{perf['franchisee_id']}</strong></td>
                            <td>{perf['state']}</td>
                            <td>{perf['months_operating']}</td>
                            <td><strong class="status-{perf['enrollment_trajectory'].lower()}">{perf['enrollment_trajectory'].replace('_', ' ').title()}</strong></td>
                            <td><span class="status-{perf['profitability_status'].lower().replace('_', '-')}" style="color: inherit; background: none;">{perf['profitability_status'].replace('_', ' ').title()}</span></td>
                            <td><strong>{perf['satisfaction_score']}/10</strong></td>
                            <td><strong style="color: {status_color}">{status_text}</strong></td>
                        </tr>
"""

    html += """                    </tbody>
                </table>
            </div>

            <!-- EXPANSION STRATEGY TAB -->
            <div id="expansion" class="tab-content">
                <h2 class="section-title">Geographic Expansion Strategy</h2>

                <div class="metrics-grid">
                    <div class="metric-card" id="progress-card">
                        <div class="label">Progress to 100 Centers</div>
                        <div class="value" id="progress-value">0/100</div>
                        <div class="sublabel" id="progress-pct">0% of target</div>
                    </div>

                    <div class="metric-card">
                        <div class="label">Top Territory</div>
                        <div class="value" id="top-territory">—</div>
                        <div class="sublabel" id="top-territory-count">0 centers</div>
                    </div>

                    <div class="metric-card">
                        <div class="label">Biggest Gap</div>
                        <div class="value" id="gap-territory">—</div>
                        <div class="sublabel" id="gap-count">0 centers needed</div>
                    </div>
                </div>

                <h3 class="section-title">Current vs. Target Centers by Territory</h3>
                <table id="expansion-table">
                    <thead>
                        <tr>
                            <th>State</th>
                            <th>Current</th>
                            <th>Target</th>
                            <th>Gap</th>
                            <th>% of Target</th>
                            <th>Status</th>
                        </tr>
                    </thead>
                    <tbody>
                    </tbody>
                </table>
            </div>

            <div class="footer">
                <p><strong>Building Kidz Worldwide</strong> — Franchise Growth Command Center</p>
                <p>Real-time visibility into franchisee pipeline, enrollment performance, launch success, marketing ROI, and franchisee health across the network.</p>
                <p style="margin-top: 12px; font-size: 0.85em; opacity: 0.8;">Generated by Building Kidz Growth Engine • Data as of {engine_data['summaries']['enrollment']['total_enrolled']} students enrolled</p>
            </div>
        </div>
    </div>

    <script>
        const engineData = """ + json.dumps(engine_data) + """;

        // Tab switching
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const tabName = btn.dataset.tab;
                document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
                document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
                btn.classList.add('active');
                document.getElementById(tabName).classList.add('active');
            });
        });

        // Populate expansion data
        function initExpansion() {
            const stateTargets = {
                TX: 50, CA: 45, FL: 35, NY: 25, PA: 20, IL: 18, GA: 16, NC: 15, VA: 12, AZ: 10
            };

            const currentByState = {{}};
            engineData.franchisee.performance.forEach(p => {
                currentByState[p.state] = (currentByState[p.state] || 0) + 1;
            });

            const currentTotal = Object.values(currentByState).reduce((a, b) => a + b, 0);
            const targetTotal = Object.values(stateTargets).reduce((a, b) => a + b, 0);

            // Update summary cards
            const topState = Object.keys(currentByState).sort((a, b) => currentByState[b] - currentByState[a])[0];
            const gapState = Object.keys(stateTargets).reduce((best, s) => {
                const gap1 = stateTargets[s] - (currentByState[s] || 0);
                const gap2 = stateTargets[best] - (currentByState[best] || 0);
                return gap1 > gap2 ? s : best;
            });

            document.getElementById('progress-value').textContent = currentTotal + '/100';
            document.getElementById('progress-pct').textContent = Math.round((currentTotal / 100) * 100) + '% of target';
            document.getElementById('top-territory').textContent = topState || '—';
            document.getElementById('top-territory-count').textContent = (currentByState[topState] || 0) + ' centers';
            document.getElementById('gap-territory').textContent = gapState;
            document.getElementById('gap-count').textContent = (stateTargets[gapState] - (currentByState[gapState] || 0)) + ' centers needed';

            // Build table
            const tbody = document.querySelector('#expansion-table tbody');
            tbody.innerHTML = '';
            Object.keys(stateTargets).sort().forEach(state => {
                const current = currentByState[state] || 0;
                const target = stateTargets[state];
                const gap = target - current;
                const pct = Math.round((current / target) * 100);
                const status = current >= target ? 'complete' : gap <= 5 ? 'on-track' : 'gap';
                const statusColor = status === 'complete' ? '#2fbf5f' : status === 'on-track' ? '#d9a520' : '#e03535';

                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td><strong>${{state}}</strong></td>
                    <td>${{current}}</td>
                    <td>${{target}}</td>
                    <td><strong style="color: ${{gap <= 0 ? '#2fbf5f' : '#e03535'}}">${{gap > 0 ? '−' + gap : '✓'}}</strong></td>
                    <td>
                        <div style="display: flex; align-items: center; gap: 6px;">
                            <div style="flex: 1; height: 8px; background: #eee; border-radius: 4px; overflow: hidden;">
                                <div style="width: ${{Math.min(100, pct)}}%; height: 100%; background: ${{pct >= 100 ? '#2fbf5f' : pct >= 80 ? '#d9a520' : '#e03535'}}; border-radius: 4px;"></div>
                            </div>
                            <span style="font-size: 0.8em; min-width: 30px;">${{pct}}%</span>
                        </div>
                    </td>
                    <td><strong style="color: ${{statusColor}}; text-transform: capitalize;">${{status}}</strong></td>
                `;
                tbody.appendChild(tr);
            });
        }

        initExpansion();
    </script>
</body>
</html>"""

    with open("docs/index.html", "w") as f:
        f.write(html)
    print("✓ docs/index.html")

    # Summary
    summaries = engine_data["summaries"]
    print("\n" + "=" * 70)
    print("BUILDING KIDZ WORLDWIDE — GROWTH ENGINE SUMMARY")
    print("=" * 70)
    print(f"\nFRANCHISEE PIPELINE")
    print(f"  Total prospects: {summaries['pipeline']['total_prospects']}")
    print(f"  Signed: {summaries['pipeline']['signed']} | Opening: {summaries['pipeline']['opening']} | Opened: {summaries['pipeline']['opened']}")

    print(f"\nENROLLMENT PERFORMANCE")
    print(f"  Total enrolled: {summaries['enrollment']['total_enrolled']} students")
    print(f"  Conversion rate: {summaries['enrollment']['avg_conversion_rate']:.1%}")
    print(f"  Monthly revenue: ${summaries['enrollment']['total_monthly_revenue']:,.0f}")
    print(f"  Capacity utilization: {summaries['enrollment']['capacity_utilization_pct']}%")

    print(f"\nLAUNCH SUCCESS")
    print(f"  Launches on-track: {summaries['launch']['successful_launches']}/{summaries['launch']['total_launches']}")
    print(f"  Success rate: {summaries['launch']['success_rate_pct']}%")

    print(f"\nMARKETING PERFORMANCE")
    print(f"  Total budget: ${summaries['marketing']['total_budget']:,.0f}")
    print(f"  Cost per inquiry: ${summaries['marketing']['avg_cost_per_inquiry']:.0f}")
    print(f"  Average ROI: {summaries['marketing']['avg_roi_pct']}%")
    print(f"  Best channel: {summaries['marketing']['best_channel']}")

    print(f"\nFRANCHISEE HEALTH")
    print(f"  Total franchisees: {summaries['franchisee_health']['total_franchisees']}")
    print(f"  Profitable: {summaries['franchisee_health']['profitable_pct']}%")
    print(f"  At-risk: {summaries['franchisee_health']['at_risk_count']}")
    print("=" * 70)


if __name__ == "__main__":
    generate_dashboard()
