from typing import Any, Optional
from pydantic import BaseModel
from app.schemas.decision import UnifiedDecisionItem


class DashboardOverviewResponse(BaseModel):
    latest_metrics: dict[str, Any]
    active_alerts: list[dict[str, Any]]
    summary: dict[str, Any]


class TrendPoint(BaseModel):
    recorded_at: str
    value: float


class DashboardTrendsResponse(BaseModel):
    blood_glucose: list[TrendPoint]
    weight_kg: list[TrendPoint]
    systolic_bp: list[TrendPoint]
    sleep_hours: list[TrendPoint]


class DashboardHealthScore(BaseModel):
    overall_score: int
    components: dict[str, Any]


class HealthNarrativeResponse(BaseModel):
    summary: str
    risks: list[str]
    trends: list[str]
    reasons: list[str]
    actions: list[str]


class DashboardOverviewV2Response(BaseModel):
    health_score: DashboardHealthScore
    alerts: list[dict[str, Any]]
    insights: list[dict[str, Any]]
    recent_symptoms: list[dict[str, Any]]
    recent_metrics: list[dict[str, Any]]
    recent_labs: list[dict[str, Any]]
    trends: dict[str, list[TrendPoint]]
    reasoning_summary: Optional[str] = None
    predictive_insights: list[dict[str, Any]] = []
    anomaly_alerts: list[dict[str, Any]] = []
    clinical_labels: list[dict[str, Any]] = []
    risk_level: Optional[str] = None
    recommendations: list[dict[str, Any]] = []
    health_narrative: Optional[HealthNarrativeResponse] = None
    health_narrative_v2: Optional[dict[str, Any]] = None
    health_narrative_v3: Optional[dict[str, Any]] = None
    prioritized_actions: list[dict[str, Any]] = []
    decision_items: list[UnifiedDecisionItem] = []
    narrative_generated_at: Optional[str] = None
    explainability_summary: Optional[str] = None
    medical_disclaimer: Optional[str] = None
