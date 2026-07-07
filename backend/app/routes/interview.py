"""
routes/interview.py — Interview Session Endpoints
==================================================
Endpoints:
  POST /interview/start        → generate questions and start session
  POST /interview/answer       → submit an answer and get feedback
  GET  /interview/{id}         → get interview session status
  GET  /interview/{id}/questions → get all questions for a session
  GET  /interview/list         → list all interviews for current user
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models.user import User
from app.schemas.interview import (
    InterviewStartRequest, InterviewStartResponse,
    AnswerSubmitRequest, AnswerFeedback,
    InterviewResponse, Question,
)
from app.services.auth_service import get_current_active_user
from app.utils.exceptions import NotFoundError, PermissionDeniedError, ValidationError
from app.utils.logger import logger

router = APIRouter(prefix="/interview", tags=["Interview"])


# ── POST /interview/start ─────────────────────────────────────────────────────
@router.post(
    "/start",
    response_model=InterviewStartResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Start a new mock interview session",
)
async def start_interview(
    request: InterviewStartRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Start a new mock interview.

    Flow:
      1. Load the user's resume from DB
      2. Run RAG search to retrieve relevant interview content (Step 13)
      3. Call IBM Granite to generate personalised questions (Step 15)
      4. Save the interview session to DB
      5. Return the first question

    Until Steps 13-15 are built, returns placeholder questions.
    """
    from app.services.interview_service import create_interview_session
    response = await create_interview_session(request, current_user, db)
    logger.info(f"Interview {response.interview_id} started for user {current_user.id}")
    return response


# ── POST /interview/answer ────────────────────────────────────────────────────
@router.post(
    "/answer",
    response_model=AnswerFeedback,
    summary="Submit an answer and get instant AI feedback",
)
async def submit_answer(
    request: AnswerSubmitRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Submit an answer to the current question.

    Flow:
      1. Validate the interview belongs to this user
      2. Call IBM Granite to evaluate the answer (Step 17)
      3. Save the answer and scores to DB
      4. Return feedback + next question (or completion signal)
    """
    from app.services.interview_service import process_answer
    feedback = await process_answer(request, current_user, db)
    return feedback


# ── GET /interview/{id} ───────────────────────────────────────────────────────
@router.get(
    "/{interview_id}",
    response_model=InterviewResponse,
    summary="Get interview session status",
)
def get_interview(
    interview_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Return the current state of an interview session."""
    from app.models.interview import Interview
    interview = db.query(Interview).filter(Interview.id == interview_id).first()
    if not interview:
        raise NotFoundError("Interview")
    if interview.user_id != current_user.id:
        raise PermissionDeniedError()
    return InterviewResponse.model_validate(interview)


# ── GET /interview/list ───────────────────────────────────────────────────────
@router.get(
    "/list",
    response_model=List[InterviewResponse],
    summary="List all interviews for current user",
)
def list_interviews(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Return all interview sessions for the logged-in user."""
    from app.models.interview import Interview
    interviews = (
        db.query(Interview)
        .filter(Interview.user_id == current_user.id)
        .order_by(Interview.created_at.desc())
        .all()
    )
    return [InterviewResponse.model_validate(i) for i in interviews]
