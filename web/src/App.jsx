import { useState, useEffect, Suspense, lazy } from 'react'
import { BrowserRouter as Router, Routes, Route, Navigate, useNavigate, useLocation } from 'react-router-dom'
import './styles.css'
import Login   from './pages/Login'
import Landing from './pages/Landing'
import Layout  from './components/Layout'
import Toast   from './components/Toast'
import { BrandMark } from './components/Brand'
import { getSession, getCurrentUser, logout } from './api'

const Dashboard = lazy(() => import('./pages/Dashboard'))
const NewScan   = lazy(() => import('./pages/NewScan'))
const Results   = lazy(() => import('./pages/Results'))
const Compare   = lazy(() => import('./pages/Compare'))
const History   = lazy(() => import('./pages/History'))
const AdminDashboard = lazy(() => import('./pages/AdminDashboard'))

function PageLoader() {
  return (
    <div style={{ flex:1, display:'flex', alignItems:'center', justifyContent:'center', minHeight:'60vh' }}>
      <div className="loader-ring" />
    </div>
  )
}

// FIX: Handle Supabase OAuth callback — Supabase sets tokens in the URL hash
function OAuthCallback({ onSuccess }) {
  const navigate = useNavigate()
  useEffect(() => {
    // Supabase JS SDK automatically handles the hash fragment on init
    getCurrentUser()
      .then(u => {
        onSuccess(u)
        navigate('/', { replace: true })
      })
      .catch(() => navigate('/login', { replace: true }))
  }, [])
  return <PageLoader />
}

function AppShell({ user, onLogout, showToast }) {
  const [scanResult, setScanResult] = useState(null)

  return (
    <Layout user={user} onLogout={onLogout} showToast={showToast}>
      <Suspense fallback={<PageLoader />}>
        <Routes>
          <Route path="/"            element={<Dashboard onShowToast={showToast} />} />
          <Route path="/scan"        element={
            <NewScan onScanComplete={r => setScanResult(r)} onShowToast={showToast} />
          } />
          <Route path="/results"     element={<Results results={scanResult} onShowToast={showToast} />} />
          <Route path="/results/:id" element={<Results onShowToast={showToast} />} />
          <Route path="/compare"     element={<Compare onShowToast={showToast} />} />
          <Route path="/history"     element={<History onShowToast={showToast} />} />
          <Route path="/admin"       element={<AdminDashboard onShowToast={showToast} />} />
          <Route path="*"            element={<Navigate to="/" replace />} />
        </Routes>
      </Suspense>
    </Layout>
  )
}

export default function App() {
  const [auth, setAuth]   = useState(null)  // null=loading, 'landing', false=login, true=authed
  const [user, setUser]   = useState(null)
  const [toast, setToast] = useState(null)

  useEffect(() => { checkSession() }, [])

  async function checkSession() {
    try {
      const session = await getSession()
      if (session) {
        const u = await getCurrentUser()
        setUser(u)
        setAuth(true)
      } else {
        setAuth('landing')
      }
    } catch {
      setAuth('landing')
    }
  }

  function showToast(message, type = 'info') {
    setToast({ message, type })
    setTimeout(() => setToast(null), 3500)
  }

  function handleLogin(userData) {
    setUser(userData)
    setAuth(true)
    showToast('Welcome back!', 'success')
  }

  async function handleLogout() {
    try { await logout() } catch {}
    setAuth('landing')
    setUser(null)
    showToast('Signed out', 'info')
  }

  if (auth === null) {
    return (
      <div className="loading-screen">
        <div style={{ textAlign:'center' }}>
          <div style={{ display:'flex', justifyContent:'center', marginBottom:20 }}>
            <BrandMark size="lg" />
          </div>
          <div className="loader-ring" style={{ margin:'0 auto' }} />
        </div>
      </div>
    )
  }

  return (
    <Router>
      {auth === 'landing' && <Landing onEnterApp={() => setAuth(false)} />}
      {auth === false     && <Login onLoginSuccess={handleLogin} />}
      {auth === true      && (
        <Routes>
          {/* FIX: OAuth callback route */}
          <Route path="/callback" element={<OAuthCallback onSuccess={u => { setUser(u); setAuth(true) }} />} />
          <Route path="/*"        element={
            <AppShell user={user} onLogout={handleLogout} showToast={showToast} />
          } />
        </Routes>
      )}

      {toast && (
        <div className="toast-container">
          <Toast message={toast.message} type={toast.type} onClose={() => setToast(null)} />
        </div>
      )}
    </Router>
  )
}
