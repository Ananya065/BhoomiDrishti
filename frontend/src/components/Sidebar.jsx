import React from 'react'
import { NavLink } from 'react-router-dom'

const NAV_ITEMS = [
  { to: '/dashboard', icon: '\u25A6', label: 'Dashboard' },
  { to: '/map', icon: '\u25C9', label: 'Live Map' },
  { to: '/alerts', icon: '\u26A0', label: 'Alerts' },
  { to: '/reports', icon: '\u25A4', label: 'Reports' },
  { to: '/field-app', icon: '\u2713', label: 'Field Verification' },
  { to: '/citizen-app', icon: '\u2691', label: 'Land Records' },
]

export default function Sidebar() {
  return (
    <aside className="portal-sidebar">
      <div className="portal-logo">
        <div className="en">भूमिदृष्टि / BhoomiDrishti</div>
        <div className="sub">LAND USE MONITORING PORTAL</div>
      </div>
      <ul className="nav-list">
        {NAV_ITEMS.map((item) => (
          <li className="nav-item" key={item.to}>
            <NavLink to={item.to} className={({ isActive }) => (isActive ? 'active' : '')}>
              <span className="nav-icon">{item.icon}</span>
              {item.label}
            </NavLink>
          </li>
        ))}
      </ul>
      <div className="sidebar-footer">
        Govt. of Maharashtra<br />v1.4.2-Live
      </div>
    </aside>
  )
}
