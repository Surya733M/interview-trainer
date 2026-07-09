"""
services/report_service.py — Final Report Generation (Step 18)
===============================================================
Aggregates all answer scores and generates the final report using Granite.
"""

import json
from sqlalchemy.orm import Session

from app.models.interview import Interview, Answer
from app.models.report import Report
from app.utils.logger import logger


async def generate_report(interview_id: int, db: Session) -> Report:
    """
    Generate a comprehensive final report for a completed interview.
    Called automatically when the last answer is submitted.
    """
    interview = db.query(Interview).filter(Interview.id == interview_id).first()
    if not interview:
        raise ValueError(f"Interview {interview_id} not found")

    answers = db.query(Answer).filter(Answer.interview_id == interview_id).all()
    if not answers:
        logger.warning(f"No answers found for interview {interview_id}")

    # ── Aggregate scores ───────────────────────────────────────────────────────
    def avg(values): return round(sum(values) / len(values) * 10, 1) if values else 50.0

    tech_scores  = [a.technical_score    for a in answers if a.technical_score]
    gram_scores  = [a.grammar_score      for a in answers if a.grammar_score]
    comm_scores  = [a.communication_score for a in answers if a.communication_score]
    star_scores  = [a.star_score         for a in answers if a.star_score]
    comp_scores  = [a.completeness_score for a in answers if a.completeness_score]
    all_scores   = [a.overall_score      for a in answers if a.overall_score]

    technical_score    = avg(tech_scores)
    communication_score = avg(comm_scores)
    behavioral_score   = avg(star_scores)
    hr_score           = avg(comp_scores)
    confidence_score   = avg(gram_scores)
    overall_score      = avg(all_scores)
    readiness_percentage = min(overall_score, 100.0)

    # ── Generate qualitative analysis with Granite ─────────────────────────────
    skills = json.loads(
        db.query(Interview).filter(Interview.id == interview_id)
        .first().resume.skills_json or "[]"
    )

    answers_summary = [
        {
            "question": a.question_text[:100],
            "score":    a.overall_score,
            "type":     "behavioral" if a.star_score and a.star_score > 0 else "technical",
        }
        for a in answers[:5]
    ]

    strengths, weaknesses, topics, learning_path, summary = \
        await _generate_analysis_with_granite(
            job_title=interview.job_title,
            experience_level=interview.experience_level,
            skills=skills,
            avg_scores={
                "technical": avg(tech_scores) / 10,
                "communication": avg(comm_scores) / 10,
                "behavioral": avg(star_scores) / 10,
                "hr": avg(comp_scores) / 10,
                "grammar": avg(gram_scores) / 10,
            },
            answers_summary=answers_summary,
        )

    # ── Save report to DB ──────────────────────────────────────────────────────
    # Delete existing report if any (re-generation case)
    existing = db.query(Report).filter(Report.interview_id == interview_id).first()
    if existing:
        db.delete(existing)
        db.flush()

    report = Report(
        interview_id=interview_id,
        technical_score=technical_score,
        communication_score=communication_score,
        behavioral_score=behavioral_score,
        hr_score=hr_score,
        confidence_score=confidence_score,
        overall_score=overall_score,
        readiness_percentage=readiness_percentage,
        strengths_json=json.dumps(strengths),
        weaknesses_json=json.dumps(weaknesses),
        topics_to_improve_json=json.dumps(topics),
        learning_path_json=json.dumps(learning_path),
        summary=summary,
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    logger.info(
        f"Report generated for interview {interview_id}: "
        f"overall={overall_score:.1f}%, readiness={readiness_percentage:.1f}%"
    )
    return report


async def _generate_analysis_with_granite(
    job_title, experience_level, skills, avg_scores, answers_summary
) -> tuple:
    """Use Granite to generate qualitative analysis; fallback if unavailable."""
    try:
        from app.services.granite_service import granite
        from app.prompts.report_gen import build_report_prompt

        if granite.is_available:
            prompt = build_report_prompt(
                job_title=job_title,
                experience_level=experience_level,
                skills=skills,
                avg_scores=avg_scores,
                answers_summary=answers_summary,
            )
            result = granite.generate_json(prompt)
            if isinstance(result, dict) and "strengths" in result:
                return (
                    result.get("strengths", []),
                    result.get("weaknesses", []),
                    result.get("topics_to_improve", []),
                    result.get("learning_path", []),
                    result.get("summary", ""),
                )
    except Exception as e:
        logger.warning(f"Granite report generation failed: {e}. Using defaults.")

    # Rule-based fallback
    overall = sum(avg_scores.values()) / len(avg_scores)

    strengths = []
    weaknesses = []

    if avg_scores.get("technical", 0) >= 6:
        strengths.append("Strong technical knowledge demonstrated")
    else:
        weaknesses.append("Technical depth needs improvement")

    if avg_scores.get("communication", 0) >= 6:
        strengths.append("Clear communication and articulation")
    else:
        weaknesses.append("Communication clarity needs work")

    if avg_scores.get("behavioral", 0) >= 6:
        strengths.append("Good use of structured examples")
    else:
        weaknesses.append("STAR method needs more practice")

    if not strengths:
        strengths = ["Shows potential", "Willing to learn"]
    if not weaknesses:
        weaknesses = ["Continue practicing technical depth"]

    topics = _suggest_topics(skills, avg_scores)
    learning_path = _suggest_learning_path(topics)
    summary = (
        f"The candidate demonstrated an overall readiness of "
        f"{int(overall*10)}% for a {job_title} position. "
        f"Focus on strengthening the identified weak areas to improve interview performance."
    )
    return strengths, weaknesses, topics, learning_path, summary


def _suggest_topics(skills: list, scores: dict) -> list:
    topics = []
    if scores.get("technical", 0) < 6:
        topics.extend(["Data Structures & Algorithms", "System Design"])
    if scores.get("behavioral", 0) < 6:
        topics.append("STAR Method for Behavioral Questions")
    if scores.get("communication", 0) < 6:
        topics.append("Clear Technical Communication")
    if "python" in [s.lower() for s in skills] and scores.get("technical", 0) < 7:
        topics.append("Advanced Python (decorators, async, OOP)")
    if not topics:
        topics = ["System Design", "Advanced Problem Solving"]
    return topics[:4]


def _suggest_learning_path(topics: list) -> list:
    resources = {
        "Data Structures & Algorithms": {"resource": "LeetCode 75 / NeetCode 150", "priority": "high"},
        "System Design":                {"resource": "System Design Primer (GitHub)", "priority": "high"},
        "STAR Method for Behavioral Questions": {"resource": "STAR Method Practice on Pramp", "priority": "medium"},
        "Advanced Python (decorators, async, OOP)": {"resource": "Python Tricks by Dan Bader", "priority": "medium"},
        "Clear Technical Communication": {"resource": "Tech Interview Handbook (github.com/yangshun)", "priority": "medium"},
    }
    path = []
    for topic in topics:
        info = resources.get(topic, {"resource": f"Search '{topic} interview guide'", "priority": "medium"})
        path.append({"topic": topic, **info})
    return path
