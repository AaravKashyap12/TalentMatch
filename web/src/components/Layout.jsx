import { useLocation, useNavigate, Link } from 'react-router-dom'
import {
  Plus, Clock, GitCompare, LayoutDashboard,
  LogOut, Search, ShieldCheck, BarChart3,
} from 'lucide-react'
import BrandLockup from './Brand'
import { SITE_PAGES } from '../sitePages'

const SHOW_ADMIN = import.meta.env.DEV || import.meta.env.VITE_ENABLE_ADMIN_DASHBOARD === 'true'

const WORKSPACE_NAV = [
  { path: '/',       icon: LayoutDashboard, label: 'Dashboard' },
  { path: '/scan',   icon: Plus,             label: 'New Scan'  },
  { path: '/history',icon: Clock,            label: 'History'   },
  { path: '/compare',icon: GitCompare,       label: 'Compare'   },
]

const NAV = SHOW_ADMIN
  ? [...WORKSPACE_NAV, { path: '/admin', icon: BarChart3, label: 'Admin' }]
  : WORKSPACE_NAV

function getInitials(user) {
  const name = user?.user_metadata?.name || user?.email || ''
  const parts = name.trim().split(/\s+/)
  return parts.length >= 2
    ? (parts[0][0] + parts[1][0]).toUpperCase()
    : name.slice(0, 2).toUpperCase()
}

export default function Layout({ user, onLogout, showToast, children }) {
  const location = useLocation()
  const navigate = useNavigate()
  const title = NAV.find(item => item.path === '/'
    ? location.pathname === '/'
    : location.pathname.startsWith(item.path))?.label || 'Workspace'

  return (
    <div className="app-shell">
      {/* ── Sidebar ── */}
      <aside className="sidebar">
        {/* Logo */}
        <Link to="/" className="sidebar-logo brand-link" aria-label="TalentMatch dashboard">
          <BrandLockup subtitle="Recruiting intelligence" />
        </Link>

        {/* Nav */}
        <nav className="sidebar-nav">
          <div className="sidebar-section-label">Workspace</div>
          {NAV.map(({ path, icon: Icon, label }) => {
            const active = path === '/'
              ? location.pathname === '/'
              : location.pathname.startsWith(path)
            return (
              <Link
                key={path}
                to={path}
                className={`nav-item${active ? ' active' : ''}`}
              >
                <Icon size={16} />
                <span>{label}</span>
              </Link>
            )
          })}
        </nav>

        {/* User */}
        <div className="sidebar-footer">
          <div className="user-chip" onClick={onLogout} title="Sign out">
            <div className="user-avatar">{getInitials(user)}</div>
            <div className="user-info" style={{ flex:1, minWidth:0 }}>
              <div style={{ fontSize:12, fontWeight:600, color:'var(--ink-2)', overflow:'hidden', textOverflow:'ellipsis', whiteSpace:'nowrap' }}>
                {user?.user_metadata?.name || user?.email?.split('@')[0] || 'User'}
              </div>
              <div style={{ fontSize:10.5, color:'var(--ink-4)', overflow:'hidden', textOverflow:'ellipsis', whiteSpace:'nowrap' }}>
                {user?.email || 'dev@local'}
              </div>
            </div>
            <LogOut size={13} color="var(--ink-5)" />
          </div>
        </div>
      </aside>

      {/* ── Main ── */}
      <main className="main-content">
        <div className="page-container">
        <div className="app-topbar">
            <div>
              <div className="workspace-label">
                <span className="workspace-dot" />
                Hiring workspace
              </div>
              <div style={{ fontFamily:'var(--syne)', fontSize:17, fontWeight:800, color:'var(--ink)', marginTop:4 }}>
                {title}
              </div>
            </div>
            <div style={{ display:'flex', alignItems:'center', gap:10 }}>
              <button className="command-pill" onClick={() => navigate('/history')}>
                <Search size={13} />
                Search assessments
              </button>
              <div className="command-pill">
                <ShieldCheck size={13} color="var(--green-strong)" />
                Evidence-aware scoring
              </div>
            </div>
          </div>
          {children}
          <footer className="app-footer">
            <span className="app-footer-copy">TalentMatch workspace</span>
            <div className="app-footer-links">
              {SITE_PAGES.map(page => (
                <Link key={page.path} to={page.path} className="app-footer-link">
                  {page.label}
                </Link>
              ))}
            </div>
          </footer>
        </div>
      </main>
    </div>
  )
}
