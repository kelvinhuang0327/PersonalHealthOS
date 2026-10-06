from __future__ import annotations

from datetime import date, datetime
from uuid import UUID
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict


class AISummaryGenerateRequest(BaseModel):
    period_start: Optional[date] = None
    period_end: Optional[date] = None


class AISummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    period_start: Optional[date]
    period_end: Optional[date]
    summary_text: str
    abnormal_explanation: Optional[str]
    recommendations: Optional[str]
    disclaimer: str
    model_name: Optional[str]
    narrative_json: Optional[dict[str, Any]] = None
    narrative_version: Optional[str] = None
    summary_type: Optional[str] = None
    generated_at: Optional[datetime] = None
    based_on_score_id: Optional[UUID] = None
    based_on_alert_snapshot: Optional[str] = None
    created_at: datetime
