const BASE_URL = '/v1'

async function request(path, options = {}) {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || `HTTP ${res.status}`)
  }
  return res.json()
}

export const api = {
  query: (body) => request('/query', { method: 'POST', body: JSON.stringify(body) }),
  getSchema: () => request('/schema'),
  getHistory: (limit = 50) => request(`/history?limit=${limit}`),
  submitFeedback: (queryId, feedback, userNote) =>
    request(`/history/${queryId}/feedback`, {
      method: 'PATCH',
      body: JSON.stringify({ feedback, user_note: userNote }),
    }),
  health: () => request('/health'),
}
