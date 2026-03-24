# nlp/test_match_engine.py
import json
import sys
import shutil
from pathlib import Path
import logging

sys.path.append(str(Path(__file__).parent.parent))

from nlp.cv_parser import parse_cv
from nlp.embedder import ProfileEmbedder
from nlp.match_engine import MatchEngine

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def create_mock_jobs(force_recreate=True):
    """Create mock job data for testing with local embeddings"""
    
    print("\n📝 Creating mock job data for testing...")
    
    try:
        import chromadb
        from sentence_transformers import SentenceTransformer
        
        # Use same local model for consistency
        model = SentenceTransformer('all-MiniLM-L6-v2')
        
        client = chromadb.PersistentClient(path="./chroma_db")
        
        # Delete the collection if it exists (regardless of force_recreate)
        try:
            client.delete_collection("job_embeddings")
            print("   ✅ Deleted existing job collection")
        except:
            print("   No existing collection to delete")
        
        # Create new collection
        collection = client.create_collection(
            name="job_embeddings",
            metadata={"hnsw:space": "cosine"}
        )
        print("   ✅ Created new job collection")
        
        # Comprehensive mock job data - 15 jobs for better variety
        mock_jobs = [
            {
                "title": "Graduate Data Scientist",
                "company": "LinkedIn",
                "location": "Dublin",
                "seniority": "Entry Level",
                "skills_extracted": ["Python", "Machine Learning", "SQL", "Pandas", "NumPy", "Scikit-learn", "Tableau", "NLP", "Deep Learning", "Data Visualization"],
                "description": "Graduate data scientist role for recent MSc graduates."
            },
            {
                "title": "Junior Data Scientist",
                "company": "Meta",
                "location": "Dublin",
                "seniority": "Entry Level",
                "skills_extracted": ["Python", "Machine Learning", "SQL", "Pandas", "NLP", "Data Visualization", "Tableau", "Deep Learning"],
                "description": "Entry-level data scientist role focusing on ML and NLP."
            },
            {
                "title": "AI/ML Graduate Program",
                "company": "Google",
                "location": "Dublin",
                "seniority": "Entry Level",
                "skills_extracted": ["Python", "Machine Learning", "SQL", "Pandas", "NumPy", "Scikit-learn", "NLP"],
                "description": "Graduate program for AI/ML engineers."
            },
            {
                "title": "Software Engineer (Graduate)",
                "company": "Microsoft",
                "location": "Dublin",
                "seniority": "Entry Level",
                "skills_extracted": ["Python", "JavaScript", "HTML", "CSS", "Flask", "Git", "SQL"],
                "description": "Graduate software engineer position."
            },
            {
                "title": "Data Analyst",
                "company": "Stripe",
                "location": "Dublin",
                "seniority": "Entry Level",
                "skills_extracted": ["Python", "SQL", "Tableau", "Excel", "Data Visualization", "Pandas"],
                "description": "Data analyst role focusing on business intelligence."
            },
            {
                "title": "Full Stack Developer (Graduate)",
                "company": "Shopify",
                "location": "Dublin",
                "seniority": "Entry Level",
                "skills_extracted": ["Python", "JavaScript", "HTML", "CSS", "Flask", "React", "Git"],
                "description": "Graduate full-stack developer position."
            },
            {
                "title": "ML Engineer",
                "company": "OpenAI",
                "location": "Remote",
                "seniority": "Junior",
                "skills_extracted": ["Python", "PyTorch", "TensorFlow", "NLP", "Deep Learning", "Transformers"],
                "description": "ML Engineer for AI model development."
            },
            {
                "title": "Backend Developer",
                "company": "Stripe",
                "location": "Dublin",
                "seniority": "Junior",
                "skills_extracted": ["Python", "Flask", "FastAPI", "PostgreSQL", "REST API", "Git"],
                "description": "Backend developer for payment processing."
            },
            {
                "title": "Frontend Developer",
                "company": "Shopify",
                "location": "Dublin",
                "seniority": "Junior",
                "skills_extracted": ["JavaScript", "React", "HTML", "CSS", "Git", "TypeScript"],
                "description": "Frontend developer for e-commerce platform."
            },
            {
                "title": "AI Research Intern",
                "company": "Hugging Face",
                "location": "Remote",
                "seniority": "Entry Level",
                "skills_extracted": ["Python", "Transformers", "NLP", "Deep Learning", "PyTorch"],
                "description": "Research internship focusing on NLP and transformer models."
            },
            {
                "title": "Data Engineer",
                "company": "Snowflake",
                "location": "Dublin",
                "seniority": "Entry Level",
                "skills_extracted": ["Python", "SQL", "ETL", "Data Warehousing", "Spark", "Airflow"],
                "description": "Data engineer role building data pipelines."
            },
            {
                "title": "DevOps Engineer",
                "company": "GitHub",
                "location": "Remote",
                "seniority": "Junior",
                "skills_extracted": ["Python", "Docker", "Kubernetes", "AWS", "CI/CD", "Git", "Linux"],
                "description": "DevOps engineer for cloud infrastructure."
            },
            {
                "title": "Product Analyst",
                "company": "Intercom",
                "location": "Dublin",
                "seniority": "Entry Level",
                "skills_extracted": ["Python", "SQL", "Tableau", "Excel", "A/B Testing", "Product Analytics"],
                "description": "Product analyst role for SaaS company."
            },
            {
                "title": "Machine Learning Intern",
                "company": "Hugging Face",
                "location": "Remote",
                "seniority": "Entry Level",
                "skills_extracted": ["Python", "Transformers", "NLP", "PyTorch", "TensorFlow", "Deep Learning"],
                "description": "ML internship focusing on open-source AI."
            },
            {
                "title": "Technical Support Engineer",
                "company": "Datadog",
                "location": "Dublin",
                "seniority": "Entry Level",
                "skills_extracted": ["Python", "Linux", "SQL", "Docker", "Kubernetes", "AWS", "Monitoring"],
                "description": "Technical support for cloud monitoring platform."
            }
        ]
        
        for i, job in enumerate(mock_jobs):
            text_to_embed = f"{job['title']} at {job['company']}. Skills: {', '.join(job['skills_extracted'])}"
            embedding = model.encode(text_to_embed).tolist()
            
            collection.add(
                embeddings=[embedding],
                metadatas=[{
                    "title": job["title"],
                    "company": job["company"],
                    "location": job["location"],
                    "seniority": job["seniority"],
                    "skills_extracted": job["skills_extracted"]
                }],
                documents=[job["description"]],
                ids=[f"job_{i}"]
            )
        
        print(f"   ✅ Created {len(mock_jobs)} mock jobs with local embeddings")
        return len(mock_jobs)
        
    except ImportError as e:
        print(f"   ❌ sentence-transformers not installed. Install with: pip install sentence-transformers")
        return 0
    except Exception as e:
        print(f"   ❌ Error creating mock jobs: {e}")
        return 0

def test_match_engine():
    """Test the complete matching pipeline"""
    
    # Update this path to your CV
    cv_path = "/Users/serenamendanha/Desktop/Resume_general.pdf"
    preferences = "Looking for software engineering roles in Dublin"
    
    print("="*70)
    print("JOBFIT AI - MATCH ENGINE TEST")
    print("="*70)
    
    # Step 1: Parse CV
    print("\n📄 STEP 1: Parsing CV...")
    profile = parse_cv(cv_path, preferences)
    print(f"   ✅ Name: {profile['name']}")
    print(f"   📊 Skills: {len(profile['skills'])}")
    print(f"   💼 Job Titles: {len(profile['job_titles'])}")
    print(f"   ⏰ Experience: {profile['years_experience']} years")
    print(f"   📍 Seniority: {profile['seniority_level']}")
    print(f"   🎯 Target Role: {profile['target_role']}")
    print(f"   📍 Target Location: {profile['target_location']}")
    
    # Step 2: Embed Profile
    print("\n🔢 STEP 2: Generating Profile Embedding...")
    embedder = ProfileEmbedder(use_local_model=True)
    profile_embedding = embedder.embed_profile(profile)
    print(f"   ✅ Embedding dimension: {len(profile_embedding)}")
    
    # Step 3: Create fresh job database
    print("\n💼 STEP 3: Creating Fresh Job Database...")
    job_count = create_mock_jobs(force_recreate=True)
    print(f"   📊 Jobs created: {job_count}")
    
    if job_count == 0:
        print("\n❌ No jobs available. Cannot proceed with matching.")
        return
    
    # Step 4: Initialize match engine
    match_engine = MatchEngine(threshold=75)
    
    # Step 5: Match Jobs
    print(f"\n🎯 STEP 4: Matching Jobs (Threshold: {match_engine.threshold}%)...")
    matches = match_engine.match_jobs(profile, profile_embedding, top_n=15)
    
    print(f"\n   Found {len(matches)} matches")
    
    if matches:
        print("\n" + "="*70)
        print("TOP MATCH RESULTS")
        print("="*70)
        
        for i, match in enumerate(matches[:15], 1):
            status = "✅ ELIGIBLE" if match['eligible_for_generation'] else "❌ NOT ELIGIBLE"
            
            print(f"\n{i}. {match['title']} at {match['company']}")
            print(f"   📍 {match['location']}")
            print(f"   ⭐ Fit Score: {match['fit_score']:.1f}%")
            print(f"   🚦 Status: {status}")
            print(f"   ✅ Matched Skills ({len(match['matched_skills'])}): {', '.join(match['matched_skills'][:6])}")
            if len(match['matched_skills']) > 6:
                print(f"      ... and {len(match['matched_skills']) - 6} more")
            if match['missing_skills']:
                print(f"   ❌ Missing Skills ({len(match['missing_skills'])}): {', '.join(match['missing_skills'][:6])}")
                if len(match['missing_skills']) > 6:
                    print(f"      ... and {len(match['missing_skills']) - 6} more")
    
    # Step 6: Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    
    eligible_count = sum(1 for m in matches if m['eligible_for_generation'])
    total_matches = len(matches)
    
    print(f"Total Jobs Analyzed: {total_matches}")
    print(f"Eligible for Generation (≥{match_engine.threshold}%): {eligible_count}")
    
    if eligible_count > 0:
        print(f"\n✅ {eligible_count} jobs qualify for CV/cover letter generation!")
        print("\n   Eligible Jobs:")
        for m in matches:
            if m['eligible_for_generation']:
                print(f"   • {m['title']} at {m['company']} - {m['fit_score']:.1f}%")
    else:
        print(f"\n⚠️ No jobs above {match_engine.threshold}% threshold.")
        
        if matches:
            print(f"\n   Closest matches:")
            for m in matches[:3]:
                print(f"   • {m['title']} at {m['company']}: {m['fit_score']:.1f}%")
    
    # Step 7: Score Distribution
    if matches:
        print("\n" + "="*70)
        print("SCORE DISTRIBUTION")
        print("="*70)
        scores = [m['fit_score'] for m in matches]
        print(f"Highest Score: {max(scores):.1f}%")
        print(f"Average Score: {sum(scores)/len(scores):.1f}%")
        print(f"Lowest Score: {min(scores):.1f}%")
    
    # Step 8: What If Analysis
    print("\n" + "="*70)
    print("WHAT IF ANALYSIS")
    print("="*70)
    
    thresholds = [90, 85, 80, 75, 70, 65, 60]
    print("\nEligible jobs at different thresholds:")
    print("-"*50)
    
    for thresh in thresholds:
        engine = MatchEngine(threshold=thresh)
        thresh_matches = engine.match_jobs(profile, profile_embedding, top_n=15)
        thresh_eligible = sum(1 for m in thresh_matches if m['eligible_for_generation'])
        print(f"   Threshold {thresh}%: {thresh_eligible} eligible jobs")
    
    # Step 9: Save Results
    output_file = 'match_results.json'
    with open(output_file, 'w') as f:
        json.dump(matches, f, indent=2, default=str)
    print(f"\n💾 Full match results saved to: {output_file}")
    
    print("\n" + "="*70)
    print("✅ TEST COMPLETE")
    print("="*70)

if __name__ == "__main__":
    test_match_engine()