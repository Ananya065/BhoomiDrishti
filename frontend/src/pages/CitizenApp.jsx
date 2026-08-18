import React, { useState } from 'react'
import { Link } from 'react-router-dom'
import PhoneFrame from '../components/PhoneFrame'
import GpsMap from '../components/GpsMap'

const TYPES = ['Unauthorized Construction', 'Encroachment', 'Land Use Change', 'Other Activity']

const GPS_OPTS = { enableHighAccuracy: true, maximumAge: 5000, timeout: 10000 }

export default function CitizenApp() {
  const [changeType, setChangeType] = useState(null)
  const [anonymous, setAnonymous]   = useState(true)
  const [submitted, setSubmitted]   = useState(false)
  const [address, setAddress]       = useState('')

  // GPS state
  const [gpsPosition, setGpsPosition]         = useState(null)   // { lat, lng, accuracy }
  const [selectedPosition, setSelectedPosition] = useState(null)  // { lat, lng } — manual or GPS
  const [gpsLoading, setGpsLoading]            = useState(false)
  const [gpsError, setGpsError]               = useState(null)   // string | null

  // ── GPS: request location only when user clicks the button ─────────────────
  const requestGps = () => {
    if (!navigator.geolocation) {
      setGpsError('Geolocation is not supported by your browser.')
      return
    }
    setGpsLoading(true)
    setGpsError(null)

    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const { latitude: lat, longitude: lng, accuracy } = pos.coords
        setGpsPosition({ lat, lng, accuracy })
        setSelectedPosition({ lat, lng })
        setGpsLoading(false)
      },
      (err) => {
        setGpsLoading(false)
        if (err.code === err.PERMISSION_DENIED) {
          setGpsError('Location access was not allowed.')
        } else if (err.code === err.TIMEOUT) {
          setGpsError('Unable to determine your current location (request timed out).')
        } else {
          setGpsError('Unable to determine your current location.')
        }
      },
      GPS_OPTS
    )
  }

  // ── Manual map click: update selected position ──────────────────────────────
  const handleMapClick = (lat, lng) => {
    setSelectedPosition({ lat, lng })
    setGpsError(null)
  }

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
            <button className="btn block" style={{ marginTop: 10 }} onClick={() => setSubmitted(false)}>
              + Submit another report
            </button>
          </>
        ) : (
          <>
            {/* ── Step 1: Location ─────────────────────────────────────────── */}
            <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--navy-800)', marginBottom: 8 }}>
              Step 1: Point Out Affected Land
            </div>

            {/* Map — always shown; clicking it selects a location */}
            <div style={{ marginBottom: 8, borderRadius: 8, overflow: 'hidden', border: '1px solid var(--border)' }}>
              <GpsMap
                mode="citizen"
                gpsPosition={gpsPosition}
                selectedPosition={selectedPosition}
                onLocationSelect={handleMapClick}
                height={200}
              />
            </div>

            {/* GPS status / coordinates */}
            {gpsPosition && !gpsError && (
              <div style={{
                background: '#edfdf4', border: '1px solid #27ae60', borderRadius: 6,
                padding: '7px 10px', fontSize: 11, marginBottom: 8, color: '#1e7e34'
              }}>
                📍 <strong>Location detected ✓</strong><br />
                {gpsPosition.lat.toFixed(4)}° N, {gpsPosition.lng.toFixed(4)}° E
                &nbsp;·&nbsp;Accuracy: ±{Math.round(gpsPosition.accuracy)} m
                <div style={{ color: '#555', marginTop: 3, fontSize: 10.5 }}>
                  You can also tap the map to select a different location.
                </div>
              </div>
            )}

            {selectedPosition && !gpsPosition && (
              <div style={{
                background: '#f0f4ff', border: '1px solid var(--medium)', borderRadius: 6,
                padding: '7px 10px', fontSize: 11, marginBottom: 8, color: '#2c5fbb'
              }}>
                📌 <strong>Location selected</strong>&nbsp;
                {selectedPosition.lat.toFixed(4)}°, {selectedPosition.lng.toFixed(4)}°
              </div>
            )}

            {gpsError && (
              <div style={{
                background: '#fff5f5', border: '1px solid #e74c3c', borderRadius: 6,
                padding: '7px 10px', fontSize: 11, marginBottom: 8, color: '#c0392b'
              }}>
                ⚠️ {gpsError}
                <button className="btn" style={{ marginLeft: 10, padding: '2px 10px', fontSize: 11 }} onClick={requestGps}>
                  Try Again
                </button>
              </div>
            )}

            {/* GPS button — only triggers on click, never on mount */}
            {!gpsPosition && (
              <button
                className="btn block"
                style={{ marginBottom: 8 }}
                onClick={requestGps}
                disabled={gpsLoading}
              >
                {gpsLoading ? '🔄 Detecting location…' : '📍 Use My Current GPS Location'}
              </button>
            )}

            {/* Manual address fallback */}
            <div className="field-group">
              <label>Or Enter Address / Survey Number</label>
              <input
                type="text"
                value={address}
                onChange={(e) => setAddress(e.target.value)}
                placeholder="e.g. Ambegaon, Survey No. 142/3"
              />
            </div>

            {/* ── Step 2: Change type ───────────────────────────────────────── */}
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
              Your personal details will not be shared. Reports are legally protected under official government
              public-asset acts. False reporting is subject to penalty.
            </p>

            <div className="btn-row">
              <button className="btn" style={{ flex: 1 }}>Cancel</button>
              <button
                className="btn primary"
                style={{ flex: 1 }}
                disabled={!changeType || (!selectedPosition && !address.trim())}
                onClick={() => setSubmitted(true)}
              >
                Next: Add Details
              </button>
            </div>
          </>
        )}
      </PhoneFrame>
    </div>
  )
}
