import { useState, useMemo } from "react";
import {
  RadarChart, PolarGrid, PolarAngleAxis, Radar, ResponsiveContainer,
  ScatterChart, Scatter, XAxis, YAxis, ZAxis, CartesianGrid, Tooltip, Cell,
  ReferenceLine, ReferenceArea, LabelList
} from "recharts";

const RADAR_PAL = ["#7c6dfa", "#00d68f", "#f5a623", "#ff4f6d", "#38b6ff", "#b06dfa"];

function shortName(name) {
  if (!name) return "?";
  return name.replace(/\.pdf$/i, "").replace(/[-_]/g, " ")
    .split(" ").filter(Boolean).slice(0, 2)
    .map(w => w.slice(0, 9)).join(" ");
}

function getInitials(filename) {
  if (!filename) return "?";
  const clean = filename.replace(/\.pdf$/i, "").replace(/[-_]/g, " ");
  const words = clean.trim().split(/\s+/).filter(Boolean);
  if (words.length >= 2) return (words[0][0] + words[1][0]).toUpperCase();
  return clean.slice(0, 2).toUpperCase();
}

// ─── TOOLTIPS ─────────────────────────────────────────────────────────────────
function ScatterTooltip({ active, payload }) {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  return (
    <div className="tooltip-card">
      <div style={{
        fontWeight: 600, fontSize: 12, color: "var(--ink)",
        marginBottom: 8, paddingBottom: 7, borderBottom: "1px solid var(--line-2)",
        maxWidth: 240, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
      }}>
        {d.name.replace(/\.pdf$/i, "")} <span style={{fontFamily: "var(--mono)", color: "var(--ink-3)", fontWeight: "normal", fontSize: 10, marginLeft: 6}}>{d.match}% Match</span>
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "4px 16px", marginBottom: 3 }}>
        {[
          ["Skills", d.Skills, "var(--violet)"],
          ["Relevance", d.Relevance, "var(--rose)"],
          ["ATS", d.ATS, "var(--sky)"],
          ["Education", d.Education, "var(--amber)"],
        ].map(([k, v, c]) => (
          <div key={k} style={{ display: "flex", justifyContent: "space-between", gap: 8 }}>
            <span style={{ color: "var(--ink-2)", fontSize: 10 }}>{k}</span>
            <span style={{ fontFamily: "var(--mono)", color: c, fontSize: 10, fontWeight: 500 }}>{v}%</span>
          </div>
        ))}
      </div>
      <div style={{ display: "flex", justifyContent: "space-between", marginTop: 6, paddingTop: 6, borderTop: "1px solid var(--line-2)" }}>
        <span style={{ color: "var(--ink-3)", fontSize: 11 }}>Experience:</span>
        <span style={{ fontFamily: "var(--mono)", color: "var(--emerald)", fontSize: 11, fontWeight: 600 }}>{d.rawExp}y (Score: {d.Exp}%)</span>
      </div>
    </div>
  );
}

// ─── 1. RADAR GRID VIEW ────────────────────────────────────────────────────────
function RadarGridView({ sorted }) {
  // Top 6 candidates for the grid
  const top = sorted.slice(0, 6);
  if (!top.length) return null;

  return (
    <div style={{
      display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
      gap: 16, height: "100%", overflowY: "auto", paddingRight: 8, paddingBottom: 8,
    }}>
      {top.map((c, i) => {
        const data = ["ATS", "Skills", "Exp", "Edu", "Rel"].map(m => ({
          metric: m,
          val: m === "ATS" ? c.ats_score :
               m === "Skills" ? c.skills_score :
               m === "Exp" ? c.exp_score :
               m === "Edu" ? c.edu_score : c.relevance_score
        }));
        
        return (
          <div key={i} style={{
            background: "var(--bg-2)", border: "1px solid var(--line)",
            borderRadius: "var(--r)", padding: "12px 10px",
            display: "flex", flexDirection: "column", alignItems: "center",
          }}>
            <div style={{ fontSize: 11, fontWeight: 600, color: "var(--ink)", marginBottom: -5 }}>
              {shortName(c.filename)}
            </div>
            <div style={{ fontSize: 9, color: "var(--ink-3)", fontFamily: "var(--mono)", marginBottom: 8 }}>
              {c.final_score}% Match
            </div>
            <div style={{ width: "100%", height: 160 }}>
              <ResponsiveContainer width="100%" height="100%">
                <RadarChart data={data} margin={{ top: 10, right: 10, bottom: 10, left: 10 }}>
                  <PolarGrid stroke="var(--line-2)" />
                  <PolarAngleAxis dataKey="metric" tick={{ fill: "var(--ink-3)", fontSize: 9, fontFamily: "var(--font)" }} />
                  <Radar
                    dataKey="val" stroke={RADAR_PAL[i % RADAR_PAL.length]}
                    fill={RADAR_PAL[i % RADAR_PAL.length]} fillOpacity={0.15} strokeWidth={1.5}
                  />
                </RadarChart>
              </ResponsiveContainer>
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ─── 2. HEAT MAP VIEW ──────────────────────────────────────────────────────────
function HeatmapView({ sorted }) {
  const [sortKey, setSortKey] = useState("final_score");
  const [sortDir, setSortDir] = useState("desc");

  const onSort = (k) => {
    if (sortKey === k) setSortDir(d => d === "desc" ? "asc" : "desc");
    else { setSortKey(k); setSortDir("desc"); }
  };

  const data = useMemo(() => {
    return [...sorted].sort((a, b) => {
      const va = a[sortKey] || 0;
      const vb = b[sortKey] || 0;
      return sortDir === "desc" ? vb - va : va - vb;
    });
  }, [sorted, sortKey, sortDir]);

  // Color logic: 0 = dark red, 100 = bright green. Wait, let's use HSL.
  // Hue: 0 is Red, 120 is Green.
  const getCellBg = (val) => {
    const v = Math.max(0, Math.min(100, val));
    const h = (v / 100) * 120; 
    // Lightness drops slightly in the middle for a richer dark look, saturation high
    return `hsla(${h}, 80%, 40%, 0.3)`;
  };
  
  const getTextColor = (val) => {
    const h = (val / 100) * 120; 
    return `hsl(${h}, 90%, 75%)`; // brighter text
  };

  const H = ({ label, k }) => (
    <div onClick={() => onSort(k)} style={{
      padding: "10px", fontSize: 9, fontWeight: 700, textTransform: "uppercase",
      color: sortKey === k ? "var(--violet)" : "var(--ink-3)",
      borderBottom: "1px solid var(--line)", cursor: "pointer",
      display: "flex", alignItems: "center", gap: 4, letterSpacing: "0.05em",
    }}>
      {label} {sortKey === k && <span style={{fontSize: 8}}>{sortDir === "desc" ? "↓" : "↑"}</span>}
    </div>
  );

  return (
    <div style={{ height: "100%", overflowY: "auto", paddingRight: 8 }}>
      <div style={{ display: "grid", gridTemplateColumns: "minmax(120px, 2fr) repeat(6, 1fr)", background: "var(--bg-2)", borderRadius: "var(--r) var(--r) 0 0" }}>
        <H label="Candidate" k="filename" />
        <H label="Match" k="final_score" />
        <H label="ATS" k="ats_score" />
        <H label="Skills" k="skills_score" />
        <H label="Experience" k="exp_score" />
        <H label="Education" k="edu_score" />
        <H label="Relevance" k="relevance_score" />
      </div>
      
      <div style={{ display: "flex", flexDirection: "column", gap: 2, marginTop: 2 }}>
        {data.map((c, i) => (
          <div key={i} style={{ display: "grid", gridTemplateColumns: "minmax(120px, 2fr) repeat(6, 1fr)", gap: 2 }}>
            <div style={{ padding: "8px 10px", background: "var(--bg-2)", fontSize: 11, color: "var(--ink-2)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
              {shortName(c.filename)}
            </div>
            {[
              c.final_score, c.ats_score, c.skills_score, 
              c.exp_score, c.edu_score, c.relevance_score
            ].map((val, vi) => (
              <div key={vi} style={{
                background: getCellBg(val),
                color: getTextColor(val),
                display: "flex", alignItems: "center", justifyContent: "center",
                fontFamily: "var(--mono)", fontSize: 11, fontWeight: 500,
              }}>
                {val}%
              </div>
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── 3. SCATTER VIEW ───────────────────────────────────────────────────────────
function ScatterView({ sorted }) {
  const data = sorted.map(c => ({
    name: c.filename, // Full name for tooltip
    initials: getInitials(c.filename), // Short initials for bubble
    Skills: c.skills_score,
    Relevance: c.relevance_score,
    Exp: Math.max(10, c.exp_score), // Prevent rendering size 0 points entirely
    rawExp: c.years_experience || 0,
    ATS: c.ats_score,
    Education: c.edu_score,
    match: c.final_score,
  }));

  const getColor = (s, r) => {
    if (s >= 65 && r >= 65) return "var(--emerald)"; // Top right: strong fit
    if (s >= 65 && r < 65) return "var(--sky)";      // Skill heavy
    if (s < 65 && r >= 65) return "var(--amber)";    // Rel heavy
    return "var(--ink-3)";                           // Weak overall
  };

  return (
    <div style={{ height: "100%", position: "relative" }}>
      <ResponsiveContainer width="100%" height="100%">
        <ScatterChart margin={{ top: 25, right: 20, bottom: 20, left: -20 }}>
          <CartesianGrid strokeDasharray="2 6" stroke="var(--line)" opacity={0.3} />
          
          <XAxis type="number" dataKey="Relevance" name="Relevance" unit="%" domain={[30, 100]} tick={{ fill: "var(--ink-3)", fontSize: 10 }} axisLine={{stroke: "var(--line-2)"}} />
          <YAxis type="number" dataKey="Skills" name="Skills" unit="%" domain={[30, 100]} tick={{ fill: "var(--ink-3)", fontSize: 10 }} axisLine={{stroke: "var(--line-2)"}} tickLine={false} />
          <ZAxis type="number" dataKey="Exp" range={[150, 700]} name="Experience Score" />
          
          <Tooltip content={<ScatterTooltip />} cursor={{ strokeDasharray: '3 3', stroke: "var(--line-2)" }} />

          {/* Quadrant Highlights */}
          <ReferenceArea x1={65} x2={100} y1={65} y2={100} fill="var(--emerald)" fillOpacity={0.04} strokeOpacity={0} />

          {/* Crosshairs */}
          <ReferenceLine x={65} stroke="var(--line-2)" strokeDasharray="4 4" />
          <ReferenceLine y={65} stroke="var(--line-2)" strokeDasharray="4 4" />

          <Scatter name="Candidates" data={data}>
            {data.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={getColor(entry.Skills, entry.Relevance)} fillOpacity={0.8} stroke={getColor(entry.Skills, entry.Relevance)} strokeWidth={1} />
            ))}
            <LabelList dataKey="initials" position="center" fill="#fff" fontSize={10} fontWeight={700} fontFamily="var(--font)" style={{ pointerEvents: 'none', textShadow: "0 1px 3px rgba(0,0,0,0.8)" }} />
          </Scatter>
        </ScatterChart>
      </ResponsiveContainer>
      
      {/* Absolute positioned zone labels */}
      <div style={{ position: "absolute", top: 15, right: 35, fontSize: 10, color: "var(--emerald)", fontWeight: 700, letterSpacing: "0.05em", opacity: 0.6, pointerEvents: "none" }}>STRONG FIT</div>
      <div style={{ position: "absolute", top: 15, left: 55, fontSize: 10, color: "var(--sky)", fontWeight: 700, letterSpacing: "0.05em", opacity: 0.5, pointerEvents: "none" }}>SKILL HEAVY</div>
      <div style={{ position: "absolute", bottom: 40, right: 35, fontSize: 10, color: "var(--amber)", fontWeight: 700, letterSpacing: "0.05em", opacity: 0.5, pointerEvents: "none" }}>RELEVANCE HEAVY</div>
    </div>
  );
}


// ─── MAIN EXPORT ───────────────────────────────────────────────────────────────
export default function ResultsChart({ results }) {
  const [view, setView] = useState("radar");
  if (!results?.length) return null;

  const sorted = useMemo(
    () => [...results].sort((a, b) => b.final_score - a.final_score),
    [results]
  );

  return (
    <div style={{
      background: "var(--bg-1)", border: "1px solid var(--line)",
      borderRadius: "var(--r-lg)", overflow: "hidden", display: "flex", flexDirection: "column"
    }} className="anim-up2">

      {/* ── Header ── */}
      <div style={{
        padding: "14px 20px", borderBottom: "1px solid var(--line)",
        display: "flex", justifyContent: "space-between", alignItems: "center",
      }}>
        <div>
          <div style={{
            fontFamily: "var(--font)", fontWeight: 700,
            fontSize: 14, color: "var(--ink)", letterSpacing: "-0.3px",
          }}>Advanced Analysis</div>
          <div style={{ color: "var(--ink-3)", fontSize: 11, marginTop: 2 }}>
            {view === "radar"   ? "Candidate shapes (Top 6)" :
             view === "heatmap" ? "Matrix scan: click columns to sort" :
                                 "Outlier detection: Bubble size = Experience"}
          </div>
        </div>

        <div style={{
          display: "flex", gap: 2,
          background: "var(--bg-3)", border: "1px solid var(--line)",
          borderRadius: "var(--r-sm)", padding: 3,
        }}>
          {[
            ["radar", "Radar Profiles"],
            ["heatmap", "Matrix Heatmap"],
            ["scatter", "Scatter Plot"]
          ].map(([v, label]) => (
            <button key={v} onClick={() => setView(v)} style={{
              padding: "4px 13px", borderRadius: 5,
              fontSize: 11, fontWeight: 600, cursor: "pointer",
              border: "none", fontFamily: "var(--font)",
              transition: "all .15s",
              background: view === v ? "var(--violet)" : "transparent",
              color:      view === v ? "#fff"          : "var(--ink-3)",
              boxShadow:  view === v ? "0 2px 8px rgba(108,95,247,0.35)" : "none",
            }}>{label}</button>
          ))}
        </div>
      </div>

      {/* ── Dynamic View Area ── */}
      <div style={{ padding: "16px 16px", height: 380 }}>
        {view === "radar"   && <RadarGridView sorted={sorted} />}
        {view === "heatmap" && <HeatmapView sorted={sorted} />}
        {view === "scatter" && <ScatterView sorted={sorted} />}
      </div>
    </div>
  );
}
