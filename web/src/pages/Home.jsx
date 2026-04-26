import { useState, useCallback } from "react";
import Sidebar from "../components/Sidebar";
import ResultsChart from "../components/ResultsChart";
import ResultsTable from "../components/ResultsTable";
import { scanResumes } from "../api";

// ─── KPI Card ──────────────────────────────────────────────────────────────
function KPI({ label, value, unit, sub, color, animClass }) {
  return (
    <div className={animClass} style={{
      background: "var(--bg-1)", border: "1px solid var(--line)",
      borderRadius: "var(--r-lg)", padding: "18px 20px",
      flex: 1, position: "relative", overflow: "hidden",
      transition: "border-color .2s",
    }}
      onMouseEnter={e => e.currentTarget.style.borderColor = "var(--line-2)"}
      onMouseLeave={e => e.currentTarget.style.borderColor = "var(--line)"}
    >
      {/* top accent line */}
      <div style={{
        position: "absolute", top: 0, left: 0, right: 0, height: 2,
        background: color, borderRadius: "var(--r-lg) var(--r-lg) 0 0",
        opacity: 0.9,
      }} />

      <div style={{
        fontSize: 9, fontWeight: 700, letterSpacing: "0.12em",
        color: "var(--ink-3)", textTransform: "uppercase",
        marginBottom: 12,
      }}>{label}</div>

      <div style={{ display: "flex", alignItems: "baseline", gap: 3 }}>
        <span style={{
          fontFamily: "var(--mono)", fontSize: 28, fontWeight: 400,
          color, letterSpacing: "-1.5px", lineHeight: 1,
        }}>{value}</span>
        {unit && (
          <span style={{
            fontFamily: "var(--mono)", fontSize: 13,
            color: "var(--ink-3)", opacity: 0.8,
          }}>{unit}</span>
        )}
      </div>

      {sub && (
        <div style={{ fontSize: 10, color: "var(--ink-4)", marginTop: 6, fontWeight: 400 }}>
          {sub}
        </div>
      )}
    </div>
  );
}

// ─── Skeleton KPI ─────────────────────────────────────────────────────────
function KPISkeleton() {
  return (
    <div style={{
      background: "var(--bg-1)", border: "1px solid var(--line)",
      borderRadius: "var(--r-lg)", padding: "18px 20px", flex: 1,
    }}>
      <div className="skeleton" style={{ height: 9, width: "60%", marginBottom: 14 }} />
      <div className="skeleton" style={{ height: 28, width: "40%", marginBottom: 8 }} />
      <div className="skeleton" style={{ height: 9, width: "50%" }} />
    </div>
  );
}

// ─── Skeleton Table ───────────────────────────────────────────────────────
function TableSkeleton() {
  return (
    <div style={{
      background: "var(--bg-1)", border: "1px solid var(--line)",
      borderRadius: "var(--r-lg)", overflow: "hidden",
    }}>
      <div style={{ padding: "14px 20px", borderBottom: "1px solid var(--line)" }}>
        <div className="skeleton" style={{ height: 14, width: 180, marginBottom: 8 }} />
        <div className="skeleton" style={{ height: 10, width: 260 }} />
      </div>
      {[...Array(5)].map((_, i) => (
        <div key={i} style={{
          padding: "14px 20px", borderBottom: "1px solid var(--line)",
          display: "flex", alignItems: "center", gap: 14,
        }}>
          <div className="skeleton" style={{ width: 22, height: 22, borderRadius: 6, flexShrink: 0 }} />
          <div className="skeleton" style={{ width: 30, height: 30, borderRadius: 8, flexShrink: 0 }} />
          <div style={{ flex: 1 }}>
            <div className="skeleton" style={{ height: 12, width: "30%", marginBottom: 6 }} />
            <div className="skeleton" style={{ height: 10, width: "20%" }} />
          </div>
          <div className="skeleton" style={{ height: 24, width: 52, borderRadius: 6 }} />
          {[1,2,3,4,5].map(j => (
            <div key={j} style={{ flex: 1 }}>
              <div className="skeleton" style={{ height: 4, borderRadius: 2 }} />
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}

// ─── Error Banner ─────────────────────────────────────────────────────────
function ErrorBanner({ msg, onClose }) {
  if (!msg) return null;
  return (
    <div style={{
      background: "var(--rose-dim)",
      border: "1px solid rgba(255,79,109,.25)",
      borderRadius: "var(--r)", padding: "10px 14px", marginBottom: 20,
      display: "flex", justifyContent: "space-between", alignItems: "center",
      animation: "fadeIn .25s ease both",
    }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--rose)" strokeWidth="2" strokeLinecap="round">
          <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
        </svg>
        <span style={{ color: "var(--rose)", fontSize: 12 }}>{msg}</span>
      </div>
      <button onClick={onClose} style={{
        color: "var(--rose)", background: "none", border: "none",
        cursor: "pointer", fontSize: 18, lineHeight: 1,
        display: "flex", alignItems: "center",
        opacity: 0.7, transition: "opacity .1s",
      }}
        onMouseEnter={e => e.currentTarget.style.opacity = 1}
        onMouseLeave={e => e.currentTarget.style.opacity = 0.7}
      >×</button>
    </div>
  );
}

// ─── Welcome State ────────────────────────────────────────────────────────
function WelcomeScreen() {
  return (
    <div style={{
      flex: 1, display: "flex", flexDirection: "column",
      alignItems: "center", justifyContent: "center",
      padding: "40px 60px", gap: 48, width: "100%",
    }}>
      {/* Hero */}
      <div style={{ textAlign: "center", maxWidth: 540 }}>
        <div style={{
          display: "inline-flex", alignItems: "center", gap: 8,
          background: "var(--violet-dim)",
          border: "1px solid var(--violet-mid)",
          borderRadius: 999, padding: "5px 14px", marginBottom: 28,
        }}>
          <div className="pulse-dot" style={{
            width: 6, height: 6, borderRadius: "50%",
            background: "var(--violet)",
          }} />
          <span style={{
            fontSize: 10, fontWeight: 700, color: "var(--violet)",
            letterSpacing: "0.1em",
          }}>RESUME SCREENING PLATFORM</span>
        </div>

        <h1 style={{
          fontFamily: "var(--font)", fontSize: 44, fontWeight: 800,
          letterSpacing: "-2px", color: "var(--ink)", lineHeight: 1.08, marginBottom: 18,
        }}>
          Rank candidates.<br />
          <span style={{
            background: "linear-gradient(135deg,#6c5ff7,#a855f7)",
            WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent",
            backgroundClip: "text",
          }}>Not guesses.</span>
        </h1>

        <p style={{
          color: "var(--ink-2)", fontSize: 14, lineHeight: 1.8,
          maxWidth: 420, margin: "0 auto", fontWeight: 400,
        }}>
          NLP-powered screening that scores resumes across skills, experience,
          education, and semantic relevance — fully explainable, no black box.
        </p>
      </div>

      {/* Steps */}
      <div style={{
        display: "grid", gridTemplateColumns: "repeat(3,1fr)",
        gap: 14, width: "100%", maxWidth: 780,
      }}>
        {[
          {
            n: "01",
            icon: "📋",
            t: "Define the role",
            d: "Paste your job description. Skills and context are extracted automatically.",
          },
          {
            n: "02",
            icon: "📑",
            t: "Upload resumes",
            d: "Drop PDF CVs in bulk. Text extraction handles complex layouts.",
          },
          {
            n: "03",
            icon: "🏆",
            t: "Get ranked results",
            d: "Explainable score breakdown per candidate. Export to CSV instantly.",
          },
        ].map(({ n, icon, t, d }) => (
          <div key={n} style={{
            background: "var(--bg-1)", border: "1px solid var(--line)",
            borderRadius: "var(--r)", padding: "18px 16px",
            transition: "border-color .2s, transform .2s",
          }}
            onMouseEnter={e => {
              e.currentTarget.style.borderColor = "var(--line-2)";
              e.currentTarget.style.transform = "translateY(-2px)";
            }}
            onMouseLeave={e => {
              e.currentTarget.style.borderColor = "var(--line)";
              e.currentTarget.style.transform = "none";
            }}
          >
            <div style={{ fontSize: 18, marginBottom: 10 }}>{icon}</div>
            <div style={{
              fontFamily: "var(--mono)", fontSize: 9,
              color: "var(--violet)", marginBottom: 6, opacity: 0.7,
            }}>{n}</div>
            <div style={{
              fontWeight: 600, fontSize: 13, color: "var(--ink)", marginBottom: 6,
            }}>{t}</div>
            <div style={{
              fontSize: 11, color: "var(--ink-3)", lineHeight: 1.7, fontWeight: 400,
            }}>{d}</div>
          </div>
        ))}
      </div>

      {/* Stat pills */}
      <div style={{ display: "flex", gap: 10, flexWrap: "wrap", justifyContent: "center" }}>
        {[
          { label: "Skills Detected", value: "900+", color: "var(--violet)" },
          { label: "Scoring Dimensions", value: "4", color: "var(--emerald)" },
          { label: "Export Formats", value: "CSV", color: "var(--sky)" },
        ].map(({ label, value, color }) => (
          <div key={label} style={{
            background: "var(--bg-1)", border: "1px solid var(--line)",
            borderRadius: 999, padding: "6px 16px",
            display: "flex", alignItems: "center", gap: 8,
          }}>
            <span style={{ fontFamily: "var(--mono)", fontSize: 13, fontWeight: 600, color }}>{value}</span>
            <span style={{ fontSize: 11, color: "var(--ink-3)" }}>{label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Main Home ────────────────────────────────────────────────────────────
export default function Home() {
  const [jd, setJd]           = useState("");
  const [files, setFiles]     = useState([]);
  const [prio, setPrio]       = useState({
    skills: "Medium", experience: "Medium",
    education: "Medium", relevance: "Medium",
  });
  const [topN, setTopN]       = useState(10);
  const [results, setResults] = useState(null);
  const [meta, setMeta]       = useState(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr]         = useState(null);

  const analyze = useCallback(async () => {
    setErr(null);
    if (!jd.trim())      { setErr("Please add a job description."); return; }
    if (!files.length)   { setErr("Please upload at least one resume."); return; }
    setLoading(true);
    try {
      const res = await scanResumes({ jobDescription: jd, files, priorities: prio });
      if (res?.results) {
        setResults(res.results);
        setMeta({
          total: res.total_candidates,
          skills: res.jd_skills_count,
          ms: res.processing_time_ms,
        });
      } else {
        throw new Error("bad response");
      }
    } catch (e) {
      setErr(e?.detail || e?.message || "Analysis failed. Check connection and file formats.");
    } finally {
      setLoading(false);
    }
  }, [jd, files, prio]);

  const exportCSV = useCallback(() => {
    if (!results) return;
    const h = ["Rank","File","Match%","ATS%","Skills%","Exp%","Edu%","Relevance%","Matched Skills","Experience","Degree"];
    const esc = v => { const s = String(v ?? ""); return s.includes(",") || s.includes('"') ? `"${s.replace(/"/g, '""')}"` : s; };
    const rows = results.map((r, i) => [
      i + 1, r.filename, r.final_score, r.ats_score,
      r.skills_score, r.exp_score, r.edu_score, r.relevance_score,
      r.matched_skills?.join("|"), r.experience, r.degree ?? "",
    ].map(esc).join(","));
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([[h.join(","), ...rows].join("\n")], { type: "text/csv" }));
    a.download = `TalentMatch_Report_${new Date().toISOString().slice(0,10)}.csv`;
    a.click();
  }, [results]);

  const top    = results?.slice(0, topN) ?? [];
  const scores = results?.map(r => r.final_score) ?? [];
  const avg    = arr => arr.length ? (arr.reduce((x, y) => x + y, 0) / arr.length).toFixed(1) : "—";
  const topScore = scores.length ? Math.max(...scores) : "—";

  return (
    <div style={{
      display: "flex", width: "100%", height: "100%",
      overflow: "hidden", background: "var(--bg)",
    }}>
      <Sidebar
        jobDescription={jd} setJobDescription={setJd}
        files={files} setFiles={setFiles}
        priorities={prio} setPriorities={setPrio}
        topN={topN} setTopN={setTopN}
        onAnalyze={analyze} loading={loading}
      />

      <main style={{
        flex: 1, minWidth: 0, overflowY: "auto",
        padding: "28px 36px",
        display: "flex", flexDirection: "column",
      }}>
        <ErrorBanner msg={err} onClose={() => setErr(null)} />

        {/* Loading skeleton */}
        {loading && (
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            {/* Topbar skeleton */}
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 4 }}>
              <div>
                <div className="skeleton" style={{ height: 20, width: 160, marginBottom: 8 }} />
                <div className="skeleton" style={{ height: 11, width: 260 }} />
              </div>
              <div style={{ display: "flex", gap: 8 }}>
                <div className="skeleton" style={{ height: 30, width: 70, borderRadius: "var(--r-sm)" }} />
                <div className="skeleton" style={{ height: 30, width: 100, borderRadius: "var(--r-sm)" }} />
              </div>
            </div>
            {/* KPI skeletons */}
            <div style={{ display: "flex", gap: 12 }}>
              <KPISkeleton /><KPISkeleton /><KPISkeleton /><KPISkeleton />
            </div>
            {/* Table skeleton */}
            <TableSkeleton />
          </div>
        )}

        {/* Welcome state */}
        {!loading && !results && <WelcomeScreen />}

        {/* Results */}
        {!loading && results && (
          <>
            {/* ── Page header ── */}
            <div className="anim-up" style={{
              display: "flex", justifyContent: "space-between",
              alignItems: "flex-start", marginBottom: 20,
            }}>
              <div>
                <h1 style={{
                  fontFamily: "var(--font)", fontSize: 22, fontWeight: 800,
                  letterSpacing: "-0.6px", color: "var(--ink)", lineHeight: 1,
                }}>Analysis Report</h1>
                <div style={{
                  color: "var(--ink-3)", fontSize: 11, marginTop: 5,
                  fontFamily: "var(--mono)", display: "flex", gap: 12,
                }}>
                  <span>{meta?.total} candidates</span>
                  <span style={{ color: "var(--line-3)" }}>·</span>
                  <span>{meta?.skills} JD skills</span>
                  <span style={{ color: "var(--line-3)" }}>·</span>
                  <span>{meta?.ms}ms</span>
                </div>
              </div>

              <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                <button
                  onClick={() => { setResults(null); setMeta(null); }}
                  style={{
                    padding: "8px 16px", borderRadius: "var(--r-sm)",
                    border: "1px solid var(--line-2)",
                    background: "transparent", color: "var(--ink-2)",
                    fontSize: 12, cursor: "pointer", fontFamily: "var(--font)",
                    fontWeight: 500, transition: "all .15s",
                  }}
                  onMouseEnter={e => { e.currentTarget.style.borderColor = "var(--line-3)"; e.currentTarget.style.color = "var(--ink)"; }}
                  onMouseLeave={e => { e.currentTarget.style.borderColor = "var(--line-2)"; e.currentTarget.style.color = "var(--ink-2)"; }}
                >
                  ← New Analysis
                </button>
                <button
                  onClick={exportCSV}
                  style={{
                    padding: "8px 16px", borderRadius: "var(--r-sm)",
                    border: "1px solid var(--violet-mid)",
                    background: "var(--violet-dim)", color: "var(--violet)",
                    fontSize: 12, fontWeight: 600, cursor: "pointer",
                    fontFamily: "var(--font)", transition: "all .15s",
                    display: "flex", alignItems: "center", gap: 6,
                  }}
                  onMouseEnter={e => e.currentTarget.style.background = "rgba(108,95,247,0.2)"}
                  onMouseLeave={e => e.currentTarget.style.background = "var(--violet-dim)"}
                >
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                    <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M7 10l5 5 5-5M12 15V3"/>
                  </svg>
                  Export CSV
                </button>
              </div>
            </div>

            {/* ── KPIs ── */}
            <div style={{ display: "flex", gap: 12, marginBottom: 20 }}>
              <KPI
                label="Top Match"
                value={topScore}
                unit="%"
                sub="Highest global score"
                color="var(--emerald)"
                animClass="anim-up"
              />
              <KPI
                label="Avg Match"
                value={avg(scores)}
                unit="%"
                sub={`Cohort of ${results.length}`}
                color="var(--violet)"
                animClass="anim-up1"
              />
              <KPI
                label="Candidates"
                value={results.length}
                sub="Total processed"
                color="var(--sky)"
                animClass="anim-up2"
              />
              <KPI
                label="JD Skills"
                value={meta?.skills ?? "—"}
                sub="Extracted from JD"
                color="var(--amber)"
                animClass="anim-up3"
              />
            </div>

            {/* ── Table + Chart ── */}
            <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
              <ResultsTable results={top} />
              <ResultsChart results={top} priorities={prio} />
            </div>
          </>
        )}
      </main>
    </div>
  );
}
