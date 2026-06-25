const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

import type {
  ApiEnvelope,
  ApplicationDetailResponse,
  ApplicationPayload,
  ApplicationResponse,
  ApplicationTrackerResponse,
  ApplicationUpdatePayload,
  AuthResponse,
  CurrentUserResponse,
  GenerateOutputsResponse,
  HealthResponse,
  MatchDetailResponse,
  MatchJobsResponse,
  OnboardingPayload,
  OnboardingResponse,
  ProfileOverviewResponse,
  ProfileUpdatePayload,
  ScraperTriggerPayload,
  SignalPayload,
  SignalResponse,
  UploadCVResponse,
} from '../types'

class ApiError extends Error {
  status: number
  constructor(message: string, status: number) {
    super(message)
    this.status = status
    this.name = 'ApiError'
  }
}

interface Tokens {
  accessToken: string
  refreshToken: string
}

const TOKENS_KEY = 'clover_tokens'

function isBrowser(): boolean {
  return typeof window !== 'undefined'
}

export function getStoredTokens(): Tokens | null {
  if (!isBrowser()) return null
  const raw = window.localStorage.getItem(TOKENS_KEY)
  if (!raw) return null
  try {
    return JSON.parse(raw)
  } catch {
    return null
  }
}

export function setStoredTokens(tokens: Tokens | null): void {
  if (!isBrowser()) return
  if (!tokens) {
    window.localStorage.removeItem(TOKENS_KEY)
    return
  }
  window.localStorage.setItem(TOKENS_KEY, JSON.stringify(tokens))
}

async function request<T>(path: string, options: RequestInit = {}, retry = true): Promise<T> {
  const tokens = getStoredTokens()
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string>),
  }
  if (tokens?.accessToken) {
    headers.Authorization = `Bearer ${tokens.accessToken}`
  }

  const url = `${API_BASE}${path}`
  const res = await fetch(url, { ...options, headers })

  if (res.status === 401 && retry && tokens?.refreshToken) {
    try {
      const refreshed = await refreshAuthToken(tokens.refreshToken)
      setStoredTokens({
        accessToken: refreshed.access_token,
        refreshToken: refreshed.refresh_token,
      })
      return request<T>(path, options, false)
    } catch {
      setStoredTokens(null)
    }
  }

  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }))
    throw new ApiError(body.detail || res.statusText, res.status)
  }
  return res.json() as Promise<T>
}

export async function checkHealth(): Promise<HealthResponse> {
  return request<HealthResponse>('/api/health')
}

export async function signup(email: string, password: string, fullName: string): Promise<AuthResponse> {
  return request<AuthResponse>('/api/auth/signup', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password, full_name: fullName }),
  })
}

export async function login(email: string, password: string): Promise<AuthResponse> {
  return request<AuthResponse>('/api/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  })
}

export async function oauthLogin(
  provider: 'google' | 'linkedin',
  email: string,
  fullName: string,
  oauthSubject: string
): Promise<AuthResponse> {
  return request<AuthResponse>('/api/auth/oauth', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      provider,
      email,
      full_name: fullName,
      oauth_subject: oauthSubject,
    }),
  })
}

export async function refreshAuthToken(refreshToken: string): Promise<AuthResponse> {
  return request<AuthResponse>(
    '/api/auth/refresh',
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refreshToken }),
    },
    false
  )
}

export async function logout(refreshToken: string): Promise<void> {
  await request('/api/auth/logout', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh_token: refreshToken }),
  })
}

export async function getCurrentUser(): Promise<CurrentUserResponse> {
  return request<CurrentUserResponse>('/api/auth/me')
}

export async function getOnboarding(): Promise<OnboardingResponse> {
  return request<OnboardingResponse>('/api/onboarding')
}

export async function updateOnboarding(payload: OnboardingPayload): Promise<OnboardingResponse> {
  return request<OnboardingResponse>('/api/onboarding', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
}

export async function uploadCV(file: File, preferences = ''): Promise<UploadCVResponse> {
  const formData = new FormData()
  formData.append('cv_file', file)
  formData.append('preferences', preferences)
  return request<UploadCVResponse>('/api/upload-cv', { method: 'POST', body: formData })
}

export async function matchJobs(
  profileId: string,
  topN = 20,
  minScore = 0
): Promise<MatchJobsResponse> {
  const params = new URLSearchParams({
    profile_id: profileId,
    top_n: String(topN),
    min_score: String(minScore),
  })
  return request<MatchJobsResponse>(`/api/match-jobs?${params}`)
}

export async function getProfileOverview(): Promise<ProfileOverviewResponse> {
  return request<ProfileOverviewResponse>('/api/profile/me')
}

export async function updateProfile(payload: ProfileUpdatePayload): Promise<ProfileOverviewResponse> {
  return request<ProfileOverviewResponse>('/api/profile/me', {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
}

export async function getProfileMatches(
  profileId?: string,
  refresh = false,
  topN = 20,
  minScore = 0
): Promise<MatchJobsResponse> {
  const params = new URLSearchParams({
    refresh: String(refresh),
    top_n: String(topN),
    min_score: String(minScore),
  })
  if (profileId) {
    params.set('profile_id', profileId)
  }
  return request<MatchJobsResponse>(`/api/profile/matches?${params}`)
}

export async function getMatchDetail(matchResultId: string): Promise<MatchDetailResponse> {
  return request<MatchDetailResponse>(`/api/match/${matchResultId}`)
}

export async function generateOutputs(matchResultId: string): Promise<GenerateOutputsResponse> {
  const params = new URLSearchParams({ match_result_id: matchResultId })
  return request<GenerateOutputsResponse>(`/api/generate-outputs?${params}`, { method: 'POST' })
}

export async function regenerateOutputs(matchResultId: string): Promise<GenerateOutputsResponse> {
  const params = new URLSearchParams({ match_result_id: matchResultId, force_regenerate: 'true' })
  return request<GenerateOutputsResponse>(`/api/generate-outputs?${params}`, { method: 'POST' })
}

export async function recordSignal(payload: SignalPayload): Promise<SignalResponse> {
  return request<SignalResponse>('/api/signals', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
}

export async function createApplication(payload: ApplicationPayload): Promise<ApplicationResponse> {
  return request<ApplicationResponse>('/api/applications', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
}

export async function listApplications(): Promise<ApplicationResponse[]> {
  return request<ApplicationResponse[]>('/api/applications')
}

export async function getApplicationTrackerBriefing(): Promise<ApplicationTrackerResponse> {
  return request<ApplicationTrackerResponse>('/api/applications/tracker/briefing')
}

export async function updateApplication(
  applicationId: string,
  payload: ApplicationUpdatePayload
): Promise<ApplicationResponse> {
  return request<ApplicationResponse>(`/api/applications/${applicationId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
}

export async function getApplicationDetail(applicationId: string): Promise<ApplicationDetailResponse> {
  return request<ApplicationDetailResponse>(`/api/applications/${applicationId}`)
}

async function downloadWithAuth(path: string, retry = true): Promise<Response> {
  const tokens = getStoredTokens()
  const headers: Record<string, string> = {}
  if (tokens?.accessToken) {
    headers.Authorization = `Bearer ${tokens.accessToken}`
  }

  const res = await fetch(`${API_BASE}${path}`, { headers })
  if (res.status === 401 && retry && tokens?.refreshToken) {
    const refreshed = await refreshAuthToken(tokens.refreshToken)
    setStoredTokens({
      accessToken: refreshed.access_token,
      refreshToken: refreshed.refresh_token,
    })
    return downloadWithAuth(path, false)
  }
  return res
}

export async function downloadActiveResume(): Promise<{ blob: Blob; filename: string }> {
  const res = await downloadWithAuth('/api/profile/resume/download')
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }))
    throw new ApiError(body.detail || res.statusText, res.status)
  }
  const blob = await res.blob()
  const header = res.headers.get('content-disposition') || ''
  const match = header.match(/filename=\"?([^\";]+)\"?/)
  const filename = match?.[1] || 'resume'
  return { blob, filename }
}

export async function downloadGeneratedAsset(
  matchResultId: string,
  assetType: 'resume' | 'cover-letter'
): Promise<{ blob: Blob; filename: string }> {
  const res = await downloadWithAuth(`/api/generated-assets/${matchResultId}/${assetType}`)
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }))
    throw new ApiError(body.detail || res.statusText, res.status)
  }
  const blob = await res.blob()
  const header = res.headers.get('content-disposition') || ''
  const match = header.match(/filename=\"?([^\";]+)\"?/)
  const fallback = assetType === 'resume' ? 'optimized_resume.docx' : 'cover_letter.docx'
  const filename = match?.[1] || fallback
  return { blob, filename }
}

export async function triggerScraper(
  provider: 'jobsie' | 'irishjobs' | 'linkedin' | 'all',
  payload: ScraperTriggerPayload
): Promise<ApiEnvelope> {
  return request<ApiEnvelope>(`/api/scrapers/${provider}/run`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
}

export async function getScraperTask(taskId: string): Promise<ApiEnvelope> {
  return request<ApiEnvelope>(`/api/scrapers/tasks/${taskId}`)
}

export { ApiError }
