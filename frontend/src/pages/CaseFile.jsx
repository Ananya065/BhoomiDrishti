import React, { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import TopHeader from '../components/TopHeader'
import Badge from '../components/Badge'
import { api } from '../api'
import { useAuth } from '../auth'
import CopilotWidget from '../components/CopilotWidget'

export default function CaseFile() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { user } = useAuth()
  const [c, setC] = useState(null)
  const [noteText, setNoteText] = useState('')
  const [saving, setSaving] = useState(false)
  const [intel, setIntel] = useState(null)

  const load = () => {
    api.getCase(id).then(setC)
    // Safe fetch intelligence; may 404 if not run through Part 2 pipeline
    fetch(`/api/cases/${id}/intelligence`)
      .then(r => r.ok ? r.json() : null)
      .then(setIntel)
      .catch(() => setIntel(null))
  }
  useEffect(() => { load() }, [id]) // eslint-disable-line

  if (!c) return <div className="loading-inline">Loading case file…</div>

  const setStatus = async (status) => {
    await api.updateStatus(id, status)
    load()
  }

  const submitNote = async () => {
    if (!noteText.trim()) return
    setSaving(true)
    await api.addNote(id, user?.name || 'Officer', noteText.trim())
    setNoteText('')
    await load()
    setSaving(false)
  }

  return (
    <>
      <TopHeader
        title={`Case File: ${c.case_number}`}
        subtitle={`Assigned to: ${c.assigned_officer}`}
        actions={
          <div className="btn-row">
            <a href={`http://localhost:8000/api/changes/${id}/report/html`} target="_blank" rel="noopener noreferrer" className="btn primary">Export PDF Report</a>
            <button className="btn" onClick={() => navigate('/map')}>← Back to Map</button>
          </div>
        }
      />
      <div className="portal-content">
        <div className="case-header">
          <div>
            <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
              <Badge value={c.priority} />
              <span style={{ fontSize: 13, color: 'var(--text-dim)' }}>{c.location_name}</span>
            </div>
          </div>
          <div className="btn-row">
            <button className="btn success" onClick={() => setStatus('reviewed')}>Mark Verified &amp; Resolved</button>
          </div>
        </div>

        <div className="case-grid">
          <div style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
            <div className="card">
              <div className="card-header"><h3>Imagery Comparison — Before / After</h3></div>
              <div className="card-body">
                <div className="image-compare" 
                     onMouseMove={(e) => {
                       const rect = e.currentTarget.getBoundingClientRect();
                       const x = e.clientX - rect.left;
                       const pct = Math.max(0, Math.min(100, (x / rect.width) * 100));
                       e.currentTarget.style.setProperty('--slider-pos', `${pct}%`);
                     }}
                     style={{ position: 'relative', width: '100%', height: '300px', overflow: 'hidden', borderRadius: '8px', cursor: 'ew-resize', '--slider-pos': '50%' }}>
                  
                  <img src={c.after_image_url} alt="after" style={{ width: '100%', height: '100%', objectFit: 'cover', position: 'absolute', top: 0, left: 0 }} />
                  
                  <div style={{ position: 'absolute', top: 0, left: 0, width: 'var(--slider-pos)', height: '100%', overflow: 'hidden' }}>
                    <img src={c.before_image_url} alt="before" style={{ width: '100%', height: '100%', objectFit: 'cover', minWidth: 'max-content' }} />
                  </div>

                  <div style={{ position: 'absolute', top: 0, bottom: 0, left: 'var(--slider-pos)', width: '2px', background: 'var(--medium)', transform: 'translateX(-50%)', zIndex: 10 }} />
                  
                  <div style={{ position: 'absolute', top: 10, left: 10, background: 'rgba(0,0,0,0.6)', color: '#fff', padding: '4px 8px', borderRadius: '4px', fontSize: '11px', zIndex: 20 }}>
                    Before: {new Date(c.before_image_date).toLocaleDateString('en-IN', { month: 'short', year: 'numeric' })}
                  </div>
                  <div style={{ position: 'absolute', top: 10, right: 10, background: 'rgba(0,0,0,0.6)', color: '#fff', padding: '4px 8px', borderRadius: '4px', fontSize: '11px', zIndex: 20 }}>
                    After: {new Date(c.after_image_date).toLocaleDateString('en-IN', { month: 'short', year: 'numeric' })}
                  </div>
                </div>
                <div className="findings-list" style={{ marginTop: 14 }}>
                  <p><b>System Findings &amp; Change Highlights</b></p>
                  
                  {intel ? (
                    <>
                      <p>• <b>Activity Classification:</b> {intel.classification.activity_type.toUpperCase()} (Confidence: {(intel.classification.confidence * 100).toFixed(0)}%)</p>
                      <p>• <b>Geospatial Context:</b> {intel.geospatial.sensitive_zone ? `Overlap with ${intel.geospatial.zone_type} detected.` : 'No sensitive zone overlap.'}</p>
                      <p>• <b>Severity Level:</b> <Badge value={intel.severity.level.toLowerCase()} /> — {intel.severity.reason}</p>
                      <p>• <b>Temporal Status:</b> {intel.temporal.status.toUpperCase()} (First detected: {intel.temporal.first_detected ? new Date(intel.temporal.first_detected).toLocaleDateString('en-IN') : 'N/A'})</p>
                    </>
                  ) : (
                    <>
                      <p>• <b>Structure Detected:</b> High-reflectance change consistent with {c.change_type} identified within the parcel boundary.</p>
                      <p>• <b>Boundary Proximity:</b> {c.sensitivity_flag ? `Change sits within or adjacent to ${c.sensitivity_zone_name}.` : 'No overlap with mapped sensitive-zone boundaries detected.'}</p>
                    </>
                  )}
                  <p>• <b>Area Affected:</b> Approximately {(c.area_sq_m / 10000).toFixed(2)} hectares affected, model detection confidence {(c.confidence * 100).toFixed(0)}%.</p>
                </div>
                <div className="disclaimer-strip">
                  {c.sensitivity_note || 'This is a geographic overlap and structural-change flag only — not a legal determination of ownership or permit status. Human review against official land records is required before any enforcement action.'}
                </div>
              </div>
            </div>

            <div className="card">
              <div className="card-header"><h3>Officer Logs &amp; Field Notes</h3></div>
              <div className="card-body">
                {c.notes.map((n, i) => (
                  <div className="note-item" key={i}>
                    <div className="note-meta"><b>{n.author}</b> · {n.date}</div>
                    <div className="note-text">{n.text}</div>
                  </div>
                ))}
                <div className="note-input">
                  <textarea
                    placeholder="Write an official review note…"
                    value={noteText}
                    onChange={(e) => setNoteText(e.target.value)}
                  />
                  <button className="btn primary" onClick={submitNote} disabled={saving}>
                    {saving ? 'Adding…' : 'Add Case Note'}
                  </button>
                </div>
              </div>
            </div>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
            <div className="card">
              <div className="card-header"><h3>Case Timeline</h3></div>
              <div className="card-body timeline">
                {intel && intel.temporal.area_progression && intel.temporal.area_progression.length > 0 && (
                  <>
                    <h4 style={{marginBottom: 8}}>Temporal Analysis Progression</h4>
                    {intel.temporal.area_progression.map((prog, i) => (
                      <div className="timeline-item done" key={`prog-${i}`}>
                        <div className="timeline-dot" style={{background: 'var(--accent)'}} />
                        <div>
                          <div className="timeline-date">{new Date(prog.date).toLocaleDateString('en-IN', { month: 'short', year: 'numeric' })}</div>
                          <div className="timeline-stage">Detection Event</div>
                          <div className="timeline-desc">Detected area: {(prog.area / 10000).toFixed(4)} ha</div>
                        </div>
                      </div>
                    ))}
                    <div style={{height: 1, background: 'var(--border)', margin: '16px 0'}} />
                  </>
                )}
                
                <h4 style={{marginBottom: 8}}>Case Log</h4>
                {c.timeline.map((t, i) => (
                  <div className={`timeline-item ${t.done ? 'done' : ''}`} key={i}>
                    <div className="timeline-dot" />
                    <div>
                      <div className="timeline-date">{t.date}</div>
                      <div className="timeline-stage">{t.stage}</div>
                      <div className="timeline-desc">{t.description}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="card">
              <div className="card-header"><h3>Cadastral &amp; Registry Records</h3></div>
              <div className="card-body meta-table">
                <div className="row"><span>Survey Number</span><span>{c.survey_number}</span></div>
                <div className="row"><span>Village / Taluka</span><span>{c.village} / {c.taluka}</span></div>
                <div className="row"><span>Registered Area</span><span>{c.registered_area_hectares} Hectares</span></div>
                <div className="row"><span>Land Class Type</span><span>{c.land_class_type}</span></div>
                <div className="row"><span>Deeded Owner</span><span>{c.deeded_owner}</span></div>
              </div>
            </div>

            <div className="card">
              <div className="card-body btn-row" style={{ flexDirection: 'column' }}>
                <button className="btn block">Assign Different Officer</button>
                <button className="btn block">Schedule On-site Inspection</button>
                <button className="btn block">Upload Field Evidence</button>
                <button className="btn danger block" onClick={() => setStatus('needs_review')}>Escalate to Collector</button>
                <button className="btn success block" onClick={() => setStatus('reviewed')}>Mark Verified &amp; Resolved</button>
              </div>
            </div>
          </div>
        </div>
      </div>
      <CopilotWidget caseId={id} />
    </>
  )
}
