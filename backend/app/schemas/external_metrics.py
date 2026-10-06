from datetime import datetime
from pydantic import BaseModel


class ExternalSyncResponse(BaseModel):
    synced_count: int
    source: str


class ExternalTrendPoint(BaseModel):
    recorded_at: datetime
    value: float


class ExternalTrendResponse(BaseModel):
    metric: str
    points: list[ExternalTrendPoint]
