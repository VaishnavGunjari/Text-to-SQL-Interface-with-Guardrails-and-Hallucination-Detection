import { useState, useEffect } from 'react'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { Copy, Check, ChevronDown, ChevronRight, Terminal, Info, Edit3, Play, RotateCcw, Eye } from 'lucide-react'

const monoCodeStyle = {
  'code[class*="language-"]': {
    color: '#f4f4f5',
    background: 'none',
    fontFamily: '"JetBrains Mono", "Fira Code", monospace',
    fontSize: '0.8125rem',
    textAlign: 'left',
    whiteSpace: 'pre',
    wordSpacing: 'normal',
    wordBreak: 'normal',
    wordWrap: 'normal',
    lineHeight: '1.6',
  },
  'pre[class*="language-"]': {
    color: '#f4f4f5',
    background: '#070709',
    fontFamily: '"JetBrains Mono", "Fira Code", monospace',
    fontSize: '0.8125rem',
    margin: 0,
    padding: '1rem',
    overflow: 'auto',
  },
  'keyword': { color: '#ffffff', fontWeight: '700' },
  'boolean': { color: '#ffffff', fontWeight: '600' },
  'number': { color: '#e4e4e7' },
  'string': { color: '#a1a1aa' },
  'char': { color: '#a1a1aa' },
  'operator': { color: '#71717a' },
  'punctuation': { color: '#52525b' },
  'function': { color: '#ffffff', fontWeight: '500' },
  'class-name': { color: '#d4d4d8' },
  'comment': { color: '#52525b', fontStyle: 'italic' },
  'variable': { color: '#d4d4d8' },
  'property': { color: '#d4d4d8' },
}

export default function SQLDisplay({ sql, explanation, tablesUsed, explainPlan, onExecuteCustomSql, loading }) {
  const [copied, setCopied] = useState(false)
  const [showExplain, setShowExplain] = useState(false)
  const [isEditing, setIsEditing] = useState(false)
  const [editedSql, setEditedSql] = useState(sql || '')

  useEffect(() => {
    setEditedSql(sql || '')
  }, [sql])

  const handleCopy = async () => {
    await navigator.clipboard.writeText(isEditing ? editedSql : sql)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const handleRunCustomSql = () => {
    if (!editedSql.trim() || loading) return
    onExecuteCustomSql?.(editedSql.trim())
  }

  const handleReset = () => {
    setEditedSql(sql || '')
  }

  if (!sql) return null

  return (
    <div className="card animate-slide-up space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Terminal size={14} className="text-zinc-900 dark:text-white" />
          <span className="text-xs font-semibold text-zinc-500 dark:text-zinc-400 uppercase tracking-wider">Generated SQL</span>
          {tablesUsed?.length > 0 && (
            <div className="flex items-center gap-1.5 ml-2">
              {tablesUsed.map(t => (
                <span key={t} className="badge-mono text-[10px] font-mono">{t}</span>
              ))}
            </div>
          )}
          {isEditing && (
            <span className="badge-white text-[10px] uppercase font-mono">Editing</span>
          )}
        </div>

        <div className="flex items-center gap-1.5">
          <button
            onClick={() => setIsEditing(v => !v)}
            id="toggle-edit-sql-btn"
            className={`btn-ghost text-xs ${isEditing ? 'border border-zinc-600 bg-surface-hover' : ''}`}
            title={isEditing ? 'View formatted SQL' : 'Edit SQL query for power users'}
          >
            {isEditing ? <Eye size={13} /> : <Edit3 size={13} />}
            <span>{isEditing ? 'Preview' : 'Edit SQL'}</span>
          </button>

          <button
            onClick={handleCopy}
            id="copy-sql-btn"
            className="btn-ghost"
            title="Copy SQL"
          >
            {copied ? <Check size={13} className="text-zinc-900 dark:text-white" /> : <Copy size={13} />}
            <span className="text-xs">{copied ? 'Copied!' : 'Copy'}</span>
          </button>
        </div>
      </div>

      {/* SQL View or Editor */}
      {isEditing ? (
        <div className="space-y-2 animate-fade-in">
          <div className="relative">
            <textarea
              id="custom-sql-editor"
              value={editedSql}
              onChange={e => setEditedSql(e.target.value)}
              rows={5}
              placeholder="SELECT ... write custom SQL here"
              className="w-full bg-[#070709] border border-surface-border rounded-xl p-4 font-mono text-xs text-zinc-200
                         focus:outline-none focus:ring-1 focus:ring-white/40 focus:border-white/50 resize-y leading-relaxed"
            />
          </div>
          <div className="flex items-center justify-between">
            <p className="text-[11px] text-zinc-500">
              Power user mode: SQL will be validated through security guardrails before execution.
            </p>
            <div className="flex items-center gap-2">
              <button
                onClick={handleReset}
                className="btn-ghost text-xs flex items-center gap-1"
                title="Reset to generated SQL"
              >
                <RotateCcw size={12} />
                <span>Reset</span>
              </button>
              <button
                onClick={handleRunCustomSql}
                disabled={!editedSql.trim() || loading}
                id="run-custom-sql-btn"
                className="btn-primary text-xs py-1.5 px-3 flex items-center gap-1.5 shadow-sm"
              >
                <Play size={12} />
                <span>{loading ? 'Executing…' : 'Run Edited SQL'}</span>
              </button>
            </div>
          </div>
        </div>
      ) : (
        <div className="rounded-xl overflow-hidden border border-surface-border">
          <SyntaxHighlighter
            language="sql"
            style={monoCodeStyle}
            customStyle={{
              margin: 0,
              padding: '1rem',
              background: '#070709',
              fontSize: '0.8125rem',
              lineHeight: '1.6',
              fontFamily: '"JetBrains Mono", "Fira Code", monospace',
            }}
            showLineNumbers
            lineNumberStyle={{ color: '#3f3f46', minWidth: '2rem' }}
          >
            {sql}
          </SyntaxHighlighter>
        </div>
      )}

      {/* Explanation */}
      {explanation && (
        <div className="flex gap-2.5 p-3.5 bg-surface hover:bg-surface-hover/70 border border-surface-border rounded-xl transition-colors">
          <Info size={14} className="text-zinc-400 mt-0.5 flex-shrink-0" />
          <p className="text-xs text-zinc-600 dark:text-zinc-300 leading-relaxed">{explanation}</p>
        </div>
      )}

      {/* EXPLAIN Plan toggle */}
      {explainPlan && (
        <div>
          <button
            onClick={() => setShowExplain(v => !v)}
            className="btn-ghost text-xs w-full justify-start"
            id="toggle-explain-btn"
          >
            {showExplain ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
            EXPLAIN Plan
          </button>
          {showExplain && (
            <pre className="mt-2 p-3 bg-surface text-xs text-zinc-500 dark:text-zinc-400 font-mono rounded-xl border border-surface-border overflow-x-auto animate-fade-in whitespace-pre-wrap">
              {explainPlan}
            </pre>
          )}
        </div>
      )}
    </div>
  )
}
