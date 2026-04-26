import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useState } from 'react'
import {
  LayoutDashboard, BarChart3, GitCompare, History,
  Plus, Menu, X, LogOut, Sparkles, Settings, Bell,
  ChevronRight
} from 'lucide-react'

const NAV = [
  { name: 'Dashboard',  path: '/',        icon: LayoutDashboard },
  { name: 'New Scan',   path: '/scan',     icon: Plus, accent: true },
  { name: 'Results',    path: '/results',  icon: BarChart3 },
  { name: 'Compare',    path: '/compare',  icon: GitCompare },
  { name: 'History',    path: '/history',  icon: History },
]

const PAGE_TITLES = {
  '/':        ['Dashboard',   'Overview & quick actions'],
  '/scan':    ['New Scan',    'Upload resumes & configure'],
  '/results': ['Results',     'Candidate rankings'],
  '/compare': ['Compare',     'Side-by-side analysis'],
  '/history': ['History',     'All past assessments'],
}

export default function Layout({ user, onLogout, children }) {
  const [mobileOpen, setMobileOpen] = useState(false)
  const location = useLocation()
  const navigate = useNavigate()

  const isActive = (path) => {
    if (path === '/') return location.pathname === '/' || location.pathname === '/dashboard'
    return location.pathname.startsWith(path)
  }

  const [pageTitle, pageSub] = PAGE_TITLES[location.pathname] ||
    PAGE_TITLES[Object.keys(PAGE_TITLES).find(k => location.pathname.startsWith(k) && k !== '/') || '/'] ||
    ['TalentMatch', '']

  const userName = user?.user_metadata?.name || user?.email?.split('@')[0] || 'Recruiter'
  const userInitial = userName[0]?.toUpperCase() || 'R'

  return (
    <div className="layout">

      {/* Mobile toggle */}
      <button
        className="mobile-menu-button"
        onClick={() => setMobileOpen(o => !o)}
        aria-label="Toggle menu"
      >
        {mobileOpen ? <X size={18} /> : <Menu size={18} />}
      </button>

      {/* Sidebar */}
      <aside className={`sidebar${mobileOpen ? ' sidebar-mobile-open' : ''}`}>

        {/* Logo */}
        <div className="sidebar-logo">
          <div className="sidebar-logo-mark">
            <Sparkles size={14} />
          </div>
          <span className="sidebar-logo-text">TalentMatch</span>
          <span className="sidebar-logo-badge">AI</span>
        </div>

        {/* Nav */}
        <nav className="sidebar-nav">
          <div className="sidebar-section-label">Workspace</div>

          {NAV.map(item => {
            const Icon = item.icon
            const active = isActive(item.path)

            if (item.accent) {
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  onClick={() => setMobileOpen(false)}
                  style={{
                    display: 'flex', alignItems: 'center', gap: 9,
                    padding: '8px 10px', borderRadius: 'var(--r)',
                    background: active ? 'var(--accent)' : 'var(--accent-soft)',
                    color: active ? 'white' : 'var(--accent)',
                    fontWeight: 600, fontSize: '13.5px',
                    textDecoration: 'none',
                    transition: 'all 0.14s',
                    margin: '4px 0',
                  }}
                >
                  <Icon size={15} />
                  {item.name}
                </Link>
              )
            }

            return (
              <Link
                key={item.path}
                to={item.path}
                className={`nav-link${active ? ' nav-link-active' : ''}`}
                onClick={() => setMobileOpen(false)}
              >
                <Icon size={15} />
                {item.name}
              </Link>
            )
          })}
        </nav>

        {/* Footer */}
        <div className="sidebar-footer">
          <div className="sidebar-user" onClick={onLogout} title="Sign out">
            <div className="sidebar-user-avatar">{userInitial}</div>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div className="sidebar-user-name">{userName}</div>
              <div className="sidebar-user-role">Recruiter</div>
            </div>
            <LogOut size={13} color="var(--ink-4)" />
          </div>
        </div>
      </aside>

      {/* Main */}
      <div className="main-container">

        {/* Topbar */}
        <header className="topbar">
          <div className="topbar-breadcrumb">
            <span>Workspace</span>
            <ChevronRight size={12} className="topbar-breadcrumb-sep" />
            <span className="topbar-breadcrumb-current">{pageTitle}</span>
          </div>
          <div className="topbar-actions">
            <button
              className="btn btn-secondary btn-sm"
              onClick={() => navigate('/scan')}
              style={{ gap: 6 }}
            >
              <Plus size={13} strokeWidth={2.5} />
              New Scan
            </button>
          </div>
        </header>

        {/* Content */}
        <main className="content">
          {children}
        </main>

      </div>

      {/* Mobile overlay */}
      {mobileOpen && (
        <div
          style={{
            position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.3)',
            zIndex: 49, backdropFilter: 'blur(2px)',
          }}
          onClick={() => setMobileOpen(false)}
        />
      )}
    </div>
  )
}