import React, { useMemo, useState } from 'react'
import { OnboardingPayload } from '../types'

interface OnboardingWizardProps {
  initialProfileId?: string
  onSubmit: (payload: OnboardingPayload) => Promise<void>
}

const ROLE_SUGGESTIONS = [
  'Backend Engineer',
  'Full Stack Engineer',
  'Data Engineer',
  'Machine Learning Engineer',
  'Data Scientist',
]

const LOCATION_SUGGESTIONS = ['Dublin', 'Cork', 'Galway', 'Remote (Ireland)', 'Remote (EU)']
const WORK_TYPE_SUGGESTIONS = ['Remote', 'Hybrid', 'On-site', 'Contract']

function parseCsv(text: string): string[] {
  return text
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean)
}

function toggleValue(values: string[], value: string): string[] {
  return values.includes(value) ? values.filter((v) => v !== value) : [...values, value]
}

export default function OnboardingWizard({ initialProfileId, onSubmit }: OnboardingWizardProps) {
  const [step, setStep] = useState(1)
  const [targetRoles, setTargetRoles] = useState<string[]>([])
  const [targetRolesText, setTargetRolesText] = useState('')
  const [preferredLocations, setPreferredLocations] = useState<string[]>([])
  const [locationsText, setLocationsText] = useState('')
  const [salaryMin, setSalaryMin] = useState('')
  const [salaryMax, setSalaryMax] = useState('')
  const [workTypes, setWorkTypes] = useState<string[]>(['Hybrid', 'Remote'])
  const [careerGoals, setCareerGoals] = useState('')
  const [preferencesRaw, setPreferencesRaw] = useState('')
  const [loading, setLoading] = useState(false)
  const [saved, setSaved] = useState(false)

  const payload = useMemo<OnboardingPayload>(() => {
    const roleSet = new Set([...targetRoles, ...parseCsv(targetRolesText)])
    const locationSet = new Set([...preferredLocations, ...parseCsv(locationsText)])
    return {
      profile_id: initialProfileId,
      target_roles: Array.from(roleSet),
      preferred_locations: Array.from(locationSet),
      salary_expectation_min: salaryMin ? Number(salaryMin) : undefined,
      salary_expectation_max: salaryMax ? Number(salaryMax) : undefined,
      work_types: workTypes,
      career_goals: careerGoals,
      preferences_raw: preferencesRaw,
      skill_confidence: {},
    }
  }, [
    initialProfileId,
    targetRoles,
    targetRolesText,
    preferredLocations,
    locationsText,
    salaryMin,
    salaryMax,
    workTypes,
    careerGoals,
    preferencesRaw,
  ])

  const profileCompletion = useMemo(() => {
    let score = 0
    if (payload.target_roles.length > 0) score += 25
    if (payload.preferred_locations.length > 0) score += 20
    if (payload.work_types.length > 0) score += 20
    if (payload.career_goals.trim()) score += 20
    if (payload.preferences_raw.trim()) score += 15
    return score
  }, [payload])

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    try {
      await onSubmit(payload)
      setSaved(true)
      setTimeout(() => setSaved(false), 2500)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="glass-card" style={{ padding: '28px' }}>
      <div style={{ marginBottom: '16px' }}>
        <p className="eyebrow">Step 1</p>
        <h3 style={{ marginBottom: '6px' }}>Tell us what a great role looks like</h3>
        <p style={{ color: 'var(--text-secondary)' }}>
          This helps Clover prioritize opportunities that match your goals.
        </p>
      </div>

      <div style={{ marginBottom: '18px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.82rem', color: 'var(--text-muted)', marginBottom: '6px' }}>
          <span>Profile setup progress</span>
          <span>{profileCompletion}%</span>
        </div>
        <div style={{ height: '8px', borderRadius: '999px', background: 'var(--bg-elevated)', overflow: 'hidden' }}>
          <div style={{ width: `${profileCompletion}%`, height: '100%', background: 'linear-gradient(90deg, var(--clover-600), var(--clover-400))' }} />
        </div>
      </div>

      <div style={{ display: 'flex', gap: '8px', marginBottom: '18px', flexWrap: 'wrap' }}>
        {[1, 2].map((item) => (
          <button
            key={item}
            type="button"
            className="btn-ghost"
            onClick={() => setStep(item)}
            style={{
              borderRadius: '999px',
              background: step === item ? 'var(--bg-secondary)' : 'transparent',
              border: step === item ? '1px solid var(--border-accent)' : '1px solid transparent',
              color: step === item ? 'var(--text-primary)' : 'var(--text-muted)',
              fontWeight: 700,
            }}
          >
            {item === 1 && 'Target Roles'}
            {item === 2 && 'Preferences'}
          </button>
        ))}
      </div>

      <form onSubmit={submit} style={{ display: 'grid', gap: '14px' }}>
        {step === 1 && (
          <>
            <div>
              <label className="field-label">Target roles</label>
              <div className="chip-row">
                {ROLE_SUGGESTIONS.map((role) => (
                  <button
                    key={role}
                    type="button"
                    className="chip"
                    data-active={targetRoles.includes(role)}
                    onClick={() => setTargetRoles((prev) => toggleValue(prev, role))}
                  >
                    {role}
                  </button>
                ))}
              </div>
              <input
                className="input"
                placeholder="Add more roles (comma-separated)"
                value={targetRolesText}
                onChange={(e) => setTargetRolesText(e.target.value)}
              />
            </div>

            <div>
              <label className="field-label">Preferred locations</label>
              <div className="chip-row">
                {LOCATION_SUGGESTIONS.map((location) => (
                  <button
                    key={location}
                    type="button"
                    className="chip"
                    data-active={preferredLocations.includes(location)}
                    onClick={() => setPreferredLocations((prev) => toggleValue(prev, location))}
                  >
                    {location}
                  </button>
                ))}
              </div>
              <input
                className="input"
                placeholder="Add more locations (comma-separated)"
                value={locationsText}
                onChange={(e) => setLocationsText(e.target.value)}
              />
            </div>
          </>
        )}

        {step === 2 && (
          <>
            <div>
              <label className="field-label">Work style</label>
              <div className="chip-row">
                {WORK_TYPE_SUGGESTIONS.map((workType) => (
                  <button
                    key={workType}
                    type="button"
                    className="chip"
                    data-active={workTypes.includes(workType)}
                    onClick={() => setWorkTypes((prev) => toggleValue(prev, workType))}
                  >
                    {workType}
                  </button>
                ))}
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
              <div>
                <label className="field-label">Salary minimum (EUR)</label>
                <input className="input" placeholder="e.g. 60000" value={salaryMin} onChange={(e) => setSalaryMin(e.target.value)} />
              </div>
              <div>
                <label className="field-label">Salary maximum (EUR)</label>
                <input className="input" placeholder="e.g. 90000" value={salaryMax} onChange={(e) => setSalaryMax(e.target.value)} />
              </div>
            </div>

            <div>
              <label className="field-label">Career goals</label>
              <textarea
                className="input"
                placeholder="What impact or role growth are you aiming for in the next 12 months?"
                value={careerGoals}
                onChange={(e) => setCareerGoals(e.target.value)}
              />
            </div>

            <div>
              <label className="field-label">Anything else we should consider?</label>
              <textarea
                className="input"
                placeholder="Example: Prefer product-focused teams with strong mentorship and clear growth paths."
                value={preferencesRaw}
                onChange={(e) => setPreferencesRaw(e.target.value)}
              />
            </div>
          </>
        )}

        <div style={{ display: 'flex', justifyContent: 'space-between', gap: '12px', flexWrap: 'wrap' }}>
          <button
            type="button"
            className="btn btn-secondary"
            disabled={step === 1}
            onClick={() => setStep((s) => Math.max(1, s - 1))}
          >
            Back
          </button>
          {step < 2 ? (
            <button type="button" className="btn btn-primary" onClick={() => setStep((s) => Math.min(2, s + 1))}>
              Continue
            </button>
          ) : (
            <button className="btn btn-primary" disabled={loading}>
              {loading ? 'Saving your preferences...' : 'Save Preferences'}
            </button>
          )}
        </div>

        {saved && <div style={{ color: 'var(--clover-700)', fontSize: '0.88rem' }}>Preferences saved. Your recommendations will use these settings.</div>}
      </form>
    </div>
  )
}
