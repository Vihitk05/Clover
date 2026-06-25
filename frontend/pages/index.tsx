import React, { useEffect, useState } from 'react'
import Head from 'next/head'
import Link from 'next/link'
import { useRouter } from 'next/router'
import Layout from '../components/Layout'
import CVUploader from '../components/CVUploader'
import AuthPanel from '../components/AuthPanel'
import OnboardingWizard from '../components/OnboardingWizard'
import {
  getCurrentUser,
  getProfileOverview,
  login,
  setStoredTokens,
  signup,
  updateOnboarding,
  uploadCV,
} from '../lib/api'
import { CurrentUserResponse, OnboardingPayload, ProfileOverviewResponse } from '../types'

export default function Home() {
  const router = useRouter()
  const [user, setUser] = useState<CurrentUserResponse | null>(null)
  const [overview, setOverview] = useState<ProfileOverviewResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [lastProfileId, setLastProfileId] = useState<string | undefined>(undefined)
  const [checkingSession, setCheckingSession] = useState(true)

  useEffect(() => {
    async function bootstrap() {
      try {
        const me = await getCurrentUser()
        setUser(me)
        try {
          const profileOverview = await getProfileOverview()
          setOverview(profileOverview)
          setLastProfileId(profileOverview.profile.id)
        } catch {
          setOverview(null)
        }
      } catch {
        setUser(null)
        setOverview(null)
      } finally {
        setCheckingSession(false)
      }
    }
    bootstrap()
  }, [])

  const handleLogin = async (email: string, password: string) => {
    const result = await login(email, password)
    setStoredTokens({
      accessToken: result.access_token,
      refreshToken: result.refresh_token,
    })
    const me = await getCurrentUser()
    setUser(me)
    try {
      const profileOverview = await getProfileOverview()
      setOverview(profileOverview)
      setLastProfileId(profileOverview.profile.id)
    } catch {
      setOverview(null)
    }
  }

  const handleSignup = async (fullName: string, email: string, password: string) => {
    const result = await signup(email, password, fullName)
    setStoredTokens({
      accessToken: result.access_token,
      refreshToken: result.refresh_token,
    })
    const me = await getCurrentUser()
    setUser(me)
    setOverview(null)
  }

  const handleOnboarding = async (payload: OnboardingPayload) => {
    await updateOnboarding(payload)
  }

  const handleUpload = async (file: File, preferences: string) => {
    setError(null)
    try {
      const result = await uploadCV(file, preferences)
      setLastProfileId(result.user_profile_id)
      router.push(`/results?profile_id=${result.user_profile_id}`)
    } catch (err: any) {
      setError(err.message || 'Failed to upload your resume')
    }
  }

  return (
    <Layout>
      <Head>
        <title>Clover | Job Match Assistant</title>
      </Head>

      <section className="section" style={{ paddingTop: '42px' }}>
        <div className="container">
          <div className="hero-shell animate-fade-in-up">
            <div>
              <p className="eyebrow">Job Search Assistant</p>
              <h1 style={{ marginBottom: '14px' }}>
                Find better-fit jobs faster, with less guesswork.
              </h1>
              <p style={{ color: 'var(--text-secondary)', fontSize: '1.05rem', maxWidth: '720px' }}>
                Clover reads your resume, ranks live openings by fit, and helps you move from discovery to application with clear next steps.
              </p>
            </div>

            <div className="hero-stats">
              <div className="glass-surface" style={{ padding: '16px 18px' }}>
                <div className="stat-value">2</div>
                <div className="stat-label">Quick setup steps</div>
              </div>
              <div className="glass-surface" style={{ padding: '16px 18px' }}>
                <div className="stat-value">Live</div>
                <div className="stat-label">Multi-source jobs</div>
              </div>
              <div className="glass-surface" style={{ padding: '16px 18px' }}>
                <div className="stat-value">Saved</div>
                <div className="stat-label">Profile and history</div>
              </div>
            </div>
          </div>

          {error && (
            <div style={{ maxWidth: '980px', margin: '0 auto 16px auto', padding: '14px', border: '1px solid #fda29b', borderRadius: 'var(--radius-md)', background: '#fef3f2', color: '#b42318' }}>
              {error}
            </div>
          )}

          {checkingSession ? (
            <div className="glass-card" style={{ padding: '32px', textAlign: 'center' }}>
              <div className="spinner" style={{ margin: '0 auto 16px auto' }} />
              Restoring your saved session...
            </div>
          ) : !user ? (
            <div className="workspace-grid">
              <div className="glass-card" style={{ padding: '28px' }}>
                <p className="eyebrow">How It Works</p>
                <h3 style={{ marginBottom: '8px' }}>Start in less than 3 minutes</h3>
                <div style={{ display: 'grid', gap: '12px' }}>
                  <div className="glass-surface" style={{ padding: '14px' }}>
                    <strong>1. Share your goals</strong>
                    <p style={{ color: 'var(--text-secondary)', marginTop: '4px' }}>Tell Clover what roles, locations, and work style you want.</p>
                  </div>
                  <div className="glass-surface" style={{ padding: '14px' }}>
                    <strong>2. Upload your resume</strong>
                    <p style={{ color: 'var(--text-secondary)', marginTop: '4px' }}>We extract your experience and skills for matching.</p>
                  </div>
                  <div className="glass-surface" style={{ padding: '14px' }}>
                    <strong>3. Focus on your best-fit roles</strong>
                    <p style={{ color: 'var(--text-secondary)', marginTop: '4px' }}>See transparent fit reasons and generate tailored application documents.</p>
                  </div>
                </div>
              </div>
              <AuthPanel onLogin={handleLogin} onSignup={handleSignup} />
            </div>
          ) : (
            <>
              {overview && (
                <div className="glass-card" style={{ padding: '20px', marginBottom: '20px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', gap: '12px', flexWrap: 'wrap', alignItems: 'center' }}>
                    <div>
                      <p className="eyebrow" style={{ marginBottom: '4px' }}>Welcome Back</p>
                      <h3 style={{ marginBottom: '6px' }}>{user.full_name || user.email}</h3>
                      <p style={{ color: 'var(--text-secondary)' }}>
                        Resume version {overview.profile.resume_version} is active. We found {overview.matched_jobs_count} saved matches.
                      </p>
                    </div>
                    <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
                      <Link href={`/results?profile_id=${overview.profile.id}`} className="btn btn-primary">
                        View Recommended Jobs
                      </Link>
                      <Link href="/profile" className="btn btn-secondary">
                        Open Profile
                      </Link>
                    </div>
                  </div>
                </div>
              )}

              <div className="workspace-grid">
                <OnboardingWizard initialProfileId={lastProfileId} onSubmit={handleOnboarding} />
                <CVUploader onUpload={handleUpload} currentResume={overview?.active_resume} />
              </div>
            </>
          )}
        </div>
      </section>
    </Layout>
  )
}
