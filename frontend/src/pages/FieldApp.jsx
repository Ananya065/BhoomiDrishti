import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import PhoneFrame from '../components/PhoneFrame'
import Badge from '../components/Badge'
import { api } from '../api'

const CHECKLIST = [
  { label: 'Navigate to Parcel Site', hint: 'GPS guidance enabled' },
  { label: 'Capture Verification Photo', hint: 'Required: 1 wide angle, 1 detail shot' },
  { label: 'Confirm Ground GPS Lock', hint: 'Accuracy tolerance < 5 meters' },
  { label: 'Record Land Use Observations', hint: '' },
  { label: 'Compare against Registry Records', hint: '' },
]

export default function FieldApp() {
  const [cases, setCases] = useState([])
  const [active, setActive] = useState(null)
  const [checked, setChecked] = useState({})

  useEffect(() => {
    api.listChanges({ status: 'needs_review' }).then((d) => {
      setCases(d.slice(0, 3))
      setActive(d[0] || null)
    })
  }, [])

  const toggle = (i) => setChecked((prev) => ({ ...prev, [i]: !prev[i] }))
  const doneCount = Object.values(checked).filter(Boolean).length

  return (
    <div className="frame-page">
      <div className="frame-nav">
        <Link to="/dashboard">← Portal</Link>
        <Link to="/field-app" className="active">Field Verification App</Link>
        <Link to="/citizen-app">Citizen Reporting App</Link>
      </div>

      <PhoneFrame
        headerTitle="Good morning, Inspector Sharma"
        headerSub="Ambegaon Sector · 3 inspections assigned for today."
        tabs={['Home', 'Inspections', 'Reports', 'Profile']}
        activeTab="Inspections"
      >
        <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.04em', textTransform: 'uppercase', color: 'var(--text-faint)', marginBottom: 8 }}>
          Today's Assignments
        </div>
        {cases.map((c, i) => (
          <div key={c.id} className="assignment-card" onClick={() => setActive(c)} style={{ cursor: 'pointer', borderColor: active?.id === c.id ? 'var(--medium)' : undefined }}>
            <div className="top-row">
              <span className="case-id">{c.case_number}</span>
              <Badge value={c.priority} />
            </div>
            <div className="survey">Survey No. {c.survey_number}, {c.village}</div>
            <div className="time">Scheduled: {['09:30 AM', '11:15 AM', '02:00 PM'][i] || '—'}</div>
          </div>
        ))}

        {active && (
          <>
            <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.04em', textTransform: 'uppercase', color: 'var(--text-faint)', margin: '18px 0 8px' }}>
              Verification Checklist — {active.case_number}
            </div>
            <div className="pin-map">📍 GPS map preview</div>
            {CHECKLIST.map((item, i) => (
              <div className="checklist-item" key={i} onClick={() => toggle(i)}>
                <div className={`checklist-box ${checked[i] ? 'checked' : ''}`}>{checked[i] ? '✓' : ''}</div>
                <div>
                  <div className="checklist-label">{item.label}</div>
                  {item.hint && <div className="checklist-hint">{item.hint}</div>}
                </div>
              </div>
            ))}
            <button className="btn success block" style={{ marginTop: 14 }} disabled={doneCount < CHECKLIST.length}>
              Submit System Findings Verification
            </button>
            <button className="btn block" style={{ marginTop: 8 }}>Save as Offline Draft</button>
          </>
        )}
      </PhoneFrame>
    </div>
  )
}
