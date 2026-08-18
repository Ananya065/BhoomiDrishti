import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import TopHeader from '../components/TopHeader'
import Badge from '../components/Badge'
import { api } from '../api'
import CopilotWidget from '../components/CopilotWidget'

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun']
const MONTH_VALUES = [24, 42, 58, 31, 18, 35] // demo trend, matches design reference

export default function Dashboard() {
  const [summary, setSummary] = useState(null)
  const [cases, setCases] = useState([])
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()

  useEffect(() => {
    Promise.all([api.summary(), api.listChanges({ status: 'needs_review' })])
      .then(([s, c]) => { setSummary(s); setCases(c.slice(0, 6)) })
      .finally(() => setLoading(false))
  }, [])

  const maxMonth = Math.max(...MONTH_VALUES)

  return (
    <>
      <TopHeader
        title="Change Detection Control Room"
        subtitle="Real-time monitoring and verification of public parcels and reserved government lands."
        actions={
          <div className="btn-row">
            <button className="btn" onClick={() => navigate('/map')}>Open Satellite Map View</button>
            <button className="btn primary">Generate Weekly Report</button>
          </div>
        }
      />
      <div className="portal-content">
        <div className="stat-row">
          <div className="stat-card">
            <div className="label">Total Alerts Under Review</div>
            <div className="value">{loading ? '—' : summary.total_changes}</div>
            <div className="sub">Total detected changes</div>
          </div>
          <div className="stat-card">
            <div className="label">Requires Verification</div>
            <div className="value" style={{ color: 'var(--high)' }}>{loading ? '—' : summary.needs_review}</div>
            <div className="sub">Requires human verification</div>
          </div>
          <div className="stat-card">
            <div className="label">Field Verified</div>
            <div className="value" style={{ color: 'var(--success)' }}>{loading ? '—' : summary.field_verified}</div>
            <div className="sub">Ground check completed</div>
          </div>
          <div className="stat-card">
            <div className="label">Critical Exception</div>
            <div className="value critical">{loading ? '—' : summary.critical_exceptions}</div>
            <div className="sub">Severe violations flagged</div>
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1.6fr 1fr', gap: 18 }}>
          <div className="card">
            <div className="card-header">
              <h3>Pending Cases Needing Inspection</h3>
              <button className="btn" onClick={() => navigate('/map')}>View all</button>
            </div>
            <table className="data-table">
              <thead>
                <tr><th>Case ID</th><th>Location (Survey No.)</th><th>Change Type</th><th>Severity</th></tr>
              </thead>
              <tbody>
                {cases.map((c) => (
                  <tr key={c.id} className="clickable" onClick={() => navigate(`/case/${c.id}`)}>
                    <td className="case-id-cell">{c.case_number}</td>
                    <td>{c.location_name}</td>
                    <td>{c.change_type}</td>
                    <td><Badge value={c.priority} /></td>
                  </tr>
                ))}
                {!loading && cases.length === 0 && (
                  <tr><td colSpan={4} style={{ textAlign: 'center', color: 'var(--text-faint)' }}>No pending cases.</td></tr>
                )}
              </tbody>
            </table>
          </div>

          <div className="card">
            <div className="card-header"><h3>Detected Land-Use Changes (Last 6 Months)</h3></div>
            <div className="card-body">
              <div className="chart-placeholder">
                {MONTH_VALUES.map((v, i) => (
                  <div className="chart-bar-col" key={i}>
                    <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--text-dim)' }}>{v}</div>
                    <div className="chart-bar" style={{ height: `${(v / maxMonth) * 110}px` }} />
                    <div className="chart-bar-label">{MONTHS[i]}</div>
                  </div>
                ))}
              </div>
              <p style={{ fontSize: 11.5, color: 'var(--text-faint)', marginTop: 6 }}>
                District Hotspot: Ambegaon taluka shows the highest concentration of flagged changes this quarter.
              </p>
            </div>
          </div>
        </div>
      </div>
      <CopilotWidget caseId={null} />
    </>
  )
}
