# cv_parser.py - Complete Universal CV Parser with JSON Databases
import re
import json
import uuid
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
from datetime import datetime
import logging

import pdfplumber
from docx import Document

logger = logging.getLogger(__name__)
CURRENT_YEAR = datetime.now().year

# Load skill and job title databases
BASE_DIR = Path(__file__).parent

def load_skills_db():
    """Load skills from JSON file"""
    try:
        with open(BASE_DIR / "skills_db.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        all_skills = []
        for category, skills in data.items():
            all_skills.extend([skill.lower() for skill in skills])
        return list(set(all_skills))
    except Exception as e:
        logger.error(f"Error loading skills DB: {e}")
        return []

def load_job_titles_db():
    """Load job titles from JSON file"""
    try:
        with open(BASE_DIR / "job_titles_db.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        all_titles = []
        for category, titles in data.items():
            all_titles.extend([title.lower() for title in titles])
        return list(set(all_titles))
    except Exception as e:
        logger.error(f"Error loading job titles DB: {e}")
        return []

SKILLS_DB = load_skills_db()
JOB_TITLES_DB = load_job_titles_db()
logger.info(f"Loaded {len(SKILLS_DB)} skills and {len(JOB_TITLES_DB)} job titles")

def clean_text(text: str) -> str:
    """Clean text by adding spaces where needed"""
    text = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)
    text = re.sub(r'(Developer|Intern|Engineer|Analyst|Manager|Scientist|Specialist|Assistant)([A-Z]|$)', r'\1 \2', text)
    text = text.replace('Pythonand', 'Python and')
    text = text.replace('DjangoDeveloper', 'Django Developer')
    text = text.replace('(Remote)', ' (Remote)')
    text = re.sub(r'(Pvt\.?)(Ltd\.?)', r'\1 \2', text, flags=re.IGNORECASE)
    text = re.sub(r'([A-Za-z])(Ltd\.?|Inc\.?|Corp\.?)', r'\1 \2', text, flags=re.IGNORECASE)
    return text.strip()

def extract_text_from_file(file_path: str) -> str:
    """Extract text from PDF or DOCX"""
    text = ""
    try:
        if file_path.lower().endswith(".pdf"):
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
        elif file_path.lower().endswith(".docx"):
            doc = Document(file_path)
            for para in doc.paragraphs:
                if para.text:
                    text += para.text + "\n"
    except Exception as e:
        logger.error(f"Error extracting text: {e}")
    return text.strip()

def extract_name(text: str, lines: List[str]) -> str:
    """Extract name from CV"""
    for line in lines[:10]:
        line = line.strip()
        if line and not any(x in line.lower() for x in ['email', 'phone', 'linkedin', 'github', 'date of birth', 'nationality', 'address']):
            words = line.split()
            if 2 <= len(words) <= 5:
                if not line.isupper() and not any(x in line.lower() for x in ['education', 'experience', 'skills']):
                    return line
    return ""

def extract_contact_info(text: str) -> Dict:
    """Extract email, phone, LinkedIn, GitHub"""
    email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', text)
    email = email_match.group() if email_match else ""
    
    phone_patterns = [
        r'\+353\d{9}',
        r'\+353\s?\d{2}\s?\d{3}\s?\d{4}',
        r'\+316\s?\d{4}\s?\d{4}',
        r'0\d{9,10}',
        r'\+\d{1,3}[\s\-]?\d{4,10}',
    ]
    phone = ""
    for pattern in phone_patterns:
        match = re.search(pattern, text)
        if match:
            phone = match.group()
            break
    
    linkedin_match = re.search(r'linkedin\.com/in/[\w\-]+', text, re.IGNORECASE)
    linkedin = f"https://{linkedin_match.group()}" if linkedin_match else ""
    
    github_match = re.search(r'github\.com/[\w\-]+', text, re.IGNORECASE)
    github = f"https://{github_match.group()}" if github_match else ""
    
    return {"email": email, "phone": phone, "linkedin": linkedin, "github": github}

def extract_skills(text: str) -> List[str]:
    """Extract skills from text using skills_db.json with precise matching"""
    skills_found = []
    text_lower = text.lower()
    
    # Split into words for better matching
    words = set(re.findall(r'\b[a-z][a-z0-9\+\.#]+\b', text_lower))
    
    for skill in SKILLS_DB:
        skill_lower = skill.lower()
        
        # For single-word skills
        if ' ' not in skill_lower:
            if skill_lower in words:
                skills_found.append(skill)
        # For multi-word skills
        else:
            if skill_lower in text_lower:
                pattern = r'\b' + re.escape(skill_lower) + r'\b'
                if re.search(pattern, text_lower):
                    skills_found.append(skill)
    
    # Remove false positives
    false_positives = [
        'irish', 'dublin', 'ireland', 'looking', 'software', 'engineering', 'roles',
        'graduate', 'student', 'trinity', 'college', 'university', 'semester',
        'cgpa', 'gpa', 'thesis', 'project', 'internship', 'experience', 'data',
        'science', 'computer', 'machine', 'learning', 'artificial', 'intelligence'
    ]
    
    skills_found = [s for s in skills_found if s.lower() not in false_positives]
    
    return sorted(list(set(skills_found)))

def extract_education(text: str, lines: List[str]) -> List[Dict]:
    """Extract education information"""
    education = []
    
    edu_start = -1
    for i, line in enumerate(lines):
        line_stripped = line.strip()
        if line_stripped == 'Education' or line_stripped == 'EDUCATION':
            edu_start = i
            break
    
    if edu_start == -1:
        for i, line in enumerate(lines):
            if 'education' in line.lower() and len(line) < 30:
                edu_start = i
                break
    
    if edu_start != -1:
        edu_end = len(lines)
        for j in range(edu_start + 1, len(lines)):
            line_stripped = lines[j].strip()
            if line_stripped in ['Experience', 'Professional Experience', 'Work Experience', 'Skills', 'Projects', 'Internships']:
                edu_end = j
                break
        
        edu_lines = lines[edu_start + 1:edu_end]
        
        degree_patterns = [
            (r'Master|MSc|M\.Sc|Master of Science', 'MSc'),
            (r'Bachelor|BSc|B\.Sc|Bachelor of Science', 'BSc'),
            (r'B\.Tech|Bachelor of Technology', 'B.Tech'),
            (r'PhD|Ph\.D|Doctor of Philosophy', 'PhD'),
            (r'MBA|Master of Business Administration', 'MBA'),
            (r'Diploma', 'Diploma'),
            (r'Grammar School|Secondary School', 'Secondary School'),
        ]
        
        for line in edu_lines:
            line = line.strip()
            if not line or len(line) < 5:
                continue
            
            for pattern, degree in degree_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    year_match = re.search(r'(20\d{2})', line)
                    year = int(year_match.group(1)) if year_match else None
                    
                    university = ""
                    uni_match = re.search(r'(Trinity College|Vellore Institute|University|College|Institute)', line, re.IGNORECASE)
                    if uni_match:
                        university = uni_match.group(0)
                    
                    education.append({
                        "degree": degree,
                        "university": university,
                        "year": year,
                        "raw_text": line
                    })
                    break
    
    return education

def extract_experiences(text: str, lines: List[str]) -> Tuple[List[Dict], float, List[str]]:
    """Extract work experiences and calculate years"""
    experiences = []
    
    # Find experience section
    exp_start = -1
    for i, line in enumerate(lines):
        line_stripped = line.strip().upper()
        if any(header in line_stripped for header in ['WORK EXPERIENCE', 'PROFESSIONAL EXPERIENCE', 'EXPERIENCE', 'INTERNSHIPS']):
            if len(line) < 50:
                exp_start = i
                logger.info(f"Found Experience section at line {i}: {line}")
                break
    
    if exp_start != -1:
        exp_end = len(lines)
        for j in range(exp_start + 1, len(lines)):
            line_stripped = lines[j].strip().upper()
            if len(lines[j]) < 50 and any(header in line_stripped for header in ['EDUCATION', 'PROJECTS', 'SKILLS', 'PUBLICATIONS', 'CERTIFICATIONS']):
                exp_end = j
                break
        
        exp_lines = lines[exp_start + 1:exp_end]
        logger.info(f"Found {len(exp_lines)} experience lines")
        
        # Debug: Print first 15 lines
        logger.info("First 15 experience lines:")
        for idx, line in enumerate(exp_lines[:15]):
            logger.info(f"  {idx}: {line[:100]}")
        
        month_map = {
            'jan': 1, 'january': 1, 'feb': 2, 'february': 2, 'mar': 3, 'march': 3,
            'apr': 4, 'april': 4, 'may': 5, 'jun': 6, 'june': 6, 'jul': 7, 'july': 7,
            'aug': 8, 'august': 8, 'sep': 9, 'september': 9, 'oct': 10, 'october': 10,
            'nov': 11, 'november': 11, 'dec': 12, 'december': 12
        }
        
        i = 0
        while i < len(exp_lines):
            line = exp_lines[i].strip()
            if not line:
                i += 1
                continue
            
            # Pattern for Vihit's format: "Company, Location MonthYear–MonthYear" (no spaces between month and year)
            # Example: "AltissAdvanceTechnologiesPvt.Ltd.,Mumbai Jun2024–Nov2024"
            vihit_pattern = r'([A-Za-z\s.&]+(?:Technologies|Solutions|Pvt\.?\s*Ltd\.?|Ltd\.?|Inc\.?|Corp\.?)),?\s*[A-Za-z]+\s+([A-Za-z]{3,})(\d{4})\s*[–-]\s*([A-Za-z]{3,})(\d{4})'
            vihit_match = re.search(vihit_pattern, line, re.IGNORECASE)
            
            if vihit_match:
                company = vihit_match.group(1).strip()
                start_month_str = vihit_match.group(2)
                start_year = int(vihit_match.group(3))
                end_month_str = vihit_match.group(4)
                end_year = int(vihit_match.group(5))
                
                start_month = month_map.get(start_month_str.lower()[:3], 1)
                end_month = month_map.get(end_month_str.lower()[:3], 12)
                company = clean_text(company)
                
                # Get role from the NEXT line
                role = ""
                if i + 1 < len(exp_lines):
                    next_line = exp_lines[i + 1].strip()
                    if next_line and not next_line.startswith('•') and not next_line.startswith('-'):
                        role = next_line
                        role = clean_text(role)
                        i += 1  # Skip the role line
                
                # Collect description (bullet points)
                description = []
                j = i + 1
                while j < len(exp_lines) and j < i + 12:
                    next_line = exp_lines[j].strip()
                    if re.search(vihit_pattern, next_line, re.IGNORECASE):
                        break
                    if next_line.startswith('•') or next_line.startswith('-') or next_line.startswith('*'):
                        clean = re.sub(r'^[•\-*]\s*', '', next_line)
                        description.append(clean)
                    elif not next_line:
                        break
                    j += 1
                
                if role:
                    experiences.append({
                        'role': role,
                        'company': company,
                        'start_year': start_year,
                        'end_year': end_year,
                        'start_month': start_month,
                        'end_month': end_month,
                        'description': '\n'.join(description)
                    })
                    logger.info(f"Found (Vihit): {role} at {company} ({start_year}-{end_year})")
                    i = j
                    continue
            
            # Pattern for Serena's format: "Web Developer – Qressy Solutions Pvt. Ltd. Feb 2025 – Jul 2025"
            serena_pattern = r'([A-Za-z/\s&]+?)\s*[–-]\s*([A-Za-z\s.&]+(?:Pvt\.?\s*Ltd\.?|Ltd\.?|Inc\.?|Corp\.?)?)\s+([A-Za-z]{3,})\s+(\d{4})\s*[–-]\s*([A-Za-z]{3,})\s+(\d{4})'
            serena_match = re.search(serena_pattern, line, re.IGNORECASE)
            
            if serena_match:
                role = serena_match.group(1).strip()
                company = serena_match.group(2).strip()
                start_month = month_map.get(serena_match.group(3).lower()[:3], 1)
                start_year = int(serena_match.group(4))
                end_month = month_map.get(serena_match.group(5).lower()[:3], 12)
                end_year = int(serena_match.group(6))
                
                role = clean_text(role)
                company = clean_text(company)
                
                description = []
                j = i + 1
                while j < len(exp_lines) and j < i + 12:
                    next_line = exp_lines[j].strip()
                    if re.search(serena_pattern, next_line, re.IGNORECASE):
                        break
                    if next_line.startswith('•') or next_line.startswith('-') or next_line.startswith('*'):
                        clean = re.sub(r'^[•\-*]\s*', '', next_line)
                        description.append(clean)
                    elif not next_line:
                        break
                    j += 1
                
                experiences.append({
                    'role': role,
                    'company': company,
                    'start_year': start_year,
                    'end_year': end_year,
                    'start_month': start_month,
                    'end_month': end_month,
                    'description': '\n'.join(description)
                })
                logger.info(f"Found (Serena): {role} at {company} ({start_year}-{end_year})")
                i = j
                continue
            
            # Pattern for: "AI/ML – Intrain Tech. Oct 2023 - Nov 2023" (dates with spaces)
            alt_pattern = r'^([A-Za-z/\s]+)[–-]([A-Za-z\s.]+)\s+([A-Za-z]{3,})\s+(\d{4})\s*[–-]\s*([A-Za-z]{3,})\s+(\d{4})'
            alt_match = re.search(alt_pattern, line, re.IGNORECASE)
            
            if alt_match:
                role = alt_match.group(1).strip()
                company = alt_match.group(2).strip()
                start_month = month_map.get(alt_match.group(3).lower()[:3], 1)
                start_year = int(alt_match.group(4))
                end_month = month_map.get(alt_match.group(5).lower()[:3], 12)
                end_year = int(alt_match.group(6))
                
                role = clean_text(role)
                company = clean_text(company)
                
                description = []
                j = i + 1
                while j < len(exp_lines) and j < i + 10:
                    next_line = exp_lines[j].strip()
                    if re.search(alt_pattern, next_line, re.IGNORECASE):
                        break
                    if next_line.startswith('•') or next_line.startswith('-') or next_line.startswith('*'):
                        clean = re.sub(r'^[•\-*]\s*', '', next_line)
                        description.append(clean)
                    elif not next_line:
                        break
                    j += 1
                
                experiences.append({
                    'role': role,
                    'company': company,
                    'start_year': start_year,
                    'end_year': end_year,
                    'start_month': start_month,
                    'end_month': end_month,
                    'description': '\n'.join(description)
                })
                logger.info(f"Found (Alt): {role} at {company} ({start_year}-{end_year})")
                i = j
                continue
            
            i += 1
    
    # Calculate total years
    total_years = 0.0
    for exp in experiences:
        if exp['start_year'] == exp['end_year']:
            months_diff = exp['end_month'] - exp['start_month'] + 1
            years = months_diff / 12.0
        else:
            years_diff = exp['end_year'] - exp['start_year']
            months_diff = (12 - exp['start_month'] + 1) + exp['end_month']
            years = years_diff - 1 + (months_diff / 12.0)
        exp['years'] = round(years, 2)
        total_years += years
    
    total_years = round(total_years, 1)
    
    job_titles = list(set([exp['role'] for exp in experiences if exp.get('role')]))
    
    return experiences, total_years, job_titles

def parse_cv(file_path: str, preferences_text: str = "") -> Dict:
    """
    Universal CV parser that handles all formats and returns complete UserProfile
    """
    # Extract text from CV only (without preferences)
    cv_text = extract_text_from_file(file_path)
    if not cv_text:
        raise ValueError("Could not extract text from CV")
    
    logger.info(f"Extracted {len(cv_text)} characters from CV")
    
    lines = cv_text.split('\n')
    
    # Extract all components - using only CV text, not preferences
    name = extract_name(cv_text, lines)
    contact = extract_contact_info(cv_text)
    skills = extract_skills(cv_text)
    education = extract_education(cv_text, lines)
    experiences, total_years, job_titles = extract_experiences(cv_text, lines)
    
    # Determine seniority
    if total_years < 1:
        seniority = "Entry Level"
    elif total_years < 3:
        seniority = "Junior"
    elif total_years < 5:
        seniority = "Mid"
    else:
        seniority = "Senior"
    
    # Extract target role and location from preferences
    target_role = ""
    target_location = ""
    if preferences_text:
        pref_lower = preferences_text.lower()
        roles = ['software engineer', 'data scientist', 'data engineer', 'ml engineer', 
                 'backend developer', 'frontend developer', 'full stack developer']
        for role in roles:
            if role in pref_lower:
                target_role = role.title()
                break
        
        locations = ['dublin', 'cork', 'galway', 'limerick', 'waterford', 'remote', 'amsterdam']
        for loc in locations:
            if loc in pref_lower:
                target_location = loc.title()
                break
    
    # Build complete profile
    profile = {
        "id": str(uuid.uuid4()),
        "name": name,
        "email": contact["email"],
        "phone": contact["phone"],
        "linkedin": contact["linkedin"],
        "github": contact["github"],
        "skills": skills,
        "job_titles": job_titles,
        "experiences": experiences,
        "years_experience": total_years,
        "seniority_level": seniority,
        "education": education,
        "preferences_raw": preferences_text,
        "target_role": target_role,
        "target_location": target_location,
        "salary_expectation_min": None,
        "created_at": datetime.now().isoformat()
    }
    
    logger.info(f"Parsed: {len(skills)} skills, {len(job_titles)} job titles, {total_years} years")
    return profile