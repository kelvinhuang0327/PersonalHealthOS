from datetime import datetime
from uuid import UUID
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class MetricCreateRequest(BaseModel):
    recorded_at: datetime
    systolic_bp: Optional[int] = Field(default=None, ge=50, le=250)
    diastolic_bp: Optional[int] = Field(default=None, ge=30, le=180)
    heart_rate: Optional[int] = Field(default=None, ge=20, le=250)
    blood_glucose: Optional[float] = Field(default=None, ge=20, le=800)
    weight_kg: Optional[float] = Field(default=None, ge=20, le=500)
    sleep_hours: Optional[float] = Field(default=None, ge=0, le=24)
    steps: Optional[int] = Field(default=None, ge=0, le=200000)
    note: Optional[str] = Field(default=None, max_length=2000)


class MetricResponse(MetricCreateRequest):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    subject_profile_id: Optional[UUID] = None
    source: str
