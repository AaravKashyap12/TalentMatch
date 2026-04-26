import { useEffect, useMemo, useState } from 'react'
import {
  Activity, BarChart3, CheckCircle2, Clock, Database, EyeOff, KeyRound,
  Lock, RefreshCw, ShieldCheck, Users, Zap,
} from 'lucide-react'
import { getAdminAnalytics } from '../api'

const SECRET_KEY = 'tm-admin-secret'

const fmt = n => Number(n || 0).toLocaleString()
const pct = n => `${Number(n || 0).toFixed(1)}%`
const ms = n => `${Math.round(Number(n || 0)).toLocaleString()} ms`

function shortDate(value) {
  return new Date(value).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
}

function fullDate(value) {
  return new Date(value).toLocaleString(undefined, {
    month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
  })
}

function MetricTile({ label, value, sub, icon: Icon, color }) {
  return (
    <div className="card metric-card card-hoverable">
      <div className="metric-card-accent" style={{ background: color }} />
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, marginBottom: 14 }}>
        <span style={{ fontSize: 11, fontWeight: 800, letterSpacing: '0.07em', textTransform: 'uppercase', color: 'var(--ink-4)' }}>
          {label}
        </span>
        <div className="admin-icon" style={{ background: `${color}1f`, color }}>
          <Icon size={15} />
        </div>
      </div>
      <div style={{ fontFamily: 'var(--mono)', fontSize: 25, lineHeight: 1, color: 'var(--ink)', fontWeight: 800 }}>
        {value}
      </div>
      {sub && <div style={{ marginTop: 8, color: 'var(--ink-4)', fontSize: 12 }}>{sub}</div>}
    </div>
  )
}

function ProgressRow({ label, value, max, color = 'var(--accent)' }) {
  const width = max > 0 ? Math.max(4, Math.min((value / max) * 100, 100)) : 0
  return (
    <div className="admin-progress-row">
      <div className="admin-progress-meta">
        <span>{label}</span>
        <strong>{fmt(value)}</strong>
      </div>
      <div className="admin-progress-track">
        <span style={{ width: `${width}%`, background: color }} />
      </div>
    </div>
  )
}

function SecretGate({ secret, setSecret, onUnlock, loading, error }) {
  return (
    <div className="admin-gate">
      <div className="card admin-gate-card au">
        <div className="admin-gate-icon">
          <Lock size={20} />
        </div>
        <div>
          <div className="page-kicker"><ShieldCheck size={12} /> Developer access</div>
          <h1 className="section-title">Admin analytics</h1>
          <p className="section-sub">
            Enter your backend <code className="inline-code">ADMIN_SECRET</code> to view platform usage, scan quality, and account limits.
          </p>
        </div>

        <form
          className="admin-secret-form"
          onSubmit={e => {
            e.preventDefault()
            onUnlock()
          }}
        >
          <label>
            <span className="input-label">Admin secret</span>
            <input
              className="input-base"
              type="password"
              value={secret}
              autoComplete="off"
              placeholder="Paste ADMIN_SECRET"
              onChange={e => setSecret(e.target.value)}
            />
          </label>
          {error && <div className="admin-error">{error}</div>}
          <button className="btn btn-primary btn-lg" type="submit" disabled={loading || !secret.trim()}>
            {loading ? <RefreshCw size={15} className="spin" /> : <KeyRound size={15} />}
            Unlock Dashboard
          </button>
        </form>
      </div>
    </div>
  )
}

export default function AdminDashboard({ onShowToast }) {
  const [secret, setSecret] = useState(() => sessionStorage.getItem(SECRET_KEY) || '')
  const [unlocked, setUnlocked] = useState(() => Boolean(sessionStorage.getItem(SECRET_KEY)))
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const maxTrend = useMemo(() => {
    if (!data?.trend?.length) return 0
    return Math.max(...data.trend.map(point => point.scans || 0), 1)
  }, [data])

  const maxScoreBucket = useMemo(() => {
    if (!data?.score_buckets?.length) return 0
    return Math.max(...data.score_buckets.map(bucket => bucket.count || 0), 1)
  }, [data])

  const maxRecommendation = useMemo(() => {
    if (!data?.recommendation_breakdown?.length) return 0
    return Math.max(...data.recommendation_breakdown.map(item => item.count || 0), 1)
  }, [data])

  useEffect(() => {
    if (unlocked && secret) loadAnalytics(secret)
  }, [unlocked])

  async function loadAnalytics(nextSecret = secret) {
    setLoading(true)
    setError('')
    try {
      const analytics = await getAdminAnalytics(nextSecret.trim())
      sessionStorage.setItem(SECRET_KEY, nextSecret.trim())
      setData(analytics)
      setUnlocked(true)
    } catch (err) {
      setError(err.message)
      onShowToast?.(err.message, 'error')
      setUnlocked(false)
      sessionStorage.removeItem(SECRET_KEY)
    } finally {
      setLoading(false)
    }
  }

  function lockDashboard() {
    sessionStorage.removeItem(SECRET_KEY)
    setSecret('')
    setData(null)
    setUnlocked(false)
    setError('')
  }

  if (!unlocked || !data) {
    return (
      <SecretGate
        secret={secret}
        setSecret={setSecret}
        onUnlock={() => loadAnalytics(secret)}
        loading={loading}
        error={error}
      />
    )
  }

  const m = data.metrics

  return (
    <>
      <div className="section-hd au">
        <div>
          <div className="page-kicker"><Database size={12} /> Backend analytics</div>
          <h1 className="section-title">Developer Dashboard</h1>
          <p className="section-sub">
            Platform usage, scan quality, quota pressure, and recent assessment health.
          </p>
        </div>
        <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
          <button className="btn btn-secondary" onClick={() => loadAnalytics()} disabled={loading}>
            <RefreshCw size={15} className={loading ? 'spin' : ''} />
            Refresh
          </button>
          <button className="btn btn-secondary" onClick={lockDashboard}>
            <EyeOff size={15} />
            Lock
          </button>
        </div>
      </div>

      <div className="metrics-grid">
        <MetricTile label="Users" value={fmt(m.total_users)} sub={`${fmt(m.active_users)} active`} icon={Users} color="var(--accent)" />
        <MetricTile label="Scans" value={fmt(m.total_scans)} sub={`${fmt(m.scans_today)} today`} icon={Activity} color="var(--green)" />
        <MetricTile label="Candidates" value={fmt(m.total_candidates)} sub={`${fmt(m.candidates_today)} today`} icon={BarChart3} color="var(--blue)" />
        <MetricTile label="Avg Score" value={pct(m.avg_score)} sub={`${ms(m.avg_processing_ms)} avg processing`} icon={Zap} color="var(--amber)" />
      </div>

      <div className="admin-grid">
        <div className="card admin-panel">
          <div className="admin-panel-head">
            <div>
              <div className="panel-title">Scan Volume</div>
              <div className="panel-copy">Last 14 days of screening activity.</div>
            </div>
            <span className="tag tag-neutral">{fullDate(data.generated_at)}</span>
          </div>
          <div className="admin-trend">
            {data.trend.map(point => (
              <div className="admin-trend-col" key={point.date}>
                <div className="admin-trend-bar">
                  <span style={{ height: `${Math.max(6, (point.scans / maxTrend) * 100)}%` }} />
                </div>
                <span>{shortDate(point.date)}</span>
              </div>
            ))}
          </div>
        </div>

        <aside className="panel-stack">
          <div className="decision-card">
            <div className="panel-title">Quota Pressure</div>
            <div className="decision-row">
              <span>Free limit reached</span>
              <span className="score-pill" style={{ background: 'var(--amber-soft)', color: 'var(--amber)' }}>{fmt(m.free_limit_reached)}</span>
            </div>
            <div className="decision-row">
              <span>Users with scans</span>
              <span className="score-pill" style={{ background: 'var(--green-soft)', color: 'var(--green-strong)' }}>{fmt(m.users_with_scans)}</span>
            </div>
            <div className="decision-row">
              <span>Active API keys</span>
              <span className="score-pill">{fmt(m.active_api_keys)}</span>
            </div>
          </div>

          <div className="decision-card">
            <div className="panel-title">Quality Signal</div>
            <div className="decision-row">
              <span>High confidence candidates</span>
              <span className="score-pill" style={{ background: 'var(--green-soft)', color: 'var(--green-strong)' }}>{fmt(m.high_confidence_candidates)}</span>
            </div>
            {data.recommendation_breakdown.slice(0, 4).map(item => (
              <ProgressRow
                key={item.recommendation}
                label={item.recommendation}
                value={item.count}
                max={maxRecommendation}
                color={item.recommendation.includes('Hire') ? 'var(--green)' : item.recommendation === 'Consider' ? 'var(--amber)' : 'var(--red)'}
              />
            ))}
          </div>
        </aside>
      </div>

      <div className="admin-grid">
        <div className="card admin-panel">
          <div className="admin-panel-head">
            <div>
              <div className="panel-title">Recent Scans</div>
              <div className="panel-copy">Newest backend assessments across all accounts.</div>
            </div>
          </div>
          <div className="table-wrap">
            <table className="tbl">
              <thead>
                <tr>
                  <th>Time</th>
                  <th>User</th>
                  <th>Role</th>
                  <th>Candidates</th>
                  <th>Top</th>
                  <th>Avg</th>
                  <th>Runtime</th>
                </tr>
              </thead>
              <tbody>
                {data.recent_scans.map(scan => (
                  <tr key={scan.scan_id}>
                    <td><span style={{ fontFamily: 'var(--mono)', fontSize: 12 }}>{fullDate(scan.created_at)}</span></td>
                    <td>{scan.user_email}</td>
                    <td><strong style={{ color: 'var(--ink)' }}>{scan.role_title}</strong></td>
                    <td>{fmt(scan.total_candidates)}</td>
                    <td><span className="score-pill score-pill-strong">{pct(scan.top_score)}</span></td>
                    <td><span className="score-pill">{pct(scan.avg_score)}</span></td>
                    <td>{ms(scan.processing_time_ms)}</td>
                  </tr>
                ))}
                {data.recent_scans.length === 0 && (
                  <tr><td colSpan="7" style={{ textAlign: 'center', padding: 28 }}>No scans have been created yet.</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        <aside className="panel-stack">
          <div className="decision-card">
            <div className="panel-title">Score Distribution</div>
            <div style={{ marginTop: 12 }}>
              {data.score_buckets.map(bucket => (
                <ProgressRow
                  key={bucket.label}
                  label={bucket.label}
                  value={bucket.count}
                  max={maxScoreBucket}
                  color={bucket.label.startsWith('85') || bucket.label.startsWith('70') ? 'var(--green)' : bucket.label.startsWith('55') ? 'var(--amber)' : 'var(--red)'}
                />
              ))}
            </div>
          </div>

          <div className="decision-card">
            <div className="panel-title">Top Roles</div>
            <div style={{ marginTop: 10, display: 'flex', flexDirection: 'column', gap: 10 }}>
              {data.top_roles.map(role => (
                <div className="admin-role-row" key={role.role_title}>
                  <div>
                    <strong>{role.role_title}</strong>
                    <span>{fmt(role.scans)} scans / {fmt(role.candidates)} candidates</span>
                  </div>
                  <span className="score-pill">{pct(role.avg_score)}</span>
                </div>
              ))}
              {data.top_roles.length === 0 && <div className="panel-copy">No role data yet.</div>}
            </div>
          </div>
        </aside>
      </div>

      <div className="card admin-panel">
        <div className="admin-panel-head">
          <div>
            <div className="panel-title">Free Scan Usage</div>
            <div className="panel-copy">Top accounts by usage against the {data.free_scan_limit}-scan free plan.</div>
          </div>
          <CheckCircle2 size={16} color="var(--green-strong)" />
        </div>
        <div className="table-wrap">
          <table className="tbl">
            <thead>
              <tr>
                <th>User</th>
                <th>Joined</th>
                <th>Used</th>
                <th>Remaining</th>
                <th>Plan status</th>
              </tr>
            </thead>
            <tbody>
              {data.usage.map(user => (
                <tr key={user.user_id}>
                  <td><strong style={{ color: 'var(--ink)' }}>{user.email}</strong></td>
                  <td>{shortDate(user.created_at)}</td>
                  <td>{fmt(user.scans_used)} / {fmt(user.free_scan_limit)}</td>
                  <td>{fmt(user.remaining)}</td>
                  <td>
                    <span className={`tag ${user.remaining > 0 ? 'tag-emerald' : 'tag-amber'}`}>
                      {user.remaining > 0 ? 'Active free plan' : 'Limit reached'}
                    </span>
                  </td>
                </tr>
              ))}
              {data.usage.length === 0 && (
                <tr><td colSpan="5" style={{ textAlign: 'center', padding: 28 }}>No users yet.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </>
  )
}
