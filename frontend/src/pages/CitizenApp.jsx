import React, { useState } from 'react'
import { Link } from 'react-router-dom'
import PhoneFrame from '../components/PhoneFrame'

const TYPES = ['Unauthorized Construction', 'Encroachment', 'Land Use Change', 'Other Activity']

export default function CitizenApp() {
  const [changeType, setChangeType] = useState(null)
  const [anonymous, setAnonymous] = useState(true)
  const [submitted, setSubmitted] = useState(false)

  return (
    <div className="frame-page">
      <div className="frame-nav">
        <Link to="/dashboard">← Portal</Link>
        <Link to="/field-app">Field Verification App</Link>
        <Link to="/citizen-app" className="active">Citizen Reporting App</Link>
      </div>

      <PhoneFrame
        headerTitle="Help Protect Public Land"
        headerSub="Report suspected unauthorized activity on government land. Your identity is fully protected."
        offline={false}
      >
        {submitted ? (
          <>
            <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.04em', textTransform: 'uppercase', color: 'var(--text-faint)', marginBottom: 10 }}>
              Track My Reports
            </div>
            <div className="report-track-item">
              <div className="title">Report #CR2026-0391</div>
              <div className="desc">Encroachment reported near Ambegaon Public Forest Boundary</div>
              <div className="date">Submitted: Jul 12 · Officer Assigned</div>
            </div>
            <button className="btn block" style={{ marginTop: 10 }} onClick={() => setSubmitted(false)}>+ Submit another report</button>
          </>
        ) : (
          <>
            <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--navy-800)', marginBottom: 8 }}>
              Step 1: Point Out Affected Land
            </div>
            <div className="pin-map">📍 Drag pin to location</div>
            <button className="btn block" style={{ marginBottom: 10 }}>Use My Current GPS Location</button>
            <div className="field-group">
              <label>Or Enter Address / Survey Number</label>
              <input type="text" defaultValue="Ambegaon, Pune, Maharashtra (Survey No. 142/3)" />
            </div>

            <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--navy-800)', margin: '14px 0 4px' }}>
              What type of change is this?
            </div>
            <div className="type-grid">
              {TYPES.map((t) => (
                <div key={t} className={`type-option ${changeType === t ? 'selected' : ''}`} onClick={() => setChangeType(t)}>
                  {t}
                </div>
              ))}
            </div>

            <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12, margin: '12px 0' }}>
              <input type="checkbox" checked={anonymous} onChange={() => setAnonymous(!anonymous)} />
              Submit Anonymously
            </label>
            <p style={{ fontSize: 10.5, color: 'var(--text-faint)', marginBottom: 14 }}>
              Your personal details will not be shared. Reports are legally protected under official
              government public-asset acts. False reporting is subject to penalty.
            </p>

            <div className="btn-row">
              <button className="btn" style={{ flex: 1 }}>Cancel</button>
              <button className="btn primary" style={{ flex: 1 }} disabled={!changeType} onClick={() => setSubmitted(true)}>
                Next: Add Details
              </button>
            </div>
          </>
        )}
      </PhoneFrame>
    </div>
  )
}
