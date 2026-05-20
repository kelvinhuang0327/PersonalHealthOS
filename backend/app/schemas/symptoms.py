from datetime import date, datetime
from uuid import UUID
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


class SymptomCreateRequest(BaseModel):
    symptom: Optional[str] = Field(default=None, min_length=1, max_length=120)
    symptom_names: Optional[list[str]] = None
    occurred_at: Optional[datetime] = None
    duration_minutes: Optional[int] = Field(default=None, ge=1, le=10080)
    severity: int = Field(ge=1, le=5)
    duration_category: Optional[str] = Field(default=None, max_length=30)
    note: Optional[str] = None
    estimated_start_date: Optional[date] = None
    estimated_duration_days: Optional[int] = Field(default=None, ge=1, le=36500)
    temporal_source: Optional[str] = Field(default=None, max_length=40)
    confidence_score: Optional[float] = Field(default=None, ge=0, le=1)

    @model_validator(mode='after')
    def validate_input(self):
        if not self.symptom and not self.symptom_names:
            raise ValueError('symptom or symptom_names is required')
        return self


class SymptomUpdateRequest(BaseModel):
    symptom: Optional[str] = Field(default=None, min_length=1, max_length=120)
    occurred_at: Optional[datetime] = None
    duration_minutes: Optional[int] = Field(default=None, ge=1, le=10080)
    severity: Optional[int] = Field(default=None, ge=1, le=5)
    note: Optional[str] = None
    estimated_start_date: Optional[date] = None
    estimated_duration_days: Optional[int] = Field(default=None, ge=1, le=36500)
    temporal_source: Optional[str] = Field(default=None, max_length=40)
    confidence_score: Optional[float] = Field(default=None, ge=0, le=1)


class SymptomResponse(SymptomCreateRequest):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    subject_profile_id: Optional[UUID] = None
