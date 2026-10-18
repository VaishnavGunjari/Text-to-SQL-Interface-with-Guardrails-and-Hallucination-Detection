import { HelpCircle, ChevronRight } from 'lucide-react'

export default function ClarificationDialog({ options, onSelect }) {
  if (!options?.length) return null

  return (
    <div className="card border-surface-border animate-slide-up">
      <div className="flex items-start gap-3">
        <div className="w-8 h-8 rounded-lg bg-zinc-100 dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 flex items-center justify-center flex-shrink-0">
          <HelpCircle size={16} className="text-zinc-900 dark:text-white" />
        </div>
        <div className="flex-1">
          <h3 className="text-sm font-semibold text-zinc-900 dark:text-white mb-1">Clarification needed</h3>
          <p className="text-xs text-zinc-600 dark:text-zinc-400 mb-4">
            Your question could be interpreted in multiple ways. Please choose the one you mean:
          </p>
          <div className="space-y-2">
            {options.map((opt, i) => (
              <button
                key={i}
                id={`clarification-option-${i}`}
                onClick={() => onSelect(opt.label)}
                className="w-full text-left p-3.5 bg-surface hover:bg-surface-hover
                           border border-surface-border hover:border-zinc-400 dark:hover:border-zinc-500
                           rounded-xl transition-all duration-200 group"
              >
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-zinc-800 dark:text-zinc-200 group-hover:text-black dark:group-hover:text-white transition-colors">
                      {opt.label}
                    </p>
                    {opt.description && (
                      <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-0.5">{opt.description}</p>
                    )}
                    {opt.example_sql && (
                      <p className="text-[11px] font-mono text-zinc-500 mt-1 truncate">
                        {opt.example_sql}
                      </p>
                    )}
                  </div>
                  <ChevronRight size={14} className="text-zinc-400 group-hover:text-black dark:group-hover:text-white transition-colors flex-shrink-0 ml-3" />
                </div>
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
