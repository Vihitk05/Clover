from nlp.cv_parser import extract_contact_info, extract_skills


def test_cv_parser_extracts_contact_info():
    text = """
    Jane Doe
    jane@example.com
    +353871234567
    linkedin.com/in/janedoe
    github.com/janedoe
    """

    result = extract_contact_info(text)

    assert result["email"] == "jane@example.com"
    assert result["phone"] == "+353871234567"
    assert result["linkedin"].endswith("/janedoe")
    assert result["github"].endswith("/janedoe")


def test_cv_parser_extracts_known_skills():
    text = "Experienced Python engineer using FastAPI, SQL, Docker, and Git."

    skills = extract_skills(text)

    lowered = {skill.lower() for skill in skills}
    assert "python" in lowered
    assert "fastapi" in lowered
