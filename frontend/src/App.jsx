import React from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import AppLayout from './layouts/AppLayout'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import LiveMap from './pages/LiveMap'
import Alerts from './pages/Alerts'
import CaseFile from './pages/CaseFile'
import Reports from './pages/Reports'
import FieldApp from './pages/FieldApp'
import CitizenApp from './pages/CitizenApp'

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/field-app" element={<FieldApp />} />
      <Route path="/citizen-app" element={<CitizenApp />} />

      <Route element={<AppLayout />}>
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/map" element={<LiveMap />} />
        <Route path="/alerts" element={<Alerts />} />
        <Route path="/case/:id" element={<CaseFile />} />
        <Route path="/reports" element={<Reports />} />
      </Route>

      <Route path="/" element={<Navigate to="/login" replace />} />
      <Route path="*" element={<Navigate to="/login" replace />} />
    </Routes>
  )
}
