import { useMemo, useState, memo } from "react";

const scoreColor = v =>
  v >= 70 ? "var(--emerald)" : v >= 45 ? "var(--amber)" : "var(--rose)";

const scoreBg = v =>
  v >= 70 ? "var(--emerald-dim)" : v >= 45 ? "var(--amber-dim)" : "var(--rose-dim)";

const SKILL_TAG_CLASSES = ["tag-violet","tag-emerald","tag-sky","tag-amber"];

function getInitials(filename) {
  if (!filename) return "?";
  const clean = filename.replace(/\.pdf$/i, "").replace(/[-_]/g, " ");
  const words = clean.trim().split(/\s+/).filter(Boolean);
  if (words.length >= 2) return (words[0][0] + words[1][0]).toUpperCase();
  return clean.slice(0, 2).toUpperCase();
}

const AVATAR_COLORS = [
  ["#6c5ff7","rgba(108,95,247,0.18)"],
  ["#00d68f","rgba(0,214,143,0.15)"],
  ["#f5a623","rgba(245,166,35,0.15)"],
  ["#38b6ff","rgba(56,182,255,0.15)"],
  ["#a855f7","rgba(168,85,247,0.15)"],
];

function Avatar({ name, index }) {
  const [fg, bg] = AVATAR_COLORS[index % AVATAR_COLORS.length];
  return (
    <div style={{
      width: 30, height: 30, borderRadius: 8, flexShrink: 0,
      background: bg, border: `1px solid ${fg}40`,
      display: "flex", alignItems: "center", justifyContent: "center",
      fontSize: 10, fontWeight: 700, color: fg, letterSpacing: "-0.02em",
      fontFamily: "var(--font)",
    }}>
      {getInitials(name)}
    </div>
  );
}

function RankBadge({ rank }) {
  const cfg =
    rank === 1 ? { bg: "linear-gradient(135deg,#f5a623,#e07820)", c: "#1a0800", shadow: "0 2px 8px rgba(245,166,35,.5)" } :
    rank === 2 ? { bg: "linear-gradient(135deg,#aaa,#777)", c: "#111" } :
    rank === 3 ? { bg: "linear-gradient(135deg,#bf7d3a,#8b5e2a)", c: "#ffe0b0" } :
    { bg: "var(--bg-4)", c: "var(--ink-3)" };
  return (
    <div style={{
      width: 22, height: 22, borderRadius: 6, flexShrink: 0,
      display: "flex", alignItems: "center", justifyContent: "center",
      fontSize: 10, fontWeight: 700, background: cfg.bg, color: cfg.c,
      boxShadow: cfg.shadow || "none", fontFamily: "var(--font)",
    }}>{rank}</div>
  );
}

function ScoreBar({ v, color }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
      <div style={{
        flex: 1, height: 4, background: "var(--bg-4)",
        borderRadius: 2, overflow: "hidden", minWidth: 36,
      }}>
        <div className="bar-fill" style={{
          height: "100%", width: `${Math.min(v, 100)}%`,
          background: color, borderRadius: 2,
        }} />
      </div>
      <span style={{
        fontFamily: "var(--mono)", fontSize: 10,
        color, minWidth: 30, textAlign: "right", fontWeight: 500,
      }}>{v}%</span>
    </div>
  );
}

function SkillTag({ skill, index }) {
  return (
    <span className={SKILL_TAG_CLASSES[index % SKILL_TAG_CLASSES.length]} style={{
      fontSize: 9, fontWeight: 600, padding: "2px 7px",
      borderRadius: 4, letterSpacing: "0.02em",
      display: "inline-flex", alignItems: "center",
    }}>
      {skill}
    </span>
  );
}

const TH = ({ children, sortKey, sortState, onSort, style }) => {
  const active = sortState?.key === sortKey;
  return (
    <th
      onClick={() => sortKey && onSort?.(sortKey)}
      style={{
        padding: "9px 14px", textAlign: "left",
        fontSize: 9, fontWeight: 700, letterSpacing: "0.09em",
        color: active ? "var(--violet)" : "var(--ink-3)",
        textTransform: "uppercase", whiteSpace: "nowrap",
        background: "var(--bg-2)", borderBottom: "1px solid var(--line)",
        cursor: sortKey ? "pointer" : "default",
        userSelect: "none",
        transition: "color .15s",
        ...style,
      }}
    >
      <span style={{ display: "flex", alignItems: "center", gap: 4 }}>
        {children}
        {sortKey && (
          <span style={{ opacity: active ? 1 : 0.3, fontSize: 8 }}>
            {active ? (sortState.dir === "asc" ? "↑" : "↓") : "↕"}
          </span>
        )}
      </span>
    </th>
  );
};

const SORT_DEFAULTS = { key: "final_score", dir: "desc" };

function ExpandedRow({ r, colSpan }) {
  const missing = r.missing_required_skills || [];
  return (
    <tr style={{ background: "var(--bg-2)", borderBottom: "1px solid var(--line)" }}>
      <td colSpan={colSpan} style={{ padding: "12px 20px 16px 64px" }}>
        <div style={{ display: "flex", gap: 32, flexWrap: "wrap" }}>
          {r.experience && (
            <div>
              <div style={{ fontSize: 9, color: "var(--ink-3)", textTransform: "uppercase", letterSpacing: "0.09em", marginBottom: 5, fontWeight: 700 }}>
                Experience
              </div>
              <div style={{ fontSize: 12, color: "var(--ink-2)", fontFamily: "var(--mono)" }}>{r.experience}</div>
            </div>
          )}
          {r.degree && r.degree !== "None" && (
            <div>
              <div style={{ fontSize: 9, color: "var(--ink-3)", textTransform: "uppercase", letterSpacing: "0.09em", marginBottom: 5, fontWeight: 700 }}>
                Education
              </div>
              <div style={{ fontSize: 12, color: "var(--ink-2)", fontFamily: "var(--mono)" }}>{r.degree}</div>
            </div>
          )}
          {missing.length > 0 && (
            <div>
              <div style={{ fontSize: 9, color: "var(--rose)", textTransform: "uppercase", letterSpacing: "0.09em", marginBottom: 5, fontWeight: 700 }}>
                Missing Skills
              </div>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 3 }}>
                {missing.slice(0, 10).map((sk, i) => (
                  <span key={i} style={{
                    background: "var(--rose-dim)", color: "var(--rose)",
                    border: "1px solid rgba(255,79,109,0.25)",
                    fontSize: 9, fontWeight: 600, padding: "2px 6px",
                    borderRadius: 4, letterSpacing: "0.02em",
                  }}>{sk}</span>
                ))}
              </div>
            </div>
          )}
          {r.matched_skills?.length > 0 && (
            <div>
              <div style={{ fontSize: 9, color: "var(--ink-3)", textTransform: "uppercase", letterSpacing: "0.09em", marginBottom: 5, fontWeight: 700 }}>
                All Matched Skills
              </div>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 3 }}>
                {r.matched_skills.map((sk, i) => (
                  <SkillTag key={i} skill={sk} index={i} />
                ))}
              </div>
            </div>
          )}
        </div>
      </td>
    </tr>
  );
}

const ResultsTable = memo(function ResultsTable({ results }) {
  const [expanded, setExpanded] = useState({});
  const [sort, setSort] = useState(SORT_DEFAULTS);

  const toggleRow = (i) => setExpanded(p => ({ ...p, [i]: !p[i] }));

  const onSort = (key) => {
    setSort(prev =>
      prev.key === key
        ? { key, dir: prev.dir === "desc" ? "asc" : "desc" }
        : { key, dir: "desc" }
    );
  };

  const sorted = useMemo(() => {
    return [...results].sort((a, b) => {
      const va = a[sort.key] ?? 0;
      const vb = b[sort.key] ?? 0;
      return sort.dir === "desc" ? vb - va : va - vb;
    });
  }, [results, sort]);

  const COL_COUNT = 9;

  return (
    <div style={{
      background: "var(--bg-1)", border: "1px solid var(--line)",
      borderRadius: "var(--r-lg)", overflow: "hidden",
    }} className="anim-up">
      {/* Header */}
      <div style={{
        padding: "14px 20px", borderBottom: "1px solid var(--line)",
        display: "flex", justifyContent: "space-between", alignItems: "center",
        background: "var(--bg-1)",
      }}>
        <div>
          <div style={{
            fontFamily: "var(--font)", fontWeight: 700, fontSize: 14,
            color: "var(--ink)", letterSpacing: "-0.3px",
          }}>Candidate Rankings</div>
          <div style={{ color: "var(--ink-3)", fontSize: 11, marginTop: 2 }}>
            {sorted.length} candidates · click a row to expand details
          </div>
        </div>
        <div style={{
          fontSize: 10, color: "var(--ink-3)", fontFamily: "var(--mono)",
          background: "var(--bg-3)", border: "1px solid var(--line)",
          borderRadius: "var(--r-sm)", padding: "4px 10px",
        }}>
          Sorted by {sort.key.replace(/_/g, " ")} {sort.dir === "desc" ? "↓" : "↑"}
        </div>
      </div>

      <div style={{ overflowX: "auto" }}>
        <table style={{ width: "100%", minWidth: 900, borderCollapse: "collapse" }}>
          <thead>
            <tr>
              <TH style={{ width: 44 }}>#</TH>
              <TH style={{ minWidth: 200 }}>Candidate</TH>
              <TH sortKey="final_score"  sortState={sort} onSort={onSort} style={{ minWidth: 110 }}>Match</TH>
              <TH sortKey="ats_score"    sortState={sort} onSort={onSort} style={{ minWidth: 100 }}>ATS</TH>
              <TH sortKey="skills_score" sortState={sort} onSort={onSort} style={{ minWidth: 100 }}>Skills</TH>
              <TH sortKey="exp_score"    sortState={sort} onSort={onSort} style={{ minWidth: 100 }}>Exp</TH>
              <TH sortKey="edu_score"    sortState={sort} onSort={onSort} style={{ minWidth: 100 }}>Education</TH>
              <TH sortKey="relevance_score" sortState={sort} onSort={onSort} style={{ minWidth: 100 }}>Relevance</TH>
              <TH style={{ minWidth: 180 }}>Matched Skills</TH>
            </tr>
          </thead>
          <tbody>
            {sorted.map((r, i) => {
              const mc = scoreColor(r.final_score);
              const isExp = expanded[i];
              const topSkills = r.matched_skills?.slice(0, 3) || [];
              const extraCount = (r.matched_skills?.length || 0) - 3;

              return (
                <>
                  <tr
                    key={i}
                    className="trow"
                    onClick={() => toggleRow(i)}
                    style={{
                      borderBottom: isExp ? "none" : "1px solid var(--line)",
                      cursor: "pointer",
                      background: isExp ? "var(--bg-2)" : "transparent",
                    }}
                  >
                    {/* Rank */}
                    <td style={{ padding: "13px 14px" }}>
                      <RankBadge rank={i + 1} />
                    </td>

                    {/* Candidate */}
                    <td style={{ padding: "13px 14px" }}>
                      <div style={{ display: "flex", alignItems: "center", gap: 9 }}>
                        <Avatar name={r.filename} index={i} />
                        <div>
                          <div style={{
                            fontWeight: 500, fontSize: 12, color: "var(--ink)",
                            maxWidth: 180, overflow: "hidden",
                            textOverflow: "ellipsis", whiteSpace: "nowrap",
                          }}>
                            {r.filename?.replace(/\.pdf$/i, "") || `Candidate ${i + 1}`}
                          </div>
                          <div style={{
                            fontSize: 10, color: "var(--ink-3)",
                            marginTop: 1, fontFamily: "var(--mono)",
                          }}>
                            {r.years_experience != null ? `${r.years_experience}y exp` : ""}
                            {r.degree && r.degree !== "None" ? ` · ${r.degree}` : ""}
                          </div>
                        </div>
                      </div>
                    </td>

                    {/* Match score */}
                    <td style={{ padding: "13px 14px" }}>
                      <div style={{
                        display: "inline-flex", alignItems: "baseline", gap: 2,
                        background: scoreBg(r.final_score),
                        border: `1px solid ${mc}30`,
                        borderRadius: 6, padding: "3px 8px",
                      }}>
                        <span style={{
                          fontFamily: "var(--mono)", fontSize: 18,
                          fontWeight: 500, color: mc, letterSpacing: "-0.5px", lineHeight: 1,
                        }}>{r.final_score}</span>
                        <span style={{ color: mc, fontSize: 10, opacity: 0.8 }}>%</span>
                      </div>
                    </td>

                    {/* Sub-scores */}
                    <td style={{ padding: "13px 14px", minWidth: 100 }}><ScoreBar v={r.ats_score}       color="var(--sky)" /></td>
                    <td style={{ padding: "13px 14px", minWidth: 100 }}><ScoreBar v={r.skills_score}    color="var(--violet)" /></td>
                    <td style={{ padding: "13px 14px", minWidth: 100 }}><ScoreBar v={r.exp_score}       color="var(--emerald)" /></td>
                    <td style={{ padding: "13px 14px", minWidth: 100 }}><ScoreBar v={r.edu_score}       color="var(--amber)" /></td>
                    <td style={{ padding: "13px 14px", minWidth: 100 }}><ScoreBar v={r.relevance_score} color="var(--rose)" /></td>

                    {/* Skills */}
                    <td style={{ padding: "13px 14px" }}>
                      <div style={{ display: "flex", flexWrap: "wrap", gap: 3, alignItems: "center" }}>
                        {topSkills.map((sk, si) => <SkillTag key={si} skill={sk} index={si} />)}
                        {extraCount > 0 && (
                          <span style={{
                            background: "var(--bg-4)", color: "var(--ink-3)",
                            fontSize: 9, fontWeight: 600, padding: "2px 6px",
                            borderRadius: 4, border: "1px solid var(--line-2)",
                          }}>+{extraCount}</span>
                        )}
                      </div>
                    </td>
                  </tr>

                  {isExp && (
                    <ExpandedRow key={`exp-${i}`} r={r} colSpan={COL_COUNT} />
                  )}
                </>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
});

export default ResultsTable;
