import React from 'react'
import Link from 'next/link'
import { JobMatch } from '../types'
import ScoreRing from './ScoreRing'
import SkillBadge from './SkillBadge'

interface JobCardProps {
  match: JobMatch
  profileId?: string
}

export default function JobCard({ match, profileId }: JobCardProps) {
  const displayScore = match.personalized_fit_score ?? match.fit_score
  const label = match.match_label || 'Moderate Match'

  return (
    <div className="glass-card" style={{ display: 'flex', flexDirection: 'column', height: '100%', padding: '22px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '12px', marginBottom: '14px' }}>
        <div>
          <h3 style={{ fontSize: '1.15rem', marginBottom: '4px' }}>{match.title}</h3>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--text-muted)', fontSize: '0.92rem', flexWrap: 'wrap' }}>
            <span style={{ fontWeight: 700, color: 'var(--clover-700)' }}>{match.company}</span>
            <span>•</span>
            <span>{match.location || 'Location not specified'}</span>
            {match.job_source && <span className="badge badge-info">{match.job_source}</span>}
          </div>
        </div>
        <ScoreRing score={displayScore} size={56} />
      </div>

      <div style={{ marginBottom: '10px' }}>
        <span className="badge badge-info">{label}</span>
      </div>

      <p style={{ fontSize: '0.88rem', color: 'var(--text-secondary)', marginBottom: '14px' }}>
        {match.fit_explanation}
      </p>

      <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginBottom: '8px', textTransform: 'uppercase', letterSpacing: '0.08em', fontWeight: 700 }}>
        Skills Snapshot
      </p>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginBottom: '18px' }}>
        {match.matched_skills.slice(0, 4).map((skill) => (
          <SkillBadge key={skill} skill={skill} variant="success" />
        ))}
        {match.missing_skills.length > 0 && <SkillBadge skill={match.missing_skills[0]} variant="danger" />}
        {match.matched_skills.length === 0 && match.missing_skills.length === 0 && (
          <span style={{ fontSize: '0.875rem', color: 'var(--text-muted)' }}>No explicit skills extracted</span>
        )}
      </div>

      <div style={{ marginTop: 'auto', display: 'grid', gap: '8px' }}>
        <Link
          href={`/job/${match.match_result_id}?profile_id=${profileId || ''}&eligible=${match.eligible_for_generation}`}
          className={`btn ${match.eligible_for_generation ? 'btn-primary' : 'btn-secondary'}`}
          style={{ width: '100%' }}
        >
          {match.eligible_for_generation ? 'View Details and Documents' : 'View Match Details'}
        </Link>

        {match.job_url ? (
          <a
            href={match.job_url}
            target="_blank"
            rel="noreferrer"
            className="btn btn-secondary"
            style={{ width: '100%' }}
          >
            Open Original Job Listing
          </a>
        ) : (
          <div style={{ textAlign: 'center', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
            Original job link unavailable for this posting.
          </div>
        )}

        {!match.eligible_for_generation && (
          <p style={{ textAlign: 'center', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            This role is below your document-generation threshold.
          </p>
        )}
      </div>
    </div>
  )
}
