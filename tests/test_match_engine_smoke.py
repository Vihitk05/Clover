from nlp.match_engine import MatchEngine


def test_match_engine_fit_score_smoke():
    engine = MatchEngine(threshold=80, use_mock=True)

    profile = {
        "skills": ["Python", "FastAPI", "SQL"],
        "seniority_level": "Mid",
        "target_location": "Dublin",
        "years_experience": 3,
    }
    job = {
        "skills_extracted": ["Python", "SQL", "Docker"],
        "seniority": "Mid",
        "location": "Dublin",
    }

    result = engine.compute_fit_score(
        profile_embedding=[1.0, 0.0, 0.0],
        job_embedding=[1.0, 0.0, 0.0],
        profile=profile,
        job=job,
    )

    assert result["fit_score"] > 0
    assert "python" in [skill.lower() for skill in result["matched_skills"]]
    assert "docker" in [skill.lower() for skill in result["missing_skills"]]
