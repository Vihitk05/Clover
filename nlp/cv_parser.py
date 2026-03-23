import pdfplumber
from docx import Document
import re
from typing import Dict

def extract_text_from_pdf(file_path: str) -> str:
    text = ""
    try:
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
    except Exception as e:
        print(f"Error extracting text from pdf: {e}")
    return text.strip()


def extract_text_from_docx(file_path: str) -> str:
    text = ""
    try:
        doc = Document(file_path)
        for para in doc.paragraphs:
            if para.text:
                text += para.text + "\n"
    except Exception as e:
        print(f"Error extracting text from docx: {e}")
    return text.strip()


def extract_text(file_path: str) -> str:
    if file_path.lower().endswith(".pdf"):
        return extract_text_from_pdf(file_path)
    elif file_path.lower().endswith(".docx"):
        return extract_text_from_docx(file_path)
    else:
        raise ValueError("Unsupported file type. Only PDF and DOCX are allowed.")


def extract_basic_info(text: str) -> Dict:
    email_match = re.findall(r"[\w\.-]+@[\w\.-]+", text)
    email = email_match[0] if email_match else ""

    lines = [line.strip() for line in text.split("\n") if line.strip()]

    name = ""
    for line in lines[:5]:  # check first few lines
        if "@" not in line and len(line.split()) <= 4:
            name = line
            break

    return {
        "name": name,
        "email": email
    }


COMMON_SKILLS = [
    "python", "java", "c++", "sql", "machine learning",
    "deep learning", "nlp", "pandas", "numpy",
    "tensorflow", "pytorch", "excel", "power bi",
    "tableau", "aws", "docker", "kubernetes"
]


def extract_entities(text: str) -> Dict:
    text_lower = text.lower()

    skills_found = []
    for skill in COMMON_SKILLS:
        if skill in text_lower:
            skills_found.append(skill.title())

    return {
        "skills": list(set(skills_found)),
        "job_titles": [],
        "companies": [],
        "dates": []
    }


def estimate_years_experience(text: str) -> int:
    years = re.findall(r"(20\d{2})", text)
    years = sorted(set(map(int, years)))

    if len(years) >= 2:
        return min(years[-1] - years[0], 15)

    return 0


def determine_seniority(years_experience: int) -> str:
    if years_experience < 2:
        return "Junior"
    elif years_experience < 5:
        return "Mid"
    else:
        return "Senior"


def build_user_profile_json(
    entities: Dict,
    basic_info: Dict,
    text: str,
    preferences_text: str
) -> Dict:

    years_experience = estimate_years_experience(text)
    seniority = determine_seniority(years_experience)

    return {
        "id": "",  # assigned later in backend
        "name": basic_info.get("name", ""),
        "email": basic_info.get("email", ""),
        "skills": entities.get("skills", []),
        "job_titles": entities.get("job_titles", []),
        "years_experience": years_experience,
        "seniority_level": seniority,
        "education": [],
        "preferences_raw": preferences_text,
        "target_role": "",
        "target_location": "",
        "salary_expectation_min": None
    }


def parse_cv(file_path: str, preferences_text: str) -> Dict:
    text = extract_text(file_path)

    if not text:
        raise ValueError(
            "Could not extract text from CV. Ensure it is not a scanned PDF."
        )

    print(f"Extracted text length: {len(text)}")

    basic_info = extract_basic_info(text)
    entities = extract_entities(text)

    user_profile = build_user_profile_json(
        entities,
        basic_info,
        text,
        preferences_text
    )

    return user_profile