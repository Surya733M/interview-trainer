"""
services/pdf_service.py — PDF Report Generation (Step 19)
===========================================================
Generates a downloadable PDF report using ReportLab.
Called from routes/report.py → GET /report/{id}/pdf
"""

import os
import json
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)

from app.models.report import Report
from app.utils.logger import logger

# IBM Blue colour
IBM_BLUE = colors.HexColor("#0f62fe")
IBM_DARK = colors.HexColor("#161616")


def generate_pdf_report(report: Report, output_dir: str = "./reports") -> str:
    """
    Generate a PDF report from a Report ORM object.

    Args:
        report     : SQLAlchemy Report instance
        output_dir : directory to save the PDF

    Returns:
        Path to the generated PDF file
    """
    os.makedirs(output_dir, exist_ok=True)
    filename  = f"report_{report.interview_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    filepath  = os.path.join(output_dir, filename)

    doc    = SimpleDocTemplate(filepath, pagesize=A4,
                               leftMargin=2*cm, rightMargin=2*cm,
                               topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    story  = []

    # ── Custom styles ──────────────────────────────────────────────────────────
    title_style = ParagraphStyle("Title", parent=styles["Title"],
                                 textColor=IBM_BLUE, fontSize=22, spaceAfter=6)
    h2_style    = ParagraphStyle("H2", parent=styles["Heading2"],
                                 textColor=IBM_DARK, fontSize=13, spaceBefore=14, spaceAfter=4)
    body_style  = styles["BodyText"]
    body_style.fontSize  = 10
    body_style.spaceAfter = 4

    # ── Header ─────────────────────────────────────────────────────────────────
    story.append(Paragraph("Interview Performance Report", title_style))
    story.append(Paragraph("Powered by IBM Granite AI + RAG", styles["Italic"]))
    story.append(Paragraph(
        f"Generated: {datetime.now().strftime('%B %d, %Y at %H:%M')} | "
        f"Interview ID: #{report.interview_id}",
        styles["Normal"]
    ))
    story.append(HRFlowable(width="100%", thickness=2, color=IBM_BLUE, spaceAfter=12))

    # ── Overall Score Banner ───────────────────────────────────────────────────
    story.append(Paragraph("Overall Performance", h2_style))
    score_data = [
        ["Overall Score", "Readiness"],
        [f"{report.overall_score:.1f}%", f"{report.readiness_percentage:.1f}%"],
    ]
    score_table = Table(score_data, colWidths=[8*cm, 8*cm])
    score_table.setStyle(TableStyle([
        ("BACKGROUND",  (0,0), (-1,0), IBM_BLUE),
        ("TEXTCOLOR",   (0,0), (-1,0), colors.white),
        ("FONTSIZE",    (0,0), (-1,0), 11),
        ("FONTNAME",    (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE",    (0,1), (-1,1), 18),
        ("FONTNAME",    (0,1), (-1,1), "Helvetica-Bold"),
        ("ALIGN",       (0,0), (-1,-1), "CENTER"),
        ("VALIGN",      (0,0), (-1,-1), "MIDDLE"),
        ("ROWHEIGHT",   (0,0), (-1,0), 28),
        ("ROWHEIGHT",   (0,1), (-1,1), 40),
        ("GRID",        (0,0), (-1,-1), 0.5, colors.lightgrey),
        ("BACKGROUND",  (0,1), (-1,1), colors.HexColor("#f0f8ff")),
    ]))
    story.append(score_table)
    story.append(Spacer(1, 12))

    # ── Score Breakdown ────────────────────────────────────────────────────────
    story.append(Paragraph("Score Breakdown", h2_style))
    breakdown = [
        ["Dimension", "Score", "Rating"],
        ["Technical Knowledge",  f"{report.technical_score:.1f}%",     _rating(report.technical_score)],
        ["Communication",        f"{report.communication_score:.1f}%", _rating(report.communication_score)],
        ["Behavioral / STAR",    f"{report.behavioral_score:.1f}%",    _rating(report.behavioral_score)],
        ["HR / Soft Skills",     f"{report.hr_score:.1f}%",            _rating(report.hr_score)],
        ["Confidence / Grammar", f"{report.confidence_score:.1f}%",    _rating(report.confidence_score)],
    ]
    bd_table = Table(breakdown, colWidths=[7*cm, 4*cm, 5*cm])
    bd_table.setStyle(TableStyle([
        ("BACKGROUND",  (0,0), (-1,0), IBM_BLUE),
        ("TEXTCOLOR",   (0,0), (-1,0), colors.white),
        ("FONTNAME",    (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE",    (0,0), (-1,-1), 10),
        ("ALIGN",       (1,0), (-1,-1), "CENTER"),
        ("GRID",        (0,0), (-1,-1), 0.5, colors.lightgrey),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#f7f8fa")]),
    ]))
    story.append(bd_table)
    story.append(Spacer(1, 12))

    # ── AI Summary ─────────────────────────────────────────────────────────────
    if report.summary:
        story.append(Paragraph("AI Assessment Summary", h2_style))
        story.append(Paragraph(report.summary, body_style))

    # ── Strengths ──────────────────────────────────────────────────────────────
    strengths = json.loads(report.strengths_json or "[]")
    if strengths:
        story.append(Paragraph("Strengths", h2_style))
        for s in strengths:
            story.append(Paragraph(f"+ {s}", body_style))

    # ── Weaknesses ─────────────────────────────────────────────────────────────
    weaknesses = json.loads(report.weaknesses_json or "[]")
    if weaknesses:
        story.append(Paragraph("Areas to Improve", h2_style))
        for w in weaknesses:
            story.append(Paragraph(f"! {w}", body_style))

    # ── Learning Path ──────────────────────────────────────────────────────────
    learning = json.loads(report.learning_path_json or "[]")
    if learning:
        story.append(Paragraph("Recommended Learning Path", h2_style))
        lp_data = [["Topic", "Resource", "Priority"]]
        for item in learning:
            lp_data.append([
                item.get("topic", ""),
                item.get("resource", ""),
                item.get("priority", "medium").upper(),
            ])
        lp_table = Table(lp_data, colWidths=[5*cm, 8*cm, 3*cm])
        lp_table.setStyle(TableStyle([
            ("BACKGROUND",  (0,0), (-1,0), IBM_BLUE),
            ("TEXTCOLOR",   (0,0), (-1,0), colors.white),
            ("FONTNAME",    (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTSIZE",    (0,0), (-1,-1), 9),
            ("GRID",        (0,0), (-1,-1), 0.5, colors.lightgrey),
            ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#f7f8fa")]),
            ("ALIGN",       (2,0), (2,-1), "CENTER"),
        ]))
        story.append(lp_table)

    # ── Footer ─────────────────────────────────────────────────────────────────
    story.append(Spacer(1, 20))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.lightgrey))
    story.append(Paragraph(
        "Generated by Interview Trainer Agent | Powered by IBM Granite + RAG",
        ParagraphStyle("Footer", parent=styles["Normal"], fontSize=8,
                       textColor=colors.grey, alignment=1)
    ))

    doc.build(story)
    logger.info(f"PDF report saved: {filepath}")
    return filepath


def _rating(score: float) -> str:
    if score >= 80: return "Excellent"
    if score >= 65: return "Good"
    if score >= 50: return "Average"
    return "Needs Work"
