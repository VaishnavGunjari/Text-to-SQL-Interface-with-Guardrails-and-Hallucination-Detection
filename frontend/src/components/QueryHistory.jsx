import { History, ThumbsUp, ThumbsDown, Clock } from 'lucide-react'

function StatusBadge({ status }) {
  const map = {
    success: 'badge-green',
    blocked: 'badge-red',
    error: 'badge-red',
    clarification: 'badge-yellow',
    unanswerable: 'badge-gray',
  }
  return <span className={map[status] || 'badge-gray'}>{status}</span>
}

function FeedbackBadge({ feedback }) {
  if (!feedback) return null
  return feedback === 'correct'
    ? <span className="badge-green"><ThumbsUp size={9} /> Correct</span>
    : <span className="badge-red"><ThumbsDown size={9} /> Incorrect</span>
}

export default function QueryHistory({ history, onSelect, onFeedback, activeId }) {
  if (!history?.length) return (
    <div className="card">
      <div className="flex items-center gap-2 mb-4">
        <History size={14} className="text-zinc-400 dark:text-zinc-500" />
        <span className="text-xs font-semibold text-zinc-500 dark:text-zinc-400 uppercase tracking-wider">Query History</span>
      </div>
      <p className="text-xs text-zinc-500 text-center py-6 font-mono">No queries yet. Run your first query!</p>
    </div>
  )

  return (
    <div className="card">
      <div className="flex items-center gap-2 mb-4">
        <History size={14} className="text-zinc-900 dark:text-white" />
        <span className="text-xs font-semibold text-zinc-500 dark:text-zinc-400 uppercase tracking-wider">Query History</span>
        <span className="badge-mono text-[10px]">{history.length}</span>
      </div>

      <div className="space-y-1.5 max-h-[400px] overflow-y-auto pr-1">
        {history.map((item) => (
          <div
            key={item.query_id}
            className={`p-3 rounded-xl border cursor-pointer transition-all duration-150 group
              ${activeId === item.query_id
                ? 'border-zinc-900 dark:border-white/60 bg-surface-hover/90 shadow-[0_0_15px_rgba(255,255,255,0.06)]'
                : 'border-surface-border hover:border-zinc-400 dark:hover:border-zinc-500 hover:bg-surface-hover'}`}
            onClick={() => onSelect?.(item)}
            id={`history-item-${item.query_id}`}
          >
            <div className="flex items-start justify-between gap-2">
              <p className="text-xs text-zinc-800 dark:text-zinc-200 line-clamp-2 flex-1 leading-relaxed">
                {item.question}
              </p>
              <div className="flex items-center gap-1 flex-shrink-0">
                <StatusBadge status={item.status} />
              </div>
            </div>

            <div className="flex items-center justify-between mt-2.5">
              <div className="flex items-center gap-2">
                {item.confidence_percentage != null && (
                  <span className={`text-[10px] font-mono ${
                    item.confidence_percentage >= 85 ? 'text-zinc-900 dark:text-white font-bold' :
                    item.confidence_percentage >= 65 ? 'text-zinc-700 dark:text-zinc-300' : 'text-zinc-400 dark:text-zinc-500'
                  }`}>
                    {item.confidence_percentage}%
                  </span>
                )}
                {item.row_count != null && (
                  <span className="text-[10px] text-zinc-500 font-mono">{item.row_count} rows</span>
                )}
                <FeedbackBadge feedback={item.feedback} />
              </div>
              <span className="text-[10px] text-zinc-500 flex items-center gap-1 font-mono">
                <Clock size={9} />
                {new Date(item.timestamp).toLocaleTimeString()}
              </span>
            </div>

            {/* Feedback buttons (only for success queries without feedback) */}
            {item.status === 'success' && !item.feedback && (
              <div className="flex items-center gap-1 mt-2 pt-2 border-t border-surface-border/50 opacity-0 group-hover:opacity-100 transition-opacity">
                <span className="text-[10px] text-zinc-500 mr-1">Mark as:</span>
                <button
                  onClick={(e) => { e.stopPropagation(); onFeedback?.(item.query_id, 'correct') }}
                  className="flex items-center gap-1 text-[10px] px-2 py-0.5 rounded bg-zinc-200 dark:bg-zinc-800 text-zinc-900 dark:text-white hover:bg-zinc-300 dark:hover:bg-zinc-700 border border-zinc-300 dark:border-zinc-600 transition-colors"
                  id={`feedback-correct-${item.query_id}`}
                >
                  <ThumbsUp size={9} /> Correct
                </button>
                <button
                  onClick={(e) => { e.stopPropagation(); onFeedback?.(item.query_id, 'incorrect') }}
                  className="flex items-center gap-1 text-[10px] px-2 py-0.5 rounded bg-zinc-100 dark:bg-zinc-900 text-zinc-500 dark:text-zinc-400 hover:text-black dark:hover:text-white border border-zinc-300 dark:border-zinc-700 transition-colors"
                  id={`feedback-incorrect-${item.query_id}`}
                >
                  <ThumbsDown size={9} /> Incorrect
                </button>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
