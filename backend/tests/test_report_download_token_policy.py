"""P44 — Report Download Token URL Risk Policy Regression

Risk identified in P39 (R5):
    The download token is embedded in the URL query string:
        GET /api/v1/reports/download/{report_id}?token=<token>

    Token leakage vectors and their status:
    - Server-side access logs (nginx/uvicorn capture query strings)  ← REAL residual risk
    - Browser history                  ← NOT AT RISK (frontend uses fetch+blob, not navigation)
    - Copied address bar URL           ← NOT AT RISK (no browser navigation)
    - Cross-origin Referer header      ← NOT AT RISK (same-origin fetch)

    Impact assessment (post-P20 hardening):
    - Token alone CANNOT download: the endpoint requires a valid owner JWT.
    - No JWT + stolen token           → HTTP 401 (auth rejected first)
    - Cross-user JWT + stolen token   → HTTP 404 (owner mismatch, report not found)
    - LOW IMPACT: server-log token leak is not exploitable without the owner's JWT.

    Residual risk: Server-side access log exposure of the token value.
    Accepted limitation for P44. Deferred mitigation: X-Report-Download-Token header (P45+).

Note on stale docstring in test_report_authorization_hardening.py:
    The class-level docstring in TestReportDownloadTokenOnly says
    "token-only (no JWT auth)" — this reflects the P18 state and is outdated.
    P20 added get_current_user (JWT) as a required dependency on the download
    endpoint. The method test_download_cross_user_denied in that class correctly
    documents the P20 behaviour.

Final Classification: P44_REPORT_DOWNLOAD_TOKEN_RISK_DOCUMENTED

Coverage
--------
TestDownloadEndpointRequiresJWT
  test_no_jwt_valid_token_denied            → HTTP 401 (no Authorization header)

TestDownloadTokenStandaloneAttack
  test_stolen_token_no_jwt_denied           → HTTP 401 (server-log leak scenario)
  test_cross_user_jwt_valid_token_denied    → HTTP 404 (attacker has own JWT + stolen token)

TestDownloadTokenBodyDoesNotLeakToken
  test_403_body_does_not_echo_token         → wrong token → 403, body does not expose real token
  test_404_body_does_not_echo_token         → cross-user → 404, body does not expose token/owner
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.reports import _REPORT_STATE
from app.core.database import Base, get_db
from app.core.deps import get_current_user
from app.main import app
from app.models.entities import User


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _clear_report_state_and_overrides():
    """Isolate each test: wipe _REPORT_STATE and dependency overrides."""
    _REPORT_STATE.clear()
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()
    _REPORT_STATE.clear()


def _make_two_user_db() -> tuple[Session, User, User]:
    """Two-user SQLite DB. Returns (db, user_a, user_b)."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db: Session = SLocal()
    user_a = User(email=f"p44_a_{uuid.uuid4().hex[:8]}@example.com", password_hash="h")
    user_b = User(email=f"p44_b_{uuid.uuid4().hex[:8]}@example.com", password_hash="h")
    db.add_all([user_a, user_b])
    db.commit()
    db.refresh(user_a)
    db.refresh(user_b)
    return db, user_a, user_b


def _client_as(db: Session, user: User) -> TestClient:
    """Return a TestClient with get_db and get_current_user overridden to the given user."""
    def _db():
        yield db

    app.dependency_overrides[get_db] = _db
    app.dependency_overrides[get_current_user] = lambda: user
    return TestClient(app)


def _client_no_jwt(db: Session) -> TestClient:
    """Return a TestClient with ONLY get_db overridden.

    get_current_user is the real JWT validator — requests without an
    Authorization header will receive HTTP 401.
    """
    def _db():
        yield db

    app.dependency_overrides[get_db] = _db
    return TestClient(app)


def _seed_ready_report(owner_user_id: str) -> tuple[str, str]:
    """Seed a ready report in _REPORT_STATE without generating a real PDF.

    Returns (report_id, token).

    The file_path is not reached in failure scenarios (auth/token checks
    raise HTTPException before FileResponse is called).
    """
    report_id = str(uuid.uuid4())
    token = str(uuid.uuid4())
    _REPORT_STATE[report_id] = {
        'status': 'ready',
        'token': token,
        'expires_at': datetime.now(timezone.utc) + timedelta(hours=1),
        'file_path': '/dev/null',   # unreachable in all tested failure paths
        'owner_user_id': owner_user_id,
    }
    return report_id, token


# ---------------------------------------------------------------------------
# TestDownloadEndpointRequiresJWT
# ---------------------------------------------------------------------------


class TestDownloadEndpointRequiresJWT:
    """GET /api/v1/reports/download requires a valid owner JWT.

    After P20 hardening, get_current_user (OAuth2PasswordBearer, auto_error=True)
    is a required dependency on the download endpoint. An absent Authorization
    header triggers a 401 before any report-state or token logic is reached.
    """

    def test_no_jwt_valid_token_denied(self):
        """No Authorization header + valid download token → HTTP 401.

        This is the primary gap addressed by P44: confirming that the download
        endpoint is NOT token-only and cannot be accessed without a JWT.
        """
        db, user_a, _user_b = _make_two_user_db()
        report_id, token = _seed_ready_report(str(user_a.id))

        client = _client_no_jwt(db)
        resp = client.get(
            f'/api/v1/reports/download/{report_id}',
            params={'token': token},
            # No Authorization header — real OAuth2PasswordBearer rejects here
        )
        assert resp.status_code == 401, (
            f"No-JWT download: expected HTTP 401, got {resp.status_code}. Body: {resp.text}"
        )


# ---------------------------------------------------------------------------
# TestDownloadTokenStandaloneAttack
# ---------------------------------------------------------------------------


class TestDownloadTokenStandaloneAttack:
    """Simulates an attacker who obtained the download token from a leaked URL.

    Residual risk: the token value appears in server-side access logs because
    it is a URL query parameter. An attacker who reads those logs could obtain
    a valid token but still cannot download without the owner's JWT.
    """

    def test_stolen_token_no_jwt_denied(self):
        """Attacker has token (e.g., from server access log) but no JWT → HTTP 401.

        Server-log leak scenario:
            nginx/uvicorn access log contains:
                GET /api/v1/reports/download/<id>?token=<uuid> HTTP/1.1 200

        Even with the token, a request without a valid Authorization header
        is rejected before reaching the report-state lookup.
        """
        db, user_a, _user_b = _make_two_user_db()
        report_id, token = _seed_ready_report(str(user_a.id))

        client = _client_no_jwt(db)
        resp = client.get(
            f'/api/v1/reports/download/{report_id}',
            params={'token': token},
        )
        assert resp.status_code == 401, (
            f"Stolen token, no JWT: expected HTTP 401, got {resp.status_code}. Body: {resp.text}"
        )

    def test_cross_user_jwt_valid_token_denied(self):
        """Attacker has own valid JWT + stolen token → HTTP 404 (owner mismatch).

        This extends the P20 cross-user test to the stolen-token threat model:
        even a fully valid, non-expired token is insufficient if the JWT does
        not belong to the report owner.

        The 404 (rather than 403) prevents the attacker from confirming that
        the report exists for another user.
        """
        db, user_a, user_b = _make_two_user_db()
        report_id, token = _seed_ready_report(str(user_a.id))

        # user_b has a valid JWT but user_a's token
        client_b = _client_as(db, user_b)
        resp = client_b.get(
            f'/api/v1/reports/download/{report_id}',
            params={'token': token},
        )
        assert resp.status_code == 404, (
            f"Cross-user stolen token: expected HTTP 404, got {resp.status_code}. Body: {resp.text}"
        )


# ---------------------------------------------------------------------------
# TestDownloadTokenBodyDoesNotLeakToken
# ---------------------------------------------------------------------------


class TestDownloadTokenBodyDoesNotLeakToken:
    """Error responses must not echo the download token or report owner identity.

    Prevents token-confirmation attacks: an attacker cannot verify a guessed
    or stolen token by inspecting the HTTP response body.
    """

    def test_403_body_does_not_echo_token(self):
        """Owner JWT + wrong token → 403; response body must not expose the real token."""
        db, user_a, _user_b = _make_two_user_db()
        report_id, real_token = _seed_ready_report(str(user_a.id))
        wrong_token = str(uuid.uuid4())

        client_a = _client_as(db, user_a)
        resp = client_a.get(
            f'/api/v1/reports/download/{report_id}',
            params={'token': wrong_token},
        )
        assert resp.status_code == 403, (
            f"Wrong token: expected HTTP 403, got {resp.status_code}. Body: {resp.text}"
        )
        body = resp.text
        assert real_token not in body, "403 response body must not expose the real download token"
        assert wrong_token not in body, "403 response body must not echo the submitted wrong token"

    def test_404_body_does_not_echo_token(self):
        """Cross-user JWT + valid token → 404; response body must not leak token or owner id."""
        db, user_a, user_b = _make_two_user_db()
        report_id, token = _seed_ready_report(str(user_a.id))

        client_b = _client_as(db, user_b)
        resp = client_b.get(
            f'/api/v1/reports/download/{report_id}',
            params={'token': token},
        )
        assert resp.status_code == 404, (
            f"Cross-user: expected HTTP 404, got {resp.status_code}. Body: {resp.text}"
        )
        body = resp.text
        assert token not in body, "404 response body must not leak the download token"
        assert report_id not in body, "404 response body must not echo the report_id"
        assert str(user_a.id) not in body, "404 response body must not leak the owner user id"


def _seed_ready_report_with_pdf(owner_user_id: str, pdf_path: str) -> tuple[str, str]:
    """Seed a ready report backed by a real file (for 200-path tests).

    Returns (report_id, token).
    """
    report_id = str(uuid.uuid4())
    token = str(uuid.uuid4())
    _REPORT_STATE[report_id] = {
        'status': 'ready',
        'token': token,
        'expires_at': datetime.now(timezone.utc) + timedelta(hours=1),
        'file_path': pdf_path,
        'owner_user_id': owner_user_id,
    }
    return report_id, token


# ---------------------------------------------------------------------------
# TestHeaderTokenDownload — P45
# ---------------------------------------------------------------------------


class TestHeaderTokenDownload:
    """P45 — Download endpoint accepts X-Report-Download-Token header.

    Token resolution order:
    1. X-Report-Download-Token header (preferred)
    2. query parameter ?token= (backward-compatible fallback)

    If the header is present but invalid, the request is rejected (HTTP 403)
    even when a valid query token is also present. This enforces strict header
    preference and prevents silent fallback to a potentially stale query token.
    """

    def test_header_token_owner_jwt_succeeds(self, tmp_path):
        """Owner JWT + X-Report-Download-Token header + no query token → 200 PDF."""
        pdf_path = str(tmp_path / 'report.pdf')
        Path(pdf_path).write_bytes(b'%PDF-1.4\n%%EOF\n')
        db, user_a, _user_b = _make_two_user_db()
        report_id, token = _seed_ready_report_with_pdf(str(user_a.id), pdf_path)
        client_a = _client_as(db, user_a)

        resp = client_a.get(
            f'/api/v1/reports/download/{report_id}',
            headers={'X-Report-Download-Token': token},
            # No ?token= in URL — header is the sole token credential
        )
        assert resp.status_code == 200, (
            f"Header token: expected 200, got {resp.status_code}. Body: {resp.text}"
        )
        assert resp.headers.get('content-type', '').startswith('application/pdf'), (
            f"Expected PDF content-type, got {resp.headers.get('content-type')}"
        )

    def test_query_token_backward_compat_succeeds(self, tmp_path):
        """Owner JWT + query token + no header → 200 PDF (backward-compatible path).

        Confirms that removing the token from the header does not break existing
        clients that still pass ?token= in the URL.
        """
        pdf_path = str(tmp_path / 'report.pdf')
        Path(pdf_path).write_bytes(b'%PDF-1.4\n%%EOF\n')
        db, user_a, _user_b = _make_two_user_db()
        report_id, token = _seed_ready_report_with_pdf(str(user_a.id), pdf_path)
        client_a = _client_as(db, user_a)

        resp = client_a.get(
            f'/api/v1/reports/download/{report_id}',
            params={'token': token},
            # No X-Report-Download-Token header
        )
        assert resp.status_code == 200, (
            f"Query backward compat: expected 200, got {resp.status_code}. Body: {resp.text}"
        )

    def test_header_preferred_header_valid_query_invalid(self, tmp_path):
        """Header valid + query invalid → 200 (header takes priority over query)."""
        pdf_path = str(tmp_path / 'report.pdf')
        Path(pdf_path).write_bytes(b'%PDF-1.4\n%%EOF\n')
        db, user_a, _user_b = _make_two_user_db()
        report_id, token = _seed_ready_report_with_pdf(str(user_a.id), pdf_path)
        client_a = _client_as(db, user_a)

        resp = client_a.get(
            f'/api/v1/reports/download/{report_id}',
            headers={'X-Report-Download-Token': token},
            params={'token': 'wrong-query-token'},
        )
        assert resp.status_code == 200, (
            f"Header preferred: expected 200, got {resp.status_code}. Body: {resp.text}"
        )

    def test_header_preferred_header_invalid_query_valid_rejected(self):
        """Header invalid + query valid → 403 (invalid header takes priority, no silent fallback).

        Prevents attackers from providing a deliberately invalid header to force
        fallback to an observed query token they may have obtained from logs.
        """
        db, user_a, _user_b = _make_two_user_db()
        report_id, token = _seed_ready_report(str(user_a.id))
        client_a = _client_as(db, user_a)

        resp = client_a.get(
            f'/api/v1/reports/download/{report_id}',
            headers={'X-Report-Download-Token': 'invalid-header-token'},
            params={'token': token},  # valid query token — must NOT be used
        )
        assert resp.status_code == 403, (
            f"Invalid header, valid query: expected 403, got {resp.status_code}. Body: {resp.text}"
        )

    def test_no_token_at_all_denied(self):
        """Owner JWT + no header + no query → 403 (token is always required)."""
        db, user_a, _user_b = _make_two_user_db()
        report_id, _ = _seed_ready_report(str(user_a.id))
        client_a = _client_as(db, user_a)

        resp = client_a.get(f'/api/v1/reports/download/{report_id}')
        assert resp.status_code == 403, (
            f"No token: expected 403, got {resp.status_code}. Body: {resp.text}"
        )

    def test_cross_user_jwt_valid_header_token_denied(self):
        """Cross-user JWT + valid header token → 404 (owner mismatch before token check)."""
        db, user_a, user_b = _make_two_user_db()
        report_id, token = _seed_ready_report(str(user_a.id))
        client_b = _client_as(db, user_b)

        resp = client_b.get(
            f'/api/v1/reports/download/{report_id}',
            headers={'X-Report-Download-Token': token},
        )
        assert resp.status_code == 404, (
            f"Cross-user header token: expected 404, got {resp.status_code}. Body: {resp.text}"
        )

    def test_no_jwt_valid_header_token_denied(self):
        """No JWT + valid header token → 401 (JWT auth runs before owner/token checks)."""
        db, user_a, _user_b = _make_two_user_db()
        report_id, token = _seed_ready_report(str(user_a.id))
        client = _client_no_jwt(db)

        resp = client.get(
            f'/api/v1/reports/download/{report_id}',
            headers={'X-Report-Download-Token': token},
        )
        assert resp.status_code == 401, (
            f"No JWT, header token: expected 401, got {resp.status_code}. Body: {resp.text}"
        )
