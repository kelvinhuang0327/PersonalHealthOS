from datetime import datetime, timezone
import uuid

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.models.entities import HealthMetric, PersonProfile, User
from app.services.health_ai_engine.insight_engine import generate_health_insights


def test_insight_engine_rule_based_generation_with_mock_llm():
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    user = User(id=uuid.uuid4(), email='insight@test.com', password_hash='x')
    person = PersonProfile(id=uuid.uuid4(), owner_user_id=user.id, display_name='本人', relationship='self', is_default=False)
    db.add(user)
    db.add(person)
    db.commit()

    now = datetime.now(timezone.utc)
    db.add(HealthMetric(user_id=user.id, subject_profile_id=person.id, recorded_at=now, systolic_bp=130, diastolic_bp=85))
    db.add(HealthMetric(user_id=user.id, subject_profile_id=person.id, recorded_at=now, systolic_bp=132, diastolic_bp=86))
    db.add(HealthMetric(user_id=user.id, subject_profile_id=person.id, recorded_at=now, systolic_bp=135, diastolic_bp=87))
    db.commit()

    insights = generate_health_insights(db, str(user.id), str(person.id), include_legacy=False)
    assert insights
    assert insights[0].summary.startswith('[LLM-mock:')
    assert 'rule_id' in (insights[0].evidence_json or {})
    assert 'category' in (insights[0].evidence_json or {})
    assert 'priority' in (insights[0].evidence_json or {})
    assert 'confidence' in (insights[0].evidence_json or {})
    assert 'evidence_level' in (insights[0].evidence_json or {})
    assert 'guideline_source' in (insights[0].evidence_json or {})
    assert 'guideline_version' in (insights[0].evidence_json or {})
    assert any('本系統為健康建議工具，非醫療診斷' in i.summary for i in insights)
