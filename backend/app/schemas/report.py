"""
schemas/report.py — Report Request/Response Schemas
=====================================================
Defines the API shape for the final interview report.
"""

from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List, Dict, Any


class LearningResource(BaseModel):
    """A single recommended learning resource."""
    topic: str
    resource: str
    url: Optional[str] = None
    priority: str = "medium"  # "high" | "medium" | "low"


class ReportResponse(BaseModel):
    """
    The complete final report returned after an interview is finished.
    This is what gets displayed on the Report page and exported as PDF.
    """
    id: int
    interview_id: int

    # Dimension scores (0.0 – 100.0)
    technical_score: float
    communication_score: float
    behavioral_score: float
    hr_score: float
    confidence_score: float
    overall_score: float
    readiness_percentage: float

    # Qualitative analysis
    strengths: List[str]
    weaknesses: List[str]
    topics_to_improve: List[str]
    learning_path: List[Dict[str, Any]]
    summary: Optional[str]

    # PDF download link (if generated)
    pdf_path: Optional[str]
    generated_at: datetime

    model_config = {"from_attributes": True}


class DashboardStats(BaseModel):
    """Summary stats shown on the user's dashboard."""
    total_interviews: int
    completed_interviews: int
    average_score: float
    best_score: float
    readiness_percentage: float
    recent_interviews: List[Dict[str, Any]]
