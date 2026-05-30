import { useEffect, useState } from 'react'
import { api } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import './LoginPage.css'

export function LoginPage() {
  const { login } = useAuth()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [demoUsername, setDemoUsername] = useState('demo')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api.getAuthConfig().then((c) => {
      if (c.demo_username) setDemoUsername(c.demo_username)
    })
  }, [])

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      await login(username.trim(), password)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Sign in failed')
    } finally {
      setSubmitting(false)
    }
  }

  async function handleDemoLogin() {
    setError(null)
    setSubmitting(true)
    try {
      await login(demoUsername, 'demo')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Demo sign in failed')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="login-page">
      <div className="login-ambient" aria-hidden>
        <div className="login-orb login-orb-1" />
        <div className="login-orb login-orb-2" />
      </div>

      <div className="login-card">
        <div className="login-brand">
          <img src="/signalforge-icon.svg" alt="" className="login-logo" width={48} height={48} />
          <div>
            <h1>SignalForge</h1>
            <p>AI competitive intelligence from the live web</p>
          </div>
        </div>

        <form className="login-form" onSubmit={handleSubmit}>
          <h2>Sign in</h2>
          <p className="login-hint">Use your workspace credentials to access the dashboard.</p>

          {error && <div className="login-error">{error}</div>}

          <div className="form-group">
            <label htmlFor="login-username">Username</label>
            <input
              id="login-username"
              type="text"
              autoComplete="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="admin"
              required
              disabled={submitting}
            />
          </div>

          <div className="form-group">
            <label htmlFor="login-password">Password</label>
            <input
              id="login-password"
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              required
              disabled={submitting}
            />
          </div>

          <button type="submit" className="btn btn-primary login-submit" disabled={submitting}>
            {submitting ? 'Signing in…' : 'Sign in'}
          </button>

          <div className="login-divider">
            <span>or</span>
          </div>

          <button
            type="button"
            className="btn login-demo-btn"
            disabled={submitting}
            onClick={handleDemoLogin}
          >
            Try demo account
          </button>
          <p className="login-demo-note">
            Demo: read-only competitors, no edit/delete, limited Forge Scout requests (
            {demoUsername} / demo).
          </p>
        </form>
      </div>
    </div>
  )
}
