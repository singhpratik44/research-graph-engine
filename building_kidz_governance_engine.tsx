// ============================================================================
// Building Kidz Worldwide — FRANCHISE GROWTH ENGINE (Network Command)
// Director of Marketing & Sales — 100-Center Network Governance
// Groups: GROWTH · ENROLLMENT · LAUNCH · MARKETING · FRANCHISEE · EXPANSION
// All figures deterministic; FDD Item 20 verified network established 2024+
// ============================================================================

import React, { useState, useEffect, useMemo, useRef, Fragment } from "react";

// ---- GEOGRAPHIC STATE COMMAND TABLE (US + 5 ECE target regions) ----
const MAP_STATE_COORDS = {
  TX: [-1.42, 3.72], FL: [3.32, 4.65], CA: [-4.75, 0.62], NY: [4.09, -2.79],
  NC: [3.99, 1.08], PA: [3.8, -1.24], IL: [1.23, -0.47], OH: [2.85, -0.78],
  GA: [2.76, 2.17], VA: [3.71, 0.31], AZ: [-3.52, 2.17], CO: [-1.9, -0.93],
  MA: [5.22, -2.64], WA: [-4.75, -4.03], MN: [0.28, -3.57], MI: [2.19, -2.48],
};

const MAP_DIMS = ["pipeline_health", "enrollment_velocity", "launch_success", "franchisee_profitability"];

function mapClamp(v) { return Math.max(0.02, Math.min(1, v)); }

function buildMapNodes(states, franchiseeData, enrollmentData, launchData, marketingData) {
  const leadsByRegion = {};
  (franchiseeData?.prospects || [])
    .filter(p => p.status === "signed")
    .forEach(p => {
      leadsByRegion[p.territory] = (leadsByRegion[p.territory] || 0) + 1;
    });

  return Object.keys(states).filter(st => MAP_STATE_COORDS[st]).map(st => {
    const centers = states[st] || [];
    const n = centers.length;

    // Pipeline health: signed-not-yet-open / total pipeline
    const pipelineHealth = (franchiseeData?.prospects || [])
      .filter(p => p.territory === st && (p.status === "signed" || p.status === "opening"))
      .length / Math.max(1, (franchiseeData?.prospects || []).filter(p => p.territory === st).length);

    // Enrollment velocity: avg inquiry-to-enrollment conversion
    const enrollmentVelocity = mapClamp(
      (enrollmentData || [])
        .filter(e => e.state === st)
        .reduce((a, e) => a + (e.conversion_rate || 0.5), 0) / Math.max(1, (enrollmentData || []).filter(e => e.state === st).length)
    );

    // Launch success: % of recent launches hitting targets
    const launchSuccess = mapClamp(
      (launchData || [])
        .filter(l => l.state === st && l.status !== "planning")
        .reduce((a, l) => a + (l.vs_target_pct / 100 || 0), 0) / Math.max(1, (launchData || []).filter(l => l.state === st && l.status !== "planning").length)
    );

    // Franchisee profitability: % profitable
    const franchiseeProfitability = mapClamp(
      (franchiseeData?.performance || [])
        .filter(p => p.state === st)
        .reduce((a, p) => a + (p.profitability_status === "profitable" ? 1 : 0), 0) / Math.max(1, (franchiseeData?.performance || []).filter(p => p.state === st).length)
    );

    // Determine overall state: prioritize at-risk launches, then conversion gaps
    const avgHealth = (pipelineHealth + enrollmentVelocity + launchSuccess + franchiseeProfitability) / 4;
    const state = avgHealth >= 0.7 ? "thriving" : avgHealth >= 0.5 ? "watch" : "at-risk";
    const hex = state === "at-risk" ? 0xe03535 : state === "watch" ? 0xd9a520 : 0x2fbf5f;

    return {
      id: st,
      label: st,
      pos: MAP_STATE_COORDS[st],
      state,
      hex,
      n,
      vals: {
        pipeline_health: mapClamp(pipelineHealth),
        enrollment_velocity: enrollmentVelocity,
        launch_success: launchSuccess,
        franchisee_profitability: franchiseeProfitability,
      },
      signedPipeline: leadsByRegion[st] || 0,
    };
  });
}

function mtVal(c, d) { return c.vals[d]; }
function mtHealth(c) { return MAP_DIMS.reduce((s, d) => s + mtVal(c, d), 0) / MAP_DIMS.length; }

function GrowthCommandTableTab({ franchiseeData, enrollmentData, launchData, marketingData, setTab, jumpTo }) {
  const [sel, setSel] = useState(null);
  const [sel2, setSel2] = useState(null);

  const states = {};
  (franchiseeData?.performance || []).forEach(p => {
    if (!states[p.state]) states[p.state] = [];
    states[p.state].push(p);
  });

  const mapNodes = useMemo(() => buildMapNodes(states, franchiseeData, enrollmentData, launchData, marketingData),
    [states, franchiseeData, enrollmentData, launchData, marketingData]);

  const sc = mapNodes.find(c => c.id === sel);
  const sc2 = mapNodes.find(c => c.id === sel2);
  const fallbackList = [...mapNodes].sort((a, b) => mtHealth(b) - mtHealth(a));

  const LEGEND = [["thriving", 0x2fbf5f], ["watch", 0xd9a520], ["at-risk", 0xe03535]];

  return (
    <div>
      <div style={{ fontFamily: "Helvetica", fontSize: 9, color: "#666", marginBottom: 6 }}>
        Every row below is a real state with Building Kidz franchisee activity ({mapNodes.length} territories).
        Metrics: franchise pipeline health (prospects → signed → opening), enrollment conversion rates, launch success tracking, and franchisee profitability.
      </div>

      <div style={{ display: "flex", gap: 6, marginBottom: 6, flexWrap: "wrap", alignItems: "center" }}>
        <span style={{ marginLeft: "auto", display: "flex", gap: 10, alignItems: "center" }}>
          {LEGEND.map(([label, hex]) => (
            <span key={label} style={{ display: "flex", alignItems: "center", gap: 4, fontFamily: "Helvetica", fontSize: 8.5, color: "#666", textTransform: "capitalize" }}>
              <span style={{ width: 8, height: 8, borderRadius: "50%", background: "#" + hex.toString(16).padStart(6, "0"), display: "inline-block" }} />
              {label}
            </span>
          ))}
          <span style={{ display: "flex", alignItems: "center", gap: 4, fontFamily: "Helvetica", fontSize: 8.5, color: "#666" }}>
            <span style={{ width: 0, height: 0, borderLeft: "4px solid transparent", borderRight: "4px solid transparent", borderBottom: "7px solid #6fe8ff", display: "inline-block" }} />
            pipeline active
          </span>
        </span>
      </div>

      <div style={{ padding: 16, fontFamily: "Helvetica", background: "#fff", border: "1px solid #ccc", borderRadius: 6 }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 10 }}>
          <thead><tr style={{ textAlign: "left", color: "#666" }}>
            <th style={{ padding: "4px 6px" }}>State</th>
            <th>Centers</th>
            <th>Pipeline</th>
            <th>Condition</th>
            <th>Composite</th>
          </tr></thead>
          <tbody>
            {fallbackList.map(c => (
              <tr key={c.id} onClick={() => setSel(sel === c.id ? null : c.id)}
                  style={{ borderTop: "1px solid #ccc", cursor: "pointer", background: sel === c.id ? "#f5f5f5" : "transparent" }}>
                <td style={{ padding: "4px 6px", fontWeight: 700 }}>{c.label}</td>
                <td style={{ padding: "4px 6px" }}>{c.n}</td>
                <td style={{ padding: "4px 6px" }}>{c.signedPipeline}</td>
                <td style={{ padding: "4px 6px", textTransform: "capitalize" }}>{c.state}</td>
                <td style={{ padding: "4px 6px" }}>{mtHealth(c).toFixed(2)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {sc && (
        <div style={{ position: "static", top: 10, right: 10, width: 280, marginTop: 10, background: "#fff", border: "1px solid #ccc", borderRadius: 6, padding: 12, fontFamily: "Helvetica", color: "#111" }}>
          <div style={{ display: "flex", justifyContent: "space-between" }}>
            <b style={{ fontSize: 12, color: "#111" }}>{sc.label} — {sc.state}</b>
            <button onClick={() => setSel(null)} style={{ cursor: "pointer", color: "#666", background: "none", border: "none", padding: 0 }}>✕</button>
          </div>
          <div style={{ fontSize: 9, color: "#666", margin: "3px 0 7px" }}>
            {sc.n} center{sc.n > 1 ? "s" : ""} · {sc.signedPipeline} signed in pipeline
          </div>

          {MAP_DIMS.map(d => {
            const v = mtVal(sc, d);
            return (
              <div key={d} style={{ margin: "6px 0" }}>
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: 9 }}>
                  <span style={{ textTransform: "capitalize", color: "#666" }}>{d.replace(/_/g, " ")}</span>
                  <b style={{ color: "#111" }}>{v.toFixed(2)}</b>
                </div>
                <div style={{ height: 4, background: "#eee", borderRadius: 2 }}>
                  <div style={{ height: 4, width: (v * 100) + "%", borderRadius: 2, background: v < 0.35 ? "#e03535" : v < 0.6 ? "#d9a520" : "#2fbf5f" }} />
                </div>
              </div>
            );
          })}

          <div style={{ display: "flex", gap: 8, marginTop: 8, flexWrap: "wrap" }}>
            <button onClick={() => setTab("franchisee")}
              style={{ fontFamily: "Helvetica", fontSize: 9, color: "#8b0000", cursor: "pointer", background: "none", border: "none", padding: 0, textDecoration: "underline" }}>
              view {sc.label} pipeline in Growth →
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

// ============================================================
// FRANCHISEE PIPELINE & ACQUISITION HUB
// ============================================================

interface FranchiseeProspect {
  prospect_id: string;
  company_name: string;
  contact_person: string;
  status: "inquiry" | "qualified" | "negotiation" | "signed" | "opening" | "opened";
  inquiry_date: string;
  projected_open_date?: string;
  territory: string;
  investment_capacity: "under_250k" | "250k_500k" | "500k_1m" | "over_1m";
  experience_level: "franchise_novice" | "franchise_veteran" | "education_background";
  notes?: string;
  last_communication_date: string;
}

interface EnrollmentCenter {
  center_id: string;
  center_name: string;
  state: string;
  opening_date: string;
  status: "planning" | "launching" | "operational" | "mature";
  monthly_inquiries: number;
  inquiry_to_enrollment_conversion_rate: number;
  current_enrollment: number;
  capacity: number;
  monthly_tuition_revenue: number;
  franchisee_satisfaction: number;
}

interface CenterLaunch {
  center_id: string;
  franchisee_id: string;
  soft_opening_date: string;
  grand_opening_date: string;
  ninety_day_target: number;
  enrollment_at_30_days: number;
  enrollment_at_60_days: number;
  enrollment_at_90_days: number;
  vs_target_pct: number;
  status: "planning" | "launching" | "active" | "closed";
}

interface MarketingCampaign {
  campaign_id: string;
  campaign_name: string;
  channel: "digital" | "local" | "events" | "partnerships" | "franchisee_run";
  budget: number;
  inquiries_generated: number;
  cost_per_inquiry: number;
  conversions: number;
  roi_pct: number;
}

interface FranchiseePerformance {
  franchisee_id: string;
  state: string;
  months_operating: number;
  enrollment_trajectory: "growing" | "flat" | "declining";
  profitability_status: "profitable" | "breaking_even" | "losing_money";
  satisfaction_score: number;
  at_risk: boolean;
}

function GrowthHubTab({ franchiseeData, enrollmentData, launchData, marketingData }) {
  const totalProspects = franchiseeData?.prospects?.length || 0;
  const signedProspects = franchiseeData?.prospects?.filter((p: FranchiseeProspect) => p.status === "signed").length || 0;
  const openingProspects = franchiseeData?.prospects?.filter((p: FranchiseeProspect) => p.status === "opening").length || 0;
  const openedCenters = franchiseeData?.prospects?.filter((p: FranchiseeProspect) => p.status === "opened").length || 0;

  const avgConversionRate = enrollmentData
    ? (enrollmentData.reduce((a: number, e: EnrollmentCenter) => a + e.inquiry_to_enrollment_conversion_rate, 0) / enrollmentData.length * 100).toFixed(1)
    : "—";

  const successfulLaunches = launchData
    ? launchData.filter((l: CenterLaunch) => l.vs_target_pct >= 60).length
    : 0;
  const totalLaunches = launchData?.length || 0;

  const avgMarketingROI = marketingData
    ? (marketingData.reduce((a: number, c: MarketingCampaign) => a + c.roi_pct, 0) / marketingData.length).toFixed(1)
    : "—";

  return (
    <div style={{ padding: 16, fontFamily: "Helvetica" }}>
      <h2 style={{ fontSize: 16, fontWeight: 700, marginBottom: 12, color: "#111" }}>Franchisee Growth Command Center</h2>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 12, marginBottom: 20 }}>
        <div style={{ border: "1px solid #ccc", borderRadius: 6, padding: 12, background: "#fff" }}>
          <div style={{ fontSize: 9, color: "#666", fontWeight: 700, marginBottom: 6, textTransform: "uppercase" }}>PIPELINE: Inquiry → Opened</div>
          <div style={{ fontSize: 14, fontWeight: 700, color: "#111", marginBottom: 3 }}>{totalProspects}</div>
          <div style={{ fontSize: 8, color: "#666", marginBottom: 8 }}>total prospects</div>
          <div style={{ fontSize: 9, marginBottom: 4 }}>
            <span style={{ color: "#2fbf5f", fontWeight: 700 }}>{signedProspects}</span> signed ·
            <span style={{ color: "#d9a520", fontWeight: 700, marginLeft: 4 }}>{openingProspects}</span> opening ·
            <span style={{ color: "#111", fontWeight: 700, marginLeft: 4 }}>{openedCenters}</span> opened
          </div>
        </div>

        <div style={{ border: "1px solid #ccc", borderRadius: 6, padding: 12, background: "#fff" }}>
          <div style={{ fontSize: 9, color: "#666", fontWeight: 700, marginBottom: 6, textTransform: "uppercase" }}>ENROLLMENT: Inquiry→Enrollment</div>
          <div style={{ fontSize: 14, fontWeight: 700, color: "#111", marginBottom: 3 }}>{avgConversionRate}%</div>
          <div style={{ fontSize: 8, color: "#666", marginBottom: 8 }}>network-wide conversion rate (target: 50-75%)</div>
        </div>

        <div style={{ border: "1px solid #ccc", borderRadius: 6, padding: 12, background: "#fff" }}>
          <div style={{ fontSize: 9, color: "#666", fontWeight: 700, marginBottom: 6, textTransform: "uppercase" }}>LAUNCH SUCCESS: 90-Day Targets</div>
          <div style={{ fontSize: 14, fontWeight: 700, color: "#111", marginBottom: 3 }}>{successfulLaunches}/{totalLaunches}</div>
          <div style={{ fontSize: 8, color: "#666", marginBottom: 8 }}>launches hitting ≥60% target (on-track)</div>
        </div>

        <div style={{ border: "1px solid #ccc", borderRadius: 6, padding: 12, background: "#fff" }}>
          <div style={{ fontSize: 9, color: "#666", fontWeight: 700, marginBottom: 6, textTransform: "uppercase" }}>MARKETING ROI</div>
          <div style={{ fontSize: 14, fontWeight: 700, color: "#111", marginBottom: 3 }}>{avgMarketingROI}%</div>
          <div style={{ fontSize: 8, color: "#666", marginBottom: 8 }}>average ROI across all channels</div>
        </div>
      </div>

      <h3 style={{ fontSize: 12, fontWeight: 700, marginBottom: 8, color: "#111" }}>Active Franchisee Prospects (In Pipeline)</h3>
      <div style={{ overflowX: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 9 }}>
          <thead>
            <tr style={{ borderBottom: "1px solid #ccc", textAlign: "left" }}>
              <th style={{ padding: "6px", fontWeight: 700, color: "#666" }}>Company</th>
              <th style={{ padding: "6px", fontWeight: 700, color: "#666" }}>Contact</th>
              <th style={{ padding: "6px", fontWeight: 700, color: "#666" }}>Status</th>
              <th style={{ padding: "6px", fontWeight: 700, color: "#666" }}>Territory</th>
              <th style={{ padding: "6px", fontWeight: 700, color: "#666" }}>Projected Open</th>
              <th style={{ padding: "6px", fontWeight: 700, color: "#666" }}>Investment</th>
              <th style={{ padding: "6px", fontWeight: 700, color: "#666" }}>Last Contact</th>
            </tr>
          </thead>
          <tbody>
            {(franchiseeData?.prospects || []).map((p: FranchiseeProspect) => (
              <tr key={p.prospect_id} style={{ borderBottom: "1px solid #eee" }}>
                <td style={{ padding: "6px" }}><b>{p.company_name}</b></td>
                <td style={{ padding: "6px" }}>{p.contact_person}</td>
                <td style={{ padding: "6px", fontWeight: 700, color: p.status === "signed" ? "#2fbf5f" : p.status === "opening" ? "#d9a520" : "#111" }}>
                  {p.status}
                </td>
                <td style={{ padding: "6px" }}>{p.territory}</td>
                <td style={{ padding: "6px" }}>{p.projected_open_date || "—"}</td>
                <td style={{ padding: "6px" }}>{p.investment_capacity.replace(/_/g, "-")}</td>
                <td style={{ padding: "6px", fontSize: 8, color: "#666" }}>{p.last_communication_date}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ============================================================
// ENROLLMENT PERFORMANCE HUB
// ============================================================

function EnrollmentHubTab({ enrollmentData }) {
  const totalEnrollment = enrollmentData
    ? enrollmentData.reduce((a: number, e: EnrollmentCenter) => a + e.current_enrollment, 0)
    : 0;

  const totalInquiries = enrollmentData
    ? enrollmentData.reduce((a: number, e: EnrollmentCenter) => a + e.monthly_inquiries, 0)
    : 0;

  const avgCapacityUtilization = enrollmentData
    ? (enrollmentData.reduce((a: number, e: EnrollmentCenter) => a + (e.current_enrollment / e.capacity), 0) / enrollmentData.length * 100).toFixed(1)
    : "—";

  const totalMonthlyRevenue = enrollmentData
    ? enrollmentData.reduce((a: number, e: EnrollmentCenter) => a + e.monthly_tuition_revenue, 0)
    : 0;

  const avgSatisfaction = enrollmentData
    ? (enrollmentData.reduce((a: number, e: EnrollmentCenter) => a + e.franchisee_satisfaction, 0) / enrollmentData.length).toFixed(1)
    : "—";

  return (
    <div style={{ padding: 16, fontFamily: "Helvetica" }}>
      <h2 style={{ fontSize: 16, fontWeight: 700, marginBottom: 12, color: "#111" }}>Network Enrollment Performance</h2>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 12, marginBottom: 20 }}>
        <div style={{ border: "1px solid #ccc", borderRadius: 6, padding: 12, background: "#fff" }}>
          <div style={{ fontSize: 9, color: "#666", fontWeight: 700, marginBottom: 6, textTransform: "uppercase" }}>Total Enrolled</div>
          <div style={{ fontSize: 18, fontWeight: 700, color: "#2fbf5f", marginBottom: 3 }}>{totalEnrollment}</div>
          <div style={{ fontSize: 8, color: "#666" }}>students across all centers</div>
        </div>

        <div style={{ border: "1px solid #ccc", borderRadius: 6, padding: 12, background: "#fff" }}>
          <div style={{ fontSize: 9, color: "#666", fontWeight: 700, marginBottom: 6, textTransform: "uppercase" }}>Monthly Inquiries</div>
          <div style={{ fontSize: 18, fontWeight: 700, color: "#111", marginBottom: 3 }}>{totalInquiries}</div>
          <div style={{ fontSize: 8, color: "#666" }}>parent inquiries this month</div>
        </div>

        <div style={{ border: "1px solid #ccc", borderRadius: 6, padding: 12, background: "#fff" }}>
          <div style={{ fontSize: 9, color: "#666", fontWeight: 700, marginBottom: 6, textTransform: "uppercase" }}>Avg Capacity</div>
          <div style={{ fontSize: 18, fontWeight: 700, color: "#111", marginBottom: 3 }}>{avgCapacityUtilization}%</div>
          <div style={{ fontSize: 8, color: "#666" }}>utilization (target: 70-85%)</div>
        </div>

        <div style={{ border: "1px solid #ccc", borderRadius: 6, padding: 12, background: "#fff" }}>
          <div style={{ fontSize: 9, color: "#666", fontWeight: 700, marginBottom: 6, textTransform: "uppercase" }}>Monthly Revenue</div>
          <div style={{ fontSize: 18, fontWeight: 700, color: "#111", marginBottom: 3 }}>${(totalMonthlyRevenue / 1000).toFixed(0)}k</div>
          <div style={{ fontSize: 8, color: "#666" }}>total tuition revenue</div>
        </div>

        <div style={{ border: "1px solid #ccc", borderRadius: 6, padding: 12, background: "#fff" }}>
          <div style={{ fontSize: 9, color: "#666", fontWeight: 700, marginBottom: 6, textTransform: "uppercase" }}>Franchisee Satisfaction</div>
          <div style={{ fontSize: 18, fontWeight: 700, color: "#111", marginBottom: 3 }}>{avgSatisfaction}/10</div>
          <div style={{ fontSize: 8, color: "#666" }}>average satisfaction score</div>
        </div>
      </div>

      <h3 style={{ fontSize: 12, fontWeight: 700, marginBottom: 8, color: "#111" }}>Center-Level Enrollment Metrics</h3>
      <div style={{ overflowX: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 9 }}>
          <thead>
            <tr style={{ borderBottom: "1px solid #ccc", textAlign: "left" }}>
              <th style={{ padding: "6px", fontWeight: 700, color: "#666" }}>Center</th>
              <th style={{ padding: "6px", fontWeight: 700, color: "#666" }}>Enrolled</th>
              <th style={{ padding: "6px", fontWeight: 700, color: "#666" }}>Monthly Inquiries</th>
              <th style={{ padding: "6px", fontWeight: 700, color: "#666" }}>Conversion %</th>
              <th style={{ padding: "6px", fontWeight: 700, color: "#666" }}>Capacity %</th>
              <th style={{ padding: "6px", fontWeight: 700, color: "#666" }}>Monthly Revenue</th>
              <th style={{ padding: "6px", fontWeight: 700, color: "#666" }}>Franchisee Score</th>
            </tr>
          </thead>
          <tbody>
            {(enrollmentData || []).map((e: EnrollmentCenter) => (
              <tr key={e.center_id} style={{ borderBottom: "1px solid #eee" }}>
                <td style={{ padding: "6px" }}><b>{e.center_name}</b></td>
                <td style={{ padding: "6px" }}>{e.current_enrollment}</td>
                <td style={{ padding: "6px" }}>{e.monthly_inquiries}</td>
                <td style={{ padding: "6px", fontWeight: 700, color: e.inquiry_to_enrollment_conversion_rate >= 0.50 ? "#2fbf5f" : "#e03535" }}>
                  {(e.inquiry_to_enrollment_conversion_rate * 100).toFixed(0)}%
                </td>
                <td style={{ padding: "6px" }}>
                  {((e.current_enrollment / e.capacity) * 100).toFixed(0)}%
                </td>
                <td style={{ padding: "6px", fontWeight: 700 }}>${(e.monthly_tuition_revenue / 1000).toFixed(1)}k</td>
                <td style={{ padding: "6px", fontWeight: 700, color: e.franchisee_satisfaction >= 7.5 ? "#2fbf5f" : "#d9a520" }}>
                  {e.franchisee_satisfaction}/10
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ============================================================
// LAUNCH SUCCESS & MARKETING ROI HUB
// ============================================================

function LaunchMarketingHubTab({ launchData, marketingData }) {
  const totalLaunches = launchData?.length || 0;
  const successfulLaunches = launchData?.filter((l: CenterLaunch) => l.vs_target_pct >= 60).length || 0;
  const atRiskLaunches = launchData?.filter((l: CenterLaunch) => l.vs_target_pct < 40 && l.status !== "closed").length || 0;

  const totalMarketingBudget = marketingData
    ? marketingData.reduce((a: number, c: MarketingCampaign) => a + c.budget, 0)
    : 0;

  const totalInquiriesGenerated = marketingData
    ? marketingData.reduce((a: number, c: MarketingCampaign) => a + c.inquiries_generated, 0)
    : 0;

  const blendedCostPerInquiry = totalInquiriesGenerated > 0
    ? (totalMarketingBudget / totalInquiriesGenerated).toFixed(0)
    : "—";

  const bestChannel = marketingData
    ? marketingData.reduce((best: MarketingCampaign | null, c: MarketingCampaign) =>
        !best || c.roi_pct > best.roi_pct ? c : best, null)
    : null;

  return (
    <div style={{ padding: 16, fontFamily: "Helvetica" }}>
      <h2 style={{ fontSize: 16, fontWeight: 700, marginBottom: 12, color: "#111" }}>Launch Success & Marketing Performance</h2>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 12, marginBottom: 20 }}>
        <div style={{ border: "1px solid #ccc", borderRadius: 6, padding: 12, background: "#fff" }}>
          <div style={{ fontSize: 9, color: "#666", fontWeight: 700, marginBottom: 6, textTransform: "uppercase" }}>Launch Success Rate</div>
          <div style={{ fontSize: 18, fontWeight: 700, color: "#2fbf5f", marginBottom: 3 }}>
            {totalLaunches > 0 ? ((successfulLaunches / totalLaunches) * 100).toFixed(0) : "—"}%
          </div>
          <div style={{ fontSize: 8, color: "#666" }}>{successfulLaunches}/{totalLaunches} launches on-track (≥60% of target)</div>
        </div>

        <div style={{ border: "1px solid #ccc", borderRadius: 6, padding: 12, background: "#fff" }}>
          <div style={{ fontSize: 9, color: "#666", fontWeight: 700, marginBottom: 6, textTransform: "uppercase" }}>At-Risk Launches</div>
          <div style={{ fontSize: 18, fontWeight: 700, color: atRiskLaunches > 0 ? "#e03535" : "#2fbf5f", marginBottom: 3 }}>
            {atRiskLaunches}
          </div>
          <div style={{ fontSize: 8, color: "#666" }}>need intervention (&lt;40% target)</div>
        </div>

        <div style={{ border: "1px solid #ccc", borderRadius: 6, padding: 12, background: "#fff" }}>
          <div style={{ fontSize: 9, color: "#666", fontWeight: 700, marginBottom: 6, textTransform: "uppercase" }}>Total Marketing Budget</div>
          <div style={{ fontSize: 18, fontWeight: 700, color: "#111", marginBottom: 3 }}>${(totalMarketingBudget / 1000).toFixed(0)}k</div>
          <div style={{ fontSize: 8, color: "#666" }}>across all channels this period</div>
        </div>

        <div style={{ border: "1px solid #ccc", borderRadius: 6, padding: 12, background: "#fff" }}>
          <div style={{ fontSize: 9, color: "#666", fontWeight: 700, marginBottom: 6, textTransform: "uppercase" }}>Cost Per Inquiry</div>
          <div style={{ fontSize: 18, fontWeight: 700, color: "#111", marginBottom: 3 }}>${blendedCostPerInquiry}</div>
          <div style={{ fontSize: 8, color: "#666" }}>blended across all channels (target: $60-$150)</div>
        </div>

        <div style={{ border: "1px solid #ccc", borderRadius: 6, padding: 12, background: "#fff" }}>
          <div style={{ fontSize: 9, color: "#666", fontWeight: 700, marginBottom: 6, textTransform: "uppercase" }}>Best Performing Channel</div>
          <div style={{ fontSize: 14, fontWeight: 700, color: "#2fbf5f", marginBottom: 3 }}>
            {bestChannel?.channel || "—"}
          </div>
          <div style={{ fontSize: 8, color: "#666" }}>{bestChannel ? `${bestChannel.roi_pct.toFixed(0)}% ROI` : "no data"}</div>
        </div>
      </div>

      <h3 style={{ fontSize: 12, fontWeight: 700, marginBottom: 8, color: "#111" }}>Launch Success Tracking (90-Day Targets)</h3>
      <div style={{ overflowX: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 9 }}>
          <thead>
            <tr style={{ borderBottom: "1px solid #ccc", textAlign: "left" }}>
              <th style={{ padding: "6px", fontWeight: 700, color: "#666" }}>Center</th>
              <th style={{ padding: "6px", fontWeight: 700, color: "#666" }}>Grand Opening</th>
              <th style={{ padding: "6px", fontWeight: 700, color: "#666" }}>90-Day Target</th>
              <th style={{ padding: "6px", fontWeight: 700, color: "#666" }}>@30 Days</th>
              <th style={{ padding: "6px", fontWeight: 700, color: "#666" }}>@60 Days</th>
              <th style={{ padding: "6px", fontWeight: 700, color: "#666" }}>@90 Days</th>
              <th style={{ padding: "6px", fontWeight: 700, color: "#666" }}>Vs Target</th>
              <th style={{ padding: "6px", fontWeight: 700, color: "#666" }}>Status</th>
            </tr>
          </thead>
          <tbody>
            {(launchData || []).map((l: CenterLaunch) => (
              <tr key={l.center_id} style={{ borderBottom: "1px solid #eee" }}>
                <td style={{ padding: "6px" }}><b>{l.center_id}</b></td>
                <td style={{ padding: "6px", fontSize: 8 }}>{l.grand_opening_date}</td>
                <td style={{ padding: "6px" }}>{l.ninety_day_target}</td>
                <td style={{ padding: "6px" }}>{l.enrollment_at_30_days}</td>
                <td style={{ padding: "6px" }}>{l.enrollment_at_60_days}</td>
                <td style={{ padding: "6px", fontWeight: 700 }}>{l.enrollment_at_90_days}</td>
                <td style={{ padding: "6px", fontWeight: 700, color: l.vs_target_pct >= 60 ? "#2fbf5f" : l.vs_target_pct >= 40 ? "#d9a520" : "#e03535" }}>
                  {l.vs_target_pct.toFixed(0)}%
                </td>
                <td style={{ padding: "6px", fontWeight: 700, color: l.vs_target_pct >= 60 ? "#2fbf5f" : l.vs_target_pct >= 40 ? "#d9a520" : "#e03535", textTransform: "capitalize" }}>
                  {l.status}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <h3 style={{ fontSize: 12, fontWeight: 700, marginBottom: 8, marginTop: 20, color: "#111" }}>Marketing Campaign ROI by Channel</h3>
      <div style={{ overflowX: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 9 }}>
          <thead>
            <tr style={{ borderBottom: "1px solid #ccc", textAlign: "left" }}>
              <th style={{ padding: "6px", fontWeight: 700, color: "#666" }}>Campaign</th>
              <th style={{ padding: "6px", fontWeight: 700, color: "#666" }}>Channel</th>
              <th style={{ padding: "6px", fontWeight: 700, color: "#666" }}>Budget</th>
              <th style={{ padding: "6px", fontWeight: 700, color: "#666" }}>Inquiries</th>
              <th style={{ padding: "6px", fontWeight: 700, color: "#666" }}>CPI</th>
              <th style={{ padding: "6px", fontWeight: 700, color: "#666" }}>Conversions</th>
              <th style={{ padding: "6px", fontWeight: 700, color: "#666" }}>ROI %</th>
            </tr>
          </thead>
          <tbody>
            {(marketingData || []).map((c: MarketingCampaign) => (
              <tr key={c.campaign_id} style={{ borderBottom: "1px solid #eee" }}>
                <td style={{ padding: "6px" }}><b>{c.campaign_name}</b></td>
                <td style={{ padding: "6px", textTransform: "capitalize" }}>{c.channel.replace(/_/g, " ")}</td>
                <td style={{ padding: "6px" }}>${(c.budget / 1000).toFixed(1)}k</td>
                <td style={{ padding: "6px" }}>{c.inquiries_generated}</td>
                <td style={{ padding: "6px", fontWeight: 700 }}>${c.cost_per_inquiry.toFixed(0)}</td>
                <td style={{ padding: "6px" }}>{c.conversions}</td>
                <td style={{ padding: "6px", fontWeight: 700, color: c.roi_pct > 100 ? "#2fbf5f" : c.roi_pct > 50 ? "#d9a520" : "#e03535" }}>
                  {c.roi_pct.toFixed(0)}%
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ============================================================
// FRANCHISEE HEALTH HUB
// ============================================================

function FranchiseeHealthHubTab({ franchiseeData }) {
  const totalFranchisees = franchiseeData?.performance?.length || 0;
  const profitableFranchisees = franchiseeData?.performance?.filter((f: FranchiseePerformance) => f.profitability_status === "profitable").length || 0;
  const atRiskFranchisees = franchiseeData?.performance?.filter((f: FranchiseePerformance) => f.at_risk).length || 0;

  const avgSatisfaction = franchiseeData?.performance
    ? (franchiseeData.performance.reduce((a: number, f: FranchiseePerformance) => a + f.satisfaction_score, 0) / franchiseeData.performance.length).toFixed(1)
    : "—";

  return (
    <div style={{ padding: 16, fontFamily: "Helvetica" }}>
      <h2 style={{ fontSize: 16, fontWeight: 700, marginBottom: 12, color: "#111" }}>Franchisee Health & Support</h2>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 12, marginBottom: 20 }}>
        <div style={{ border: "1px solid #ccc", borderRadius: 6, padding: 12, background: "#fff" }}>
          <div style={{ fontSize: 9, color: "#666", fontWeight: 700, marginBottom: 6, textTransform: "uppercase" }}>Total Franchisees</div>
          <div style={{ fontSize: 18, fontWeight: 700, color: "#111", marginBottom: 3 }}>{totalFranchisees}</div>
          <div style={{ fontSize: 8, color: "#666" }}>operating centers in network</div>
        </div>

        <div style={{ border: "1px solid #ccc", borderRadius: 6, padding: 12, background: "#fff" }}>
          <div style={{ fontSize: 9, color: "#666", fontWeight: 700, marginBottom: 6, textTransform: "uppercase" }}>Profitable</div>
          <div style={{ fontSize: 18, fontWeight: 700, color: "#2fbf5f", marginBottom: 3 }}>
            {totalFranchisees > 0 ? ((profitableFranchisees / totalFranchisees) * 100).toFixed(0) : "—"}%
          </div>
          <div style={{ fontSize: 8, color: "#666" }}>{profitableFranchisees}/{totalFranchisees} franchisees</div>
        </div>

        <div style={{ border: "1px solid #ccc", borderRadius: 6, padding: 12, background: "#fff" }}>
          <div style={{ fontSize: 9, color: "#666", fontWeight: 700, marginBottom: 6, textTransform: "uppercase" }}>At-Risk</div>
          <div style={{ fontSize: 18, fontWeight: 700, color: atRiskFranchisees > 0 ? "#e03535" : "#2fbf5f", marginBottom: 3 }}>
            {atRiskFranchisees}
          </div>
          <div style={{ fontSize: 8, color: "#666" }}>need intervention or support</div>
        </div>

        <div style={{ border: "1px solid #ccc", borderRadius: 6, padding: 12, background: "#fff" }}>
          <div style={{ fontSize: 9, color: "#666", fontWeight: 700, marginBottom: 6, textTransform: "uppercase" }}>Avg Satisfaction</div>
          <div style={{ fontSize: 18, fontWeight: 700, color: "#111", marginBottom: 3 }}>{avgSatisfaction}/10</div>
          <div style={{ fontSize: 8, color: "#666" }}>franchisee satisfaction score</div>
        </div>
      </div>

      <h3 style={{ fontSize: 12, fontWeight: 700, marginBottom: 8, color: "#111" }}>Franchisee Performance & Health Status</h3>
      <div style={{ overflowX: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 9 }}>
          <thead>
            <tr style={{ borderBottom: "1px solid #ccc", textAlign: "left" }}>
              <th style={{ padding: "6px", fontWeight: 700, color: "#666" }}>Franchisee ID</th>
              <th style={{ padding: "6px", fontWeight: 700, color: "#666" }}>Territory</th>
              <th style={{ padding: "6px", fontWeight: 700, color: "#666" }}>Months Operating</th>
              <th style={{ padding: "6px", fontWeight: 700, color: "#666" }}>Trajectory</th>
              <th style={{ padding: "6px", fontWeight: 700, color: "#666" }}>Profitability</th>
              <th style={{ padding: "6px", fontWeight: 700, color: "#666" }}>Satisfaction</th>
              <th style={{ padding: "6px", fontWeight: 700, color: "#666" }}>Status</th>
            </tr>
          </thead>
          <tbody>
            {(franchiseeData?.performance || []).map((f: FranchiseePerformance) => (
              <tr key={f.franchisee_id} style={{ borderBottom: "1px solid #eee" }}>
                <td style={{ padding: "6px" }}><b>{f.franchisee_id}</b></td>
                <td style={{ padding: "6px" }}>{f.state}</td>
                <td style={{ padding: "6px" }}>{f.months_operating}</td>
                <td style={{ padding: "6px", fontWeight: 700, color: f.enrollment_trajectory === "growing" ? "#2fbf5f" : f.enrollment_trajectory === "flat" ? "#d9a520" : "#e03535", textTransform: "capitalize" }}>
                  {f.enrollment_trajectory}
                </td>
                <td style={{ padding: "6px", fontWeight: 700, color: f.profitability_status === "profitable" ? "#2fbf5f" : "#e03535", textTransform: "capitalize" }}>
                  {f.profitability_status}
                </td>
                <td style={{ padding: "6px", fontWeight: 700 }}>{f.satisfaction_score}/10</td>
                <td style={{ padding: "6px", fontWeight: 700, color: f.at_risk ? "#e03535" : "#2fbf5f" }}>
                  {f.at_risk ? "AT-RISK" : "OK"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ============================================================
// EXPANSION STRATEGY HUB
// ============================================================

function ExpansionStrategyHubTab({ franchiseeData }) {
  const stateTargets = {
    TX: 50, CA: 45, FL: 35, NY: 25, PA: 20, IL: 18, GA: 16, NC: 15, VA: 12, AZ: 10,
  };

  const currentByState: Record<string, number> = {};
  (franchiseeData?.performance || []).forEach((f: FranchiseePerformance) => {
    currentByState[f.state] = (currentByState[f.state] || 0) + 1;
  });

  const currentTotal = Object.values(currentByState).reduce((a, b) => a + b, 0);
  const targetTotal = Object.values(stateTargets).reduce((a, b) => a + b, 0);

  return (
    <div style={{ padding: 16, fontFamily: "Helvetica" }}>
      <h2 style={{ fontSize: 16, fontWeight: 700, marginBottom: 12, color: "#111" }}>Geographic Expansion Strategy</h2>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 12, marginBottom: 20 }}>
        <div style={{ border: "1px solid #ccc", borderRadius: 6, padding: 12, background: "#fff" }}>
          <div style={{ fontSize: 9, color: "#666", fontWeight: 700, marginBottom: 6, textTransform: "uppercase" }}>Progress to 100 Centers</div>
          <div style={{ fontSize: 18, fontWeight: 700, color: currentTotal >= 100 ? "#2fbf5f" : "#d9a520", marginBottom: 3 }}>
            {currentTotal}/100
          </div>
          <div style={{ fontSize: 8, color: "#666" }}>{((currentTotal / 100) * 100).toFixed(0)}% of target</div>
        </div>

        <div style={{ border: "1px solid #ccc", borderRadius: 6, padding: 12, background: "#fff" }}>
          <div style={{ fontSize: 9, color: "#666", fontWeight: 700, marginBottom: 6, textTransform: "uppercase" }}>Top Territory</div>
          <div style={{ fontSize: 14, fontWeight: 700, color: "#111", marginBottom: 3 }}>
            {Object.keys(currentByState).sort((a, b) => currentByState[b] - currentByState[a])[0]}
          </div>
          <div style={{ fontSize: 8, color: "#666" }}>
            {Math.max(...Object.values(currentByState))} centers
          </div>
        </div>

        <div style={{ border: "1px solid #ccc", borderRadius: 6, padding: 12, background: "#fff" }}>
          <div style={{ fontSize: 9, color: "#666", fontWeight: 700, marginBottom: 6, textTransform: "uppercase" }}>Biggest Gap</div>
          <div style={{ fontSize: 14, fontWeight: 700, color: "#111", marginBottom: 3 }}>
            {
              Object.keys(stateTargets).reduce((bestState, state) => {
                const gap = stateTargets[state] - (currentByState[state] || 0);
                const bestGap = stateTargets[bestState] - (currentByState[bestState] || 0);
                return gap > bestGap ? state : bestState;
              })
            }
          </div>
          <div style={{ fontSize: 8, color: "#666" }}>
            {
              Math.max(
                ...Object.keys(stateTargets).map(state => stateTargets[state] - (currentByState[state] || 0))
              )
            } centers needed
          </div>
        </div>
      </div>

      <h3 style={{ fontSize: 12, fontWeight: 700, marginBottom: 8, color: "#111" }}>Current vs. Target Centers by Territory</h3>
      <div style={{ overflowX: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 9 }}>
          <thead>
            <tr style={{ borderBottom: "1px solid #ccc", textAlign: "left" }}>
              <th style={{ padding: "6px", fontWeight: 700, color: "#666" }}>State</th>
              <th style={{ padding: "6px", fontWeight: 700, color: "#666" }}>Current</th>
              <th style={{ padding: "6px", fontWeight: 700, color: "#666" }}>Target</th>
              <th style={{ padding: "6px", fontWeight: 700, color: "#666" }}>Gap</th>
              <th style={{ padding: "6px", fontWeight: 700, color: "#666" }}>% of Target</th>
              <th style={{ padding: "6px", fontWeight: 700, color: "#666" }}>Status</th>
            </tr>
          </thead>
          <tbody>
            {Object.keys(stateTargets).sort().map(state => {
              const current = currentByState[state] || 0;
              const target = stateTargets[state];
              const gap = target - current;
              const pctOfTarget = ((current / target) * 100).toFixed(0);
              const status = current >= target ? "complete" : gap <= 5 ? "on-track" : "gap";

              return (
                <tr key={state} style={{ borderBottom: "1px solid #eee" }}>
                  <td style={{ padding: "6px", fontWeight: 700 }}>{state}</td>
                  <td style={{ padding: "6px" }}>{current}</td>
                  <td style={{ padding: "6px" }}>{target}</td>
                  <td style={{ padding: "6px", fontWeight: 700, color: gap <= 0 ? "#2fbf5f" : "#e03535" }}>
                    {gap > 0 ? "−" + gap : "✓"}
                  </td>
                  <td style={{ padding: "6px" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
                      <div style={{ width: 60, height: 8, background: "#eee", borderRadius: 4, overflow: "hidden" }}>
                        <div style={{
                          width: Math.min(100, parseInt(pctOfTarget)) + "%",
                          height: "100%",
                          background: parseInt(pctOfTarget) >= 100 ? "#2fbf5f" : parseInt(pctOfTarget) >= 80 ? "#d9a520" : "#e03535",
                          borderRadius: 4
                        }} />
                      </div>
                      <span style={{ fontSize: 8 }}>{pctOfTarget}%</span>
                    </div>
                  </td>
                  <td style={{ padding: "6px", fontWeight: 700, color: status === "complete" ? "#2fbf5f" : status === "on-track" ? "#d9a520" : "#e03535", textTransform: "capitalize" }}>
                    {status}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ============================================================
// MAIN APP COMPONENT
// ============================================================

export default function BuildingKidzGovernanceEngine({ data }: { data: any }) {
  const [tab, setTab] = useState("growth");

  const franchiseeData = data?.franchisee;
  const enrollmentData = data?.enrollment;
  const launchData = data?.launch;
  const marketingData = data?.marketing;

  return (
    <div style={{ fontFamily: "Helvetica", fontSize: 11, color: "#111", background: "#fafafa", minHeight: "100vh", padding: 20 }}>
      <div style={{ maxWidth: 1400, margin: "0 auto", background: "#fff", borderRadius: 8, boxShadow: "0 2px 8px rgba(0,0,0,0.1)" }}>
        <div style={{ padding: 24, borderBottom: "1px solid #eee" }}>
          <h1 style={{ fontSize: 28, fontWeight: 800, marginBottom: 6, color: "#111" }}>🎨 Building Kidz Worldwide</h1>
          <p style={{ fontSize: 12, color: "#666", marginBottom: 12 }}>Franchise Growth Command Center — 100-Center Network Governance</p>
          <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
            <button
              onClick={() => setTab("growth")}
              style={{
                padding: "8px 14px",
                fontFamily: "Helvetica",
                fontWeight: tab === "growth" ? 700 : 500,
                fontSize: 11,
                background: tab === "growth" ? "#111" : "#f0f0f0",
                color: tab === "growth" ? "#fff" : "#111",
                border: "none",
                borderRadius: 4,
                cursor: "pointer",
              }}
            >
              Growth Command
            </button>
            <button
              onClick={() => setTab("enrollment")}
              style={{
                padding: "8px 14px",
                fontFamily: "Helvetica",
                fontWeight: tab === "enrollment" ? 700 : 500,
                fontSize: 11,
                background: tab === "enrollment" ? "#111" : "#f0f0f0",
                color: tab === "enrollment" ? "#fff" : "#111",
                border: "none",
                borderRadius: 4,
                cursor: "pointer",
              }}
            >
              Enrollment Performance
            </button>
            <button
              onClick={() => setTab("launch")}
              style={{
                padding: "8px 14px",
                fontFamily: "Helvetica",
                fontWeight: tab === "launch" ? 700 : 500,
                fontSize: 11,
                background: tab === "launch" ? "#111" : "#f0f0f0",
                color: tab === "launch" ? "#fff" : "#111",
                border: "none",
                borderRadius: 4,
                cursor: "pointer",
              }}
            >
              Launch & Marketing
            </button>
            <button
              onClick={() => setTab("franchisee")}
              style={{
                padding: "8px 14px",
                fontFamily: "Helvetica",
                fontWeight: tab === "franchisee" ? 700 : 500,
                fontSize: 11,
                background: tab === "franchisee" ? "#111" : "#f0f0f0",
                color: tab === "franchisee" ? "#fff" : "#111",
                border: "none",
                borderRadius: 4,
                cursor: "pointer",
              }}
            >
              Franchisee Health
            </button>
            <button
              onClick={() => setTab("expansion")}
              style={{
                padding: "8px 14px",
                fontFamily: "Helvetica",
                fontWeight: tab === "expansion" ? 700 : 500,
                fontSize: 11,
                background: tab === "expansion" ? "#111" : "#f0f0f0",
                color: tab === "expansion" ? "#fff" : "#111",
                border: "none",
                borderRadius: 4,
                cursor: "pointer",
              }}
            >
              Expansion Strategy
            </button>
          </div>
        </div>

        <div style={{ minHeight: 600 }}>
          {tab === "growth" && <GrowthHubTab franchiseeData={franchiseeData} enrollmentData={enrollmentData} launchData={launchData} marketingData={marketingData} />}
          {tab === "enrollment" && <EnrollmentHubTab enrollmentData={enrollmentData} />}
          {tab === "launch" && <LaunchMarketingHubTab launchData={launchData} marketingData={marketingData} />}
          {tab === "franchisee" && <FranchiseeHealthHubTab franchiseeData={franchiseeData} />}
          {tab === "expansion" && <ExpansionStrategyHubTab franchiseeData={franchiseeData} />}
        </div>
      </div>
    </div>
  );
}
