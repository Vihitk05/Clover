import json
import logging
import os
import re
from typing import Any, Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)


SENIORITY_ORDER = {
    "Fresher": 0,
    "Entry Level": 1,
    "Junior": 2,
    "Mid": 3,
    "Senior": 4,
    "Lead": 5,
    "Manager": 6,
    "Principal": 7,
    "Staff": 7,
}


def _normalize_seniority(value: str) -> str:
    token = (value or "").lower()
    if any(k in token for k in ["principal", "staff"]):
        return "Principal"
    if any(k in token for k in ["manager", "head of", "director"]):
        return "Manager"
    if "lead" in token:
        return "Lead"
    if "senior" in token:
        return "Senior"
    if "mid" in token:
        return "Mid"
    if any(k in token for k in ["junior", "associate"]):
        return "Junior"
    if any(k in token for k in ["intern", "internship", "graduate", "entry"]):
        return "Entry Level"
    if "fresher" in token:
        return "Fresher"
    return "Junior"


def _extract_required_years(text: str) -> Optional[float]:
    if not text:
        return None
    matches = re.findall(r"(\d+(?:\.\d+)?)\s*\+?\s*(?:years|yrs)", text.lower())
    if not matches:
        return None
    try:
        return float(max(float(x) for x in matches))
    except ValueError:
        return None


def _is_entry_friendly(title: str, description: str, seniority: str) -> bool:
    token = f"{title} {description} {seniority}".lower()
    entry_terms = ["intern", "graduate", "entry", "junior", "trainee", "apprentice"]
    return any(term in token for term in entry_terms)


def _fit_label(score: float) -> str:
    if score >= 85:
        return "Excellent Match"
    if score >= 72:
        return "Strong Match"
    if score >= 58:
        return "Good Match"
    return "Moderate Match"


class MatchEngine:
    """Production match engine with seniority-aware filtering and safer scoring."""

    def __init__(
        self,
        threshold: float = None,
        persist_directory: str = "./chroma_db",
        use_mock: bool = False,
    ):
        if threshold is None:
            threshold = float(os.getenv("GENERATION_THRESHOLD", "75.0"))

        self.threshold = threshold
        self.use_mock = use_mock

        if not use_mock:
            try:
                import chromadb

                self.chroma_client = chromadb.PersistentClient(path=persist_directory)
                try:
                    self.job_collection = self.chroma_client.get_collection("job_embeddings")
                    logger.info(
                        "Loaded job embeddings collection with %s jobs",
                        self.job_collection.count(),
                    )
                except Exception as exc:
                    logger.warning("Job embeddings collection not found: %s", exc)
                    self.job_collection = None
            except ImportError:
                logger.warning("ChromaDB not installed. Install with: pip install chromadb")
                self.job_collection = None
        else:
            self.job_collection = None
            logger.info("Using mock mode - no ChromaDB connection")

    def _build_profile_context(self, profile: Dict[str, Any]) -> Dict[str, Any]:
        years = float(profile.get("years_experience") or 0.0)
        internship_years = float(profile.get("internship_years") or 0.0)
        fulltime_years = float(profile.get("fulltime_years") or max(0.0, years - internship_years))
        internship_only = bool(profile.get("internship_only") or (fulltime_years < 0.5 and internship_years > 0))
        profile_seniority = _normalize_seniority(profile.get("seniority_level", "Junior"))

        return {
            "years": years,
            "internship_years": internship_years,
            "fulltime_years": fulltime_years,
            "internship_only": internship_only,
            "seniority": profile_seniority,
            "seniority_rank": SENIORITY_ORDER.get(profile_seniority, 2),
            "skills": {s.lower() for s in profile.get("skills", []) if isinstance(s, str)},
            "education": profile.get("education", []) or [],
            "project_complexity": (profile.get("project_complexity") or "basic").lower(),
        }

    def _is_role_too_senior(self, profile_ctx: Dict[str, Any], job: Dict[str, Any]) -> bool:
        title = job.get("title", "")
        description = job.get("description_raw", "")
        job_seniority = _normalize_seniority(job.get("seniority", ""))
        job_rank = SENIORITY_ORDER.get(job_seniority, 2)
        req_years = _extract_required_years(f"{title} {description}")

        if profile_ctx["internship_only"] and not _is_entry_friendly(title, description, job_seniority):
            if job_rank >= SENIORITY_ORDER["Mid"]:
                return True

        if profile_ctx["seniority_rank"] <= SENIORITY_ORDER["Entry Level"] and job_rank >= SENIORITY_ORDER["Senior"]:
            return True

        if req_years is not None:
            if profile_ctx["fulltime_years"] + 0.5 < req_years and req_years >= 4:
                return True

        seniority_keywords = ["staff", "principal", "engineering manager", "head of", "director"]
        lowered = f"{title} {description}".lower()
        if profile_ctx["seniority_rank"] <= SENIORITY_ORDER["Junior"] and any(k in lowered for k in seniority_keywords):
            return True

        return False

    def _simple_explanation(
        self,
        label: str,
        matched_skills: List[str],
        missing_skills: List[str],
        profile_ctx: Dict[str, Any],
        job: Dict[str, Any],
    ) -> str:
        if matched_skills:
            skills_phrase = ", ".join(matched_skills[:2])
        else:
            skills_phrase = "your core skills"

        if label in {"Excellent Match", "Strong Match"}:
            if profile_ctx["internship_only"]:
                return f"Strong fit for your internship experience in {skills_phrase}."
            return f"Recommended because your experience and {skills_phrase} align with this role."

        if missing_skills:
            return f"Good potential match. Building {missing_skills[0]} would strengthen your fit."

        return "This role has partial overlap with your profile and may still be worth exploring."

    def compute_fit_score(
        self,
        profile_embedding: List[float],
        job_embedding: List[float],
        profile: Dict[str, Any],
        job: Dict[str, Any],
    ) -> Dict[str, Any]:
        profile_ctx = self._build_profile_context(profile)

        profile_vec = np.array(profile_embedding)
        job_vec = np.array(job_embedding)
        dot_product = np.dot(profile_vec, job_vec)
        norm_product = np.linalg.norm(profile_vec) * np.linalg.norm(job_vec)
        cosine_similarity = dot_product / norm_product if norm_product > 0 else 0
        semantic_score = float(max(0.0, min(100.0, cosine_similarity * 100)))

        profile_skills = profile_ctx["skills"]
        job_skills = {s.lower() for s in (job.get("skills_extracted") or []) if isinstance(s, str)}

        matched_skills = sorted(list(profile_skills & job_skills))
        missing_skills = sorted(list(job_skills - profile_skills))
        skill_precision = (len(matched_skills) / max(1, len(profile_skills))) * 100
        skill_recall = (len(matched_skills) / max(1, len(job_skills))) * 100
        if skill_precision + skill_recall == 0:
            skill_score = 0.0
        else:
            skill_score = 2 * skill_precision * skill_recall / (skill_precision + skill_recall)

        job_seniority = _normalize_seniority(job.get("seniority", ""))
        profile_rank = profile_ctx["seniority_rank"]
        job_rank = SENIORITY_ORDER.get(job_seniority, 2)
        diff = job_rank - profile_rank
        if diff <= 0:
            seniority_score = 92.0
        elif diff == 1:
            seniority_score = 76.0
        elif diff == 2:
            seniority_score = 48.0
        else:
            seniority_score = 22.0

        req_years = _extract_required_years(f"{job.get('title', '')} {job.get('description_raw', '')}")
        candidate_years = profile_ctx["fulltime_years"] + (0.4 * profile_ctx["internship_years"])
        if req_years is None:
            expected_years = {
                "Entry Level": 0.0,
                "Junior": 1.5,
                "Mid": 4.0,
                "Senior": 6.0,
                "Lead": 8.0,
                "Manager": 8.0,
                "Principal": 10.0,
            }.get(job_seniority, 2.0)
        else:
            expected_years = req_years

        gap = candidate_years - expected_years
        if gap >= 0:
            experience_score = 95.0
        elif gap >= -1:
            experience_score = 72.0
        elif gap >= -2.5:
            experience_score = 46.0
        else:
            experience_score = 18.0

        internship_alignment = 88.0
        if profile_ctx["internship_only"]:
            internship_alignment = 90.0 if _is_entry_friendly(job.get("title", ""), job.get("description_raw", ""), job_seniority) else 20.0

        profile_location = (profile.get("target_location", "") or "").lower()
        job_location = (job.get("location", "") or "").lower()
        if profile_location and job_location:
            if profile_location in job_location or job_location in profile_location:
                location_score = 100.0
            elif "remote" in job_location or "remote" in profile_location:
                location_score = 82.0
            else:
                location_score = 52.0
        else:
            location_score = 68.0

        profile_edu_text = " ".join(str(x) for x in profile_ctx["education"]).lower()
        job_text = f"{job.get('title', '')} {job.get('description_raw', '')}".lower()
        if "phd" in job_text and "phd" not in profile_edu_text:
            education_score = 45.0
        elif any(x in job_text for x in ["bachelor", "degree", "computer science"]):
            education_score = 80.0 if profile_ctx["education"] else 62.0
        else:
            education_score = 72.0

        complexity = profile_ctx["project_complexity"]
        if "distributed" in job_text or "microservices" in job_text:
            project_relevance_score = 90.0 if complexity in {"high", "medium"} else 48.0
        elif "api" in job_text or "backend" in job_text or "frontend" in job_text:
            project_relevance_score = 84.0 if complexity in {"medium", "high"} else 65.0
        else:
            project_relevance_score = 72.0

        weights = {
            "semantic": 0.18,
            "skills": 0.30,
            "seniority": 0.16,
            "experience": 0.17,
            "internship": 0.09,
            "project": 0.05,
            "education": 0.03,
            "location": 0.02,
        }

        fit_score = (
            weights["semantic"] * semantic_score
            + weights["skills"] * skill_score
            + weights["seniority"] * seniority_score
            + weights["experience"] * experience_score
            + weights["internship"] * internship_alignment
            + weights["project"] * project_relevance_score
            + weights["education"] * education_score
            + weights["location"] * location_score
        )

        penalties = 0.0
        if diff >= 2:
            penalties += 16.0
        if gap < -2.5:
            penalties += 12.0
        if profile_ctx["internship_only"] and not _is_entry_friendly(
            job.get("title", ""), job.get("description_raw", ""), job_seniority
        ):
            penalties += 18.0

        fit_score = max(0.0, min(100.0, fit_score - penalties))

        confidence = max(
            10.0,
            min(
                100.0,
                (0.5 * skill_recall)
                + (0.3 * max(0.0, 100 - max(0, diff) * 25))
                + (0.2 * max(0.0, 100 - abs(gap) * 18)),
            ),
        )

        label = _fit_label(fit_score)
        explanation = self._simple_explanation(
            label=label,
            matched_skills=matched_skills,
            missing_skills=missing_skills,
            profile_ctx=profile_ctx,
            job=job,
        )

        eligible = fit_score >= self.threshold and confidence >= 45

        return {
            "fit_score": float(round(fit_score, 2)),
            "eligible_for_generation": bool(eligible),
            "semantic_score": float(round(semantic_score, 2)),
            "skill_score": float(round(skill_score, 2)),
            "seniority_score": float(round(seniority_score, 2)),
            "location_score": float(round(location_score, 2)),
            "experience_score": float(round(experience_score, 2)),
            "matched_skills": matched_skills,
            "missing_skills": missing_skills,
            "confidence": float(round(confidence, 2)),
            "match_label": label,
            "fit_explanation": explanation,
            "score_breakdown": {
                "semantic": float(round(semantic_score, 2)),
                "skills": float(round(skill_score, 2)),
                "seniority": float(round(seniority_score, 2)),
                "location": float(round(location_score, 2)),
                "experience": float(round(experience_score, 2)),
            },
        }

    def match_jobs(
        self,
        profile: Dict[str, Any],
        profile_embedding: List[float],
        top_n: int = 20,
        min_score: float = 0.0,
    ) -> List[Dict[str, Any]]:
        if not self.job_collection and not self.use_mock:
            logger.error("Job embeddings not available")
            return []

        try:
            if self.use_mock:
                return self._get_mock_matches(profile, profile_embedding, top_n)

            results = self.job_collection.query(
                query_embeddings=[profile_embedding],
                n_results=min(top_n * 3, 150),
                include=["metadatas", "documents", "embeddings", "distances"],
            )

            profile_ctx = self._build_profile_context(profile)
            matches = []
            for i in range(len(results["ids"][0])):
                job_id = results["ids"][0][i]
                job_metadata = results["metadatas"][0][i]
                job_embedding = results["embeddings"][0][i]

                skills_raw = job_metadata.get("skills_extracted", [])
                if isinstance(skills_raw, str):
                    try:
                        skills_raw = json.loads(skills_raw)
                    except (json.JSONDecodeError, TypeError):
                        skills_raw = [s.strip() for s in skills_raw.split(",") if s.strip()]

                job = {
                    "id": job_id,
                    "title": job_metadata.get("title", ""),
                    "company": job_metadata.get("company", ""),
                    "location": job_metadata.get("location", ""),
                    "seniority": job_metadata.get("seniority", ""),
                    "skills_extracted": skills_raw,
                    "salary_min": job_metadata.get("salary_min"),
                    "salary_max": job_metadata.get("salary_max"),
                    "description_raw": results["documents"][0][i] if results.get("documents") else "",
                }

                if self._is_role_too_senior(profile_ctx, job):
                    continue

                score_result = self.compute_fit_score(
                    profile_embedding=profile_embedding,
                    job_embedding=job_embedding,
                    profile=profile,
                    job=job,
                )

                if score_result["fit_score"] < min_score:
                    continue

                matches.append(
                    {
                        "job_id": job_id,
                        "title": job["title"],
                        "company": job["company"],
                        "location": job["location"],
                        "fit_score": score_result["fit_score"],
                        "eligible_for_generation": score_result["eligible_for_generation"],
                        "matched_skills": score_result["matched_skills"],
                        "missing_skills": score_result["missing_skills"],
                        "score_breakdown": score_result["score_breakdown"],
                        "confidence": score_result["confidence"],
                        "match_label": score_result["match_label"],
                        "fit_explanation": score_result["fit_explanation"],
                    }
                )

            matches.sort(key=lambda x: (x["fit_score"], x.get("confidence", 0)), reverse=True)
            return matches[:top_n]

        except Exception as exc:
            logger.error("Error matching jobs: %s", exc)
            return []

    def _get_mock_matches(
        self,
        profile: Dict[str, Any],
        profile_embedding: List[float],
        top_n: int = 20,
    ) -> List[Dict[str, Any]]:
        mock_jobs = [
            {
                "title": "Graduate Data Scientist",
                "company": "Meta",
                "location": "Dublin",
                "seniority": "Entry Level",
                "skills_extracted": ["python", "sql", "pandas"],
                "description_raw": "Entry level graduate role",
            },
            {
                "title": "Junior Backend Engineer",
                "company": "Stripe",
                "location": "Dublin",
                "seniority": "Junior",
                "skills_extracted": ["python", "fastapi", "sql", "docker"],
                "description_raw": "1-2 years experience",
            },
            {
                "title": "Senior Software Engineer",
                "company": "Acme",
                "location": "Remote",
                "seniority": "Senior",
                "skills_extracted": ["go", "kubernetes", "distributed systems"],
                "description_raw": "6+ years required",
            },
        ]

        matches = []
        for idx, job in enumerate(mock_jobs):
            if self._is_role_too_senior(self._build_profile_context(profile), job):
                continue
            scored = self.compute_fit_score(
                profile_embedding=profile_embedding,
                job_embedding=[1.0] * len(profile_embedding),
                profile=profile,
                job=job,
            )
            matches.append(
                {
                    "job_id": f"mock_{idx}",
                    "title": job["title"],
                    "company": job["company"],
                    "location": job["location"],
                    "fit_score": scored["fit_score"],
                    "eligible_for_generation": scored["eligible_for_generation"],
                    "matched_skills": scored["matched_skills"],
                    "missing_skills": scored["missing_skills"],
                    "score_breakdown": scored["score_breakdown"],
                    "confidence": scored["confidence"],
                    "match_label": scored["match_label"],
                    "fit_explanation": scored["fit_explanation"],
                }
            )
        matches.sort(key=lambda x: x["fit_score"], reverse=True)
        return matches[:top_n]

    def get_threshold(self) -> float:
        return float(self.threshold)
