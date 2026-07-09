"""
services/interview_service.py — Full Interview Engine (Steps 15-17)
=====================================================================
Real implementation replacing the placeholder:
  - Step 15: IBM Granite generates personalised questions via RAG
  - Step 16: Mock interview session management
  - Step 17: IBM Granite evaluates every answer with scores + feedback

Falls back to curated sample questions when Granite is unavailable.
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

# ── Sample fallback questions (used when Granite unavailable) ─────────────────
FALLBACK_QUESTIONS = [
    {"id":1,"question":"Tell me about yourself and your technical background.","type":"hr","difficulty":"easy","topic":"Introduction","hint":"Keep it under 2 minutes. Present-Past-Future structure.","model_answer":"A strong answer covers current skills, key past experiences with results, and enthusiasm for this specific role."},
    {"id":2,"question":"What are your strongest technical skills? Give a real example of applying them.","type":"technical","difficulty":"medium","topic":"Technical Skills","hint":"Be specific — name the tech, the problem, the result.","model_answer":"Name 2-3 skills, describe a specific project or problem, quantify the outcome."},
    {"id":3,"question":"Describe a challenging bug you debugged. What was your process?","type":"technical","difficulty":"medium","topic":"Problem Solving","hint":"Show systematic debugging methodology.","model_answer":"Reproduce → isolate → hypothesise → test → fix → prevent. Show systematic thinking."},
    {"id":4,"question":"Tell me about a time you worked under a tight deadline. How did you handle it?","type":"behavioral","difficulty":"medium","topic":"Time Management","hint":"Use STAR. Show prioritisation skills.","model_answer":"STAR: specific situation, your prioritisation approach, concrete actions, on-time delivery."},
    {"id":5,"question":"Where do you see yourself in 3 years?","type":"hr","difficulty":"easy","topic":"Career Goals","hint":"Align with company's growth direction.","model_answer":"Show ambition + realism: master this role, take ownership, grow toward senior/lead."},
    {"id":6,"question":"Explain the difference between REST and GraphQL APIs.","type":"technical","difficulty":"medium","topic":"Web APIs","hint":"Cover: request model, over-fetching, use cases.","model_answer":"REST: multiple endpoints, fixed response shapes. GraphQL: single endpoint, client specifies exact data needed. REST for simple APIs, GraphQL for complex clients."},
    {"id":7,"question":"What is your approach to writing clean, maintainable code?","type":"technical","difficulty":"medium","topic":"Code Quality","hint":"Mention SOLID, DRY, testing, documentation.","model_answer":"Meaningful names, single responsibility, small functions, tests, code reviews, consistent style (linter)."},
    {"id":8,"question":"Describe a time you disagreed with a teammate's technical decision. What did you do?","type":"behavioral","difficulty":"medium","topic":"Collaboration","hint":"Show professional disagreement and resolution.","model_answer":"Listen to understand, present data-backed counter-argument, agree to try both if unsure, accept team decision gracefully."},
    {"id":9,"question":"How do you stay updated with new technologies?","type":"hr","difficulty":"easy","topic":"Learning","hint":"Show specific, credible sources and hands-on learning.","model_answer":"Official docs, engineering blogs, build side projects with new tech, contribute to open source."},
    {"id":10,"question":"What questions do you have for us?","type":"hr","difficulty":"easy","topic":"Engagement","hint":"3-5 thoughtful questions show genuine interest.","model_answer":"Ask about team culture, tech stack choices, onboarding, growth opportunities, biggest current challenges."},
]


async def create_interview_session(
    request: InterviewStartRequest,
    current_user: User,
    db: Session,
) -> InterviewStartResponse:
    """
    Create a new interview session with IBM Granite-generated questions.
    Falls back to curated questions if Granite is unavailable.
    """
    # Verify the resume belongs to this user
    resume = db.query(Resume).filter(
        Resume.id == request.resume_id,
        Resume.user_id == current_user.id,
    ).first()
    if not resume:
        raise NotFoundError("Resume")

    # Try Granite question generation (RAG-powered)
    questions = await _generate_questions_with_granite(
        resume=resume,
        job_title=request.job_title,
        experience_level=request.experience_level,
        num_technical=request.num_technical,
        num_behavioral=request.num_behavioral,
        num_hr=request.num_hr,
    )

    # Save interview to DB
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

    logger.info(f"Interview {interview.id} created with {len(questions)} questions.")

    return InterviewStartResponse(
        interview_id=interview.id,
        job_title=interview.job_title,
        total_questions=len(questions),
        first_question=Question(**questions[0]),
    )


async def _generate_questions_with_granite(
    resume,
    job_title: str,
    experience_level: str,
    num_technical: int,
    num_behavioral: int,
    num_hr: int,
) -> list:
    """Call the RAG pipeline + Granite to generate personalised questions."""
    try:
        from app.rag.retriever import retrieve_relevant_context, ensure_knowledge_base_populated
        from app.prompts.question_gen import build_question_generation_prompt, format_rag_context
        from app.services.granite_service import granite

        # Ensure vector DB is populated
        ensure_knowledge_base_populated()

        # Get relevant context from vector DB
        skills = json.loads(resume.skills_json or "[]")
        retrieved = retrieve_relevant_context(
            resume_text=resume.parsed_text or "",
            job_title=job_title,
            skills=skills,
            n_results=10,
        )

        # Build RAG-augmented prompt
        rag_ctx = format_rag_context(retrieved)
        prompt  = build_question_generation_prompt(
            job_title=job_title,
            skills=skills,
            experience_level=experience_level,
            resume_summary=resume.parsed_text or "",
            rag_context=rag_ctx,
            num_technical=num_technical,
            num_behavioral=num_behavioral,
            num_hr=num_hr,
        )

        # Call IBM Granite
        if granite.is_available:
            result = granite.generate_json(prompt)
            if isinstance(result, list) and len(result) >= 3:
                # Validate and normalise Granite output
                questions = _normalise_questions(result)
                if questions:
                    logger.info(f"Granite generated {len(questions)} questions.")
                    return questions

        logger.warning("Granite unavailable or returned invalid output. Using fallback questions.")

    except Exception as e:
        logger.error(f"RAG/Granite question generation failed: {e}. Using fallback.")

    # Return curated fallback questions
    total = num_technical + num_behavioral + num_hr
    return FALLBACK_QUESTIONS[:total]


def _normalise_questions(raw: list) -> list:
    """Validate and normalise Granite-generated question objects."""
    required = ["question", "type", "difficulty", "topic"]
    valid    = []
    for i, q in enumerate(raw, 1):
        if not isinstance(q, dict):
            continue
        if not all(k in q for k in required):
            continue
        valid.append({
            "id":           i,
            "question":     str(q.get("question", ""))[:500],
            "type":         q.get("type", "technical"),
            "difficulty":   q.get("difficulty", "medium"),
            "topic":        str(q.get("topic", "General"))[:50],
            "hint":         str(q.get("hint", ""))[:200],
            "model_answer": str(q.get("model_answer", ""))[:500],
        })
    return valid


async def process_answer(
    request: AnswerSubmitRequest,
    current_user: User,
    db: Session,
) -> AnswerFeedback:
    """
    Evaluate a submitted answer using IBM Granite.
    Falls back to rule-based scoring if Granite is unavailable.
    """
    interview = db.query(Interview).filter(Interview.id == request.interview_id).first()
    if not interview:
        raise NotFoundError("Interview")
    if interview.user_id != current_user.id:
        raise PermissionDeniedError()
    if interview.status == "completed":
        raise ValidationError("This interview is already completed.")

    questions = json.loads(interview.questions_json)
    if request.question_index >= len(questions):
        raise ValidationError("Invalid question index.")

    current_q = questions[request.question_index]

    # Get AI evaluation
    scores, strengths, improvements, model_answer = await _evaluate_answer(
        question=current_q.get("question", ""),
        question_type=current_q.get("type", "hr"),
        answer=request.answer_text,
        job_title=interview.job_title,
        experience_level=interview.experience_level,
    )

    overall = round(sum(scores.values()) / len(scores), 1)

    # Save to DB
    answer = Answer(
        interview_id=interview.id,
        question_index=request.question_index,
        question_text=current_q.get("question", ""),
        answer_text=request.answer_text,
        technical_score=scores.get("technical", 0),
        grammar_score=scores.get("grammar", 0),
        communication_score=scores.get("communication", 0),
        star_score=scores.get("star_method", 0),
        completeness_score=scores.get("completeness", 0),
        overall_score=overall,
        feedback_json=json.dumps({"strengths": strengths, "improvements": improvements}),
        model_answer=model_answer,
    )
    db.add(answer)

    # Advance interview state
    next_index = request.question_index + 1
    is_complete = next_index >= len(questions)
    interview.current_question = next_index
    if is_complete:
        interview.status = "completed"
        interview.completed_at = datetime.now(timezone.utc)
        # Auto-generate report
        await _generate_report(interview, db)

    db.commit()

    return AnswerFeedback(
        question_index=request.question_index,
        scores=scores,
        overall_score=overall,
        strengths=strengths,
        improvements=improvements,
        model_answer=model_answer,
        next_question=Question(**questions[next_index]) if not is_complete else None,
        is_complete=is_complete,
    )


async def _evaluate_answer(
    question: str, question_type: str, answer: str,
    job_title: str, experience_level: str
) -> tuple:
    """Evaluate with Granite; fall back to rule-based scoring."""
    try:
        from app.services.granite_service import granite
        from app.prompts.evaluation import build_evaluation_prompt

        if granite.is_available:
            prompt = build_evaluation_prompt(
                question=question,
                question_type=question_type,
                answer=answer,
                job_title=job_title,
                experience_level=experience_level,
            )
            result = granite.generate_json(prompt)
            if isinstance(result, dict) and "scores" in result:
                return (
                    result["scores"],
                    result.get("strengths", ["Good attempt"]),
                    result.get("improvements", ["Add more specific examples"]),
                    result.get("model_answer", "A strong answer includes specific examples, quantifiable results, and clear structure.")
                )
    except Exception as e:
        logger.warning(f"Granite evaluation failed: {e}. Using rule-based scoring.")

    # Rule-based fallback scoring
    word_count = len(answer.split())
    base = min(9.0, max(3.0, word_count / 25.0 * 10.0))
    scores = {
        "technical":     round(min(10.0, base * 0.9), 1),
        "grammar":       round(min(10.0, base * 1.0), 1),
        "communication": round(min(10.0, base * 0.95), 1),
        "star_method":   round(min(10.0, base * 0.85), 1),
        "completeness":  round(min(10.0, base * 0.9), 1),
    }
    return (
        scores,
        ["Clear response", "Relevant content"],
        ["Add specific examples with measurable outcomes", "Use STAR method for behavioral answers"],
        "A strong answer includes specific examples, quantifiable results, and clear structure.",
    )


async def _generate_report(interview: Interview, db: Session):
    """Auto-generate the final report after interview completion."""
    try:
        from app.services.report_service import generate_report
        await generate_report(interview.id, db)
    except Exception as e:
        logger.error(f"Auto report generation failed: {e}")
