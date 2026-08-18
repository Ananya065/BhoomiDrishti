import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import TopHeader from '../components/TopHeader'
import Badge from '../components/Badge'
import { api } from '../api'

export default function Alerts() {
  const [cases, setCases] = useState([])
  const [statusFilter, setStatusFilter] = useState('')
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()

  useEffect(() => {
    setLoading(true)
    api.listChanges({ status: statusFilter }).then((d) => { setCases(d); setLoading(false) })
  }, [statusFilter])

  return (
    <>
      <TopHeader title="Alerts" subtitle="All detected changes across monitored parcels." />
      <div className="portal-content">
        <div className="card">
          <div className="card-header">
            <h3>All Alerts ({cases.length})</h3>
            <div className="btn-row">
              {['', 'needs_review', 'reviewed', 'dismissed'].map((s) => (
                <button
                  key={s}
                  className="btn"
                  style={statusFilter === s ? { borderColor: 'var(--medium)', color: 'var(--medium)' } : {}}
                  onClick={() => setStatusFilter(s)}
                >
                  {s === '' ? 'All' : s.replace('_', ' ')}
                </button>
              ))}
            </div>
          </div>
          <table className="data-table">
            <thead>
              <tr><th>Case ID</th><th>Location</th><th>Change Type</th><th>Priority</th><th>Status</th></tr>
            </thead>
            <tbody>
              {cases.map((c) => (
                <tr key={c.id} className="clickable" onClick={() => navigate(`/case/${c.id}`)}>
                  <td className="case-id-cell">{c.case_number}</td>
                  <td>{c.location_name}</td>
                  <td>{c.change_type}</td>
                  <td><Badge value={c.priority} /></td>
                  <td><Badge value={c.status} /></td>
                </tr>
              ))}
              {!loading && cases.length === 0 && (
                <tr><td colSpan={5} style={{ textAlign: 'center', color: 'var(--text-faint)' }}>No alerts match this filter.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </>
  )
}
