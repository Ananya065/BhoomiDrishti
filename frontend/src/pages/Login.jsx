import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../auth'
import { api } from '../api'

export default function Login() {
  const [role, setRole] = useState('District Officer')
  const [username, setUsername] = useState('rajesh.patil@maharashtra.gov.in')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const { login } = useAuth()
  const navigate = useNavigate()

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError(null)
    try {
      const res = await api.login(username, password || 'demo', role)
      login(res)
      navigate('/dashboard')
    } catch (err) {
      setError('Could not sign in — check the backend is running on :8000.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="login-page">
      <div>
        <div className="login-card">
          <div className="login-brand">
            <div className="hi">भूमिदृष्टि / BhoomiDrishti</div>
            <div className="en" style={{ marginTop: 6 }}>See land change. Act faster.</div>
          </div>

          <form onSubmit={handleSubmit}>
            <div className="field-group">
              <label>Select User Role</label>
              <select value={role} onChange={(e) => setRole(e.target.value)}>
                <option>District Officer</option>
                <option>Field Inspector</option>
                <option>Revenue Collector</option>
                <option>System Admin</option>
              </select>
            </div>
            <div className="field-group">
              <label>Username / Email ID</label>
              <input type="text" value={username} onChange={(e) => setUsername(e.target.value)} />
            </div>
            <div className="field-group">
              <label>Password</label>
              <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="••••••••••••" />
            </div>

            {error && <p style={{ color: 'var(--critical)', fontSize: 12, marginBottom: 10 }}>{error}</p>}

            <button className="btn primary block" type="submit" disabled={loading}>
              {loading ? 'Signing in…' : 'Sign In to Secure Portal'}
            </button>
          </form>

          <p style={{ textAlign: 'center', fontSize: 11.5, color: 'var(--text-faint)', marginTop: 12 }}>
            Forgot password or locked out? Contact Admin Helpdesk
          </p>

          <div className="login-notice">
            This is a secure Government of Maharashtra systems access portal. Unauthorized attempts
            to access this system are strictly prohibited and punishable under law. All platform
            change flags require official human review.
          </div>
        </div>
        <div className="login-footer">
          Department of Revenue — Government of Maharashtra<br />
          System Version 1.4.2-Live • Technical Helpdesk: 1800-419-5555
        </div>
      </div>
    </div>
  )
}
