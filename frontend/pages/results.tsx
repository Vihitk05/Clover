import React, { useEffect, useMemo, useState } from 'react'
import { useRouter } from 'next/router'
import Head from 'next/head'
import Layout from '../components/Layout'
import JobCard from '../components/JobCard'
import { getProfileMatches, getProfileOverview, matchJobs, recordSignal } from '../lib/api'
import { MatchJobsResponse } from '../types'

export default function ResultsPage() {
  const router = useRouter()
  const { profile_id } = router.query

  const [activeProfileId, setActiveProfileId] = useState<string | null>(null)
  const [data, setData] = useState<MatchJobsResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [filter, setFilter] = useState<'all' | 'eligible'>('all')

  useEffect(() => {
    async function resolveProfileId(): Promise<string | null> {
      if (profile_id && typeof profile_id === 'string') return profile_id
      try {
        const overview = await getProfileOverview()
        return overview.profile.id
      } catch {
        return null
      }
    }

    async function fetchMatches() {
      try {
        setLoading(true)
        setError(null)
        const resolvedProfileId = await resolveProfileId()
        if (!resolvedProfileId) {
          setLoading(false)
          return
        }
        setActiveProfileId(resolvedProfileId)

        let viewedCount = 0
        const stored = await getProfileMatches(resolvedProfileId, false)
        if (stored.total_matches > 0) {
          setData(stored)
          viewedCount = stored.total_matches
        } else {
          const result = await matchJobs(resolvedProfileId)
          setData(result)
          viewedCount = result.total_matches
        }

        await recordSignal({
          profile_id: resolvedProfileId,
          signal_type: 'preferences_updated',
          payload: {
            profile_id: resolvedProfileId,
            viewed_results: viewedCount,
          },
        }).catch(() => undefined)
      } catch (err: any) {
        setError(err.message || 'Failed to load your job matches')
      } finally {
        setLoading(false)
      }
    }

    fetchMatches()
  }, [profile_id])

  const displayedMatches = useMemo(
    () => data?.matches.filter((m) => filter === 'all' || m.eligible_for_generation) || [],
    [data, filter]
  )

  const refreshMatches = async () => {
    if (!activeProfileId) return
    try {
      setLoading(true)
      setError(null)
      const refreshed = await getProfileMatches(activeProfileId, true)
      setData(refreshed)
    } catch (err: any) {
      setError(err.message || 'Could not refresh matches right now')
    } finally {
      setLoading(false)
    }
  }

  if (!loading && !activeProfileId && !error) {
    return (
      <Layout>
        <div className="container section" style={{ textAlign: 'center' }}>
          <h2 style={{ marginBottom: '8px' }}>No profile found yet</h2>
          <p style={{ color: 'var(--text-secondary)', marginBottom: '20px' }}>
            Upload your resume to get personalized job matches.
          </p>
          <button className="btn btn-primary" onClick={() => router.push('/')}>Go to Home</button>
        </div>
      </Layout>
    )
  }

  return (
    <Layout>
      <Head>
        <title>Recommended Jobs | Clover</title>
      </Head>

      <section className="section" style={{ paddingTop: '36px' }}>
        <div className="container">
          <div className="hero-shell" style={{ marginBottom: '24px' }}>
            <div>
              <p className="eyebrow">Recommended Jobs</p>
              <h1 style={{ fontSize: '2.15rem', marginBottom: '8px' }}>Your best-fit opportunities</h1>
              <p style={{ color: 'var(--text-secondary)' }}>
                Roles are ranked by how well they align with your experience, skills, and job goals.
              </p>
            </div>

            {data && (
              <div className="hero-stats">
                <div className="glass-surface" style={{ padding: '12px 16px' }}>
                  <div className="stat-value">{data.average_score}%</div>
                  <div className="stat-label">Average fit</div>
                </div>
                <div className="glass-surface" style={{ padding: '12px 16px' }}>
                  <div className="stat-value">{data.eligible_count}</div>
                  <div className="stat-label">Ready for docs</div>
                </div>
                <div className="glass-surface" style={{ padding: '12px 16px' }}>
                  <div className="stat-value">{data.total_matches}</div>
                  <div className="stat-label">Total roles</div>
                </div>
              </div>
            )}
          </div>

          {loading ? (
            <div className="glass-card" style={{ textAlign: 'center', padding: '48px' }}>
              <div className="spinner" style={{ margin: '0 auto 16px auto' }} />
              <p style={{ color: 'var(--text-secondary)' }}>Finding your best-fit roles...</p>
            </div>
          ) : error ? (
            <div style={{ padding: '24px', border: '1px solid #fda29b', borderRadius: 'var(--radius-md)', background: '#fef3f2', color: '#b42318', textAlign: 'center' }}>
              {error}
              <div style={{ marginTop: '16px', display: 'flex', justifyContent: 'center', gap: '10px', flexWrap: 'wrap' }}>
                <button className="btn btn-secondary" onClick={() => router.push('/')}>Back to Home</button>
                <button className="btn btn-primary" onClick={refreshMatches}>Try Again</button>
              </div>
            </div>
          ) : (
            <>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '12px', marginBottom: '20px', flexWrap: 'wrap' }}>
                <h2 style={{ fontSize: '1.4rem' }}>Showing {displayedMatches.length} roles</h2>
                <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                  <button
                    className={`btn ${filter === 'all' ? 'btn-primary' : 'btn-secondary'}`}
                    onClick={() => setFilter('all')}
                  >
                    All roles
                  </button>
                  <button
                    className={`btn ${filter === 'eligible' ? 'btn-primary' : 'btn-secondary'}`}
                    onClick={() => setFilter('eligible')}
                  >
                    Document-ready roles
                  </button>
                  <button className="btn btn-secondary" onClick={refreshMatches}>
                    Refresh Matches
                  </button>
                </div>
              </div>

              {displayedMatches.length === 0 ? (
                <div className="glass-card" style={{ padding: '40px', textAlign: 'center' }}>
                  <p style={{ color: 'var(--text-secondary)', fontSize: '1rem', marginBottom: '12px' }}>
                    No roles match this filter yet.
                  </p>
                  <p style={{ color: 'var(--text-muted)' }}>
                    Try widening your preferences or refresh the match list after updating your resume.
                  </p>
                </div>
              ) : (
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: '18px' }}>
                  {displayedMatches.map((match, i) => (
                    <div key={match.match_result_id} className="animate-fade-in-up" style={{ animationDelay: `${i * 0.05}s` }}>
                      <JobCard match={match} profileId={activeProfileId || undefined} />
                    </div>
                  ))}
                </div>
              )}
            </>
          )}
        </div>
      </section>
    </Layout>
  )
}
