from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.models.entities import AISummary, PersonProfile, User
from app.services.health_ai_engine.insight_engine import get_latest_narrative, get_narrative_history, get_previous_narrative, persist_narrative_history


def _build_db():
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    user = User(email='narrative@example.com', password_hash='hashed')
    db.add(user)
    db.commit()
    db.refresh(user)
    person = PersonProfile(owner_user_id=user.id, display_name='本人', relationship='self', is_default=True)
    db.add(person)
    db.commit()
    db.refresh(person)
    return db, user, person


def _build_payload(now: datetime, *, score: int = 66, risk_level: str = 'moderate'):
    return {
        'overall_score': score,
        'health_score': {'overall_score': score, 'components': {'cardiovascular': 61}},
        'risk_level': risk_level,
        'summary_type': 'daily',
        'narrative_version': 'v2',
        'generated_at': now.isoformat(),
        'based_on_score_id': None,
        'based_on_alert_snapshot': 'snapshot-1',
        'alerts': [{'id': 'alert-1', 'title': '血壓偏高', 'severity': 'high'}],
        'insights': [],
        'trends': {},
        'symptoms': [],
        'labs': [],
        'metrics': [],
        'actions': [],
        'health_narrative': {
            'summary': '你的健康目前處於中度風險。',
            'risks': ['心血管風險增加'],
            'trends': ['血壓在過去 7 天呈上升趨勢'],
            'reasons': ['最近壓力偏高'],
            'actions': ['每天量血壓 7 天'],
        },
        'health_narrative_v2': {
            'summary': '你的健康目前處於中度風險。',
            'risks': ['心血管風險增加'],
            'trends': ['血壓在過去 7 天呈上升趨勢'],
            'reasons': ['最近壓力偏高'],
            'actions': ['每天量血壓 7 天'],
            'delta_summary': '與上週相比，你的健康狀況沒有明顯變化，但血壓仍持續偏高。',
            'improvements': ['已開始記錄血壓'],
            'deteriorations': ['血壓在過去 7 天呈上升趨勢'],
            'adherence': ['已持續量血壓 3 天'],
            'missed_risks': ['血壓偏高已出現提醒，但尚未持續追蹤'],
        },
    }


def test_narrative_history_persistence_and_ordering():
    db, user, person = _build_db()
    now = datetime.now(timezone.utc)
    first_payload = _build_payload(now)

    first_row = persist_narrative_history(db, str(user.id), str(person.id), first_payload, summary_type='daily')
    assert first_row is not None
    assert db.query(AISummary).count() == 1

    duplicate_row = persist_narrative_history(db, str(user.id), str(person.id), first_payload, summary_type='daily')
    assert duplicate_row is None
    assert db.query(AISummary).count() == 1

    later_payload = _build_payload(now + timedelta(hours=25), score=68)
    later_row = persist_narrative_history(db, str(user.id), str(person.id), later_payload, summary_type='daily')
    assert later_row is not None
    assert db.query(AISummary).count() == 2

    latest = get_latest_narrative(db, str(user.id), str(person.id), summary_type='daily')
    previous = get_previous_narrative(db, str(user.id), str(person.id), summary_type='daily')
    history = get_narrative_history(db, str(user.id), str(person.id), limit=10, summary_type='daily')

    assert latest and latest['generated_at']
    assert previous and previous['generated_at']
    assert latest['generated_at'] > previous['generated_at']
    assert len(history) == 2
    assert history[0]['generated_at'] > history[1]['generated_at']
    assert history[0]['health_narrative_v2']['delta_summary']
    assert '7 天' in history[0]['health_narrative_v2']['trends'][0] or '7天' in history[0]['health_narrative_v2']['trends'][0]
