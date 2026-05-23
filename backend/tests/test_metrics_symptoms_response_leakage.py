"""P35 — Metrics & Symptoms API user_id Exposure Audit

Verifies that the dedicated metrics and symptoms CRUD API routes do not
expose the ORM-internal `user_id` column or any other sensitive/internal
field to client responses, and that cross-user `person_id` access returns
404 on both APIs.

Routes covered
--------------
POST /metrics           → MetricResponse
GET  /metrics           → list[MetricResponse]
GET  /metrics/latest    → Optional[MetricResponse]
POST /symptoms          → SymptomResponse
GET  /symptoms          → list[SymptomResponse]
PUT  /symptoms/{id}     → SymptomResponse

Coverage map
------------
TestMetricsResponseLeakage
  test_create_metric_status_201             → baseline — route accessible, returns 201 or 200
  test_create_metric_no_user_id             → POST response must not expose user_id
  test_create_metric_no_sensitive_keys      → recursive scan on POST response
  test_list_metrics_no_user_id              → GET list items must not expose user_id
  test_list_metrics_no_sensitive_keys       → recursive scan on GET list response
  test_latest_metric_no_user_id             → GET /latest must not expose user_id
  test_metric_response_fields              → id + subject_profile_id present; user_id absent

TestSymptomsResponseLeakage
  test_create_symptom_no_user_id            → POST response must not expose user_id
  test_create_symptom_no_sensitive_keys     → recursive scan on POST response
  test_list_symptoms_no_user_id             → GET list items must not expose user_id
  test_list_symptoms_no_sensitive_keys      → recursive scan on GET list response
  test_update_symptom_no_user_id            → PUT response must not expose user_id
  test_symptom_response_fields             → id + subject_profile_id present; user_id absent

TestCrossUserMetricsSymptomsIsolation
  test_cross_user_metrics_404              → foreign person_id on GET /metrics → 404
  test_cross_user_symptoms_404             → foreign person_id on GET /symptoms → 404

Strategy:
  HTTP tests use SQLite in-memory DB + get_db override + get_current_user override.
  No running server required. Same fixture pattern as P32/P33/P34 suites.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.deps import get_current_user
from app.main import app
from app.models.entities import HealthMetric, PersonProfile, SymptomLog, User


# ---------------------------------------------------------------------------
# Sensitive key set — same as P32 / P33 / P34 regression suites
# ---------------------------------------------------------------------------

_SENSITIVE_KEYS: frozenset[str] = frozenset({
    "password_hash",
    "hashed_password",
    "password",
    "storage_bucket",
    "storage_key",
    "file_path",
    "download_token",
    "secret_key",
    "secret",
    "is_superuser",
    "is_staff",
    "user_id",
})


def _find_sensitive_key(obj: Any, path: str = "") -> str | None:
    """Recursively scan a deserialized JSON object for sensitive key names.

    Returns the first offending key path, or None if clean.
    """
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k.lower() in _SENSITIVE_KEYS:
                return f"{path}.{k}" if path else k
            found = _find_sensitive_key(v, f"{path}.{k}" if path else k)
            if found:
                return found
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            found = _find_sensitive_key(item, f"{path}[{i}]")
            if found:
                return found
    return None


# ---------------------------------------------------------------------------
# Shared DB + user helpers
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _clear_overrides():
    yield
    app.dependency_overrides.clear()


def _make_db_and_user(email: str = "p35test@example.com") -> tuple[Session, User, PersonProfile]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db: Session = SLocal()

    user = User(
        id=uuid.uuid4(),
        email=email,
        password_hash="hashed_not_real",
        is_active=True,
    )
    db.add(user)
    db.flush()

    person = PersonProfile(
        id=uuid.uuid4(),
        owner_user_id=user.id,
        display_name="P35 Test User",
        relationship="self",
        is_default=True,
    )
    db.add(person)
    db.commit()
    return db, user, person


def _make_client(db: Session, user: User) -> TestClient:
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: user
    return TestClient(app, raise_server_exceptions=False)


def _seed_metric(db: Session, user: User, person: PersonProfile) -> HealthMetric:
    metric = HealthMetric(
        id=uuid.uuid4(),
        user_id=user.id,
        subject_profile_id=person.id,
        recorded_at=datetime.now(timezone.utc),
        heart_rate=72,
        source="manual",
    )
    db.add(metric)
    db.commit()
    db.refresh(metric)
    return metric


def _seed_symptom(db: Session, user: User, person: PersonProfile) -> SymptomLog:
    symptom = SymptomLog(
        id=uuid.uuid4(),
        user_id=user.id,
        subject_profile_id=person.id,
        symptom="headache",
        occurred_at=datetime.now(timezone.utc),
        severity=2,
    )
    db.add(symptom)
    db.commit()
    db.refresh(symptom)
    return symptom


# ---------------------------------------------------------------------------
# TestMetricsResponseLeakage
# ---------------------------------------------------------------------------


class TestMetricsResponseLeakage:
    """POST/GET /metrics responses must not expose user_id or sensitive fields."""

    _METRIC_PAYLOAD = {
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "heart_rate": 72,
    }

    def test_create_metric_status_201(self):
        db, user, person = _make_db_and_user()
        client = _make_client(db, user)
        # Mock risk engine: pre-existing bug where it passes str(uuid) into UUID column on SQLite
        with patch("app.api.metrics.evaluate_metric_risks", return_value=[]):
            resp = client.post(
                f"/api/v1/metrics?person_id={person.id}",
                json=self._METRIC_PAYLOAD,
            )
        assert resp.status_code in (200, 201), resp.text

    def test_create_metric_no_user_id(self):
        """POST /metrics response must not expose user_id."""
        db, user, person = _make_db_and_user()
        client = _make_client(db, user)
        with patch("app.api.metrics.evaluate_metric_risks", return_value=[]):
            resp = client.post(
                f"/api/v1/metrics?person_id={person.id}",
                json=self._METRIC_PAYLOAD,
            )
        assert resp.status_code in (200, 201), resp.text
        body = resp.json()
        assert "user_id" not in body, (
            f"MetricResponse must not expose user_id. Got keys: {list(body.keys())}"
        )

    def test_create_metric_no_sensitive_keys(self):
        """POST /metrics response must pass recursive sensitive-key scan."""
        db, user, person = _make_db_and_user()
        client = _make_client(db, user)
        with patch("app.api.metrics.evaluate_metric_risks", return_value=[]):
            resp = client.post(
                f"/api/v1/metrics?person_id={person.id}",
                json=self._METRIC_PAYLOAD,
            )
        assert resp.status_code in (200, 201), resp.text
        found = _find_sensitive_key(resp.json())
        assert found is None, (
            f"Sensitive key '{found}' found in POST /metrics response. "
            "No internal fields must be exposed to clients."
        )

    def test_list_metrics_no_user_id(self):
        """GET /metrics list items must not expose user_id."""
        db, user, person = _make_db_and_user()
        _seed_metric(db, user, person)
        client = _make_client(db, user)
        resp = client.get(f"/api/v1/metrics?person_id={person.id}")
        assert resp.status_code == 200, resp.text
        items = resp.json()
        assert isinstance(items, list)
        assert len(items) >= 1
        for item in items:
            assert "user_id" not in item, (
                f"MetricResponse list item must not expose user_id. Got keys: {list(item.keys())}"
            )

    def test_list_metrics_no_sensitive_keys(self):
        """GET /metrics list response must pass recursive sensitive-key scan."""
        db, user, person = _make_db_and_user()
        _seed_metric(db, user, person)
        client = _make_client(db, user)
        resp = client.get(f"/api/v1/metrics?person_id={person.id}")
        assert resp.status_code == 200, resp.text
        found = _find_sensitive_key(resp.json())
        assert found is None, (
            f"Sensitive key '{found}' found in GET /metrics response."
        )

    def test_latest_metric_no_user_id(self):
        """GET /metrics/latest must not expose user_id."""
        db, user, person = _make_db_and_user()
        _seed_metric(db, user, person)
        client = _make_client(db, user)
        resp = client.get(f"/api/v1/metrics/latest?person_id={person.id}")
        assert resp.status_code == 200, resp.text
        body = resp.json()
        if body is not None:
            assert "user_id" not in body, (
                f"MetricResponse (latest) must not expose user_id. Got keys: {list(body.keys())}"
            )

    def test_metric_response_fields(self):
        """MetricResponse must include id and subject_profile_id; must NOT include user_id."""
        db, user, person = _make_db_and_user()
        client = _make_client(db, user)
        with patch("app.api.metrics.evaluate_metric_risks", return_value=[]):
            resp = client.post(
                f"/api/v1/metrics?person_id={person.id}",
                json=self._METRIC_PAYLOAD,
            )
        assert resp.status_code in (200, 201), resp.text
        body = resp.json()
        assert "id" in body, "MetricResponse must include 'id'"
        assert "subject_profile_id" in body, "MetricResponse must include 'subject_profile_id'"
        assert "user_id" not in body, "MetricResponse must NOT include 'user_id'"


# ---------------------------------------------------------------------------
# TestSymptomsResponseLeakage
# ---------------------------------------------------------------------------


class TestSymptomsResponseLeakage:
    """POST/GET/PUT /symptoms responses must not expose user_id or sensitive fields."""

    _SYMPTOM_PAYLOAD = {
        "symptom": "headache",
        "severity": 2,
        "occurred_at": datetime.now(timezone.utc).isoformat(),
    }

    def test_create_symptom_no_user_id(self):
        """POST /symptoms response must not expose user_id."""
        db, user, person = _make_db_and_user()
        client = _make_client(db, user)
        resp = client.post(
            f"/api/v1/symptoms?person_id={person.id}",
            json=self._SYMPTOM_PAYLOAD,
        )
        assert resp.status_code in (200, 201), resp.text
        body = resp.json()
        assert "user_id" not in body, (
            f"SymptomResponse must not expose user_id. Got keys: {list(body.keys())}"
        )

    def test_create_symptom_no_sensitive_keys(self):
        """POST /symptoms response must pass recursive sensitive-key scan."""
        db, user, person = _make_db_and_user()
        client = _make_client(db, user)
        resp = client.post(
            f"/api/v1/symptoms?person_id={person.id}",
            json=self._SYMPTOM_PAYLOAD,
        )
        assert resp.status_code in (200, 201), resp.text
        found = _find_sensitive_key(resp.json())
        assert found is None, (
            f"Sensitive key '{found}' found in POST /symptoms response."
        )

    def test_list_symptoms_no_user_id(self):
        """GET /symptoms list items must not expose user_id."""
        db, user, person = _make_db_and_user()
        _seed_symptom(db, user, person)
        client = _make_client(db, user)
        resp = client.get(f"/api/v1/symptoms?person_id={person.id}")
        assert resp.status_code == 200, resp.text
        items = resp.json()
        assert isinstance(items, list)
        assert len(items) >= 1
        for item in items:
            assert "user_id" not in item, (
                f"SymptomResponse list item must not expose user_id. Got keys: {list(item.keys())}"
            )

    def test_list_symptoms_no_sensitive_keys(self):
        """GET /symptoms list response must pass recursive sensitive-key scan."""
        db, user, person = _make_db_and_user()
        _seed_symptom(db, user, person)
        client = _make_client(db, user)
        resp = client.get(f"/api/v1/symptoms?person_id={person.id}")
        assert resp.status_code == 200, resp.text
        found = _find_sensitive_key(resp.json())
        assert found is None, (
            f"Sensitive key '{found}' found in GET /symptoms response."
        )

    def test_update_symptom_no_user_id(self):
        """PUT /symptoms/{id} response must not expose user_id."""
        db, user, person = _make_db_and_user()
        symptom = _seed_symptom(db, user, person)
        client = _make_client(db, user)
        resp = client.put(
            f"/api/v1/symptoms/{symptom.id}?person_id={person.id}",
            json={"severity": 3},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert "user_id" not in body, (
            f"SymptomResponse (PUT) must not expose user_id. Got keys: {list(body.keys())}"
        )

    def test_symptom_response_fields(self):
        """SymptomResponse must include id and subject_profile_id; must NOT include user_id."""
        db, user, person = _make_db_and_user()
        client = _make_client(db, user)
        resp = client.post(
            f"/api/v1/symptoms?person_id={person.id}",
            json=self._SYMPTOM_PAYLOAD,
        )
        assert resp.status_code in (200, 201), resp.text
        body = resp.json()
        assert "id" in body, "SymptomResponse must include 'id'"
        assert "subject_profile_id" in body, "SymptomResponse must include 'subject_profile_id'"
        assert "user_id" not in body, "SymptomResponse must NOT include 'user_id'"


# ---------------------------------------------------------------------------
# TestCrossUserMetricsSymptomsIsolation
# ---------------------------------------------------------------------------


class TestCrossUserMetricsSymptomsIsolation:
    """Cross-user person_id on metrics/symptoms routes must return 404."""

    def test_cross_user_metrics_404(self):
        """GET /metrics with a foreign person_id must return 404."""
        db, user_a, _ = _make_db_and_user("p35a@example.com")

        # Create a second user + person in the same DB
        user_b = User(
            id=uuid.uuid4(),
            email="p35b@example.com",
            password_hash="hashed_not_real",
            is_active=True,
        )
        db.add(user_b)
        db.flush()
        person_b = PersonProfile(
            id=uuid.uuid4(),
            owner_user_id=user_b.id,
            display_name="User B",
            relationship="self",
            is_default=True,
        )
        db.add(person_b)
        db.commit()

        # user_a authenticates but targets user_b's person_id
        client = _make_client(db, user_a)
        resp = client.get(f"/api/v1/metrics?person_id={person_b.id}")
        assert resp.status_code == 404, (
            f"Expected 404 when accessing foreign person_id on /metrics, got {resp.status_code}"
        )

    def test_cross_user_symptoms_404(self):
        """GET /symptoms with a foreign person_id must return 404."""
        db, user_a, _ = _make_db_and_user("p35c@example.com")

        user_b = User(
            id=uuid.uuid4(),
            email="p35d@example.com",
            password_hash="hashed_not_real",
            is_active=True,
        )
        db.add(user_b)
        db.flush()
        person_b = PersonProfile(
            id=uuid.uuid4(),
            owner_user_id=user_b.id,
            display_name="User B",
            relationship="self",
            is_default=True,
        )
        db.add(person_b)
        db.commit()

        client = _make_client(db, user_a)
        resp = client.get(f"/api/v1/symptoms?person_id={person_b.id}")
        assert resp.status_code == 404, (
            f"Expected 404 when accessing foreign person_id on /symptoms, got {resp.status_code}"
        )
