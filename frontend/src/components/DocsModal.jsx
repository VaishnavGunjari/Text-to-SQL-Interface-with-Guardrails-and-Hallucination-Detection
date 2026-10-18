import { useState } from 'react'
import { X, BookOpen, Shield, Database, Terminal, Layers, ExternalLink, Code2, Check, Copy } from 'lucide-react'

export default function DocsModal({ isOpen, onClose }) {
  const [activeTab, setActiveTab] = useState('overview')
  const [copiedIndex, setCopiedIndex] = useState(null)

  if (!isOpen) return null

  const copyToClipboard = (text, index) => {
    navigator.clipboard.writeText(text)
    setCopiedIndex(index)
    setTimeout(() => setCopiedIndex(null), 2000)
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-6 bg-black/80 backdrop-blur-sm animate-fade-in">
      <div className="relative w-full max-w-4xl max-h-[90vh] bg-surface-card border border-surface-border rounded-2xl shadow-2xl flex flex-col overflow-hidden text-zinc-200">
        
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-surface-border bg-surface/50">
          <div className="flex items-center gap-2.5">
            <div className="w-7 h-7 rounded-lg bg-zinc-800 text-white border border-zinc-700 flex items-center justify-center">
              <BookOpen size={14} />
            </div>
            <div>
              <h2 className="text-sm font-bold text-zinc-900 dark:text-white leading-none">Documentation & API Reference</h2>
              <p className="text-[11px] text-zinc-500 mt-0.5">Text-to-SQL AI Architecture, Endpoints & Data Model</p>
            </div>
          </div>
          
          <div className="flex items-center gap-2">
            <a
              href="/docs"
              target="_blank"
              rel="noreferrer"
              className="btn-ghost flex items-center gap-1.5 text-xs py-1 px-2.5 border border-surface-border rounded-lg"
              title="Open FastAPI Swagger UI"
            >
              <span>Swagger UI</span>
              <ExternalLink size={12} />
            </a>
            <button
              onClick={onClose}
              className="btn-ghost p-1.5 rounded-lg text-zinc-400 hover:text-white"
              id="close-docs-modal"
            >
              <X size={16} />
            </button>
          </div>
        </div>

        {/* Navigation Tabs */}
        <div className="flex items-center gap-1 px-5 border-b border-surface-border bg-surface/30 overflow-x-auto text-xs font-medium">
          {[
            { id: 'overview', label: 'Architecture', icon: Layers },
            { id: 'api', label: 'API Reference', icon: Terminal },
            { id: 'guardrails', label: 'Safety & Guardrails', icon: Shield },
            { id: 'schema', label: 'Database Schema', icon: Database },
            { id: 'examples', label: 'Query Examples', icon: Code2 },
          ].map(tab => {
            const Icon = tab.icon
            const isActive = activeTab === tab.id
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 px-3 py-3 border-b-2 transition-all whitespace-nowrap ${
                  isActive
                    ? 'border-zinc-900 dark:border-white text-zinc-900 dark:text-white font-semibold'
                    : 'border-transparent text-zinc-500 hover:text-zinc-800 dark:hover:text-zinc-300'
                }`}
              >
                <Icon size={13} />
                <span>{tab.label}</span>
              </button>
            )
          })}
        </div>

        {/* Modal Body */}
        <div className="flex-1 overflow-y-auto p-5 sm:p-6 space-y-6 text-xs text-zinc-300 leading-relaxed font-sans">
          
          {/* TAB 1: OVERVIEW & ARCHITECTURE */}
          {activeTab === 'overview' && (
            <div className="space-y-6 animate-fade-in">
              <div>
                <h3 className="text-base font-bold text-zinc-900 dark:text-white">8-Stage Defense-in-Depth Pipeline</h3>
                <p className="text-zinc-600 dark:text-zinc-400 mt-1">
                  Every natural language query traverses an 8-stage verification pipeline to guarantee safety, zero hallucinations, and high confidence before execution.
                </p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {[
                  { step: "01", title: "Few-Shot LLM Translation", desc: "Injects live schema context and few-shot exemplars to convert natural language to ANSI SQL. Catches vague questions and outputs clarification choices." },
                  { step: "02", title: "AST SQL Guardrails", desc: "Strictly parses SQL with sqlglot. Blocks all DDL/DML mutations (INSERT, UPDATE, DELETE, DROP), rejects multi-statements, and injects default limits." },
                  { step: "03", title: "Hallucination Verification", desc: "Extracts all table/column AST nodes and verifies existence against the PostgreSQL catalog. Runs reverse back-translation to measure semantic query alignment." },
                  { step: "04", title: "Read-Only Execution", desc: "Runs inside a read-only transaction (SET TRANSACTION READ ONLY) with statement timeout protection and captures execution plans." },
                  { step: "05", title: "Result Sanity Checks", desc: "Validates statistical sanity: detects empty results on non-empty domains, out-of-bounds metrics, extreme negative values, and abnormal null ratios." },
                  { step: "06", title: "Multi-Query Consensus", desc: "Generates an independent alternative SQL query formulation and calculates set similarity between result sets to confirm agreement." },
                  { step: "07", title: "Confidence Scoring", desc: "Computes a transparent 0-100% score across 5 weighted signals (Guardrails, Schema, Back-translation, Sanity, Multi-query)." },
                  { step: "08", title: "Audit & Human Feedback", desc: "Persists query history with execution times, confidence breakdowns, and enables user thumbs up/down correctness feedback." },
                ].map(item => (
                  <div key={item.step} className="p-3.5 rounded-xl border border-surface-border bg-surface/40 space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-[10px] font-bold text-zinc-400 bg-zinc-800 border border-zinc-700 px-1.5 py-0.5 rounded">{item.step}</span>
                      <h4 className="font-semibold text-zinc-900 dark:text-white">{item.title}</h4>
                    </div>
                    <p className="text-zinc-500 dark:text-zinc-400 text-[11px] leading-normal">{item.desc}</p>
                  </div>
                ))}
              </div>

              <div className="p-4 rounded-xl border border-surface-border bg-surface/50 space-y-2">
                <h4 className="font-bold text-zinc-900 dark:text-white">Security & Read-Only Guarantees</h4>
                <p className="text-zinc-500 dark:text-zinc-400 text-[11px]">
                  The engine is designed from the ground up to prevent data tampering and SQL injection. Write operations are blocked at both the AST guardrail layer and by the database transaction connection pool itself.
                </p>
              </div>
            </div>
          )}

          {/* TAB 2: API REFERENCE */}
          {activeTab === 'api' && (
            <div className="space-y-6 animate-fade-in">
              <div>
                <h3 className="text-base font-bold text-zinc-900 dark:text-white">REST API Endpoints</h3>
                <p className="text-zinc-600 dark:text-zinc-400 mt-1">
                  Base URL: <code className="font-mono text-zinc-200 bg-zinc-800 px-1.5 py-0.5 rounded">http://localhost:8000/v1</code>
                </p>
              </div>

              {/* Endpoint 1 */}
              <div className="p-4 rounded-xl border border-surface-border bg-surface/40 space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="bg-zinc-800 text-white font-mono text-[10px] font-bold px-2 py-0.5 rounded border border-zinc-700">POST</span>
                    <span className="font-mono text-xs font-semibold text-zinc-900 dark:text-white">/v1/query</span>
                  </div>
                  <span className="badge-mono text-[10px]">Core Query</span>
                </div>
                <p className="text-zinc-500 dark:text-zinc-400 text-[11px]">
                  Converts a natural language question into validated SQL, executes it, and returns results with confidence score and safety breakdown.
                </p>

                <div className="space-y-1.5">
                  <span className="text-[10px] uppercase font-bold text-zinc-500 tracking-wider">Request Payload:</span>
                  <pre className="p-3 bg-surface rounded-lg border border-surface-border font-mono text-[11px] text-zinc-300 overflow-x-auto">
{`{
  "question": "What is the total MRR from active subscriptions?",
  "enable_multi_query": true,
  "max_rows": 100
}`}
                  </pre>
                </div>

                <div className="space-y-1.5">
                  <span className="text-[10px] uppercase font-bold text-zinc-500 tracking-wider">Response:</span>
                  <pre className="p-3 bg-surface rounded-lg border border-surface-border font-mono text-[11px] text-zinc-300 overflow-x-auto">
{`{
  "query_id": "c1f7a0b3-90d1-4e89-a2de-6df37b420011",
  "status": "success",
  "sql": "SELECT SUM(mrr) AS total_mrr FROM subscriptions WHERE status = 'active'",
  "columns": ["total_mrr"],
  "rows": [{"total_mrr": 48250.00}],
  "confidence": { "percentage": 98, "label": "High" }
}`}
                  </pre>
                </div>
              </div>

              {/* Endpoint 2 */}
              <div className="p-4 rounded-xl border border-surface-border bg-surface/40 space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="bg-zinc-800 text-white font-mono text-[10px] font-bold px-2 py-0.5 rounded border border-zinc-700">PATCH</span>
                    <span className="font-mono text-xs font-semibold text-zinc-900 dark:text-white">/v1/history/&#123;query_id&#125;/feedback</span>
                  </div>
                  <span className="badge-mono text-[10px]">Feedback</span>
                </div>
                <p className="text-zinc-500 dark:text-zinc-400 text-[11px]">
                  Submits human evaluation feedback (correct or incorrect) for a specific query execution.
                </p>
                <pre className="p-3 bg-surface rounded-lg border border-surface-border font-mono text-[11px] text-zinc-300 overflow-x-auto">
{`{
  "feedback": "correct",
  "user_note": "Expected calculation matches actual data"
}`}
                </pre>
              </div>

              {/* Endpoint 3 & 4 */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div className="p-3.5 rounded-xl border border-surface-border bg-surface/40 space-y-1.5">
                  <div className="flex items-center gap-2">
                    <span className="bg-zinc-800 text-white font-mono text-[10px] font-bold px-2 py-0.5 rounded border border-zinc-700">GET</span>
                    <span className="font-mono text-xs font-semibold text-zinc-900 dark:text-white">/v1/schema</span>
                  </div>
                  <p className="text-zinc-500 dark:text-zinc-400 text-[11px]">
                    Returns the complete active database schema with tables, data types, and foreign key relations.
                  </p>
                </div>

                <div className="p-3.5 rounded-xl border border-surface-border bg-surface/40 space-y-1.5">
                  <div className="flex items-center gap-2">
                    <span className="bg-zinc-800 text-white font-mono text-[10px] font-bold px-2 py-0.5 rounded border border-zinc-700">GET</span>
                    <span className="font-mono text-xs font-semibold text-zinc-900 dark:text-white">/v1/history</span>
                  </div>
                  <p className="text-zinc-500 dark:text-zinc-400 text-[11px]">
                    Lists the latest 50 queries executed, including row counts, status, and feedback states.
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* TAB 3: SAFETY & GUARDRAILS */}
          {activeTab === 'guardrails' && (
            <div className="space-y-6 animate-fade-in">
              <div>
                <h3 className="text-base font-bold text-zinc-900 dark:text-white">Guardrails & Hallucination Prevention</h3>
                <p className="text-zinc-600 dark:text-zinc-400 mt-1">
                  How our system enforces query safety and ensures zero hallucinated metrics.
                </p>
              </div>

              <div className="space-y-3">
                <div className="p-4 rounded-xl border border-surface-border bg-surface/40 space-y-2">
                  <h4 className="font-bold text-zinc-900 dark:text-white flex items-center gap-2">
                    <Shield size={14} />
                    Blocked Operations Policy
                  </h4>
                  <p className="text-zinc-500 dark:text-zinc-400 text-[11px]">
                    The query parser uses <code className="font-mono text-zinc-300">sqlglot</code> to analyze statement tokens. Any query containing the following statements is rejected immediately:
                  </p>
                  <div className="flex flex-wrap gap-1.5 pt-1">
                    {["DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "TRUNCATE", "CREATE", "GRANT", "REVOKE", "EXEC", "EXECUTE", "COPY"].map(kw => (
                      <span key={kw} className="font-mono text-[10px] px-2 py-0.5 rounded bg-zinc-900 text-zinc-300 border border-zinc-700">{kw}</span>
                    ))}
                  </div>
                </div>

                <div className="p-4 rounded-xl border border-surface-border bg-surface/40 space-y-2">
                  <h4 className="font-bold text-zinc-900 dark:text-white flex items-center gap-2">
                    <Layers size={14} />
                    Reverse Back-Translation
                  </h4>
                  <p className="text-zinc-500 dark:text-zinc-400 text-[11px]">
                    To confirm that the generated SQL faithfully answers what the user requested, the SQL query is fed into a reverse translation prompt asking what question it answers. The generated question is then compared against the user's input with semantic alignment scoring. If the similarity is low (&lt;65%), the query is flagged for review.
                  </p>
                </div>

                <div className="p-4 rounded-xl border border-surface-border bg-surface/40 space-y-2">
                  <h4 className="font-bold text-zinc-900 dark:text-white flex items-center gap-2">
                    <Terminal size={14} />
                    Confidence Score Formula (100 Points)
                  </h4>
                  <div className="overflow-x-auto">
                    <table className="w-full text-[11px] text-left">
                      <thead>
                        <tr className="border-b border-surface-border text-zinc-400">
                          <th className="py-1.5">Verification Signal</th>
                          <th className="py-1.5">Max Weight</th>
                          <th className="py-1.5">Passing Requirement</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-surface-border/40 text-zinc-300">
                        <tr>
                          <td className="py-1.5 font-medium">SQL Syntax &amp; Guardrails</td>
                          <td className="py-1.5 font-mono">20 pts</td>
                          <td className="py-1.5 text-zinc-500">Read-only SELECT, authorized tables only</td>
                        </tr>
                        <tr>
                          <td className="py-1.5 font-medium">Schema Coverage &amp; Validity</td>
                          <td className="py-1.5 font-mono">20 pts</td>
                          <td className="py-1.5 text-zinc-500">All tables &amp; columns confirmed in schema</td>
                        </tr>
                        <tr>
                          <td className="py-1.5 font-medium">Question Alignment (Back-Translation)</td>
                          <td className="py-1.5 font-mono">25 pts</td>
                          <td className="py-1.5 text-zinc-500">Semantic alignment &ge; 65%</td>
                        </tr>
                        <tr>
                          <td className="py-1.5 font-medium">Result Sanity Checks</td>
                          <td className="py-1.5 font-mono">20 pts</td>
                          <td className="py-1.5 text-zinc-500">Passes statistical anomaly &amp; boundary tests</td>
                        </tr>
                        <tr>
                          <td className="py-1.5 font-medium">Multi-Query Consensus</td>
                          <td className="py-1.5 font-mono">15 pts</td>
                          <td className="py-1.5 text-zinc-500">Alternative query formulation matches primary</td>
                        </tr>
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* TAB 4: DATABASE SCHEMA */}
          {activeTab === 'schema' && (
            <div className="space-y-6 animate-fade-in">
              <div>
                <h3 className="text-base font-bold text-zinc-900 dark:text-white">SaaS Analytics Database Schema</h3>
                <p className="text-zinc-600 dark:text-zinc-400 mt-1">
                  The data model comprises 7 relational entities in PostgreSQL representing SaaS operations.
                </p>
              </div>

              <div className="space-y-4">
                {[
                  {
                    table: 'organizations',
                    desc: 'Customer organizations and companies',
                    columns: 'id (PK), name, plan, country, industry, employee_count, created_at, churned_at'
                  },
                  {
                    table: 'users',
                    desc: 'Individual user accounts belonging to organizations',
                    columns: 'id (PK), org_id (FK), email, name, role, is_active, created_at, last_login_at'
                  },
                  {
                    table: 'subscriptions',
                    desc: 'Recurring subscriptions, plans, and MRR metrics',
                    columns: 'id (PK), org_id (FK), plan, status, mrr, currency, billing_interval, started_at, ended_at'
                  },
                  {
                    table: 'invoices',
                    desc: 'Invoices, payment charges, and due dates',
                    columns: 'id (PK), org_id (FK), subscription_id (FK), amount, currency, status, due_date, paid_at'
                  },
                  {
                    table: 'events',
                    desc: 'Telemetry actions (login, export, report view, etc.)',
                    columns: 'id (PK), user_id (FK), org_id (FK), event_type, page, created_at'
                  },
                  {
                    table: 'features',
                    desc: 'Product capabilities and tier entitlements',
                    columns: 'id (PK), name, description, plan_required'
                  },
                  {
                    table: 'feature_usage',
                    desc: 'Usage volume of specific features per organization',
                    columns: 'id (PK), org_id (FK), feature_id (FK), used_at, usage_count'
                  },
                ].map(item => (
                  <div key={item.table} className="p-3.5 rounded-xl border border-surface-border bg-surface/40 space-y-1">
                    <div className="flex items-center justify-between">
                      <span className="font-mono text-xs font-bold text-zinc-900 dark:text-white">{item.table}</span>
                      <span className="text-[10px] text-zinc-500 font-mono">Table</span>
                    </div>
                    <p className="text-zinc-500 dark:text-zinc-400 text-[11px]">{item.desc}</p>
                    <p className="font-mono text-[10px] text-zinc-400 pt-1 border-t border-surface-border/50">
                      {item.columns}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* TAB 5: QUERY EXAMPLES */}
          {activeTab === 'examples' && (
            <div className="space-y-6 animate-fade-in">
              <div>
                <h3 className="text-base font-bold text-zinc-900 dark:text-white">Sample Queries &amp; Generated SQL</h3>
                <p className="text-zinc-600 dark:text-zinc-400 mt-1">
                  Try asking questions like these directly in the natural language query input.
                </p>
              </div>

              <div className="space-y-3">
                {[
                  {
                    question: "How many active users do we have?",
                    sql: "SELECT COUNT(*) AS active_users FROM users WHERE is_active = TRUE;"
                  },
                  {
                    question: "What is the total MRR from active subscriptions?",
                    sql: "SELECT SUM(mrr) AS total_mrr FROM subscriptions WHERE status = 'active';"
                  },
                  {
                    question: "Show me the top 5 organizations by MRR",
                    sql: "SELECT o.name, s.mrr, s.plan FROM organizations o JOIN subscriptions s ON o.id = s.org_id WHERE s.status = 'active' ORDER BY s.mrr DESC LIMIT 5;"
                  },
                  {
                    question: "Which organizations are on the enterprise plan?",
                    sql: "SELECT id, name, industry, country, employee_count FROM organizations WHERE plan = 'enterprise' ORDER BY name ASC;"
                  },
                  {
                    question: "Show me all failed invoices",
                    sql: "SELECT i.id, o.name AS organization, i.amount, i.due_date, i.created_at FROM invoices i JOIN organizations o ON i.org_id = o.id WHERE i.status = 'failed' ORDER BY i.created_at DESC;"
                  }
                ].map((item, idx) => (
                  <div key={idx} className="p-3.5 rounded-xl border border-surface-border bg-surface/40 space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="font-semibold text-zinc-900 dark:text-white">"{item.question}"</span>
                      <button
                        onClick={() => copyToClipboard(item.sql, idx)}
                        className="btn-ghost flex items-center gap-1 text-[10px] py-1 px-2 border border-surface-border rounded"
                      >
                        {copiedIndex === idx ? <Check size={11} className="text-white" /> : <Copy size={11} />}
                        <span>{copiedIndex === idx ? 'Copied' : 'Copy SQL'}</span>
                      </button>
                    </div>
                    <pre className="p-2.5 bg-surface rounded-lg font-mono text-[11px] text-zinc-300 border border-surface-border overflow-x-auto">
                      {item.sql}
                    </pre>
                  </div>
                ))}
              </div>
            </div>
          )}

        </div>

        {/* Modal Footer */}
        <div className="flex items-center justify-between px-5 py-3 border-t border-surface-border bg-surface/60 text-xs">
          <span className="text-[11px] text-zinc-500 font-mono">v1.0.0 · Production Ready</span>
          <button
            onClick={onClose}
            className="btn-primary text-xs py-1.5 px-4"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  )
}
