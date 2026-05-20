"""Tests for FamilyRelationship model + API endpoints — P8

Coverage
--------
  - FamilyRelationship model persists and queries correctly
  - FamilyRelationship unique constraint (owner, subject, related)
  - POST /family-relationships creates relationship
  - POST /family-relationships is idempotent (returns existing)
  - POST /family-relationships validates relationship_type
  - POST /family-relationships validates permission_level
  - POST /family-relationships returns 404 for unknown related_profile
  - GET /family-relationships returns all relationships for person
  - GET /family-health-context returns empty state when no relationships
  - GET /family-health-context returns context after relationship created
  - GET /family-recommendations returns empty list when no relationships
  - Permission level read_only / manage / full_access all accepted
  - Relationship types self / child / parent / spouse / caregiver all accepted
"""
from __future__ import annotations

from typing import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.deps import get_current_user, get_target_person
from app.main import app
from app.models.entities import FamilyRelationship, PersonProfile, User


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _clear_app_overrides():
    yield
    app.dependency_overrides.clear()


def _build_client() -> tuple[TestClient, User, PersonProfile, PersonProfile, Session]:
    """Build TestClient with in-memory SQLite + two person profiles."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    db: Session = SLocal()

    user = User(email="family_test@example.com", password_hash="hash")
    db.add(user)
    db.commit()
    db.refresh(user)

    person_a = PersonProfile(
        owner_user_id=user.id,
        display_name="主要使用者",
        relationship="self",
        is_default=True,
    )
    person_b = PersonProfile(
        owner_user_id=user.id,
        display_name="小明",
        relationship="child",
        is_default=False,
    )
    db.add_all([person_a, person_b])
    db.commit()
    db.refresh(person_a)
    db.refresh(person_b)

    def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_target_person] = lambda: person_a

    client = TestClient(app)
    return client, user, person_a, person_b, db


# ---------------------------------------------------------------------------
# TestFamilyRelationshipModel
# ---------------------------------------------------------------------------

class TestFamilyRelationshipModel:

    def test_create_and_query(self):
        engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(bind=engine)
        db = sessionmaker(bind=engine)()

        user = User(email="model_test@example.com", password_hash="x")
        db.add(user)
        db.commit()
        db.refresh(user)

        pa = PersonProfile(owner_user_id=user.id, display_name="A", relationship="self", is_default=True)
        pb = PersonProfile(owner_user_id=user.id, display_name="B", relationship="child", is_default=False)
        db.add_all([pa, pb])
        db.commit()
        db.refresh(pa)
        db.refresh(pb)

        rel = FamilyRelationship(
            owner_user_id=user.id,
            subject_profile_id=pa.id,
            related_profile_id=pb.id,
            relationship_type="child",
            permission_level="manage",
        )
        db.add(rel)
        db.commit()
        db.refresh(rel)

        loaded = db.query(FamilyRelationship).filter(
            FamilyRelationship.subject_profile_id == pa.id
        ).first()
        assert loaded is not None
        assert loaded.relationship_type == "child"
        assert loaded.permission_level == "manage"

    def test_unique_constraint_prevents_duplicate(self):
        from sqlalchemy.exc import IntegrityError

        engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(bind=engine)
        db = sessionmaker(bind=engine)()

        user = User(email="unique_test@example.com", password_hash="x")
        db.add(user)
        db.commit()
        db.refresh(user)

        pa = PersonProfile(owner_user_id=user.id, display_name="A", relationship="self", is_default=True)
        pb = PersonProfile(owner_user_id=user.id, display_name="B", relationship="child", is_default=False)
        db.add_all([pa, pb])
        db.commit()
        db.refresh(pa)
        db.refresh(pb)

        rel1 = FamilyRelationship(
            owner_user_id=user.id,
            subject_profile_id=pa.id,
            related_profile_id=pb.id,
            relationship_type="child",
            permission_level="manage",
        )
        rel2 = FamilyRelationship(
            owner_user_id=user.id,
            subject_profile_id=pa.id,
            related_profile_id=pb.id,
            relationship_type="child",
            permission_level="read_only",
        )
        db.add(rel1)
        db.commit()

        db.add(rel2)
        with pytest.raises(IntegrityError):
            db.commit()

    def test_all_relationship_types_accepted(self):
        engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(bind=engine)
        db = sessionmaker(bind=engine)()

        user = User(email="reltypes_test@example.com", password_hash="x")
        db.add(user)
        db.commit()
        db.refresh(user)

        profiles = []
        for i in range(6):
            p = PersonProfile(
                owner_user_id=user.id,
                display_name=f"P{i}",
                relationship="self",
                is_default=(i == 0),
            )
            db.add(p)
            profiles.append(p)
        db.commit()
        for p in profiles:
            db.refresh(p)

        for rel_type, subject, related in zip(
            ["child", "parent", "spouse", "caregiver", "self"],
            profiles[0:5],
            profiles[1:6],
        ):
            rel = FamilyRelationship(
                owner_user_id=user.id,
                subject_profile_id=subject.id,
                related_profile_id=related.id,
                relationship_type=rel_type,
                permission_level="read_only",
            )
            db.add(rel)
        db.commit()
        count = db.query(FamilyRelationship).count()
        assert count == 5


# ---------------------------------------------------------------------------
# TestFamilyRelationshipsAPI
# ---------------------------------------------------------------------------

class TestFamilyRelationshipsAPI:

    def test_post_creates_relationship(self):
        client, user, person_a, person_b, db = _build_client()
        resp = client.post(
            "/api/v1/health-assistant/family-relationships",
            json={
                "related_profile_id": str(person_b.id),
                "relationship_type": "child",
                "permission_level": "manage",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["created"] is True
        assert data["relationship_type"] == "child"
        assert data["permission_level"] == "manage"

    def test_post_idempotent_returns_existing(self):
        client, user, person_a, person_b, db = _build_client()
        payload = {
            "related_profile_id": str(person_b.id),
            "relationship_type": "child",
            "permission_level": "manage",
        }
        resp1 = client.post("/api/v1/health-assistant/family-relationships", json=payload)
        resp2 = client.post("/api/v1/health-assistant/family-relationships", json=payload)
        assert resp1.status_code == 201
        assert resp2.status_code == 201
        assert resp2.json()["created"] is False
        assert resp1.json()["id"] == resp2.json()["id"]

    def test_post_invalid_relationship_type_422(self):
        client, user, person_a, person_b, db = _build_client()
        resp = client.post(
            "/api/v1/health-assistant/family-relationships",
            json={
                "related_profile_id": str(person_b.id),
                "relationship_type": "enemy",
                "permission_level": "manage",
            },
        )
        assert resp.status_code == 422

    def test_post_invalid_permission_level_422(self):
        client, user, person_a, person_b, db = _build_client()
        resp = client.post(
            "/api/v1/health-assistant/family-relationships",
            json={
                "related_profile_id": str(person_b.id),
                "relationship_type": "child",
                "permission_level": "superuser",
            },
        )
        assert resp.status_code == 422

    def test_post_unknown_related_profile_404(self):
        client, user, person_a, person_b, db = _build_client()
        resp = client.post(
            "/api/v1/health-assistant/family-relationships",
            json={
                "related_profile_id": "00000000-0000-0000-0000-000000000000",
                "relationship_type": "child",
                "permission_level": "manage",
            },
        )
        assert resp.status_code == 404

    def test_get_family_relationships_empty(self):
        client, user, person_a, person_b, db = _build_client()
        resp = client.get("/api/v1/health-assistant/family-relationships")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0
        assert data["relationships"] == []

    def test_get_family_relationships_after_create(self):
        client, user, person_a, person_b, db = _build_client()
        client.post(
            "/api/v1/health-assistant/family-relationships",
            json={
                "related_profile_id": str(person_b.id),
                "relationship_type": "child",
                "permission_level": "manage",
            },
        )
        resp = client.get("/api/v1/health-assistant/family-relationships")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["relationships"][0]["relationship_type"] == "child"
        assert "related_display_name" in data["relationships"][0]

    def test_all_permission_levels_accepted(self):
        for perm in ["read_only", "manage", "full_access"]:
            client, user, person_a, person_b, db = _build_client()
            resp = client.post(
                "/api/v1/health-assistant/family-relationships",
                json={
                    "related_profile_id": str(person_b.id),
                    "relationship_type": "child",
                    "permission_level": perm,
                },
            )
            assert resp.status_code == 201, f"permission {perm} failed"
            assert resp.json()["permission_level"] == perm


# ---------------------------------------------------------------------------
# TestFamilyHealthContextAPI
# ---------------------------------------------------------------------------

class TestFamilyHealthContextAPI:

    def test_empty_context_when_no_relationships(self):
        client, user, person_a, person_b, db = _build_client()
        resp = client.get("/api/v1/health-assistant/family-health-context")
        assert resp.status_code == 200
        data = resp.json()
        ctx = data["context"]
        assert ctx["relatedProfiles"] == []
        assert ctx["confidence"] == 0.0
        assert len(ctx["limitations"]) >= 1

    def test_context_has_related_profiles_after_relationship_created(self):
        client, user, person_a, person_b, db = _build_client()
        client.post(
            "/api/v1/health-assistant/family-relationships",
            json={
                "related_profile_id": str(person_b.id),
                "relationship_type": "child",
                "permission_level": "manage",
            },
        )
        resp = client.get("/api/v1/health-assistant/family-health-context")
        assert resp.status_code == 200
        ctx = resp.json()["context"]
        assert len(ctx["relatedProfiles"]) == 1
        assert ctx["relatedProfiles"][0]["relationship_type"] == "child"

    def test_family_recommendations_empty_when_no_relationships(self):
        client, user, person_a, person_b, db = _build_client()
        resp = client.get("/api/v1/health-assistant/family-recommendations")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0
        assert data["recommendations"] == []
