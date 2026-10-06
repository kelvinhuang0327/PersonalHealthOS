from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.entities import HealthInsight, PersonProfile
from app.services.health_ai_engine.insight_engine import generate_health_insights as generate_with_engine


def generate_health_insights(db: Session, user_id: str, profile: PersonProfile, include_legacy: bool) -> list[HealthInsight]:
    return generate_with_engine(db, user_id=user_id, person_id=str(profile.id), include_legacy=include_legacy)
