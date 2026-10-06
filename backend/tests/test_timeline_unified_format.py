from datetime import date, datetime, timezone
import uuid

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.models.entities import AISummary, HealthInsight, HealthMetric, LabReport, PersonProfile, RiskAlert, SymptomLog, User
from app.services.timeline_service import build_health_timeline


def test_timeline_contains_unified_types():
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    user = User(id=uuid.uuid4(), email='t@test.com', password_hash='x')
    db.add(user)
    db.commit()
    person = PersonProfile(id=uuid.uuid4(), owner_user_id=user.id, display_name='本人', relationship='self', is_default=True)
    db.add(person)
    db.commit()

    now = datetime.now(timezone.utc)
    db.add(HealthMetric(user_id=user.id, subject_profile_id=person.id, recorded_at=now, systolic_bp=120, diastolic_bp=80))
    db.add(SymptomLog(user_id=user.id, subject_profile_id=person.id, symptom='頭痛', occurred_at=now, severity=2))
    db.add(
        LabReport(
            user_id=user.id,
            subject_profile_id=person.id,
            report_date=date.today(),
            report_type='health_check',
            raw_text='x',
        )
    )
    db.add(AISummary(user_id=user.id, subject_profile_id=person.id, summary_text='summary', disclaimer='d'))
    db.add(
        HealthInsight(
            user_id=user.id,
            subject_profile_id=person.id,
            insight_type='trend',
            severity='info',
            title='洞察',
            summary='summary',
            is_active=True,
        )
    )
    db.add(
        RiskAlert(
            user_id=user.id,
            subject_profile_id=person.id,
            source_type='risk_monitor',
            rule_code='R1',
            severity='warning',
            title='警示',
            message='msg',
            status='active',
        )
    )
    db.commit()

    items = build_health_timeline(db, str(user.id), str(person.id), include_legacy=False, days=365, limit=100)
    assert items
    for item in items:
        assert item['type'] in {'symptom', 'metric', 'lab', 'insight', 'alert'}
        assert item['temporal_type'] in {'exact', 'estimated'}
        assert 'start_date' in item
        assert 'label' in item
        assert 'data' in item
