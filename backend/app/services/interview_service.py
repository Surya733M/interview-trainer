"""
services/interview_service.py — Interview Session Business Logic
=================================================================
Placeholder service — fully implemented in Steps 14-17.

Right now it:
  - Creates an interview record in the database
  - Returns sample questions so the API is testable end-to-end
  - Accepts answers and returns placeholder feedback

Later steps will replace the placeholder logic with:
  - RAG retrieval (Step 13)
  - IBM Granite question generation (Step 15)
  - IBM Granite answer evaluation (Step 17)
"""

import json
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.models.interview import Interview, Answer, Resume
from app.schemas.interview import (
    InterviewStartRequest, InterviewStartResponse,
    AnswerSubmitRequest, AnswerFeedback, Question,
)
from app.models.user import User
from app.utils.exceptions import NotFoundError, PermissionDeniedError, ValidationError
from app.utils.logger import logger


# ── Sample questions (replaced by Granite in Step 15) ────────────────────────
SAMPLE_QUESTIONS = [
    {
        "id": 1,
        "question": "Tell me about yourself and your background.",
        "type": "hr",
        "difficulty": "easy",
        "topic": "Introduction",
        "hint": "Keep it under 2 minutes. Cover education, experience, and why you want this role.",
    },
    {
        "id": 2,
        "question": "What are your strongest technical skills and how have you applied them?",
        "type": "technical",
        "difficulty": "medium",
        "topic": "Skills",
        "hint": "Give specific examples with measurable outcomes.",
    },
    {
        "id": 3,
        "question": "Describe a challenging project you worked on. What was your approach?",
        "type": "behavioral",
        "difficulty": "medium",
        "topic": "Problem Solving",
        "hint": "Use the STAR method: Situation, Task, Action, Result.",
    },
    {
        "id": 4,
        "question": "Where do you see yourself in 5 years?",
        "type": "hr",
        "difficulty": "easy",
        "topic": "Career Goals",
        "hint": "Align your answer with the company's growth opportunities.",
    },
    {
        "id": 5,
        "question": "Explain the difference between REST and GraphQL APIs.",
        "type": "technical",
        "difficulty": "medium",
        "topic": "Web APIs",
        "hint": "Cover: request structure, over-fetching, use cases.",
    },
]


async def create_interview_session(
    request: InterviewStartRequest,
    current_user: User,
    db: Session,
) -> InterviewStartResponse:
    """
    Create a new interview session.
    Step 15 will replace SAMPLE_QUESTIONS with Granite-generated ones.
    """
    # Verify the resume exists and belongs to this user
    resume = db.query(Resume).filter(
        Resume.id == request.resume_id,
        Resume.user_id == current_user.id,
    ).first()
    if not resume:
        raise NotFoundError("Resume")

    # TODO Step 15: call granite_service to generate real questions
    questions = SAMPLE_QUESTIONS[:request.num_technical + request.num_behavioral + request.num_hr]

    # Create interview record
    interview = Interview(
        user_id=current_user.id,
        resume_id=request.resume_id,
        job_title=request.job_title,
        experience_level=request.experience_level,
        questions_json=json.dumps(questions),
        status="in_progress",
        current_question=0,
        total_questions=len(questions),
    )
    db.add(interview)
    db.commit()
    db.refresh(interview)

    first_q = Question(**questions[0])

    return InterviewStartResponse(
        interview_id=interview.id,
        job_title=interview.job_title,
        total_questions=len(questions),
        first_question=first_q,
    )


async def process_answer(
    request: AnswerSubmitRequest,
    current_user: User,
    db: Session,
) -> AnswerFeedback:
    """
    Process a submitted answer.
    Step 17 will replace placeholder scores with Granite evaluation.
    """
    interview = db.query(Interview).filter(Interview.id == request.interview_id).first()
    if not interview:
        raise NotFoundError("Interview")
    if interview.user_id != current_user.id:
        raise PermissionDeniedError()
    if interview.status == "completed":
        raise ValidationError("This interview is already completed")

    questions = json.loads(interview.questions_json)

    # Validate question index
    if request.question_index >= len(questions):
        raise ValidationError("Invalid question index")

    current_q = questions[request.question_index]

    # TODO Step 17: call evaluation_service to get real Granite scores
    # Placeholder: give a random-ish score based on answer length
    answer_len = len(request.answer_text.split())
    base_score = min(10.0, max(4.0, answer_len / 20.0 * 10.0))

    scores = {
        "technical":     round(base_score * 0.9, 1),
        "grammar":       round(base_score * 1.0, 1),
        "communication": round(base_score * 0.95, 1),
        "star_method":   round(base_score * 0.85, 1),
        "completeness":  round(base_score * 0.9, 1),
    }
    overall = round(sum(scores.values()) / len(scores), 1)

    # Save the answer
    answer = Answer(
        interview_id=interview.id,
        question_index=request.question_index,
        question_text=current_q["question"],
        answer_text=request.answer_text,
        technical_score=scores["technical"],
        grammar_score=scores["grammar"],
        communication_score=scores["communication"],
        star_score=scores["star_method"],
        completeness_score=scores["completeness"],
        overall_score=overall,
        feedback_json=json.dumps({
            "strengths": ["Good attempt", "Relevant content included"],
            "improvements": ["Add more specific examples", "Use STAR structure"],
        }),
        model_answer="A strong answer would include specific examples with measurable outcomes and follow the STAR method.",
    )
    db.add(answer)

    # Advance to next question
    next_index = request.question_index + 1
    is_complete = next_index >= len(questions)

    interview.current_question = next_index
    if is_complete:
        interview.status = "completed"
        interview.completed_at = datetime.now(timezone.utc)

    db.commit()

    # Determine next question
    next_q = None
    if not is_complete:
        next_q = Question(**questions[next_index])

    return AnswerFeedback(
        question_index=request.question_index,
        scores=scores,
        overall_score=overall,
        strengths=["Good attempt", "Relevant content included"],
        improvements=["Add specific examples", "Use STAR method for behavioral questions"],
        model_answer=answer.model_answer,
        next_question=next_q,
        is_complete=is_complete,
    )
