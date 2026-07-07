"""
services/resume_service.py — Resume Parsing Placeholder
=========================================================
Placeholder service — fully implemented in Steps 8 and 9.

Right now it:
  - Saves the file to disk
  - Creates a Resume record in the database
  - Returns a basic analysis structure

Steps 8 & 9 will replace this with:
  - PyMuPDF text extraction (Step 8)
  - spaCy + keyword skill extraction (Step 9)
"""

import json
import os
from sqlalchemy.orm import Session

from app.models.interview import Resume
from app.schemas.interview import ResumeAnalysis
from app.utils.logger import logger


def parse_and_analyze_resume(
    file_path: str,
    user_id: int,
    db: Session,
) -> ResumeAnalysis:
    """
    Parse a resume PDF and extract structured information.
    Currently returns placeholder data until Steps 8-9 are built.
    """
    filename = os.path.basename(file_path)

    # TODO Step 8: replace with PyMuPDF text extraction
    parsed_text = "Resume text will be extracted here in Step 8."

    # TODO Step 9: replace with spaCy skill extractor
    placeholder_skills = ["Python", "FastAPI", "SQL", "Problem Solving"]

    # Save to database
    resume = Resume(
        user_id=user_id,
        filename=filename,
        parsed_text=parsed_text,
        skills_json=json.dumps(placeholder_skills),
        experience_json=json.dumps([]),
        education_json=json.dumps([]),
        certifications_json=json.dumps([]),
        projects_json=json.dumps([]),
        experience_level="fresher",
        suggested_role="Software Developer",
        missing_skills=json.dumps(["Docker", "Kubernetes", "Cloud"]),
    )
    db.add(resume)
    db.commit()
    db.refresh(resume)

    logger.info(f"Resume record created: id={resume.id}, user={user_id}")

    return ResumeAnalysis(
        resume_id=resume.id,
        filename=filename,
        skills=placeholder_skills,
        experience_level="fresher",
        suggested_role="Software Developer",
        missing_skills=["Docker", "Kubernetes", "Cloud"],
        education=[],
        experience=[],
        certifications=[],
    )
