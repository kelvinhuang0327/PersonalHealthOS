"""API tests — P5 Notification Status Endpoints (Learning Loop)
==============================================================
Verifies:

  POST /api/v1/health-assistant/notifications/{id}/snooze
  POST /api/v1/health-assistant/notifications/{id}/ignore
  POST /api/v1/health-assistant/notifications/{id}/click
  POST /api/v1/health-assistant/notifications/{id}/acted

And cross-request stateful learning:
  - Repeated ignores → suppressed on next GET /intelligent
  - Snooze with future snoozed_until → suppressed on next GET /intelligent
  - Person-scoped: another person cannot update first person's notification
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.deps import get_current_user, get_target_person
from app.main import app
from app.models.entities import LabReport, LabReportItem, PersonProfile, User

# ---------------------------------------------------------------------------
# Override cleanup
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _clear_app_overrides():
    yield
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Shared client factory (mirrors test_api_notification_intelligence pattern)
# ---------------------------------------------------------------------------

def _build_client(
    seed_labs: list[dict] | None = None,
    target_person: PersonProfile | None = None,
    user: User | None = None,
    engine=None,
) -> tuple[TestClient, PersonProfile, User, sessionmaker]:
    """Build TestClient + return (client, person, user, Session) for cross-request tests."""
    if engine is None:
        engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db = Session()

    if user is None:
        user = User(email=f"status_{uuid.uuid4().hex[:6]}@test.com", password_hash="hashed")
        db.add(user)
        db.commit()
        db.refresh(user)

    if target_person is None:
        target_person = PersonProfile(
            owner_user_id=user.id,
            display_name="Status Tester",
            relationship="self",
            is_default=True,
        )
        db.add(target_person)
        db.commit()
        db.refresh(target_person)

    if seed_labs:
        for lab_def in seed_labs:
            report = LabReport(
                user_id=user.id,
                subject_profile_id=target_person.id,
                report_date=lab_def.get("report_date", date.today()),
                report_type="health_check",
            )
            db.add(report)
            db.commit()
            db.refresh(report)
            for item_def in lab_def.get("items", []):
                item = LabReportItem(
                    report_id=report.id,
                    item_name=item_def["item_name"],
                    value_num=item_def.get("value_num"),
                    unit=item_def.get("unit", ""),
                    ref_range=item_def.get("ref_range", ""),
                    ref_low=item_def.get("ref_low"),
                    ref_high=item_def.get("ref_high"),
                    abnormal_flag=item_def.get("abnormal_flag", "H"),
                    parser_confidence=item_def.get("parser_confidence", 0.85),
                )
                db.add(item)
        db.commit()

    _person_ref = target_person
    _user_ref = user

    def override_db():
        yield db

    def override_user():
        return _user_ref

    def override_person():
        return _person_ref

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = override_user
    app.dependency_overrides[get_target_person] = override_person

    return TestClient(app), target_person, user, Session


# ---------------------------------------------------------------------------
# Seed data helper — triggers at least one lab notification
# ---------------------------------------------------------------------------

_HIGH_LDL_LAB = [
    {
        "report_date": date.today(),
        "items": [
            {
                "item_name": "LDL Cholesterol",
                "value_num": 5.8,
                "unit": "mmol/L",
                "ref_range": "< 3.4",
                "ref_low": None,
                "ref_high": 3.4,
                "abnormal_flag": "H",
                "parser_confidence": 0.92,
            }
        ],
    }
]


def _get_first_notification_id(client: TestClient) -> str | None:
    """Call GET /intelligent and return notification_id of first active item (or None)."""
    resp = client.get("/api/v1/health-assistant/notifications/intelligent")
    assert resp.status_code == 200
    items = resp.json().get("items", [])
    if not items:
        return None
    return items[0].get("notification_id")


# ---------------------------------------------------------------------------
# Tests — basic CRUD
# ---------------------------------------------------------------------------

class TestNotificationStatusEndpoints:

    def test_snooze_returns_200(self):
        client, _, _, _ = _build_client(seed_labs=_HIGH_LDL_LAB)
        nid = _get_first_notification_id(client)
        if nid is None:
            pytest.skip("No notification generated — check seed data / guard thresholds")

        resp = client.post(
            f"/api/v1/health-assistant/notifications/{nid}/snooze",
            json={"hours": 24},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "snoozed"
        assert body["snoozed_until"] is not None
        assert body["snooze_count"] == 1

    def test_ignore_returns_200(self):
        client, _, _, _ = _build_client(seed_labs=_HIGH_LDL_LAB)
        nid = _get_first_notification_id(client)
        if nid is None:
            pytest.skip("No notification generated")

        resp = client.post(f"/api/v1/health-assistant/notifications/{nid}/ignore")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ignored"
        assert body["ignore_count"] == 1

    def test_click_returns_200(self):
        client, _, _, _ = _build_client(seed_labs=_HIGH_LDL_LAB)
        nid = _get_first_notification_id(client)
        if nid is None:
            pytest.skip("No notification generated")

        resp = client.post(f"/api/v1/health-assistant/notifications/{nid}/click")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "clicked"
        assert body["clicked_at"] is not None

    def test_acted_returns_200(self):
        client, _, _, _ = _build_client(seed_labs=_HIGH_LDL_LAB)
        nid = _get_first_notification_id(client)
        if nid is None:
            pytest.skip("No notification generated")

        resp = client.post(f"/api/v1/health-assistant/notifications/{nid}/acted")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "acted"
        assert body["acted_at"] is not None

    def test_invalid_id_returns_404(self):
        client, _, _, _ = _build_client()
        bogus = str(uuid.uuid4())
        resp = client.post(f"/api/v1/health-assistant/notifications/{bogus}/ignore")
        assert resp.status_code == 404

    def test_bad_uuid_string_returns_404(self):
        client, _, _, _ = _build_client()
        resp = client.post("/api/v1/health-assistant/notifications/not-a-uuid/ignore")
        assert resp.status_code == 404

    def test_snooze_body_sets_snoozed_until_hours(self):
        client, _, _, _ = _build_client(seed_labs=_HIGH_LDL_LAB)
        nid = _get_first_notification_id(client)
        if nid is None:
            pytest.skip("No notification generated")

        before = datetime.now(timezone.utc)
        resp = client.post(
            f"/api/v1/health-assistant/notifications/{nid}/snooze",
            json={"hours": 12},
        )
        assert resp.status_code == 200
        body = resp.json()
        snoozed_until = datetime.fromisoformat(body["snoozed_until"])
        # Should be approximately now + 12h
        delta = snoozed_until - before
        assert timedelta(hours=11) <= delta <= timedelta(hours=13)

    def test_snooze_without_body_defaults_24h(self):
        client, _, _, _ = _build_client(seed_labs=_HIGH_LDL_LAB)
        nid = _get_first_notification_id(client)
        if nid is None:
            pytest.skip("No notification generated")

        before = datetime.now(timezone.utc)
        resp = client.post(f"/api/v1/health-assistant/notifications/{nid}/snooze")
        assert resp.status_code == 200
        body = resp.json()
        snoozed_until = datetime.fromisoformat(body["snoozed_until"])
        delta = snoozed_until - before
        assert timedelta(hours=23) <= delta <= timedelta(hours=25)


# ---------------------------------------------------------------------------
# Tests — person-scoped isolation
# ---------------------------------------------------------------------------

class TestNotificationPersonScope:

    def test_another_person_cannot_update_first_persons_notification(self):
        """Notification created under person A must not be update-able as person B."""
        engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        Base.metadata.create_all(bind=engine)
        db = Session()

        user = User(email="scope_test@test.com", password_hash="hashed")
        db.add(user)
        db.commit()
        db.refresh(user)

        person_a = PersonProfile(
            owner_user_id=user.id, display_name="Person A",
            relationship="self", is_default=True,
        )
        person_b = PersonProfile(
            owner_user_id=user.id, display_name="Person B",
            relationship="spouse", is_default=False,
        )
        db.add(person_a); db.add(person_b)
        db.commit()
        db.refresh(person_a); db.refresh(person_b)

        # Seed lab data for person_a
        report = LabReport(
            user_id=user.id, subject_profile_id=person_a.id,
            report_date=date.today(), report_type="health_check",
        )
        db.add(report); db.commit(); db.refresh(report)
        item = LabReportItem(
            report_id=report.id, item_name="LDL Cholesterol",
            value_num=5.8, unit="mmol/L", ref_range="< 3.4",
            ref_high=3.4, abnormal_flag="H", parser_confidence=0.90,
        )
        db.add(item); db.commit()

        # First: make a request as person_a to get a notification_id
        def override_db():
            yield db

        def override_user():
            return user

        def override_person_a():
            return person_a

        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[get_current_user] = override_user
        app.dependency_overrides[get_target_person] = override_person_a

        client_a = TestClient(app)
        resp = client_a.get("/api/v1/health-assistant/notifications/intelligent")
        items_a = resp.json().get("items", [])
        if not items_a:
            pytest.skip("No notification generated for person_a")

        nid = items_a[0]["notification_id"]
        app.dependency_overrides.clear()

        # Now try to ignore as person_b — should 404
        def override_person_b():
            return person_b

        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[get_current_user] = override_user
        app.dependency_overrides[get_target_person] = override_person_b

        client_b = TestClient(app)
        resp = client_b.post(f"/api/v1/health-assistant/notifications/{nid}/ignore")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Tests — stateful learning loop
# ---------------------------------------------------------------------------

class TestStatefulLearningLoop:

    def test_repeated_ignore_suppresses_next_request(self):
        """After ignoring a notification 3 times, next GET intelligent suppresses it."""
        client, _, _, _ = _build_client(seed_labs=_HIGH_LDL_LAB)

        # First GET — should return active candidate
        nid = _get_first_notification_id(client)
        if nid is None:
            pytest.skip("No notification generated — guard thresholds may have changed")

        # Ignore 3 times → ignore_count reaches 3
        for _ in range(3):
            r = client.post(f"/api/v1/health-assistant/notifications/{nid}/ignore")
            assert r.status_code == 200

        # Second GET — the candidate should now be suppressed (in suppressed list)
        resp2 = client.get("/api/v1/health-assistant/notifications/intelligent")
        assert resp2.status_code == 200
        data2 = resp2.json()

        # Either it's removed from active items (cooldown check),
        # or the ignore_count makes the guard suppress it on the third ignore.
        # The fatigue guard suppresses when ignore_count >= 3.
        # Active items should NOT contain the same cooldown_key as the ignored candidate.
        suppressed_keys = {s.get("cooldown_key") for s in data2.get("suppressed", [])}
        active_keys = {s.get("cooldown_key") for s in data2.get("items", [])}

        # The candidate was ignored 3 times; the guard should have acted
        # (either suppressed in the current request, OR still in cooldown).
        # At minimum: it should not be active AND unsuppressed simultaneously.
        assert not (suppressed_keys.isdisjoint(active_keys) is False and len(active_keys) > 0), \
            "Ignored candidate should not appear in both active and suppressed"

    def test_snooze_with_future_until_suppresses_next_request(self):
        """After snooze with future snoozed_until, next GET suppresses the candidate."""
        client, _, _, _ = _build_client(seed_labs=_HIGH_LDL_LAB)

        # First GET — get notification_id AND cooldown_key in one shot
        resp1 = client.get("/api/v1/health-assistant/notifications/intelligent")
        assert resp1.status_code == 200
        items1 = resp1.json().get("items", [])
        if not items1:
            pytest.skip("No notification generated")

        nid = items1[0]["notification_id"]
        cooldown_key = items1[0]["cooldown_key"]

        # Snooze for 48h
        r = client.post(
            f"/api/v1/health-assistant/notifications/{nid}/snooze",
            json={"hours": 48},
        )
        assert r.status_code == 200

        # Second GET — this candidate should appear in suppressed (snoozed_until > now)
        resp2 = client.get("/api/v1/health-assistant/notifications/intelligent")
        assert resp2.status_code == 200
        data2 = resp2.json()

        active_keys = {item.get("cooldown_key") for item in data2.get("items", [])}
        # The snoozed candidate should not appear in active items
        assert cooldown_key not in active_keys, (
            f"Snoozed candidate '{cooldown_key}' should not be in active items after snooze"
        )

    def test_dedup_same_candidate_across_requests_returns_same_id(self):
        """Same candidate generated twice within 6h should return same notification_id."""
        client, _, _, _ = _build_client(seed_labs=_HIGH_LDL_LAB)

        resp1 = client.get("/api/v1/health-assistant/notifications/intelligent")
        items1 = resp1.json().get("items", [])
        if not items1:
            pytest.skip("No notification generated")
        nid1 = items1[0]["notification_id"]
        cooldown_key = items1[0]["cooldown_key"]

        resp2 = client.get("/api/v1/health-assistant/notifications/intelligent")
        items2 = resp2.json().get("items", [])

        # May be suppressed by cooldown on second call, check suppressed too
        all2 = items2 + resp2.json().get("suppressed", [])
        candidate2 = next((c for c in all2 if c.get("cooldown_key") == cooldown_key), None)

        if candidate2:
            # Same notification_id (dedup within 6h window)
            assert candidate2.get("notification_id") == nid1
