from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.services.health_ai_engine.timeline_engine import build_health_timeline as build_health_timeline_with_engine


def build_health_timeline(db: Session, user_id: str, person_id: str, include_legacy: bool, days: int = 180, limit: int = 200) -> list[dict[str, Any]]:
    return build_health_timeline_with_engine(db, user_id, person_id, include_legacy, days=days, limit=limit)
