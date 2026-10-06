from datetime import datetime, timezone
import uuid

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.models.entities import HealthMetric, PersonProfile, RiskAlert, User
from app.services.health_ai_engine.health_score_engine import calculate_health_score


def test_health_score_engine_rule_penalty_outputs():
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    user = User(id=uuid.uuid4(), email='score@test.com', password_hash='x')
    person = PersonProfile(id=uuid.uuid4(), owner_user_id=user.id, display_name='本人', relationship='self', is_default=False, height_cm=170)
    db.add(user)
    db.add(person)
    db.commit()

    now = datetime.now(timezone.utc)
    db.add(HealthMetric(user_id=user.id, subject_profile_id=person.id, recorded_at=now, systolic_bp=145, diastolic_bp=90, weight_kg=88, sleep_hours=6, steps=3000))
    db.add(RiskAlert(user_id=user.id, subject_profile_id=person.id, source_type='risk_monitor', rule_code='R1', severity='warning', title='x', message='x', status='active'))
    db.commit()

    result = calculate_health_score(db, str(user.id), str(person.id), person, include_legacy=False, days=90)
    assert 'health_score' in result
    assert 'cardiovascular_score' in result
    assert 'metabolic_score' in result
    assert 'activity_score' in result
    assert 'lifestyle_score' in result
    assert isinstance(result['score_detail'].get('applied_rules'), list)
