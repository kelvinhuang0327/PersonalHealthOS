from __future__ import annotations

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class AIModuleRequest(BaseModel):
    days: int = Field(default=90, ge=7, le=365)
    focus: Optional[str] = None
    max_items: int = Field(default=5, ge=1, le=10)


class AIHealthRisk(BaseModel):
    title: str
    level: str
    reason: str
    evidence_ids: list[str]


class AIRecommendation(BaseModel):
    title: str
    action: str
    priority: str
    evidence_ids: list[str]


class AIFollowUpItem(BaseModel):
    item: str
    timeline: str
    why: str
    evidence_ids: list[str]


class AIGuardrailReport(BaseModel):
    dropped_items: int
    grounded_items: int
    total_items: int
    grounded_ratio: float
    safety_flags: list[str]


class AIModuleResponse(BaseModel):
    module: str
    model_name: str
    generated_at: datetime
    health_risks: list[AIHealthRisk]
    lifestyle_recommendations: list[AIRecommendation]
    follow_up_items: list[AIFollowUpItem]
    confidence: float
    guardrail_report: AIGuardrailReport
    disclaimer: str


class AIModuleEvaluationResponse(BaseModel):
    module: str
    format_valid: bool
    grounded_ratio: float
    safety_pass: bool
    actionability_score: float
    overall_score: float
