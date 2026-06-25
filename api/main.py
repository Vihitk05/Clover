import logging
import os
import re
import shutil
import uuid
from datetime import datetime
from typing import Dict, Generator, List, Optional, Tuple

import jwt
from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import desc
from sqlalchemy.orm import Session

from agents.gemini_client import GeminiClient
from agents.application_tracking_agent import ApplicationTrackingAgent
from agents.pipeline import AgentPipeline
from api.document_service import create_generation_assets
from api.schemas import (
    ApplicationDetailResponse,
    ApiEnvelope,
    ApplicationCreateRequest,
    ApplicationResponse,
    ApplicationTrackerResponse,
    ApplicationUpdateRequest,
    AuthResponse,
    CurrentUserResponse,
    EducationSchema,
    ExperienceSchema,
    GapReportSchema,
    GenerateOutputsResponse,
    HealthResponse,
    KeywordReason,
    LoginRequest,
    MatchDetailResponse,
    MatchJobsResponse,
    MatchResultSchema,
    OAuthLoginRequest,
    OnboardingRequest,
    OnboardingResponse,
    ProfileOverviewResponse,
    ProfileUpdateRequest,
    RefreshRequest,
    ResumeSummaryResponse,
    ScraperTaskResponse,
    ScraperTriggerRequest,
    SignalRequest,
    SignalResponse,
    SignupRequest,
    UploadCVResponse,
    UserProfileResponse,
)
from api.scraper_service import ScraperTaskManager, is_rate_limited, source_label
from api.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    hash_token,
    verify_password,
)
from config.settings import config
from database.connections import db_manager
from nlp.cv_parser import parse_cv
from nlp.embedder import ProfileEmbedder
from nlp.match_engine import MatchEngine
from scraper.models import (
    AppUser,
    GeneratedOutput,
    Job,
    MatchResult,
    OnboardingPreference,
    RefreshSession,
    ResumeDocument,
    ScraperRun,
    UserApplication,
    UserProfile,
    UserSignal,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Clover API",
    description="Adaptive and scrutable AI job application assistant",
    version="3.0.0",
    docs_url=None,
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer(auto_error=False)

match_engine: Optional[MatchEngine] = None
profile_embedder: Optional[ProfileEmbedder] = None
agent_pipeline: Optional[AgentPipeline] = None
gemini_client: Optional[GeminiClient] = None
scraper_tasks = ScraperTaskManager()
application_tracker = ApplicationTrackingAgent()

APPLICATION_STATUSES = {
    "draft",
    "saved",
    "generated",
    "applied",
    "interviewing",
    "offer",
    "rejected",
    "withdrawn",
}


def get_db() -> Generator:
    session = db_manager.get_session()
    try:
        yield session
    finally:
        session.close()


def get_match_engine() -> MatchEngine:
    global match_engine
    if match_engine is None:
        match_engine = MatchEngine(
            threshold=config.GENERATION_THRESHOLD,
            persist_directory=config.CHROMA_DB_PATH,
            use_mock=False,
        )
    return match_engine


def get_profile_embedder() -> ProfileEmbedder:
    global profile_embedder
    if profile_embedder is None:
        profile_embedder = ProfileEmbedder(persist_directory=config.CHROMA_DB_PATH)
    return profile_embedder


def get_agent_pipeline() -> AgentPipeline:
    global agent_pipeline
    if agent_pipeline is None:
        agent_pipeline = AgentPipeline()
    return agent_pipeline


def get_gemini() -> GeminiClient:
    global gemini_client
    if gemini_client is None:
        gemini_client = GeminiClient()
    return gemini_client


def _decode_user_from_token(token: str, session: Session) -> AppUser:
    try:
        payload = decode_token(token)
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    if payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Invalid token type")
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Token subject missing")
    user = session.query(AppUser).filter_by(id=user_id, is_active=True).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: Session = Depends(get_db),
) -> AppUser:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    return _decode_user_from_token(credentials.credentials, session=session)


def get_optional_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: Session = Depends(get_db),
) -> Optional[AppUser]:
    if credentials is None:
        return None
    try:
        return _decode_user_from_token(credentials.credentials, session=session)
    except HTTPException:
        return None


def _issue_tokens_for_user(
    user: AppUser,
    session: Session,
    user_agent: Optional[str] = None,
    ip_address: Optional[str] = None,
) -> AuthResponse:
    access_token = create_access_token(subject=user.id, extra={"email": user.email})
    refresh_token, token_hash, expires_at = create_refresh_token(
        subject=user.id, extra={"email": user.email}
    )
    refresh_session = RefreshSession(
        user_id=user.id,
        refresh_token_hash=token_hash,
        user_agent=user_agent,
        ip_address=ip_address,
        expires_at=expires_at.replace(tzinfo=None),
    )
    user.last_login_at = datetime.utcnow()
    session.add(refresh_session)
    session.add(user)
    session.commit()
    return AuthResponse(
        user_id=user.id,
        email=user.email,
        full_name=user.full_name or "",
        access_token=access_token,
        refresh_token=refresh_token,
    )


def _safe_file_name(filename: str) -> str:
    name = os.path.basename(filename)
    return re.sub(r"[^a-zA-Z0-9._-]", "_", name)


def _asset_download_url(match_result_id: str, asset_type: str) -> str:
    return f"/api/generated-assets/{match_result_id}/{asset_type}"


def _serialize_experiences(cv_data: Dict) -> List[ExperienceSchema]:
    return [
        ExperienceSchema(
            role=exp.get("role", ""),
            company=exp.get("company", ""),
            start_year=exp.get("start_year", 0),
            end_year=exp.get("end_year", 0),
            start_month=exp.get("start_month"),
            end_month=exp.get("end_month"),
            description=exp.get("description"),
            years=exp.get("years"),
        )
        for exp in cv_data.get("experiences", [])
    ]


def _serialize_education(cv_data: Dict) -> List[EducationSchema]:
    return [
        EducationSchema(
            degree=edu.get("degree", ""),
            university=edu.get("university", ""),
            year=edu.get("year"),
            raw_text=edu.get("raw_text"),
        )
        for edu in cv_data.get("education", [])
    ]


def profile_to_response(profile: UserProfile, cv_data: Optional[Dict] = None) -> UserProfileResponse:
    resume_payload = cv_data or profile.parsed_resume_data or {}
    return UserProfileResponse(
        id=profile.id,
        name=profile.name or "",
        email=profile.email or "",
        phone=profile.phone or resume_payload.get("phone", ""),
        linkedin=resume_payload.get("linkedin", ""),
        github=resume_payload.get("github", ""),
        skills=profile.skills or [],
        job_titles=profile.job_titles or [],
        experiences=_serialize_experiences(resume_payload),
        years_experience=profile.years_experience or 0,
        seniority_level=profile.seniority_level or "Mid",
        education=_serialize_education(resume_payload),
        preferences_raw=profile.preferences_raw or "",
        target_role=profile.target_role or "",
        target_location=profile.target_location or "",
        salary_expectation_min=profile.salary_expectation_min,
        resume_version=profile.resume_version or 1,
        created_at=profile.created_at,
        updated_at=profile.updated_at,
    )


def _onboarding_to_schema(record: Optional[OnboardingPreference], user_id: str) -> OnboardingResponse:
    if record is None:
        return OnboardingResponse(user_id=user_id, updated_at=datetime.utcnow())
    return OnboardingResponse(
        user_id=user_id,
        profile_id=record.profile_id,
        target_roles=record.target_roles or [],
        preferred_locations=record.preferred_locations or [],
        salary_expectation_min=record.salary_expectation_min,
        salary_expectation_max=record.salary_expectation_max,
        work_types=record.work_types or [],
        career_goals=record.career_goals or "",
        skill_confidence=record.skill_confidence or {},
        onboarding_completed=record.onboarding_completed,
        updated_at=record.updated_at,
    )


def _upsert_onboarding(
    session: Session, user_id: str, payload: OnboardingRequest
) -> OnboardingPreference:
    record = session.query(OnboardingPreference).filter_by(user_id=user_id).first()
    if record is None:
        record = OnboardingPreference(user_id=user_id, created_at=datetime.utcnow())
        session.add(record)
    record.profile_id = payload.profile_id
    record.target_roles = payload.target_roles
    record.preferred_locations = payload.preferred_locations
    record.salary_expectation_min = payload.salary_expectation_min
    record.salary_expectation_max = payload.salary_expectation_max
    record.work_types = payload.work_types
    record.career_goals = payload.career_goals
    record.skill_confidence = payload.skill_confidence or {}
    record.onboarding_completed = True
    record.updated_at = datetime.utcnow()
    session.add(record)
    session.commit()
    session.refresh(record)
    return record


def _get_user_profile(session: Session, user_id: str) -> Optional[UserProfile]:
    onboarding = session.query(OnboardingPreference).filter_by(user_id=user_id).first()
    if onboarding and onboarding.profile_id:
        profile = session.query(UserProfile).filter_by(id=onboarding.profile_id).first()
        if profile:
            if not profile.user_id:
                profile.user_id = user_id
                session.add(profile)
                session.commit()
            return profile
    profile = (
        session.query(UserProfile)
        .filter_by(user_id=user_id)
        .order_by(desc(UserProfile.updated_at), desc(UserProfile.created_at))
        .first()
    )
    return profile


def _resume_to_schema(resume: ResumeDocument) -> ResumeSummaryResponse:
    return ResumeSummaryResponse(
        resume_id=resume.id,
        profile_id=resume.profile_id,
        version=resume.version,
        original_filename=resume.original_filename,
        uploaded_at=resume.uploaded_at,
        file_size_bytes=resume.file_size_bytes,
        mime_type=resume.mime_type,
    )


def _set_resume_active(session: Session, profile_id: str, active_version: int):
    resumes = session.query(ResumeDocument).filter_by(profile_id=profile_id).all()
    for row in resumes:
        row.is_active = row.version == active_version
        session.add(row)


def _clear_stale_profile_data(session: Session, profile_id: str):
    stale_matches = session.query(MatchResult).filter_by(user_profile_id=profile_id).all()
    match_ids = [row.id for row in stale_matches]
    if match_ids:
        session.query(GeneratedOutput).filter(
            GeneratedOutput.match_result_id.in_(match_ids)
        ).delete(synchronize_session=False)
    session.query(GeneratedOutput).filter_by(profile_id=profile_id).delete(
        synchronize_session=False
    )
    session.query(MatchResult).filter_by(user_profile_id=profile_id).delete(
        synchronize_session=False
    )
    session.query(UserApplication).filter_by(profile_id=profile_id).delete(
        synchronize_session=False
    )


def _validate_profile_access(profile: UserProfile, current_user: Optional[AppUser]):
    if current_user and profile.user_id and profile.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this profile")


def _normalize_application_status(status: Optional[str]) -> str:
    normalized = (status or "saved").strip().lower()
    if normalized not in APPLICATION_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid application status. Expected one of: {', '.join(sorted(APPLICATION_STATUSES))}",
        )
    return normalized


def _application_to_response(
    app_row: UserApplication,
    job: Optional[Job] = None,
    match: Optional[MatchResult] = None,
    generated: Optional[GeneratedOutput] = None,
) -> ApplicationResponse:
    insight = application_tracker.inspect_application(app_row, job)
    return ApplicationResponse(
        id=app_row.id,
        user_id=app_row.user_id,
        profile_id=app_row.profile_id,
        job_id=app_row.job_id,
        match_result_id=app_row.match_result_id,
        generated_output_id=app_row.generated_output_id,
        status=app_row.status,
        notes=app_row.notes or "",
        deadline_at=app_row.deadline_at,
        next_action=app_row.next_action or insight["next_action"],
        last_agent_summary=app_row.last_agent_summary or insight["summary"],
        deadline_status=insight["deadline_status"],
        urgency=insight["urgency"],
        job_title=job.title if job else "",
        company=job.company if job else "",
        location=job.location if job else "",
        match_label=match.match_label if match else "",
        fit_explanation=match.fit_explanation if match else "",
        generated_at=generated.generated_at if generated else None,
        created_at=app_row.created_at,
        updated_at=app_row.updated_at,
    )


def _build_profile_dict(profile: UserProfile) -> Dict:
    parsed = profile.parsed_resume_data or {}
    return {
        "id": profile.id,
        "name": profile.name or "",
        "email": profile.email or "",
        "phone": profile.phone or parsed.get("phone", ""),
        "skills": profile.skills or [],
        "job_titles": profile.job_titles or [],
        "education": profile.education or parsed.get("education", []),
        "experiences": parsed.get("experiences", []),
        "years_experience": profile.years_experience or 0,
        "seniority_level": profile.seniority_level or "Mid",
        "internship_years": parsed.get("internship_years", 0),
        "fulltime_years": parsed.get("fulltime_years", 0),
        "internship_only": parsed.get("internship_only", False),
        "leadership_experience": parsed.get("leadership_experience", False),
        "tech_stack_maturity": parsed.get("tech_stack_maturity", "foundational"),
        "project_complexity": parsed.get("project_complexity", "basic"),
        "target_role": profile.target_role or "",
        "target_location": profile.target_location or "",
        "preferences_raw": profile.preferences_raw or "",
    }


def _signal_preferences(session: Session, user_id: str) -> Dict:
    signals = (
        session.query(UserSignal)
        .filter_by(user_id=user_id)
        .order_by(desc(UserSignal.created_at))
        .limit(300)
        .all()
    )
    skill_weights: Dict[str, float] = {}
    role_weights: Dict[str, float] = {}
    location_weights: Dict[str, float] = {}

    signal_weight_map = {
        "job_clicked": 1.0,
        "job_ignored": -0.7,
        "generation_requested": 2.0,
        "cv_edited": 1.4,
        "preferences_updated": 1.5,
    }

    for signal in signals:
        weight = signal_weight_map.get(signal.signal_type, 0.5)
        payload = signal.signal_payload or {}
        for skill in payload.get("skills", []):
            key = skill.strip().lower()
            if key:
                skill_weights[key] = skill_weights.get(key, 0.0) + weight
        for role in payload.get("target_roles", []):
            key = role.strip().lower()
            if key:
                role_weights[key] = role_weights.get(key, 0.0) + weight
        for loc in payload.get("locations", []) + payload.get("preferred_locations", []):
            key = loc.strip().lower()
            if key:
                location_weights[key] = location_weights.get(key, 0.0) + weight

    return {
        "skills": skill_weights,
        "roles": role_weights,
        "locations": location_weights,
    }


def _label_from_score(score: float) -> str:
    if score >= 85:
        return "Excellent Match"
    if score >= 72:
        return "Strong Match"
    if score >= 58:
        return "Good Match"
    return "Moderate Match"


def _build_fit_explanation(match: Dict, adaptive_boost: float) -> str:
    matched = ", ".join(match.get("matched_skills", [])[:2])
    missing = match.get("missing_skills", [])
    if matched:
        if missing:
            return f"Recommended because your experience in {matched} aligns well. Building {missing[0]} could improve fit further."
        return f"Recommended because your experience in {matched} aligns well with this role."
    if missing:
        return f"This role has partial overlap today. Strengthening {missing[0]} could improve your match."
    return "This role has a moderate overlap with your profile and goals."


def _apply_personalization(
    match: Dict,
    signal_preferences: Dict,
    onboarding: Optional[OnboardingPreference],
) -> Dict:
    boost = 0.0
    title = match.get("title", "").lower()
    location = match.get("location", "").lower()
    matched_skills = [s.lower() for s in match.get("matched_skills", [])]
    missing_skills = [s.lower() for s in match.get("missing_skills", [])]
    all_skills = set(matched_skills + missing_skills)

    for skill in all_skills:
        boost += max(0.0, signal_preferences["skills"].get(skill, 0.0)) * 0.45

    for role, score in signal_preferences["roles"].items():
        if role and role in title and score > 0:
            boost += min(3.0, score * 0.35)

    if onboarding:
        for role in onboarding.target_roles or []:
            role_l = role.lower()
            if role_l and role_l in title:
                boost += 1.75
        preferred_locations = [loc.lower() for loc in onboarding.preferred_locations or []]
        if preferred_locations:
            if any(loc in location for loc in preferred_locations):
                boost += 1.25
            elif "remote" not in location:
                boost -= 0.75

    boost = max(-3.0, min(6.0, boost))
    personalized = max(0.0, min(100.0, float(match["fit_score"]) + boost))
    match["adaptive_boost"] = round(boost, 2)
    match["personalized_fit_score"] = round(personalized, 2)
    match["match_label"] = _label_from_score(personalized)
    match["fit_explanation"] = _build_fit_explanation(match, adaptive_boost=boost)
    match["eligible_for_generation"] = personalized >= config.GENERATION_THRESHOLD
    return match


def _match_rows_to_response(
    rows: List[Tuple[MatchResult, Optional[Job]]],
) -> List[MatchResultSchema]:
    payload = []
    for row, job in rows:
        payload.append(
            MatchResultSchema(
                match_result_id=row.id,
                job_id=row.job_id,
                title=job.title if job else "",
                company=job.company if job else "",
                location=job.location if job else "",
                job_url=job.url if job else "",
                job_source=job.source if job else "",
                fit_score=float(row.fit_score or 0),
                personalized_fit_score=float(row.personalized_fit_score or row.fit_score or 0),
                adaptive_boost=float(row.adaptive_boost or 0),
                confidence=float(row.confidence or 0),
                match_label=row.match_label or _label_from_score(float(row.personalized_fit_score or row.fit_score or 0)),
                eligible_for_generation=bool(row.eligible_for_generation),
                matched_skills=row.matched_skills or [],
                missing_skills=row.missing_skills or [],
                score_breakdown=row.score_breakdown or {},
                fit_explanation=row.fit_explanation or "",
            )
        )
    return payload


def _load_stored_matches(
    session: Session,
    profile: UserProfile,
    top_n: int,
    min_score: float,
) -> List[MatchResultSchema]:
    query_rows = (
        session.query(MatchResult, Job)
        .outerjoin(Job, Job.id == MatchResult.job_id)
        .filter(
            MatchResult.user_profile_id == profile.id,
            MatchResult.resume_version == (profile.resume_version or 1),
            MatchResult.personalized_fit_score >= min_score,
        )
        .order_by(desc(MatchResult.personalized_fit_score), desc(MatchResult.created_at))
        .limit(top_n)
        .all()
    )
    return _match_rows_to_response(query_rows)


def _run_matching(
    session: Session,
    profile: UserProfile,
    current_user: Optional[AppUser],
    top_n: int,
    min_score: float,
) -> MatchJobsResponse:
    embedder = get_profile_embedder()
    engine = get_match_engine()

    profile_dict = _build_profile_dict(profile)
    profile_embedding = embedder.get_profile_embedding(profile.id)
    if not profile_embedding:
        profile_embedding = embedder.embed_profile(profile_dict)

    matches = engine.match_jobs(
        profile=profile_dict,
        profile_embedding=profile_embedding,
        top_n=top_n,
        min_score=min_score,
    )

    job_ids = [str(match.get("job_id", "")) for match in matches if match.get("job_id")]
    job_meta = {}
    if job_ids:
        rows = session.query(Job.id, Job.url, Job.source).filter(Job.id.in_(job_ids)).all()
        job_meta = {
            row.id: {
                "job_url": row.url or "",
                "job_source": row.source or "",
            }
            for row in rows
        }

    signal_preferences = {"skills": {}, "roles": {}, "locations": {}}
    onboarding = None
    if current_user:
        signal_preferences = _signal_preferences(session, user_id=current_user.id)
        onboarding = session.query(OnboardingPreference).filter_by(user_id=current_user.id).first()

    enriched_matches: List[Dict] = []
    resume_version = profile.resume_version or 1
    for match in matches:
        source_meta = job_meta.get(str(match.get("job_id", "")), {})
        match["job_url"] = source_meta.get("job_url", "")
        match["job_source"] = source_meta.get("job_source", "")
        enriched = _apply_personalization(
            match=match,
            signal_preferences=signal_preferences,
            onboarding=onboarding,
        )
        enriched_matches.append(enriched)
        existing = (
            session.query(MatchResult)
            .filter_by(
                user_profile_id=profile.id,
                job_id=enriched["job_id"],
                resume_version=resume_version,
            )
            .first()
        )
        if not existing:
            existing = MatchResult(
                id=str(uuid.uuid4()),
                user_profile_id=profile.id,
                resume_version=resume_version,
                job_id=enriched["job_id"],
                created_at=datetime.utcnow(),
            )
        existing.fit_score = float(enriched.get("fit_score", 0.0))
        existing.personalized_fit_score = float(enriched.get("personalized_fit_score", 0.0))
        existing.adaptive_boost = float(enriched.get("adaptive_boost", 0.0))
        existing.confidence = float(enriched.get("confidence", 0.0))
        existing.match_label = enriched.get("match_label", _label_from_score(float(enriched.get("personalized_fit_score", 0.0))))
        existing.eligible_for_generation = bool(enriched.get("eligible_for_generation", False))
        existing.missing_skills = enriched["missing_skills"]
        existing.matched_skills = enriched["matched_skills"]
        existing.score_breakdown = {
            key: float(value)
            for key, value in (enriched.get("score_breakdown") or {}).items()
        }
        existing.fit_explanation = enriched["fit_explanation"]
        enriched["match_result_id"] = existing.id
        session.add(existing)

    session.commit()

    typed_matches = [MatchResultSchema(**m) for m in enriched_matches]
    scores = [m.personalized_fit_score for m in typed_matches]
    eligible_count = sum(1 for m in typed_matches if m.eligible_for_generation)

    return MatchJobsResponse(
        matches=typed_matches,
        total_matches=len(typed_matches),
        eligible_count=eligible_count,
        average_score=round(sum(scores) / len(scores), 1) if scores else 0.0,
        highest_score=max(scores) if scores else 0.0,
        threshold=engine.get_threshold(),
        source="fresh",
    )


def _build_match_jobs_response_from_rows(
    rows: List[MatchResultSchema],
) -> MatchJobsResponse:
    scores = [m.personalized_fit_score for m in rows]
    eligible_count = sum(1 for m in rows if m.eligible_for_generation)
    return MatchJobsResponse(
        matches=rows,
        total_matches=len(rows),
        eligible_count=eligible_count,
        average_score=round(sum(scores) / len(scores), 1) if scores else 0.0,
        highest_score=max(scores) if scores else 0.0,
        threshold=get_match_engine().get_threshold(),
        source="stored",
    )


@app.get("/api/health", response_model=HealthResponse)
async def health_check():
    session = db_manager.get_session()
    try:
        jobs_count = session.query(Job).count()
        db_healthy = True
    except Exception as exc:
        logger.error(f"Health check error: {exc}")
        db_healthy = False
        jobs_count = 0
    finally:
        session.close()
    return HealthResponse(
        status="healthy" if db_healthy else "degraded",
        timestamp=datetime.utcnow(),
        database=db_healthy,
        jobs_count=jobs_count,
        threshold=get_match_engine().get_threshold(),
        gemini_configured=get_gemini().enabled,
    )


@app.post("/api/auth/signup", response_model=AuthResponse)
async def signup(
    request: SignupRequest,
    user_agent: Optional[str] = Header(default=None),
    session: Session = Depends(get_db),
):
    existing = session.query(AppUser).filter_by(email=request.email.lower().strip()).first()
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")
    user = AppUser(
        email=request.email.lower().strip(),
        full_name=request.full_name.strip(),
        password_hash=hash_password(request.password),
        created_at=datetime.utcnow(),
        is_active=True,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return _issue_tokens_for_user(user=user, session=session, user_agent=user_agent)


@app.post("/api/auth/login", response_model=AuthResponse)
async def login(
    request: LoginRequest,
    user_agent: Optional[str] = Header(default=None),
    session: Session = Depends(get_db),
):
    user = session.query(AppUser).filter_by(email=request.email.lower().strip()).first()
    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="User account is inactive")
    return _issue_tokens_for_user(user=user, session=session, user_agent=user_agent)


@app.post("/api/auth/oauth", response_model=AuthResponse)
async def oauth_login(
    request: OAuthLoginRequest,
    user_agent: Optional[str] = Header(default=None),
    session: Session = Depends(get_db),
):
    email = request.email.lower().strip()
    user = session.query(AppUser).filter_by(email=email).first()
    if user is None:
        user = AppUser(
            email=email,
            full_name=request.full_name.strip(),
            password_hash=hash_password(uuid.uuid4().hex),
            oauth_provider=request.provider,
            oauth_subject=request.oauth_subject,
            created_at=datetime.utcnow(),
            is_active=True,
        )
        session.add(user)
        session.commit()
        session.refresh(user)
    else:
        user.oauth_provider = request.provider
        user.oauth_subject = request.oauth_subject
        session.add(user)
        session.commit()

    return _issue_tokens_for_user(user=user, session=session, user_agent=user_agent)


@app.post("/api/auth/refresh", response_model=AuthResponse)
async def refresh_token(
    request: RefreshRequest,
    user_agent: Optional[str] = Header(default=None),
    session: Session = Depends(get_db),
):
    try:
        payload = decode_token(request.refresh_token)
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token type")
    session_hash = hash_token(request.refresh_token)
    active_session = session.query(RefreshSession).filter_by(refresh_token_hash=session_hash).first()
    if (
        active_session is None
        or active_session.revoked_at is not None
        or active_session.expires_at < datetime.utcnow()
    ):
        raise HTTPException(status_code=401, detail="Refresh session expired or revoked")
    user = session.query(AppUser).filter_by(id=payload.get("sub"), is_active=True).first()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    active_session.revoked_at = datetime.utcnow()
    session.add(active_session)
    session.commit()
    return _issue_tokens_for_user(user=user, session=session, user_agent=user_agent)


@app.post("/api/auth/logout")
async def logout(request: RefreshRequest, session: Session = Depends(get_db)):
    token_hash = hash_token(request.refresh_token)
    row = session.query(RefreshSession).filter_by(refresh_token_hash=token_hash).first()
    if row and row.revoked_at is None:
        row.revoked_at = datetime.utcnow()
        session.add(row)
        session.commit()
    return {"status": "ok"}


@app.get("/api/auth/me", response_model=CurrentUserResponse)
async def me(current_user: AppUser = Depends(get_current_user), session: Session = Depends(get_db)):
    onboarding = session.query(OnboardingPreference).filter_by(user_id=current_user.id).first()
    return CurrentUserResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name or "",
        created_at=current_user.created_at,
        onboarding_completed=bool(onboarding and onboarding.onboarding_completed),
    )


@app.get("/api/onboarding", response_model=OnboardingResponse)
async def get_onboarding(
    current_user: AppUser = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    record = session.query(OnboardingPreference).filter_by(user_id=current_user.id).first()
    return _onboarding_to_schema(record, user_id=current_user.id)


@app.post("/api/onboarding", response_model=OnboardingResponse)
async def update_onboarding(
    request: OnboardingRequest,
    current_user: AppUser = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    record = _upsert_onboarding(session=session, user_id=current_user.id, payload=request)
    return _onboarding_to_schema(record, user_id=current_user.id)


@app.get("/api/profile/me", response_model=ProfileOverviewResponse)
async def get_profile_overview(
    current_user: AppUser = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    profile = _get_user_profile(session, user_id=current_user.id)
    if not profile:
        raise HTTPException(status_code=404, detail="No profile found. Upload a resume to get started.")

    active_resume = (
        session.query(ResumeDocument)
        .filter_by(profile_id=profile.id, is_active=True)
        .order_by(desc(ResumeDocument.uploaded_at))
        .first()
    )
    matched_jobs_count = (
        session.query(MatchResult)
        .filter_by(user_profile_id=profile.id, resume_version=profile.resume_version or 1)
        .count()
    )
    generated_cover_letters_count = (
        session.query(GeneratedOutput)
        .filter_by(profile_id=profile.id, resume_version=profile.resume_version or 1)
        .count()
    )

    return ProfileOverviewResponse(
        profile=profile_to_response(profile),
        active_resume=_resume_to_schema(active_resume) if active_resume else None,
        matched_jobs_count=matched_jobs_count,
        generated_cover_letters_count=generated_cover_letters_count,
    )


@app.patch("/api/profile/me", response_model=ProfileOverviewResponse)
async def update_profile_overview(
    request: ProfileUpdateRequest,
    current_user: AppUser = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    profile = _get_user_profile(session, user_id=current_user.id)
    if not profile:
        raise HTTPException(status_code=404, detail="No profile found")

    if request.full_name is not None:
        current_user.full_name = request.full_name.strip()
        profile.name = request.full_name.strip()
    if request.email is not None:
        email = request.email.strip().lower()
        existing = session.query(AppUser).filter(AppUser.email == email, AppUser.id != current_user.id).first()
        if existing:
            raise HTTPException(status_code=409, detail="Email already in use")
        current_user.email = email
        profile.email = email
    if request.phone is not None:
        profile.phone = request.phone.strip()
    if request.preferred_role is not None:
        profile.target_role = request.preferred_role.strip()
    if request.preferred_location is not None:
        profile.target_location = request.preferred_location.strip()
    if request.preferences_raw is not None:
        profile.preferences_raw = request.preferences_raw

    profile.updated_at = datetime.utcnow()
    session.add(current_user)
    session.add(profile)
    session.commit()
    session.refresh(profile)

    active_resume = (
        session.query(ResumeDocument)
        .filter_by(profile_id=profile.id, is_active=True)
        .order_by(desc(ResumeDocument.uploaded_at))
        .first()
    )
    matched_jobs_count = (
        session.query(MatchResult)
        .filter_by(user_profile_id=profile.id, resume_version=profile.resume_version or 1)
        .count()
    )
    generated_cover_letters_count = (
        session.query(GeneratedOutput)
        .filter_by(profile_id=profile.id, resume_version=profile.resume_version or 1)
        .count()
    )
    return ProfileOverviewResponse(
        profile=profile_to_response(profile),
        active_resume=_resume_to_schema(active_resume) if active_resume else None,
        matched_jobs_count=matched_jobs_count,
        generated_cover_letters_count=generated_cover_letters_count,
    )


@app.get("/api/profile/resume/download")
async def download_active_resume(
    current_user: AppUser = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    profile = _get_user_profile(session, user_id=current_user.id)
    if not profile:
        raise HTTPException(status_code=404, detail="No profile found")
    resume = (
        session.query(ResumeDocument)
        .filter_by(profile_id=profile.id, is_active=True)
        .order_by(desc(ResumeDocument.uploaded_at))
        .first()
    )
    if not resume or not os.path.exists(resume.storage_path):
        raise HTTPException(status_code=404, detail="No active resume file found")
    return FileResponse(
        path=resume.storage_path,
        filename=resume.original_filename,
        media_type=resume.mime_type or "application/octet-stream",
    )


@app.post("/api/upload-cv", response_model=UploadCVResponse)
async def upload_cv(
    cv_file: UploadFile = File(...),
    preferences: str = Form(""),
    current_user: Optional[AppUser] = Depends(get_optional_user),
    session: Session = Depends(get_db),
):
    ext = os.path.splitext(cv_file.filename or "")[1].lower().lstrip(".")
    allowed = [x.strip().lower().lstrip(".") for x in config.ALLOWED_CV_EXTENSIONS]
    if ext not in allowed:
        raise HTTPException(status_code=400, detail="Only PDF and DOCX files are allowed")

    os.makedirs(config.UPLOAD_DIR, exist_ok=True)
    tmp_path = os.path.join(config.UPLOAD_DIR, f"tmp_{uuid.uuid4()}_{_safe_file_name(cv_file.filename or 'resume')}")

    try:
        with open(tmp_path, "wb") as buffer:
            shutil.copyfileobj(cv_file.file, buffer)

        file_size_bytes = os.path.getsize(tmp_path)
        if file_size_bytes > config.MAX_CV_SIZE_MB * 1024 * 1024:
            raise HTTPException(
                status_code=400,
                detail=f"File too large. Maximum allowed size is {config.MAX_CV_SIZE_MB}MB.",
            )

        cv_data = parse_cv(tmp_path, preferences)
        if not cv_data.get("skills"):
            raise HTTPException(status_code=400, detail="Could not extract skills from CV")

        replaced_previous_resume = False
        owner_user_id = current_user.id if current_user else None
        profile = _get_user_profile(session, current_user.id) if current_user else None

        if profile:
            replaced_previous_resume = True
            next_version = (profile.resume_version or 1) + 1
            _clear_stale_profile_data(session, profile.id)
        else:
            next_version = 1
            profile = UserProfile(
                id=str(uuid.uuid4()),
                user_id=owner_user_id,
                created_at=datetime.utcnow(),
            )
            session.add(profile)

        profile.user_id = owner_user_id
        profile.name = cv_data.get("name", "")
        profile.email = cv_data.get("email", "")
        profile.phone = cv_data.get("phone", "")
        profile.skills = cv_data.get("skills", [])
        profile.job_titles = cv_data.get("job_titles", [])
        profile.years_experience = cv_data.get("years_experience", 0)
        profile.seniority_level = cv_data.get("seniority_level", "Mid")
        profile.education = cv_data.get("education", [])
        profile.preferences_raw = preferences
        profile.target_role = cv_data.get("target_role", "")
        profile.target_location = cv_data.get("target_location", "")
        profile.salary_expectation_min = cv_data.get("salary_expectation_min")
        profile.parsed_resume_data = cv_data
        profile.resume_version = next_version
        profile.updated_at = datetime.utcnow()
        session.add(profile)
        session.flush()

        owner_folder = current_user.id if current_user else "anonymous"
        resume_dir = os.path.join(config.UPLOAD_DIR, "resumes", owner_folder, profile.id)
        os.makedirs(resume_dir, exist_ok=True)

        final_filename = f"v{next_version}_{_safe_file_name(cv_file.filename or f'resume.{ext}') }"
        final_path = os.path.join(resume_dir, final_filename)
        shutil.copyfile(tmp_path, final_path)

        _set_resume_active(session, profile.id, active_version=-1)
        resume_doc = ResumeDocument(
            id=str(uuid.uuid4()),
            user_id=owner_user_id,
            profile_id=profile.id,
            version=next_version,
            original_filename=cv_file.filename or final_filename,
            storage_path=final_path,
            mime_type=cv_file.content_type,
            file_size_bytes=file_size_bytes,
            parsed_data=cv_data,
            uploaded_at=datetime.utcnow(),
            is_active=True,
        )
        session.add(resume_doc)

        if current_user:
            onboarding = session.query(OnboardingPreference).filter_by(user_id=current_user.id).first()
            if onboarding is None:
                onboarding = OnboardingPreference(
                    id=str(uuid.uuid4()),
                    user_id=current_user.id,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                )
                session.add(onboarding)
            onboarding.profile_id = profile.id
            onboarding.onboarding_completed = onboarding.onboarding_completed or False
            onboarding.updated_at = datetime.utcnow()
            session.add(onboarding)

        session.commit()
        session.refresh(profile)

        return UploadCVResponse(
            user_profile_id=profile.id,
            profile=profile_to_response(profile, cv_data),
            resume_version=profile.resume_version or 1,
            replaced_previous_resume=replaced_previous_resume,
            message=(
                "Resume updated. We cleared old matches and will generate fresh recommendations."
                if replaced_previous_resume
                else "Resume uploaded and parsed successfully"
            ),
        )
    except HTTPException:
        session.rollback()
        raise
    except Exception as exc:
        session.rollback()
        logger.exception("Error parsing CV")
        raise HTTPException(status_code=500, detail=f"Error parsing CV: {exc}")
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


@app.get("/api/profile/matches", response_model=MatchJobsResponse)
async def profile_matches(
    profile_id: Optional[str] = Query(default=None),
    refresh: bool = Query(False),
    top_n: int = Query(20, ge=1, le=100),
    min_score: float = Query(0, ge=0, le=100),
    current_user: AppUser = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    profile: Optional[UserProfile] = None
    if profile_id:
        profile = session.query(UserProfile).filter_by(id=profile_id).first()
        if not profile:
            raise HTTPException(status_code=404, detail=f"Profile {profile_id} not found")
        _validate_profile_access(profile, current_user)
    else:
        profile = _get_user_profile(session, user_id=current_user.id)
        if not profile:
            raise HTTPException(status_code=404, detail="No profile found")

    if refresh:
        return _run_matching(
            session=session,
            profile=profile,
            current_user=current_user,
            top_n=top_n,
            min_score=min_score,
        )

    rows = _load_stored_matches(session, profile=profile, top_n=top_n, min_score=min_score)
    return _build_match_jobs_response_from_rows(rows)


@app.get("/api/match-jobs", response_model=MatchJobsResponse)
async def match_jobs(
    profile_id: str = Query(...),
    top_n: int = Query(20, ge=1, le=100),
    min_score: float = Query(0, ge=0, le=100),
    current_user: Optional[AppUser] = Depends(get_optional_user),
    session: Session = Depends(get_db),
):
    profile = session.query(UserProfile).filter_by(id=profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail=f"Profile {profile_id} not found")
    _validate_profile_access(profile, current_user)
    return _run_matching(
        session=session,
        profile=profile,
        current_user=current_user,
        top_n=top_n,
        min_score=min_score,
    )


@app.get("/api/match/{match_result_id}", response_model=MatchDetailResponse)
async def match_detail(
    match_result_id: str,
    current_user: Optional[AppUser] = Depends(get_optional_user),
    session: Session = Depends(get_db),
):
    match = session.query(MatchResult).filter_by(id=match_result_id).first()
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")
    profile = session.query(UserProfile).filter_by(id=match.user_profile_id).first()
    if profile:
        _validate_profile_access(profile, current_user)
    job = session.query(Job).filter_by(id=match.job_id).first()
    match_payload = {
        "match_result_id": match.id,
        "job_id": match.job_id,
        "title": job.title if job else "",
        "company": job.company if job else "",
        "location": job.location if job else "",
        "job_url": job.url if job else "",
        "job_source": job.source if job else "",
        "fit_score": float(match.fit_score or 0),
        "personalized_fit_score": float(match.personalized_fit_score or match.fit_score or 0),
        "adaptive_boost": float(match.adaptive_boost or 0),
        "confidence": float(match.confidence or 0),
        "match_label": match.match_label or _label_from_score(float(match.personalized_fit_score or match.fit_score or 0)),
        "eligible_for_generation": bool(match.eligible_for_generation),
        "matched_skills": match.matched_skills or [],
        "missing_skills": match.missing_skills or [],
        "score_breakdown": match.score_breakdown or {},
        "fit_explanation": match.fit_explanation or "",
    }
    return MatchDetailResponse(
        match=MatchResultSchema(**match_payload),
        job_description=job.description_raw if job else "",
        source=job.source if job else "",
        posted_at=job.posted_at if job else None,
    )


@app.post("/api/signals", response_model=SignalResponse)
async def record_signal(
    request: SignalRequest,
    current_user: AppUser = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    payload = request.payload or {}
    if request.job_id:
        job = session.query(Job).filter_by(id=request.job_id).first()
        if job and "skills" not in payload:
            payload["skills"] = job.skills_extracted or []
        if job and "locations" not in payload:
            payload["locations"] = [job.location] if job.location else []

    signal = UserSignal(
        id=str(uuid.uuid4()),
        user_id=current_user.id,
        profile_id=request.profile_id,
        job_id=request.job_id,
        signal_type=request.signal_type,
        signal_payload=payload,
        created_at=datetime.utcnow(),
    )
    session.add(signal)
    session.commit()
    return SignalResponse(signal_id=signal.id, recorded_at=signal.created_at)


@app.post("/api/applications", response_model=ApplicationResponse)
async def create_application(
    request: ApplicationCreateRequest,
    current_user: AppUser = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    status = _normalize_application_status(request.status)
    resume_version = 1
    if request.profile_id:
        profile = session.query(UserProfile).filter_by(id=request.profile_id).first()
        if profile:
            _validate_profile_access(profile, current_user)
            resume_version = profile.resume_version or 1

    application = (
        session.query(UserApplication)
        .filter_by(
            user_id=current_user.id,
            profile_id=request.profile_id,
            job_id=request.job_id,
            resume_version=resume_version,
        )
        .first()
    )
    if application is None:
        application = UserApplication(
            id=str(uuid.uuid4()),
            user_id=current_user.id,
            profile_id=request.profile_id,
            resume_version=resume_version,
            job_id=request.job_id,
            created_at=datetime.utcnow(),
        )
    application.match_result_id = request.match_result_id
    application.generated_output_id = request.generated_output_id
    application.status = status
    application.notes = request.notes
    application.deadline_at = request.deadline_at
    application.next_action = request.next_action
    application.updated_at = datetime.utcnow()
    session.add(application)
    session.flush()
    job = session.query(Job).filter_by(id=application.job_id).first()
    insight = application_tracker.inspect_application(application, job)
    application.next_action = application.next_action or insight["next_action"]
    application.last_agent_summary = insight["summary"]
    session.add(application)
    session.commit()
    session.refresh(application)
    match = (
        session.query(MatchResult)
        .filter_by(id=application.match_result_id)
        .first()
        if application.match_result_id
        else None
    )
    generated = (
        session.query(GeneratedOutput)
        .filter_by(id=application.generated_output_id)
        .first()
        if application.generated_output_id
        else None
    )
    return _application_to_response(application, job=job, match=match, generated=generated)


@app.get("/api/applications", response_model=List[ApplicationResponse])
async def list_applications(
    current_user: AppUser = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    rows = (
        session.query(UserApplication, Job, MatchResult, GeneratedOutput)
        .outerjoin(Job, Job.id == UserApplication.job_id)
        .outerjoin(MatchResult, MatchResult.id == UserApplication.match_result_id)
        .outerjoin(GeneratedOutput, GeneratedOutput.id == UserApplication.generated_output_id)
        .filter(UserApplication.user_id == current_user.id)
        .order_by(desc(UserApplication.updated_at))
        .all()
    )

    return [
        _application_to_response(app, job=job, match=match, generated=generated)
        for app, job, match, generated in rows
    ]


@app.get("/api/applications/tracker/briefing", response_model=ApplicationTrackerResponse)
async def application_tracker_briefing(
    current_user: AppUser = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    rows = (
        session.query(UserApplication, Job)
        .outerjoin(Job, Job.id == UserApplication.job_id)
        .filter(UserApplication.user_id == current_user.id)
        .all()
    )
    return ApplicationTrackerResponse(**application_tracker.brief(rows))


@app.patch("/api/applications/{application_id}", response_model=ApplicationResponse)
async def update_application(
    application_id: str,
    request: ApplicationUpdateRequest,
    current_user: AppUser = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    app_row = session.query(UserApplication).filter_by(id=application_id, user_id=current_user.id).first()
    if not app_row:
        raise HTTPException(status_code=404, detail="Application not found")
    if request.status is not None:
        app_row.status = _normalize_application_status(request.status)
    if request.notes is not None:
        app_row.notes = request.notes
    if request.deadline_at is not None:
        app_row.deadline_at = request.deadline_at
    if request.next_action is not None:
        app_row.next_action = request.next_action

    job = session.query(Job).filter_by(id=app_row.job_id).first()
    insight = application_tracker.inspect_application(app_row, job)
    app_row.next_action = app_row.next_action or insight["next_action"]
    app_row.last_agent_summary = insight["summary"]
    app_row.updated_at = datetime.utcnow()
    session.add(app_row)
    session.commit()
    session.refresh(app_row)
    match = session.query(MatchResult).filter_by(id=app_row.match_result_id).first() if app_row.match_result_id else None
    generated = (
        session.query(GeneratedOutput).filter_by(id=app_row.generated_output_id).first()
        if app_row.generated_output_id
        else None
    )
    return _application_to_response(app_row, job=job, match=match, generated=generated)


@app.get("/api/applications/{application_id}", response_model=ApplicationDetailResponse)
async def application_detail(
    application_id: str,
    current_user: AppUser = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    app_row = session.query(UserApplication).filter_by(id=application_id, user_id=current_user.id).first()
    if not app_row:
        raise HTTPException(status_code=404, detail="Application not found")

    job = session.query(Job).filter_by(id=app_row.job_id).first()
    match = session.query(MatchResult).filter_by(id=app_row.match_result_id).first() if app_row.match_result_id else None
    generated = (
        session.query(GeneratedOutput).filter_by(id=app_row.generated_output_id).first()
        if app_row.generated_output_id
        else None
    )
    if generated is None and app_row.match_result_id:
        generated = (
            session.query(GeneratedOutput)
            .filter_by(match_result_id=app_row.match_result_id)
            .order_by(desc(GeneratedOutput.generated_at))
            .first()
        )

    match_schema = None
    if match:
        match_schema = MatchResultSchema(
            match_result_id=match.id,
            job_id=match.job_id,
            title=job.title if job else "",
            company=job.company if job else "",
            location=job.location if job else "",
            job_url=job.url if job else "",
            job_source=job.source if job else "",
            fit_score=float(match.fit_score or 0),
            personalized_fit_score=float(match.personalized_fit_score or match.fit_score or 0),
            adaptive_boost=float(match.adaptive_boost or 0),
            confidence=float(match.confidence or 0),
            match_label=match.match_label or _label_from_score(float(match.personalized_fit_score or 0)),
            eligible_for_generation=bool(match.eligible_for_generation),
            matched_skills=match.matched_skills or [],
            missing_skills=match.missing_skills or [],
            score_breakdown=match.score_breakdown or {},
            fit_explanation=match.fit_explanation or "",
        )

    app_response = _application_to_response(app_row, job=job, match=match, generated=generated)

    match_result_ref = ""
    if match:
        match_result_ref = match.id
    elif generated and generated.match_result_id:
        match_result_ref = generated.match_result_id

    return ApplicationDetailResponse(
        application=app_response,
        match=match_schema,
        job_description=job.description_raw if job else "",
        gap_report=GapReportSchema(**(generated.gap_report or {})) if generated and generated.gap_report else None,
        cover_letter=generated.cover_letter if generated else "",
        optimized_resume=generated.rewritten_cv if generated else "",
        optimized_resume_download_url=_asset_download_url(match_result_ref, "resume") if generated and match_result_ref else "",
        cover_letter_download_url=_asset_download_url(match_result_ref, "cover-letter") if generated and match_result_ref else "",
        timeline={
            "application_created_at": app_row.created_at,
            "application_updated_at": app_row.updated_at,
            "documents_generated_at": generated.generated_at if generated else None,
        },
    )


@app.post("/api/generate-outputs", response_model=GenerateOutputsResponse)
async def generate_outputs(
    match_result_id: str = Query(...),
    force_regenerate: bool = Query(False),
    current_user: Optional[AppUser] = Depends(get_optional_user),
    session: Session = Depends(get_db),
):
    match = session.query(MatchResult).filter_by(id=match_result_id).first()
    if not match:
        raise HTTPException(status_code=404, detail=f"Match result {match_result_id} not found")
    if not match.eligible_for_generation:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Match score {match.personalized_fit_score or match.fit_score}% is below "
                f"threshold {config.GENERATION_THRESHOLD}%."
            ),
        )

    profile = session.query(UserProfile).filter_by(id=match.user_profile_id).first()
    job = session.query(Job).filter_by(id=match.job_id).first()
    if not profile or not job:
        raise HTTPException(status_code=404, detail="Job or profile not found")
    _validate_profile_access(profile, current_user)

    resume_version = match.resume_version or profile.resume_version or 1

    cached = (
        session.query(GeneratedOutput)
        .filter_by(
            profile_id=profile.id,
            job_id=job.id,
            resume_version=resume_version,
        )
        .order_by(desc(GeneratedOutput.generated_at))
        .first()
    )

    if cached and not force_regenerate:
        if not cached.optimized_resume_path or not cached.cover_letter_path or not (
            os.path.exists(cached.optimized_resume_path or "")
            and os.path.exists(cached.cover_letter_path or "")
        ):
            resume_file_path, cover_file_path = create_generation_assets(
                output_root=config.UPLOAD_DIR,
                user_id=current_user.id if current_user else profile.user_id,
                profile={
                    "id": profile.id,
                    "name": profile.name or "",
                    "email": profile.email or "",
                    "phone": profile.phone or "",
                    "skills": profile.skills or [],
                    "experiences": (profile.parsed_resume_data or {}).get("experiences", []),
                    "education": profile.education or [],
                    "target_location": profile.target_location or "",
                },
                job={"title": job.title, "company": job.company},
                cv_result={
                    "keywords_added": cached.keywords_added or [],
                },
                cover_letter=cached.cover_letter or "",
            )
            cached.optimized_resume_path = resume_file_path
            cached.cover_letter_path = cover_file_path
            session.add(cached)
            session.commit()

        return GenerateOutputsResponse(
            match_result_id=match_result_id,
            gap_report=GapReportSchema(**(cached.gap_report or {})),
            rewritten_cv=cached.rewritten_cv or "",
            cover_letter=cached.cover_letter or "",
            ats_score_before=cached.ats_score_before or 0,
            ats_score_after=cached.ats_score_after or 0,
            fit_explanation=cached.fit_explanation or (match.fit_explanation or ""),
            keywords_added=cached.keywords_added or [],
            keyword_justifications=[
                KeywordReason(**item)
                for item in (cached.keyword_justifications or [])
                if isinstance(item, dict)
            ],
            cv_diff=cached.cv_diff or [],
            generated_at=cached.generated_at,
            cached=True,
            optimized_resume_download_url=_asset_download_url(match_result_id, "resume"),
            cover_letter_download_url=_asset_download_url(match_result_id, "cover-letter"),
        )

    parsed = profile.parsed_resume_data or {}
    profile_dict = {
        "id": profile.id,
        "name": profile.name or "",
        "email": profile.email or "",
        "phone": profile.phone or parsed.get("phone", ""),
        "skills": profile.skills or [],
        "job_titles": profile.job_titles or [],
        "education": profile.education or parsed.get("education", []),
        "experiences": parsed.get("experiences", []),
        "years_experience": profile.years_experience or 0,
        "seniority_level": profile.seniority_level or "Mid",
        "internship_years": parsed.get("internship_years", 0),
        "fulltime_years": parsed.get("fulltime_years", 0),
        "internship_only": parsed.get("internship_only", False),
        "leadership_experience": parsed.get("leadership_experience", False),
        "tech_stack_maturity": parsed.get("tech_stack_maturity", "foundational"),
        "project_complexity": parsed.get("project_complexity", "basic"),
        "target_role": profile.target_role or "",
        "target_location": profile.target_location or "",
    }

    try:
        pipeline_result = get_agent_pipeline().run(
            profile=profile_dict,
            job_description=job.description_raw,
            company_name=job.company,
            original_cv=parsed.get("raw_text", "") or profile.preferences_raw or "",
        )
        gap_report = pipeline_result["gap_report"]
        cv_result = pipeline_result["cv_result"]
        cover_letter = pipeline_result["cover_letter"]

        resume_file_path, cover_file_path = create_generation_assets(
            output_root=config.UPLOAD_DIR,
            user_id=current_user.id if current_user else profile.user_id,
            profile=profile_dict,
            job={"title": job.title, "company": job.company},
            cv_result=cv_result,
            cover_letter=cover_letter,
        )

        generated = cached or GeneratedOutput(
            id=str(uuid.uuid4()),
            match_result_id=match_result_id,
            user_id=current_user.id if current_user else profile.user_id,
            profile_id=profile.id,
            job_id=job.id,
            resume_version=resume_version,
        )
        generated.gap_report = gap_report
        generated.rewritten_cv = cv_result.get("rewritten_cv", "")
        generated.cover_letter = cover_letter
        generated.ats_score_before = cv_result.get("ats_score_before", 0)
        generated.ats_score_after = cv_result.get("ats_score_after", 0)
        generated.fit_explanation = match.fit_explanation or ""
        generated.keyword_justifications = cv_result.get("keyword_justifications", [])
        generated.cv_diff = cv_result.get("cv_diff", [])
        generated.keywords_added = cv_result.get("keywords_added", [])
        generated.optimized_resume_path = resume_file_path
        generated.cover_letter_path = cover_file_path
        generated.generated_at = datetime.utcnow()
        generated.match_result_id = match_result_id
        generated.user_id = current_user.id if current_user else profile.user_id
        generated.profile_id = profile.id
        generated.job_id = job.id
        generated.resume_version = resume_version
        session.add(generated)
        session.flush()

        if current_user:
            app_entry = (
                session.query(UserApplication)
                .filter_by(
                    user_id=current_user.id,
                    profile_id=profile.id,
                    job_id=job.id,
                    resume_version=resume_version,
                )
                .first()
            )
            if app_entry is None:
                app_entry = UserApplication(
                    id=str(uuid.uuid4()),
                    user_id=current_user.id,
                    profile_id=profile.id,
                    resume_version=resume_version,
                    job_id=job.id,
                    created_at=datetime.utcnow(),
                )
            app_entry.match_result_id = match_result_id
            app_entry.generated_output_id = generated.id
            app_entry.status = "generated"
            app_entry.notes = "Documents generated"
            insight = application_tracker.inspect_application(app_entry, job)
            app_entry.next_action = app_entry.next_action or insight["next_action"]
            app_entry.last_agent_summary = insight["summary"]
            app_entry.updated_at = datetime.utcnow()
            session.add(app_entry)

        session.commit()
        session.refresh(generated)

        return GenerateOutputsResponse(
            match_result_id=match_result_id,
            gap_report=GapReportSchema(**gap_report),
            rewritten_cv=generated.rewritten_cv or "",
            cover_letter=generated.cover_letter or "",
            ats_score_before=generated.ats_score_before or 0,
            ats_score_after=generated.ats_score_after or 0,
            fit_explanation=generated.fit_explanation or "",
            keywords_added=generated.keywords_added or [],
            keyword_justifications=[
                KeywordReason(**item)
                for item in (generated.keyword_justifications or [])
                if isinstance(item, dict)
            ],
            cv_diff=generated.cv_diff or [],
            generated_at=generated.generated_at,
            cached=False,
            optimized_resume_download_url=_asset_download_url(match_result_id, "resume"),
            cover_letter_download_url=_asset_download_url(match_result_id, "cover-letter"),
        )
    except Exception as exc:
        session.rollback()
        logger.error(f"Error generating outputs: {exc}")
        raise HTTPException(status_code=500, detail=f"Generation failed: {exc}")


@app.get("/api/generated-assets/{match_result_id}/{asset_type}")
async def download_generated_asset(
    match_result_id: str,
    asset_type: str,
    current_user: AppUser = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    generated = (
        session.query(GeneratedOutput)
        .filter_by(match_result_id=match_result_id)
        .order_by(desc(GeneratedOutput.generated_at))
        .first()
    )
    if not generated:
        raise HTTPException(status_code=404, detail="Generated assets not found")

    profile = session.query(UserProfile).filter_by(id=generated.profile_id).first()
    if profile:
        _validate_profile_access(profile, current_user)

    if asset_type == "resume":
        path = generated.optimized_resume_path
        filename = f"optimized_resume_{match_result_id}.docx"
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    elif asset_type == "cover-letter":
        path = generated.cover_letter_path
        filename = f"cover_letter_{match_result_id}.docx"
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    else:
        raise HTTPException(status_code=400, detail="Unknown asset type")

    if not path or not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Asset file not found")

    return FileResponse(path=path, filename=filename, media_type=media_type)


def _scraper_response(
    status: str,
    message: str,
    data: Optional[Dict] = None,
    success: bool = True,
    error: Optional[Dict] = None,
) -> ApiEnvelope:
    return ApiEnvelope(
        success=success,
        status=status,
        message=message,
        data=data or {},
        error=error,
    )


def _trigger_scraper(
    provider: str,
    payload: ScraperTriggerRequest,
    session: Session,
) -> ApiEnvelope:
    if is_rate_limited(provider=provider, session=session):
        raise HTTPException(
            status_code=429,
            detail=(
                f"{source_label(provider)} scrape was triggered recently. "
                "Please wait before triggering again."
            ),
        )

    if payload.async_mode:
        task = scraper_tasks.submit(
            provider=provider,
            retries=payload.retries,
            target_count=payload.target_count,
        )
        typed = ScraperTaskResponse(
            task_id=task["task_id"],
            provider=provider,
            status=task["status"],
            accepted_at=task["accepted_at"],
            message="Scrape queued",
        )
        return _scraper_response(
            status="accepted",
            message=f"{source_label(provider)} scrape queued",
            data=typed.model_dump(),
        )

    task = scraper_tasks.run_sync(
        provider=provider,
        retries=payload.retries,
        target_count=payload.target_count,
    )
    if task.get("status") == "completed":
        return _scraper_response(
            status="completed",
            message=f"{source_label(provider)} scrape completed",
            data=task,
        )

    return _scraper_response(
        status="failed",
        success=False,
        message=f"{source_label(provider)} scrape failed",
        data=task,
        error=task.get("error") or {"message": "unknown error"},
    )


@app.post("/api/scrapers/jobsie/run", response_model=ApiEnvelope)
async def scrape_jobsie(
    request: ScraperTriggerRequest,
    session: Session = Depends(get_db),
):
    return _trigger_scraper(provider="jobsie", payload=request, session=session)


@app.post("/api/scrapers/irishjobs/run", response_model=ApiEnvelope)
async def scrape_irishjobs(
    request: ScraperTriggerRequest,
    session: Session = Depends(get_db),
):
    return _trigger_scraper(provider="irishjobs", payload=request, session=session)


@app.post("/api/scrapers/linkedin/run", response_model=ApiEnvelope)
async def scrape_linkedin(
    request: ScraperTriggerRequest,
    session: Session = Depends(get_db),
):
    return _trigger_scraper(provider="linkedin", payload=request, session=session)


@app.post("/api/scrapers/all/run", response_model=ApiEnvelope)
async def scrape_all(
    request: ScraperTriggerRequest,
    session: Session = Depends(get_db),
):
    return _trigger_scraper(provider="all", payload=request, session=session)


@app.get("/api/scrapers/tasks/{task_id}", response_model=ApiEnvelope)
async def scraper_task_status(task_id: str):
    task = scraper_tasks.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Scraper task not found")

    status = task.get("status", "unknown")
    if status == "failed":
        return _scraper_response(
            success=False,
            status="failed",
            message="Scraper task failed",
            data=task,
            error=task.get("error") or {"message": "unknown error"},
        )
    return _scraper_response(
        status=status,
        message="Scraper task status",
        data=task,
    )


@app.get("/api/scrapers/runs/latest", response_model=ApiEnvelope)
async def latest_scraper_run(
    source: Optional[str] = Query(default=None),
    session: Session = Depends(get_db),
):
    query = session.query(ScraperRun)
    if source:
        query = query.filter_by(source=source)
    run = query.order_by(desc(ScraperRun.started_at)).first()
    if not run:
        return _scraper_response(status="empty", message="No scraper runs found", data={})
    return _scraper_response(
        status="ok",
        message="Latest scraper run",
        data={
            "id": run.id,
            "source": run.source,
            "status": run.status,
            "started_at": run.started_at,
            "finished_at": run.finished_at,
            "jobs_found": run.jobs_found,
            "jobs_inserted": run.jobs_inserted,
            "duplicates_skipped": run.duplicates_skipped,
            "errors": run.errors,
        },
    )


@app.get("/")
async def root():
    return {
        "name": "Clover",
        "version": "3.0.0",
        "health": "/api/health",
        "features": {
            "auth": ["/api/auth/signup", "/api/auth/login", "/api/auth/refresh", "/api/auth/me"],
            "onboarding": ["/api/onboarding"],
            "profile": ["/api/profile/me", "/api/profile/matches", "/api/profile/resume/download"],
            "matching": ["/api/upload-cv", "/api/match-jobs", "/api/match/{id}"],
            "generation": ["/api/generate-outputs", "/api/generated-assets/{match_result_id}/{asset_type}"],
            "adaptive_learning": ["/api/signals"],
            "applications": ["/api/applications", "/api/applications/{application_id}"],
            "scrapers": [
                "/api/scrapers/jobsie/run",
                "/api/scrapers/irishjobs/run",
                "/api/scrapers/linkedin/run",
                "/api/scrapers/all/run",
                "/api/scrapers/tasks/{task_id}",
            ],
        },
    }


@app.on_event("startup")
async def startup_event():
    logger.info("=" * 50)
    logger.info("Clover API Starting...")
    logger.info(f"Database: {config.POSTGRES_HOST}:{config.POSTGRES_PORT}/{config.POSTGRES_DB}")
    logger.info(f"Generation threshold: {config.GENERATION_THRESHOLD}%")
    logger.info(f"Gemini configured: {bool(config.GEMINI_API_KEY)}")
    if db_manager.init_db():
        logger.info("Database initialized")
    else:
        logger.error("Database initialization failed")
    logger.info("=" * 50)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "api.main:app",
        host=config.API_HOST,
        port=config.API_PORT,
        reload=config.API_DEBUG,
    )
