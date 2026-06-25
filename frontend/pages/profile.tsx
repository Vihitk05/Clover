import React, { useEffect, useState } from 'react'
import Head from 'next/head'
import Link from 'next/link'
import { useRouter } from 'next/router'
import Layout from '../components/Layout'
import {
  downloadActiveResume,
  getProfileOverview,
  getStoredTokens,
  logout,
  setStoredTokens,
  updateProfile,
} from '../lib/api'
import { ProfileOverviewResponse } from '../types'

export default function ProfilePage() {
  const router = useRouter()
  const [overview, setOverview] = useState<ProfileOverviewResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [downloading, setDownloading] = useState(false)

  const [fullName, setFullName] = useState('')
  const [email, setEmail] = useState('')
  const [phone, setPhone] = useState('')
  const [preferredRole, setPreferredRole] = useState('')
  const [preferredLocation, setPreferredLocation] = useState('')
  const [preferencesRaw, setPreferencesRaw] = useState('')

  useEffect(() => {
    async function fetchProfile() {
      try {
        setLoading(true)
        const data = await getProfileOverview()
        setOverview(data)
        setFullName(data.profile.name || '')
        setEmail(data.profile.email || '')
        setPhone(data.profile.phone || '')
        setPreferredRole(data.profile.target_role || '')
        setPreferredLocation(data.profile.target_location || '')
        setPreferencesRaw(data.profile.preferences_raw || '')
      } catch (err: any) {
        setError(err.message || 'Could not load your profile')
      } finally {
        setLoading(false)
      }
    }
    fetchProfile()
  }, [])

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      setSaving(true)
      setError(null)
      const updated = await updateProfile({
        full_name: fullName,
        email,
        phone,
        preferred_role: preferredRole,
        preferred_location: preferredLocation,
        preferences_raw: preferencesRaw,
      })
      setOverview(updated)
    } catch (err: any) {
      setError(err.message || 'Unable to save profile changes')
    } finally {
      setSaving(false)
    }
  }

  const handleDownload = async () => {
    try {
      setDownloading(true)
      const { blob, filename } = await downloadActiveResume()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = filename
      document.body.appendChild(a)
      a.click()
      a.remove()
      URL.revokeObjectURL(url)
    } catch (err: any) {
      setError(err.message || 'Failed to download resume')
    } finally {
      setDownloading(false)
    }
  }

  const handlePreview = async () => {
    try {
      const { blob } = await downloadActiveResume()
      const url = URL.createObjectURL(blob)
      window.open(url, '_blank', 'noopener,noreferrer')
      setTimeout(() => URL.revokeObjectURL(url), 30000)
    } catch (err: any) {
      setError(err.message || 'Failed to preview resume')
    }
  }

  const handleSignOut = async () => {
    try {
      const tokens = getStoredTokens()
      if (tokens?.refreshToken) {
        await logout(tokens.refreshToken).catch(() => undefined)
      }
    } finally {
      setStoredTokens(null)
      router.push('/')
    }
  }

  return (
    <Layout>
      <Head>
        <title>Profile | Clover</title>
      </Head>

      <div className="container section">
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: '12px', flexWrap: 'wrap', alignItems: 'center' }}>
          <div>
            <p className="eyebrow">Profile</p>
            <h1 style={{ marginBottom: '10px' }}>Account and profile settings</h1>
          </div>
          <button className="btn btn-secondary" onClick={handleSignOut}>Sign Out</button>
        </div>
        <p style={{ color: 'var(--text-secondary)', marginBottom: '24px' }}>
          Keep your details current so recommendations and generated documents stay accurate.
        </p>

        {loading ? (
          <div className="glass-card" style={{ padding: '28px', textAlign: 'center' }}>
            <div className="spinner" style={{ margin: '0 auto 16px auto' }} />
            Loading your profile...
          </div>
        ) : error ? (
          <div className="glass-card" style={{ padding: '24px', color: '#b42318' }}>
            {error}
          </div>
        ) : !overview ? (
          <div className="glass-card" style={{ padding: '24px' }}>
            No profile available yet. Upload your resume to get started.
          </div>
        ) : (
          <div style={{ display: 'grid', gap: '18px' }}>
            <form className="glass-card" style={{ padding: '22px', display: 'grid', gap: '12px' }} onSubmit={handleSave}>
              <h3 style={{ marginBottom: '4px' }}>Edit profile</h3>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <div>
                  <label className="field-label">Full name</label>
                  <input className="input" value={fullName} onChange={(e) => setFullName(e.target.value)} />
                </div>
                <div>
                  <label className="field-label">Email</label>
                  <input className="input" type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
                </div>
                <div>
                  <label className="field-label">Phone</label>
                  <input className="input" value={phone} onChange={(e) => setPhone(e.target.value)} />
                </div>
                <div>
                  <label className="field-label">Preferred role</label>
                  <input className="input" value={preferredRole} onChange={(e) => setPreferredRole(e.target.value)} />
                </div>
                <div>
                  <label className="field-label">Preferred location</label>
                  <input className="input" value={preferredLocation} onChange={(e) => setPreferredLocation(e.target.value)} />
                </div>
              </div>
              <div>
                <label className="field-label">Additional preferences</label>
                <textarea className="input" value={preferencesRaw} onChange={(e) => setPreferencesRaw(e.target.value)} />
              </div>
              <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
                <button className="btn btn-primary" disabled={saving}>{saving ? 'Saving...' : 'Save Changes'}</button>
              </div>
            </form>

            <div className="glass-card" style={{ padding: '22px' }}>
              <h3 style={{ marginBottom: '12px' }}>Resume</h3>
              {overview.active_resume ? (
                <>
                  <p style={{ fontWeight: 700 }}>{overview.active_resume.original_filename}</p>
                  <p style={{ color: 'var(--text-secondary)', marginBottom: '14px' }}>
                    Version {overview.active_resume.version} • Uploaded {new Date(overview.active_resume.uploaded_at).toLocaleString()}
                  </p>
                  <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
                    <button className="btn btn-secondary" onClick={handlePreview}>
                      Preview Resume
                    </button>
                    <button className="btn btn-secondary" onClick={handleDownload} disabled={downloading}>
                      {downloading ? 'Preparing download...' : 'Download Resume'}
                    </button>
                    <Link href="/" className="btn btn-primary">Upload New Version</Link>
                  </div>
                </>
              ) : (
                <p style={{ color: 'var(--text-secondary)' }}>No resume file found for this profile.</p>
              )}
            </div>

            <div className="glass-card" style={{ padding: '22px' }}>
              <h3 style={{ marginBottom: '12px' }}>Your progress</h3>
              <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
                <span className="badge badge-info">{overview.matched_jobs_count} matched jobs</span>
                <span className="badge badge-info">{overview.generated_cover_letters_count} generated document sets</span>
              </div>
            </div>
          </div>
        )}
      </div>
    </Layout>
  )
}
