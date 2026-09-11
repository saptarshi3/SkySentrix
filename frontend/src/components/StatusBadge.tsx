interface StatusBadgeProps {
  level: 'NORMAL' | 'WARNING' | 'CRITICAL'
}

export function StatusBadge({ level }: StatusBadgeProps) {
  const classes = {
    NORMAL: 'bg-emerald-900 text-emerald-300 border-emerald-700',
    WARNING: 'bg-amber-900 text-amber-300 border-amber-700',
    CRITICAL: 'bg-rose-900 text-rose-300 border-rose-700',
  }[level]

  return (
    <span className={`rounded-full border px-3 py-1 text-xs font-semibold ${classes}`}>{level}</span>
  )
}
