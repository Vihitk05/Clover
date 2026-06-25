export interface Education {
  degree: string
  university: string
  year?: number
  raw_text?: string
}

export interface Experience {
  role: string
  company: string
  start_year: number
  end_year: number
  start_month?: number
  end_month?: number
  description?: string
  years?: number
}

export interface UserProfile {
  id: string
  name: string
  email: string
  phone: string
  linkedin: string
  github: string
  skills: string[]
  job_titles: string[]
  experiences: Experience[]
  years_experience: number
  seniority_level: string
  education: Education[]
  preferences_raw: string
  target_role: string
  target_location: string
  salary_expectation_min?: number
  resume_version: number
  updated_at?: string
  created_at: string
}

export interface UploadCVResponse {
  user_profile_id: string
  profile: UserProfile
  resume_version: number
  replaced_previous_resume: boolean
  message: string
}

export interface ScoreBreakdown {
  semantic: number
  skills: number
  seniority: number
  location: number
  experience: number
}

export interface JobMatch {
  match_result_id: string
  job_id: string
  title: string
  company: string
  location: string
  job_url: string
  job_source: string
  fit_score: number
  personalized_fit_score: number
  adaptive_boost: number
  confidence: number
  match_label: string
  eligible_for_generation: boolean
  matched_skills: string[]
  missing_skills: string[]
  score_breakdown: ScoreBreakdown
  fit_explanation: string
}

export interface MatchJobsResponse {
  matches: JobMatch[]
  total_matches: number
  eligible_count: number
  average_score: number
  highest_score: number
  threshold: number
  source: 'fresh' | 'stored' | string
}

export interface MatchDetailResponse {
  match: JobMatch
  job_description: string
  source: string
  posted_at?: string
}

export interface GapReport {
  missing_skills: string[]
  weak_areas: string[]
  matched_skills: string[]
  summary: string
  recommended_courses: string[]
  experience_gap?: string
}

export interface KeywordReason {
  keyword: string
  reason: string
}

export interface CVDeltaItem {
  type: string
  before: string
  after: string
  reason: string
}

export interface GenerateOutputsResponse {
  match_result_id: string
  gap_report: GapReport
  rewritten_cv: string
  cover_letter: string
  ats_score_before: number
  ats_score_after: number
  fit_explanation: string
  keywords_added: string[]
  keyword_justifications: KeywordReason[]
  cv_diff: CVDeltaItem[]
  generated_at: string
  cached: boolean
  optimized_resume_download_url: string
  cover_letter_download_url: string
}

export interface HealthResponse {
  status: string
  timestamp: string
  database: boolean
  jobs_count: number
  threshold: number
  gemini_configured: boolean
}

export interface AuthResponse {
  user_id: string
  email: string
  full_name: string
  access_token: string
  refresh_token: string
  token_type: string
}

export interface CurrentUserResponse {
  id: string
  email: string
  full_name: string
  created_at: string
  onboarding_completed: boolean
}

export interface OnboardingPayload {
  profile_id?: string
  target_roles: string[]
  preferred_locations: string[]
  salary_expectation_min?: number
  salary_expectation_max?: number
  work_types: string[]
  career_goals: string
  preferences_raw: string
  skill_confidence?: Record<string, number>
}

export interface OnboardingResponse extends OnboardingPayload {
  user_id: string
  onboarding_completed: boolean
  updated_at: string
}

export type SignalType =
  | 'job_clicked'
  | 'job_ignored'
  | 'generation_requested'
  | 'cv_edited'
  | 'preferences_updated'

export interface SignalPayload {
  profile_id?: string
  job_id?: string
  signal_type: SignalType
  payload?: Record<string, unknown>
}

export interface SignalResponse {
  signal_id: string
  recorded_at: string
}

export interface ApplicationPayload {
  profile_id?: string
  job_id: string
  match_result_id?: string
  generated_output_id?: string
  status?: string
  notes?: string
  deadline_at?: string
  next_action?: string
}

export interface ApplicationUpdatePayload {
  status?: string
  notes?: string
  deadline_at?: string
  next_action?: string
}

export interface ApplicationResponse {
  id: string
  user_id: string
  profile_id?: string
  job_id: string
  match_result_id?: string
  generated_output_id?: string
  status: string
  notes: string
  deadline_at?: string
  next_action: string
  last_agent_summary: string
  deadline_status: string
  urgency: string
  job_title: string
  company: string
  location: string
  match_label: string
  fit_explanation: string
  generated_at?: string
  created_at: string
  updated_at: string
}

export interface ResumeSummary {
  resume_id: string
  profile_id: string
  version: number
  original_filename: string
  uploaded_at: string
  file_size_bytes?: number
  mime_type?: string
}

export interface ProfileOverviewResponse {
  profile: UserProfile
  active_resume?: ResumeSummary
  matched_jobs_count: number
  generated_cover_letters_count: number
}

export interface ProfileUpdatePayload {
  full_name?: string
  email?: string
  phone?: string
  preferred_role?: string
  preferred_location?: string
  preferences_raw?: string
}

export interface ApplicationDetailResponse {
  application: ApplicationResponse
  match?: JobMatch
  job_description: string
  gap_report?: GapReport
  cover_letter: string
  optimized_resume: string
  optimized_resume_download_url: string
  cover_letter_download_url: string
  timeline: Record<string, unknown>
}

export interface ApplicationTrackerInsight {
  application_id: string
  status: string
  deadline_status: string
  days_until_deadline?: number
  urgency: string
  next_action: string
  summary: string
}

export interface ApplicationTrackerResponse {
  headline: string
  active_count: number
  overdue_count: number
  due_soon_count: number
  status_counts: Record<string, number>
  next_focus: ApplicationTrackerInsight[]
  generated_at: string
}

export interface ScraperTriggerPayload {
  async_mode: boolean
  retries: number
  target_count?: number
}

export interface ApiEnvelope<T = Record<string, unknown>> {
  success: boolean
  status: string
  message: string
  data: T
  error?: Record<string, unknown>
}
