"""
Generate static HTML for GitHub Pages deployment
Includes franchise network visualization and tabbed interface
"""

from franchise_engine import FranchiseEngine, FranchiseStatus
import json


def generate_html(engine: FranchiseEngine) -> str:
    """Generate complete HTML page from engine state"""

    network_data = json.dumps(engine.to_dict())
    brand = engine.brand_name
    created_at = engine.created_at[:10]

    # Use template string without f-string to avoid issues with JavaScript braces
    html_template = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BRAND_NAME Franchise Engine</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }

        header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px 30px;
            text-align: center;
        }

        header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
        }

        header p {
            font-size: 1.1em;
            opacity: 0.9;
        }

        .summary {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            padding: 30px;
            background: #f8f9fa;
            border-bottom: 1px solid #e9ecef;
        }

        .stat {
            text-align: center;
        }

        .stat-value {
            font-size: 2.5em;
            font-weight: bold;
            color: #667eea;
            margin-bottom: 5px;
        }

        .stat-label {
            color: #666;
            font-size: 0.95em;
        }

        .tabs {
            display: flex;
            border-bottom: 2px solid #e9ecef;
            background: white;
            position: sticky;
            top: 0;
            z-index: 10;
        }

        .tab-button {
            flex: 1;
            padding: 20px;
            text-align: center;
            background: none;
            border: none;
            font-size: 1.05em;
            font-weight: 600;
            color: #666;
            cursor: pointer;
            transition: all 0.3s ease;
            border-bottom: 3px solid transparent;
            margin-bottom: -2px;
        }

        .tab-button:hover {
            background: #f8f9fa;
            color: #667eea;
        }

        .tab-button.active {
            color: #667eea;
            border-bottom-color: #667eea;
        }

        .tab-content {
            display: none;
            animation: fadeIn 0.3s ease;
        }

        .tab-content.active {
            display: block;
        }

        @keyframes fadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
        }

        .content {
            padding: 30px;
        }

        .region-card {
            background: white;
            border: 1px solid #e9ecef;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 20px;
            transition: box-shadow 0.3s ease;
        }

        .region-card:hover {
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        }

        .region-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
            border-bottom: 2px solid #f0f0f0;
            padding-bottom: 10px;
        }

        .region-name {
            font-size: 1.3em;
            font-weight: bold;
            color: #333;
        }

        .status-badge {
            padding: 6px 12px;
            border-radius: 20px;
            font-size: 0.85em;
            font-weight: 600;
            text-transform: uppercase;
        }

        .status-thriving {
            background: #d4edda;
            color: #155724;
        }

        .status-watch {
            background: #fff3cd;
            color: #856404;
        }

        .status-atrisk {
            background: #f8d7da;
            color: #721c24;
        }

        .center-item {
            background: #f8f9fa;
            padding: 12px;
            margin: 8px 0;
            border-left: 4px solid #667eea;
            border-radius: 4px;
        }

        .metric-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 15px;
            margin-top: 15px;
        }

        .metric {
            text-align: center;
            padding: 10px;
            background: white;
            border-radius: 6px;
        }

        .metric-value {
            font-size: 1.5em;
            font-weight: bold;
            color: #667eea;
        }

        .metric-label {
            font-size: 0.85em;
            color: #666;
            margin-top: 5px;
        }

        .program-card {
            background: #f8f9fa;
            border-left: 4px solid #764ba2;
            padding: 15px;
            margin-bottom: 15px;
            border-radius: 4px;
        }

        .program-name {
            font-weight: bold;
            font-size: 1.1em;
            color: #333;
            margin-bottom: 5px;
        }

        .ticket {
            background: #f8f9fa;
            border: 1px solid #e9ecef;
            padding: 15px;
            margin-bottom: 12px;
            border-radius: 6px;
            border-left: 4px solid #667eea;
        }

        .ticket.resolved {
            opacity: 0.7;
            border-left-color: #28a745;
        }

        .ticket-header {
            display: flex;
            justify-content: space-between;
            align-items: start;
            margin-bottom: 8px;
        }

        .ticket-id {
            font-weight: bold;
            color: #667eea;
        }

        .ticket-status {
            padding: 3px 8px;
            border-radius: 12px;
            font-size: 0.85em;
            font-weight: 600;
            text-transform: uppercase;
        }

        .status-open {
            background: #e7f3ff;
            color: #0050b3;
        }

        .status-in_progress {
            background: #fff7e6;
            color: #ad6800;
        }

        .status-resolved {
            background: #f6ffed;
            color: #274000;
        }

        .compliance-check {
            background: #f8f9fa;
            padding: 12px;
            margin: 8px 0;
            border-radius: 4px;
            border-left: 4px solid #28a745;
        }

        .footer {
            text-align: center;
            padding: 20px;
            background: #f8f9fa;
            color: #666;
            font-size: 0.9em;
        }

        .empty-state {
            text-align: center;
            padding: 40px;
            color: #999;
        }

        @media (max-width: 768px) {
            header h1 { font-size: 1.8em; }
            .summary { grid-template-columns: 1fr 1fr; }
            .metric-grid { grid-template-columns: 1fr 1fr; }
            .tabs { flex-wrap: wrap; }
            .tab-button { flex: 1 0 50%; }
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🚀 BRAND_NAME Franchise Engine</h1>
            <p>Real-time Operations Dashboard</p>
        </header>

        <div class="summary" id="summary">
            <!-- Generated by JavaScript -->
        </div>

        <div class="tabs">
            <button class="tab-button active" onclick="switchTab('network')">📍 Network</button>
            <button class="tab-button" onclick="switchTab('programs')">📚 Programs</button>
            <button class="tab-button" onclick="switchTab('support')">🆘 Support</button>
            <button class="tab-button" onclick="switchTab('record')">📋 Record</button>
        </div>

        <div id="network" class="tab-content active">
            <div class="content" id="network-content">
                <!-- Generated by JavaScript -->
            </div>
        </div>

        <div id="programs" class="tab-content">
            <div class="content" id="programs-content">
                <!-- Generated by JavaScript -->
            </div>
        </div>

        <div id="support" class="tab-content">
            <div class="content" id="support-content">
                <!-- Generated by JavaScript -->
            </div>
        </div>

        <div id="record" class="tab-content">
            <div class="content" id="record-content">
                <!-- Generated by JavaScript -->
            </div>
        </div>

        <div class="footer">
            Generated by Franchise Engine · CREATED_DATE
        </div>
    </div>

    <script>
        const engineData = ENGINE_DATA_JSON;

        function formatPercent(val) {
            return Math.round(val * 100) + '%';
        }

        function renderSummary() {
            const brand = engineData.brand_name;
            const regions = Object.keys(engineData.regions).length;

            let total_centers = 0;
            let total_enrollment = 0;
            let total_health = 0;

            Object.values(engineData.regions).forEach(r => {
                total_centers += r.centers.length;
                total_enrollment += r.centers.reduce((s, c) => s + (c.enrollment || 0), 0);
                total_health += r.centers.reduce((s, c) => s + (c.health || 0), 0);
            });

            const avgHealth = total_centers > 0 ? (total_health / total_centers) : 0;

            const html = `
                <div class="stat">
                    <div class="stat-value">${total_centers}</div>
                    <div class="stat-label">Active Centers</div>
                </div>
                <div class="stat">
                    <div class="stat-value">${total_enrollment.toLocaleString()}</div>
                    <div class="stat-label">Total Enrollment</div>
                </div>
                <div class="stat">
                    <div class="stat-value">${regions}</div>
                    <div class="stat-label">Regions</div>
                </div>
                <div class="stat">
                    <div class="stat-value">${Math.round(avgHealth)}</div>
                    <div class="stat-label">Network Health</div>
                </div>
            `;

            document.getElementById('summary').innerHTML = html;
        }

        function getStatusClass(status) {
            return 'status-' + status.replace('-', '');
        }

        function renderNetwork() {
            let html = '';

            Object.entries(engineData.regions).forEach(([rid, region]) => {
                const metrics = region.metrics;
                const condition = region.centers.length > 0
                    ? (region.centers.reduce((s, c) => s + c.health, 0) / region.centers.length >= 80 ? 'thriving' : 'watch')
                    : 'watch';

                html += `
                    <div class="region-card">
                        <div class="region-header">
                            <div class="region-name">${region.label}</div>
                            <span class="status-badge ${getStatusClass(condition)}">${condition}</span>
                        </div>
                        <div style="font-size: 0.9em; color: #666; margin-bottom: 10px;">
                            ${region.centers.length} center(s)
                        </div>
                `;

                region.centers.forEach(center => {
                    html += `
                        <div class="center-item">
                            <strong>${center.name}</strong> · Health: ${center.health.toFixed(1)}% ·
                            Enrollment: ${center.enrollment}
                        </div>
                    `;
                });

                html += `
                    <div class="metric-grid">
                        <div class="metric">
                            <div class="metric-value">${(metrics.engagement * 100).toFixed(0)}%</div>
                            <div class="metric-label">Engagement</div>
                        </div>
                        <div class="metric">
                            <div class="metric-value">$${(metrics.margin * 100).toFixed(0)}k</div>
                            <div class="metric-label">Margin</div>
                        </div>
                        <div class="metric">
                            <div class="metric-value">${(metrics.staffing).toFixed(1)}</div>
                            <div class="metric-label">Staffing</div>
                        </div>
                        <div class="metric">
                            <div class="metric-value">${(metrics.community).toFixed(0)}%</div>
                            <div class="metric-label">Retention</div>
                        </div>
                    </div>
                    </div>
                `;
            });

            if (html === '') {
                html = '<div class="empty-state">No regions configured</div>';
            }

            document.getElementById('network-content').innerHTML = html;
        }

        function renderPrograms() {
            let html = '';

            Object.values(engineData.programs).forEach(program => {
                html += `
                    <div class="program-card">
                        <div class="program-name">${program.name}</div>
                        <div style="font-size: 0.9em; color: #666;">
                            Type: ${program.program_type} ·
                            Enrollment: ${program.enrollment} ·
                            Instructors: ${program.instructor_count}
                        </div>
                        <div style="margin-top: 8px; padding-top: 8px; border-top: 1px solid #ddd; font-size: 0.85em;">
                            Available at: ${program.centers_offering.join(', ') || 'TBD'}
                        </div>
                    </div>
                `;
            });

            if (html === '') {
                html = '<div class="empty-state">No programs configured</div>';
            }

            document.getElementById('programs-content').innerHTML = html;
        }

        function renderSupport() {
            let html = '';

            engineData.support_tickets.forEach(ticket => {
                const statusClass = 'status-' + ticket.status;
                html += `
                    <div class="ticket ${ticket.status === 'resolved' ? 'resolved' : ''}">
                        <div class="ticket-header">
                            <div>
                                <div class="ticket-id">${ticket.ticket_id}</div>
                                <div style="font-size: 0.9em; color: #666; margin-top: 4px;">
                                    Center: ${ticket.center_name} · Category: ${ticket.category}
                                </div>
                            </div>
                            <span class="ticket-status ${statusClass}">${ticket.status}</span>
                        </div>
                        <div style="margin-top: 8px; padding-top: 8px; border-top: 1px solid #ddd; font-size: 0.85em;">
                            Created: ${new Date(ticket.created_at).toLocaleDateString()}
                            ${ticket.resolved_at ? ' · Resolved: ' + new Date(ticket.resolved_at).toLocaleDateString() : ''}
                        </div>
                        ${ticket.notes ? '<div style="margin-top: 8px; padding: 8px; background: white; border-radius: 4px; font-size: 0.9em;">Notes: ' + ticket.notes + '</div>' : ''}
                    </div>
                `;
            });

            if (html === '') {
                html = '<div class="empty-state">No support tickets</div>';
            }

            document.getElementById('support-content').innerHTML = html;
        }

        function renderRecord() {
            let html = '<h2 style="margin-bottom: 20px;">FDD Compliance & Audit</h2>';

            engineData.compliance_records.forEach(record => {
                html += `
                    <div class="compliance-check">
                        <div style="font-weight: bold; margin-bottom: 5px;">${record.center_name}</div>
                        <div style="font-size: 0.9em; color: #666;">
                            FDD Item 20: <strong>${record.fdd_item_20}</strong> units ·
                            Status: <strong>${record.verification_status}</strong>
                            ${record.last_audit ? ' · Last Audit: ' + record.last_audit : ''}
                        </div>
                        ${record.notes ? '<div style="margin-top: 5px; font-size: 0.85em; font-style: italic;">' + record.notes + '</div>' : ''}
                    </div>
                `;
            });

            if (html === '<h2 style="margin-bottom: 20px;">FDD Compliance & Audit</h2>') {
                html += '<div class="empty-state">No compliance records</div>';
            }

            document.getElementById('record-content').innerHTML = html;
        }

        function switchTab(tabName) {
            document.querySelectorAll('.tab-content').forEach(tab => {
                tab.classList.remove('active');
            });
            document.querySelectorAll('.tab-button').forEach(btn => {
                btn.classList.remove('active');
            });

            document.getElementById(tabName).classList.add('active');
            event.target.classList.add('active');
        }

        // Initialize on load
        document.addEventListener('DOMContentLoaded', () => {
            renderSummary();
            renderNetwork();
            renderPrograms();
            renderSupport();
            renderRecord();
        });
    </script>
</body>
</html>"""

    # Replace placeholders
    html = html_template.replace("BRAND_NAME", brand)
    html = html.replace("CREATED_DATE", created_at)
    html = html.replace("ENGINE_DATA_JSON", network_data)

    return html
