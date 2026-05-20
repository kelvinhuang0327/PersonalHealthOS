from __future__ import annotations

from datetime import datetime
from uuid import UUID
from typing import Optional
from pydantic import BaseModel, ConfigDict


class RiskAlertResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    risk_type: Optional[str]
    source_type: str
    source_id: Optional[UUID]
    rule_code: str
    severity: str
    title: str
    message: str
    description: Optional[str]
    recommendation: Optional[str]
    status: str
    resolved_at: Optional[datetime]
    created_at: datetime
