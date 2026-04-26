import { useState } from 'react'
import {
  signupWithEmail,
  loginWithEmail,
  loginWithGoogle,
  getCurrentUser,
  loginAsDev,
} from '../api'
import {
  AlertCircle,
  ArrowRight,
  BarChart3,
  CheckCircle2,
  Eye,
  EyeOff,
  FileSearch,
  Lock,
  Mail,
  ShieldCheck,
  Sparkles,
  User,
} from 'lucide-react'
import BrandLockup, { BrandMark } from '../components/Brand'

function InputField({
  icon: Icon,
  type = 'text',
  label,
  placeholder,
  value,
  onChange,
  required,
  autoComplete,
}) {
  const [show, setShow] = useState(false)
  const isPassword = type === 'password'

  return (
    <label className="auth-field">
      <span className="auth-label">{label}</span>
      <span className="auth-input-wrap">
        <Icon size={15} className="auth-input-icon" />
        <input
          type={isPassword && show ? 'text' : type}
          className="input-base auth-input"
          placeholder={placeholder}
          value={value}
          onChange={onChange}
          required={required}
          autoComplete={autoComplete}
        />
        {isPassword && (
          <button
            type="button"
            className="auth-eye-button"
            onClick={() => setShow(value => !value)}
            aria-label={show ? 'Hide password' : 'Show password'}
          >
            {show ? <EyeOff size={15} /> : <Eye size={15} />}
          </button>
        )}
      </span>
    </label>
  )
}

function GoogleIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" aria-hidden="true">
      <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
      <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
      <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" />
      <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" />
    </svg>
  )
}

export default function Login({ onLoginSuccess }) {
  const [isSignup, setIsSignup] = useState(false)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [name, setName] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const isDevMode = import.meta.env.DEV

  async function handleSubmit(event) {
    event.preventDefault()
    setError(null)
    setLoading(true)
    try {
      if (isSignup) await signupWithEmail(email, password, name)
      await loginWithEmail(email, password)
      const user = await getCurrentUser()
      onLoginSuccess?.(user)
    } catch (err) {
      setError(err.message || 'Authentication failed')
      setLoading(false)
    }
  }

  async function handleGoogle() {
    setError(null)
    setLoading(true)
    try {
      await loginWithGoogle()
    } catch (err) {
      setError(err.message || 'Google sign-in failed')
      setLoading(false)
    }
  }

  async function handleDev() {
    setError(null)
    try {
      const data = await loginAsDev()
      onLoginSuccess?.(data.user)
    } catch (err) {
      setError(err.message)
    }
  }

  function toggleMode() {
    setIsSignup(value => !value)
    setError(null)
  }

  return (
    <main className="auth-page">
      <section className="auth-showcase" aria-label="TalentMatch product highlights">
        <div className="auth-showcase-top">
          <BrandLockup subtitle="Recruiting intelligence" />
        </div>

        <div className="auth-showcase-copy">
          <div className="page-kicker auth-kicker">
            <Sparkles size={12} />
            AI-assisted screening
          </div>
          <h1 className="auth-showcase-title">
            Rank candidates with evidence, not spreadsheets.
          </h1>
          <p className="auth-showcase-body">
            TalentMatch turns resumes and job requirements into scored, explainable hiring decisions for recruiting teams.
          </p>
        </div>

        <div className="auth-proof-grid">
          <div className="auth-proof-card">
            <FileSearch size={16} />
            <span>Resume parsing</span>
          </div>
          <div className="auth-proof-card">
            <BarChart3 size={16} />
            <span>Weighted scoring</span>
          </div>
          <div className="auth-proof-card">
            <ShieldCheck size={16} />
            <span>Explainable decisions</span>
          </div>
        </div>

        <div className="auth-stats">
          {['10,000+ resumes analyzed', '95% recruiter time saved', '3.2x faster hiring'].map(item => (
            <div className="auth-stat" key={item}>
              <CheckCircle2 size={14} />
              <span>{item}</span>
            </div>
          ))}
        </div>
      </section>

      <section className="auth-panel" aria-label={isSignup ? 'Create account' : 'Sign in'}>
        <div className="auth-card au">
          <div className="auth-card-header">
            <BrandMark />
            <div>
              <h2>{isSignup ? 'Create your account' : 'Welcome back'}</h2>
              <p>{isSignup ? 'Start with 5 free scans.' : 'Sign in to your hiring workspace.'}</p>
            </div>
          </div>

          {error && (
            <div className="auth-error" role="alert">
              <AlertCircle size={15} />
              <span>{error}</span>
            </div>
          )}

          <form className="auth-form" onSubmit={handleSubmit}>
            {isSignup && (
              <InputField
                icon={User}
                label="Full Name"
                placeholder="Aarav Kashyap"
                value={name}
                onChange={event => setName(event.target.value)}
                required={isSignup}
                autoComplete="name"
              />
            )}
            <InputField
              icon={Mail}
              type="email"
              label="Email"
              placeholder="you@company.com"
              value={email}
              onChange={event => setEmail(event.target.value)}
              required
              autoComplete="email"
            />
            <InputField
              icon={Lock}
              type="password"
              label="Password"
              placeholder="Enter your password"
              value={password}
              onChange={event => setPassword(event.target.value)}
              required
              autoComplete={isSignup ? 'new-password' : 'current-password'}
            />

            <button type="submit" className="btn btn-primary btn-lg auth-submit" disabled={loading}>
              {loading ? (
                <span className="auth-spinner" aria-label="Loading" />
              ) : (
                <>
                  {isSignup ? 'Create account' : 'Sign in'}
                  <ArrowRight size={15} />
                </>
              )}
            </button>
          </form>

          <div className="auth-divider">
            <span />
            <strong>or</strong>
            <span />
          </div>

          <button className="btn btn-secondary btn-lg auth-submit" onClick={handleGoogle} disabled={loading}>
            <GoogleIcon />
            Continue with Google
          </button>

          {isDevMode && (
            <button className="btn btn-ghost btn-md auth-dev" onClick={handleDev} disabled={loading}>
              Dev mode: skip login
            </button>
          )}

          <p className="auth-switch">
            {isSignup ? 'Already have an account?' : "Don't have an account?"}
            <button type="button" onClick={toggleMode}>
              {isSignup ? 'Sign in' : 'Sign up'}
            </button>
          </p>
        </div>
      </section>
    </main>
  )
}
