import { useMemo, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import {
  ArrowLeft, BarChart3, Briefcase, CheckCircle2, FileText, GraduationCap,
  Lightbulb, Scale, Sparkles, TrendingUp, UserRoundCheck, XCircle, Zap,
} from 'lucide-react'

const scoreColor = v => v >= 70 ? 'var(--green-strong)' : v >= 45 ? 'var(--amber)' : 'var(--red)'
const scoreBg = v => v >= 70 ? 'var(--green-soft)' : v >= 45 ? 'var(--amber-soft)' : 'var(--red-soft)'

const AVATAR_COLORS = [
  ['#d4875a', 'rgba(212,135,90,0.15)'],
  ['#7a9e8e', 'rgba(122,158,142,0.15)'],
  ['#fbbf24', 'rgba(251,191,36,0.13)'],
  ['#cdc9c0', 'rgba(205,201,192,0.12)'],
  ['#c97444', 'rgba(201,116,68,0.14)'],
]

const DIMENSIONS = [
  { key: 'final_score', label: 'Overall Match', icon: BarChart3, color: 'var(--accent)' },
  { key: 'skills_score', label: 'Skills', icon: Zap, color: 'var(--accent-2)' },
  { key: 'exp_score', label: 'Experience', icon: Briefcase, color: 'var(--green)' },
  { key: 'edu_score', label: 'Education', icon: GraduationCap, color: 'var(--violet)' },
  { key: 'relevance_score', label: 'Relevance', icon: BarChart3, color: 'var(--sky)' },
  { key: 'ats_score', label: 'ATS Score', icon: FileText, color: 'var(--amber)' },
]

function candidateName(candidate) {
  return (candidate?.filename || 'Candidate').replace(/\.pdf$/i, '').replace(/[-_]/g, ' ')
}

function shortName(candidate) {
  return candidateName(candidate).split(/\s+/).filter(Boolean).slice(0, 2).join(' ') || 'Candidate'
}

function getInitials(filename) {
  const clean = candidateName({ filename })
  const words = clean.trim().split(/\s+/).filter(Boolean)
  return words.length >= 2 ? (words[0][0] + words[1][0]).toUpperCase() : clean.slice(0, 2).toUpperCase()
}

function Avatar({ name, index, size = 34 }) {
  const [fg, bg] = AVATAR_COLORS[index % AVATAR_COLORS.length]
  return (
    <div style={{
      width: size, height: size, borderRadius: Math.round(size * 0.27),
      background: bg, border: `1.5px solid ${fg}40`,
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      fontSize: size * 0.3, fontWeight: 700, color: fg, flexShrink: 0,
    }}>
      {getInitials(name)}
    </div>
  )
}

function ScoreBar({ value, color, delay = '0s' }) {
  const safeValue = Math.max(0, Math.min(100, Math.round(value || 0)))
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
      <div style={{ flex: 1, height: 6, background: 'var(--bg-5)', borderRadius: 3, overflow: 'hidden' }}>
        <div className="bar-fill" style={{ height: '100%', borderRadius: 3, width: `${safeValue}%`, background: color, animationDelay: delay }} />
      </div>
      <span style={{ fontFamily: 'var(--mono)', fontSize: 12, fontWeight: 700, color, width: 38, textAlign: 'right' }}>
        {safeValue}%
      </span>
    </div>
  )
}

function topDimension(candidate) {
  const dims = [
    ['Backend fit', candidate.role_alignment_score || 0],
    ['Skill coverage', candidate.skills_score || 0],
    ['Evidence depth', candidate.relevance_score || 0],
    ['Experience', candidate.exp_score || 0],
    ['ATS quality', candidate.ats_score || 0],
  ]
  return dims.sort((a, b) => b[1] - a[1])[0]?.[0] || 'Role fit'
}

function primaryWeakness(candidate) {
  const concern = candidate.score_concerns?.[0]
  if (concern) return concern.replace(/\.$/, '')
  if ((candidate.missing_required_skills || []).length) {
    return `Missing ${candidate.missing_required_skills.slice(0, 2).join(', ')}`
  }
  if ((candidate.skills_score || 0) < 55) return 'Limited required-skill coverage'
  if ((candidate.role_alignment_score || 0) < 55) return 'Role focus mismatch'
  if ((candidate.ats_score || 0) < 55) return 'Resume structure needs work'
  return 'No major gap'
}

function recommendation(candidate) {
  if (candidate.hiring_recommendation) return candidate.hiring_recommendation
  const score = candidate.final_score || 0
  if (score >= 85) return 'Strong Hire'
  if (score >= 70) return 'Hire'
  if (score >= 55) return 'Consider'
  return 'Reject'
}

function compareValue(winner, challenger, key) {
  return Math.round((winner[key] || 0) - (challenger[key] || 0))
}

function buildPairwiseReasons(winner, challenger) {
  const reasons = []
  const dimensionWins = DIMENSIONS
    .filter(d => d.key !== 'final_score')
    .map(d => ({ ...d, gap: compareValue(winner, challenger, d.key) }))
    .filter(d => d.gap >= 5)
    .sort((a, b) => b.gap - a.gap)

  dimensionWins.slice(0, 3).forEach(d => {
    reasons.push(`${d.label}: ${shortName(winner)} leads by ${d.gap} points.`)
  })

  const winnerMissing = winner.missing_required_skills?.length || 0
  const challengerMissing = challenger.missing_required_skills?.length || 0
  if (winnerMissing < challengerMissing) {
    reasons.push(`Required skills: fewer explicit gaps (${winnerMissing} vs ${challengerMissing}).`)
  }

  if ((winner.role_alignment_score || 0) >= 70 && (challenger.role_alignment_score || 0) < 70) {
    reasons.push(`Role alignment: stronger ${winner.jd_role_family || 'target-role'} signal than ${shortName(challenger)}.`)
  }

  if (winner.confidence_level === 'High' && challenger.confidence_level !== 'High') {
    reasons.push('Evidence confidence: stronger supported evidence behind the score.')
  }

  if (winner.primary_backend_language && challenger.primary_backend_language && winner.primary_backend_language !== challenger.primary_backend_language) {
    reasons.push(`Stack fit: ${winner.primary_backend_language} appears closer to this JD than ${challenger.primary_backend_language}.`)
  }

  if (!reasons.length) {
    const gap = Math.max(0, compareValue(winner, challenger, 'final_score'))
    reasons.push(`Overall score: ${shortName(winner)} has a ${gap}-point lead after weighted evidence scoring.`)
    reasons.push('The lead is narrow, so review their project evidence before making a final call.')
  }

  return reasons.slice(0, 4)
}

function bestIdx(candidates, key) {
  return candidates.reduce((best, c, i) => (c[key] || 0) > (candidates[best][key] || 0) ? i : best, 0)
}

export default function Compare() {
  const location = useLocation()
  const navigate = useNavigate()
  const { candidates = [], scan } = location.state || {}
  const [mode, setMode] = useState('recruiter')
  const [pair, setPair] = useState(null)

  const ranked = useMemo(
    () => [...candidates].sort((a, b) => (b.final_score || 0) - (a.final_score || 0)),
    [candidates],
  )

  const activePair = pair || (ranked.length >= 2 ? { winner: ranked[0], challenger: ranked[1] } : null)

  if (!ranked.length) {
    return (
      <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '50vh' }}>
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: 15, fontWeight: 600, color: 'var(--ink-3)', marginBottom: 16 }}>
            No candidates to compare
          </div>
          <p style={{ fontSize: 13, color: 'var(--ink-5)', marginBottom: 20 }}>
            Select 2-5 candidates from a results page to compare them here.
          </p>
          <button className="btn btn-secondary" onClick={() => navigate(-1)}>
            <ArrowLeft size={14} /> Go back
          </button>
        </div>
      </div>
    )
  }

  return (
    <>
      <div className="section-hd au">
        <div>
          <div className="page-kicker"><Scale size={12} /> Decision support</div>
          <h1 className="section-title">Candidate Comparison</h1>
          <p className="section-sub">
            {scan?.role_title ? `${scan.role_title} - ` : ''}
            {ranked.length} candidates compared
          </p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
          <div style={{ display: 'flex', gap: 5, padding: 4, borderRadius: 'var(--r-md)', background: 'var(--bg-3)', border: '1px solid var(--line)' }}>
            <button className={`btn btn-sm ${mode === 'recruiter' ? 'btn-primary' : 'btn-ghost'}`} onClick={() => setMode('recruiter')}>
              <UserRoundCheck size={13} /> Recruiter
            </button>
            <button className={`btn btn-sm ${mode === 'candidate' ? 'btn-primary' : 'btn-ghost'}`} onClick={() => setMode('candidate')}>
              <Lightbulb size={13} /> Candidate
            </button>
          </div>
          <button className="btn btn-secondary" onClick={() => navigate(-1)}>
            <ArrowLeft size={14} /> Back to Results
          </button>
        </div>
      </div>

      {mode === 'recruiter' ? (
        <>
          <div className="card au au-1" style={{ overflow: 'hidden' }}>
            <div style={{ padding: '12px 20px', borderBottom: '1px solid var(--line)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12 }}>
              <div>
                <div style={{ fontFamily: 'var(--syne)', fontWeight: 700, fontSize: 13, color: 'var(--ink)' }}>Top Candidates</div>
                <div style={{ fontSize: 12, color: 'var(--ink-4)', marginTop: 2 }}>Ranked by weighted match score and evidence quality</div>
              </div>
              {activePair && (
                <span className="badge badge-accent" style={{ gap: 5 }}>
                  <Scale size={11} /> Pairwise reasoning ready
                </span>
              )}
            </div>
            <div className="table-wrap">
              <table className="tbl">
                <thead>
                  <tr>
                    <th style={{ width: 52 }}>Rank</th>
                    <th>Name</th>
                    <th style={{ textAlign: 'center' }}>Score</th>
                    <th style={{ textAlign: 'center' }}>Rec</th>
                    <th>Strength</th>
                    <th>Weakness</th>
                    <th style={{ textAlign: 'right' }}>Why</th>
                  </tr>
                </thead>
                <tbody>
                  {ranked.map((c, i) => {
                    const next = ranked[i + 1]
                    return (
                      <tr key={c.filename || i}>
                        <td style={{ fontFamily: 'var(--mono)', color: i === 0 ? 'var(--amber)' : 'var(--ink-4)', fontWeight: 700 }}>
                          #{i + 1}
                        </td>
                        <td>
                          <div style={{ display: 'flex', alignItems: 'center', gap: 9 }}>
                            <Avatar name={c.filename} index={i} />
                            <div style={{ minWidth: 0 }}>
                              <div style={{ fontWeight: 700, color: 'var(--ink)', fontSize: 13, lineHeight: 1.3 }}>
                                {candidateName(c)}
                              </div>
                              <div style={{ fontSize: 11, color: 'var(--ink-5)', marginTop: 1 }}>
                                {c.years_experience != null ? `${c.years_experience}y exp` : 'Experience unknown'}
                                {c.confidence_level ? ` - ${c.confidence_level} confidence` : ''}
                              </div>
                            </div>
                          </div>
                        </td>
                        <td style={{ textAlign: 'center' }}>
                          <span className="score-pill" style={{ background: scoreBg(c.final_score || 0), color: scoreColor(c.final_score || 0) }}>
                            {Math.round(c.final_score || 0)}%
                          </span>
                        </td>
                        <td style={{ textAlign: 'center' }}>
                          <span className={`tag ${recommendation(c).includes('Hire') ? 'tag-emerald' : recommendation(c) === 'Consider' ? 'tag-amber' : 'tag-red'}`}>
                            {recommendation(c)}
                          </span>
                        </td>
                        <td>{topDimension(c)}</td>
                        <td style={{ color: primaryWeakness(c) === 'No major gap' ? 'var(--ink-4)' : 'var(--amber)' }}>
                          {primaryWeakness(c)}
                        </td>
                        <td style={{ textAlign: 'right' }}>
                          {next ? (
                            <button className="btn btn-secondary btn-sm" onClick={() => setPair({ winner: c, challenger: next })}>
                              <Scale size={13} /> Why &gt; #{i + 2}
                            </button>
                          ) : (
                            <span style={{ fontSize: 12, color: 'var(--ink-5)' }}>-</span>
                          )}
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </div>

          {activePair && (
            <div className="card au au-2" style={{ padding: 20 }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 14, marginBottom: 14, flexWrap: 'wrap' }}>
                <div>
                  <div style={{ fontFamily: 'var(--syne)', fontWeight: 800, fontSize: 15, color: 'var(--ink)' }}>
                    Why {shortName(activePair.winner)} ranks above {shortName(activePair.challenger)}
                  </div>
                  <div style={{ fontSize: 12, color: 'var(--ink-4)', marginTop: 3 }}>
                    Pairwise reasoning from score deltas, missing skills, role fit, and confidence.
                  </div>
                </div>
                <span className="score-pill" style={{ background: 'var(--accent-soft)', color: 'var(--accent-2)', height: 28 }}>
                  +{Math.max(0, compareValue(activePair.winner, activePair.challenger, 'final_score'))} pts
                </span>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  {buildPairwiseReasons(activePair.winner, activePair.challenger).map(reason => (
                    <div key={reason} style={{ display: 'flex', gap: 9, padding: '10px 12px', borderRadius: 'var(--r-md)', background: 'var(--bg-3)', border: '1px solid var(--line)' }}>
                      <CheckCircle2 size={14} color="var(--green-strong)" style={{ flexShrink: 0, marginTop: 1 }} />
                      <span style={{ fontSize: 12.5, color: 'var(--ink-2)', lineHeight: 1.45 }}>{reason}</span>
                    </div>
                  ))}
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                  {DIMENSIONS.filter(d => d.key !== 'final_score').map(({ key, label, color }) => {
                    const gap = compareValue(activePair.winner, activePair.challenger, key)
                    return (
                      <div key={key} style={{ padding: '10px 12px', borderRadius: 'var(--r-md)', background: 'var(--bg-3)', border: '1px solid var(--line)' }}>
                        <div style={{ fontSize: 11, color: 'var(--ink-5)', marginBottom: 6 }}>{label}</div>
                        <div style={{ display: 'flex', alignItems: 'baseline', gap: 6 }}>
                          <span style={{ fontFamily: 'var(--mono)', fontSize: 18, fontWeight: 800, color: gap >= 0 ? color : 'var(--red)' }}>
                            {gap >= 0 ? '+' : ''}{gap}
                          </span>
                          <span style={{ fontSize: 11, color: 'var(--ink-5)' }}>points</span>
                        </div>
                      </div>
                    )
                  })}
                </div>
              </div>
            </div>
          )}
        </>
      ) : (
        <div className="card au au-1" style={{ padding: 20 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 9, marginBottom: 16 }}>
            <Sparkles size={16} color="var(--accent)" />
            <div>
              <div style={{ fontFamily: 'var(--syne)', fontWeight: 800, fontSize: 15, color: 'var(--ink)' }}>Candidate Mode</div>
              <div style={{ fontSize: 12, color: 'var(--ink-4)', marginTop: 2 }}>Same engine, reframed as resume improvement guidance.</div>
            </div>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: 14 }}>
            {ranked.map((c, i) => {
              const improvements = c.score_improvements?.length ? c.score_improvements : [primaryWeakness(c)]
              return (
                <div key={c.filename || i} style={{ padding: 16, borderRadius: 'var(--r-lg)', background: 'var(--bg-3)', border: '1px solid var(--line)' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 12 }}>
                    <Avatar name={c.filename} index={i} size={32} />
                    <div style={{ minWidth: 0 }}>
                      <div style={{ fontWeight: 700, color: 'var(--ink)', fontSize: 13, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {candidateName(c)}
                      </div>
                      <div style={{ fontSize: 11, color: 'var(--ink-5)', marginTop: 1 }}>{recommendation(c)} - {Math.round(c.final_score || 0)}%</div>
                    </div>
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                    {improvements.slice(0, 3).map(item => (
                      <div key={item} style={{ display: 'flex', gap: 8, color: 'var(--ink-3)', fontSize: 12.5, lineHeight: 1.45 }}>
                        <TrendingUp size={13} color="var(--sky)" style={{ flexShrink: 0, marginTop: 2 }} />
                        <span>{item}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}

      <div className="card au au-3" style={{ overflow: 'hidden' }}>
        <div style={{ padding: '12px 20px', borderBottom: '1px solid var(--line)' }}>
          <span style={{ fontFamily: 'var(--syne)', fontWeight: 700, fontSize: 13, color: 'var(--ink)' }}>
            Score Breakdown
          </span>
        </div>
        {DIMENSIONS.map(({ key, label, icon: Icon, color }) => {
          const best = bestIdx(ranked, key)
          return (
            <div key={key} style={{ borderBottom: key === 'ats_score' ? 'none' : '1px solid var(--line)' }}>
              <div style={{
                padding: '12px 20px',
                display: 'grid',
                gridTemplateColumns: '190px 1fr',
                gap: 16,
                alignItems: 'center',
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 9 }}>
                  <div style={{ width: 28, height: 28, borderRadius: 8, background: `${color}18`, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    <Icon size={13} color={color} />
                  </div>
                  <span style={{ fontWeight: 700, fontSize: 12.5, color: 'var(--ink-2)' }}>{label}</span>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: `repeat(${ranked.length}, minmax(120px, 1fr))`, gap: 14, overflowX: 'auto' }}>
                  {ranked.map((c, i) => {
                    const val = Math.round(c[key] || 0)
                    const isWinner = i === best
                    return (
                      <div key={c.filename || i} style={{ minWidth: 120 }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 7 }}>
                          <span style={{ fontSize: 11, color: 'var(--ink-4)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: 92 }}>
                            {shortName(c)}
                          </span>
                          {isWinner ? <CheckCircle2 size={12} color={color} /> : null}
                        </div>
                        <ScoreBar value={val} color={color} delay={`${i * 0.06}s`} />
                      </div>
                    )
                  })}
                </div>
              </div>
            </div>
          )
        })}
      </div>

      <div className="card au au-4" style={{ overflow: 'hidden' }}>
        <div style={{ padding: '12px 20px', borderBottom: '1px solid var(--line)' }}>
          <span style={{ fontFamily: 'var(--syne)', fontWeight: 700, fontSize: 13, color: 'var(--ink)' }}>
            Skills Matrix
          </span>
        </div>
        {(() => {
          const allSkills = [...new Set(ranked.flatMap(c => [
            ...(c.matched_skills || []),
            ...(c.missing_required_skills || []),
          ]))].sort()

          if (!allSkills.length) {
            return <div style={{ padding: '24px 20px', color: 'var(--ink-5)', fontSize: 13 }}>No skills data available</div>
          }

          return (
            <div className="table-wrap" style={{ maxHeight: 360 }}>
              <table className="tbl">
                <thead>
                  <tr>
                    <th>Skill</th>
                    {ranked.map((c, i) => (
                      <th key={c.filename || i} style={{ textAlign: 'center', maxWidth: 120 }}>
                        <div style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: 120 }}>
                          {shortName(c)}
                        </div>
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {allSkills.map(skill => (
                    <tr key={skill}>
                      <td style={{ fontWeight: 600, color: 'var(--ink-2)' }}>{skill}</td>
                      {ranked.map((c, i) => {
                        const has = (c.matched_skills || []).includes(skill)
                        return (
                          <td key={c.filename || i} style={{ textAlign: 'center' }}>
                            {has
                              ? <CheckCircle2 size={15} color="var(--green-strong)" />
                              : <XCircle size={15} color="var(--bg-5)" />
                            }
                          </td>
                        )
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )
        })()}
      </div>
    </>
  )
}
