import { useState, useEffect, useMemo, useCallback } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { getScanDetail } from '../api'
import {
  X, Search, GitCompare, CheckCircle2, XCircle,
  FileText, Zap, GraduationCap, Briefcase, Star,
  BarChart3, AlertTriangle, Clock, Users,
  ShieldCheck, Target, UserRoundCheck,
} from 'lucide-react'

// ── Helpers ───────────────────────────────────────────────────────────────────
const scoreColor = v => v >= 70 ? 'var(--green-strong)' : v >= 45 ? 'var(--amber)' : 'var(--red)'
const scoreBg    = v => v >= 70 ? 'var(--green-soft)'   : v >= 45 ? 'var(--amber-soft)' : 'var(--red-soft)'

function recommendation(candidate) {
  if (candidate.hiring_recommendation) return candidate.hiring_recommendation
  const score = candidate.final_score || 0
  if (score >= 85) return 'Strong Hire'
  if (score >= 70) return 'Hire'
  if (score >= 55) return 'Consider'
  return 'Reject'
}

function recommendationClass(label) {
  if (label.includes('Hire')) return 'tag-emerald'
  if (label === 'Consider') return 'tag-amber'
  return 'tag-red'
}

const AVATAR_COLORS = [
  ['#d4875a','rgba(212,135,90,0.15)'],
  ['#7a9e8e','rgba(122,158,142,0.15)'],
  ['#fbbf24','rgba(251,191,36,0.13)'],
  ['#cdc9c0','rgba(205,201,192,0.12)'],
  ['#c97444','rgba(201,116,68,0.14)'],
]

function getInitials(filename) {
  const clean = (filename || '').replace(/\.pdf$/i, '').replace(/[-_]/g, ' ')
  const words = clean.trim().split(/\s+/).filter(Boolean)
  return words.length >= 2
    ? (words[0][0] + words[1][0]).toUpperCase()
    : clean.slice(0, 2).toUpperCase()
}

function Avatar({ name, index, size = 30 }) {
  const [fg, bg] = AVATAR_COLORS[index % AVATAR_COLORS.length]
  return (
    <div style={{
      width:size, height:size, borderRadius: Math.round(size * 0.27),
      background:bg, border:`1px solid ${fg}40`,
      display:'flex', alignItems:'center', justifyContent:'center',
      fontSize: size * 0.33, fontWeight:700, color:fg, flexShrink:0,
    }}>
      {getInitials(name)}
    </div>
  )
}

function RankBadge({ rank }) {
  const cfg = rank === 1
    ? { bg:'linear-gradient(135deg,#f5a623,#e07820)', c:'white', shadow:'0 2px 8px rgba(245,166,35,0.45)' }
    : rank === 2 ? { bg:'linear-gradient(135deg,#adb5bd,#868e96)', c:'white' }
    : rank === 3 ? { bg:'linear-gradient(135deg,#c97024,#8b5e2a)', c:'white' }
    : { bg:'var(--bg-4)', c:'var(--ink-4)' }
  return (
    <div style={{
      width:22, height:22, borderRadius:6, flexShrink:0,
      display:'flex', alignItems:'center', justifyContent:'center',
      fontSize:10, fontWeight:700, background:cfg.bg, color:cfg.c,
      boxShadow:cfg.shadow || 'none',
    }}>{rank}</div>
  )
}

// ── Candidate Drawer ──────────────────────────────────────────────────────────
function CandidateDrawer({ candidate: c, rank, onClose }) {
  if (!c) return null

  // FIX: use the correct field names from the API response
  const matchedSkills  = c.matched_skills          || []
  const missingSkills  = c.missing_required_skills || []   // ← was c.missing_skills (wrong)
  const concerns       = c.score_concerns          || []
  const improvements   = c.score_improvements      || []
  const score          = c.final_score   || 0
  const name           = (c.filename || 'Candidate').replace(/\.pdf$/i, '').replace(/[-_]/g, ' ')

  const breakdowns = [
    { label:'Skills Match',   value: c.skills_score    || 0, icon: Zap,           color:'var(--accent)'   },
    { label:'Experience',     value: c.exp_score        || 0, icon: Briefcase,     color:'var(--green)'    },
    { label:'Education',      value: c.edu_score        || 0, icon: GraduationCap, color:'var(--violet)'   },
    { label:'Relevance',      value: c.relevance_score  || 0, icon: BarChart3,     color:'var(--sky)'      },
    { label:'ATS Score',      value: c.ats_score        || 0, icon: FileText,      color:'var(--amber)'    },
  ]

  return (
    <>
      <div className="drawer-overlay" onClick={onClose} />
      <div className="drawer">
        <div className="drawer-header">
          <Avatar name={c.filename} index={rank - 1} size={34} />
          <div style={{ flex:1, minWidth:0 }}>
            <div style={{ fontWeight:700, fontSize:14, color:'var(--ink)', overflow:'hidden', textOverflow:'ellipsis', whiteSpace:'nowrap' }}>
              {name}
            </div>
            <div style={{ fontSize:12, color:'var(--ink-4)', display:'flex', alignItems:'center', gap:6, marginTop:1 }}>
              <span>Rank #{rank}</span>
              {c.years_experience != null && (
                <><span style={{ color:'var(--line-3)' }}>·</span><span>{c.years_experience}y exp</span></>
              )}
              {c.degree && c.degree !== 'None' && (
                <><span style={{ color:'var(--line-3)' }}>·</span><span>{c.degree}</span></>
              )}
            </div>
          </div>
          <div style={{ display:'flex', alignItems:'center', gap:8 }}>
            <span className="score-pill" style={{ background:scoreBg(score), color:scoreColor(score), fontSize:14, height:26 }}>
              {score}%
            </span>
            <button className="btn btn-ghost btn-sm btn-icon" onClick={onClose}>
              <X size={16} />
            </button>
          </div>
        </div>

        <div className="drawer-body">
          {/* Requirement flags */}
          {(c.meets_min_experience != null || c.meets_degree_req != null) && (
            <div style={{ display:'flex', gap:8, flexWrap:'wrap' }}>
              {c.meets_min_experience != null && (
                <span className={`badge ${c.meets_min_experience ? 'badge-success' : 'badge-amber'}`}
                  style={{ gap:5 }}>
                  {c.meets_min_experience ? <CheckCircle2 size={10} /> : <AlertTriangle size={10} />}
                  {c.meets_min_experience ? 'Meets exp. req.' : 'Below min. experience'}
                </span>
              )}
              {c.meets_degree_req != null && (
                <span className={`badge ${c.meets_degree_req ? 'badge-success' : 'badge-amber'}`}
                  style={{ gap:5 }}>
                  {c.meets_degree_req ? <CheckCircle2 size={10} /> : <AlertTriangle size={10} />}
                  {c.meets_degree_req ? 'Meets degree req.' : 'Below required degree'}
                </span>
              )}
            </div>
          )}

          {/* Score breakdown */}
          <div>
            <div style={{ fontSize:11, fontWeight:700, color:'var(--ink-5)', letterSpacing:'0.08em', textTransform:'uppercase', marginBottom:10 }}>
              Score Breakdown
            </div>
            <div style={{ display:'flex', flexDirection:'column', gap:8 }}>
              {breakdowns.map(b => (
                <div key={b.label} style={{
                  display:'flex', alignItems:'center', gap:10,
                  padding:'10px 14px', borderRadius:'var(--r-md)',
                  background:'var(--bg-3)', border:'1px solid var(--line)',
                }}>
                  <div style={{
                    width:28, height:28, borderRadius:8,
                    background:`${b.color}18`,
                    display:'flex', alignItems:'center', justifyContent:'center', flexShrink:0,
                  }}>
                    <b.icon size={13} color={b.color} />
                  </div>
                  <div style={{ flex:1 }}>
                    <div style={{ display:'flex', justifyContent:'space-between', marginBottom:5 }}>
                      <span style={{ fontSize:12, fontWeight:600, color:'var(--ink-3)' }}>{b.label}</span>
                      <span style={{ fontSize:12, fontFamily:'var(--mono)', fontWeight:700, color:b.color }}>{b.value}%</span>
                    </div>
                    <div style={{ height:4, background:'var(--bg-5)', borderRadius:2, overflow:'hidden' }}>
                      <div className="bar-fill" style={{ width:`${b.value}%`, height:'100%', background:b.color, borderRadius:2 }} />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {(c.ai_overview || c.score_summary || concerns.length > 0 || improvements.length > 0) && (
            <div>
              <div style={{ fontSize:11, fontWeight:700, color:'var(--ink-5)', letterSpacing:'0.08em', textTransform:'uppercase', marginBottom:10 }}>
                Score Explanation
              </div>
              <div style={{
                display:'flex', flexDirection:'column', gap:10,
                padding:'12px 14px', borderRadius:'var(--r-md)',
                background:'var(--bg-3)', border:'1px solid var(--line)',
              }}>
                {c.ai_overview && (
                  <div style={{ display:'flex', flexDirection:'column', gap:5 }}>
                    <div style={{ fontSize:11.5, fontWeight:700, color:'var(--accent-2)' }}>AI Overview</div>
                    <div style={{ fontSize:12.5, lineHeight:1.55, color:'var(--ink-2)' }}>
                      {c.ai_overview}
                    </div>
                  </div>
                )}
                {c.score_summary && (
                  <div style={{ fontSize:12.5, lineHeight:1.55, color:'var(--ink-3)' }}>
                    {c.score_summary}
                  </div>
                )}
                {(c.hiring_recommendation || c.confidence_level) && (
                  <div style={{ display:'flex', flexWrap:'wrap', gap:6 }}>
                    {c.hiring_recommendation && (
                      <span className="tag tag-emerald" style={{ fontSize:10.5 }}>
                        {c.hiring_recommendation}
                      </span>
                    )}
                    {c.confidence_level && (
                      <span className="tag tag-neutral" style={{ fontSize:10.5 }}>
                        Confidence: {c.confidence_level}
                      </span>
                    )}
                  </div>
                )}
                {(c.primary_backend_language || c.jd_primary_backend_language) && (
                  <div style={{ display:'flex', flexWrap:'wrap', gap:6 }}>
                    {c.primary_backend_language && (
                      <span className="tag tag-neutral" style={{ fontSize:10.5 }}>
                        Candidate stack: {c.primary_backend_language}
                      </span>
                    )}
                    {c.jd_primary_backend_language && (
                      <span className="tag tag-neutral" style={{ fontSize:10.5 }}>
                        JD stack: {c.jd_primary_backend_language}
                      </span>
                    )}
                  </div>
                )}
                {(c.semantic_overlap_score != null || c.role_alignment_score != null) && (
                  <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:8 }}>
                    {c.semantic_overlap_score != null && (
                      <div style={{ padding:'8px 10px', borderRadius:'var(--r-sm)', background:'var(--bg-4)', border:'1px solid var(--line)' }}>
                        <div style={{ fontSize:10.5, color:'var(--ink-5)', marginBottom:3 }}>Semantic overlap</div>
                        <div style={{ fontSize:12, fontWeight:700, color:'var(--sky)' }}>{c.semantic_overlap_score}%</div>
                      </div>
                    )}
                    {c.role_alignment_score != null && (
                      <div style={{ padding:'8px 10px', borderRadius:'var(--r-sm)', background:'var(--bg-4)', border:'1px solid var(--line)' }}>
                        <div style={{ fontSize:10.5, color:'var(--ink-5)', marginBottom:3 }}>Role alignment</div>
                        <div style={{ fontSize:12, fontWeight:700, color:'var(--green)' }}>{c.role_alignment_score}%</div>
                      </div>
                    )}
                  </div>
                )}
                {concerns.length > 0 && (
                  <div style={{ display:'flex', flexDirection:'column', gap:5 }}>
                    <div style={{ fontSize:11.5, fontWeight:700, color:'var(--amber)' }}>Watchouts</div>
                    {concerns.map(item => (
                      <div key={item} style={{ fontSize:12, color:'var(--ink-4)', lineHeight:1.45 }}>
                        {item}
                      </div>
                    ))}
                  </div>
                )}
                {improvements.length > 0 && (
                  <div style={{ display:'flex', flexDirection:'column', gap:5 }}>
                    <div style={{ fontSize:11.5, fontWeight:700, color:'var(--sky)' }}>Improve Score</div>
                    {improvements.map(item => (
                      <div key={item} style={{ fontSize:12, color:'var(--ink-4)', lineHeight:1.45 }}>
                        {item}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Matched skills */}
          {matchedSkills.length > 0 && (
            <div>
              <div style={{ fontSize:11, fontWeight:700, color:'var(--ink-5)', letterSpacing:'0.08em', textTransform:'uppercase', marginBottom:10 }}>
                Matched Skills ({matchedSkills.length})
              </div>
              <div style={{ display:'flex', flexWrap:'wrap', gap:6 }}>
                {matchedSkills.map(s => (
                  <span key={s} style={{
                    display:'inline-flex', alignItems:'center', gap:4,
                    padding:'3px 9px', borderRadius:'var(--r-full)',
                    background:'var(--green-dim)', color:'var(--green-strong)',
                    fontSize:11.5, fontWeight:600,
                  }}>
                    <CheckCircle2 size={10} />{s}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Missing skills */}
          {missingSkills.length > 0 && (
            <div>
              <div style={{ fontSize:11, fontWeight:700, color:'var(--ink-5)', letterSpacing:'0.08em', textTransform:'uppercase', marginBottom:10 }}>
                Missing Required Skills ({missingSkills.length})
              </div>
              <div style={{ display:'flex', flexWrap:'wrap', gap:6 }}>
                {missingSkills.map(s => (
                  <span key={s} style={{
                    display:'inline-flex', alignItems:'center', gap:4,
                    padding:'3px 9px', borderRadius:'var(--r-full)',
                    background:'var(--red-dim)', color:'var(--red)',
                    fontSize:11.5, fontWeight:600,
                  }}>
                    <XCircle size={10} />{s}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </>
  )
}

// ── Results Page ──────────────────────────────────────────────────────────────
export default function Results({ results: propResults, onShowToast }) {
  const [loading, setLoading]       = useState(false)
  const [data, setData]             = useState(propResults)
  const [selected, setSelected]     = useState(null)
  const [selectedIds, setSelectedIds] = useState([])
  const [search, setSearch]         = useState('')
  const [sortBy, setSortBy]         = useState('score')

  const navigate = useNavigate()
  const { id }   = useParams()

  // FIX: if navigating directly to /results/:id, always fetch from API
  useEffect(() => {
    if (id) {
      fetchDetail(id)
    } else if (!propResults) {
      navigate('/scan', { replace: true })
    }
  }, [id])

  const fetchDetail = useCallback(async scanId => {
    setLoading(true)
    try {
      const res = await getScanDetail(scanId)
      setData(res)
    } catch {
      onShowToast?.('Failed to load scan', 'error')
      navigate('/history')
    } finally {
      setLoading(false)
    }
  }, [])

  const candidates = useMemo(() => data?.results || [], [data])

  const filtered = useMemo(() => {
    const q = search.toLowerCase()
    return candidates
      .filter(c =>
        (c.filename || '').toLowerCase().includes(q) ||
        (c.matched_skills || []).join(' ').toLowerCase().includes(q)
      )
      .sort((a, b) => {
        if (sortBy === 'score') {
          if (b.final_score !== a.final_score) return b.final_score - a.final_score
          return b.skills_score - a.skills_score  // tie breaker: sort by skills_score
        } else if (sortBy === 'ats') {
          return b.ats_score - a.ats_score
        } else {
          return (b.years_experience || 0) - (a.years_experience || 0)
        }
      })
  }, [candidates, search, sortBy])

  const toggleId = (e, id) => {
    e.stopPropagation()
    setSelectedIds(p => p.includes(id) ? p.filter(x => x !== id) : [...p, id])
  }

  if (loading) return (
    <div style={{ display:'flex', alignItems:'center', justifyContent:'center', flex:1, minHeight:'50vh' }}>
      <div style={{ textAlign:'center' }}>
        <div className="loader-ring" style={{ margin:'0 auto 14px' }} />
        <p style={{ fontSize:13, color:'var(--ink-4)' }}>Loading results…</p>
      </div>
    </div>
  )

  if (!data) return null

  const processingSeconds = data.processing_time_ms ? (data.processing_time_ms / 1000).toFixed(1) : null
  const topCandidate = candidates.reduce((best, c) => (c.final_score || 0) > (best?.final_score || 0) ? c : best, null)
  const hireCount = candidates.filter(c => recommendation(c).includes('Hire')).length
  const highConfidence = candidates.filter(c => c.confidence_level === 'High').length
  const avgScore = candidates.length
    ? Math.round(candidates.reduce((sum, c) => sum + (c.final_score || 0), 0) / candidates.length)
    : 0

  return (
    <>
      {/* Header */}
      <div className="section-hd au">
        <div>
          <h1 className="section-title">{data.role_title || 'Scan Results'}</h1>
          <p className="section-sub" style={{ display:'flex', alignItems:'center', gap:10 }}>
            <span style={{ display:'flex', alignItems:'center', gap:4 }}>
              <Users size={12} />{candidates.length} candidate{candidates.length !== 1 ? 's' : ''} ranked
            </span>
            {processingSeconds && (
              <span style={{ display:'flex', alignItems:'center', gap:4, color:'var(--ink-5)' }}>
                <Clock size={11} />{processingSeconds}s
              </span>
            )}
          </p>
        </div>
        {selectedIds.length >= 2 && (
          <button
            className="btn btn-secondary"
            onClick={() => {
              const sel = candidates.filter(c => selectedIds.includes(c.filename))
              navigate('/compare', { state: { candidates: sel, scan: data } })
            }}
          >
            <GitCompare size={14} />
            Compare {selectedIds.length}
          </button>
        )}
      </div>

      <div className="results-summary-grid au au-1">
        <div className="summary-tile">
          <div className="summary-tile-label"><UserRoundCheck size={12} /> Recommended</div>
          <div className="summary-tile-value">{hireCount}</div>
        </div>
        <div className="summary-tile">
          <div className="summary-tile-label"><Target size={12} /> Average Match</div>
          <div className="summary-tile-value">{avgScore}%</div>
        </div>
        <div className="summary-tile">
          <div className="summary-tile-label"><ShieldCheck size={12} /> High Confidence</div>
          <div className="summary-tile-value">{highConfidence}</div>
        </div>
        <div className="summary-tile">
          <div className="summary-tile-label"><Star size={12} /> Best Candidate</div>
          <div className="summary-tile-value" style={{ fontSize:18, overflow:'hidden', textOverflow:'ellipsis', whiteSpace:'nowrap' }}>
            {topCandidate ? getInitials(topCandidate.filename) : '-'}
          </div>
        </div>
      </div>

      {/* Filter strip */}
      <div className="card au au-1" style={{ padding:'10px 14px', display:'flex', alignItems:'center', gap:10 }}>
        <div style={{ position:'relative', flex:1, maxWidth:300 }}>
          <Search size={13} style={{ position:'absolute', left:10, top:'50%', transform:'translateY(-50%)', color:'var(--ink-5)' }} />
          <input
            className="input-base"
            placeholder="Search by name or skill…"
            style={{ paddingLeft:32, height:32, fontSize:13 }}
            value={search}
            onChange={e => setSearch(e.target.value)}
          />
        </div>
        <div style={{ display:'flex', gap:5 }}>
          {[['score','Match'],['ats','ATS'],['experience','Exp']].map(([k, l]) => (
            <button
              key={k}
              className={`btn btn-sm ${sortBy === k ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => setSortBy(k)}
              style={{ fontSize:12 }}
            >
              {l}
            </button>
          ))}
        </div>
        <div style={{ marginLeft:'auto', fontSize:12, color:'var(--ink-5)', fontFamily:'var(--mono)' }}>
          {filtered.length} / {candidates.length}
        </div>
      </div>

      {/* Table */}
      <div className="card au au-2" style={{ overflow:'hidden', flex:1 }}>
        <div className="table-wrap" style={{ maxHeight:'calc(100vh - 300px)' }}>
          <table className="tbl">
            <thead>
              <tr>
                <th style={{ width:36 }}></th>
                <th style={{ width:36 }}>#</th>
                <th>Candidate</th>
                <th style={{ textAlign:'center' }}>Match</th>
                <th style={{ textAlign:'center' }}>Decision</th>
                <th style={{ textAlign:'center' }}>Confidence</th>
                <th style={{ textAlign:'center' }}>ATS</th>
                <th style={{ textAlign:'center' }}>Skills</th>
                <th style={{ textAlign:'center' }}>Experience</th>
                <th style={{ textAlign:'center' }}>Education</th>
                <th>Matched Skills</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((c, i) => {
                const rank      = i + 1
                const isChecked = selectedIds.includes(c.filename)
                return (
                  <tr
                    key={c.filename || i}
                    className={`au${isChecked ? ' selected' : ''}`}
                    style={{ cursor:'pointer', animationDelay:`${i * 0.03}s` }}
                    onClick={() => setSelected({ candidate: c, rank })}
                  >
                    <td onClick={e => toggleId(e, c.filename)} style={{ padding:'11px 8px 11px 14px' }}>
                      <div className={`checkbox${isChecked ? ' checked' : ''}`}>
                        {isChecked && <svg width="10" height="8" viewBox="0 0 10 8"><path d="M1 4l2.5 3L9 1" stroke="white" strokeWidth="1.8" fill="none" strokeLinecap="round" strokeLinejoin="round"/></svg>}
                      </div>
                    </td>
                    <td><RankBadge rank={rank} /></td>
                    <td>
                      <div style={{ display:'flex', alignItems:'center', gap:9 }}>
                        <Avatar name={c.filename} index={i} />
                        <div>
                          <div style={{ fontWeight:600, color:'var(--ink)', fontSize:13, lineHeight:1.3 }}>
                            {(c.filename || 'Unknown').replace(/\.pdf$/i, '').replace(/[-_]/g, ' ')}
                          </div>
                          {c.years_experience != null && (
                            <div style={{ fontSize:11, color:'var(--ink-5)', marginTop:1 }}>
                              {c.years_experience}y exp{c.degree && c.degree !== 'None' ? ` · ${c.degree}` : ''}
                            </div>
                          )}
                        </div>
                      </div>
                    </td>
                    <td style={{ textAlign:'center' }}>
                      <span className="score-pill score-pill-strong" style={{ background:scoreBg(c.final_score||0), color:scoreColor(c.final_score||0) }}>
                        {c.final_score||0}%
                      </span>
                    </td>
                    <td style={{ textAlign:'center' }}>
                      <span className={`tag ${recommendationClass(recommendation(c))}`}>
                        {recommendation(c)}
                      </span>
                    </td>
                    <td style={{ textAlign:'center' }}>
                      <span className="tag tag-neutral">
                        {c.confidence_level || 'Medium'}
                      </span>
                    </td>
                    <td style={{ textAlign:'center' }}>
                      <span className="score-pill" style={{ background:scoreBg(c.ats_score||0), color:scoreColor(c.ats_score||0) }}>
                        {c.ats_score||0}%
                      </span>
                    </td>
                    <td style={{ textAlign:'center' }}>
                      <span className="score-pill" style={{ background:scoreBg(c.skills_score||0), color:scoreColor(c.skills_score||0) }}>
                        {c.skills_score||0}%
                      </span>
                    </td>
                    <td style={{ textAlign:'center' }}>
                      <span className="score-pill" style={{ background:scoreBg(c.exp_score||0), color:scoreColor(c.exp_score||0) }}>
                        {c.exp_score||0}%
                      </span>
                    </td>
                    <td style={{ textAlign:'center' }}>
                      <span className="score-pill" style={{ background:scoreBg(c.edu_score||0), color:scoreColor(c.edu_score||0) }}>
                        {c.edu_score||0}%
                      </span>
                    </td>
                    <td>
                      <div style={{ display:'flex', flexWrap:'wrap', gap:4, maxWidth:260 }}>
                        {(c.matched_skills || []).slice(0, 4).map(s => (
                          <span key={s} className="tag tag-emerald" style={{ fontSize:10.5 }}>{s}</span>
                        ))}
                        {(c.matched_skills || []).length > 4 && (
                          <span className="tag tag-neutral" style={{ fontSize:10.5 }}>
                            +{c.matched_skills.length - 4}
                          </span>
                        )}
                      </div>
                    </td>
                  </tr>
                )
              })}

              {filtered.length === 0 && (
                <tr>
                  <td colSpan={11} style={{ textAlign:'center', padding:'48px 0', color:'var(--ink-5)' }}>
                    No candidates match your search
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {selected && (
        <CandidateDrawer
          candidate={selected.candidate}
          rank={selected.rank}
          onClose={() => setSelected(null)}
        />
      )}
    </>
  )
}
