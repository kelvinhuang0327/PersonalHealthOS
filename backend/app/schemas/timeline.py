from __future__ import annotations

from typing import Optional
from pydantic import BaseModel


class TimelineItem(BaseModel):
    type: str
    event_type: str
    event_time: str
    temporal_type: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    label: Optional[str] = None
    title: str
    description: str
    data: dict
    metadata: Optional[dict] = None


class TimelineResponse(BaseModel):
    items: list[TimelineItem]
