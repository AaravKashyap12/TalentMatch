import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { listScans } from '../api'
import {
  Plus, History, Users, Activity, TrendingUp, ArrowRight, Clock,
  Sparkles, ChevronRight, CheckCircle2, AlertTriangle, Target,
} from 'lucide-react'

const scoreColor = v => v >= 70 ? 'var(--green-strong)' : v >= 45 ? 'var(--amber)' : 'var(--red)'
const scoreBg = v => v >= 70 ? 'var(--green-soft)' : v >= 45 ? 'var(--amber-soft)' : 'var(--red-soft)'

function MetricCard({ label, value, icon: Icon, color, delay }) {
  return (
    <div className="card metric-card au card-hoverable" style={{ animationDelay: delay }}>
      <div className="metric-card-accent" style={{ background: color }} />
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14 }}>
        <span style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.07em', textTransform: 'uppercase', color: 'var(--ink-4)' }}>
          {label}
        </span>
        <div style={{ width: 30, height: 30, borderRadius: 8, background: `${color}18`, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <Icon size={14} color={color} />
        </div>
      </div>
      <div style={{ fontFamily: 'var(--mono)', fontSize: 26, fontWeight: 700, color: 'var(--ink)', lineHeight: 1 }}>
        {value}
      </div>
    </div>
  )
}

function EmptyState({ onStart }) {
  return (
    <div className="empty-premium">
      <div style={{
        width: 52, height: 52, borderRadius: 14,
        background: 'var(--accent-soft)', border: '1px solid var(--accent-mid)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        margin: '0 auto 16px',
      }}>
        <Sparkles size={22} color="var(--accent)" />
      </div>
      <h3 style={{ fontFamily: 'var(--syne)', fontSize: 16, fontWeight: 700, marginBottom: 8 }}>No scans yet</h3>
      <p style={{ fontSize: 13.5, color: 'var(--ink-4)', margin: '0 auto 24px', maxWidth: 340, lineHeight: 1.55 }}>
        Upload a resume batch and TalentMatch will build a ranked candidate slate.
      </p>
      <button className="btn btn-primary" onClick={onStart}>
        <Plus size={15} />
        Create First Scan
      </button>
    </div>
  )
}

export default function Dashboard({ onShowToast }) {
  const navigate = useNavigate()
  const [scans, setScans] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => { fetchScans() }, [])

  async function fetchScans() {
    try {
      const data = await listScans()
      setScans(data)
    } catch {
      onShowToast?.('Could not load dashboard data', 'error')
    } finally {
      setLoading(false)
    }
  }

  const totalScans = scans.length
  const totalCandidates = scans.reduce((a, s) => a + (s.total_candidates || 0), 0)
  const avgMatch = totalScans > 0 ? (scans.reduce((a, s) => a + (s.avg_score || 0), 0) / totalScans).toFixed(1) : '-'
  const topMatch = totalScans > 0 ? Math.max(...scans.map(s => s.top_score || 0)) : '-'
  const hireReady = scans.filter(s => (s.top_score || 0) >= 70).length
  const needsReview = scans.filter(s => (s.top_score || 0) > 0 && (s.top_score || 0) < 70).length

  const metrics = [
    { label: 'Total Scans', value: totalScans, icon: History, color: 'var(--accent)', delay: '0s' },
    { label: 'Candidates', value: totalCandidates, icon: Users, color: 'var(--green)', delay: '0.06s' },
    { label: 'Avg Match Score', value: avgMatch === '-' ? '-' : `${avgMatch}%`, icon: Activity, color: 'var(--amber)', delay: '0.12s' },
    { label: 'Top Candidate', value: topMatch === '-' ? '-' : `${topMatch}%`, icon: TrendingUp, color: 'var(--violet)', delay: '0.18s' },
  ]

  const recent = scans.slice(0, 8).map(s => ({
    id: s.scan_id,
    role: s.role_title || 'Untitled',
    date: new Date(s.created_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' }),
    count: s.total_candidates || 0,
    top: s.top_score || 0,
    avg: s.avg_score || 0,
  }))

  return (
    <>
      <div className="section-hd au">
        <div>
          <div className="page-kicker"><Target size={12} /> Hiring intelligence</div>
          <h1 className="section-title">Dashboard</h1>
          <p className="section-sub">Pipeline health, shortlist signal, and recent screening decisions</p>
        </div>
        <button className="btn btn-primary" onClick={() => navigate('/scan')}>
          <Plus size={15} strokeWidth={2.5} />
          New Scan
        </button>
      </div>

      {loading ? (
        <div className="metrics-grid">
          {[1, 2, 3, 4].map(i => (
            <div key={i} className="card metric-card">
              <div className="skeleton" style={{ width: '55%', height: 10, marginBottom: 14 }} />
              <div className="skeleton" style={{ width: '40%', height: 26 }} />
            </div>
          ))}
        </div>
      ) : (
        <div className="metrics-grid">
          {metrics.map(m => <MetricCard key={m.label} {...m} />)}
        </div>
      )}

      <div className="dashboard-grid">
        <div className="card au au-2" style={{ overflow: 'hidden' }}>
          <div style={{
            padding: '16px 20px', borderBottom: '1px solid var(--line)',
            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          }}>
            <div>
              <div className="panel-title">Recent Scans</div>
              <div style={{ fontSize: 12, color: 'var(--ink-4)', marginTop: 1 }}>
                {loading ? '...' : `${scans.length} total assessment${scans.length !== 1 ? 's' : ''}`}
              </div>
            </div>
            {scans.length > 0 && (
              <button
                className="btn btn-ghost btn-sm"
                onClick={() => navigate('/history')}
                style={{ gap: 4, color: 'var(--accent-2)', fontWeight: 600 }}
              >
                View all <ChevronRight size={13} />
              </button>
            )}
          </div>

          {loading ? (
            <div style={{ padding: 20, display: 'flex', flexDirection: 'column', gap: 12 }}>
              {[1, 2, 3, 4].map(i => (
                <div key={i} style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
                  <div className="skeleton" style={{ width: 32, height: 32, borderRadius: 8 }} />
                  <div style={{ flex: 1 }}>
                    <div className="skeleton" style={{ width: '40%', height: 11, marginBottom: 6 }} />
                    <div className="skeleton" style={{ width: '25%', height: 9 }} />
                  </div>
                  <div className="skeleton" style={{ width: 48, height: 22, borderRadius: 99 }} />
                </div>
              ))}
            </div>
          ) : recent.length === 0 ? (
            <div style={{ padding: 32 }}>
              <EmptyState onStart={() => navigate('/scan')} />
            </div>
          ) : (
            <div className="table-wrap">
              <table className="tbl">
                <thead>
                  <tr>
                    <th><div style={{ display: 'flex', alignItems: 'center', gap: 5 }}><Clock size={11} />Date</div></th>
                    <th>Role Title</th>
                    <th style={{ textAlign: 'center' }}>Candidates</th>
                    <th style={{ textAlign: 'center' }}>Top Score</th>
                    <th style={{ textAlign: 'center' }}>Avg Score</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {recent.map((s, i) => (
                    <tr
                      key={s.id}
                      className="au"
                      style={{ cursor: 'pointer', animationDelay: `${i * 0.04}s` }}
                      onClick={() => navigate(`/results/${s.id}`)}
                    >
                      <td><span style={{ fontSize: 12, color: 'var(--ink-3)', fontFamily: 'var(--mono)' }}>{s.date}</span></td>
                      <td><div style={{ fontWeight: 600, color: 'var(--ink)', fontSize: 13.5 }}>{s.role}</div></td>
                      <td style={{ textAlign: 'center' }}>
                        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4, fontSize: 12.5, color: 'var(--ink-3)', fontFamily: 'var(--mono)' }}>
                          <Users size={11} color="var(--ink-5)" />{s.count}
                        </span>
                      </td>
                      <td style={{ textAlign: 'center' }}>
                        <span className="score-pill" style={{ background: scoreBg(s.top), color: scoreColor(s.top) }}>{s.top}%</span>
                      </td>
                      <td style={{ textAlign: 'center' }}>
                        <span className="score-pill" style={{ background: scoreBg(s.avg), color: scoreColor(s.avg) }}>{s.avg}%</span>
                      </td>
                      <td>
                        <button
                          className="btn btn-ghost btn-sm btn-icon"
                          onClick={e => { e.stopPropagation(); navigate(`/results/${s.id}`) }}
                          style={{ color: 'var(--accent-2)' }}
                        >
                          <ArrowRight size={14} />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        <aside className="panel-stack sticky-actions au au-3">
          <div className="decision-card">
            <div className="panel-title">Decision Queue</div>
            <p className="panel-copy">Shortlist momentum from the latest assessments.</p>
            <div style={{ marginTop: 14 }}>
              <div className="decision-row">
                <span style={{ display: 'flex', alignItems: 'center', gap: 8, color: 'var(--ink-3)', fontSize: 12.5 }}>
                  <CheckCircle2 size={14} color="var(--green-strong)" /> Hire-ready scans
                </span>
                <span className="score-pill" style={{ background: 'var(--green-soft)', color: 'var(--green-strong)' }}>{hireReady}</span>
              </div>
              <div className="decision-row">
                <span style={{ display: 'flex', alignItems: 'center', gap: 8, color: 'var(--ink-3)', fontSize: 12.5 }}>
                  <AlertTriangle size={14} color="var(--amber)" /> Needs review
                </span>
                <span className="score-pill" style={{ background: 'var(--amber-soft)', color: 'var(--amber)' }}>{needsReview}</span>
              </div>
              <div className="decision-row">
                <span style={{ color: 'var(--ink-4)', fontSize: 12.5 }}>Best current signal</span>
                <span style={{ fontFamily: 'var(--mono)', color: scoreColor(topMatch === '-' ? 0 : topMatch), fontWeight: 800 }}>
                  {topMatch === '-' ? '-' : `${topMatch}%`}
                </span>
              </div>
            </div>
          </div>
          <div className="card panel-pad">
            <div className="panel-title">Next Best Action</div>
            <div className="insight-list" style={{ marginTop: 12 }}>
              <div className="insight-item">
                <Sparkles size={14} color="var(--accent-2)" style={{ flexShrink: 0, marginTop: 1 }} />
                {totalScans ? 'Open the strongest recent scan and compare the top candidates side by side.' : 'Create a scan to start building a ranked hiring slate.'}
              </div>
              <div className="insight-item">
                <Target size={14} color="var(--green-strong)" style={{ flexShrink: 0, marginTop: 1 }} />
                Tune required skills per role to keep missing-required logic strict and trustworthy.
              </div>
            </div>
          </div>
        </aside>
      </div>
    </>
  )
}
