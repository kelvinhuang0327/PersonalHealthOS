from datetime import datetime, timezone
from io import BytesIO

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.deps import get_current_user
from app.main import app
from app.models.entities import PersonProfile, SymptomLog, User


def _build_client():
    engine = create_engine(
        'sqlite://',
        connect_args={'check_same_thread': False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    user = User(email='test@example.com', password_hash='hashed')
    db.add(user)
    db.commit()
    db.refresh(user)
    self_person = PersonProfile(owner_user_id=user.id, display_name='本人', relationship='self', is_default=True)
    db.add(self_person)
    db.commit()
    db.refresh(self_person)

    def override_get_db():
        try:
            yield db
        finally:
            pass

    def override_get_current_user():
        return user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    return TestClient(app), db, self_person


def test_symptom_crud_with_person_switch():
    client, _db, self_person = _build_client()
    child = client.post('/api/v1/persons', json={'display_name': '小孩', 'relationship': 'child'}).json()

    create = client.post(
        f"/api/v1/symptoms?person_id={child['id']}",
        json={
            'symptom': '發燒',
            'occurred_at': datetime.now(timezone.utc).isoformat(),
            'duration_minutes': 60,
            'severity': 4,
            'note': '夜間偏高',
        },
    )
    assert create.status_code == 200
    symptom_id = create.json()['id']

    child_logs = client.get(f"/api/v1/symptoms?person_id={child['id']}").json()
    self_logs = client.get(f"/api/v1/symptoms?person_id={self_person.id}").json()
    assert len(child_logs) == 1
    assert len(self_logs) == 0

    updated = client.put(f"/api/v1/symptoms/{symptom_id}?person_id={child['id']}", json={'severity': 2})
    assert updated.status_code == 200
    assert updated.json()['severity'] == 2


def test_update_self_symptom_with_null_subject_profile():
    client, db, self_person = _build_client()
    user = db.query(User).filter(User.email == 'test@example.com').first()
    legacy = SymptomLog(
        user_id=user.id,
        subject_profile_id=None,
        symptom='頭痛',
        occurred_at=datetime.now(timezone.utc),
        severity=3,
        note='舊資料',
    )
    db.add(legacy)
    db.commit()
    db.refresh(legacy)

    updated = client.put(f'/api/v1/symptoms/{legacy.id}?person_id={self_person.id}', json={'severity': 2})
    assert updated.status_code == 200
    assert updated.json()['severity'] == 2


def test_document_confirm_flow(monkeypatch):
    client, _db, self_person = _build_client()

    import app.api.documents as documents_api

    monkeypatch.setattr(documents_api, 'validate_upload', lambda *_args, **_kwargs: None)
    monkeypatch.setattr(documents_api, 'upload_file', lambda *_args, **_kwargs: ('bucket', 'key'))
    monkeypatch.setattr(documents_api, 'download_file', lambda *_args, **_kwargs: b'content')
    monkeypatch.setattr(documents_api, 'extract_text', lambda *_args, **_kwargs: 'Glucose 110 mg/dL 70-99')
    monkeypatch.setattr(
        documents_api,
        'parse_lab_items',
        lambda *_args, **_kwargs: [{'item_name': 'Glucose', 'value_num': 110, 'unit': 'mg/dL', 'abnormal_flag': 'H'}],
    )
    monkeypatch.setattr(documents_api, 'evaluate_lab_item_risks', lambda *_args, **_kwargs: [])

    upload = client.post(
        f'/api/v1/documents/upload?person_id={self_person.id}',
        data={'category': '健檢'},
        files={'file': ('test.pdf', BytesIO(b'dummy'), 'application/pdf')},
    )
    assert upload.status_code == 200
    document_id = upload.json()['id']

    parsed = client.post(f'/api/v1/documents/{document_id}/parse?person_id={self_person.id}')
    assert parsed.status_code == 200
    assert parsed.json()['extracted_items'] == 1

    confirmed = client.put(
        f'/api/v1/documents/{document_id}/confirm?person_id={self_person.id}',
        json={'confirmed_data': {'doctor_note': '已確認'}},
    )
    assert confirmed.status_code == 200
    assert confirmed.json()['parse_status'] == 'confirmed'


def test_external_sync_and_analysis():
    client, _db, self_person = _build_client()
    synced = client.post(f'/api/v1/external-metrics/sync?person_id={self_person.id}')
    assert synced.status_code == 200
    assert synced.json()['synced_count'] > 0

    trends = client.get(f'/api/v1/external-metrics/trends?person_id={self_person.id}&metric=steps')
    assert trends.status_code == 200
    assert trends.json()['metric'] == 'steps'

    analysis = client.get(f'/api/v1/analytics/health-analysis?person_id={self_person.id}')
    assert analysis.status_code == 200
    assert 'disclaimer' in analysis.json()


def test_dashboard_payload_shape():
    client, _db, self_person = _build_client()
    client.post(
        f'/api/v1/metrics?person_id={self_person.id}',
        json={
            'recorded_at': datetime.now(timezone.utc).isoformat(),
            'systolic_bp': 118,
            'diastolic_bp': 76,
            'heart_rate': 82,
            'blood_glucose': 95,
            'weight_kg': 70,
            'sleep_hours': 6.5,
        },
    )
    client.post(
        f'/api/v1/symptoms?person_id={self_person.id}',
        json={
            'symptom': '歷史症狀自述',
            'occurred_at': datetime.now(timezone.utc).isoformat(),
            'duration_minutes': 60,
            'severity': 3,
            'note': '腰痠10年',
            'estimated_duration_days': 3650,
        },
    )

    response = client.get(f'/api/v1/dashboard?person_id={self_person.id}')
    assert response.status_code == 200
    payload = response.json()
    assert 'health_score' in payload
    assert 'alerts' in payload
    assert 'insights' in payload
    assert 'recent_symptoms' in payload
    assert 'recent_metrics' in payload
    assert 'recent_labs' in payload
    assert 'trends' in payload
    assert 'reasoning_summary' in payload
    assert 'predictive_insights' in payload
    assert 'anomaly_alerts' in payload
    assert 'clinical_labels' in payload
    assert 'risk_level' in payload
    assert 'recommendations' in payload
    assert 'health_narrative' in payload
    assert 'health_narrative_v2' in payload
    assert 'narrative_generated_at' in payload
    assert 'explainability_summary' in payload
    assert 'medical_disclaimer' in payload
    assert payload['health_narrative']['summary']
    assert len(payload['health_narrative']['actions']) >= 3
    assert payload['health_narrative_v2']['delta_summary']
    assert len(payload['health_narrative_v2']['actions']) >= 3
    assert '本系統為健康建議工具，非醫療診斷' in payload['medical_disclaimer']
    assert '證據等級' in payload['explainability_summary']
    if payload['recommendations']:
        rec = payload['recommendations'][0]
        assert 'confidence' in rec
        assert 'evidence_level' in rec
        assert 'guideline_source' in rec
        assert 'guideline_version' in rec


def test_insights_generate_and_dismiss():
    client, _db, self_person = _build_client()
    generated = client.post(f'/api/v1/insights/generate?person_id={self_person.id}')
    assert generated.status_code == 200
    items = generated.json()
    assert isinstance(items, list)

    listing = client.get(f'/api/v1/insights?person_id={self_person.id}')
    assert listing.status_code == 200

    if listing.json():
        target_id = listing.json()[0]['id']
        dismissed = client.post(f'/api/v1/insights/{target_id}/dismiss?person_id={self_person.id}')
        assert dismissed.status_code == 200


def test_insights_list_prioritizes_higher_severity_first():
    client, db, self_person = _build_client()
    user = db.query(User).filter(User.email == 'test@example.com').first()
    from app.models.entities import HealthInsight

    low = HealthInsight(
        user_id=user.id,
        subject_profile_id=self_person.id,
        insight_type='trend',
        severity='info',
        title='低優先洞察',
        summary='一般追蹤即可',
        recommendation='',
        generated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        is_active=True,
    )
    high = HealthInsight(
        user_id=user.id,
        subject_profile_id=self_person.id,
        insight_type='alert',
        severity='warning',
        title='高優先洞察',
        summary='需要先處理',
        recommendation='',
        generated_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
        is_active=True,
    )
    db.add_all([low, high])
    db.commit()

    listing = client.get(f'/api/v1/insights?person_id={self_person.id}')
    assert listing.status_code == 200
    items = listing.json()
    assert items[0]['title'] == '高優先洞察'
