const BASE = '/api'

async function req(path, opts) {
  const res = await fetch(BASE + path, {
    headers: { 'Content-Type': 'application/json' },
    ...opts,
  })
  if (!res.ok) throw new Error(`${path} failed: ${res.status}`)
  return res.json()
}

export const api = {
  login: (username, password, role) =>
    req('/auth/login', { method: 'POST', body: JSON.stringify({ username, password, role }) }),

  listChanges: (params = {}) => {
    const clean = Object.fromEntries(Object.entries(params).filter(([, v]) => v !== '' && v != null && v !== false))
    const qs = new URLSearchParams(clean).toString()
    return req(`/changes${qs ? '?' + qs : ''}`)
  },
  getCase: (id) => req(`/changes/${id}`),
  detectChange: (body) => req('/detect-change', { method: 'POST', body: JSON.stringify(body) }),
  updateStatus: (id, status) =>
    req(`/changes/${id}/status`, { method: 'PATCH', body: JSON.stringify({ status }) }),
  assignOfficer: (id, assigned_officer) =>
    req(`/changes/${id}/assign`, { method: 'PATCH', body: JSON.stringify({ assigned_officer }) }),
  addNote: (id, author, text) =>
    req(`/changes/${id}/notes`, { method: 'POST', body: JSON.stringify({ author, text }) }),
  getReport: (id) => req(`/changes/${id}/report`),

  summary: () => req('/stats/summary'),
  analyticsSummary: () => req('/analytics/summary'),
  timeline: (location_name) =>
    req(`/timeline${location_name ? '?location_name=' + encodeURIComponent(location_name) : ''}`),
}
