from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ActionOutcomeRead(BaseModel):
    id: UUID
    action_id: UUID
    metric_type: str
    before_value: Optional[float] = None
    after_value: Optional[float] = None
    delta: Optional[float] = None
    delta_pct: Optional[float] = None
    time_window_days: int
    outcome_label: str
    computed_at: datetime

    model_config = {'from_attributes': True}


class HealthActionCreate(BaseModel):
    person_id: Optional[UUID] = None
    source_type: str = Field(default='manual', max_length=60)
    source_id: Optional[str] = Field(default=None, max_length=120)
    title: str = Field(..., max_length=240)
    description: Optional[str] = Field(default=None, max_length=2000)
    category: Optional[str] = Field(default=None, max_length=60)
    action_type: str = Field(default='lifestyle', max_length=60)
    priority: str = Field(default='medium', max_length=30)
    frequency: str = Field(default='daily', max_length=60)
    status: str = Field(default='todo', max_length=30)
    due_date: Optional[datetime] = None
    confidence: Optional[float] = Field(default=None, ge=0, le=1)
    evidence_level: Optional[str] = Field(default=None, max_length=60)
    guideline_source: Optional[str] = Field(default=None, max_length=200)
    rule_id: Optional[str] = Field(default=None, max_length=120)


class HealthActionUpdate(BaseModel):
    person_id: Optional[UUID] = None
    title: Optional[str] = Field(None, max_length=240)
    description: Optional[str] = Field(None, max_length=2000)
    category: Optional[str] = Field(None, max_length=60)
    priority: Optional[str] = Field(None, max_length=30)
    frequency: Optional[str] = Field(None, max_length=60)
    status: Optional[str] = Field(None, max_length=30)
    due_date: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    snoozed_until: Optional[datetime] = None
    snooze_reason: Optional[str] = Field(None, max_length=500)
    reminder_status: Optional[str] = Field(None, max_length=30)
    impact_status: Optional[str] = Field(None, max_length=30)


class HealthActionRead(BaseModel):
    id: UUID
    user_id: UUID
    person_id: Optional[UUID] = None
    source_type: str
    source_id: Optional[str] = None
    title: str
    description: Optional[str] = None
    category: Optional[str] = None
    action_type: str
    priority: str
    frequency: Optional[str] = None
    status: str
    due_date: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    snoozed_until: Optional[datetime] = None
    snoozed_at: Optional[datetime] = None
    snooze_reason: Optional[str] = None
    resurface_count: int
    streak_count: int
    last_completed_at: Optional[datetime] = None
    reminder_status: Optional[str] = None
    impact_status: Optional[str] = None
    confidence: Optional[float] = None
    evidence_level: Optional[str] = None
    guideline_source: Optional[str] = None
    rule_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    outcomes: list[ActionOutcomeRead] = []

    model_config = {'from_attributes': True}
