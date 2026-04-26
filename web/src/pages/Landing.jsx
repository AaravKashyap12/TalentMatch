import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  ArrowRight, BarChart3, CheckCircle2, FileSearch, GitCompare,
  Moon, ShieldCheck, Sun, Users, Zap,
} from 'lucide-react'
import BrandLockup, { BrandMark } from '../components/Brand'

function useTheme() {
  const [theme, setTheme] = useState(() => {
    if (typeof window === 'undefined') return 'dark'
    return localStorage.getItem('tm-theme') || 'dark'
  })

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
    localStorage.setItem('tm-theme', theme)
  }, [theme])

  const toggle = () => setTheme(t => (t === 'dark' ? 'light' : 'dark'))
  return { theme, toggle }
}

function FeatureCard({ icon: Icon, tag, title, desc }) {
  return (
    <div className="feature-card">
      <div className="feature-card-top">
        <div className="feature-icon">
          <Icon size={15} strokeWidth={1.8} />
        </div>
        <span className="feature-tag">{tag}</span>
      </div>
      <h3 className="feature-title">{title}</h3>
      <p className="feature-desc">{desc}</p>
    </div>
  )
}

function StatBlock({ value, label }) {
  return (
    <div className="stat-block">
      <span className="stat-value">{value}</span>
      <span className="stat-label">{label}</span>
    </div>
  )
}

function PreviewRow({ rank, name, score, top }) {
  return (
    <div className={`preview-row${top ? ' preview-row--top' : ''}`}>
      <span className="preview-rank">{rank}</span>
      <span className="preview-name">{name}</span>
      <div className="preview-bar-track">
        <div className="preview-bar-fill" style={{ width: `${score}%` }} />
      </div>
      <span className="preview-pct">{score}%</span>
    </div>
  )
}

function Chip({ children, matched = false }) {
  return (
    <span className={`badge ${matched ? 'badge-green' : 'badge-neutral'}`}>
      {children}
    </span>
  )
}

export default function Landing({ onEnterApp }) {
  const navigate = useNavigate()
  const { theme, toggle } = useTheme()
  const go = () => { if (onEnterApp) onEnterApp(); else navigate('/login') }

  return (
    <div className="landing">
      <nav className="l-nav">
        <a href="#" className="l-nav-logo" aria-label="TalentMatch home">
          <BrandLockup />
        </a>

        <div className="l-nav-links">
          <a href="#features" className="l-nav-link">Features</a>
          <a href="#how" className="l-nav-link">Workflow</a>
          <a href="#pricing" className="l-nav-link">Pricing</a>
        </div>

        <div style={{ display:'flex', alignItems:'center', gap:8 }}>
          <button className="theme-toggle" onClick={toggle} aria-label="Toggle theme">
            {theme === 'dark' ? <Sun size={14} strokeWidth={2} /> : <Moon size={14} strokeWidth={2} />}
          </button>
          <div className="l-nav-sep" />
          <button className="btn btn-ghost btn-md" onClick={go}>Sign in</button>
          <button className="btn btn-primary btn-md" onClick={go}>Get started</button>
        </div>
      </nav>

      <section className="l-hero">
        <div>
          <div className="hero-kicker">
            <span className="hero-kicker-dot" />
            AI recruiting intelligence
          </div>
          <h1 className="hero-h1">
            Rank every candidate.
            <br />
            <span className="hero-h1-muted">Decide with evidence.</span>
          </h1>
          <p className="hero-body">
            TalentMatch parses, scores, and ranks resumes against your exact job requirements
            so hiring teams can move from upload to shortlist in minutes.
          </p>
          <div className="hero-actions">
            <button className="btn btn-primary btn-lg" onClick={go}>
              Start screening free
              <ArrowRight size={15} strokeWidth={2.5} />
            </button>
            <button className="btn btn-outline btn-lg" onClick={go}>
              View live demo
            </button>
          </div>

          <div className="hero-social">
            <StatBlock value="10k+" label="Resumes analyzed" />
            <div className="hero-social-sep" />
            <StatBlock value="95%" label="Time saved" />
            <div className="hero-social-sep" />
            <StatBlock value="3.2x" label="Faster hiring" />
          </div>
        </div>

        <div className="preview-panel">
          <div className="preview-card">
            <div className="preview-card-top">
              <div>
                <div className="preview-card-label">Candidate Rankings</div>
                <div className="preview-card-meta">Backend Engineer / 12 resumes / just now</div>
              </div>
              <span className="badge badge-green" style={{ gap:5 }}>
                <span className="live-dot" />
                Live
              </span>
            </div>

            <div className="preview-rows">
              <PreviewRow rank="01" name="Alex R." score={94} top />
              <PreviewRow rank="02" name="Jamie L." score={81} />
              <PreviewRow rank="03" name="Sam K." score={76} />
              <PreviewRow rank="04" name="Morgan T." score={61} />
            </div>

            <div className="preview-footer">
              <span className="preview-footer-lbl">Required skills</span>
              <div className="preview-chips">
                <Chip matched>Python</Chip>
                <Chip matched>FastAPI</Chip>
                <Chip matched>SQL</Chip>
                <Chip>Docker</Chip>
              </div>
            </div>
          </div>

          <div className="preview-mini-cards">
            <div className="preview-mini">
              <div className="preview-mini-header">
                <span className="preview-mini-label">Recommendation</span>
                <div className="preview-mini-icon"><CheckCircle2 size={13} /></div>
              </div>
              <span className="preview-mini-val">Hire</span>
              <span className="preview-mini-sub">High confidence</span>
            </div>
            <div className="preview-mini">
              <div className="preview-mini-header">
                <span className="preview-mini-label">Free scans</span>
                <div className="preview-mini-icon"><Zap size={13} /></div>
              </div>
              <span className="preview-mini-val">5</span>
              <span className="preview-mini-sub">Included per account</span>
            </div>
          </div>
        </div>
      </section>

      <div className="l-band">
        <div className="l-band-item"><FileSearch size={14} /> Resume parsing</div>
        <div className="l-band-item"><BarChart3 size={14} /> Evidence scoring</div>
        <div className="l-band-item"><GitCompare size={14} /> Candidate compare</div>
        <div className="l-band-item"><ShieldCheck size={14} /> Audit history</div>
      </div>

      <section id="features" className="l-features">
        <div className="l-section-head">
          <div className="eyebrow">
            <span className="live-dot" />
            Built for real hiring workflows
          </div>
          <h2 className="section-h2">Everything your team needs</h2>
          <p className="section-body">
            From PDF parsing to shortlist, TalentMatch handles the screening pipeline with
            structured scoring and recruiter-readable explanations.
          </p>
        </div>

        <div className="features-grid">
          <FeatureCard icon={FileSearch} tag="Parsing" title="Intelligent resume parsing" desc="Extract skills, experience, and education from PDF resumes and prepare clean candidate profiles." />
          <FeatureCard icon={BarChart3} tag="Scoring" title="Weighted candidate scoring" desc="Score every candidate by skills, experience, education, relevance, ATS quality, and role alignment." />
          <FeatureCard icon={GitCompare} tag="Compare" title="Side-by-side comparison" desc="Compare candidates across evidence-backed dimensions before making a shortlist decision." />
          <FeatureCard icon={Zap} tag="Config" title="Configurable priorities" desc="Tune scoring weights per role so each search reflects the hiring bar that matters." />
          <FeatureCard icon={ShieldCheck} tag="Trust" title="Explainable recommendations" desc="Show confidence, watchouts, and improvement guidance so the score feels transparent." />
          <FeatureCard icon={Users} tag="Team" title="Hiring workflow ready" desc="Review scan history, revisit assessments, and keep candidate decisions in one place." />
        </div>
      </section>

      <section id="how" className="l-how">
        <div className="l-how-inner">
          <div className="l-section-head">
            <div className="eyebrow">
              <span className="live-dot" />
              Workflow
            </div>
            <h2 className="section-h2">Three steps to a shortlist</h2>
            <p className="section-body">No setup required. Start screening in under two minutes.</p>
          </div>
          <div className="how-grid">
            {[
              { n: '01', title: 'Define the role', desc: 'Set required skills, preferred skills, experience, degree expectations, and scoring weights.' },
              { n: '02', title: 'Upload resumes', desc: 'Drop in PDF resumes. TalentMatch extracts structured data and checks ATS readability.' },
              { n: '03', title: 'Review ranked results', desc: 'Open explanations, compare candidates, and move forward with the strongest evidence.' },
            ].map(s => (
              <div key={s.n} className="how-step">
                <div className="how-step-num">{s.n}</div>
                <h3 className="how-step-title">{s.title}</h3>
                <p className="how-step-desc">{s.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section id="pricing" className="l-pricing">
        <div className="l-pricing-inner">
          <div>
            <div className="eyebrow">
              <span className="live-dot" />
              Pricing
            </div>
            <h2 className="section-h2">Start with 5 free scans</h2>
            <p className="section-body">
              Every account can run 5 free resume scans. The product now enforces this
              allowance in the backend and shows remaining scans before upload.
            </p>
          </div>
          <div className="pricing-card">
            <div className="pricing-card-top">
              <span className="feature-tag">Free plan</span>
              <span className="pricing-price">5 scans</span>
            </div>
            <div className="pricing-list">
              <span><CheckCircle2 size={14} /> PDF resume screening</span>
              <span><CheckCircle2 size={14} /> Ranked candidate results</span>
              <span><CheckCircle2 size={14} /> Explanation and confidence layer</span>
            </div>
            <button className="btn btn-primary btn-lg" onClick={go}>
              Create account
              <ArrowRight size={15} strokeWidth={2.5} />
            </button>
          </div>
        </div>
      </section>

      <section className="l-cta">
        <div className="l-cta-inner">
          <div className="eyebrow">
            <span className="live-dot" />
            Get started today
          </div>
          <h2 className="cta-h2">Ready to hire smarter?</h2>
          <p className="cta-body">Join hiring teams screening faster with evidence-aware candidate rankings.</p>
          <div className="hero-actions" style={{ marginBottom:0, justifyContent:'center' }}>
            <button className="btn btn-primary btn-lg" onClick={go}>
              Start screening free
              <ArrowRight size={15} strokeWidth={2.5} />
            </button>
            <button className="btn btn-outline btn-lg" onClick={go}>Talk to sales</button>
          </div>
        </div>
      </section>

      <footer className="l-footer">
        <div className="l-footer-logo">
          <BrandMark size="sm" />
          <span className="l-footer-brand">TalentMatch</span>
        </div>
        <span className="l-footer-copy">Copyright 2026 TalentMatch. All rights reserved.</span>
        <div className="l-footer-links">
          {['Privacy', 'Terms', 'Docs', 'Status'].map(label => (
            <a key={label} href="#" className="l-footer-link">{label}</a>
          ))}
        </div>
      </footer>
    </div>
  )
}
