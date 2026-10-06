from __future__ import annotations

from datetime import datetime
from uuid import UUID
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class HealthScoreCalculateRequest(BaseModel):
    days: int = Field(default=30, ge=7, le=365)


class HealthScoreResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    source_period_days: int
    overall_score: int
    cardiovascular_score: int
    metabolic_score: int
    weight_score: int
    sleep_score: int
    score_detail: Optional[dict[str, Any]]
    calculated_at: datetime
