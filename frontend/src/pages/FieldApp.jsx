import React, { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import PhoneFrame from '../components/PhoneFrame'
import Badge from '../components/Badge'
import GpsMap, { haversineMetres } from '../components/GpsMap'
import { api } from '../api'

const GPS_OPTS = { enableHighAccuracy: true, maximumAge: 5000, timeout: 10000 }

const CHECKLIST_BASE = [
  { label: 'Navigate to Parcel Site',          hint: 'GPS guidance enabled' },
  { label: 'Capture Verification Photo',        hint: 'Required: 1 wide angle, 1 detail shot' },
  { label: 'Confirm Ground GPS Lock',           hint: 'Accuracy tolerance < 5 meters', gpsRequired: true },
  { label: 'Record Land Use Observations',      hint: '' },
  { label: 'Compare against Registry Records',  hint: '' },
]

export default function FieldApp() {
  const [cases, setCases]   = useState([])
  const [active, setActive] = useState(null)
  const [checked, setChecked] = useState({})

  // GPS state
  const [gpsPosition, setGpsPosition] = useState(null)   // { lat, lng, accuracy }
  const [gpsError, setGpsError]       = useState(null)   // string | null
  const [gpsLoading, setGpsLoading]   = useState(false)

  const watchIdRef = useRef(null)

  // ── Load cases on mount ───────────────────────────────────────────────────
  useEffect(() => {
    api.listChanges({ status: 'needs_review' }).then((d) => {
      setCases(d.slice(0, 3))
      setActive(d[0] || null)
    })
  }, [])

  // ── Start watchPosition when an active case is selected ───────────────────
  useEffect(() => {
    if (!active) return

    // Clean up any previous watcher
    if (watchIdRef.current !== null) {
      navigator.geolocation.clearWatch(watchIdRef.current)
      watchIdRef.current = null
    }

    if (!navigator.geolocation) {
      setGpsError('Geolocation is not supported by your browser.')
      return
    }

    setGpsLoading(true)
    setGpsError(null)
    setGpsPosition(null)

    // First: get immediate position
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const { latitude: lat, longitude: lng, accuracy } = pos.coords
        setGpsPosition({ lat, lng, accuracy })
        setGpsLoading(false)
      },
      (err) => {
        setGpsLoading(false)
        handleGpsError(err)
      },
      GPS_OPTS
    )

    // Then: live tracking
    watchIdRef.current = navigator.geolocation.watchPosition(
      (pos) => {
        const { latitude: lat, longitude: lng, accuracy } = pos.coords
        setGpsPosition({ lat, lng, accuracy })
        setGpsLoading(false)
        setGpsError(null)
      },
      (err) => {
        handleGpsError(err)
      },
      GPS_OPTS
    )

    // Cleanup when case changes or component unmounts
    return () => {
      if (watchIdRef.current !== null) {
        navigator.geolocation.clearWatch(watchIdRef.current)
        watchIdRef.current = null
      }
    }
  }, [active?.id]) // re-run only when active case changes

  // Also clean up watchPosition on component unmount
  useEffect(() => {
    return () => {
      if (watchIdRef.current !== null) {
        navigator.geolocation.clearWatch(watchIdRef.current)
        watchIdRef.current = null
      }
    }
  }, [])

  const handleGpsError = (err) => {
    setGpsLoading(false)
    if (err.code === err.PERMISSION_DENIED) {
      setGpsError('Location access is required for field verification.')
    } else if (err.code === err.TIMEOUT) {
      setGpsError('Unable to determine your current location (request timed out).')
    } else {
      setGpsError('Unable to determine your current location.')
    }
  }

  const retryGps = () => {
    // Restart GPS for the active case by toggling active (triggers useEffect)
    setGpsError(null)
    if (!active) return
    setGpsLoading(true)
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const { latitude: lat, longitude: lng, accuracy } = pos.coords
        setGpsPosition({ lat, lng, accuracy })
        setGpsLoading(false)
      },
      (err) => handleGpsError(err),
      GPS_OPTS
    )
  }

  // ── Target parcel coords from active case ─────────────────────────────────
  const targetPosition = active?.latitude && active?.longitude
    ? { lat: active.latitude, lng: active.longitude }
    : null

  // ── Distance calculation ──────────────────────────────────────────────────
  const distanceM = gpsPosition && targetPosition
    ? haversineMetres(gpsPosition.lat, gpsPosition.lng, targetPosition.lat, targetPosition.lng)
    : null

  const formatDistance = (m) => {
    if (m === null) return null
    if (m < 1000) return `${Math.round(m)} m`
    return `${(m / 1000).toFixed(2)} km`
  }

  // ── GPS lock quality ──────────────────────────────────────────────────────
  const gpsLocked = gpsPosition !== null
  const gpsWeak   = gpsPosition && gpsPosition.accuracy > 20

  // ── Checklist toggle; "Confirm Ground GPS Lock" requires actual GPS ────────
  const toggle = (i) => {
    const item = CHECKLIST_BASE[i]
    if (item.gpsRequired && !gpsLocked) return  // can't manually check GPS item without real lock
    setChecked((prev) => ({ ...prev, [i]: !prev[i] }))
  }

  // Auto-check GPS lock item when GPS is obtained
  useEffect(() => {
    if (gpsLocked) {
      setChecked((prev) => ({ ...prev, 2: true }))
    } else {
      setChecked((prev) => ({ ...prev, 2: false }))
    }
  }, [gpsLocked])

  const doneCount = Object.values(checked).filter(Boolean).length

  // ── Navigate to parcel ────────────────────────────────────────────────────
  const navigateToParcel = () => {
    if (!targetPosition) {
      alert('Parcel coordinates are unavailable.')
      return
    }
    const { lat, lng } = targetPosition
    // Opens in Google Maps / Apple Maps / device default nav app
    const url = `https://www.google.com/maps/dir/?api=1&destination=${lat},${lng}`
    window.open(url, '_blank', 'noopener,noreferrer')
  }

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
          <div
            key={c.id}
            className="assignment-card"
            onClick={() => { setActive(c); setChecked({}) }}
            style={{ cursor: 'pointer', borderColor: active?.id === c.id ? 'var(--medium)' : undefined }}
          >
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

            {/* ── GPS status banner ─────────────────────────────────────── */}
            {gpsLoading && (
              <div style={{ background: '#f0f4ff', border: '1px solid var(--medium)', borderRadius: 6, padding: '7px 10px', fontSize: 11, marginBottom: 8, color: '#2c5fbb' }}>
                🔄 Acquiring GPS lock…
              </div>
            )}

            {!gpsLoading && gpsError && (
              <div style={{ background: '#fff5f5', border: '1px solid #e74c3c', borderRadius: 6, padding: '7px 10px', fontSize: 11, marginBottom: 8, color: '#c0392b' }}>
                ⚠️ {gpsError}
                <button className="btn" style={{ marginLeft: 10, padding: '2px 10px', fontSize: 11 }} onClick={retryGps}>
                  Try Again
                </button>
              </div>
            )}

            {!gpsLoading && gpsPosition && (
              <div style={{
                background: gpsWeak ? '#fffbf0' : '#edfdf4',
                border: `1px solid ${gpsWeak ? '#e67e22' : '#27ae60'}`,
                borderRadius: 6, padding: '7px 10px', fontSize: 11, marginBottom: 8,
                color: gpsWeak ? '#c87600' : '#1e7e34'
              }}>
                {gpsWeak ? '⚠️ GPS SIGNAL WEAK' : '✅ GPS LOCK ✓'}
                &nbsp;·&nbsp;Accuracy: ±{Math.round(gpsPosition.accuracy)} m
                <br />
                <span style={{ color: '#555', fontSize: 10.5 }}>
                  Officer: {gpsPosition.lat.toFixed(5)}°, {gpsPosition.lng.toFixed(5)}°
                </span>
              </div>
            )}

            {/* ── Map: officer + target ─────────────────────────────────── */}
            <div style={{ marginBottom: 8, borderRadius: 8, overflow: 'hidden', border: '1px solid var(--border)' }}>
              <GpsMap
                mode="field"
                gpsPosition={gpsPosition}
                targetPosition={targetPosition}
                height={200}
              />
            </div>

            {/* ── Distance to parcel ───────────────────────────────────── */}
            {distanceM !== null && (
              <div style={{
                background: '#f8f8f8', border: '1px solid var(--border)', borderRadius: 6,
                padding: '7px 10px', fontSize: 11, marginBottom: 10, display: 'flex',
                justifyContent: 'space-between', alignItems: 'center'
              }}>
                <span>📌 Distance to parcel</span>
                <strong style={{ fontSize: 13 }}>{formatDistance(distanceM)}</strong>
              </div>
            )}
            {gpsPosition && !targetPosition && (
              <div style={{ fontSize: 10.5, color: 'var(--text-faint)', marginBottom: 8 }}>
                Parcel coordinates unavailable for this case.
              </div>
            )}

            {/* ── Checklist ────────────────────────────────────────────── */}
            {CHECKLIST_BASE.map((item, i) => {
              const isGpsItem = item.gpsRequired
              const isGpsChecked = isGpsItem && gpsLocked
              const isDisabled = isGpsItem && !gpsLocked
              const isChecked = checked[i] || isGpsChecked

              return (
                <div
                  className="checklist-item"
                  key={i}
                  onClick={() => {
                    if (i === 0) { navigateToParcel(); return }
                    toggle(i)
                  }}
                  style={{ opacity: isDisabled ? 0.45 : 1, cursor: isDisabled ? 'not-allowed' : 'pointer' }}
                >
                  <div className={`checklist-box ${isChecked ? 'checked' : ''}`}>{isChecked ? '✓' : ''}</div>
                  <div>
                    <div className="checklist-label">{item.label}</div>
                    {isGpsItem && gpsPosition ? (
                      <div className="checklist-hint" style={{ color: '#27ae60' }}>
                        ✓ Ground GPS Lock · Accuracy: ±{Math.round(gpsPosition.accuracy)} m
                      </div>
                    ) : isGpsItem && gpsLoading ? (
                      <div className="checklist-hint">Acquiring GPS…</div>
                    ) : isGpsItem && gpsError ? (
                      <div className="checklist-hint" style={{ color: '#c0392b' }}>GPS unavailable</div>
                    ) : (
                      item.hint && <div className="checklist-hint">{item.hint}</div>
                    )}
                  </div>
                </div>
              )
            })}

            <button
              className="btn success block"
              style={{ marginTop: 14 }}
              disabled={doneCount < CHECKLIST_BASE.length}
            >
              Submit System Findings Verification
            </button>
            <button className="btn block" style={{ marginTop: 8 }}>Save as Offline Draft</button>
          </>
        )}
      </PhoneFrame>
    </div>
  )
}
