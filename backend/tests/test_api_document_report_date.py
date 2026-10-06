"""P104 — Document Confirm report_date write-through tests

Verifies that the PUT /documents/{id}/confirm endpoint correctly handles
the optional report_date field introduced in P104.

Coverage:
  T1 — Confirm with report_date updates LabReport.report_date
  T2 — Confirm without report_date leaves LabReport.report_date unchanged
  T3 — Confirm with report_date still stores confirmed_data
  T4 — Invalid date string returns 422 validation error
"""
from __future__ import annotations

import uuid
from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.deps import get_current_user, get_target_person
from app.main import app
from app.models.entities import LabReport, MedicalDocument, PersonProfile, User


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_db_and_user(email: str = "p104test@example.com") -> tuple[Session, User, PersonProfile]:
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
        display_name="P104 Test",
        relationship="self",
        is_default=True,
    )
    db.add(person)
    db.commit()
    return db, user, person


def _make_doc_and_report(db: Session, user: User, person: PersonProfile) -> tuple[MedicalDocument, LabReport]:
    doc = MedicalDocument(
        id=uuid.uuid4(),
        user_id=user.id,
        subject_profile_id=person.id,
        category="health_check",
        original_filename="test_report.pdf",
        file_type="pdf",
        mime_type="application/pdf",
        file_size=1024,
        storage_bucket="test-bucket",
        storage_key="test/key.pdf",
        parse_status="parsed",
    )
    db.add(doc)
    db.flush()

    lab_report = LabReport(
        id=uuid.uuid4(),
        user_id=user.id,
        subject_profile_id=person.id,
        document_id=doc.id,
        report_date=date(2025, 1, 1),  # placeholder parse-time date
        raw_text="test",
        parser_version="v1",
    )
    db.add(lab_report)
    db.commit()
    return doc, lab_report


def _make_client(db: Session, user: User, person: PersonProfile) -> TestClient:
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_target_person] = lambda: person
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture(autouse=True)
def _clear_overrides():
    yield
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestDocumentConfirmReportDate:
    """PUT /documents/{id}/confirm — report_date write-through contract."""

    def test_confirm_with_report_date_updates_lab_report(self):
        """T1 — When report_date is provided, LabReport.report_date is updated."""
        db, user, person = _make_db_and_user("p104_t1@example.com")
        doc, lab_report = _make_doc_and_report(db, user, person)
        client = _make_client(db, user, person)

        original_date = lab_report.report_date
        assert original_date == date(2025, 1, 1)

        resp = client.put(
            f"/api/v1/documents/{doc.id}/confirm",
            json={"confirmed_data": {"items": [], "extracted_items": 0}, "report_date": "2025-03-12"},
        )
        assert resp.status_code == 200, resp.text

        db.refresh(lab_report)
        assert lab_report.report_date == date(2025, 3, 12), (
            f"Expected 2025-03-12, got {lab_report.report_date}"
        )

    def test_confirm_without_report_date_leaves_lab_report_date_unchanged(self):
        """T2 — When report_date is omitted, LabReport.report_date is not changed."""
        db, user, person = _make_db_and_user("p104_t2@example.com")
        doc, lab_report = _make_doc_and_report(db, user, person)
        client = _make_client(db, user, person)

        resp = client.put(
            f"/api/v1/documents/{doc.id}/confirm",
            json={"confirmed_data": {"items": [], "extracted_items": 3}},
        )
        assert resp.status_code == 200, resp.text

        db.refresh(lab_report)
        assert lab_report.report_date == date(2025, 1, 1), (
            f"LabReport.report_date should be unchanged; got {lab_report.report_date}"
        )

    def test_confirm_with_report_date_still_stores_confirmed_data(self):
        """T3 — report_date does not interfere with confirmed_data storage."""
        db, user, person = _make_db_and_user("p104_t3@example.com")
        doc, _ = _make_doc_and_report(db, user, person)
        client = _make_client(db, user, person)

        payload = {
            "confirmed_data": {"items": [{"name": "ALT", "value": 45}], "extracted_items": 1},
            "report_date": "2025-06-01",
        }
        resp = client.put(f"/api/v1/documents/{doc.id}/confirm", json=payload)
        assert resp.status_code == 200, resp.text

        db.refresh(doc)
        assert doc.confirmed_data is not None
        assert doc.confirmed_data.get("extracted_items") == 1
        assert doc.parse_status == "confirmed"

    def test_confirm_with_invalid_date_returns_422(self):
        """T4 — Invalid date string triggers Pydantic validation error (422)."""
        db, user, person = _make_db_and_user("p104_t4@example.com")
        doc, _ = _make_doc_and_report(db, user, person)
        client = _make_client(db, user, person)

        resp = client.put(
            f"/api/v1/documents/{doc.id}/confirm",
            json={"confirmed_data": {}, "report_date": "not-a-date"},
        )
        assert resp.status_code == 422, (
            f"Expected 422 for invalid date; got {resp.status_code}: {resp.text}"
        )
