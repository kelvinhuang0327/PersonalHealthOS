from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.entities import RiskAlert
from app.services.health_ai_engine.risk_engine import generate_risk_alerts


def run_health_risk_monitor(db: Session, user_id: str, person_id: str, include_legacy: bool) -> list[RiskAlert]:
    return generate_risk_alerts(db, user_id=user_id, person_id=person_id, include_legacy=include_legacy)
