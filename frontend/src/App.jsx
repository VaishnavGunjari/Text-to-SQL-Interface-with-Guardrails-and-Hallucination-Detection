import { useState, useEffect } from 'react'
import { Database, Activity, AlertCircle, ThumbsUp, ThumbsDown, XCircle, Sun, Moon, BookOpen } from 'lucide-react'
import QueryInput from './components/QueryInput.jsx'
import SQLDisplay from './components/SQLDisplay.jsx'
import ResultsTable from './components/ResultsTable.jsx'
import ConfidenceScore from './components/ConfidenceScore.jsx'
import ValidationPanel from './components/ValidationPanel.jsx'
import QueryHistory from './components/QueryHistory.jsx'
import ClarificationDialog from './components/ClarificationDialog.jsx'
import DocsModal from './components/DocsModal.jsx'
import { useQuery } from './hooks/useQuery.js'

function LoadingSkeleton() {
  return (
    <div className="space-y-4 animate-fade-in">
      {[1,2,3].map(i => (
        <div key={i} className="card shimmer h-24" />
      ))}
    </div>
  )
}

function StatusBanner({ result }) {
  if (!result) return null
  if (result.status === 'blocked') return (
    <div className="card border-zinc-700 bg-zinc-900/80 flex gap-3 animate-slide-up">
      <XCircle size={16} className="text-zinc-300 flex-shrink-0 mt-0.5" />
      <div>
        <p className="text-sm font-semibold text-white">Query Blocked</p>
        <p className="text-xs text-zinc-400 mt-0.5 font-mono">{result.error_message}</p>
      </div>
    </div>
  )
  if (result.status === 'error') return (
    <div className="card border-zinc-700 bg-zinc-900/80 flex gap-3 animate-slide-up">
      <AlertCircle size={16} className="text-zinc-300 flex-shrink-0 mt-0.5" />
      <div>
        <p className="text-sm font-semibold text-white">Execution Error</p>
        <p className="text-xs text-zinc-400 mt-0.5 font-mono">{result.error_message}</p>
      </div>
    </div>
  )
  if (result.status === 'unanswerable') return (
    <div className="card border-zinc-800 bg-zinc-900/50 flex gap-3 animate-slide-up">
      <AlertCircle size={16} className="text-zinc-400 flex-shrink-0 mt-0.5" />
      <div>
        <p className="text-sm font-semibold text-zinc-200">Cannot Answer</p>
        <p className="text-xs text-zinc-400 mt-0.5">{result.unanswerable_reason}</p>
      </div>
    </div>
  )
  return null
}

export default function App() {
  const { result, loading, error, history, runQuery, submitFeedback, loadHistory } = useQuery()
  const [currentQuestion, setCurrentQuestion] = useState('')
  const [dbStatus, setDbStatus] = useState(null)
  const [docsOpen, setDocsOpen] = useState(false)
  const [theme, setTheme] = useState(() => {
    return localStorage.getItem('theme') || 'dark'
  })

  useEffect(() => {
    if (theme === 'light') {
      document.documentElement.classList.add('light')
      document.documentElement.classList.remove('dark')
    } else {
      document.documentElement.classList.add('dark')
      document.documentElement.classList.remove('light')
    }
    localStorage.setItem('theme', theme)
  }, [theme])

  useEffect(() => {
    loadHistory()
    fetch('/v1/health').then(r => r.json()).then(d => setDbStatus(d)).catch(() => {})
  }, [])

  const handleQuery = async (question) => {
    setCurrentQuestion(question)
    await runQuery(question)
  }

  const handleClarification = async (choice) => {
    await runQuery(currentQuestion, { clarificationChoice: choice })
  }

  const handleCustomSql = async (customSql) => {
    await runQuery(currentQuestion || "Custom SQL Execution", { customSql })
  }

  const handleHistorySelect = (item) => {
    setCurrentQuestion(item.question)
  }

  const hasFeedback = result?.status === 'success'

  return (
    <div className="min-h-screen">
      {/* Header */}
      <header className="border-b border-surface-border bg-surface-card/80 backdrop-blur-md sticky top-0 z-10 transition-colors">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 h-14 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-black text-white dark:bg-white dark:text-black flex items-center justify-center border border-zinc-300 dark:border-zinc-700 shadow-sm transition-colors">
              <Database size={16} />
            </div>
            <div>
              <h1 className="text-sm font-bold text-zinc-900 dark:text-white leading-none tracking-tight">
                Text-to-SQL <span className="gradient-text font-black">AI</span>
              </h1>
              <p className="text-[10px] text-zinc-500 leading-none mt-0.5">With Guardrails & Hallucination Detection</p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {dbStatus && (
              <div className="flex items-center gap-1.5 text-xs">
                <div className={`w-2 h-2 rounded-full ${dbStatus.status === 'healthy' ? 'bg-black dark:bg-white shadow-[0_0_8px_rgba(255,255,255,0.9)]' : 'bg-zinc-400 dark:bg-zinc-600'} animate-pulse`} />
                <span className="text-zinc-600 dark:text-zinc-400 font-mono text-[11px] hidden sm:block">
                  {dbStatus.status === 'healthy' ? 'Connected' : 'Disconnected'}
                </span>
              </div>
            )}

            <button
              onClick={() => setTheme(t => t === 'dark' ? 'light' : 'dark')}
              className="btn-ghost flex items-center gap-1.5 border border-surface-border text-xs py-1 px-2.5 rounded-lg transition-all"
              title={theme === 'dark' ? 'Switch to Paper (Light B&W) theme' : 'Switch to Noir (Dark B&W) theme'}
              id="theme-toggle-btn"
            >
              {theme === 'dark' ? (
                <>
                  <Sun size={13} className="text-zinc-300" />
                  <span className="text-zinc-300 font-mono text-[11px]">Paper</span>
                </>
              ) : (
                <>
                  <Moon size={13} className="text-zinc-700" />
                  <span className="text-zinc-700 font-mono text-[11px]">Noir</span>
                </>
              )}
            </button>

            <button
              onClick={() => setDocsOpen(true)}
              className="btn-ghost flex items-center gap-1.5 text-xs py-1 px-2.5 border border-surface-border rounded-lg text-zinc-600 dark:text-zinc-400 hover:text-black dark:hover:text-white transition-colors"
              id="open-docs-btn"
            >
              <BookOpen size={13} />
              <span>API Docs</span>
            </button>
          </div>
        </div>
      </header>

      {/* Main layout */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 py-6">
        <div className="grid grid-cols-1 lg:grid-cols-[1fr_320px] gap-6">

          {/* Left column */}
          <div className="space-y-4 min-w-0">
            {/* Hero text */}
            <div className="mb-2">
              <h2 className="text-2xl font-bold text-zinc-900 dark:text-white tracking-tight">
                Ask your database anything
              </h2>
              <p className="text-sm text-zinc-600 dark:text-zinc-400 mt-1">
                Natural language → validated SQL → transparent confidence score
              </p>
            </div>

            <QueryInput onSubmit={handleQuery} loading={loading} />

            {/* Loading skeleton */}
            {loading && <LoadingSkeleton />}

            {/* Error */}
            {error && !loading && (
              <div className="card border-zinc-700 bg-zinc-900/80 flex gap-3">
                <AlertCircle size={16} className="text-zinc-300 flex-shrink-0 mt-0.5" />
                <p className="text-sm text-zinc-300 font-mono">{error}</p>
              </div>
            )}

            {/* Result */}
            {result && !loading && (
              <div className="space-y-4 animate-fade-in">
                <StatusBanner result={result} />

                {/* Clarification */}
                {result.status === 'clarification' && (
                  <ClarificationDialog
                    options={result.clarification_options}
                    onSelect={handleClarification}
                  />
                )}

                {/* SQL */}
                {result.sql && (
                  <SQLDisplay
                    sql={result.sql}
                    explanation={result.sql_explanation}
                    tablesUsed={result.tables_used}
                    explainPlan={result.execution?.explain_plan}
                    onExecuteCustomSql={handleCustomSql}
                    loading={loading}
                  />
                )}

                {/* Results table */}
                {result.columns?.length > 0 && (
                  <ResultsTable
                    columns={result.columns}
                    rows={result.rows}
                    execution={result.execution}
                  />
                )}

                {/* Feedback bar */}
                {hasFeedback && !result.feedback && (
                  <div className="card flex items-center justify-between animate-fade-in">
                    <div className="flex items-center gap-2">
                      <Activity size={13} className="text-zinc-400" />
                      <span className="text-xs text-zinc-600 dark:text-zinc-300">Was this result correct?</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => submitFeedback(result.query_id, 'correct')}
                        id="main-feedback-correct"
                        className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg bg-zinc-800 text-white hover:bg-zinc-700 border border-zinc-600 transition-colors"
                      >
                        <ThumbsUp size={12} /> Correct
                      </button>
                      <button
                        onClick={() => submitFeedback(result.query_id, 'incorrect')}
                        id="main-feedback-incorrect"
                        className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg bg-zinc-900 text-zinc-400 hover:text-white hover:bg-zinc-800 border border-zinc-700 transition-colors"
                      >
                        <ThumbsDown size={12} /> Incorrect
                      </button>
                    </div>
                  </div>
                )}

                {result.feedback && (
                  <div className="card flex items-center gap-2 animate-fade-in">
                    {result.feedback === 'correct'
                      ? <ThumbsUp size={13} className="text-zinc-900 dark:text-white" />
                      : <ThumbsDown size={13} className="text-zinc-500 dark:text-zinc-400" />}
                    <span className="text-xs text-zinc-600 dark:text-zinc-300">
                      Marked as <span className="text-zinc-900 dark:text-white font-semibold">{result.feedback}</span>
                    </span>
                  </div>
                )}

                {/* Validation panel (mobile: after table) */}
                <div className="lg:hidden">
                  <div className="space-y-4">
                    <ConfidenceScore confidence={result.confidence} />
                    <ValidationPanel
                      guardrail={result.guardrail}
                      hallucination={result.hallucination}
                      sanity={result.sanity}
                      multiQuery={result.multi_query}
                    />
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Right column (desktop) */}
          <div className="hidden lg:flex flex-col gap-4 min-w-0">
            {result && !loading ? (
              <>
                <ConfidenceScore confidence={result.confidence} />
                <ValidationPanel
                  guardrail={result.guardrail}
                  hallucination={result.hallucination}
                  sanity={result.sanity}
                  multiQuery={result.multi_query}
                />
              </>
            ) : (
              <div className="card h-32 flex items-center justify-center">
                <p className="text-xs text-zinc-500 text-center">
                  Confidence score and<br />validation details appear here
                </p>
              </div>
            )}
            <QueryHistory
              history={history}
              onSelect={handleHistorySelect}
              onFeedback={submitFeedback}
              activeId={result?.query_id}
            />
          </div>
        </div>

        {/* History (mobile only) */}
        <div className="lg:hidden mt-4">
          <QueryHistory
            history={history}
            onSelect={handleHistorySelect}
            onFeedback={submitFeedback}
            activeId={result?.query_id}
          />
        </div>
      </main>

      {/* In-app Documentation Modal */}
      <DocsModal isOpen={docsOpen} onClose={() => setDocsOpen(false)} />
    </div>
  )
}
