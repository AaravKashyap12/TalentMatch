import { useRef, useState, useCallback } from "react";

const OPTS = ["Ignore", "Low", "Medium", "High", "Critical"];
const P_COLOR = {
  Ignore: "var(--ink-3)",
  Low: "var(--ink-2)",
  Medium: "var(--sky)",
  High: "var(--emerald)",
  Critical: "var(--violet)",
};
const P_BG = {
  Ignore: "transparent",
  Low: "transparent",
  Medium: "var(--sky-dim)",
  High: "var(--emerald-dim)",
  Critical: "var(--violet-dim)",
};

const WEIGHT_ICONS = {
  skills:     "⬡",
  experience: "◷",
  education:  "◈",
  relevance:  "◉",
};

const SKILL_TAG_COLORS = ["tag-violet","tag-emerald","tag-sky","tag-amber"];

function SectionLabel({ children }) {
  return (
    <div style={{
      fontSize: 9, fontWeight: 700, letterSpacing: "0.12em",
      color: "var(--ink-4)", textTransform: "uppercase",
      marginBottom: 8, fontFamily: "var(--font)", paddingLeft: 2,
    }}>{children}</div>
  );
}

function WeightRow({ label, k, value, onChange }) {
  return (
    <div style={{
      display: "flex", alignItems: "center", justifyContent: "space-between",
      padding: "6px 10px", borderRadius: "var(--r-sm)",
      border: "1px solid var(--line)", background: "var(--bg-3)",
      transition: "border-color .15s",
    }}
      onMouseEnter={e => e.currentTarget.style.borderColor = "var(--line-2)"}
      onMouseLeave={e => e.currentTarget.style.borderColor = "var(--line)"}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 7 }}>
        <span style={{ fontSize: 11, color: "var(--ink-3)", lineHeight: 1 }}>{WEIGHT_ICONS[k]}</span>
        <span style={{ fontSize: 12, color: "var(--ink-2)", fontWeight: 400 }}>{label}</span>
      </div>
      <select
        value={value}
        onChange={e => onChange(k, e.target.value)}
        style={{
          background: P_BG[value],
          border: `1px solid ${value === "Ignore" ? "var(--line)" : "transparent"}`,
          borderRadius: "var(--r-sm)",
          color: P_COLOR[value],
          fontSize: 11, fontWeight: 600,
          padding: "2px 24px 2px 7px",
          fontFamily: "var(--font)",
          outline: "none",
          width: 86,
          transition: "all .15s",
        }}
      >
        {OPTS.map(o => <option key={o} value={o} style={{ color: "var(--ink)", background: "var(--bg-3)" }}>{o}</option>)}
      </select>
    </div>
  );
}

function FileChip({ file, onRemove, index }) {
  const ext = file.name.split(".").pop().toUpperCase();
  const name = file.name.replace(/\.[^/.]+$/, "");
  const colorClass = SKILL_TAG_COLORS[index % SKILL_TAG_COLORS.length];
  return (
    <div style={{
      display: "flex", alignItems: "center", gap: 7,
      background: "var(--bg-3)", borderRadius: "var(--r-sm)",
      padding: "5px 8px", border: "1px solid var(--line)",
      transition: "border-color .12s",
    }}
      onMouseEnter={e => e.currentTarget.style.borderColor = "var(--line-2)"}
      onMouseLeave={e => e.currentTarget.style.borderColor = "var(--line)"}
    >
      <span className={colorClass} style={{
        fontSize: 8, fontWeight: 700, padding: "1px 5px",
        borderRadius: 3, flexShrink: 0, letterSpacing: "0.05em",
      }}>{ext}</span>
      <span style={{
        fontSize: 11, color: "var(--ink-2)", overflow: "hidden",
        textOverflow: "ellipsis", whiteSpace: "nowrap", flex: 1, maxWidth: 150,
      }}>{name}</span>
      <button onClick={() => onRemove(file.name)} style={{
        color: "var(--ink-3)", background: "none", border: "none",
        cursor: "pointer", fontSize: 14, lineHeight: 1, flexShrink: 0,
        transition: "color .1s", padding: "0 2px",
        display: "flex", alignItems: "center",
      }}
        onMouseEnter={e => e.currentTarget.style.color = "var(--rose)"}
        onMouseLeave={e => e.currentTarget.style.color = "var(--ink-3)"}
      >×</button>
    </div>
  );
}

export default function Sidebar({
  jobDescription, setJobDescription,
  files, setFiles,
  priorities, setPriorities,
  topN, setTopN,
  onAnalyze, loading,
}) {
  const inputRef = useRef(null);
  const dropRef  = useRef(null);
  const [dragging, setDragging] = useState(false);
  const [jdFocused, setJdFocused] = useState(false);

  const addFiles = useCallback((newFiles) => {
    const arr = Array.from(newFiles).filter(f => f.type === "application/pdf");
    setFiles(prev => {
      const names = new Set(prev.map(f => f.name));
      return [...prev, ...arr.filter(f => !names.has(f.name))];
    });
  }, [setFiles]);

  const onDrop = useCallback((e) => {
    e.preventDefault();
    setDragging(false);
    addFiles(e.dataTransfer.files);
  }, [addFiles]);

  const onDragOver = (e) => { e.preventDefault(); setDragging(true); };
  const onDragLeave = () => setDragging(false);

  const ready = !loading && jobDescription.trim().length >= 20 && files.length > 0;
  const jdLen = jobDescription.trim().length;
  const jdOk  = jdLen >= 20;

  return (
    <aside style={{
      width: 280, minWidth: 280,
      background: "var(--bg-1)",
      borderRight: "1px solid var(--line)",
      display: "flex", flexDirection: "column",
      height: "100vh", position: "relative", zIndex: 10,
    }}>
      {/* ── Logo ── */}
      <div style={{
        padding: "16px 18px", borderBottom: "1px solid var(--line)",
        display: "flex", alignItems: "center", gap: 10, flexShrink: 0,
      }}>
        <img
          src="/logo.png"
          alt="TalentMatch Logo"
          style={{
            width: 32, height: 32, borderRadius: 8,
            aspectRatio: "1 / 1", objectFit: "contain",
            flexShrink: 0,
            filter: "drop-shadow(0 4px 12px rgba(108,95,247,0.3))",
          }}
        />
        <div>
          <div style={{
            fontFamily: "var(--font)", fontWeight: 700, fontSize: 14,
            color: "var(--ink)", letterSpacing: "-0.3px", lineHeight: 1,
          }}>TalentMatch</div>
          <div style={{ fontSize: 9, color: "var(--ink-3)", marginTop: 2, letterSpacing: "0.1em" }}>
            RESUME INTELLIGENCE
          </div>
        </div>
        <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 5 }}>
          <div className="pulse-dot" style={{
            width: 6, height: 6, borderRadius: "50%",
            background: "var(--emerald)",
          }} />
          <span style={{ fontSize: 9, color: "var(--emerald)", fontWeight: 600, letterSpacing: "0.06em" }}>LIVE</span>
        </div>
      </div>

      {/* ── Scrollable body ── */}
      <div style={{ flex: 1, overflowY: "auto", padding: "18px 18px", display: "flex", flexDirection: "column", gap: 20 }}>

        {/* JD */}
        <div>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
            <SectionLabel>Job Description</SectionLabel>
            {jdLen > 0 && (
              <span style={{
                fontSize: 9, fontFamily: "var(--mono)",
                color: jdOk ? "var(--emerald)" : "var(--rose)",
                fontWeight: 500,
              }}>{jdLen} / 10000</span>
            )}
          </div>
          <div style={{ position: "relative" }}>
            <textarea
              value={jobDescription}
              onChange={e => setJobDescription(e.target.value)}
              placeholder="Paste job description here…"
              rows={7}
              onFocus={() => setJdFocused(true)}
              onBlur={() => setJdFocused(false)}
              style={{
                width: "100%",
                background: "var(--bg-3)",
                border: `1px solid ${jdFocused ? "var(--violet)" : "var(--line)"}`,
                borderRadius: "var(--r)",
                padding: "10px 12px",
                color: "var(--ink)",
                fontSize: 12,
                outline: "none",
                fontFamily: "var(--font)",
                resize: "vertical",
                lineHeight: 1.65,
                transition: "border-color .15s",
                minHeight: 120,
              }}
            />
            {jdLen > 0 && !jdOk && (
              <div style={{ fontSize: 10, color: "var(--rose)", marginTop: 4 }}>
                Need at least 20 characters
              </div>
            )}
          </div>
        </div>

        {/* Upload */}
        <div>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
            <SectionLabel>Resumes</SectionLabel>
            {files.length > 0 && (
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <span style={{
                  background: "var(--violet-dim)", color: "var(--violet)",
                  fontSize: 9, fontWeight: 700, padding: "2px 7px",
                  borderRadius: 999, letterSpacing: "0.06em", border: "1px solid var(--violet-mid)",
                }}>{files.length} PDF{files.length !== 1 ? "s" : ""}</span>
                <button onClick={() => setFiles([])} style={{
                  color: "var(--ink-3)", fontSize: 10, background: "none",
                  border: "none", cursor: "pointer", fontFamily: "var(--font)",
                  transition: "color .1s",
                }}
                  onMouseEnter={e => e.currentTarget.style.color = "var(--rose)"}
                  onMouseLeave={e => e.currentTarget.style.color = "var(--ink-3)"}
                >Clear all</button>
              </div>
            )}
          </div>

          <input ref={inputRef} id="fu" type="file" accept="application/pdf"
            multiple onChange={e => { addFiles(e.target.files); e.target.value = ""; }}
            style={{ display: "none" }} />

          <label htmlFor="fu"
            ref={dropRef}
            className={dragging ? "drop-active" : ""}
            onDragOver={onDragOver}
            onDragLeave={onDragLeave}
            onDrop={onDrop}
            style={{
              display: "flex", flexDirection: "column", alignItems: "center",
              gap: 8, border: "1.5px dashed var(--line-2)",
              borderRadius: "var(--r)", padding: "18px 12px",
              cursor: "pointer", background: "var(--bg-2)",
              transition: "all .15s", textAlign: "center",
            }}
            onMouseEnter={e => { e.currentTarget.style.borderColor = "var(--violet)"; e.currentTarget.style.background = "var(--violet-dim)"; }}
            onMouseLeave={e => { if (!dragging) { e.currentTarget.style.borderColor = "var(--line-2)"; e.currentTarget.style.background = "var(--bg-2)"; } }}
          >
            <div style={{
              width: 32, height: 32, borderRadius: "var(--r-sm)",
              background: "var(--bg-4)", display: "flex",
              alignItems: "center", justifyContent: "center",
              border: "1px solid var(--line-2)",
            }}>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--ink-3)" strokeWidth="1.8" strokeLinecap="round">
                <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M17 8l-5-5-5 5M12 3v12" />
              </svg>
            </div>
            <div>
              <div style={{ color: "var(--ink-2)", fontSize: 12, fontWeight: 500 }}>
                Drop PDFs or <span style={{ color: "var(--violet)" }}>browse</span>
              </div>
              <div style={{ color: "var(--ink-3)", fontSize: 10, marginTop: 2 }}>
                Multiple files supported
              </div>
            </div>
          </label>

          {files.length > 0 && (
            <div style={{
              marginTop: 8, maxHeight: 140, overflowY: "auto",
              display: "flex", flexDirection: "column", gap: 3,
            }}>
              {files.map((f, i) => (
                <FileChip
                  key={f.name}
                  file={f}
                  index={i}
                  onRemove={name => setFiles(p => p.filter(x => x.name !== name))}
                />
              ))}
            </div>
          )}
        </div>

        {/* Ranking Weights */}
        <div>
          <SectionLabel>Ranking Weights</SectionLabel>
          <div style={{ display: "flex", flexDirection: "column", gap: 5 }}>
            {[["skills", "Skills"], ["experience", "Experience"], ["education", "Education"], ["relevance", "Relevance"]].map(([k, l]) => (
              <WeightRow
                key={k} k={k} label={l}
                value={priorities[k]}
                onChange={(key, val) => setPriorities(p => ({ ...p, [key]: val }))}
              />
            ))}
          </div>
        </div>

        {/* Top N */}
        <div>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
            <SectionLabel>Show Top Candidates</SectionLabel>
            <span style={{
              fontFamily: "var(--mono)", fontSize: 12,
              color: "var(--violet)", fontWeight: 500,
              background: "var(--violet-dim)", border: "1px solid var(--violet-mid)",
              borderRadius: 5, padding: "1px 7px",
            }}>{topN}</span>
          </div>
          <input type="range" min={1} max={20} value={topN}
            onChange={e => setTopN(Number(e.target.value))}
            style={{ width: "100%", accentColor: "var(--violet)", cursor: "pointer", height: 3 }}
          />
          <div style={{ display: "flex", justifyContent: "space-between", marginTop: 4 }}>
            <span style={{ color: "var(--ink-4)", fontSize: 9, fontFamily: "var(--mono)" }}>1</span>
            <span style={{ color: "var(--ink-4)", fontSize: 9, fontFamily: "var(--mono)" }}>20</span>
          </div>
        </div>
      </div>

      {/* ── Analyze Button ── */}
      <div style={{ padding: "14px 18px", borderTop: "1px solid var(--line)", flexShrink: 0 }}>
        <button
          onClick={onAnalyze}
          disabled={!ready}
          style={{
            width: "100%", padding: "11px",
            borderRadius: "var(--r)", border: "none",
            background: ready
              ? "linear-gradient(135deg,#6c5ff7 0%,#a855f7 100%)"
              : "var(--bg-4)",
            color: ready ? "#fff" : "var(--ink-4)",
            fontFamily: "var(--font)", fontWeight: 600, fontSize: 13,
            cursor: ready ? "pointer" : "not-allowed",
            display: "flex", alignItems: "center", justifyContent: "center", gap: 8,
            letterSpacing: "-0.01em",
            boxShadow: ready ? "0 4px 20px rgba(108,95,247,0.35)" : "none",
            transition: "all .2s cubic-bezier(.4,0,.2,1)",
          }}
          onMouseEnter={e => ready && (e.currentTarget.style.transform = "translateY(-1px)")}
          onMouseLeave={e => (e.currentTarget.style.transform = "none")}
        >
          {loading ? (
            <>
              <span style={{
                width: 13, height: 13,
                border: "1.5px solid rgba(255,255,255,.3)",
                borderTopColor: "#fff",
                borderRadius: "50%",
                animation: "spin .7s linear infinite",
                display: "inline-block", flexShrink: 0,
              }} />
              <span>Analyzing…</span>
            </>
          ) : (
            <>
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                <circle cx="11" cy="11" r="8" /><path d="M21 21l-4.35-4.35" />
              </svg>
              Analyze Resumes
            </>
          )}
        </button>

        {!ready && !loading && (
          <div style={{
            textAlign: "center", marginTop: 7, fontSize: 10,
            color: "var(--ink-4)",
          }}>
            {!jdOk && files.length === 0
              ? "Add a JD and upload PDFs"
              : !jdOk
              ? "Job description too short"
              : "Upload at least one PDF"}
          </div>
        )}
      </div>
    </aside>
  );
}
