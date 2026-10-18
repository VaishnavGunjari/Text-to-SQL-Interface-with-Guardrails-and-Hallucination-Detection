import { useState } from 'react'
import { ShieldCheck, ShieldAlert, ScanSearch, GitCompare, AlertCircle, CheckCircle2, ChevronDown } from 'lucide-react'

function Section({ icon: Icon, title, iconClass, children, defaultOpen = false }) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <div className="border border-surface-border rounded-xl overflow-hidden bg-surface/40">
      <button
        onClick={() => setOpen(v => !v)}
        className="w-full flex items-center justify-between px-4 py-3 hover:bg-surface-hover transition-colors"
      >
        <div className="flex items-center gap-2.5">
          <Icon size={14} className={iconClass} />
          <span className="text-xs font-semibold text-zinc-800 dark:text-zinc-200">{title}</span>
        </div>
        <ChevronDown size={13} className={`text-zinc-500 transition-transform ${open ? 'rotate-180' : ''}`} />
      </button>
      {open && <div className="px-4 pb-4 pt-1 space-y-2 animate-fade-in">{children}</div>}
    </div>
  )
}

export default function ValidationPanel({ guardrail, hallucination, sanity, multiQuery }) {
  if (!guardrail && !hallucination && !sanity && !multiQuery) return null

  return (
    <div className="card animate-slide-up space-y-2.5">
      <div className="flex items-center gap-2 mb-3">
        <ScanSearch size={14} className="text-zinc-900 dark:text-white" />
        <span className="text-xs font-semibold text-zinc-500 dark:text-zinc-400 uppercase tracking-wider">Validation & Safety</span>
      </div>

      {/* Guardrails */}
      {guardrail && (
        <Section
          icon={guardrail.passed ? ShieldCheck : ShieldAlert}
          title="SQL Guardrails"
          iconClass={guardrail.passed ? 'text-zinc-900 dark:text-white' : 'text-zinc-500 dark:text-zinc-400'}
          defaultOpen={!guardrail.passed}
        >
          {guardrail.passed
            ? <p className="text-xs text-zinc-900 dark:text-white">✓ Query passed all safety checks</p>
            : <p className="text-xs text-zinc-700 dark:text-zinc-300 font-mono">✗ {guardrail.blocked_reason}</p>}
          {guardrail.warnings?.map((w, i) => (
            <div key={i} className="flex gap-2 text-xs text-zinc-500 dark:text-zinc-400">
              <AlertCircle size={11} className="mt-0.5 flex-shrink-0 text-zinc-500" />
              {w}
            </div>
          ))}
        </Section>
      )}

      {/* Hallucination detection */}
      {hallucination && (
        <Section
          icon={hallucination.hallucination_detected ? ShieldAlert : ShieldCheck}
          title="Hallucination Detection"
          iconClass={hallucination.hallucination_detected ? 'text-zinc-500 dark:text-zinc-400' : 'text-zinc-900 dark:text-white'}
          defaultOpen={hallucination.hallucination_detected}
        >
          {/* Schema validation */}
          <div className="flex items-center gap-2 text-xs">
            {hallucination.schema_valid
              ? <CheckCircle2 size={12} className="text-zinc-900 dark:text-white" />
              : <AlertCircle size={12} className="text-zinc-500 dark:text-zinc-400" />}
            <span className={hallucination.schema_valid ? 'text-zinc-900 dark:text-white' : 'text-zinc-700 dark:text-zinc-300'}>
              Schema validation: {hallucination.schema_valid ? 'All tables & columns exist' : 'Invalid references detected'}
            </span>
          </div>
          {hallucination.invalid_tables?.map(t => (
            <p key={t} className="text-xs text-zinc-600 dark:text-zinc-400 font-mono pl-5">✗ Table not found: {t}</p>
          ))}
          {hallucination.invalid_columns?.map((c, i) => (
            <p key={i} className="text-xs text-zinc-600 dark:text-zinc-400 font-mono pl-5">✗ {c.reason}</p>
          ))}

          {/* Back-translation */}
          {hallucination.back_translation && (
            <div className="mt-2.5 pt-2.5 border-t border-surface-border">
              <p className="text-[11px] text-zinc-500 uppercase tracking-wider mb-1 font-semibold">Back-translation</p>
              <p className="text-xs text-zinc-700 dark:text-zinc-300 italic">
                "{hallucination.back_translation.back_translated_question}"
              </p>
              <div className="flex items-center gap-2 mt-1.5">
                <div className="flex-1 h-1 bg-surface-border rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all duration-700 ${
                      hallucination.back_translation.alignment_score >= 0.65 ? 'bg-black dark:bg-white' : 'bg-zinc-300 dark:bg-zinc-700'
                    }`}
                    style={{ width: `${hallucination.back_translation.alignment_score * 100}%` }}
                  />
                </div>
                <span className="text-[11px] text-zinc-500 dark:text-zinc-400 font-mono">
                  {Math.round(hallucination.back_translation.alignment_score * 100)}% aligned
                </span>
              </div>
              <p className="text-[11px] text-zinc-500 mt-1">{hallucination.back_translation.alignment_explanation}</p>
            </div>
          )}

          {hallucination.hallucination_reasons?.map((r, i) => (
            <div key={i} className="flex gap-2 text-xs text-zinc-600 dark:text-zinc-400 mt-1">
              <AlertCircle size={11} className="mt-0.5 flex-shrink-0" />
              {r}
            </div>
          ))}
        </Section>
      )}

      {/* Result sanity */}
      {sanity && (
        <Section
          icon={sanity.passed ? CheckCircle2 : AlertCircle}
          title={`Result Sanity (${Math.round(sanity.pass_rate * 100)}% pass rate)`}
          iconClass={sanity.passed ? 'text-zinc-900 dark:text-white' : 'text-zinc-500 dark:text-zinc-400'}
          defaultOpen={sanity.warnings?.length > 0}
        >
          {sanity.checks?.filter(c => c.severity !== 'info').map((c, i) => (
            <div key={i} className="flex gap-2 text-xs text-zinc-700 dark:text-zinc-300">
              {c.passed ? <CheckCircle2 size={11} className="mt-0.5 flex-shrink-0 text-zinc-900 dark:text-white" /> : <AlertCircle size={11} className="mt-0.5 flex-shrink-0 text-zinc-500 dark:text-zinc-400" />}
              {c.message}
            </div>
          ))}
          {sanity.checks?.filter(c => c.severity === 'info' && !c.passed).map((c, i) => (
            <div key={`info-${i}`} className="flex gap-2 text-xs text-zinc-500">
              <AlertCircle size={11} className="mt-0.5 flex-shrink-0" />
              {c.message}
            </div>
          ))}
        </Section>
      )}

      {/* Multi-query agreement */}
      {multiQuery?.enabled && multiQuery.alternative_sql && (
        <Section
          icon={GitCompare}
          title={
            multiQuery.results_agree === null ? 'Multi-Query (running…)' :
            multiQuery.results_agree ? 'Multi-Query Agreement ✓' : 'Multi-Query Discrepancy ⚠'
          }
          iconClass={
            multiQuery.results_agree === null ? 'text-zinc-400' :
            multiQuery.results_agree ? 'text-zinc-900 dark:text-white' : 'text-zinc-500 dark:text-zinc-400'
          }
          defaultOpen={multiQuery.results_agree === false}
        >
          {multiQuery.results_agree !== null && (
            <p className="text-xs text-zinc-700 dark:text-zinc-300">
              {multiQuery.results_agree
                ? `✓ Independent SQL approaches agree (${Math.round((multiQuery.agreement_score || 1) * 100)}% similarity)`
                : `⚠ ${multiQuery.discrepancy_explanation}`}
            </p>
          )}
          <details className="mt-1">
            <summary className="text-[11px] text-zinc-500 cursor-pointer hover:text-black dark:hover:text-zinc-300 transition-colors">
              View alternative SQL
            </summary>
            <pre className="mt-1.5 p-2.5 bg-surface rounded-lg text-[11px] text-zinc-600 dark:text-zinc-400 font-mono border border-surface-border overflow-x-auto whitespace-pre-wrap">
              {multiQuery.alternative_sql}
            </pre>
          </details>
        </Section>
      )}
    </div>
  )
}
