import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { MapContainer, TileLayer, CircleMarker, Tooltip } from 'react-leaflet'
import TopHeader from '../components/TopHeader'
import Badge from '../components/Badge'
import { api } from '../api'

const VILLAGES = ['Ambegaon', 'Ghodegaon', 'Manchar', 'Nirgude']

function markerColor(c) {
  if (c.priority === 'critical') return '#c0392b'
  if (c.priority === 'high') return '#d9822b'
  return '#2e6fdb'
}

export default function LiveMap() {
  const [cases, setCases] = useState([])
  const [selected, setSelected] = useState(null)
  const [village, setVillage] = useState('')
  const [priority, setPriority] = useState('')
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()

  const load = () => {
    setLoading(true)
    api.listChanges({ village, priority }).then((data) => {
      setCases(data)
      setSelected(data[0] || null)
      setLoading(false)
    })
  }

  useEffect(() => { load() }, []) // eslint-disable-line

  const center = selected ? [selected.latitude, selected.longitude] : [19.13, 73.9]

  return (
    <>
      <TopHeader title="Live Map" subtitle="Satellite imagery comparison and change verification." />
      <div className="portal-content">
        <div className="map-layout">
          <div className="card filter-panel">
            <h4>Select District</h4>
            <select className="btn block" style={{ textAlign: 'left' }} disabled>
              <option>Pune</option>
            </select>

            <h4>Select Village</h4>
            <select
              value={village}
              onChange={(e) => setVillage(e.target.value)}
              style={{ width: '100%', padding: '8px 10px', borderRadius: 5, border: '1px solid var(--border-strong)' }}
            >
              <option value="">All Villages</option>
              {VILLAGES.map((v) => <option key={v} value={v}>{v}</option>)}
            </select>

            <h4>Priority Level</h4>
            {['critical', 'high', 'medium'].map((p) => (
              <label key={p} className="toggle-row">
                <span style={{ textTransform: 'capitalize' }}>{p}</span>
                <input
                  type="radio"
                  name="priority"
                  checked={priority === p}
                  onChange={() => setPriority(priority === p ? '' : p)}
                />
              </label>
            ))}

            <button className="btn primary block" style={{ marginTop: 14 }} onClick={load}>Apply Filters</button>

            <h4>Detected Cases ({cases.length})</h4>
            {cases.slice(0, 8).map((c) => (
              <div
                key={c.id}
                onClick={() => setSelected(c)}
                style={{
                  padding: '8px 0', borderBottom: '1px solid var(--border)', cursor: 'pointer',
                  fontSize: 12, fontWeight: selected?.id === c.id ? 700 : 500,
                }}
              >
                <div className="case-id-cell">{c.case_number}</div>
                <div style={{ color: 'var(--text-dim)' }}>{c.location_name}</div>
              </div>
            ))}
          </div>

          <div className="map-canvas">
            {loading ? (
              <div className="loading-inline">Loading map data…</div>
            ) : (
              <MapContainer center={center} zoom={11} style={{ height: '100%', width: '100%' }}>
                <TileLayer
                  url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
                  attribution='&copy; OpenStreetMap &copy; CARTO'
                />
                {cases.map((c) => (
                  <CircleMarker
                    key={c.id}
                    center={[c.latitude, c.longitude]}
                    radius={selected?.id === c.id ? 12 : 8}
                    pathOptions={{ color: markerColor(c), fillColor: markerColor(c), fillOpacity: 0.7, weight: 2 }}
                    eventHandlers={{ click: () => setSelected(c) }}
                  >
                    <Tooltip>{c.case_number} · {c.location_name}</Tooltip>
                  </CircleMarker>
                ))}
              </MapContainer>
            )}

            {selected && (
              <div className="map-info-panel">
                <div className="mi-header">
                  <strong style={{ fontSize: 13 }}>Survey No. {selected.survey_number}</strong>
                  <Badge value={selected.priority} />
                </div>
                <div className="mi-body">
                  <div className="mi-row"><span>Area</span><span>{selected.registered_area_hectares} Hectares</span></div>
                  <div className="mi-row"><span>Type</span><span>{selected.land_class_type}</span></div>
                  <div className="mi-row"><span>Village</span><span>{selected.village}</span></div>
                  <p style={{ fontSize: 11.5, color: 'var(--text-dim)', margin: '10px 0' }}>
                    {selected.change_type} detected covering approximately {selected.area_sq_m.toFixed(0)} m².
                    {selected.sensitivity_flag ? ` Falls within ${selected.sensitivity_zone_name}. ` : ' '}
                    Requires field verification.
                  </p>
                  <button className="btn primary block" onClick={() => navigate(`/case/${selected.id}`)}>
                    Open Case Detail Sheet
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </>
  )
}
