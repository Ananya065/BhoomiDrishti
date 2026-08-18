import React, { useEffect, useState } from 'react'
import TopHeader from '../components/TopHeader'
import { api } from '../api'

const TREND = [
  { month: 'Jan', detected: 24, resolved: 16 },
  { month: 'Feb', detected: 42, resolved: 28 },
  { month: 'Mar', detected: 58, resolved: 39 },
  { month: 'Apr', detected: 31, resolved: 22 },
  { month: 'May', detected: 18, resolved: 14 },
  { month: 'Jun', detected: 35, resolved: 27 },
]

export default function Reports() {
  const [data, setData] = useState(null)

  useEffect(() => { api.analyticsSummary().then(setData) }, [])

  if (!data) return <div className="loading-inline">Loading analytics…</div>

  const maxTrend = Math.max(...TREND.map((t) => t.detected))
  const hotspots = Object.entries(data.by_village_hotspot).sort((a, b) => b[1] - a[1])

  return (
    <>
      <TopHeader
        title="Analytics &amp; Reports"
        subtitle="Pune District · Jan 2026 – Jul 2026"
        actions={
          <div className="btn-row">
            <button className="btn">Download CSV</button>
            <button className="btn primary">Export Executive PDF</button>
          </div>
        }
      />
      <div className="portal-content">
        <div className="stat-row">
          <div className="stat-card">
            <div className="label">Total Cases Registered</div>
            <div className="value">{data.total_cases}</div>
            <div className="sub">Pune District</div>
          </div>
          <div className="stat-card">
            <div className="label">Resolution Rate</div>
            <div className="value" style={{ color: 'var(--success)' }}>{data.resolution_rate_pct}%</div>
            <div className="sub">Field checked &amp; closed</div>
          </div>
          <div className="stat-card">
            <div className="label">Avg. Resolution Time</div>
            <div className="value">{data.avg_resolution_days} Days</div>
            <div className="sub">Target limit: 30 days</div>
          </div>
          <div className="stat-card">
            <div className="label">Pending Verification</div>
            <div className="value" style={{ color: 'var(--high)' }}>{data.pending_verification} Cases</div>
            <div className="sub">Needs field visit</div>
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 18, marginBottom: 18 }}>
          <div className="card">
            <div className="card-header"><h3>District Change Detection Hotspots</h3></div>
            <div className="card-body">
              {hotspots.map(([village, count]) => (
                <div key={village} className="category-row">
                  <div className="category-name">{village}</div>
                  <div className="category-track">
                    <div className="category-fill" style={{ width: `${(count / (hotspots[0]?.[1] || 1)) * 100}%`, background: 'var(--medium)' }} />
                  </div>
                  <div className="category-frac">{count} cases</div>
                </div>
              ))}
            </div>
          </div>

          <div className="card">
            <div className="card-header"><h3>6-Month Trend: Detected vs Resolved</h3></div>
            <div className="card-body">
              <div className="chart-placeholder">
                {TREND.map((t) => (
                  <div className="chart-bar-col" key={t.month}>
                    <div style={{ display: 'flex', gap: 3, alignItems: 'flex-end', height: 110 }}>
                      <div className="chart-bar" style={{ height: `${(t.detected / maxTrend) * 100}px`, width: 14 }} />
                      <div className="chart-bar secondary" style={{ height: `${(t.resolved / maxTrend) * 100}px`, width: 14 }} />
                    </div>
                    <div className="chart-bar-label">{t.month}</div>
                  </div>
                ))}
              </div>
              <div style={{ display: 'flex', gap: 16, fontSize: 11, color: 'var(--text-dim)', marginTop: 4 }}>
                <span><span style={{ display: 'inline-block', width: 8, height: 8, background: 'var(--medium)', borderRadius: 2, marginRight: 5 }} />Detected</span>
                <span><span style={{ display: 'inline-block', width: 8, height: 8, background: 'var(--success)', borderRadius: 2, marginRight: 5 }} />Resolved</span>
              </div>
            </div>
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 18 }}>
          <div className="card">
            <div className="card-header"><h3>Case Verification Speed by Category</h3></div>
            <div className="card-body">
              {Object.entries(data.category_breakdown).map(([cat, v]) => (
                <div key={cat} className="category-row">
                  <div className="category-name" style={{ textTransform: 'capitalize' }}>{cat}</div>
                  <div className="category-track">
                    <div className="category-fill" style={{ width: `${v.total ? (v.resolved / v.total) * 100 : 0}%` }} />
                  </div>
                  <div className="category-frac">{v.resolved} / {v.total} Resolved</div>
                </div>
              ))}
            </div>
          </div>

          <div className="card">
            <div className="card-header"><h3>Executive Findings Summary</h3></div>
            <div className="card-body exec-summary">
              For the quarter ending July 2026, satellite system findings detected a concentration
              of unauthorized layouts near the Ambegaon public sector. Overall resolution rate stands
              at {data.resolution_rate_pct}%, within Government compliance goals. Encroachment
              verification protocols continue to keep high-risk land-mutation cases under active review.
              All findings remain subject to field verification and official land-record cross-checks
              before any administrative action is issued.
            </div>
          </div>
        </div>
      </div>
    </>
  )
}
