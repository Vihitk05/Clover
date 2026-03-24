from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid

class UserProfile(BaseModel):
    """User profile extracted from CV"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    email: str = ""
    phone: str = ""
    linkedin: str = ""
    github: str = ""
    skills: List[str] = Field(default_factory=list)
    job_titles: List[str] = Field(default_factory=list)
    years_experience: float = 0.0
    seniority_level: str = "Entry Level"
    education: List[Dict[str, Any]] = Field(default_factory=list)
    preferences_raw: str = ""
    target_role: str = ""
    target_location: str = ""
    salary_expectation_min: Optional[int] = None
    created_at: datetime = Field(default_factory=datetime.now)
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "John Doe",
                "email": "john@example.com",
                "skills": ["Python", "Machine Learning"],
                "job_titles": ["Software Engineer"],
                "years_experience": 3.5,
                "seniority_level": "Junior"
            }
        }

class JobRecord(BaseModel):
    """Job record from scraper"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    company: str
    location: str
    description_raw: str
    skills_extracted: List[str] = Field(default_factory=list)
    seniority: str = ""
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    source: str
    url: str
    posted_at: datetime
    scraped_at: datetime = Field(default_factory=datetime.now)
    is_active: bool = True
    
    class Config:
        json_schema_extra = {
            "example": {
                "title": "Software Engineer",
                "company": "Google",
                "location": "Dublin",
                "source": "jobs.ie",
                "url": "https://..."
            }
        }