"""
schemas/interview.py — Interview Request/Response Schemas
==========================================================
Defines the API shape for:
  - Starting an interview
  - Submitting an answer
  - Receiving questions and feedback
  - Resume analysis responses
"""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List, Dict, Any


# ── Resume ────────────────────────────────────────────────────────────────────
class ResumeAnalysis(BaseModel):
    """Response returned after resume upload and analysis."""
    resume_id: int
    filename: str
    skills: List[str]
    experience_level: str
    suggested_role: Optional[str]
    missing_skills: List[str]
    education: List[Dict[str, Any]]
    experience: List[Dict[str, Any]]
    certifications: List[str]


# ── Questions ─────────────────────────────────────────────────────────────────
class Question(BaseModel):
    """A single interview question with metadata."""
    id: int
    question: str
    type: str           # "technical" | "behavioral" | "hr" | "coding"
    difficulty: str     # "easy" | "medium" | "hard"
    topic: str          # "Python" | "React" | "STAR" etc.
    hint: Optional[str] = None


# ── Start Interview ───────────────────────────────────────────────────────────
class InterviewStartRequest(BaseModel):
    """What the frontend sends to start a new interview session."""
    resume_id: int
    job_title: str = Field(..., min_length=2, max_length=100)
    experience_level: str = Field(default="fresher")
    # Number of questions to generate in each category
    num_technical: int = Field(default=5, ge=1, le=10)
    num_behavioral: int = Field(default=3, ge=1, le=5)
    num_hr: int = Field(default=2, ge=1, le=5)


class InterviewStartResponse(BaseModel):
    """Returned when an interview session is created successfully."""
    interview_id: int
    job_title: str
    total_questions: int
    first_question: Question
    message: str = "Interview started! Answer each question to proceed."


# ── Answer Submission ─────────────────────────────────────────────────────────
class AnswerSubmitRequest(BaseModel):
    """The user's answer to the current question."""
    interview_id: int
    question_index: int
    answer_text: str = Field(..., min_length=1, max_length=5000)


class AnswerFeedback(BaseModel):
    """
    Detailed per-answer feedback returned immediately after submission.
    Gives the user instant feedback during the mock interview.
    """
    question_index: int
    scores: Dict[str, float]    # {"technical": 7.5, "grammar": 8.0, ...}
    overall_score: float
    strengths: List[str]
    improvements: List[str]
    model_answer: str           # reference answer from Granite
    next_question: Optional[Question] = None   # None = interview complete
    is_complete: bool = False


# ── Interview Status ──────────────────────────────────────────────────────────
class InterviewResponse(BaseModel):
    """Full interview session state — returned when fetching a session."""
    id: int
    job_title: str
    status: str
    current_question: int
    total_questions: int
    experience_level: str
    created_at: datetime

    model_config = {"from_attributes": True}
