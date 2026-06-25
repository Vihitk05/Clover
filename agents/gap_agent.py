import logging
from typing import Dict, Any, List

from agents.gemini_client import GeminiClient

logger = logging.getLogger(__name__)

class GapAgent:
    """Agent 1: Gap analysis - identifies missing skills and weak areas"""
    
    def __init__(self):
        self.name = "Gap Analyst"
        self.gemini = GeminiClient()
    
    def run(self, profile: Dict[str, Any], job_description: str) -> Dict[str, Any]:
        """
        Analyze gap between profile and job description
        
        Args:
            profile: User profile with skills, experience, etc.
            job_description: Job description text
            
        Returns:
            Gap report with missing skills, weak areas, summary
        """
        logger.info(f"Running {self.name} agent")

        from scraper.etl.cleaner import DataCleaner
        cleaner = DataCleaner()
        job_skills = cleaner.extract_skills(job_description)
        
        profile_skills = set([s.lower() for s in profile.get('skills', [])])
        job_skills_set = set([s.lower() for s in job_skills])
        
        matched_skills = list(profile_skills & job_skills_set)
        missing_skills = list(job_skills_set - profile_skills)
        
        weak_areas = []
        if len(missing_skills) > 5:
            weak_areas.append(f"Missing {len(missing_skills)} technical skills")
        elif len(missing_skills) > 0:
            weak_areas.append(f"Missing key skills: {', '.join(missing_skills[:3])}")
        
        match_percentage = len(matched_skills) / len(job_skills_set) * 100 if job_skills_set else 0
        
        if match_percentage >= 80:
            summary = "Strong profile match! Your skills align well with this role."
        elif match_percentage >= 50:
            summary = "Good foundation, but there are some skill gaps to address."
        else:
            summary = "Significant skill gaps detected. Consider upskilling in key areas."
        
        fallback = {
            "missing_skills": missing_skills,
            "weak_areas": weak_areas,
            "matched_skills": matched_skills,
            "summary": summary,
            "recommended_courses": missing_skills[:3],
            "experience_gap": None
        }

        profile_skills_list = profile.get("skills", [])
        if not self.gemini.enabled:
            return fallback

        prompt = f"""
You are Clover's Gap Analysis agent.
Given profile skills and job description, produce strict JSON with keys:
missing_skills (array of strings),
weak_areas (array of strings),
matched_skills (array of strings),
summary (string, <= 35 words),
recommended_courses (array of strings),
experience_gap (string or null).

Profile skills: {profile_skills_list}
Job description:
{job_description[:5000]}
        """.strip()

        generated = self.gemini.generate_json(prompt=prompt, fallback=fallback)
        return {
            "missing_skills": generated.get("missing_skills", fallback["missing_skills"]),
            "weak_areas": generated.get("weak_areas", fallback["weak_areas"]),
            "matched_skills": generated.get("matched_skills", fallback["matched_skills"]),
            "summary": generated.get("summary", fallback["summary"]),
            "recommended_courses": generated.get("recommended_courses", fallback["recommended_courses"]),
            "experience_gap": generated.get("experience_gap", fallback["experience_gap"]),
        }
