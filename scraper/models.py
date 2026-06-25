from sqlalchemy import Column, Integer, String, Text, DateTime, Float, Boolean, Index, JSON, Numeric
from sqlalchemy.orm import declarative_base
from datetime import datetime
import hashlib
import uuid

Base = declarative_base()

class Job(Base):
    __tablename__ = 'jobs'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    source_hash = Column(String(64), unique=True, nullable=False, index=True)
    title = Column(String(255), nullable=False)
    company = Column(String(255), nullable=False)
    location = Column(String(100))
    salary_min = Column(Integer)
    salary_max = Column(Integer)
    seniority = Column(String(20))
    sector = Column(String(50))
    description_raw = Column(Text, nullable=False)
    skills_extracted = Column(JSON)
    source = Column(String(30), nullable=False)
    url = Column(Text)
    posted_at = Column(DateTime)
    scraped_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    __table_args__ = (
        Index('idx_job_company', 'company'),
        Index('idx_job_title', 'title'),
        Index('idx_job_location', 'location'),
        Index('idx_job_seniority', 'seniority'),
        Index('idx_job_source', 'source'),
        Index('idx_job_posted_at', 'posted_at'),
    )
    
    def generate_hash(self):
        """Generate unique hash WITHOUT time to prevent daily duplication"""
        hash_string = f"{self.title}|{self.company}|{self.location}"
        return hashlib.sha256(hash_string.encode()).hexdigest()

class ScraperRun(Base):
    __tablename__ = 'scraper_runs'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    source = Column(String(30), nullable=False)
    pages_scraped = Column(Integer, default=0)
    jobs_found = Column(Integer, default=0)
    jobs_inserted = Column(Integer, default=0)
    duplicates_skipped = Column(Integer, default=0)
    errors = Column(Integer, default=0)
    started_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime)
    status = Column(String(20), default='running')

class UserProfile(Base):
    __tablename__ = 'user_profiles'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), index=True)
    name = Column(String(255))
    email = Column(String(255))
    phone = Column(String(64))
    skills = Column(JSON)
    job_titles = Column(JSON)
    years_experience = Column(Float)
    seniority_level = Column(String(20))
    education = Column(JSON)
    preferences_raw = Column(Text)
    target_role = Column(String(255))
    target_location = Column(String(100))
    salary_expectation_min = Column(Integer)
    parsed_resume_data = Column(JSON)
    resume_version = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ResumeDocument(Base):
    __tablename__ = "resume_documents"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), index=True)
    profile_id = Column(String(36), nullable=False, index=True)
    version = Column(Integer, nullable=False, default=1)
    original_filename = Column(String(255), nullable=False)
    storage_path = Column(Text, nullable=False)
    mime_type = Column(String(100))
    file_size_bytes = Column(Integer)
    parsed_data = Column(JSON)
    uploaded_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

class MatchResult(Base):
    __tablename__ = 'match_results'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_profile_id = Column(String(36), nullable=False, index=True)
    resume_version = Column(Integer, default=1, nullable=False, index=True)
    job_id = Column(String(36), nullable=False, index=True)
    fit_score = Column(Numeric(5, 2))
    confidence = Column(Numeric(5, 2), default=0)
    match_label = Column(String(40), default="Moderate Match")
    eligible_for_generation = Column(Boolean, default=False)
    missing_skills = Column(JSON)
    matched_skills = Column(JSON)
    score_breakdown = Column(JSON)
    personalized_fit_score = Column(Numeric(5, 2))
    adaptive_boost = Column(Numeric(5, 2), default=0)
    fit_explanation = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

class GeneratedOutput(Base):
    __tablename__ = 'generated_outputs'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    match_result_id = Column(String(36), nullable=False, index=True)
    user_id = Column(String(36), index=True)
    profile_id = Column(String(36), index=True)
    job_id = Column(String(36), index=True)
    resume_version = Column(Integer, default=1, nullable=False, index=True)
    gap_report = Column(JSON)
    rewritten_cv = Column(Text)
    optimized_resume_path = Column(Text)
    cover_letter_path = Column(Text)
    cover_letter = Column(Text)
    ats_score_before = Column(Integer)
    ats_score_after = Column(Integer)
    fit_explanation = Column(Text)
    keyword_justifications = Column(JSON)
    cv_diff = Column(JSON)
    keywords_added = Column(JSON)
    generated_at = Column(DateTime, default=datetime.utcnow)


class AppUser(Base):
    __tablename__ = "app_users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), unique=True, nullable=False, index=True)
    full_name = Column(String(255))
    password_hash = Column(Text, nullable=False)
    oauth_provider = Column(String(30))
    oauth_subject = Column(String(255))
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_login_at = Column(DateTime)


class RefreshSession(Base):
    __tablename__ = "refresh_sessions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), nullable=False, index=True)
    refresh_token_hash = Column(String(128), nullable=False, unique=True, index=True)
    user_agent = Column(String(255))
    ip_address = Column(String(64))
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    revoked_at = Column(DateTime)


class OnboardingPreference(Base):
    __tablename__ = "onboarding_preferences"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), nullable=False, unique=True, index=True)
    profile_id = Column(String(36), index=True)
    target_roles = Column(JSON)
    preferred_locations = Column(JSON)
    salary_expectation_min = Column(Integer)
    salary_expectation_max = Column(Integer)
    work_types = Column(JSON)
    career_goals = Column(Text)
    skill_confidence = Column(JSON)
    onboarding_completed = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class UserSignal(Base):
    __tablename__ = "user_signals"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), nullable=False, index=True)
    profile_id = Column(String(36), index=True)
    job_id = Column(String(36), index=True)
    signal_type = Column(String(40), nullable=False, index=True)
    signal_payload = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class UserApplication(Base):
    __tablename__ = "user_applications"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), nullable=False, index=True)
    profile_id = Column(String(36), index=True)
    resume_version = Column(Integer, default=1, nullable=False)
    job_id = Column(String(36), nullable=False, index=True)
    match_result_id = Column(String(36), index=True)
    generated_output_id = Column(String(36), index=True)
    status = Column(String(30), nullable=False, default="draft")
    deadline_at = Column(DateTime)
    next_action = Column(Text)
    last_agent_summary = Column(Text)
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
