import numpy as np
from typing import List, Dict, Any, Tuple, Optional
import logging
import os

logger = logging.getLogger(__name__)

class MatchEngine:
    """
    Handles matching user profiles with job postings.
    This is Serena's component - implements fit score calculation and 75% gate.
    """
    
    def __init__(
        self, 
        threshold: float = None, 
        persist_directory: str = "./chroma_db", 
        use_mock: bool = False
    ):
        """
        Initialize match engine
        
        Args:
            threshold: Minimum fit score for eligible_for_generation.
                       Defaults to 75% (configurable for testing)
            persist_directory: Directory where ChromaDB data is stored
            use_mock: If True, use mock data for testing (no ChromaDB required)
        """
        # Default threshold is 75%
        if threshold is None:
            threshold = float(os.getenv("GENERATION_THRESHOLD", "75.0"))
        
        self.threshold = threshold
        self.use_mock = use_mock
        
        # Connect to ChromaDB (populated by Vihit's scraper)
        if not use_mock:
            try:
                import chromadb
                self.chroma_client = chromadb.PersistentClient(path=persist_directory)
                
                try:
                    self.job_collection = self.chroma_client.get_collection("job_embeddings")
                    logger.info(f"✅ Loaded job embeddings collection with {self.job_collection.count()} jobs")
                except Exception as e:
                    logger.warning(f"⚠️ Job embeddings collection not found: {e}")
                    logger.warning("   Please run Vihit's scraper to populate job data")
                    self.job_collection = None
            except ImportError:
                logger.warning("⚠️ ChromaDB not installed. Install with: pip install chromadb")
                self.job_collection = None
        else:
            self.job_collection = None
            logger.info("🔧 Using mock mode - no ChromaDB connection")
    
    def compute_fit_score(
        self, 
        profile_embedding: List[float], 
        job_embedding: List[float],
        profile: Dict[str, Any],
        job: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Compute comprehensive fit score between profile and job
        
        Scoring factors:
        - Semantic similarity (25%): Cosine similarity of embeddings
        - Skills match (40%): Overlap between profile and job skills
        - Seniority match (15%): Level alignment (Entry Level, Junior, etc.)
        - Location match (10%): Geographic preference alignment
        - Experience match (10%): Years of experience vs job requirements
        
        Returns:
            Dictionary with fit_score, eligibility flag, and detailed breakdown
        """
        # Convert to numpy arrays
        profile_vec = np.array(profile_embedding)
        job_vec = np.array(job_embedding)
        
        # 1. Semantic similarity (cosine distance)
        dot_product = np.dot(profile_vec, job_vec)
        norm_product = np.linalg.norm(profile_vec) * np.linalg.norm(job_vec)
        cosine_similarity = dot_product / norm_product if norm_product > 0 else 0
        semantic_score = cosine_similarity * 100
        
        # 2. Skill match score
        profile_skills = set([s.lower() for s in profile.get('skills', [])])
        job_skills = set([s.lower() for s in job.get('skills_extracted', [])])
        
        if job_skills:
            matched_skills = profile_skills & job_skills
            missing_skills = job_skills - profile_skills
            skill_score = (len(matched_skills) / len(job_skills)) * 100
        else:
            matched_skills = set()
            missing_skills = set()
            skill_score = 0
        
        # 3. Seniority match
        seniority_levels = {"Entry Level": 1, "Junior": 2, "Mid": 3, "Senior": 4, "Lead": 5}
        profile_seniority = seniority_levels.get(profile.get('seniority_level', 'Entry Level'), 1)
        job_seniority = seniority_levels.get(job.get('seniority', 'Junior'), 2)
        
        seniority_diff = abs(profile_seniority - job_seniority)
        if seniority_diff == 0:
            seniority_score = 100
        elif seniority_diff == 1:
            seniority_score = 70
        else:
            seniority_score = 40
        
        # 4. Location match
        profile_location = profile.get('target_location', '').lower()
        job_location = job.get('location', '').lower()
        
        if profile_location and job_location:
            if profile_location == job_location:
                location_score = 100
            elif 'remote' in job_location or 'remote' in profile_location:
                location_score = 80
            else:
                location_score = 50
        else:
            location_score = 70  # Default if location not specified
        
        # 5. Experience match
        profile_years = profile.get('years_experience', 0)
        job_seniority_str = job.get('seniority', 'Junior')
        
        seniority_to_years = {
            'Entry Level': 0.5,
            'Junior': 2,
            'Mid': 4,
            'Senior': 7,
            'Lead': 10
        }
        expected_years = seniority_to_years.get(job_seniority_str, 2)
        
        if profile_years >= expected_years:
            experience_score = 100
        elif profile_years >= expected_years * 0.7:
            experience_score = 70
        elif profile_years >= expected_years * 0.5:
            experience_score = 50
        else:
            experience_score = 30
        
        # 6. Weighted final score
        weights = {
            'semantic': 0.25,
            'skills': 0.40,
            'seniority': 0.15,
            'location': 0.10,
            'experience': 0.10
        }
        
        fit_score = (
            weights['semantic'] * semantic_score +
            weights['skills'] * skill_score +
            weights['seniority'] * seniority_score +
            weights['location'] * location_score +
            weights['experience'] * experience_score
        )
        
        # Use epsilon to handle floating point rounding issues (74.95% = 75%)
        epsilon = 0.01
        
        return {
            "fit_score": round(fit_score, 2),
            "eligible_for_generation": fit_score >= (self.threshold - epsilon),
            "semantic_score": round(semantic_score, 2),
            "skill_score": round(skill_score, 2),
            "seniority_score": round(seniority_score, 2),
            "location_score": round(location_score, 2),
            "experience_score": round(experience_score, 2),
            "matched_skills": list(matched_skills),
            "missing_skills": list(missing_skills),
            "score_breakdown": {
                "semantic": round(weights['semantic'] * semantic_score, 2),
                "skills": round(weights['skills'] * skill_score, 2),
                "seniority": round(weights['seniority'] * seniority_score, 2),
                "location": round(weights['location'] * location_score, 2),
                "experience": round(weights['experience'] * experience_score, 2)
            }
        }
    
    def match_jobs(
        self, 
        profile: Dict[str, Any], 
        profile_embedding: List[float],
        top_n: int = 20,
        min_score: float = 0.0
    ) -> List[Dict[str, Any]]:
        """
        Find top N matching jobs for a profile
        
        Args:
            profile: UserProfile dictionary
            profile_embedding: Pre-computed profile embedding
            top_n: Number of top matches to return
            min_score: Minimum fit score to include in results
            
        Returns:
            List of match results with scores and details, sorted by fit_score desc
        """
        if not self.job_collection and not self.use_mock:
            logger.error("❌ Job embeddings not available. Please ensure:")
            logger.error("   1. Vihit has populated ChromaDB with job embeddings")
            logger.error("   2. ChromaDB is running")
            logger.error("   3. The 'job_embeddings' collection exists")
            return []
        
        try:
            # If using mock mode, return mock results
            if self.use_mock:
                return self._get_mock_matches(profile, profile_embedding, top_n)
            
            # Query ChromaDB for similar jobs
            results = self.job_collection.query(
                query_embeddings=[profile_embedding],
                n_results=min(top_n * 2, 100),
                include=["metadatas", "documents", "embeddings", "distances"]
            )
            
            matches = []
            
            for i in range(len(results['ids'][0])):
                job_id = results['ids'][0][i]
                job_metadata = results['metadatas'][0][i]
                job_embedding = results['embeddings'][0][i]
                
                # Construct job object from metadata
                job = {
                    'id': job_id,
                    'title': job_metadata.get('title', ''),
                    'company': job_metadata.get('company', ''),
                    'location': job_metadata.get('location', ''),
                    'seniority': job_metadata.get('seniority', ''),
                    'skills_extracted': job_metadata.get('skills_extracted', []),
                    'salary_min': job_metadata.get('salary_min'),
                    'salary_max': job_metadata.get('salary_max'),
                    'description_raw': results['documents'][0][i] if results['documents'] else ''
                }
                
                # Compute fit score
                score_result = self.compute_fit_score(
                    profile_embedding, 
                    job_embedding,
                    profile,
                    job
                )
                
                # Filter by minimum score
                if score_result['fit_score'] >= min_score:
                    matches.append({
                        'job_id': job_id,
                        'title': job['title'],
                        'company': job['company'],
                        'location': job['location'],
                        'fit_score': score_result['fit_score'],
                        'eligible_for_generation': score_result['eligible_for_generation'],
                        'matched_skills': score_result['matched_skills'],
                        'missing_skills': score_result['missing_skills'],
                        'score_breakdown': score_result['score_breakdown']
                    })
            
            # Sort by fit score and return top N
            matches.sort(key=lambda x: x['fit_score'], reverse=True)
            return matches[:top_n]
            
        except Exception as e:
            logger.error(f"❌ Error matching jobs: {e}")
            return []
    
    def _get_mock_matches(
        self, 
        profile: Dict[str, Any], 
        profile_embedding: List[float],
        top_n: int = 20
    ) -> List[Dict[str, Any]]:
        """Generate mock matches for testing (used when use_mock=True)"""
        # This is for testing only - in production, real data from ChromaDB is used
        mock_jobs = [
            {"title": "Data Scientist", "company": "Meta", "location": "Dublin", "seniority": "Entry Level"},
            {"title": "ML Engineer", "company": "OpenAI", "location": "Remote", "seniority": "Junior"},
            {"title": "Software Engineer", "company": "Google", "location": "Dublin", "seniority": "Entry Level"},
            {"title": "Data Analyst", "company": "Stripe", "location": "Dublin", "seniority": "Entry Level"},
            {"title": "Backend Developer", "company": "Shopify", "location": "Remote", "seniority": "Junior"},
        ]
        
        matches = []
        for job in mock_jobs[:top_n]:
            # Simulate fit scores
            import random
            fit_score = random.uniform(60, 85)
            
            matches.append({
                'job_id': f"mock_{job['title'].replace(' ', '_')}",
                'title': job['title'],
                'company': job['company'],
                'location': job['location'],
                'fit_score': round(fit_score, 1),
                'eligible_for_generation': fit_score >= self.threshold,
                'matched_skills': ['python', 'sql', 'machine learning'][:random.randint(2, 4)],
                'missing_skills': ['java', 'react'][:random.randint(0, 2)],
                'score_breakdown': {
                    'semantic': round(fit_score * 0.25, 1),
                    'skills': round(fit_score * 0.4, 1),
                    'seniority': round(fit_score * 0.15, 1),
                    'location': round(fit_score * 0.1, 1),
                    'experience': round(fit_score * 0.1, 1)
                }
            })
        
        matches.sort(key=lambda x: x['fit_score'], reverse=True)
        return matches
    
    def get_job_count(self) -> int:
        """Get total number of jobs in the collection"""
        if self.job_collection:
            try:
                return self.job_collection.count()
            except:
                return 0
        return 0
    
    def get_threshold(self) -> float:
        """Get current generation threshold"""
        return self.threshold
    
    def update_threshold(self, new_threshold: float) -> None:
        """Update generation threshold (useful for A/B testing)"""
        self.threshold = new_threshold
        logger.info(f"Threshold updated to {new_threshold}%")
    
    def get_match_summary(self, matches: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate summary statistics for match results
        
        Args:
            matches: List of match results from match_jobs()
            
        Returns:
            Dictionary with summary statistics
        """
        if not matches:
            return {
                "total_matches": 0,
                "eligible_count": 0,
                "average_score": 0,
                "highest_score": 0,
                "lowest_score": 0
            }
        
        scores = [m['fit_score'] for m in matches]
        eligible = sum(1 for m in matches if m['eligible_for_generation'])
        
        return {
            "total_matches": len(matches),
            "eligible_count": eligible,
            "average_score": round(sum(scores) / len(scores), 1),
            "highest_score": max(scores),
            "lowest_score": min(scores),
            "threshold": self.threshold
        }


# Convenience function for API integration
def create_match_engine(threshold: float = 75.0) -> MatchEngine:
    """Factory function to create a match engine instance with 75% default threshold"""
    return MatchEngine(threshold=threshold)


# Example usage for testing
if __name__ == "__main__":
    # This is for quick testing - in production, use test_match_engine.py
    print("Match Engine Module")
    print("=" * 50)
    print(f"Default threshold: 75%")
    print("To test the match engine, run: python3 nlp/test_match_engine.py")
    print("\nKey Features:")
    print("  ✅ Configurable threshold (default 75%)")
    print("  ✅ Weighted fit score calculation")
    print("  ✅ Skill gap analysis (matched/missing skills)")
    print("  ✅ Eligibility gate for generation")
    print("  ✅ ChromaDB integration (populated by Vihit)")
    print("  ✅ Mock mode for testing")