import React from 'react'

export default function PhoneFrame({ children, headerTitle, headerSub, offline = true, activeTab, tabs }) {
  return (
    <div className="phone-frame">
      <div className="phone-screen">
        <div className="phone-statusbar">
          <span>9:41 AM</span>
          <span>BhoomiDrishti · MAHARASHTRA GOVT.</span>
        </div>
        <div className="phone-app-header">
          <div className="app-title">{headerTitle}</div>
          {headerSub && <div className="app-sub">{headerSub}</div>}
          {offline && <div style={{ marginTop: 8 }}><span className="offline-chip">● Offline · 3 pending</span></div>}
        </div>
        <div className="phone-body">{children}</div>
        {tabs && (
          <div className="phone-tabbar">
            {tabs.map((t) => (
              <div key={t} className={`tab ${activeTab === t ? 'active' : ''}`}>{t}</div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
