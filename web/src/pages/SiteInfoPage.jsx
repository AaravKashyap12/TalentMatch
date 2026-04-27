import { ArrowLeft, ArrowRight, FileText } from 'lucide-react'
import { Link, useNavigate } from 'react-router-dom'
import BrandLockup from '../components/Brand'
import { SITE_PAGES } from '../sitePages'

function getPage(path) {
  return SITE_PAGES.find(page => page.path === path)
}

export default function SiteInfoPage({ path, embedded = false, onEnterApp }) {
  const navigate = useNavigate()
  const page = getPage(path)

  if (!page) return null

  function openApp() {
    onEnterApp?.()
    navigate('/login')
  }

  return (
    <div className={`site-info${embedded ? ' site-info--embedded' : ''}`}>
      {!embedded && (
        <div className="site-info-nav">
          <Link to="/" className="brand-link" aria-label="TalentMatch home">
            <BrandLockup subtitle="Hiring workspace" />
          </Link>
          <button className="btn btn-ghost btn-md" onClick={() => navigate(-1)}>
            <ArrowLeft size={14} />
            Back
          </button>
        </div>
      )}

      <section className="site-info-hero">
        <div className="page-kicker">
          <FileText size={12} />
          {page.kicker}
        </div>
        <h1 className="site-info-title">{page.title}</h1>
        <p className="site-info-intro">{page.intro}</p>
      </section>

      <section className="site-info-grid">
        {page.sections.map(section => (
          <article key={section.title} className="site-info-card">
            <h2>{section.title}</h2>
            <p>{section.body}</p>
          </article>
        ))}
      </section>

      {!embedded && (
        <section className="site-info-cta">
          <div>
            <div className="site-info-cta-title">Ready to screen candidates?</div>
            <p className="site-info-cta-copy">
              Start a workspace, upload a job description, and generate a ranked slate in minutes.
            </p>
          </div>
          <button className="btn btn-primary btn-lg" onClick={openApp}>
            Open TalentMatch
            <ArrowRight size={15} />
          </button>
        </section>
      )}
    </div>
  )
}
