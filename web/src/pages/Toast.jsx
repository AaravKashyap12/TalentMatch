import { useEffect } from 'react'
import { CheckCircle2, AlertCircle, Info, XCircle, X } from 'lucide-react'

const CONFIGS = {
  success: { bg:'var(--bg-1)', border:'rgba(14,184,122,0.3)', accent:'var(--green)', dot:'var(--green)', Icon: CheckCircle2 },
  error:   { bg:'var(--bg-1)', border:'rgba(240,64,64,0.3)',  accent:'var(--red)',   dot:'var(--red)',   Icon: XCircle },
  warning: { bg:'var(--bg-1)', border:'rgba(245,158,11,0.3)', accent:'var(--amber)', dot:'var(--amber)', Icon: AlertCircle },
  info:    { bg:'var(--bg-1)', border:'var(--accent-mid)',     accent:'var(--accent)', dot:'var(--accent)', Icon: Info },
}

export default function Toast({ message, type='info', onClose, autoClose=4000 }) {
  useEffect(() => {
    if (autoClose > 0) {
      const t = setTimeout(onClose, autoClose)
      return () => clearTimeout(t)
    }
  }, [autoClose, onClose])

  const cfg = CONFIGS[type] || CONFIGS.info
  const { bg, border, accent, dot, Icon } = cfg

  return (
    <div
      className="au"
      style={{
        padding:'11px 14px',
        borderRadius:'var(--r-lg)',
        background: bg,
        border:`1px solid ${border}`,
        boxShadow:'var(--sh-xl)',
        display:'flex', alignItems:'center', gap: 10,
        fontSize: 13, fontWeight: 500,
        minWidth: 300, maxWidth: 420,
        pointerEvents:'auto',
        color:'var(--ink-2)',
      }}
    >
      <div style={{
        width: 20, height: 20, borderRadius: 6,
        background:`${dot}18`,
        display:'flex', alignItems:'center', justifyContent:'center', flexShrink: 0,
      }}>
        <Icon size={12} color={dot} />
      </div>
      <span style={{ flex: 1, lineHeight: 1.4 }}>{message}</span>
      <button
        onClick={onClose}
        style={{
          background:'none', border:'none', cursor:'pointer',
          color:'var(--ink-4)', padding: 2, display:'flex',
          borderRadius: 4, transition:'background 0.12s',
        }}
        onMouseEnter={e=>e.currentTarget.style.background='var(--bg-3)'}
        onMouseLeave={e=>e.currentTarget.style.background='none'}
      >
        <X size={13} />
      </button>
    </div>
  )
}