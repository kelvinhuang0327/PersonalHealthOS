from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class HealthInsightResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    subject_profile_id: Optional[UUID] = None
    insight_type: str
    severity: str
    title: str
    summary: str
    recommendation: Optional[str] = None
    evidence_json: Optional[dict[str, Any]] = None
    generated_at: datetime
    expires_at: Optional[datetime] = None
    is_active: bool
