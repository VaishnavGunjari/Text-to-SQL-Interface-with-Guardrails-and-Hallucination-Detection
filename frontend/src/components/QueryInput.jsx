import { useState, useRef } from 'react'
import { Send, Zap, Loader2, ChevronDown } from 'lucide-react'

const EXAMPLE_QUESTIONS = [
  "How many active users do we have?",
  "What is the total MRR from active subscriptions?",
  "Show me the top 5 organizations by MRR",
  "How many users signed up this month?",
  "Which organizations are on the enterprise plan?",
  "Show me all failed invoices",
  "What events happened in the last 7 days?",
  "Which features are most used?",
]

export default function QueryInput({ onSubmit, loading, disabled }) {
  const [question, setQuestion] = useState('')
  const [showExamples, setShowExamples] = useState(false)
  const textareaRef = useRef(null)

  const handleSubmit = (e) => {
    e?.preventDefault()
    if (!question.trim() || loading) return
    onSubmit(question.trim())
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
  }

  const pickExample = (q) => {
    setQuestion(q)
    setShowExamples(false)
    textareaRef.current?.focus()
  }

  return (
    <div className="card animate-slide-up">
      <div className="flex items-center gap-2 mb-3">
        <div className="w-6 h-6 rounded bg-zinc-100 dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 flex items-center justify-center">
          <Zap size={13} className="text-zinc-900 dark:text-white" />
        </div>
        <span className="text-xs font-semibold text-zinc-500 dark:text-zinc-400 uppercase tracking-wider">Natural Language Query</span>
      </div>

      <form onSubmit={handleSubmit}>
        <div className="relative">
          <textarea
            ref={textareaRef}
            id="query-input"
            value={question}
            onChange={e => setQuestion(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask a question about your data… e.g. 'What are the top 5 organizations by MRR this month?'"
            rows={3}
            disabled={loading || disabled}
            className="w-full bg-surface border border-surface-border rounded-xl px-4 py-3.5 pr-14
                       text-zinc-900 dark:text-zinc-100 placeholder-zinc-400 dark:placeholder-zinc-500 text-sm font-sans resize-none
                       focus:outline-none focus:ring-1 focus:ring-zinc-400 dark:focus:ring-white/30 focus:border-zinc-500 dark:focus:border-white/50
                       transition-all duration-200 disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={!question.trim() || loading || disabled}
            id="submit-query-btn"
            className="absolute bottom-3 right-3 btn-primary px-3 py-2 text-sm shadow-md"
          >
            {loading
              ? <Loader2 size={16} className="animate-spin" />
              : <Send size={16} />}
          </button>
        </div>
      </form>

      <div className="mt-3 flex items-center justify-between">
        <p className="text-xs text-zinc-500">Press Enter to run · Shift+Enter for new line</p>
        <button
          onClick={() => setShowExamples(v => !v)}
          className="btn-ghost text-xs"
          id="toggle-examples-btn"
        >
          Examples
          <ChevronDown size={12} className={`transition-transform ${showExamples ? 'rotate-180' : ''}`} />
        </button>
      </div>

      {showExamples && (
        <div className="mt-3 pt-3 border-t border-surface-border grid grid-cols-1 sm:grid-cols-2 gap-1.5 animate-fade-in">
          {EXAMPLE_QUESTIONS.map((q, i) => (
            <button
              key={i}
              onClick={() => pickExample(q)}
              className="text-left text-xs text-zinc-700 dark:text-zinc-400 hover:text-black dark:hover:text-white px-3 py-2.5
                         bg-surface hover:bg-surface-hover border border-surface-border hover:border-zinc-400 dark:hover:border-zinc-500
                         rounded-lg transition-all duration-150"
            >
              {q}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
