import React, { useState } from 'react'

interface AuthPanelProps {
  onLogin: (email: string, password: string) => Promise<void>
  onSignup: (fullName: string, email: string, password: string) => Promise<void>
}

export default function AuthPanel({ onLogin, onSignup }: AuthPanelProps) {
  const [mode, setMode] = useState<'login' | 'signup'>('login')
  const [fullName, setFullName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try {
      if (mode === 'login') {
        await onLogin(email, password)
      } else {
        await onSignup(fullName, email, password)
      }
      setPassword('')
    } catch (err: any) {
      setError(err.message || 'Authentication failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="glass-card" style={{ padding: '28px' }}>
      <div style={{ marginBottom: '18px' }}>
        <p className="eyebrow">Account</p>
        <h3 style={{ marginBottom: '6px' }}>Welcome back</h3>
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.95rem' }}>
          Sign in to keep your resume, job matches, and applications saved in one place.
        </p>
      </div>

      <div style={{ display: 'flex', marginBottom: '18px', background: 'var(--bg-elevated)', borderRadius: '999px', padding: '4px' }}>
        <button
          className="btn-ghost"
          style={{ flex: 1, borderRadius: '999px', background: mode === 'login' ? 'var(--bg-card)' : 'transparent', color: mode === 'login' ? 'var(--text-primary)' : 'var(--text-muted)' }}
          onClick={() => setMode('login')}
          type="button"
        >
          Sign in
        </button>
        <button
          className="btn-ghost"
          style={{ flex: 1, borderRadius: '999px', background: mode === 'signup' ? 'var(--bg-card)' : 'transparent', color: mode === 'signup' ? 'var(--text-primary)' : 'var(--text-muted)' }}
          onClick={() => setMode('signup')}
          type="button"
        >
          Sign up
        </button>
      </div>

      <form onSubmit={submit} style={{ display: 'grid', gap: '12px' }}>
        {mode === 'signup' && (
          <input className="input" placeholder="Full name" value={fullName} onChange={(e) => setFullName(e.target.value)} required />
        )}
        <input className="input" type="email" placeholder="Email address" value={email} onChange={(e) => setEmail(e.target.value)} required />
        <input className="input" type="password" placeholder="Password" value={password} onChange={(e) => setPassword(e.target.value)} required minLength={8} />
        {error && <div style={{ color: '#b42318', fontSize: '0.875rem' }}>{error}</div>}
        <button className="btn btn-primary" disabled={loading}>
          {loading ? 'Please wait...' : mode === 'login' ? 'Continue' : 'Create account'}
        </button>
      </form>
    </div>
  )
}
