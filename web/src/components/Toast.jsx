import { useEffect } from 'react'
import { CheckCircle2, XCircle, AlertTriangle, Info, X } from 'lucide-react'

const CONFIG = {
  success: { icon: CheckCircle2, color: 'var(--green-strong)', bg: 'var(--green-soft)' },
  error:   { icon: XCircle,      color: 'var(--red)',          bg: 'var(--red-soft)'   },
  warning: { icon: AlertTriangle,color: 'var(--amber)',        bg: 'var(--amber-soft)' },
  info:    { icon: Info,          color: 'var(--accent-2)',    bg: 'var(--accent-soft)' },
}

export default function Toast({ message, type = 'info', onClose }) {
  const { icon: Icon, color, bg } = CONFIG[type] || CONFIG.info

  useEffect(() => {
    const t = setTimeout(onClose, 3200)
    return () => clearTimeout(t)
  }, [])

  return (
    <div className={`toast toast-${type}`}>
      <div style={{
        width: 28, height: 28, borderRadius: 8,
        background: bg, display:'flex', alignItems:'center', justifyContent:'center', flexShrink:0,
      }}>
        <Icon size={14} color={color} />
      </div>
      <span style={{ flex:1, color:'var(--ink-2)', fontSize:13.5, fontWeight:500 }}>{message}</span>
      <button
        onClick={onClose}
        style={{ background:'none', border:'none', cursor:'pointer', color:'var(--ink-4)', display:'flex', padding:2 }}
      >
        <X size={14} />
      </button>
    </div>
  )
}
