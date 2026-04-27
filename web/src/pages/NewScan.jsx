import { useState, useRef, useCallback, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { getUsage, scanResumes } from '../api'
import {
  FileText, Upload, X, CheckCircle2, AlertCircle,
  Sparkles, ChevronRight, Loader2, Info,
} from 'lucide-react'

const PRIORITIES = ['Ignore', 'Low', 'Medium', 'High', 'Critical']
const PRIORITY_COLOR = {
  Ignore: 'var(--ink-5)',
  Low: 'var(--blue)',
  Medium: 'var(--amber)',
  High: 'var(--accent)',
  Critical: 'var(--red)',
}
const DEGREES = ['None', 'Associate', 'Bachelor', 'Master', 'PhD']
const MIN_JD_CHARS = 20
const MAX_JD_CHARS = 10000
const MAX_JD_FILE_BYTES = 256 * 1024
const MAX_RESUME_FILES = 20
const MAX_PDF_SIZE_BYTES = 20 * 1024 * 1024
const STEPS = ['Parsing resumes', 'Extracting skills and experience', 'Ranking candidates']

function formatBytes(bytes) {
  if (bytes < 1024) return `${bytes}B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)}KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)}MB`
}

function SkillsInput({ label, hint, value, onChange, variant = 'required' }) {
  const [input, setInput] = useState('')
  const inputRef = useRef()

  function addSkill(raw) {
    const skill = raw.trim().toLowerCase()
    if (!skill || value.includes(skill)) return
    onChange([...value, skill])
    setInput('')
  }

  function onKey(event) {
    if (['Enter', ',', 'Tab'].includes(event.key)) {
      event.preventDefault()
      addSkill(input)
    }
    if (event.key === 'Backspace' && !input && value.length) {
      onChange(value.slice(0, -1))
    }
  }

  function remove(skill) {
    onChange(value.filter(item => item !== skill))
  }

  const tagClass = variant === 'required' ? 'skill-tag-required' : 'skill-tag-preferred'

  return (
    <div>
      <label className="input-label">{label}</label>
      {hint && <div style={{ fontSize: 11.5, color: 'var(--ink-4)', marginBottom: 7, lineHeight: 1.4 }}>{hint}</div>}
      <div className="skills-input-wrap" onClick={() => inputRef.current?.focus()}>
        {value.map(skill => (
          <span key={skill} className={`skill-tag-item ${tagClass}`}>
            {skill}
            <button
              type="button"
              onClick={() => remove(skill)}
              style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'inherit', display: 'flex', padding: 0, opacity: 0.7 }}
            >
              <X size={10} />
            </button>
          </span>
        ))}
        <input
          ref={inputRef}
          className="skill-tag-input"
          value={input}
          onChange={event => setInput(event.target.value)}
          onKeyDown={onKey}
          onBlur={() => input && addSkill(input)}
          placeholder={value.length === 0 ? 'Type skill and press Enter...' : ''}
        />
      </div>
    </div>
  )
}

export default function NewScan({ onScanComplete, onShowToast }) {
  const [jdMode, setJdMode] = useState('text')
  const [jd, setJd] = useState('')
  const [jdFile, setJdFile] = useState(null)
  const [jdFileChars, setJdFileChars] = useState(0)
  const [roleTitle, setRole] = useState('')
  const [files, setFiles] = useState([])
  const [loading, setLoading] = useState(false)
  const [step, setStep] = useState(0)
  const [drag, setDrag] = useState(false)
  const [showAdvanced, setAdvanced] = useState(false)
  const [usage, setUsage] = useState(null)

  const [weights, setWeights] = useState({
    skills: 'High',
    experience: 'Medium',
    education: 'Low',
    relevance: 'Low',
  })
  const [requiredSkills, setRequiredSkills] = useState([])
  const [preferredSkills, setPreferredSkills] = useState([])
  const [minYears, setMinYears] = useState('')
  const [requiredDegree, setRequiredDegree] = useState('None')
  const [expCap, setExpCap] = useState('15')

  const fileRef = useRef()
  const jdFileRef = useRef()
  const navigate = useNavigate()

  useEffect(() => {
    getUsage()
      .then(setUsage)
      .catch(() => onShowToast?.('Could not load scan usage', 'warning'))
  }, [onShowToast])

  async function processJdFile(file) {
    if (!file) return

    const name = file.name.toLowerCase()
    if (!name.endsWith('.txt') && !name.endsWith('.md')) {
      onShowToast?.('Upload a .txt or .md job description file', 'error')
      return
    }
    if (file.size > MAX_JD_FILE_BYTES) {
      onShowToast?.(`JD file exceeds ${formatBytes(MAX_JD_FILE_BYTES)}`, 'error')
      return
    }

    const text = (await file.text()).trim()
    if (text.length < MIN_JD_CHARS) {
      onShowToast?.(`JD file is too short (min ${MIN_JD_CHARS} chars)`, 'error')
      return
    }
    if (text.length > MAX_JD_CHARS) {
      onShowToast?.(`JD file is too long (max ${MAX_JD_CHARS.toLocaleString()} chars)`, 'error')
      return
    }

    setJdFile(file)
    setJdFileChars(text.length)
  }

  function processFiles(selected) {
    const picked = Array.from(selected || [])
    const pdfs = picked.filter(file => file.type === 'application/pdf')
    const tooBig = pdfs.filter(file => file.size > MAX_PDF_SIZE_BYTES)

    if (tooBig.length) onShowToast?.(`${tooBig.length} file(s) exceed ${formatBytes(MAX_PDF_SIZE_BYTES)}`, 'error')
    if (pdfs.length < picked.length) onShowToast?.('Only PDF files are accepted', 'warning')

    const valid = pdfs.filter(file => file.size <= MAX_PDF_SIZE_BYTES)
    setFiles(prev => {
      const next = [...prev, ...valid].slice(0, MAX_RESUME_FILES)
      if (prev.length + valid.length > MAX_RESUME_FILES) {
        onShowToast?.(`Only ${MAX_RESUME_FILES} PDFs can be uploaded per scan`, 'warning')
      }
      return next
    })
  }

  const onDrag = useCallback(event => {
    event.preventDefault()
    event.stopPropagation()
    setDrag(event.type === 'dragenter' || event.type === 'dragover')
  }, [])

  const onDrop = useCallback(event => {
    event.preventDefault()
    event.stopPropagation()
    setDrag(false)
    if (event.dataTransfer.files?.length) processFiles(event.dataTransfer.files)
  }, [])

  async function handleStart() {
    if (usage && !usage.is_unlimited && usage.free_scans_remaining <= 0) {
      onShowToast?.('Free scan limit reached. This account has used all 5 scans.', 'error')
      return
    }
    if (!roleTitle.trim()) {
      onShowToast?.('Enter a role title', 'error')
      return
    }
    if (jdMode === 'text' && jd.trim().length < MIN_JD_CHARS) {
      onShowToast?.(`Job description too short (min ${MIN_JD_CHARS} chars)`, 'error')
      return
    }
    if (jdMode === 'text' && jd.length > MAX_JD_CHARS) {
      onShowToast?.(`Job description too long (max ${MAX_JD_CHARS.toLocaleString()} chars)`, 'error')
      return
    }
    if (jdMode === 'file' && !jdFile) {
      onShowToast?.('Upload a job description file', 'error')
      return
    }
    if (files.length === 0) {
      onShowToast?.('Upload at least one resume', 'error')
      return
    }

    setLoading(true)
    setStep(1)
    const t1 = setTimeout(() => setStep(2), 2000)
    const t2 = setTimeout(() => setStep(3), 4200)

    try {
      const result = await scanResumes({
        roleTitle,
        jobDescription: jdMode === 'text' ? jd : '',
        jdFile,
        files,
        priorities: weights,
        requiredSkills,
        preferredSkills,
        minYearsExperience: minYears ? parseFloat(minYears) : null,
        requiredDegree: requiredDegree === 'None' ? null : requiredDegree,
        experienceCapYears: parseFloat(expCap) || 15,
      })
      clearTimeout(t1)
      clearTimeout(t2)
      onScanComplete?.(result)
      onShowToast?.(`Analysis complete - ${result.total_candidates} candidates ranked`, 'success')
      navigate('/results')
    } catch (error) {
      clearTimeout(t1)
      clearTimeout(t2)
      onShowToast?.(error.message || 'Scan failed', 'error')
    } finally {
      setLoading(false)
      setStep(0)
    }
  }

  const quotaRemaining = usage?.free_scans_remaining
  const quotaUnlimited = Boolean(usage?.is_unlimited)
  const quotaExhausted = !quotaUnlimited && quotaRemaining != null && quotaRemaining <= 0
  const jdReady = jdMode === 'text'
    ? jd.trim().length >= MIN_JD_CHARS && jd.length <= MAX_JD_CHARS
    : Boolean(jdFile && jdFileChars >= MIN_JD_CHARS && jdFileChars <= MAX_JD_CHARS)
  const canStart = roleTitle.trim() && jdReady && files.length > 0 && !loading && !quotaExhausted

  if (loading) {
    return (
      <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div className="card au" style={{ padding: '48px 56px', textAlign: 'center', maxWidth: 440 }}>
          <div
            style={{
              width: 56,
              height: 56,
              borderRadius: 16,
              background: 'var(--accent-soft)',
              border: '1px solid var(--accent-mid)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              margin: '0 auto 20px',
            }}
          >
            <Sparkles size={24} color="var(--accent)" />
          </div>
          <h3 style={{ fontSize: 17, fontWeight: 800, marginBottom: 6 }}>Analyzing candidates...</h3>
          <p style={{ fontSize: 13, color: 'var(--ink-4)', marginBottom: 28 }}>
            Processing {files.length} resume{files.length !== 1 ? 's' : ''} for {roleTitle}
          </p>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 24 }}>
            {STEPS.map((label, index) => {
              const isDone = index < step - 1
              const isActive = index === step - 1
              return (
                <div
                  key={label}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 10,
                    padding: '10px 14px',
                    borderRadius: 'var(--r-md)',
                    background: isActive ? 'var(--accent-soft)' : isDone ? 'var(--green-dim)' : 'var(--bg-3)',
                    border: `1px solid ${isActive ? 'var(--accent-mid)' : isDone ? 'rgba(16,185,129,0.2)' : 'var(--line)'}`,
                    transition: 'all 0.3s ease',
                  }}
                >
                  <div style={{ flexShrink: 0 }}>
                    {isDone ? (
                      <CheckCircle2 size={15} color="var(--green)" />
                    ) : isActive ? (
                      <Loader2 size={15} color="var(--accent)" className="spin" />
                    ) : (
                      <div style={{ width: 15, height: 15, borderRadius: '50%', border: '1.5px solid var(--bg-5)' }} />
                    )}
                  </div>
                  <span
                    style={{
                      fontSize: 13,
                      fontWeight: 600,
                      color: isActive ? 'var(--accent-2)' : isDone ? 'var(--green)' : 'var(--ink-5)',
                    }}
                  >
                    {label}
                  </span>
                </div>
              )
            })}
          </div>
          <div style={{ height: 4, background: 'var(--bg-4)', borderRadius: 2, overflow: 'hidden' }}>
            <div
              className="bar-fill"
              style={{
                height: '100%',
                background: 'var(--accent)',
                borderRadius: 2,
                width: `${(step / 3) * 100}%`,
                transition: 'width 0.5s ease',
              }}
            />
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
        <div className="panel-stack">
          <div className="card au au-1" style={{ padding: 20 }}>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14, marginBottom: 14 }}>
              <div>
                <label className="input-label">Role Title</label>
                <input
                  className="input-base"
                  placeholder="e.g. Senior Frontend Engineer"
                  value={roleTitle}
                  onChange={event => setRole(event.target.value)}
                />
              </div>
              <div>
                <label className="input-label">Experience Cap (years)</label>
                <input
                  className="input-base"
                  type="number"
                  min="1"
                  max="40"
                  placeholder="15"
                  value={expCap}
                  onChange={event => setExpCap(event.target.value)}
                />
              </div>
            </div>

            <div>
              <label className="input-label">Job Description</label>
              <div className="mode-toggle" style={{ marginBottom: 10 }}>
                <button
                  type="button"
                  className={`mode-toggle-button${jdMode === 'text' ? ' active' : ''}`}
                  onClick={() => setJdMode('text')}
                >
                  Paste text
                </button>
                <button
                  type="button"
                  className={`mode-toggle-button${jdMode === 'file' ? ' active' : ''}`}
                  onClick={() => setJdMode('file')}
                >
                  Upload .txt
                </button>
              </div>

              {jdMode === 'text' ? (
                <>
                  <textarea
                    className="input-base"
                    rows={7}
                    placeholder="Paste the full job description here. Include responsibilities, required skills, and qualifications..."
                    value={jd}
                    onChange={event => setJd(event.target.value)}
                    style={{ resize: 'vertical', minHeight: 160 }}
                  />
                  <div style={{ marginTop: 5, fontSize: 11, color: jdReady ? 'var(--green)' : 'var(--ink-5)' }}>
                    {jd.length.toLocaleString()} / {MAX_JD_CHARS.toLocaleString()} chars
                  </div>
                </>
              ) : (
                <>
                  <div className="drop-zone" onClick={() => jdFileRef.current?.click()}>
                    <input
                      ref={jdFileRef}
                      type="file"
                      accept=".txt,.md,text/plain,text/markdown"
                      style={{ display: 'none' }}
                      onChange={event => processJdFile(event.target.files?.[0])}
                    />
                    <FileText size={20} style={{ margin: '0 auto 10px', color: 'var(--accent)' }} />
                    <div style={{ fontSize: 13.5, fontWeight: 600, color: 'var(--ink-3)', marginBottom: 4 }}>
                      {jdFile ? jdFile.name : 'Upload a plain text job description'}
                    </div>
                    <div style={{ fontSize: 12, color: 'var(--ink-5)' }}>
                      Max {formatBytes(MAX_JD_FILE_BYTES)} and {MAX_JD_CHARS.toLocaleString()} parsed chars
                    </div>
                  </div>
                  {jdFile && (
                    <div style={{ marginTop: 8, fontSize: 11.5, color: jdReady ? 'var(--green)' : 'var(--ink-5)' }}>
                      {jdFileChars.toLocaleString()} characters parsed from file
                    </div>
                  )}
                </>
              )}
            </div>
          </div>

          <div className="card au au-2" style={{ padding: 20, display: 'flex', flexDirection: 'column', gap: 16 }}>
            <SkillsInput
              label="Required Skills"
              hint="Must-have skills. Candidates missing these will be penalized."
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

          <div className="card au au-3" style={{ overflow: 'hidden' }}>
            <button
              onClick={() => setAdvanced(current => !current)}
              style={{
                width: '100%',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '14px 20px',
                background: 'none',
                border: 'none',
                cursor: 'pointer',
                color: 'var(--ink-3)',
                fontSize: 13,
                fontWeight: 600,
              }}
            >
              <span style={{ display: 'flex', alignItems: 'center', gap: 7 }}><Info size={14} />Advanced Filters</span>
              <ChevronRight size={14} style={{ transform: showAdvanced ? 'rotate(90deg)' : 'none', transition: 'transform 0.2s' }} />
            </button>
            {showAdvanced && (
              <div style={{ padding: '0 20px 20px', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
                <div>
                  <label className="input-label">Min. Years Experience</label>
                  <input
                    className="input-base"
                    type="number"
                    min="0"
                    max="40"
                    placeholder="e.g. 3"
                    value={minYears}
                    onChange={event => setMinYears(event.target.value)}
                  />
                </div>
                <div>
                  <label className="input-label">Required Degree</label>
                  <select
                    className="input-base"
                    value={requiredDegree}
                    onChange={event => setRequiredDegree(event.target.value)}
                    style={{ cursor: 'pointer' }}
                  >
                    {DEGREES.map(degree => <option key={degree} value={degree}>{degree}</option>)}
                  </select>
                </div>
              </div>
            )}
          </div>

          <div className="card au au-4" style={{ padding: 20 }}>
            <label className="input-label">Resume Files ({files.length}/{MAX_RESUME_FILES})</label>
            <div
              className={`drop-zone${drag ? ' active' : ''}`}
              onDragEnter={onDrag}
              onDragOver={onDrag}
              onDragLeave={onDrag}
              onDrop={onDrop}
              onClick={() => fileRef.current?.click()}
            >
              <input
                ref={fileRef}
                type="file"
                accept=".pdf"
                multiple
                style={{ display: 'none' }}
                onChange={event => processFiles(event.target.files)}
              />
              <Upload size={22} style={{ margin: '0 auto 10px', color: drag ? 'var(--accent)' : 'var(--ink-5)' }} />
              <div style={{ fontSize: 13.5, fontWeight: 600, color: drag ? 'var(--accent-2)' : 'var(--ink-3)', marginBottom: 4 }}>
                {drag ? 'Drop here' : 'Drop PDF resumes or click to browse'}
              </div>
              <div style={{ fontSize: 12, color: 'var(--ink-5)' }}>
                Up to {MAX_RESUME_FILES} files, PDF only, max {formatBytes(MAX_PDF_SIZE_BYTES)} each
              </div>
            </div>

            {files.length > 0 && (
              <div style={{ marginTop: 12, display: 'flex', flexDirection: 'column', gap: 6 }}>
                {files.map((file, index) => (
                  <div
                    key={`${file.name}-${index}`}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 10,
                      padding: '8px 12px',
                      borderRadius: 'var(--r-md)',
                      background: 'var(--bg-3)',
                      border: '1px solid var(--line)',
                    }}
                  >
                    <FileText size={14} color="var(--accent)" style={{ flexShrink: 0 }} />
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ fontSize: 12.5, fontWeight: 600, color: 'var(--ink-2)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {file.name}
                      </div>
                      <div style={{ fontSize: 11, color: 'var(--ink-5)' }}>{formatBytes(file.size)}</div>
                    </div>
                    <button
                      className="btn btn-ghost btn-sm btn-icon"
                      onClick={() => setFiles(current => current.filter((_, itemIndex) => itemIndex !== index))}
                      style={{ color: 'var(--ink-4)' }}
                    >
                      <X size={13} />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        <div className="panel-stack sticky-actions">
          <div className="decision-card au au-1">
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12 }}>
              <div>
                <div className="panel-title">Free Plan Usage</div>
                <p className="panel-copy">Each account includes 5 free scans.</p>
              </div>
              <span
                className="score-pill score-pill-strong"
                style={{
                  background: quotaExhausted ? 'var(--red-dim)' : 'var(--accent-dim)',
                  color: quotaExhausted ? 'var(--red)' : 'var(--accent-2)',
                }}
              >
                {quotaUnlimited ? 'Dev' : usage ? `${usage.free_scans_used}/${usage.free_scan_limit}` : '--/5'}
              </span>
            </div>
            <div style={{ height: 6, background: 'var(--bg-5)', borderRadius: 3, overflow: 'hidden', marginTop: 14 }}>
              <div
                className="bar-fill"
                style={{
                  width: `${quotaUnlimited ? 100 : usage ? Math.min((usage.free_scans_used / usage.free_scan_limit) * 100, 100) : 0}%`,
                  height: '100%',
                  background: quotaExhausted ? 'var(--red)' : 'var(--accent)',
                  borderRadius: 3,
                }}
              />
            </div>
            <div style={{ marginTop: 10, fontSize: 12, color: quotaExhausted ? 'var(--red)' : 'var(--ink-4)', lineHeight: 1.45 }}>
              {usage
                ? quotaUnlimited
                  ? 'Dev mode active. Free scan limits are bypassed locally.'
                  : quotaExhausted
                    ? 'Free scan limit reached for this account.'
                    : `${usage.free_scans_remaining} free scan${usage.free_scans_remaining !== 1 ? 's' : ''} remaining.`
                : 'Loading scan allowance...'}
            </div>
          </div>

          <div className="card au au-1" style={{ padding: 20 }}>
            <div style={{ marginBottom: 16 }}>
              <div style={{ fontSize: 13.5, fontWeight: 700, color: 'var(--ink)', marginBottom: 3 }}>
                Scoring Weights
              </div>
              <div style={{ fontSize: 12, color: 'var(--ink-4)' }}>Prioritize what matters for this role</div>
            </div>

            {Object.entries(weights).map(([key, value]) => (
              <div key={key} style={{ marginBottom: 14 }}>
                <div
                  style={{
                    fontSize: 12,
                    fontWeight: 600,
                    color: 'var(--ink-3)',
                    textTransform: 'capitalize',
                    marginBottom: 7,
                    display: 'flex',
                    justifyContent: 'space-between',
                  }}
                >
                  <span>{key}</span>
                  <span style={{ color: PRIORITY_COLOR[value], fontFamily: 'var(--mono)', fontSize: 11 }}>{value}</span>
                </div>
                <div style={{ display: 'flex', gap: 5 }}>
                  {PRIORITIES.map(option => (
                    <button
                      key={option}
                      className={`weight-chip${value === option ? ' active' : ''}`}
                      style={value === option ? { background: PRIORITY_COLOR[option], borderColor: PRIORITY_COLOR[option] } : {}}
                      onClick={() => setWeights(current => ({ ...current, [key]: option }))}
                    >
                      {option[0]}
                    </button>
                  ))}
                </div>
              </div>
            ))}

            <div style={{ marginTop: 4, padding: '8px 10px', borderRadius: 'var(--r)', background: 'var(--bg-3)', border: '1px solid var(--line)' }}>
              <div style={{ fontSize: 10.5, color: 'var(--ink-5)', lineHeight: 1.5 }}>
                Ignore, Low, Medium, High, Critical
              </div>
            </div>
          </div>

          <div className="card au au-2" style={{ padding: 20 }}>
            <label className="input-label" style={{ marginBottom: 12 }}>Scan Summary</label>
            {[
              { label: 'Role', value: roleTitle || '-', ok: !!roleTitle },
              {
                label: 'JD',
                value: jdMode === 'file'
                  ? jdFile
                    ? `${jdFile.name} - ${jdFileChars} chars`
                    : '-'
                  : jd.length > 0
                    ? `${jd.length} chars`
                    : '-',
                ok: jdReady,
              },
              { label: 'Resumes', value: `${files.length} file${files.length !== 1 ? 's' : ''}`, ok: files.length > 0 },
              { label: 'Req. Skills', value: requiredSkills.length > 0 ? `${requiredSkills.length} added` : 'auto-detect', ok: true },
            ].map(row => (
              <div
                key={row.label}
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  padding: '7px 0',
                  borderBottom: '1px solid var(--line)',
                  fontSize: 12.5,
                }}
              >
                <span style={{ color: 'var(--ink-4)' }}>{row.label}</span>
                <span style={{ display: 'flex', alignItems: 'center', gap: 5, fontWeight: 600, color: row.ok ? 'var(--ink-2)' : 'var(--ink-5)' }}>
                  {row.ok ? <CheckCircle2 size={11} color="var(--green)" /> : <AlertCircle size={11} color="var(--ink-5)" />}
                  {row.value}
                </span>
              </div>
            ))}

            <button
              className="btn btn-primary"
              style={{ width: '100%', height: 42, fontSize: 14, justifyContent: 'center', marginTop: 18 }}
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
