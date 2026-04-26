export function BrandMark({ size = 'md' }) {
  return (
    <div className={`brand-mark brand-mark--${size}`} aria-hidden="true">
      <svg className="brand-mark-glyph" viewBox="0 0 32 32" role="img">
        <path className="brand-mark-link" d="M10.2 11.2 16 20.2l5.8-9" />
        <circle className="brand-mark-node" cx="9.5" cy="9.5" r="3.2" />
        <circle className="brand-mark-node" cx="22.5" cy="9.5" r="3.2" />
        <circle className="brand-mark-node brand-mark-node--primary" cx="16" cy="22.5" r="3.8" />
        <path className="brand-mark-check" d="m14.2 22.4 1.25 1.25 2.55-3" />
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
