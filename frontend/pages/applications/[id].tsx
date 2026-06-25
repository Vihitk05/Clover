import React, { useEffect, useMemo, useState } from 'react'
import Head from 'next/head'
import { useRouter } from 'next/router'
import Layout from '../../components/Layout'
import GapRadar from '../../components/GapRadar'
import SkillBadge from '../../components/SkillBadge'
import CoverLetterModal from '../../components/CoverLetterModal'
import { downloadGeneratedAsset, getApplicationDetail, updateApplication } from '../../lib/api'
import { ApplicationDetailResponse } from '../../types'

const STATUS_OPTIONS = ['saved', 'generated', 'applied', 'interviewing', 'offer', 'rejected', 'withdrawn']

function dateInputValue(value?: string): string {
  if (!value) return ''
  return new Date(value).toISOString().slice(0, 10)
}

export default function ApplicationDetailPage() {
  const router = useRouter()
  const { id } = router.query

  const [data, setData] = useState<ApplicationDetailResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [modalOpen, setModalOpen] = useState(false)
  const [saving, setSaving] = useState(false)
  const [status, setStatus] = useState('saved')
  const [deadline, setDeadline] = useState('')
  const [nextAction, setNextAction] = useState('')
  const [notes, setNotes] = useState('')

  useEffect(() => {
    if (!id) return
    async function load() {
      try {
        setLoading(true)
        const result = await getApplicationDetail(id as string)
        setData(result)
        setStatus(result.application.status || 'saved')
        setDeadline(dateInputValue(result.application.deadline_at))
        setNextAction(result.application.next_action || '')
        setNotes(result.application.notes || '')
      } catch (err: any) {
        setError(err.message || 'Unable to load application details')
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [id])

  const scoreBreakdown = useMemo(() => {
    const breakdown = data?.match?.score_breakdown
    return {
      semantic: breakdown?.semantic || 0,
      skills: breakdown?.skills || 0,
      seniority: breakdown?.seniority || 0,
      location: breakdown?.location || 0,
      experience: breakdown?.experience || 0,
    }
  }, [data])

  const handleDownload = async (assetType: 'resume' | 'cover-letter') => {
    try {
      if (!data?.match?.match_result_id) return
      const { blob, filename } = await downloadGeneratedAsset(data.match.match_result_id, assetType)
      const url = URL.createObjectURL(blob)
      const anchor = document.createElement('a')
      anchor.href = url
      anchor.download = filename
      document.body.appendChild(anchor)
      anchor.click()
      anchor.remove()
      URL.revokeObjectURL(url)
    } catch (err: any) {
      setError(err.message || 'Unable to download file')
    }
  }

  const handleSaveTracker = async () => {
    try {
      if (!data?.application.id) return
      setSaving(true)
      const updated = await updateApplication(data.application.id, {
        status,
        deadline_at: deadline ? `${deadline}T17:00:00` : undefined,
        next_action: nextAction,
        notes,
      })
      setData({
        ...data,
        application: updated,
      })
      setStatus(updated.status)
      setDeadline(dateInputValue(updated.deadline_at))
      setNextAction(updated.next_action || '')
      setNotes(updated.notes || '')
    } catch (err: any) {
      setError(err.message || 'Unable to update application')
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return (
      <Layout>
        <div className="container section" style={{ textAlign: 'center' }}>
          <div className="spinner" style={{ margin: '0 auto 16px auto' }} />
          Loading application details...
        </div>
      </Layout>
    )
  }

  if (error || !data) {
    return (
      <Layout>
        <div className="container section">
          <div className="glass-card" style={{ padding: '24px', color: '#b42318' }}>{error || 'Application not found'}</div>
        </div>
      </Layout>
    )
  }

  const { application, match } = data
  const urgent = application.urgency === 'critical' || application.urgency === 'high'

  return (
    <Layout>
      <Head>
        <title>{application.job_title || 'Application'} | Clover</title>
      </Head>

      <div className="container section" style={{ paddingTop: '36px' }}>
        <button className="btn-ghost" onClick={() => router.push('/applications')} style={{ marginBottom: '12px' }}>
          ← Back to Applications
        </button>

        <div className="hero-shell" style={{ marginBottom: '20px' }}>
          <div>
            <p className="eyebrow">Application Detail</p>
            <h1 style={{ fontSize: '2rem', marginBottom: '8px' }}>{application.job_title || 'Role in progress'}</h1>
            <p style={{ color: 'var(--text-secondary)' }}>
              {application.company || 'Company unavailable'}
              {application.location ? ` • ${application.location}` : ''}
            </p>
            {application.fit_explanation && (
              <p style={{ color: 'var(--text-muted)', marginTop: '8px' }}>{application.fit_explanation}</p>
            )}
          </div>
          <div style={{ display: 'grid', gap: '10px' }}>
            <span className="badge badge-info">{application.match_label || 'Tracked'}</span>
            <span className="badge badge-success">{application.status}</span>
            <span className={urgent ? 'badge badge-danger' : 'badge badge-info'}>{application.deadline_status}</span>
            <span className="badge badge-info">Updated {new Date(application.updated_at).toLocaleDateString()}</span>
          </div>
        </div>

        <div className="detail-grid">
          <div style={{ display: 'grid', gap: '18px' }}>
            <div className="glass-card" style={{ padding: '24px' }}>
              <h3 style={{ marginBottom: '12px' }}>Tracker</h3>
              <div style={{ display: 'grid', gap: '12px' }}>
                <select className="input" value={status} onChange={(event) => setStatus(event.target.value)}>
                  {STATUS_OPTIONS.map((option) => (
                    <option key={option} value={option}>
                      {option}
                    </option>
                  ))}
                </select>
                <input
                  className="input"
                  type="date"
                  value={deadline}
                  onChange={(event) => setDeadline(event.target.value)}
                />
                <textarea
                  className="input"
                  rows={3}
                  value={nextAction}
                  onChange={(event) => setNextAction(event.target.value)}
                  placeholder="Next action"
                />
                <textarea
                  className="input"
                  rows={4}
                  value={notes}
                  onChange={(event) => setNotes(event.target.value)}
                  placeholder="Notes"
                />
                <button className="btn btn-primary" onClick={handleSaveTracker} disabled={saving}>
                  {saving ? 'Saving...' : 'Save tracker'}
                </button>
              </div>
              <p style={{ marginTop: '14px', color: 'var(--text-secondary)' }}>
                {application.last_agent_summary || application.next_action}
              </p>
              {application.deadline_at && (
                <p style={{ marginTop: '8px', color: 'var(--text-muted)', fontSize: '0.9rem' }}>
                  Deadline {new Date(application.deadline_at).toLocaleDateString()}
                </p>
              )}
            </div>

            <div className="glass-card" style={{ padding: '24px' }}>
              <h3 style={{ marginBottom: '10px' }}>Match Summary</h3>
              {match ? (
                <>
                  <GapRadar scoreBreakdown={scoreBreakdown} />
                  <p style={{ marginTop: '12px', color: 'var(--text-secondary)' }}>
                    {scoreBreakdown.skills >= 70 && scoreBreakdown.experience < 60
                      ? 'Your technical skills are strong for this role, but more hands-on experience could improve your chances.'
                      : scoreBreakdown.skills < 60
                        ? 'This role is partially aligned. Building missing role skills can improve your competitiveness.'
                        : 'Your profile is well aligned across the main requirements for this role.'}
                  </p>
                  <div style={{ marginTop: '12px', display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                    {(match.matched_skills || []).slice(0, 8).map((skill) => (
                      <SkillBadge key={skill} skill={skill} variant="success" />
                    ))}
                  </div>
                </>
              ) : (
                <p style={{ color: 'var(--text-secondary)' }}>No match summary available for this application yet.</p>
              )}
            </div>
          </div>

          <div style={{ display: 'grid', gap: '18px' }}>
            <div className="glass-card" style={{ padding: '24px' }}>
              <h3 style={{ marginBottom: '10px' }}>Gap Analysis</h3>
              {data.gap_report ? (
                <>
                  <p style={{ color: 'var(--text-secondary)', marginBottom: '10px' }}>{data.gap_report.summary}</p>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                    {data.gap_report.missing_skills.slice(0, 8).map((skill) => (
                      <SkillBadge key={skill} skill={skill} variant="danger" />
                    ))}
                  </div>
                </>
              ) : (
                <p style={{ color: 'var(--text-secondary)' }}>No gap report generated yet.</p>
              )}
            </div>

            <div className="glass-card" style={{ padding: '24px' }}>
              <h3 style={{ marginBottom: '10px' }}>Generated Documents</h3>
              <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                <button className="btn btn-secondary" onClick={() => handleDownload('resume')} disabled={!match}>
                  Download Optimized Resume
                </button>
                <button className="btn btn-secondary" onClick={() => handleDownload('cover-letter')} disabled={!match}>
                  Download Cover Letter
                </button>
                <button className="btn btn-primary" onClick={() => setModalOpen(true)} disabled={!data.cover_letter}>
                  Open Cover Letter
                </button>
              </div>
              <p style={{ color: 'var(--text-muted)', marginTop: '10px', fontSize: '0.88rem' }}>
                Documents generated: {application.generated_at ? new Date(application.generated_at).toLocaleString() : 'Not generated yet'}
              </p>
            </div>

            <div className="glass-card" style={{ padding: '24px' }}>
              <h3 style={{ marginBottom: '10px' }}>Job Description</h3>
              <p style={{ color: 'var(--text-secondary)', whiteSpace: 'pre-wrap' }}>
                {(data.job_description || '').slice(0, 1800) || 'Job description unavailable.'}
              </p>
            </div>
          </div>
        </div>
      </div>

      <CoverLetterModal isOpen={modalOpen} onClose={() => setModalOpen(false)} content={data.cover_letter || ''} />
    </Layout>
  )
}
