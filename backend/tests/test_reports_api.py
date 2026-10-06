from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.deps import get_current_user
from app.main import app
from app.models.entities import PersonProfile, User


def _build_client():
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()

    user = User(email='report-test@example.com', password_hash='hashed')
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
    return TestClient(app), self_person


def test_generate_and_poll_report_ready():
    client, person = _build_client()

    resp = client.post(
        f'/api/v1/reports/generate?person_id={person.id}',
        json={'person_id': str(person.id), 'include_sections': ['score', 'metrics', 'insights']},
    )
    assert resp.status_code == 202
    payload = resp.json()
    assert payload['status'] == 'generating'
    report_id = payload['report_id']

    poll = client.get(f'/api/v1/reports/{report_id}?person_id={person.id}')
    assert poll.status_code == 200
    data = poll.json()
    assert data['status'] == 'ready'
    assert isinstance(data.get('download_url'), str)
    assert len(data.get('download_url') or '') > 0
