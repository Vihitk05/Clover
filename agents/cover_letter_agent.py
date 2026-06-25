import logging
from typing import Dict, Any

from agents.gemini_client import GeminiClient

logger = logging.getLogger(__name__)

class CoverLetterAgent:
    """Agent 3: Cover Letter Writer - generates personalized cover letters"""
    
    def __init__(self):
        self.name = "Cover Letter Writer"
        self.gemini = GeminiClient()
    
    def run(
        self,
        profile: Dict[str, Any],
        gap_report: Dict[str, Any],
        job_description: str,
        company_name: str,
        candidate_name: str = "",
    ) -> str:
        """
        Generate personalized cover letter
        
        Args:
            profile: User profile
            gap_report: Gap analysis from Agent 1
            job_description: Job description text
            company_name: Company name
            
        Returns:
            Personalized cover letter
        """
        logger.info(f"Running {self.name} agent")

        matched_skills = gap_report.get('matched_skills', [])
        missing_skills = gap_report.get('missing_skills', [])
        
        signature_name = candidate_name or profile.get("name") or "[Your Name]"

        cover_letter = f"""
Dear Hiring Manager,

I am writing to express my strong interest in the position at {company_name}. 
With a background in {', '.join(matched_skills[:3]) if matched_skills else 'relevant technologies'}, 
I am confident in my ability to contribute effectively to your team.

My experience includes working with {', '.join(matched_skills[:5])} which directly aligns with the requirements of this role. 
{'I am also actively developing skills in ' + ', '.join(missing_skills[:3]) if missing_skills else ''}

I am particularly excited about this opportunity because it combines my technical expertise with the chance to work on innovative projects. 
I look forward to discussing how I can contribute to {company_name}'s success.

Best regards,
{signature_name}
        """.strip()
        
        if not self.gemini.enabled:
            return cover_letter

        prompt = f"""
You are Clover's cover letter agent.
Write a concise but role-tailored cover letter in plain text.
No markdown fences.
Keep it <= 260 words.

Company: {company_name}
Candidate name: {signature_name}
Profile skills: {profile.get('skills', [])}
Matched skills: {matched_skills}
Missing skills under development: {missing_skills[:5]}
Job description:
{job_description[:5000]}
        """.strip()

        generated = self.gemini.generate_text(prompt=prompt)
        if not generated:
            return cover_letter
        if signature_name and signature_name.lower() not in generated.lower():
            return f"{generated.strip()}\n\nSincerely,\n{signature_name}\n"
        return generated
