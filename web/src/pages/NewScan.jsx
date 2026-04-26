import { useState, useRef, useCallback, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { getUsage, scanResumes } from '../api'
import {
  FileText, Upload, X, CheckCircle2, AlertCircle,
  Sparkles, ChevronRight, Loader2, Plus, Info,
} from 'lucide-react'

const PRIORITIES = ['Ignore', 'Low', 'Medium', 'High', 'Critical']
const PRIORITY_COLOR = { Ignore:'var(--ink-5)', Low:'var(--sky)', Medium:'var(--amber)', High:'var(--accent)', Critical:'var(--rose)' }
const DEGREES = ['None', 'Associate', 'Bachelor', 'Master', 'PhD']

function formatBytes(b) {
  if (b < 1024) return `${b}B`
  if (b < 1024*1024) return `${(b/1024).toFixed(0)}KB`
  return `${(b/1024/1024).toFixed(1)}MB`
}

// Skills tag input
function SkillsInput({ label, hint, value, onChange, variant = 'required' }) {
  const [input, setInput] = useState('')
  const inputRef = useRef()

  function addSkill(raw) {
    const skill = raw.trim().toLowerCase()
    if (!skill || value.includes(skill)) return
    onChange([...value, skill])
    setInput('')
  }

  function onKey(e) {
    if (['Enter', ',', 'Tab'].includes(e.key)) {
      e.preventDefault()
      addSkill(input)
    }
    if (e.key === 'Backspace' && !input && value.length) {
      onChange(value.slice(0, -1))
    }
  }

  function remove(skill) { onChange(value.filter(s => s !== skill)) }

  const tagClass = variant === 'required' ? 'skill-tag-required' : 'skill-tag-preferred'

  return (
    <div>
      <label className="input-label">{label}</label>
      {hint && <div style={{ fontSize:11.5, color:'var(--ink-4)', marginBottom:7, lineHeight:1.4 }}>{hint}</div>}
      <div
        className="skills-input-wrap"
        onClick={() => inputRef.current?.focus()}
      >
        {value.map(s => (
          <span key={s} className={`skill-tag-item ${tagClass}`}>
            {s}
            <button
              type="button"
              onClick={() => remove(s)}
              style={{ background:'none', border:'none', cursor:'pointer', color:'inherit', display:'flex', padding:0, opacity:0.7 }}
            >
              <X size={10} />
            </button>
          </span>
        ))}
        <input
          ref={inputRef}
          className="skill-tag-input"
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={onKey}
          onBlur={() => input && addSkill(input)}
          placeholder={value.length === 0 ? 'Type skill and press Enter…' : ''}
        />
      </div>
    </div>
  )
}

const STEPS = ['Parsing resumes', 'Extracting skills & experience', 'Ranking candidates']

export default function NewScan({ onScanComplete, onShowToast }) {
  const [jd, setJd]               = useState('')
  const [roleTitle, setRole]       = useState('')
  const [files, setFiles]          = useState([])
  const [loading, setLoading]      = useState(false)
  const [step, setStep]            = useState(0)
  const [drag, setDrag]            = useState(false)
  const [showAdvanced, setAdvanced] = useState(false)
  const [usage, setUsage]          = useState(null)

  const [weights, setWeights] = useState({
    skills: 'High', experience: 'Medium', education: 'Low', relevance: 'Low',
  })
  const [requiredSkills,  setRequiredSkills]  = useState([])
  const [preferredSkills, setPreferredSkills] = useState([])
  const [minYears,        setMinYears]        = useState('')
  const [requiredDegree,  setRequiredDegree]  = useState('None')
  const [expCap,          setExpCap]          = useState('15')

  const fileRef  = useRef()
  const navigate = useNavigate()

  useEffect(() => {
    getUsage()
      .then(setUsage)
      .catch(() => onShowToast?.('Could not load scan usage', 'warning'))
  }, [])

  function processFiles(selected) {
    const pdfs    = Array.from(selected).filter(f => f.type === 'application/pdf')
    const tooBig  = pdfs.filter(f => f.size > 20*1024*1024)
    if (tooBig.length)  onShowToast?.(`${tooBig.length} file(s) exceed 20MB`, 'error')
    if (pdfs.length < selected.length) onShowToast?.('Only PDF files are accepted', 'warning')
    const valid = pdfs.filter(f => f.size <= 20*1024*1024)
    setFiles(p => [...p, ...valid].slice(0, 15))
  }

  const onDrag = useCallback(e => {
    e.preventDefault(); e.stopPropagation()
    setDrag(e.type === 'dragenter' || e.type === 'dragover')
  }, [])
  const onDrop = useCallback(e => {
    e.preventDefault(); e.stopPropagation(); setDrag(false)
    if (e.dataTransfer.files?.length) processFiles(e.dataTransfer.files)
  }, [])

  async function handleStart() {
    if (usage && !usage.is_unlimited && usage.free_scans_remaining <= 0) {
      onShowToast?.('Free scan limit reached. This account has used all 5 scans.', 'error')
      return
    }
    if (!roleTitle.trim())       { onShowToast?.('Enter a role title', 'error'); return }
    if (jd.trim().length < 20)   { onShowToast?.('Job description too short (min 20 chars)', 'error'); return }
    if (files.length === 0)      { onShowToast?.('Upload at least one resume', 'error'); return }

    setLoading(true); setStep(1)
    const t1 = setTimeout(() => setStep(2), 2000)
    const t2 = setTimeout(() => setStep(3), 4200)

    try {
      const result = await scanResumes({
        roleTitle,
        jobDescription: jd,
        files,
        priorities: weights,
        requiredSkills,
        preferredSkills,
        minYearsExperience: minYears ? parseFloat(minYears) : null,
        requiredDegree: requiredDegree === 'None' ? null : requiredDegree,
        experienceCapYears: parseFloat(expCap) || 15,
      })
      clearTimeout(t1); clearTimeout(t2)
      onScanComplete?.(result)
      onShowToast?.(`Analysis complete — ${result.total_candidates} candidates ranked`, 'success')
      navigate('/results')
    } catch (err) {
      clearTimeout(t1); clearTimeout(t2)
      onShowToast?.(err.message || 'Scan failed', 'error')
    } finally {
      setLoading(false); setStep(0)
    }
  }

  const quotaRemaining = usage?.free_scans_remaining
  const quotaUnlimited = Boolean(usage?.is_unlimited)
  const quotaExhausted = !quotaUnlimited && quotaRemaining != null && quotaRemaining <= 0
  const canStart = roleTitle.trim() && jd.trim().length >= 20 && files.length > 0 && !loading && !quotaExhausted

  // Loading overlay
  if (loading) {
    return (
      <div style={{ flex:1, display:'flex', alignItems:'center', justifyContent:'center' }}>
        <div className="card au" style={{ padding:'48px 56px', textAlign:'center', maxWidth:440 }}>
          <div style={{
            width:56, height:56, borderRadius:16,
            background:'var(--accent-soft)', border:'1px solid var(--accent-mid)',
            display:'flex', alignItems:'center', justifyContent:'center',
            margin:'0 auto 20px',
          }}>
            <Sparkles size={24} color="var(--accent)" />
          </div>
          <h3 style={{ fontFamily:'var(--syne)', fontSize:17, fontWeight:800, marginBottom:6 }}>Analyzing candidates…</h3>
          <p style={{ fontSize:13, color:'var(--ink-4)', marginBottom:28 }}>
            Processing {files.length} resume{files.length !== 1 ? 's' : ''} for {roleTitle}
          </p>
          <div style={{ display:'flex', flexDirection:'column', gap:8, marginBottom:24 }}>
            {STEPS.map((s, i) => {
              const isDone   = i < step - 1
              const isActive = i === step - 1
              return (
                <div key={s} style={{
                  display:'flex', alignItems:'center', gap:10,
                  padding:'10px 14px', borderRadius:'var(--r-md)',
                  background: isActive ? 'var(--accent-soft)' : isDone ? 'var(--green-dim)' : 'var(--bg-3)',
                  border:`1px solid ${isActive ? 'var(--accent-mid)' : isDone ? 'rgba(16,185,129,0.2)' : 'var(--line)'}`,
                  transition:'all 0.3s ease',
                }}>
                  <div style={{ flexShrink:0 }}>
                    {isDone
                      ? <CheckCircle2 size={15} color="var(--green-strong)" />
                      : isActive
                        ? <Loader2 size={15} color="var(--accent)" className="spin" />
                        : <div style={{ width:15, height:15, borderRadius:'50%', border:'1.5px solid var(--bg-5)' }} />
                    }
                  </div>
                  <span style={{
                    fontSize:13, fontWeight:600,
                    color: isActive ? 'var(--accent-2)' : isDone ? 'var(--green-strong)' : 'var(--ink-5)',
                  }}>{s}</span>
                </div>
              )
            })}
          </div>
          <div style={{ height:4, background:'var(--bg-4)', borderRadius:2, overflow:'hidden' }}>
            <div className="bar-fill" style={{
              height:'100%', background:'var(--accent)', borderRadius:2,
              width:`${(step/3)*100}%`, transition:'width 0.5s ease',
            }} />
          </div>
        </div>
      </div>
    )
  }

  return (
    <>
      <div className="section-hd au">
        <div>
          <div className="page-kicker"><Sparkles size={12} /> Scan setup</div>
          <h1 className="section-title">New Candidate Scan</h1>
          <p className="section-sub">Define the hiring bar, add resumes, and generate a ranked decision slate</p>
        </div>
      </div>

      <div className="workbench-grid">

        {/* Left column */}
        <div className="panel-stack">

          {/* Role */}
          <div className="card au au-1" style={{ padding:20 }}>
            <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:14, marginBottom:14 }}>
              <div>
                <label className="input-label">Role Title</label>
                <input className="input-base" placeholder="e.g. Senior Frontend Engineer"
                  value={roleTitle} onChange={e => setRole(e.target.value)} />
              </div>
              <div>
                <label className="input-label">Experience Cap (years)</label>
                <input className="input-base" type="number" min="1" max="40" placeholder="15"
                  value={expCap} onChange={e => setExpCap(e.target.value)} />
              </div>
            </div>
            <div>
              <label className="input-label">Job Description</label>
              <textarea
                className="input-base"
                rows={7}
                placeholder="Paste the full job description here. Include responsibilities, required skills, and qualifications…"
                value={jd}
                onChange={e => setJd(e.target.value)}
                style={{ resize:'vertical', minHeight:160 }}
              />
              <div style={{ marginTop:5, fontSize:11, color: jd.length < 20 ? 'var(--ink-5)' : 'var(--green-strong)' }}>
                {jd.length} chars {jd.length < 20 && '(min 20)'}
              </div>
            </div>
          </div>

          {/* Skills */}
          <div className="card au au-2" style={{ padding:20, display:'flex', flexDirection:'column', gap:16 }}>
            <SkillsInput
              label="Required Skills"
              hint="Must-have skills. Candidates missing these will be penalised."
              value={requiredSkills}
              onChange={setRequiredSkills}
              variant="required"
            />
            <SkillsInput
              label="Preferred Skills"
              hint="Nice-to-have skills. Provide a small scoring boost if present."
              value={preferredSkills}
              onChange={setPreferredSkills}
              variant="preferred"
            />
          </div>

          {/* Advanced */}
          <div className="card au au-3" style={{ overflow:'hidden' }}>
            <button
              onClick={() => setAdvanced(s => !s)}
              style={{
                width:'100%', display:'flex', alignItems:'center', justifyContent:'space-between',
                padding:'14px 20px', background:'none', border:'none', cursor:'pointer',
                color:'var(--ink-3)', fontSize:13, fontWeight:600,
              }}
            >
              <span style={{ display:'flex', alignItems:'center', gap:7 }}><Info size={14} />Advanced Filters</span>
              <ChevronRight size={14} style={{ transform: showAdvanced ? 'rotate(90deg)' : 'none', transition:'transform 0.2s' }} />
            </button>
            {showAdvanced && (
              <div style={{ padding:'0 20px 20px', display:'grid', gridTemplateColumns:'1fr 1fr', gap:14 }}>
                <div>
                  <label className="input-label">Min. Years Experience</label>
                  <input className="input-base" type="number" min="0" max="40" placeholder="e.g. 3"
                    value={minYears} onChange={e => setMinYears(e.target.value)} />
                </div>
                <div>
                  <label className="input-label">Required Degree</label>
                  <select
                    className="input-base"
                    value={requiredDegree}
                    onChange={e => setRequiredDegree(e.target.value)}
                    style={{ cursor:'pointer' }}
                  >
                    {DEGREES.map(d => <option key={d} value={d}>{d}</option>)}
                  </select>
                </div>
              </div>
            )}
          </div>

          {/* Drop zone */}
          <div className="card au au-4" style={{ padding:20 }}>
            <label className="input-label">Resume Files ({files.length}/15)</label>
            <div
              className={`drop-zone${drag ? ' active' : ''}`}
              onDragEnter={onDrag} onDragOver={onDrag} onDragLeave={onDrag} onDrop={onDrop}
              onClick={() => fileRef.current?.click()}
            >
              <input ref={fileRef} type="file" accept=".pdf" multiple style={{ display:'none' }}
                onChange={e => processFiles(e.target.files)} />
              <Upload size={22} style={{ margin:'0 auto 10px', color: drag ? 'var(--accent)' : 'var(--ink-5)' }} />
              <div style={{ fontSize:13.5, fontWeight:600, color: drag ? 'var(--accent-2)' : 'var(--ink-3)', marginBottom:4 }}>
                {drag ? 'Drop here' : 'Drop PDF resumes or click to browse'}
              </div>
              <div style={{ fontSize:12, color:'var(--ink-5)' }}>Up to 15 files · PDF only · Max 20MB each</div>
            </div>

            {files.length > 0 && (
              <div style={{ marginTop:12, display:'flex', flexDirection:'column', gap:6 }}>
                {files.map((f, i) => (
                  <div key={i} style={{
                    display:'flex', alignItems:'center', gap:10,
                    padding:'8px 12px', borderRadius:'var(--r-md)',
                    background:'var(--bg-3)', border:'1px solid var(--line)',
                  }}>
                    <FileText size={14} color="var(--accent)" style={{ flexShrink:0 }} />
                    <div style={{ flex:1, minWidth:0 }}>
                      <div style={{ fontSize:12.5, fontWeight:600, color:'var(--ink-2)', overflow:'hidden', textOverflow:'ellipsis', whiteSpace:'nowrap' }}>
                        {f.name}
                      </div>
                      <div style={{ fontSize:11, color:'var(--ink-5)' }}>{formatBytes(f.size)}</div>
                    </div>
                    <button className="btn btn-ghost btn-sm btn-icon" onClick={() => setFiles(p => p.filter((_, j) => j !== i))}
                      style={{ color:'var(--ink-4)' }}>
                      <X size={13} />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Right column */}
        <div className="panel-stack sticky-actions">

          <div className="decision-card au au-1">
            <div style={{ display:'flex', alignItems:'center', justifyContent:'space-between', gap:12 }}>
              <div>
                <div className="panel-title">Free Plan Usage</div>
                <p className="panel-copy">Each account includes 5 free scans.</p>
              </div>
              <span className="score-pill score-pill-strong" style={{
                background: quotaExhausted ? 'var(--red-soft)' : 'var(--accent-soft)',
                color: quotaExhausted ? 'var(--red)' : 'var(--accent-2)',
              }}>
                {quotaUnlimited ? 'Dev' : usage ? `${usage.free_scans_used}/${usage.free_scan_limit}` : '--/5'}
              </span>
            </div>
            <div style={{ height:6, background:'var(--bg-5)', borderRadius:3, overflow:'hidden', marginTop:14 }}>
              <div
                className="bar-fill"
                style={{
                  width: `${quotaUnlimited ? 100 : usage ? Math.min((usage.free_scans_used / usage.free_scan_limit) * 100, 100) : 0}%`,
                  height:'100%',
                  background: quotaExhausted ? 'var(--red)' : 'var(--accent)',
                  borderRadius:3,
                }}
              />
            </div>
            <div style={{ marginTop:10, fontSize:12, color: quotaExhausted ? 'var(--red)' : 'var(--ink-4)', lineHeight:1.45 }}>
              {usage
                ? quotaUnlimited
                  ? 'Dev mode active. Free scan limits are bypassed locally.'
                  : quotaExhausted
                  ? 'Free scan limit reached for this account.'
                  : `${usage.free_scans_remaining} free scan${usage.free_scans_remaining !== 1 ? 's' : ''} remaining.`
                : 'Loading scan allowance...'}
            </div>
          </div>

          {/* Scoring weights */}
          <div className="card au au-1" style={{ padding:20 }}>
            <div style={{ marginBottom:16 }}>
              <div style={{ fontFamily:'var(--syne)', fontSize:13.5, fontWeight:700, color:'var(--ink)', marginBottom:3 }}>
                Scoring Weights
              </div>
              <div style={{ fontSize:12, color:'var(--ink-4)' }}>Prioritize what matters for this role</div>
            </div>

            {Object.entries(weights).map(([key, val]) => (
              <div key={key} style={{ marginBottom:14 }}>
                <div style={{
                  fontSize:12, fontWeight:600, color:'var(--ink-3)',
                  textTransform:'capitalize', marginBottom:7,
                  display:'flex', justifyContent:'space-between',
                }}>
                  <span>{key}</span>
                  <span style={{ color: PRIORITY_COLOR[val], fontFamily:'var(--mono)', fontSize:11 }}>{val}</span>
                </div>
                <div style={{ display:'flex', gap:5 }}>
                  {PRIORITIES.map(opt => (
                    <button
                      key={opt}
                      className={`weight-chip${val === opt ? ' active' : ''}`}
                      style={val === opt ? { background: PRIORITY_COLOR[opt], borderColor: PRIORITY_COLOR[opt] } : {}}
                      onClick={() => setWeights(w => ({ ...w, [key]: opt }))}
                    >
                      {opt[0]}
                    </button>
                  ))}
                </div>
              </div>
            ))}

            <div style={{ marginTop:4, padding:'8px 10px', borderRadius:'var(--r)', background:'var(--bg-3)', border:'1px solid var(--line)' }}>
              <div style={{ fontSize:10.5, color:'var(--ink-5)', lineHeight:1.5 }}>
                <strong style={{ color:'var(--ink-4)' }}>I</strong>gnore · <strong style={{ color:'var(--sky)' }}>L</strong>ow · <strong style={{ color:'var(--amber)' }}>M</strong>edium · <strong style={{ color:'var(--accent-2)' }}>H</strong>igh · <strong style={{ color:'var(--rose)' }}>C</strong>ritical
              </div>
            </div>
          </div>

          {/* Summary + CTA */}
          <div className="card au au-2" style={{ padding:20 }}>
            <label className="input-label" style={{ marginBottom:12 }}>Scan Summary</label>
            {[
              { label:'Role',     value: roleTitle || '—',                         ok: !!roleTitle },
              { label:'JD',       value: jd.length > 0 ? `${jd.length} chars` : '—', ok: jd.length >= 20 },
              { label:'Resumes',  value: `${files.length} file${files.length !== 1 ? 's' : ''}`, ok: files.length > 0 },
              { label:'Req. Skills', value: requiredSkills.length > 0 ? `${requiredSkills.length} added` : 'auto-detect', ok: true },
            ].map(r => (
              <div key={r.label} style={{
                display:'flex', justifyContent:'space-between', alignItems:'center',
                padding:'7px 0', borderBottom:'1px solid var(--line)', fontSize:12.5,
              }}>
                <span style={{ color:'var(--ink-4)' }}>{r.label}</span>
                <span style={{ display:'flex', alignItems:'center', gap:5, fontWeight:600, color: r.ok ? 'var(--ink-2)' : 'var(--ink-5)' }}>
                  {r.ok
                    ? <CheckCircle2 size={11} color="var(--green-strong)" />
                    : <AlertCircle  size={11} color="var(--ink-5)" />
                  }
                  {r.value}
                </span>
              </div>
            ))}

            <button
              className="btn btn-primary"
              style={{ width:'100%', height:42, fontSize:14, justifyContent:'center', marginTop:18 }}
              onClick={handleStart}
              disabled={!canStart}
            >
              <Sparkles size={15} />
              Start AI Scan
              <ChevronRight size={15} />
            </button>
          </div>
        </div>
      </div>
    </>
  )
}
