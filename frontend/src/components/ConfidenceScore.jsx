import { Shield, CheckCircle, XCircle, Activity } from 'lucide-react'

function SignalRow({ signal }) {
  const getStatusIcon = () => {
    if (signal.passed === null) return <Activity size={13} className="text-zinc-400 dark:text-zinc-600" />
    if (signal.passed) return <CheckCircle size={13} className="text-zinc-900 dark:text-white" />
    return <XCircle size={13} className="text-zinc-400 dark:text-zinc-500" />
  }

  const getBarColor = () => {
    if (signal.passed === null) return 'bg-zinc-200 dark:bg-zinc-800'
    if (signal.passed) return 'bg-black dark:bg-white'
    return 'bg-zinc-300 dark:bg-zinc-700'
  }

  const pct = Math.round((signal.earned_points / signal.max_points) * 100)

  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {getStatusIcon()}
          <span className="text-xs text-zinc-800 dark:text-zinc-200">{signal.display_name}</span>
        </div>
        <span className="text-xs text-zinc-500 dark:text-zinc-400 font-mono">
          {signal.earned_points}/{signal.max_points}
        </span>
      </div>
      <div className="h-1 bg-surface-border rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-700 ${getBarColor()}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      {signal.detail && (
        <p className="text-[11px] text-zinc-500 pl-5">{signal.detail}</p>
      )}
    </div>
  )
}

export default function ConfidenceScore({ confidence }) {
  if (!confidence) return null

  const { percentage, label, signals, summary } = confidence

  const getLabelBadge = () => {
    if (label === 'High') return 'badge-white'
    if (label === 'Medium') return 'badge-mono'
    return 'badge-outline'
  }

  const circumference = 2 * Math.PI * 28
  const strokeDashoffset = circumference - (percentage / 100) * circumference

  return (
    <div className="card animate-slide-up space-y-4">
      <div className="flex items-center gap-2">
        <Shield size={14} className="text-zinc-900 dark:text-white" />
        <span className="text-xs font-semibold text-zinc-500 dark:text-zinc-400 uppercase tracking-wider">Confidence Score</span>
      </div>

      {/* Score display */}
      <div className="flex items-center gap-5">
        {/* Ring */}
        <div className="relative flex-shrink-0">
          <svg width="80" height="80" className="-rotate-90">
            <circle cx="40" cy="40" r="28" fill="none" stroke="var(--color-surface-border)" strokeWidth="6" />
            <circle
              cx="40" cy="40" r="28" fill="none"
              stroke="var(--ring-stroke)" strokeWidth="6"
              strokeDasharray={circumference}
              strokeDashoffset={strokeDashoffset}
              strokeLinecap="round"
              className="transition-all duration-1000 ease-out"
            />
          </svg>
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span className="text-lg font-bold text-zinc-900 dark:text-white leading-none font-mono">{percentage}%</span>
          </div>
        </div>

        {/* Label and summary */}
        <div>
          <div className="flex items-center gap-2 mb-1.5">
            <span className="text-xl font-bold text-zinc-900 dark:text-white font-mono">{percentage}%</span>
            <span className={getLabelBadge()}>{label} Confidence</span>
          </div>
          <p className="text-xs text-zinc-600 dark:text-zinc-400 leading-relaxed">{summary}</p>
        </div>
      </div>

      {/* Signal breakdown */}
      <div className="pt-3 border-t border-surface-border space-y-3">
        <p className="text-[11px] text-zinc-500 uppercase tracking-wider font-semibold">Score Breakdown</p>
        {signals?.map(s => (
          <SignalRow key={s.name} signal={s} />
        ))}
      </div>
    </div>
  )
}
