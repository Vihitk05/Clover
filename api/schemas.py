from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class EducationSchema(BaseModel):
    degree: str
    university: str
    year: Optional[int] = None
    raw_text: Optional[str] = None


class ExperienceSchema(BaseModel):
    role: str
    company: str
    start_year: int
    end_year: int
    start_month: Optional[int] = None
    end_month: Optional[int] = None
    description: Optional[str] = None
    years: Optional[float] = None


class UserProfileResponse(BaseModel):
    id: str
    name: str = ""
    email: str = ""
    phone: str = ""
    linkedin: str = ""
    github: str = ""
    skills: List[str] = Field(default_factory=list)
    job_titles: List[str] = Field(default_factory=list)
    experiences: List[ExperienceSchema] = Field(default_factory=list)
    years_experience: float = 0.0
    seniority_level: str = "Mid"
    education: List[EducationSchema] = Field(default_factory=list)
    preferences_raw: str = ""
    target_role: str = ""
    target_location: str = ""
    salary_expectation_min: Optional[int] = None
    resume_version: int = 1
    updated_at: Optional[datetime] = None
    created_at: datetime


class UploadCVResponse(BaseModel):
    user_profile_id: str
    profile: UserProfileResponse
    resume_version: int = 1
    replaced_previous_resume: bool = False
    message: str = "CV uploaded and parsed successfully"


class MatchResultSchema(BaseModel):
    match_result_id: str
    job_id: str
    title: str
    company: str
    location: str
    job_url: str = ""
    job_source: str = ""
    fit_score: float
    personalized_fit_score: float
    adaptive_boost: float
    confidence: float = 0.0
    match_label: str = "Moderate Match"
    eligible_for_generation: bool
    matched_skills: List[str] = Field(default_factory=list)
    missing_skills: List[str] = Field(default_factory=list)
    score_breakdown: Dict[str, float] = Field(default_factory=dict)
    fit_explanation: str = ""


class MatchJobsResponse(BaseModel):
    matches: List[MatchResultSchema]
    total_matches: int
    eligible_count: int
    average_score: float
    highest_score: float
    threshold: float
    source: str = "fresh"


class GapReportSchema(BaseModel):
    missing_skills: List[str] = Field(default_factory=list)
    weak_areas: List[str] = Field(default_factory=list)
    matched_skills: List[str] = Field(default_factory=list)
    summary: str = ""
    recommended_courses: List[str] = Field(default_factory=list)
    experience_gap: Optional[str] = None


class CVDeltaItem(BaseModel):
    type: str
    before: str = ""
    after: str = ""
    reason: str = ""


class KeywordReason(BaseModel):
    keyword: str
    reason: str


class GenerateOutputsResponse(BaseModel):
    match_result_id: str
    gap_report: GapReportSchema
    rewritten_cv: str
    cover_letter: str
    ats_score_before: int
    ats_score_after: int
    fit_explanation: str = ""
    keywords_added: List[str] = Field(default_factory=list)
    keyword_justifications: List[KeywordReason] = Field(default_factory=list)
    cv_diff: List[CVDeltaItem] = Field(default_factory=list)
    generated_at: datetime
    cached: bool = False
    optimized_resume_download_url: str = ""
    cover_letter_download_url: str = ""


class HealthResponse(BaseModel):
    status: str
    timestamp: datetime
    database: bool
    jobs_count: int
    threshold: float
    gemini_configured: bool


class SignupRequest(BaseModel):
    email: str
    password: str
    full_name: str


class LoginRequest(BaseModel):
    email: str
    password: str


class OAuthLoginRequest(BaseModel):
    provider: Literal["google", "linkedin"]
    email: str
    full_name: str
    oauth_subject: str


class RefreshRequest(BaseModel):
    refresh_token: str


class AuthResponse(BaseModel):
    user_id: str
    email: str
    full_name: str
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserSessionResponse(BaseModel):
    id: str
    user_id: str
    created_at: datetime
    expires_at: datetime
    revoked_at: Optional[datetime] = None


class CurrentUserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    created_at: datetime
    onboarding_completed: bool = False


class OnboardingRequest(BaseModel):
    profile_id: Optional[str] = None
    target_roles: List[str] = Field(default_factory=list)
    preferred_locations: List[str] = Field(default_factory=list)
    salary_expectation_min: Optional[int] = None
    salary_expectation_max: Optional[int] = None
    work_types: List[str] = Field(default_factory=list)
    career_goals: str = ""
    skill_confidence: Dict[str, int] = Field(default_factory=dict)
    preferences_raw: str = ""


class OnboardingResponse(BaseModel):
    user_id: str
    profile_id: Optional[str] = None
    target_roles: List[str] = Field(default_factory=list)
    preferred_locations: List[str] = Field(default_factory=list)
    salary_expectation_min: Optional[int] = None
    salary_expectation_max: Optional[int] = None
    work_types: List[str] = Field(default_factory=list)
    career_goals: str = ""
    skill_confidence: Dict[str, int] = Field(default_factory=dict)
    onboarding_completed: bool = False
    updated_at: datetime


SignalType = Literal[
    "job_clicked",
    "job_ignored",
    "generation_requested",
    "cv_edited",
    "preferences_updated",
]


class SignalRequest(BaseModel):
    profile_id: Optional[str] = None
    job_id: Optional[str] = None
    signal_type: SignalType
    payload: Dict[str, Any] = Field(default_factory=dict)


class SignalResponse(BaseModel):
    signal_id: str
    recorded_at: datetime


class ApplicationCreateRequest(BaseModel):
    profile_id: Optional[str] = None
    job_id: str
    match_result_id: Optional[str] = None
    generated_output_id: Optional[str] = None
    status: str = "draft"
    notes: str = ""
    deadline_at: Optional[datetime] = None
    next_action: str = ""


class ApplicationUpdateRequest(BaseModel):
    status: Optional[str] = None
    notes: Optional[str] = None
    deadline_at: Optional[datetime] = None
    next_action: Optional[str] = None


class ApplicationResponse(BaseModel):
    id: str
    user_id: str
    profile_id: Optional[str] = None
    job_id: str
    match_result_id: Optional[str] = None
    generated_output_id: Optional[str] = None
    status: str
    notes: str = ""
    deadline_at: Optional[datetime] = None
    next_action: str = ""
    last_agent_summary: str = ""
    deadline_status: str = "unscheduled"
    urgency: str = "low"
    job_title: str = ""
    company: str = ""
    location: str = ""
    match_label: str = ""
    fit_explanation: str = ""
    generated_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class MatchDetailResponse(BaseModel):
    match: MatchResultSchema
    job_description: str = ""
    source: str = ""
    posted_at: Optional[datetime] = None


class ResumeSummaryResponse(BaseModel):
    resume_id: str
    profile_id: str
    version: int
    original_filename: str
    uploaded_at: datetime
    file_size_bytes: Optional[int] = None
    mime_type: Optional[str] = None


class ProfileOverviewResponse(BaseModel):
    profile: UserProfileResponse
    active_resume: Optional[ResumeSummaryResponse] = None
    matched_jobs_count: int = 0
    generated_cover_letters_count: int = 0


class ProfileUpdateRequest(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    preferred_role: Optional[str] = None
    preferred_location: Optional[str] = None
    preferences_raw: Optional[str] = None


class ApplicationDetailResponse(BaseModel):
    application: ApplicationResponse
    match: Optional[MatchResultSchema] = None
    job_description: str = ""
    gap_report: Optional[GapReportSchema] = None
    cover_letter: str = ""
    optimized_resume: str = ""
    optimized_resume_download_url: str = ""
    cover_letter_download_url: str = ""
    timeline: Dict[str, Any] = Field(default_factory=dict)


class ApplicationTrackerResponse(BaseModel):
    headline: str
    active_count: int
    overdue_count: int
    due_soon_count: int
    status_counts: Dict[str, int] = Field(default_factory=dict)
    next_focus: List[Dict[str, Any]] = Field(default_factory=list)
    generated_at: datetime


class ScraperTriggerRequest(BaseModel):
    async_mode: bool = True
    retries: int = Field(default=2, ge=0, le=5)
    target_count: Optional[int] = Field(default=None, ge=10, le=3000)


class ScraperTaskResponse(BaseModel):
    task_id: str
    provider: str
    status: str
    accepted_at: datetime
    message: str


class ApiEnvelope(BaseModel):
    success: bool = True
    status: str
    message: str
    data: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[Dict[str, Any]] = None
