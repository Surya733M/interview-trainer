"""
routes/resume.py — Resume Upload and Analysis Endpoints
========================================================
Endpoints:
  POST /resume/upload   → upload a PDF resume (multipart form)
  GET  /resume/{id}     → get a specific resume's analysis
  GET  /resume/list     → list all resumes for the current user
  DELETE /resume/{id}   → delete a resume
"""

from fastapi import APIRouter, Depends, UploadFile, File, Form, status
from sqlalchemy.orm import Session
from typing import List, Optional
import os, shutil

from app.database import get_db
from app.models.user import User
from app.models.interview import Resume
from app.schemas.interview import ResumeAnalysis
from app.services.auth_service import get_current_active_user
from app.utils.exceptions import (
    InvalidFileTypeError, FileTooLargeError, NotFoundError, PermissionDeniedError
)
from app.utils.logger import logger
from app.config import settings

router = APIRouter(prefix="/resume", tags=["Resume"])


# ── POST /resume/upload ───────────────────────────────────────────────────────
@router.post(
    "/upload",
    response_model=ResumeAnalysis,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a PDF resume for analysis",
)
async def upload_resume(
    file: UploadFile = File(..., description="PDF resume file"),
    job_title: Optional[str] = Form(None, description="Target job title"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Upload a PDF resume. The backend will:
      1. Validate file type and size
      2. Save the file temporarily
      3. Extract text using PyMuPDF (Step 8)
      4. Extract skills using spaCy + keyword matching (Step 9)
      5. Save analysis to the database
      6. Upload to IBM Cloud Object Storage (later)

    Returns the extracted skills, experience level, and analysis.
    """
    # ── Validate file type ─────────────────────────────────────────────────────
    if not file.filename.lower().endswith(".pdf"):
        raise InvalidFileTypeError("Only PDF files are accepted")

    # ── Validate file size ─────────────────────────────────────────────────────
    content = await file.read()
    max_bytes = settings.max_file_size_mb * 1024 * 1024
    if len(content) > max_bytes:
        raise FileTooLargeError(settings.max_file_size_mb)

    # ── Save file temporarily ──────────────────────────────────────────────────
    os.makedirs(settings.upload_dir, exist_ok=True)
    safe_name = f"user_{current_user.id}_{file.filename}"
    temp_path = os.path.join(settings.upload_dir, safe_name)

    with open(temp_path, "wb") as f:
        f.write(content)

    logger.info(f"Resume saved temporarily: {temp_path}")

    # ── Parse resume (Step 8 & 9 will fill these in) ──────────────────────────
    # Placeholder until resume_service and skill_extractor are built
    from app.services.resume_service import parse_and_analyze_resume
    analysis = parse_and_analyze_resume(temp_path, current_user.id, db, job_title)

    logger.success(f"Resume uploaded and analysed for user {current_user.id}")
    return analysis


# ── GET /resume/list ──────────────────────────────────────────────────────────
@router.get(
    "/list",
    response_model=List[ResumeAnalysis],
    summary="List all resumes uploaded by current user",
)
def list_resumes(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Return all resumes for the logged-in user."""
    resumes = db.query(Resume).filter(Resume.user_id == current_user.id).all()
    return [_resume_to_schema(r) for r in resumes]


# ── GET /resume/{id} ──────────────────────────────────────────────────────────
@router.get(
    "/{resume_id}",
    response_model=ResumeAnalysis,
    summary="Get a specific resume's analysis",
)
def get_resume(
    resume_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Return analysis for a specific resume. Users can only access their own."""
    resume = db.query(Resume).filter(Resume.id == resume_id).first()
    if not resume:
        raise NotFoundError("Resume")
    if resume.user_id != current_user.id:
        raise PermissionDeniedError()
    return _resume_to_schema(resume)


# ── DELETE /resume/{id} ───────────────────────────────────────────────────────
@router.delete(
    "/{resume_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a resume",
)
def delete_resume(
    resume_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Delete a resume and its associated file."""
    resume = db.query(Resume).filter(Resume.id == resume_id).first()
    if not resume:
        raise NotFoundError("Resume")
    if resume.user_id != current_user.id:
        raise PermissionDeniedError()

    db.delete(resume)
    db.commit()
    logger.info(f"Resume {resume_id} deleted by user {current_user.id}")


# ── Helper ─────────────────────────────────────────────────────────────────────
def _resume_to_schema(resume: Resume) -> ResumeAnalysis:
    """Convert ORM Resume object to Pydantic ResumeAnalysis schema."""
    import json
    return ResumeAnalysis(
        resume_id=resume.id,
        filename=resume.filename,
        skills=json.loads(resume.skills_json or "[]"),
        experience_level=resume.experience_level or "fresher",
        suggested_role=resume.suggested_role,
        missing_skills=json.loads(resume.missing_skills or "[]"),
        education=json.loads(resume.education_json or "[]"),
        experience=json.loads(resume.experience_json or "[]"),
        certifications=json.loads(resume.certifications_json or "[]"),
    )
