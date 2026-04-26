import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { listScans, deleteScan } from '../api'
import {
  Search, Clock, Users, ArrowRight, Calendar,
  RefreshCw, BarChart3, Trash2, Target,
} from 'lucide-react'

const scoreColor = v => v >= 70 ? 'var(--green-strong)' : v >= 45 ? 'var(--amber)' : 'var(--red)'
const scoreBg    = v => v >= 70 ? 'var(--green-soft)'   : v >= 45 ? 'var(--amber-soft)' : 'var(--red-soft)'

function statusInfo(score) {
  if (score >= 80) return ['High Signal', 'badge-success']
  if (score >= 50) return ['Qualified',   'badge-accent']
  return                  ['Low Signal',  'badge-neutral']
}

export default function History({ onShowToast }) {
  const navigate = useNavigate()
  const [scans,   setScans]   = useState([])
  const [loading, setLoading] = useState(true)
  const [search,  setSearch]  = useState('')
  const [deleting, setDeleting] = useState(null)

  useEffect(() => { fetchScans() }, [])

  async function fetchScans() {
    setLoading(true)
    try { setScans(await listScans()) }
    catch  { onShowToast?.('Failed to load history', 'error') }
    finally { setLoading(false) }
  }

  async function handleDelete(e, scanId) {
    e.stopPropagation()
    if (!confirm('Delete this scan and all its results?')) return
    setDeleting(scanId)
    try {
      await deleteScan(scanId)
      setScans(s => s.filter(x => x.scan_id !== scanId))
      onShowToast?.('Scan deleted', 'success')
    } catch {
      onShowToast?.('Failed to delete scan', 'error')
    } finally {
      setDeleting(null)
    }
  }

  const filtered = scans
    .filter(s => (s.role_title || '').toLowerCase().includes(search.toLowerCase()))
    .sort((a, b) => new Date(b.created_at) - new Date(a.created_at))

  return (
    <>
      <div className="section-hd au">
        <div>
          <div className="page-kicker"><Target size={12} /> Audit trail</div>
          <h1 className="section-title">Assessment History</h1>
          <p className="section-sub">
            {loading ? '…' : `${scans.length} total scan${scans.length !== 1 ? 's' : ''}`}
          </p>
        </div>
        <div style={{ display:'flex', gap:10 }}>
          <div style={{ position:'relative' }}>
            <Search size={13} style={{
              position:'absolute', left:10, top:'50%', transform:'translateY(-50%)',
              color:'var(--ink-5)', pointerEvents:'none',
            }} />
            <input
              className="input-base"
              placeholder="Search role titles…"
              style={{ paddingLeft:32, height:36, width:220 }}
              value={search}
              onChange={e => setSearch(e.target.value)}
            />
          </div>
          <button className="btn btn-secondary" onClick={fetchScans} disabled={loading}>
            <RefreshCw size={13} className={loading ? 'spin' : ''} />
            Refresh
          </button>
        </div>
      </div>

      <div className="card au au-1" style={{ overflow:'hidden', flex:1 }}>
        {loading ? (
          <div style={{ padding:20, display:'flex', flexDirection:'column', gap:12 }}>
            {[1,2,3,4,5].map(i => (
              <div key={i} style={{ display:'flex', gap:16, alignItems:'center' }}>
                <div className="skeleton" style={{ width:40, height:40, borderRadius:10 }} />
                <div style={{ flex:1 }}>
                  <div className="skeleton" style={{ width:'35%', height:12, marginBottom:7 }} />
                  <div className="skeleton" style={{ width:'20%', height:9 }} />
                </div>
                <div className="skeleton" style={{ width:60, height:24, borderRadius:99 }} />
              </div>
            ))}
          </div>
        ) : filtered.length === 0 ? (
          <div style={{ textAlign:'center', padding:'64px 32px', color:'var(--ink-4)' }}>
            <BarChart3 size={32} style={{ margin:'0 auto 12px', opacity:0.3 }} />
            <div style={{ fontSize:14, fontWeight:600, marginBottom:6, color:'var(--ink-3)' }}>
              {search ? 'No scans match your search' : 'No scans yet'}
            </div>
            {!search && (
              <button className="btn btn-primary btn-sm" style={{ marginTop:16 }} onClick={() => navigate('/scan')}>
                Create your first scan
              </button>
            )}
          </div>
        ) : (
          <div className="table-wrap">
            <table className="tbl">
              <thead>
                <tr>
                  <th><div style={{ display:'flex', alignItems:'center', gap:5 }}><Calendar size={11} />Date</div></th>
                  <th>Role</th>
                  <th style={{ textAlign:'center' }}>Candidates</th>
                  <th style={{ textAlign:'center' }}>Top Match</th>
                  <th style={{ textAlign:'center' }}>Avg Score</th>
                  <th style={{ textAlign:'center' }}>Status</th>
                  <th style={{ textAlign:'right' }}></th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((s, i) => {
                  const top = s.top_score || 0
                  const avg = s.avg_score || 0
                  const [statusText, statusClass] = statusInfo(top)
                  const date = new Date(s.created_at)
                  const dateStr = date.toLocaleDateString(undefined, { month:'short', day:'numeric', year:'numeric' })
                  const timeStr = date.toLocaleTimeString(undefined, { hour:'2-digit', minute:'2-digit' })

                  return (
                    <tr
                      key={s.scan_id}
                      className="au"
                      style={{ cursor:'pointer', animationDelay:`${i * 0.035}s` }}
                      onClick={() => navigate(`/results/${s.scan_id}`)}
                    >
                      <td>
                        <div style={{ fontSize:12.5, fontFamily:'var(--mono)', color:'var(--ink-3)' }}>{dateStr}</div>
                        <div style={{ fontSize:11, color:'var(--ink-5)', marginTop:1 }}>{timeStr}</div>
                      </td>
                      <td>
                        <div style={{ fontWeight:600, fontSize:13.5, color:'var(--ink)' }}>
                          {s.role_title || 'Untitled Assessment'}
                        </div>
                      </td>
                      <td style={{ textAlign:'center' }}>
                        <span style={{ display:'inline-flex', alignItems:'center', gap:4, fontSize:12.5, fontFamily:'var(--mono)', color:'var(--ink-3)' }}>
                          <Users size={11} color="var(--ink-5)" />
                          {s.total_candidates || 0}
                        </span>
                      </td>
                      <td style={{ textAlign:'center' }}>
                        <span className="score-pill" style={{ background:scoreBg(top), color:scoreColor(top) }}>{top}%</span>
                      </td>
                      <td style={{ textAlign:'center' }}>
                        <span className="score-pill" style={{ background:scoreBg(avg), color:scoreColor(avg) }}>{avg}%</span>
                      </td>
                      <td style={{ textAlign:'center' }}>
                        <span className={`badge ${statusClass}`}>{statusText}</span>
                      </td>
                      <td style={{ textAlign:'right' }}>
                        <div style={{ display:'flex', alignItems:'center', justifyContent:'flex-end', gap:4 }}>
                          <button
                            className="btn btn-ghost btn-sm btn-icon"
                            style={{ color:'var(--ink-5)' }}
                            onClick={e => handleDelete(e, s.scan_id)}
                            disabled={deleting === s.scan_id}
                            title="Delete scan"
                          >
                            {deleting === s.scan_id
                              ? <RefreshCw size={13} className="spin" />
                              : <Trash2 size={13} />
                            }
                          </button>
                          <button
                            className="btn btn-ghost btn-sm btn-icon"
                            style={{ color:'var(--accent-2)' }}
                            onClick={e => { e.stopPropagation(); navigate(`/results/${s.scan_id}`) }}
                          >
                            <ArrowRight size={14} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </>
  )
}
