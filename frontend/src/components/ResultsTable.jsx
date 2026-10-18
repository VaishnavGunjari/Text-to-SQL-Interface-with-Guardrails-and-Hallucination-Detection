import { useState } from 'react'
import { Table, ChevronUp, ChevronDown, ChevronsUpDown, Download, Clock, Rows } from 'lucide-react'

export default function ResultsTable({ columns, rows, execution }) {
  const [sortCol, setSortCol] = useState(null)
  const [sortDir, setSortDir] = useState('asc')
  const [page, setPage] = useState(0)
  const PAGE_SIZE = 20

  if (!columns?.length) return null

  const handleSort = (col) => {
    if (sortCol === col) {
      setSortDir(d => d === 'asc' ? 'desc' : 'asc')
    } else {
      setSortCol(col)
    }
    setPage(0)
  }

  const sorted = sortCol
    ? [...rows].sort((a, b) => {
        const va = a[sortCol], vb = b[sortCol]
        if (va === null) return 1
        if (vb === null) return -1
        const cmp = va < vb ? -1 : va > vb ? 1 : 0
        return sortDir === 'asc' ? cmp : -cmp
      })
    : rows

  const paged = sorted.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE)
  const totalPages = Math.ceil(rows.length / PAGE_SIZE)

  const handleExportCSV = () => {
    const header = columns.join(',')
    const body = rows.map(r => columns.map(c => {
      const v = r[c]
      if (v === null || v === undefined) return ''
      if (typeof v === 'string' && v.includes(',')) return `"${v}"`
      return v
    }).join(',')).join('\n')
    const blob = new Blob([header + '\n' + body], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url; a.download = 'query_results.csv'; a.click()
    URL.revokeObjectURL(url)
  }

  const SortIcon = ({ col }) => {
    if (sortCol !== col) return <ChevronsUpDown size={11} className="text-zinc-400 dark:text-zinc-600" />
    return sortDir === 'asc'
      ? <ChevronUp size={11} className="text-zinc-900 dark:text-white" />
      : <ChevronDown size={11} className="text-zinc-900 dark:text-white" />
  }

  return (
    <div className="card animate-slide-up space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Table size={14} className="text-zinc-900 dark:text-white" />
          <span className="text-xs font-semibold text-zinc-500 dark:text-zinc-400 uppercase tracking-wider">Results</span>
          <span className="badge-mono">{rows.length.toLocaleString()} rows</span>
          {execution?.was_limited && (
            <span className="badge-outline">Truncated at limit</span>
          )}
        </div>
        <div className="flex items-center gap-3">
          {execution && (
            <div className="flex items-center gap-3 text-xs text-zinc-500 font-mono">
              <span className="flex items-center gap-1">
                <Clock size={11} />
                {execution.execution_time_ms}ms
              </span>
              <span className="flex items-center gap-1">
                <Rows size={11} />
                {columns.length} cols
              </span>
            </div>
          )}
          <button onClick={handleExportCSV} className="btn-ghost" id="export-csv-btn">
            <Download size={12} />
            <span className="text-xs">CSV</span>
          </button>
        </div>
      </div>

      <div className="overflow-x-auto rounded-xl border border-surface-border">
        <table className="w-full text-xs">
          <thead>
            <tr className="bg-surface border-b border-surface-border">
              {columns.map(col => (
                <th
                  key={col}
                  onClick={() => handleSort(col)}
                  className="px-3.5 py-3 text-left text-zinc-600 dark:text-zinc-400 font-medium cursor-pointer
                             hover:text-black dark:hover:text-white hover:bg-surface-hover transition-colors select-none whitespace-nowrap"
                >
                  <span className="flex items-center gap-1">
                    {col}
                    <SortIcon col={col} />
                  </span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {paged.map((row, ri) => (
              <tr
                key={ri}
                className="border-b border-surface-border/40 hover:bg-surface-hover/80 transition-colors"
              >
                {columns.map(col => (
                  <td key={col} className="px-3.5 py-2.5 text-zinc-800 dark:text-zinc-300 font-mono max-w-[200px] truncate" title={String(row[col] ?? '')}>
                    {row[col] === null
                      ? <span className="text-zinc-400 dark:text-zinc-600 italic">null</span>
                      : typeof row[col] === 'boolean'
                        ? <span className={row[col] ? 'text-black dark:text-white font-semibold' : 'text-zinc-400 dark:text-zinc-500'}>{String(row[col])}</span>
                        : String(row[col])}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between text-xs text-zinc-500">
          <span>Showing {page * PAGE_SIZE + 1}–{Math.min((page + 1) * PAGE_SIZE, rows.length)} of {rows.length}</span>
          <div className="flex gap-1">
            <button
              onClick={() => setPage(p => Math.max(0, p - 1))}
              disabled={page === 0}
              className="px-2.5 py-1 rounded-lg border border-surface-border hover:bg-surface-hover disabled:opacity-30 transition-colors"
            >
              ←
            </button>
            {Array.from({ length: totalPages }, (_, i) => (
              <button
                key={i}
                onClick={() => setPage(i)}
                className={`px-2.5 py-1 rounded-lg border transition-all text-xs font-mono ${
                  i === page
                    ? 'border-black bg-black text-white dark:border-white dark:bg-white dark:text-black font-semibold shadow-sm'
                    : 'border-surface-border text-zinc-600 dark:text-zinc-400 hover:text-black dark:hover:text-white hover:bg-surface-hover'
                }`}
              >
                {i + 1}
              </button>
            )).slice(Math.max(0, page - 2), page + 3)}
            <button
              onClick={() => setPage(p => Math.min(totalPages - 1, p + 1))}
              disabled={page >= totalPages - 1}
              className="px-2.5 py-1 rounded-lg border border-surface-border hover:bg-surface-hover disabled:opacity-30 transition-colors"
            >
              →
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
