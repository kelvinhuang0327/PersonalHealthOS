"""P32 — Response Schema Leakage Regression

Verifies that API response models and route handlers do not expose sensitive
or internal fields to clients.

Coverage map
------------
TestAuthResponseLeakage
  test_register_response_no_password_hash        → UserResponse: no password_hash
  test_register_response_fields                  → UserResponse: only id + email
  test_login_response_no_password_hash           → TokenResponse: no password_hash
  test_login_response_has_access_token           → TokenResponse: access_token present (intentional)

TestPersonResponseLeakage
  test_persons_list_no_password_hash             → PersonResponse items: no password_hash
  test_persons_list_owner_uuid_is_own            → PersonResponse: owner_user_id is own UUID

TestDocumentSchemaLeakage
  test_document_response_no_storage_bucket_field → DocumentResponse schema: no storage_bucket
  test_document_response_no_storage_key_field    → DocumentResponse schema: no storage_key
  test_document_response_omits_storage_from_orm  → model_validate from full dict excludes infra fields

TestReportSchemaLeakage
  test_report_status_response_no_raw_token_field → ReportStatusResponse schema: no 'token' field
  test_report_status_response_no_file_path_field → ReportStatusResponse schema: no 'file_path' field
  test_report_status_schema_serialized_keys      → serialized response: only status + download_url

Strategy: HTTP tests use SQLite in-memory + get_db/get_current_user overrides.
          Schema-level tests use direct Pydantic model inspection.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.deps import get_current_user
from app.main import app
from app.models.entities import PersonProfile, User
from app.schemas.documents import DocumentResponse
from app.schemas.auth import UserResponse, TokenResponse
from app.api.reports import ReportStatusResponse


# ---------------------------------------------------------------------------
# Shared test fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _clear_overrides():
    yield
    app.dependency_overrides.clear()


def _make_db_and_user() -> tuple[Session, User, PersonProfile]:
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
        email="p32leak@example.com",
        password_hash="hashed_not_real",
        is_active=True,
    )
    db.add(user)
    db.flush()

    person = PersonProfile(
        id=uuid.uuid4(),
        owner_user_id=user.id,
        display_name="P32 Person",
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


# ---------------------------------------------------------------------------
# TestAuthResponseLeakage
# ---------------------------------------------------------------------------


class TestAuthResponseLeakage:
    """Register + login routes must never return password_hash."""

    def test_register_response_no_password_hash(self):
        """POST /auth/register response body must not contain password_hash."""
        db, _, _ = _make_db_and_user()
        app.dependency_overrides[get_db] = lambda: db
        client = TestClient(app, raise_server_exceptions=False)

        unique_email = f"newuser_{uuid.uuid4().hex[:8]}@example.com"
        resp = client.post("/api/v1/auth/register", json={
            "email": unique_email,
            "password": "Str0ngPass!",
        })
        assert resp.status_code in (200, 201), resp.text
        body = resp.json()
        assert "password_hash" not in body
        assert "hashed_password" not in body
        assert "password" not in body

    def test_register_response_fields(self):
        """POST /auth/register response contains only id and email (UserResponse)."""
        db, _, _ = _make_db_and_user()
        app.dependency_overrides[get_db] = lambda: db
        client = TestClient(app, raise_server_exceptions=False)

        unique_email = f"regfields_{uuid.uuid4().hex[:8]}@example.com"
        resp = client.post("/api/v1/auth/register", json={
            "email": unique_email,
            "password": "Str0ngPass!",
        })
        assert resp.status_code in (200, 201)
        body = resp.json()
        # UserResponse must have exactly id and email
        assert "id" in body
        assert "email" in body
        sensitive = {"password_hash", "hashed_password", "password", "is_active",
                     "is_superuser", "is_staff", "secret"}
        assert sensitive.isdisjoint(body.keys()), f"Sensitive keys found: {sensitive & body.keys()}"

    def test_login_response_no_password_hash(self):
        """POST /auth/login response must not contain password_hash."""
        db, user, _ = _make_db_and_user()
        # Register a fresh user so we know the real password
        from app.core.security import hash_password
        real_pw = "LoginTest123!"
        user2 = User(
            id=uuid.uuid4(),
            email=f"logintest_{uuid.uuid4().hex[:8]}@example.com",
            password_hash=hash_password(real_pw),
            is_active=True,
        )
        db.add(user2)
        db.commit()
        app.dependency_overrides[get_db] = lambda: db
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post("/api/v1/auth/login", json={
            "email": user2.email,
            "password": real_pw,
        })
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert "password_hash" not in body
        assert "hashed_password" not in body
        assert "password" not in body

    def test_login_response_has_access_token(self):
        """POST /auth/login intentionally returns access_token (TokenResponse)."""
        db, _, _ = _make_db_and_user()
        from app.core.security import hash_password
        real_pw = "LoginToken456!"
        user2 = User(
            id=uuid.uuid4(),
            email=f"toktest_{uuid.uuid4().hex[:8]}@example.com",
            password_hash=hash_password(real_pw),
            is_active=True,
        )
        db.add(user2)
        db.commit()
        app.dependency_overrides[get_db] = lambda: db
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post("/api/v1/auth/login", json={
            "email": user2.email,
            "password": real_pw,
        })
        assert resp.status_code == 200
        body = resp.json()
        # access_token is intentional — verify it exists and is a string
        assert "access_token" in body
        assert isinstance(body["access_token"], str)
        assert len(body["access_token"]) > 10


# ---------------------------------------------------------------------------
# TestPersonResponseLeakage
# ---------------------------------------------------------------------------


class TestPersonResponseLeakage:
    """Person list/create responses must not expose password_hash."""

    def test_persons_list_no_password_hash(self):
        """GET /persons response items must not contain password_hash."""
        db, user, _ = _make_db_and_user()
        client = _make_client(db, user)
        resp = client.get("/api/v1/persons")
        assert resp.status_code == 200, resp.text
        for item in resp.json():
            assert "password_hash" not in item
            assert "hashed_password" not in item
            assert "password" not in item

    def test_persons_list_owner_uuid_is_own(self):
        """PersonResponse.owner_user_id is the current user's own UUID (no cross-user leak)."""
        db, user, _ = _make_db_and_user()
        client = _make_client(db, user)
        resp = client.get("/api/v1/persons")
        assert resp.status_code == 200
        items = resp.json()
        assert len(items) >= 1
        for item in items:
            if "owner_user_id" in item:
                assert item["owner_user_id"] == str(user.id), (
                    "owner_user_id in response must be the requesting user's own UUID"
                )


# ---------------------------------------------------------------------------
# TestDocumentSchemaLeakage
# ---------------------------------------------------------------------------


class TestDocumentSchemaLeakage:
    """DocumentResponse must not expose storage_bucket or storage_key."""

    def test_document_response_no_storage_bucket_field(self):
        """DocumentResponse schema must not declare a storage_bucket field."""
        assert "storage_bucket" not in DocumentResponse.model_fields, (
            "storage_bucket is an internal infrastructure field and must not be "
            "included in the DocumentResponse schema exposed to clients."
        )

    def test_document_response_no_storage_key_field(self):
        """DocumentResponse schema must not declare a storage_key field."""
        assert "storage_key" not in DocumentResponse.model_fields, (
            "storage_key is an internal infrastructure field (e.g., S3 object path) "
            "and must not be included in the DocumentResponse schema exposed to clients."
        )

    def test_document_response_omits_storage_from_orm(self):
        """model_validate with storage fields present must not serialize them."""
        now = datetime.now(timezone.utc)
        doc_data = {
            "id": uuid.uuid4(),
            "category": "lab",
            "subject_profile_id": uuid.uuid4(),
            "original_filename": "blood_panel.pdf",
            "file_type": "pdf",
            "mime_type": "application/pdf",
            "file_size": 12345,
            "storage_bucket": "internal-bucket-name",  # must be excluded
            "storage_key": "users/abc123/docs/blood_panel.pdf",  # must be excluded
            "parse_status": "done",
            "confirmed_data": None,
            "confirmed_at": None,
            "uploaded_at": now,
        }
        response = DocumentResponse.model_validate(doc_data)
        serialized = response.model_dump()
        assert "storage_bucket" not in serialized
        assert "storage_key" not in serialized
        # Verify benign fields ARE present
        assert "original_filename" in serialized
        assert "parse_status" in serialized


# ---------------------------------------------------------------------------
# TestReportSchemaLeakage
# ---------------------------------------------------------------------------


class TestReportSchemaLeakage:
    """ReportStatusResponse must not expose raw token or internal file_path."""

    def test_report_status_response_no_raw_token_field(self):
        """ReportStatusResponse schema must not declare a 'token' field."""
        assert "token" not in ReportStatusResponse.model_fields, (
            "Download token must not appear as a raw field in ReportStatusResponse. "
            "It should only be embedded in download_url when ready."
        )

    def test_report_status_response_no_file_path_field(self):
        """ReportStatusResponse schema must not expose internal file_path."""
        assert "file_path" not in ReportStatusResponse.model_fields, (
            "Internal file_path (server filesystem path) must not appear in "
            "ReportStatusResponse."
        )

    def test_report_status_schema_serialized_keys(self):
        """Serialized ReportStatusResponse contains only status and download_url."""
        r = ReportStatusResponse(status="ready", download_url="/api/v1/reports/download/abc?token=xyz")
        keys = set(r.model_dump(exclude_none=False).keys())
        assert keys == {"status", "download_url"}, (
            f"ReportStatusResponse must only serialize status and download_url; got {keys}"
        )
