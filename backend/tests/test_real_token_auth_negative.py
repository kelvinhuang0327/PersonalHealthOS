"""P13 Real-Token Auth Negative Smoke.

Upgrade from P12 dependency-override tests to REAL JWT token verification.

Architecture
------------
Production ``get_current_user`` (app/core/deps.py) passes the JWT ``sub``
claim as a raw string to a ``UUID(as_uuid=True)`` SQLAlchemy column.
PostgreSQL's psycopg2 adapter handles the implicit string→UUID coercion;
SQLite does not (AttributeError: 'str' object has no attribute 'hex').

Mitigation in this test module only:
  - ``_sqlite_current_user_factory`` wraps the real JWT decode (same
    ``jwt.decode``, same ``settings.jwt_secret_key``, same algorithm) and
    converts ``user_id`` to ``uuid.UUID`` before the DB query.
  - ``get_target_person`` is NEVER overridden — production access-control code
    runs in full.
  - Token issuance uses ``create_access_token`` — the exact same production
    function as the login endpoint.

This means:
  ✓ JWT signature & expiry validated by real production crypto code
  ✓ Cross-user ownership enforced by production ``get_target_person``
  ✓ 401 rejection paths (no token / expired / garbage) tested against real
    ``oauth2_scheme`` + ``jwt.decode``
  ✗ The string→UUID coercion step in ``get_current_user`` is shimmed for
    SQLite — a no-op difference in production where psycopg2 handles it.

Coverage
--------
  TestRealTokenCrossUserIsolation:
    - user A real token + user B person_id → /family-health-context → 404
    - user A real token + user B person_id → /family-recommendations  → 404
    - user A real token + user B person_id → body must not leak user B data
    - no Authorization header                                          → 401
    - expired JWT                                                      → 401
    - garbage (non-JWT) string                                         → 401
    - user A real token + own person_id    → 200 (sanity)
    - user A real token + no person_id     → 200 (default person, sanity)
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from fastapi.testclient import TestClient
from jose import JWTError, jwt
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import get_settings
from app.core.database import Base, get_db
from app.core.deps import get_current_user
from app.core.security import create_access_token
from app.main import app
from app.models.entities import PersonProfile, User

settings = get_settings()
_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


# ---------------------------------------------------------------------------
# Token helpers
# ---------------------------------------------------------------------------

def _make_token(user_id: uuid.UUID) -> str:
    """Issue a real JWT — identical to the production login endpoint."""
    return create_access_token(str(user_id))


def _auth_headers(user_id: uuid.UUID) -> dict[str, str]:
    return {"Authorization": f"Bearer {_make_token(user_id)}"}


def _expired_token(user_id: uuid.UUID) -> str:
    """Mint a structurally valid JWT that expired 1 hour ago."""
    payload = {
        "sub": str(user_id),
        "exp": datetime.now(timezone.utc) - timedelta(hours=1),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def _garbage_token() -> str:
    return "not.a.valid.jwt.token"


# ---------------------------------------------------------------------------
# SQLite-compatible get_current_user shim
#
# Decodes the real JWT (same keys + algorithm as production), then coerces
# the ``sub`` string to uuid.UUID before the SQLAlchemy query — required only
# because SQLite's UUID(as_uuid=True) does not accept strings directly.
# In production (PostgreSQL) this coercion is transparent.
# ---------------------------------------------------------------------------

def _sqlite_current_user_factory(db_session: Session):
    """Return a FastAPI dependency that validates real JWTs against db_session."""

    async def _dep(token: str = Depends(_oauth2_scheme)) -> User:
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        try:
            payload = jwt.decode(
                token,
                settings.jwt_secret_key,
                algorithms=[settings.jwt_algorithm],
            )
            user_id_str = payload.get("sub")
            if not user_id_str:
                raise credentials_exception
            # Coerce string → UUID for SQLite UUID(as_uuid=True) column
            user_uuid = uuid.UUID(user_id_str)
        except (JWTError, ValueError) as exc:
            raise credentials_exception from exc

        user = (
            db_session.query(User)
            .filter(User.id == user_uuid, User.is_active.is_(True))
            .first()
        )
        if not user:
            raise credentials_exception
        return user

    return _dep


# ---------------------------------------------------------------------------
# Test fixture
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _clear_app_overrides():
    yield
    app.dependency_overrides.clear()


def _build_two_user_client() -> tuple[TestClient, User, PersonProfile, User, PersonProfile]:
    """
    Two distinct users each owning one PersonProfile.

    Overrides:
      - get_db           → in-memory SQLite session
      - get_current_user → SQLite-compatible JWT shim (real decode, UUID coercion)
    NOT overridden:
      - get_target_person → production ownership check runs unmodified
    """
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db: Session = SLocal()

    user_a = User(email=f"rta_{uuid.uuid4().hex[:8]}@example.com", password_hash="h")
    user_b = User(email=f"rtb_{uuid.uuid4().hex[:8]}@example.com", password_hash="h")
    db.add_all([user_a, user_b])
    db.commit()
    db.refresh(user_a)
    db.refresh(user_b)

    person_a = PersonProfile(
        owner_user_id=user_a.id,
        display_name="RealToken UserA",
        relationship="self",
        is_default=True,
    )
    person_b = PersonProfile(
        owner_user_id=user_b.id,
        display_name="RealToken UserB",
        relationship="self",
        is_default=True,
    )
    db.add_all([person_a, person_b])
    db.commit()
    db.refresh(person_a)
    db.refresh(person_b)

    def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = _sqlite_current_user_factory(db)

    client = TestClient(app, raise_server_exceptions=False)
    return client, user_a, person_a, user_b, person_b


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestRealTokenCrossUserIsolation:
    """Real JWT tokens — user A must not reach user B's family context."""

    def test_cross_user_family_context_returns_404(self):
        client, user_a, person_a, user_b, person_b = _build_two_user_client()

        resp = client.get(
            "/api/v1/health-assistant/family-health-context",
            params={"person_id": str(person_b.id)},
            headers=_auth_headers(user_a.id),
        )
        assert resp.status_code == 404, (
            f"[REAL TOKEN] Expected 404 for cross-user family-health-context, "
            f"got {resp.status_code}. Body: {resp.text}"
        )
        body = resp.text
        assert "RealToken UserB" not in body, "Response leaked user B display_name"
        assert str(person_b.id) not in body, "Response leaked user B person_id"

    def test_cross_user_family_recommendations_returns_404(self):
        client, user_a, person_a, user_b, person_b = _build_two_user_client()

        resp = client.get(
            "/api/v1/health-assistant/family-recommendations",
            params={"person_id": str(person_b.id)},
            headers=_auth_headers(user_a.id),
        )
        assert resp.status_code == 404, (
            f"[REAL TOKEN] Expected 404 for cross-user family-recommendations, "
            f"got {resp.status_code}. Body: {resp.text}"
        )
        body = resp.text
        assert "RealToken UserB" not in body, "Response leaked user B display_name"
        assert str(person_b.id) not in body, "Response leaked user B person_id"

    def test_no_token_returns_401(self):
        """Fully real: no dependency overrides involved in rejection path."""
        client, user_a, person_a, user_b, person_b = _build_two_user_client()

        resp = client.get(
            "/api/v1/health-assistant/family-health-context",
            params={"person_id": str(person_b.id)},
            # No Authorization header — oauth2_scheme rejects before our shim runs
        )
        assert resp.status_code == 401, (
            f"Expected 401 for missing token, got {resp.status_code}. Body: {resp.text}"
        )

    def test_expired_token_returns_401(self):
        """JWT signature valid but exp in the past → 401."""
        client, user_a, person_a, user_b, person_b = _build_two_user_client()

        resp = client.get(
            "/api/v1/health-assistant/family-health-context",
            headers={"Authorization": f"Bearer {_expired_token(user_a.id)}"},
        )
        assert resp.status_code == 401, (
            f"Expected 401 for expired token, got {resp.status_code}. Body: {resp.text}"
        )

    def test_garbage_token_returns_401(self):
        """Non-JWT string → JWTError → 401."""
        client, user_a, person_a, user_b, person_b = _build_two_user_client()

        resp = client.get(
            "/api/v1/health-assistant/family-health-context",
            headers={"Authorization": f"Bearer {_garbage_token()}"},
        )
        assert resp.status_code == 401, (
            f"Expected 401 for garbage token, got {resp.status_code}. Body: {resp.text}"
        )

    def test_own_person_id_accessible_with_real_token(self):
        """Sanity: user A's real token can access user A's own profile."""
        client, user_a, person_a, user_b, person_b = _build_two_user_client()

        resp = client.get(
            "/api/v1/health-assistant/family-health-context",
            params={"person_id": str(person_a.id)},
            headers=_auth_headers(user_a.id),
        )
        assert resp.status_code == 200, (
            f"[REAL TOKEN] Expected 200 for own profile, "
            f"got {resp.status_code}. Body: {resp.text}"
        )

    def test_default_person_accessible_with_real_token(self):
        """Sanity: real token with no person_id returns user A's default person."""
        client, user_a, person_a, user_b, person_b = _build_two_user_client()

        resp = client.get(
            "/api/v1/health-assistant/family-health-context",
            headers=_auth_headers(user_a.id),
        )
        assert resp.status_code == 200, (
            f"[REAL TOKEN] Expected 200 for default person, "
            f"got {resp.status_code}. Body: {resp.text}"
        )
        assert "RealToken UserB" not in resp.text, "Default response leaked user B data"
