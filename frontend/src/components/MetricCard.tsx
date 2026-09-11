interface MetricCardProps {
  label: string
  value: string
  subtitle?: string
}

export function MetricCard({ label, value, subtitle }: MetricCardProps) {
  return (
    <div className="rounded-lg border border-slate-800 bg-slate-900 p-3 shadow-sm">
      <div className="text-xs uppercase tracking-wide text-slate-400">{label}</div>
      <div className="mt-1 text-2xl font-semibold text-slate-100">{value}</div>
      {subtitle ? <div className="mt-1 text-xs text-slate-500">{subtitle}</div> : null}
    </div>
  )
}
