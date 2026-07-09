"""
routes/report.py — Report and Dashboard Endpoints
===================================================
Endpoints:
  GET  /report/{interview_id}      → get the final report for an interview
  GET  /report/{interview_id}/pdf  → download the report as PDF
  GET  /dashboard/stats            → get user's overall stats for dashboard
"""

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
import os

from app.database import get_db
from app.models.user import User
from app.models.report import Report
from app.schemas.report import ReportResponse, DashboardStats
from app.services.auth_service import get_current_active_user
from app.utils.exceptions import NotFoundError, PermissionDeniedError
from app.utils.logger import logger

router = APIRouter(prefix="/report", tags=["Report"])


# ── GET /report/{interview_id} ────────────────────────────────────────────────
@router.get(
    "/{interview_id}",
    response_model=ReportResponse,
    summary="Get final report for a completed interview",
)
def get_report(
    interview_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Return the full report for a completed interview.
    Ownership check: users can only view their own reports.
    """
    report = (
        db.query(Report)
        .filter(Report.interview_id == interview_id)
        .first()
    )
    if not report:
        raise NotFoundError("Report")

    # Verify ownership via the interview relationship
    if report.interview.user_id != current_user.id:
        raise PermissionDeniedError()

    import json
    return ReportResponse(
        id=report.id,
        interview_id=report.interview_id,
        technical_score=report.technical_score,
        communication_score=report.communication_score,
        behavioral_score=report.behavioral_score,
        hr_score=report.hr_score,
        confidence_score=report.confidence_score,
        overall_score=report.overall_score,
        readiness_percentage=report.readiness_percentage,
        strengths=json.loads(report.strengths_json or "[]"),
        weaknesses=json.loads(report.weaknesses_json or "[]"),
        topics_to_improve=json.loads(report.topics_to_improve_json or "[]"),
        learning_path=json.loads(report.learning_path_json or "[]"),
        summary=report.summary,
        pdf_path=report.pdf_path,
        generated_at=report.generated_at,
    )


# ── GET /report/{interview_id}/pdf ────────────────────────────────────────────
@router.get(
    "/{interview_id}/pdf",
    summary="Download the report as a PDF file",
)
def download_pdf(
    interview_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Stream the generated PDF report file.
    FileResponse sends the file directly to the browser.
    """
    report = db.query(Report).filter(Report.interview_id == interview_id).first()
    if not report:
        raise NotFoundError("Report")
    if report.interview.user_id != current_user.id:
        raise PermissionDeniedError()
    if not report.pdf_path or not os.path.exists(report.pdf_path):
        raise NotFoundError("PDF file")

    # Generate PDF on demand if not already created
    if not report.pdf_path or not os.path.exists(report.pdf_path):
        from app.services.pdf_service import generate_pdf_report
        pdf_path = generate_pdf_report(report)
        report.pdf_path = pdf_path
        db.commit()

    return FileResponse(
        path=report.pdf_path,
        filename=f"interview_report_{interview_id}.pdf",
        media_type="application/pdf",
    )


# ── Dashboard router ──────────────────────────────────────────────────────────
dashboard_router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

@dashboard_router.get(
    "/stats",
    response_model=DashboardStats,
    summary="Get user's interview statistics for the dashboard",
)
def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Aggregate stats for the user's dashboard:
      - Total interviews taken
      - Average and best scores
      - Interview readiness percentage
      - Recent interview history
    """
    from app.models.interview import Interview
    from sqlalchemy import func

    interviews = (
        db.query(Interview)
        .filter(Interview.user_id == current_user.id)
        .order_by(Interview.created_at.desc())
        .all()
    )

    completed = [i for i in interviews if i.status == "completed"]

    # Fetch scores from reports
    scores = []
    for i in completed:
        if i.report:
            scores.append(i.report.overall_score)

    avg_score  = sum(scores) / len(scores) if scores else 0.0
    best_score = max(scores) if scores else 0.0
    readiness  = min(avg_score, 100.0)

    # Build recent interviews list
    recent = []
    for iv in interviews[:5]:
        recent.append({
            "id":         iv.id,
            "job_title":  iv.job_title,
            "status":     iv.status,
            "created_at": iv.created_at.isoformat() if iv.created_at else None,
            "score":      iv.report.overall_score if iv.report else None,
        })

    return DashboardStats(
        total_interviews=len(interviews),
        completed_interviews=len(completed),
        average_score=round(avg_score, 1),
        best_score=round(best_score, 1),
        readiness_percentage=round(readiness, 1),
        recent_interviews=recent,
    )
