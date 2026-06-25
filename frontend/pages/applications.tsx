import React, { useEffect, useState } from 'react'
import Head from 'next/head'
import Link from 'next/link'
import Layout from '../components/Layout'
import { getApplicationTrackerBriefing, listApplications } from '../lib/api'
import { ApplicationResponse, ApplicationTrackerResponse } from '../types'

export default function ApplicationsPage() {
  const [items, setItems] = useState<ApplicationResponse[]>([])
  const [tracker, setTracker] = useState<ApplicationTrackerResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    async function fetchItems() {
      try {
        setLoading(true)
        const [data, briefing] = await Promise.all([
          listApplications(),
          getApplicationTrackerBriefing(),
        ])
        setItems(data)
        setTracker(briefing)
      } catch (err: any) {
        setError(err.message || 'Unable to fetch applications')
      } finally {
        setLoading(false)
      }
    }
    fetchItems()
  }, [])

  return (
    <Layout>
      <Head>
        <title>Applications | Clover</title>
      </Head>
      <div className="container section">
        <p className="eyebrow">Applications</p>
        <h1 style={{ marginBottom: '10px' }}>Your application tracker</h1>
        <p style={{ color: 'var(--text-secondary)', marginBottom: '24px' }}>
          Review roles where you generated documents or started applying, with deadline-aware next steps.
        </p>

        {loading ? (
          <div className="glass-card" style={{ padding: '28px' }}>
            <div className="spinner" style={{ margin: '0 auto 16px auto' }} />
            <div style={{ textAlign: 'center' }}>Loading applications...</div>
          </div>
        ) : error ? (
          <div className="glass-card" style={{ padding: '24px', color: '#f87171' }}>
            {error}
          </div>
        ) : items.length === 0 ? (
          <div className="glass-card" style={{ padding: '24px' }}>
            No tracked applications yet. Generate documents from a strong match to create your first item.
          </div>
        ) : (
          <>
            {tracker && (
              <div className="glass-card" style={{ padding: '20px', marginBottom: '18px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', gap: '18px', flexWrap: 'wrap' }}>
                  <div>
                    <h3 style={{ marginBottom: '6px' }}>Tracker briefing</h3>
                    <p style={{ color: 'var(--text-secondary)' }}>{tracker.headline}</p>
                  </div>
                  <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
                    <span className="badge badge-info">{tracker.active_count} active</span>
                    <span className={tracker.overdue_count ? 'badge badge-danger' : 'badge badge-success'}>
                      {tracker.overdue_count} overdue
                    </span>
                    <span className={tracker.due_soon_count ? 'badge badge-info' : 'badge badge-success'}>
                      {tracker.due_soon_count} due soon
                    </span>
                  </div>
                </div>
              </div>
            )}

            <div style={{ display: 'grid', gap: '14px' }}>
              {items.map((app) => {
                const deadline = app.deadline_at ? new Date(app.deadline_at).toLocaleDateString() : 'No deadline'
                const urgent = app.urgency === 'critical' || app.urgency === 'high'
                return (
                  <Link
                    key={app.id}
                    href={`/applications/${app.id}`}
                    className="glass-card"
                    style={{ padding: '18px 20px', display: 'block' }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', gap: '16px', flexWrap: 'wrap' }}>
                      <div>
                        <div style={{ fontWeight: 700 }}>{app.job_title || 'Role in progress'}</div>
                        <div style={{ color: 'var(--text-secondary)' }}>
                          {app.company || 'Company unavailable'}
                          {app.location ? ` • ${app.location}` : ''}
                        </div>
                        <div style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>
                          Updated {new Date(app.updated_at).toLocaleString()} · Deadline {deadline}
                        </div>
                      </div>
                      <div style={{ display: 'grid', gap: '8px', justifyItems: 'end' }}>
                        <span className="badge badge-info">{app.match_label || 'Tracked'}</span>
                        <span className="badge badge-success">{app.status}</span>
                        <span className={urgent ? 'badge badge-danger' : 'badge badge-info'}>{app.deadline_status}</span>
                      </div>
                    </div>
                    <p style={{ marginTop: '10px', color: 'var(--text-secondary)' }}>
                      {app.next_action || app.last_agent_summary || app.fit_explanation}
                    </p>
                  </Link>
                )
              })}
            </div>
          </>
        )}
      </div>
    </Layout>
  )
}
