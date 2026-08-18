/**
 * GpsMap — shared Leaflet map for CitizenApp and FieldApp.
 *
 * Props:
 *   mode         : 'citizen' | 'field'
 *   gpsPosition  : { lat, lng, accuracy } | null   — current officer/user GPS position
 *   targetPosition: { lat, lng } | null             — target parcel (field mode only)
 *   onLocationSelect: (lat, lng) => void            — called when user clicks map (citizen mode)
 *   selectedPosition: { lat, lng } | null           — manually-selected pin (citizen mode)
 */
import React, { useEffect, useRef } from 'react'
import { MapContainer, TileLayer, Marker, Circle, Popup, useMap, useMapEvents } from 'react-leaflet'
import L from 'leaflet'

// ── Fix default leaflet marker icons broken by Vite's asset bundling ──────────
import markerIconUrl from 'leaflet/dist/images/marker-icon.png'
import markerShadowUrl from 'leaflet/dist/images/marker-shadow.png'
delete L.Icon.Default.prototype._getIconUrl
L.Icon.Default.mergeOptions({ iconUrl: markerIconUrl, shadowUrl: markerShadowUrl })

// Custom coloured markers
function colorIcon(color) {
  return new L.Icon({
    iconUrl: `https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-${color}.png`,
    shadowUrl: markerShadowUrl,
    iconSize: [25, 41],
    iconAnchor: [12, 41],
    popupAnchor: [1, -34],
    shadowSize: [41, 41],
  })
}

const blueIcon   = colorIcon('blue')
const redIcon    = colorIcon('red')
const greenIcon  = colorIcon('green')

// ── Helper: haversine distance in metres ─────────────────────────────────────
export function haversineMetres(lat1, lng1, lat2, lng2) {
  const R = 6371000
  const toRad = (d) => (d * Math.PI) / 180
  const dLat = toRad(lat2 - lat1)
  const dLng = toRad(lng2 - lng1)
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLng / 2) ** 2
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a))
}

// ── Internal: recenter map when position changes ──────────────────────────────
function MapRecenterer({ center }) {
  const map = useMap()
  useEffect(() => {
    if (center) map.setView(center, map.getZoom())
  }, [center, map])
  return null
}

// ── Internal: click handler for citizen manual-select mode ────────────────────
function ClickHandler({ onLocationSelect }) {
  useMapEvents({
    click(e) {
      if (onLocationSelect) onLocationSelect(e.latlng.lat, e.latlng.lng)
    },
  })
  return null
}

// ── Main component ────────────────────────────────────────────────────────────
export default function GpsMap({
  mode = 'citizen',
  gpsPosition = null,
  targetPosition = null,
  onLocationSelect = null,
  selectedPosition = null,
  height = 220,
}) {
  // Default map center: India centre-ish, zoomed out a bit
  const defaultCenter = gpsPosition
    ? [gpsPosition.lat, gpsPosition.lng]
    : targetPosition
    ? [targetPosition.lat, targetPosition.lng]
    : [20.5937, 78.9629]

  const defaultZoom = gpsPosition || targetPosition ? 15 : 5

  return (
    <MapContainer
      center={defaultCenter}
      zoom={defaultZoom}
      style={{ height, width: '100%', borderRadius: 8, zIndex: 0 }}
    >
      <TileLayer
        url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
        attribution='&copy; OpenStreetMap &copy; CARTO'
      />

      {/* Recenter when GPS arrives */}
      {gpsPosition && (
        <MapRecenterer center={[gpsPosition.lat, gpsPosition.lng]} />
      )}

      {/* Citizen: click-to-select */}
      {mode === 'citizen' && onLocationSelect && (
        <ClickHandler onLocationSelect={onLocationSelect} />
      )}

      {/* GPS position marker + accuracy circle */}
      {gpsPosition && (
        <>
          <Marker position={[gpsPosition.lat, gpsPosition.lng]} icon={mode === 'field' ? greenIcon : blueIcon}>
            <Popup>
              {mode === 'field' ? '📍 Your current location' : '📍 GPS location'}
              <br />
              {gpsPosition.lat.toFixed(5)}°, {gpsPosition.lng.toFixed(5)}°
              <br />
              Accuracy: ±{Math.round(gpsPosition.accuracy)} m
            </Popup>
          </Marker>
          {gpsPosition.accuracy && (
            <Circle
              center={[gpsPosition.lat, gpsPosition.lng]}
              radius={gpsPosition.accuracy}
              pathOptions={{ color: mode === 'field' ? '#27ae60' : '#2980b9', fillOpacity: 0.12, weight: 1 }}
            />
          )}
        </>
      )}

      {/* Field: target parcel marker */}
      {mode === 'field' && targetPosition && (
        <Marker position={[targetPosition.lat, targetPosition.lng]} icon={redIcon}>
          <Popup>📌 Target parcel<br />{targetPosition.lat.toFixed(5)}°, {targetPosition.lng.toFixed(5)}°</Popup>
        </Marker>
      )}

      {/* Citizen: manually selected pin */}
      {mode === 'citizen' && selectedPosition && (
        <Marker position={[selectedPosition.lat, selectedPosition.lng]} icon={redIcon}>
          <Popup>📌 Selected location<br />{selectedPosition.lat.toFixed(5)}°, {selectedPosition.lng.toFixed(5)}°</Popup>
        </Marker>
      )}
    </MapContainer>
  )
}
