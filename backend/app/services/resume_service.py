"""
services/resume_service.py — Resume Upload, Parse & Analysis Pipeline
=======================================================================
This service orchestrates the complete resume processing pipeline:

  1. Parse PDF → extract raw text (PyMuPDF)
  2. Detect sections (education, experience, skills, projects)
  3. Extract structured data from each section
  4. Determine experience level from years found
  5. Save everything to the database
  6. Upload original file to IBM Cloud Object Storage
  7. Return analysis to the route

This is called by routes/resume.py → POST /resume/upload
"""

import json
import os
import re
from typing import Optional
from sqlalchemy.orm import Session

from app.models.interview import Resume
from app.schemas.interview import ResumeAnalysis
from app.services.resume_parser import extract_text_from_pdf, get_pdf_metadata
from app.services.section_extractor import extract_sections, get_candidate_name
from app.utils.cos_client import cos_client
from app.utils.logger import logger
from app.utils.exceptions import ResumeParseError


def parse_and_analyze_resume(
    file_path: str,
    user_id: int,
    db: Session,
    job_title: Optional[str] = None,
) -> ResumeAnalysis:
    """
    Full resume processing pipeline.

    Args:
        file_path : local path to the saved PDF file
        user_id   : ID of the authenticated user
        db        : SQLAlchemy database session
        job_title : optional target job title

    Returns:
        ResumeAnalysis schema with all extracted data
    """
    filename = os.path.basename(file_path)
    logger.info(f"Processing resume: {filename} for user {user_id}")

    # ── Step 1: Extract raw text from PDF ─────────────────────────────────────
    parsed_text = extract_text_from_pdf(file_path)
    metadata    = get_pdf_metadata(file_path)
    logger.info(f"Extracted {len(parsed_text)} chars from PDF ({metadata['pages']} pages)")

    # ── Step 2: Split into sections ────────────────────────────────────────────
    sections = extract_sections(parsed_text)

    # ── Step 3: Extract structured data from sections ─────────────────────────
    skills         = _extract_skills(sections)
    experience     = _extract_experience(sections)
    education      = _extract_education(sections)
    projects       = _extract_projects(sections)
    certifications = _extract_certifications(sections)

    # ── Step 4: Determine experience level ────────────────────────────────────
    experience_level = _determine_experience_level(experience, parsed_text)

    # ── Step 5: Suggest a role based on skills ────────────────────────────────
    suggested_role = _suggest_role(skills, job_title)

    # ── Step 6: Identify missing skills for the target role ───────────────────
    missing_skills = _find_missing_skills(skills, suggested_role)

    # ── Step 7: Upload PDF to IBM Cloud Object Storage ────────────────────────
    object_name = f"resumes/user_{user_id}/{filename}"
    cos_url = cos_client.upload_file(file_path, object_name)

    # ── Step 8: Save everything to the database ───────────────────────────────
    resume = Resume(
        user_id              = user_id,
        filename             = filename,
        cos_url              = cos_url,
        parsed_text          = parsed_text,
        skills_json          = json.dumps(skills),
        experience_json      = json.dumps(experience),
        education_json       = json.dumps(education),
        projects_json        = json.dumps(projects),
        certifications_json  = json.dumps(certifications),
        experience_level     = experience_level,
        suggested_role       = suggested_role,
        missing_skills       = json.dumps(missing_skills),
    )
    db.add(resume)
    db.commit()
    db.refresh(resume)

    logger.info(f"Resume saved to DB: id={resume.id}, skills={len(skills)}, level={experience_level}")

    # ── Step 9: Clean up temp file (already in COS/local storage) ─────────────
    # We keep it locally if COS is not configured (local:// URL)
    if cos_url.startswith("local://"):
        logger.debug("Keeping local file (COS not configured)")
    # If real COS URL, we could delete local copy — keeping it for now for debug

    return ResumeAnalysis(
        resume_id        = resume.id,
        filename         = filename,
        skills           = skills,
        experience_level = experience_level,
        suggested_role   = suggested_role,
        missing_skills   = missing_skills,
        education        = education,
        experience       = experience,
        certifications   = certifications,
    )


# ── Private Extraction Functions ──────────────────────────────────────────────

# Master list of tech skills we recognise
# This is a keyword-based approach — Step 9 will enhance this with spaCy NLP
KNOWN_SKILLS = {
    # Languages
    "python", "java", "javascript", "typescript", "c", "c++", "c#", "go",
    "rust", "kotlin", "swift", "ruby", "php", "scala", "r", "matlab",
    # Frontend
    "react", "vue", "angular", "html", "css", "tailwind", "bootstrap",
    "next.js", "nextjs", "gatsby", "redux", "webpack", "vite",
    # Backend
    "fastapi", "django", "flask", "express", "spring", "node.js", "nodejs",
    "graphql", "rest", "grpc", "microservices",
    # Databases
    "sql", "mysql", "postgresql", "sqlite", "mongodb", "redis", "cassandra",
    "dynamodb", "elasticsearch", "firebase",
    # Cloud & DevOps
    "aws", "azure", "gcp", "docker", "kubernetes", "terraform", "ansible",
    "jenkins", "github actions", "ci/cd", "linux", "bash",
    # AI/ML
    "machine learning", "deep learning", "tensorflow", "pytorch", "keras",
    "scikit-learn", "pandas", "numpy", "nlp", "computer vision",
    "langchain", "huggingface", "openai",
    # Tools
    "git", "github", "jira", "figma", "postman", "vs code",
}


def _extract_skills(sections: dict) -> list[str]:
    """
    Extract skills from the skills section (and fallback to full text).
    Uses keyword matching against KNOWN_SKILLS.
    """
    # Prioritise the dedicated skills section
    skills_text = sections.get("skills", "")
    full_text   = " ".join(sections.values()).lower()

    # If skills section is thin, also scan the full text
    search_text = (skills_text + " " + full_text).lower()

    found = set()
    for skill in KNOWN_SKILLS:
        # Use word boundary matching for short skills to avoid false matches
        # e.g., "r" should not match inside "framework"
        if len(skill) <= 2:
            pattern = rf'\b{re.escape(skill)}\b'
        else:
            pattern = re.escape(skill)

        if re.search(pattern, search_text, re.IGNORECASE):
            # Capitalise nicely: "python" → "Python", "aws" → "AWS"
            found.add(_format_skill(skill))

    # Sort for consistent ordering
    return sorted(found)


def _format_skill(skill: str) -> str:
    """Format a skill name for display."""
    # Short acronyms → uppercase
    acronyms = {"sql", "aws", "gcp", "css", "html", "nlp", "api",
                 "ci/cd", "rest", "grpc", "vs code"}
    if skill.lower() in acronyms:
        return skill.upper()
    # Known multi-word skills → title case
    if " " in skill or "." in skill:
        return skill.title()
    # Default → title case
    return skill.title()


def _extract_experience(sections: dict) -> list[dict]:
    """
    Extract work experience entries from the experience section.
    Each entry: { title, company, duration, description }
    """
    exp_text = sections.get("experience", "")
    if not exp_text:
        return []

    entries = []
    lines = [l.strip() for l in exp_text.split('\n') if l.strip()]

    # Simple heuristic: look for date patterns like "Jan 2022 - Dec 2023"
    date_pattern = re.compile(
        r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|January|February|'
        r'March|April|June|July|August|September|October|November|December)'
        r'.{0,20}(\d{4})',
        re.IGNORECASE
    )

    current_entry: dict = {}
    current_desc: list  = []

    for line in lines:
        if date_pattern.search(line):
            # Save previous entry
            if current_entry:
                current_entry["description"] = " ".join(current_desc)
                entries.append(current_entry)
                current_desc = []
            current_entry = {"duration": line, "title": "", "company": ""}
        elif current_entry and not current_entry.get("title"):
            current_entry["title"] = line
        elif current_entry and not current_entry.get("company"):
            current_entry["company"] = line
        else:
            current_desc.append(line)

    # Don't forget the last entry
    if current_entry:
        current_entry["description"] = " ".join(current_desc)
        entries.append(current_entry)

    return entries[:5]   # cap at 5 entries


def _extract_education(sections: dict) -> list[dict]:
    """
    Extract education entries: { degree, institution, year }
    """
    edu_text = sections.get("education", "")
    if not edu_text:
        return []

    entries = []
    lines = [l.strip() for l in edu_text.split('\n') if l.strip()]

    # Common degree keywords
    degree_pattern = re.compile(
        r'\b(B\.?Tech|M\.?Tech|B\.?E|M\.?E|B\.?Sc|M\.?Sc|BCA|MCA|'
        r'Bachelor|Master|PhD|Diploma|MBA|B\.?Com|B\.?A|M\.?A)\b',
        re.IGNORECASE
    )
    year_pattern = re.compile(r'\b(19|20)\d{2}\b')

    current: dict = {}
    for line in lines:
        if degree_pattern.search(line):
            if current:
                entries.append(current)
            current = {"degree": line, "institution": "", "year": ""}
        elif current and not current.get("institution") and len(line) > 3:
            current["institution"] = line
        elif current and year_pattern.search(line):
            current["year"] = year_pattern.search(line).group()

    if current:
        entries.append(current)

    return entries[:4]   # cap at 4 entries


def _extract_projects(sections: dict) -> list[dict]:
    """Extract project names and descriptions."""
    proj_text = sections.get("projects", "")
    if not proj_text:
        return []

    entries = []
    lines = [l.strip() for l in proj_text.split('\n') if l.strip()]

    # Simple approach: treat short lines as project names, longer as descriptions
    current: dict = {}
    for line in lines:
        if len(line) < 80 and not line.startswith(('-', '•', '*', '·')):
            if current:
                entries.append(current)
            current = {"name": line, "description": ""}
        elif current:
            current["description"] += " " + line

    if current:
        entries.append(current)

    return entries[:5]


def _extract_certifications(sections: dict) -> list[str]:
    """Extract certification names as a flat list."""
    cert_text = sections.get("certifications", "")
    if not cert_text:
        return []

    lines = [l.strip() for l in cert_text.split('\n') if l.strip()]
    # Filter out very short lines (likely bullets/punctuation)
    return [l.lstrip('•-*·').strip() for l in lines if len(l) > 5][:8]


def _determine_experience_level(experience: list[dict], full_text: str) -> str:
    """
    Determine experience level from:
      1. Number of experience entries found
      2. Keywords like "fresher", "entry level", "5 years experience"
    """
    full_lower = full_text.lower()

    # Explicit keywords in the resume
    if any(k in full_lower for k in ["fresher", "entry level", "entry-level", "no experience", "0 years"]):
        return "fresher"
    if any(k in full_lower for k in ["8+ years", "9 years", "10 years", "10+ years", "senior architect"]):
        return "expert"
    if any(k in full_lower for k in ["6 years", "7 years", "8 years", "senior developer", "tech lead"]):
        return "senior"
    if any(k in full_lower for k in ["3 years", "4 years", "5 years", "mid-level", "mid level"]):
        return "mid"
    if any(k in full_lower for k in ["1 year", "2 years", "junior", "associate developer"]):
        return "junior"

    # Fall back to number of experience entries
    num_entries = len(experience)
    if num_entries == 0:
        return "fresher"
    elif num_entries == 1:
        return "junior"
    elif num_entries == 2:
        return "mid"
    else:
        return "senior"


def _suggest_role(skills: list[str], provided_title: Optional[str] = None) -> str:
    """
    Suggest a job role based on skills.
    If the user already provided a job title, use that.
    """
    if provided_title:
        return provided_title

    skills_lower = {s.lower() for s in skills}

    # Role scoring: count matching skills per role
    role_signals = {
        "Full Stack Developer":   {"react", "node.js", "python", "javascript", "sql", "html", "css"},
        "Frontend Developer":     {"react", "vue", "angular", "html", "css", "javascript", "typescript"},
        "Backend Developer":      {"python", "java", "fastapi", "django", "spring", "sql", "rest"},
        "Data Scientist":         {"python", "machine learning", "pandas", "numpy", "tensorflow", "sql"},
        "DevOps Engineer":        {"docker", "kubernetes", "aws", "jenkins", "linux", "terraform", "bash"},
        "Android Developer":      {"kotlin", "java", "android"},
        "iOS Developer":          {"swift", "ios"},
        "ML Engineer":            {"python", "tensorflow", "pytorch", "machine learning", "deep learning"},
        "Database Administrator": {"sql", "mysql", "postgresql", "mongodb", "redis"},
    }

    best_role  = "Software Developer"
    best_score = 0

    for role, signal_skills in role_signals.items():
        score = len(skills_lower & signal_skills)   # intersection count
        if score > best_score:
            best_score = score
            best_role  = role

    return best_role


def _find_missing_skills(detected_skills: list[str], role: str) -> list[str]:
    """
    Compare detected skills against the expected skills for the target role.
    Returns skills that are missing (to show on the analysis page).
    """
    detected_lower = {s.lower() for s in detected_skills}

    role_requirements = {
        "Full Stack Developer":   ["React", "Node.js", "SQL", "Git", "Docker", "REST API"],
        "Frontend Developer":     ["React", "TypeScript", "CSS", "Git", "Testing", "Webpack"],
        "Backend Developer":      ["Docker", "PostgreSQL", "Redis", "Git", "Testing", "AWS"],
        "Data Scientist":         ["TensorFlow", "PyTorch", "SQL", "Statistics", "Tableau", "Spark"],
        "DevOps Engineer":        ["Docker", "Kubernetes", "Terraform", "CI/CD", "Monitoring", "Python"],
        "ML Engineer":            ["MLOps", "Docker", "SQL", "Cloud (AWS/GCP)", "FastAPI", "Git"],
        "Software Developer":     ["Git", "SQL", "Docker", "Testing", "REST API", "Linux"],
    }

    expected = role_requirements.get(role, role_requirements["Software Developer"])
    missing  = [s for s in expected if s.lower() not in detected_lower]
    return missing
