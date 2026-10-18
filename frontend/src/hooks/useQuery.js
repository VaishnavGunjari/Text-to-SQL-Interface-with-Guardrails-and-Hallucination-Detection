import { useState, useCallback } from 'react'
import { api } from '../services/api'

export function useQuery() {
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [history, setHistory] = useState([])

  const runQuery = useCallback(async (question, options = {}) => {
    setLoading(true)
    setError(null)
    try {
      const data = await api.query({
        question,
        clarification_choice: options.clarificationChoice || null,
        enable_multi_query: options.enableMultiQuery !== false,
        max_rows: options.maxRows || 100,
        custom_sql: options.customSql || null,
      })
      setResult(data)
      // Prepend to local history
      setHistory(prev => [data, ...prev].slice(0, 50))
      return data
    } catch (e) {
      setError(e.message)
      return null
    } finally {
      setLoading(false)
    }
  }, [])

  const submitFeedback = useCallback(async (queryId, feedback) => {
    await api.submitFeedback(queryId, feedback)
    setResult(prev => prev?.query_id === queryId ? { ...prev, feedback } : prev)
    setHistory(prev => prev.map(h => h.query_id === queryId ? { ...h, feedback } : h))
  }, [])

  const loadHistory = useCallback(async () => {
    try {
      const items = await api.getHistory()
      setHistory(items)
    } catch (e) {
      console.error('Failed to load history', e)
    }
  }, [])

  return { result, loading, error, history, runQuery, submitFeedback, loadHistory }
}
