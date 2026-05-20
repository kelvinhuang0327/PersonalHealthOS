from datetime import datetime, timezone, timedelta
import uuid

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.models.entities import (
    AISummary,
    HealthMetric,
    PersonProfile,
    SymptomLog,
    User,
)
from app.services.health_risk_monitor_service import run_health_risk_monitor


def test_health_risk_monitor_generates_alerts():
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    user = User(id=uuid.uuid4(), email='m@test.com', password_hash='x')
    db.add(user)
    db.commit()
    person = PersonProfile(id=uuid.uuid4(), owner_user_id=user.id, display_name='本人', relationship='self', is_default=True)
    db.add(person)
    db.commit()

    now = datetime.now(timezone.utc)
    for _ in range(3):
        db.add(
            HealthMetric(
                user_id=user.id,
                subject_profile_id=person.id,
                recorded_at=now - timedelta(days=1),
                systolic_bp=150,
                diastolic_bp=95,
                source='manual',
            )
        )
    db.add(
        SymptomLog(
            user_id=user.id,
            subject_profile_id=person.id,
            symptom='腰痠',
            occurred_at=now - timedelta(days=30),
            severity=2,
            estimated_duration_days=1200,
            temporal_source='user_narrative',
        )
    )
    db.add(
        AISummary(
            user_id=user.id,
            subject_profile_id=person.id,
            summary_text='近期有高風險訊號',
            disclaimer='d',
        )
    )
    db.commit()

    alerts = run_health_risk_monitor(db, str(user.id), str(person.id), include_legacy=False)
    risk_types = {a.risk_type for a in alerts}
    assert 'bp_high_3times' in risk_types
    assert 'long_term_symptom' in risk_types
