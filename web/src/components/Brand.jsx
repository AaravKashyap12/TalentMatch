export function BrandMark({ size = 'md' }) {
  return (
    <div className={`brand-mark brand-mark--${size}`} aria-hidden="true">
      <svg className="brand-mark-glyph" viewBox="0 0 32 32" role="img">
        <rect className="brand-mark-bar brand-mark-bar--short" x="5.5" y="7" width="12" height="3.2" rx="1.6" />
        <rect className="brand-mark-bar brand-mark-bar--long" x="5.5" y="14.4" width="18.5" height="3.2" rx="1.6" />
        <rect className="brand-mark-bar brand-mark-bar--mid" x="5.5" y="21.8" width="10" height="3.2" rx="1.6" />
        <circle className="brand-mark-badge" cx="24.6" cy="8.8" r="3.9" />
        <path className="brand-mark-check" d="m22.9 8.9 1.25 1.2 2.55-3.05" />
      </svg>
    </div>
  )
}

export default function BrandLockup({ compact = false, subtitle }) {
  return (
    <div className="brand-lockup">
      <BrandMark />
      {!compact && (
        <div className="brand-copy">
          <span className="brand-wordmark">TalentMatch</span>
          {subtitle && <span className="brand-subtitle">{subtitle}</span>}
        </div>
      )}
    </div>
  )
}
