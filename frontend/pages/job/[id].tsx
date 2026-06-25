import React, { useEffect, useState } from 'react'
import { useRouter } from 'next/router'
import Head from 'next/head'
import Layout from '../../components/Layout'
import GapRadar from '../../components/GapRadar'
import AtsScoreBar from '../../components/AtsScoreBar'
import SkillBadge from '../../components/SkillBadge'
import CoverLetterModal from '../../components/CoverLetterModal'
import {
  createApplication,
  downloadGeneratedAsset,
  generateOutputs,
  getMatchDetail,
  regenerateOutputs,
  recordSignal,
} from '../../lib/api'
import { GenerateOutputsResponse, MatchDetailResponse } from '../../types'

export default function JobDetail() {
  const router = useRouter()
  const { id, eligible, profile_id } = router.query
  const isEligible = eligible === 'true'

  const [detail, setDetail] = useState<MatchDetailResponse | null>(null)
  const [genData, setGenData] = useState<GenerateOutputsResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [generating, setGenerating] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [modalOpen, setModalOpen] = useState(false)

  const handleDownload = async (assetType: 'resume' | 'cover-letter') => {
    if (!id) return
    try {
      const { blob, filename } = await downloadGeneratedAsset(id as string, assetType)
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

  useEffect(() => {
    if (!id) return
    async function fetchDetail() {
      try {
        setLoading(true)
        const result = await getMatchDetail(id as string)
        setDetail(result)
        await recordSignal({
          profile_id: profile_id as string,
          job_id: result.match.job_id,
          signal_type: 'job_clicked',
          payload: {
            skills: result.match.matched_skills,
            locations: [result.match.location],
          },
        }).catch(() => undefined)
      } catch (err: any) {
        setError(err.message || 'Failed to load match detail')
      } finally {
        setLoading(false)
      }
    }
    fetchDetail()
  }, [id, profile_id])

  const handleGenerate = async (forceRegenerate = false) => {
    if (!id || !detail) return
    try {
      setGenerating(true)
      setError(null)
      const result = forceRegenerate
        ? await regenerateOutputs(id as string)
        : await generateOutputs(id as string)
      setGenData(result)
      await recordSignal({
        profile_id: profile_id as string,
        job_id: detail.match.job_id,
        signal_type: 'generation_requested',
        payload: {
          skills: detail.match.matched_skills,
          score: detail.match.personalized_fit_score,
        },
      }).catch(() => undefined)
      await createApplication({
        profile_id: profile_id as string,
        job_id: detail.match.job_id,
        match_result_id: id as string,
        status: 'generated',
        notes: 'Generated via Clover UI',
      }).catch(() => undefined)
    } catch (err: any) {
      setError(err.message || 'Generation failed')
    } finally {
      setGenerating(false)
    }
  }

  if (loading) {
    return (
      <Layout>
        <div style={{ textAlign: 'center', padding: '100px 0' }}>
          <div className="spinner" style={{ margin: '0 auto 24px auto' }} />
          <h2 style={{ fontSize: '1.5rem', marginBottom: '8px' }}>Preparing your job details...</h2>
          <p style={{ color: 'var(--text-secondary)' }}>Loading fit breakdown and application tools.</p>
        </div>
      </Layout>
    )
  }

  if (!detail) {
    return (
      <Layout>
        <div className="container section">
          <h2>Match not found</h2>
          <p style={{ color: 'var(--text-secondary)' }}>We could not load this job match.</p>
        </div>
      </Layout>
    )
  }

  const { match } = detail
  const scoreBreakdown = {
    semantic: match.score_breakdown?.semantic || 0,
    skills: match.score_breakdown?.skills || 0,
    seniority: match.score_breakdown?.seniority || 0,
    location: match.score_breakdown?.location || 0,
    experience: match.score_breakdown?.experience || 0,
  }

  return (
    <Layout>
      <Head>
        <title>{match.title} | Clover</title>
      </Head>

      <section className="section" style={{ paddingTop: '36px' }}>
        <div className="container">
          <div className="hero-shell" style={{ marginBottom: '20px' }}>
            <div>
              <button
                className="btn-ghost"
                onClick={() => router.back()}
                style={{ display: 'inline-flex', alignItems: 'center', gap: '8px', marginBottom: '10px', paddingLeft: 0 }}
              >
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="m15 18-6-6 6-6" />
                </svg>
                Back to Recommended Jobs
              </button>
              <h1 style={{ fontSize: '2rem', marginBottom: '8px' }}>{match.title}</h1>
              <p style={{ color: 'var(--text-secondary)' }}>
                {match.company} • {match.location || 'Location not specified'}
              </p>
              <div style={{ marginTop: '10px' }}>
                <span className="badge badge-info">{match.match_label}</span>
              </div>
              <p style={{ color: 'var(--text-muted)', marginTop: '10px' }}>{match.fit_explanation}</p>
            </div>
            <div style={{ display: 'grid', gap: '10px' }}>
              {match.job_url ? (
                <a href={match.job_url} target="_blank" rel="noreferrer" className="btn btn-secondary">
                  Open Original Listing
                </a>
              ) : (
                <span className="badge badge-warning">Original listing unavailable</span>
              )}
              {match.job_source && <span className="badge badge-info">{match.job_source}</span>}
            </div>
          </div>

          {error && (
            <div style={{ marginBottom: '24px', padding: '14px', border: '1px solid #fda29b', borderRadius: '12px', background: '#fef3f2', color: '#b42318' }}>
              {error}
            </div>
          )}

          <div className="detail-grid">
            <div className="glass-card" style={{ padding: '24px' }}>
              <h3 style={{ marginBottom: '16px' }}>Fit Breakdown</h3>
              <GapRadar scoreBreakdown={scoreBreakdown} />
              <div style={{ marginTop: '20px', display: 'grid', gap: '6px' }}>
                <div style={{ fontWeight: 700, color: 'var(--clover-700)' }}>{match.match_label}</div>
                <div style={{ color: 'var(--text-secondary)' }}>
                  {match.fit_explanation}
                </div>
                <div style={{ color: 'var(--text-muted)' }}>
                  Match confidence: {Math.round(match.confidence || 0)}%
                </div>
              </div>
              <p style={{ marginTop: '12px', color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
                {scoreBreakdown.skills >= 70 && scoreBreakdown.experience < 60
                  ? 'Your skills align strongly, but additional hands-on experience could improve competitiveness.'
                  : scoreBreakdown.skills < 60
                    ? 'Your background partially aligns. Building missing role skills can improve fit.'
                    : 'Your profile has solid alignment across core areas for this role.'}
              </p>

              <div style={{ marginTop: '16px' }}>
                <p style={{ fontWeight: 700, marginBottom: '8px' }}>Matched Skills</p>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                  {match.matched_skills.map((skill) => (
                    <SkillBadge key={skill} skill={skill} variant="success" />
                  ))}
                  {match.matched_skills.length === 0 && <span style={{ color: 'var(--text-muted)' }}>No explicit skills matched</span>}
                </div>
              </div>

              <div style={{ marginTop: '16px' }}>
                <p style={{ fontWeight: 700, marginBottom: '8px' }}>Missing Skills</p>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                  {match.missing_skills.length > 0 ? match.missing_skills.map((skill) => (
                    <SkillBadge key={skill} skill={skill} variant="danger" />
                  )) : <span style={{ color: 'var(--text-muted)' }}>No major gaps detected</span>}
                </div>
              </div>
            </div>

            <div style={{ display: 'grid', gap: '18px' }}>
              <div className="glass-card" style={{ padding: '24px' }}>
                    <h3 style={{ marginBottom: '10px' }}>Generate Application Documents</h3>
                    <p style={{ color: 'var(--text-secondary)', marginBottom: '14px' }}>
                      Generate a polished, downloadable resume and a tailored cover letter for this role.
                    </p>
                {!isEligible && (
                  <p style={{ color: '#b54708', marginBottom: '12px' }}>
                    Document generation is disabled because this role is below your quality threshold.
                  </p>
                )}
                <button
                  className={`btn ${isEligible ? 'btn-primary' : 'btn-secondary'}`}
                  disabled={!isEligible || generating}
                  onClick={() => handleGenerate(false)}
                >
                  {generating ? 'Preparing documents...' : 'Generate Documents'}
                </button>
                {genData && (
                  <button
                    className="btn btn-secondary"
                    style={{ marginTop: '10px' }}
                    disabled={generating}
                    onClick={() => handleGenerate(true)}
                  >
                    Regenerate Documents
                  </button>
                )}
              </div>

              {genData && (
                <>
                  {genData.cached && (
                    <div className="glass-card" style={{ padding: '16px 18px' }}>
                      <p style={{ color: 'var(--text-secondary)' }}>
                        Showing your previously generated documents for this job and resume version.
                      </p>
                    </div>
                  )}
                  <div className="glass-card" style={{ padding: '24px' }}>
                    <h3 style={{ marginBottom: '10px' }}>Resume Optimization Summary</h3>
                    <AtsScoreBar scoreBefore={genData.ats_score_before} scoreAfter={genData.ats_score_after} />
                    <div style={{ marginTop: '16px' }}>
                      <p style={{ fontWeight: 700, marginBottom: '8px' }}>Keywords Added</p>
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                        {genData.keywords_added.map((k) => <SkillBadge key={k} skill={k} variant="success" />)}
                      </div>
                    </div>
                  </div>

                  <div className="glass-card" style={{ padding: '24px' }}>
                    <h3 style={{ marginBottom: '10px' }}>What was improved</h3>
                    <div style={{ display: 'grid', gap: '10px' }}>
                      {genData.cv_diff.map((item, idx) => (
                        <div key={`${item.type}-${idx}`} style={{ border: '1px solid var(--border-subtle)', borderRadius: '10px', padding: '12px' }}>
                          <div style={{ fontSize: '0.74rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>{item.type}</div>
                          <div style={{ color: 'var(--text-secondary)' }}>{item.reason}</div>
                        </div>
                      ))}
                    </div>
                    <div style={{ marginTop: '14px', display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                      <button className="btn btn-secondary" onClick={() => handleDownload('resume')}>
                        Download Optimized Resume
                      </button>
                    </div>
                  </div>

                  <div className="glass-card" style={{ padding: '24px' }}>
                    <h3 style={{ marginBottom: '10px' }}>Cover Letter</h3>
                    <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                      <button className="btn btn-primary" onClick={() => setModalOpen(true)}>
                        Open Cover Letter
                      </button>
                      <button className="btn btn-secondary" onClick={() => handleDownload('cover-letter')}>
                        Download Cover Letter
                      </button>
                    </div>
                  </div>
                </>
              )}
            </div>
          </div>
        </div>
      </section>

      {genData && (
        <CoverLetterModal
          isOpen={modalOpen}
          onClose={() => setModalOpen(false)}
          content={genData.cover_letter}
        />
      )}
    </Layout>
  )
}
