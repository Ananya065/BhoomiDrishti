import React from 'react'
import { Navigate, Outlet } from 'react-router-dom'
import Sidebar from '../components/Sidebar'
import { useAuth } from '../auth'

export default function AppLayout() {
  const { user } = useAuth()
  if (!user) return <Navigate to="/login" replace />

  return (
    <div className="portal-shell">
      <Sidebar />
      <div>
        <Outlet />
      </div>
    </div>
  )
}
