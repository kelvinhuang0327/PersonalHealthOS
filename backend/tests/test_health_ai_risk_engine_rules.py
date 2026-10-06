from datetime import datetime, timezone
import uuid

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.models.entities import HealthMetric, PersonProfile, User
from app.services.health_ai_engine.risk_engine import generate_risk_alerts


def test_risk_engine_applies_yaml_rules():
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    user = User(id=uuid.uuid4(), email='risk@test.com', password_hash='x')
    person = PersonProfile(id=uuid.uuid4(), owner_user_id=user.id, display_name='本人', relationship='self', is_default=False)
    db.add(user)
    db.add(person)
    db.commit()

    now = datetime.now(timezone.utc)
    db.add(HealthMetric(user_id=user.id, subject_profile_id=person.id, recorded_at=now, systolic_bp=150, diastolic_bp=95, weight_kg=95))
    db.add(HealthMetric(user_id=user.id, subject_profile_id=person.id, recorded_at=now, systolic_bp=148, diastolic_bp=96, weight_kg=95))
    db.add(HealthMetric(user_id=user.id, subject_profile_id=person.id, recorded_at=now, systolic_bp=149, diastolic_bp=94, weight_kg=95))
    db.commit()

    alerts = generate_risk_alerts(db, str(user.id), str(person.id), include_legacy=False)
    risk_types = {a.risk_type for a in alerts}
    assert 'bp_high_3times' in risk_types
    assert 'bmi_high' in risk_types or 'bmi_very_high' in risk_types
    priorities = [getattr(a, 'priority', 0) for a in alerts]
    assert priorities == sorted(priorities, reverse=True)
