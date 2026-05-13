"""
Pydantic data models for the SJT Assessment Engine API.
"""
from __future__ import annotations

from pydantic import BaseModel, Field


# ── Request Models ─────────────────────────────────────────────────

class SubmitRequest(BaseModel):
    """
    Payload sent by SurveyJS on survey completion.
    `answers` is a flat dict like {"Q_Gala": "A", "Q_Gala_verify": "C"}.
    """
    user_id: str = Field(default="anonymous", description="Optional student identifier")
    answers: dict[str, str] = Field(..., description="Flat key-value map of question_id → selected option")


# ── Response Models ────────────────────────────────────────────────

class SubmitResponse(BaseModel):
    """Returned after successfully saving a submission."""
    submission_id: str
    message: str = "Submission saved successfully"


class DimensionScore(BaseModel):
    """Score for a single personality / interest dimension."""
    dimension_code: str = Field(..., description="e.g. 'Holland_R', 'MBTI_E'")
    base_score: float = Field(0.0, description="Score from model layer (mother-template weights)")
    penalty_score: float = Field(0.0, description="Score from rule layer (consistency penalty)")
    final_score: float = Field(0.0, description="base_score + penalty_score")


class ReportResponse(BaseModel):
    """Full assessment report returned to the frontend."""
    submission_id: str
    source_version: str = Field(default="", description="Question bank / scoring source version")
    dimensions: list[DimensionScore] = Field(default_factory=list)
    holland_top3: list[str] = Field(default_factory=list, description="Top 3 Holland codes")
    mbti_type: str = Field(default="", description="Derived MBTI 4-letter type")
    cross_insight: str = Field(default="", description="Cross interpretation of MBTI and Holland")
    recommended_cn_occupations: list[dict] = Field(default_factory=list, description="Recommended occupations mapped from the main project")
    consistency_issues: list[dict] = Field(default_factory=list, description="Triggered consistency rules")
    source_lineage: dict = Field(default_factory=dict, description="Lineage for answered questions and scoring inputs")
