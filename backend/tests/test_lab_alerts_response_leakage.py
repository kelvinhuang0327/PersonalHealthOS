"""P36 — Lab Reports & Risk Alerts API Response Audit

Verifies that lab document / parsed-item / lab-history and risk alert API
routes do not expose storage fields (storage_key, storage_bucket, file_path),
user_id, or other sensitive/internal fields to client responses, and that
cross-user person_id access returns 404.

Routes covered
--------------
Documents (lab reports):
  GET  /documents                          → list[DocumentResponse]
  GET  /documents/{id}/parsed-items        → list[ParsedItemResponse] (explicit construction)
  GET  /documents/lab-history              → list[dict] (untyped, explicit construction)

Risk Alerts:
  GET  /risk-alerts                        → list[RiskAlertResponse]
  GET  /risk-alerts/unread-count           → {'count': N} (untyped, explicit dict)
  POST /risk-alerts/{id}/dismiss           → {'ok': True} (untyped, explicit dict)

Coverage map
------------
TestDocumentResponseLeakage
  test_list_documents_no_storage_fields        → GET list: no storage_key / storage_bucket / file_path
  test_list_documents_no_user_id               → GET list: no user_id
  test_list_documents_no_sensitive_keys        → recursive scan on GET list
  test_parsed_items_no_sensitive_keys          → GET parsed-items: recursive scan (explicit construction)
  test_parsed_items_no_user_id                 → GET parsed-items items do not include user_id
  test_lab_history_no_sensitive_keys           → GET lab-history: recursive scan on explicit dict

TestRiskAlertResponseLeakage
  test_list_alerts_no_user_id                  → GET list: user_id absent from RiskAlertResponse items
  test_list_alerts_no_sensitive_keys           → recursive scan
  test_unread_count_shape                      → GET unread-count: only 'count' key, no user_id
  test_dismiss_alert_shape                     → POST dismiss: only 'ok' key, no user_id

TestCrossUserLabAlertsIsolation
  test_cross_user_documents_404                → foreign person_id on GET /documents → 404
  test_cross_user_risk_alerts_404              → foreign person_id on GET /risk-alerts → 404

Strategy:
  HTTP tests use SQLite in-memory DB + get_db override + get_current_user override.
  MedicalDocument seeded with dummy storage_bucket/storage_key (required ORM fields).
  RiskAlert seeded directly with UUID objects (avoids pre-existing str-UUID bug in risk_engine).
  evaluate_metric_risks / run_health_risk_monitor mocked where needed.
  No running server required. Same fixture pattern as P32/P33/P34/P35 suites.

Audit Result:
  No C.GAP found.
  DocumentResponse: A.SAFE (P32 fixed storage fields; user_id absent)
  ParsedItemResponse: A.SAFE (explicit construction; no user_id/report_id/storage)
  GET /documents/lab-history: B.PARTIAL → explicit dict, confirmed safe content
  RiskAlertResponse: A.SAFE (user_id not in schema; from_attributes serializes only declared fields)
  GET /risk-alerts/unread-count: B.PARTIAL → explicit {'count': N}
  POST /risk-alerts/{id}/dismiss: B.PARTIAL → explicit {'ok': True}
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import Any
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.deps import get_current_user
from app.main import app
from app.models.entities import (
    LabReport,
    LabReportItem,
    MedicalDocument,
    PersonProfile,
    RiskAlert,
    User,
)


# ---------------------------------------------------------------------------
# Sensitive key set — same as P32 / P33 / P34 / P35 regression suites
# Extended: user_id included as in P35
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


def _make_db_and_user(email: str = "p36test@example.com") -> tuple[Session, User, PersonProfile]:
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
        display_name="P36 Test User",
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


def _seed_document(db: Session, user: User, person: PersonProfile) -> MedicalDocument:
    """Seed a MedicalDocument with dummy storage fields (required ORM columns).
    The storage fields must NOT appear in DocumentResponse (validated by tests).
    """
    doc = MedicalDocument(
        id=uuid.uuid4(),
        user_id=user.id,
        subject_profile_id=person.id,
        category="lab_report",
        original_filename="blood_test.pdf",
        file_type="pdf",
        mime_type="application/pdf",
        file_size=12345,
        storage_bucket="test-bucket",       # ORM-internal, must NOT appear in response
        storage_key="uploads/test-key.pdf", # ORM-internal, must NOT appear in response
        parse_status="parsed",
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


def _seed_lab_report_with_items(
    db: Session, user: User, person: PersonProfile, doc: MedicalDocument
) -> tuple[LabReport, list[LabReportItem]]:
    report = LabReport(
        id=uuid.uuid4(),
        user_id=user.id,
        subject_profile_id=person.id,
        document_id=doc.id,
        report_date=date.today(),
        report_type="health_check",
        raw_text="test raw text",
        parser_version="v1",
    )
    db.add(report)
    db.flush()

    item = LabReportItem(
        id=uuid.uuid4(),
        report_id=report.id,
        item_name="Glucose",
        value_num=5.2,
        unit="mmol/L",
        ref_range="3.9–6.1",
        abnormal_flag=None,
        parser_confidence=0.95,
    )
    db.add(item)
    db.commit()
    db.refresh(report)
    db.refresh(item)
    return report, [item]


def _seed_confirmed_document_with_history(
    db: Session, user: User, person: PersonProfile
) -> tuple[MedicalDocument, LabReport, LabReportItem]:
    """Seed a confirmed document + lab report + item for lab-history tests."""
    doc = _seed_document(db, user, person)
    doc.confirmed_at = datetime.now(timezone.utc)
    doc.parse_status = "confirmed"
    db.commit()

    report, items = _seed_lab_report_with_items(db, user, person, doc)
    return doc, report, items[0]


def _seed_risk_alert(db: Session, user: User, person: PersonProfile) -> RiskAlert:
    """Seed a RiskAlert directly with UUID objects to avoid the pre-existing
    str-UUID bug in evaluate_metric_risks (risk_engine passes str(user.id)
    into a UUID(as_uuid=True) column, which fails on SQLite)."""
    alert = RiskAlert(
        id=uuid.uuid4(),
        user_id=user.id,              # UUID object — correct
        subject_profile_id=person.id, # UUID object — correct
        source_type="health_metric",
        source_id=uuid.uuid4(),
        risk_type="bp_high",
        rule_code="BP_HIGH",
        severity="high",
        title="Blood Pressure High",
        message="Systolic BP is elevated.",
        description="BP above 140/90 threshold.",
        recommendation="Monitor and consult physician.",
        status="active",
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)
    return alert


# ---------------------------------------------------------------------------
# TestDocumentResponseLeakage
# ---------------------------------------------------------------------------


class TestDocumentResponseLeakage:
    """GET /documents and related lab routes must not expose storage or user fields."""

    def test_list_documents_no_storage_fields(self):
        """GET /documents list items must not contain storage_bucket, storage_key, or file_path."""
        db, user, person = _make_db_and_user()
        _seed_document(db, user, person)
        client = _make_client(db, user)
        resp = client.get(f"/api/v1/documents?person_id={person.id}")
        assert resp.status_code == 200, resp.text
        items = resp.json()
        assert isinstance(items, list)
        assert len(items) >= 1
        for item in items:
            assert "storage_bucket" not in item, (
                f"DocumentResponse must not expose storage_bucket. Got keys: {list(item.keys())}"
            )
            assert "storage_key" not in item, (
                f"DocumentResponse must not expose storage_key. Got keys: {list(item.keys())}"
            )
            assert "file_path" not in item, (
                f"DocumentResponse must not expose file_path. Got keys: {list(item.keys())}"
            )

    def test_list_documents_no_user_id(self):
        """GET /documents list items must not contain user_id."""
        db, user, person = _make_db_and_user()
        _seed_document(db, user, person)
        client = _make_client(db, user)
        resp = client.get(f"/api/v1/documents?person_id={person.id}")
        assert resp.status_code == 200, resp.text
        items = resp.json()
        assert isinstance(items, list)
        assert len(items) >= 1
        for item in items:
            assert "user_id" not in item, (
                f"DocumentResponse must not expose user_id. Got keys: {list(item.keys())}"
            )

    def test_list_documents_no_sensitive_keys(self):
        """GET /documents list response must pass recursive sensitive-key scan."""
        db, user, person = _make_db_and_user()
        _seed_document(db, user, person)
        client = _make_client(db, user)
        resp = client.get(f"/api/v1/documents?person_id={person.id}")
        assert resp.status_code == 200, resp.text
        found = _find_sensitive_key(resp.json())
        assert found is None, (
            f"Sensitive key '{found}' found in GET /documents response. "
            "No storage or credential fields must be exposed to clients."
        )

    def test_parsed_items_no_sensitive_keys(self):
        """GET /documents/{id}/parsed-items must pass recursive sensitive-key scan."""
        db, user, person = _make_db_and_user()
        doc = _seed_document(db, user, person)
        _seed_lab_report_with_items(db, user, person, doc)
        client = _make_client(db, user)
        resp = client.get(f"/api/v1/documents/{doc.id}/parsed-items?person_id={person.id}")
        assert resp.status_code == 200, resp.text
        found = _find_sensitive_key(resp.json())
        assert found is None, (
            f"Sensitive key '{found}' found in GET parsed-items response."
        )

    def test_parsed_items_no_user_id(self):
        """ParsedItemResponse items must not expose user_id or report_id."""
        db, user, person = _make_db_and_user()
        doc = _seed_document(db, user, person)
        _seed_lab_report_with_items(db, user, person, doc)
        client = _make_client(db, user)
        resp = client.get(f"/api/v1/documents/{doc.id}/parsed-items?person_id={person.id}")
        assert resp.status_code == 200, resp.text
        items = resp.json()
        assert isinstance(items, list)
        assert len(items) >= 1
        for item in items:
            assert "user_id" not in item, (
                f"ParsedItemResponse must not expose user_id. Got keys: {list(item.keys())}"
            )
            assert "report_id" not in item, (
                f"ParsedItemResponse must not expose internal report_id. Got keys: {list(item.keys())}"
            )

    def test_lab_history_no_sensitive_keys(self):
        """GET /documents/lab-history must pass recursive sensitive-key scan (explicit dict response)."""
        db, user, person = _make_db_and_user()
        _seed_confirmed_document_with_history(db, user, person)
        client = _make_client(db, user)
        resp = client.get(f"/api/v1/documents/lab-history?person_id={person.id}")
        assert resp.status_code == 200, resp.text
        found = _find_sensitive_key(resp.json())
        assert found is None, (
            f"Sensitive key '{found}' found in GET /documents/lab-history response. "
            "No storage or user fields must appear in the untyped dict response."
        )


# ---------------------------------------------------------------------------
# TestRiskAlertResponseLeakage
# ---------------------------------------------------------------------------


class TestRiskAlertResponseLeakage:
    """GET /risk-alerts and related routes must not expose user_id or sensitive fields."""

    def test_list_alerts_no_user_id(self):
        """GET /risk-alerts list items must not expose user_id."""
        db, user, person = _make_db_and_user()
        _seed_risk_alert(db, user, person)
        client = _make_client(db, user)
        resp = client.get(f"/api/v1/risk-alerts?person_id={person.id}")
        assert resp.status_code == 200, resp.text
        items = resp.json()
        assert isinstance(items, list)
        assert len(items) >= 1
        for item in items:
            assert "user_id" not in item, (
                f"RiskAlertResponse must not expose user_id. Got keys: {list(item.keys())}"
            )

    def test_list_alerts_no_sensitive_keys(self):
        """GET /risk-alerts list response must pass recursive sensitive-key scan."""
        db, user, person = _make_db_and_user()
        _seed_risk_alert(db, user, person)
        client = _make_client(db, user)
        resp = client.get(f"/api/v1/risk-alerts?person_id={person.id}")
        assert resp.status_code == 200, resp.text
        found = _find_sensitive_key(resp.json())
        assert found is None, (
            f"Sensitive key '{found}' found in GET /risk-alerts response."
        )

    def test_unread_count_shape(self):
        """GET /risk-alerts/unread-count must return only {'count': N}; no user_id."""
        db, user, person = _make_db_and_user()
        _seed_risk_alert(db, user, person)
        client = _make_client(db, user)
        resp = client.get(f"/api/v1/risk-alerts/unread-count?person_id={person.id}")
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert "count" in body, "unread-count response must include 'count'"
        assert isinstance(body["count"], int)
        assert "user_id" not in body, (
            f"unread-count must not expose user_id. Got keys: {list(body.keys())}"
        )
        # Only 'count' key expected
        assert set(body.keys()) == {"count"}, (
            f"unread-count response unexpectedly contains extra keys: {set(body.keys()) - {'count'}}"
        )

    def test_dismiss_alert_shape(self):
        """POST /risk-alerts/{id}/dismiss must return only {'ok': True}; no user_id."""
        db, user, person = _make_db_and_user()
        alert = _seed_risk_alert(db, user, person)
        client = _make_client(db, user)
        resp = client.post(f"/api/v1/risk-alerts/{alert.id}/dismiss")
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert "ok" in body, "dismiss response must include 'ok'"
        assert body["ok"] is True
        assert "user_id" not in body, (
            f"dismiss response must not expose user_id. Got keys: {list(body.keys())}"
        )
        # Only 'ok' key expected
        assert set(body.keys()) == {"ok"}, (
            f"dismiss response unexpectedly contains extra keys: {set(body.keys()) - {'ok'}}"
        )


# ---------------------------------------------------------------------------
# TestCrossUserLabAlertsIsolation
# ---------------------------------------------------------------------------


class TestCrossUserLabAlertsIsolation:
    """Cross-user person_id on lab/alert routes must return 404."""

    def test_cross_user_documents_404(self):
        """GET /documents with a foreign person_id must return 404."""
        db, user_a, _ = _make_db_and_user("p36a@example.com")

        user_b = User(
            id=uuid.uuid4(),
            email="p36b@example.com",
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
        resp = client.get(f"/api/v1/documents?person_id={person_b.id}")
        assert resp.status_code == 404, (
            f"Expected 404 for foreign person_id on GET /documents, got {resp.status_code}"
        )

    def test_cross_user_risk_alerts_404(self):
        """GET /risk-alerts with a foreign person_id must return 404."""
        db, user_a, _ = _make_db_and_user("p36c@example.com")

        user_b = User(
            id=uuid.uuid4(),
            email="p36d@example.com",
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
        resp = client.get(f"/api/v1/risk-alerts?person_id={person_b.id}")
        assert resp.status_code == 404, (
            f"Expected 404 for foreign person_id on GET /risk-alerts, got {resp.status_code}"
        )
