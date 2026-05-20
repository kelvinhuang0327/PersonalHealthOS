from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class TrendSummary(BaseModel):
    metric: str
    points: int
    first_value: Optional[float]
    last_value: Optional[float]
    change_percent: Optional[float]
    slope_per_day: Optional[float]
    direction: str


class TrendsAnalysisResponse(BaseModel):
    period_days: int
    summaries: list[TrendSummary]
