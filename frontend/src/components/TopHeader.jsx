import React from 'react'
import { useAuth } from '../auth'

export default function TopHeader({ title, subtitle, actions }) {
  const { user } = useAuth()
  const initials = (user?.name || 'RP').split(' ').map((s) => s[0]).join('').slice(0, 2).toUpperCase()

  return (
    <header className="portal-topbar">
      <div className="topbar-title">
        <h1>{title}</h1>
        {subtitle && <p>{subtitle}</p>}
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
        {actions}
        <div className="topbar-user">
          <div className="user-avatar">{initials}</div>
          <div className="user-meta">
            <div className="name">{user?.name || 'Rajesh Patil'}</div>
            <div className="role">{user?.role || 'District Officer'}</div>
          </div>
        </div>
      </div>
    </header>
  )
}
