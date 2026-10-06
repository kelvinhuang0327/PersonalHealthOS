"""Tests for P9 — Family Context Real Evidence Data Population

Coverage
--------
  TestExtractFamilyEvidenceFromBundle (pure-function):
    - empty bundle → all lists empty
    - lab_abnormalities present → lab_abnormality_summaries populated
    - lab_abnormalities missing labItemName → entry skipped
    - symptom_patterns with symptomType + label → combined summary
    - symptom_patterns with label only → label used
    - device_escalation urgent → escalation_summaries populated
    - device_escalation none-level → escalation_summaries empty
    - active actions → action_titles populated
    - all data fields → all lists populated simultaneously

  TestLoadFamilyEvidenceDataIntegration (DB helper):
    - no relationships → all returned dicts are empty
    - related profile with lab data → lab_abnormalities_by_profile populated
    - related profile with active action → active_actions_by_profile populated
    - unrelated profile evidence not included
    - duplicate related_profile_id in relationships → loaded once only

  TestPopulatedFamilyContextAPI (API endpoint):
    - GET /family-health-context with no relationships → empty context (confidence=0)
    - GET /family-health-context with child + lab data → childAttentionItems populated
    - GET /family-health-context confidence > 0 with evidence
    - GET /family-recommendations with active action → dedup suppresses recommendation
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.deps import get_current_user, get_target_person
from app.main import app
from app.models.entities import (
    FamilyRelationship,
    HealthAction,
    LabReport,
    LabReportItem,
    PersonProfile,
    User,
)
from app.services.family_health_context_service import (
    extract_family_evidence_from_bundle,
    load_family_evidence_data,
    load_family_relationships,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _clear_app_overrides():
    yield
    app.dependency_overrides.clear()


def _build_client_with_child() -> tuple[TestClient, User, PersonProfile, PersonProfile, Session]:
    """Build TestClient with in-memory SQLite; person_a is subject, person_b is child."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    db: Session = SLocal()

    user = User(email=f"pop_test_{uuid.uuid4().hex[:8]}@example.com", password_hash="h")
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


def _create_lab_report_with_abnormal_item(
    db: Session, user_id: uuid.UUID, person_id: uuid.UUID,
    item_name: str = "LDL-C", abnormal_flag: str = "high",
) -> None:
    """Insert a LabReport + one abnormal LabReportItem for the given person."""
    report = LabReport(
        user_id=user_id,
        subject_profile_id=person_id,
        report_type="health_check",
        created_at=datetime.now(timezone.utc),
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    item = LabReportItem(
        report_id=report.id,
        item_name=item_name,
        value_num=4.8,
        unit="mmol/L",
        ref_high=3.4,
        abnormal_flag=abnormal_flag,
    )
    db.add(item)
    db.commit()


def _create_active_action(
    db: Session, user_id: uuid.UUID, person_id: uuid.UUID,
    title: str = "每日量血壓",
) -> None:
    """Insert one active HealthAction for the given person."""
    action = HealthAction(
        user_id=user_id,
        person_id=person_id,
        title=title,
        status="todo",
        source_type="manual",
        action_type="lifestyle",
        priority="medium",
    )
    db.add(action)
    db.commit()


def _create_child_relationship(
    db: Session, user_id: uuid.UUID, subject_id: uuid.UUID, child_id: uuid.UUID,
    permission_level: str = "manage",
) -> None:
    """Create a child family relationship."""
    rel = FamilyRelationship(
        owner_user_id=user_id,
        subject_profile_id=subject_id,
        related_profile_id=child_id,
        relationship_type="child",
        permission_level=permission_level,
    )
    db.add(rel)
    db.commit()


# ---------------------------------------------------------------------------
# TestExtractFamilyEvidenceFromBundle  (pure-function)
# ---------------------------------------------------------------------------

class TestExtractFamilyEvidenceFromBundle:

    def test_empty_bundle_returns_all_empty(self):
        result = extract_family_evidence_from_bundle({})
        assert result["lab_abnormality_summaries"] == []
        assert result["symptom_pattern_summaries"] == []
        assert result["escalation_summaries"] == []
        assert result["action_titles"] == []

    def test_lab_abnormalities_to_summaries(self):
        bundle = {
            "lab_abnormalities": [
                {"labItemName": "LDL-C", "severity": "high"},
                {"labItemName": "血糖", "severity": "critical"},
            ]
        }
        result = extract_family_evidence_from_bundle(bundle)
        assert "LDL-C 異常（high）" in result["lab_abnormality_summaries"]
        assert "血糖 異常（critical）" in result["lab_abnormality_summaries"]
        assert len(result["lab_abnormality_summaries"]) == 2

    def test_lab_abnormality_missing_name_skipped(self):
        bundle = {
            "lab_abnormalities": [
                {"labItemName": "", "severity": "high"},
                {"severity": "medium"},
                {"labItemName": "ALT", "severity": "warning"},
            ]
        }
        result = extract_family_evidence_from_bundle(bundle)
        assert len(result["lab_abnormality_summaries"]) == 1
        assert "ALT 異常（warning）" in result["lab_abnormality_summaries"]

    def test_symptom_patterns_combined_summary(self):
        bundle = {
            "symptom_patterns": [
                {"symptomType": "頭痛", "label": "重複發作"},
            ]
        }
        result = extract_family_evidence_from_bundle(bundle)
        assert "頭痛 重複發作" in result["symptom_pattern_summaries"]

    def test_symptom_patterns_label_only(self):
        bundle = {
            "symptom_patterns": [
                {"patternType": "worsening_symptom", "label": "症狀惡化"},
            ]
        }
        result = extract_family_evidence_from_bundle(bundle)
        assert "症狀惡化" in result["symptom_pattern_summaries"]

    def test_device_escalation_urgent_produces_summaries(self):
        bundle = {
            "device_escalation": {
                "escalationLevel": "urgent",
                "reasons": ["心率持續偏高", "血壓異常"],
            }
        }
        result = extract_family_evidence_from_bundle(bundle)
        assert "心率持續偏高" in result["escalation_summaries"]
        assert "血壓異常" in result["escalation_summaries"]

    def test_device_escalation_none_level_no_summaries(self):
        bundle = {
            "device_escalation": {
                "escalationLevel": "none",
                "reasons": [],
            }
        }
        result = extract_family_evidence_from_bundle(bundle)
        assert result["escalation_summaries"] == []

    def test_actions_to_action_titles(self):
        bundle = {
            "actions": [
                {"summary": "每日量血壓", "status": "todo"},
                {"summary": "監控膽固醇", "status": "in_progress"},
            ]
        }
        result = extract_family_evidence_from_bundle(bundle)
        assert "每日量血壓" in result["action_titles"]
        assert "監控膽固醇" in result["action_titles"]
        assert len(result["action_titles"]) == 2

    def test_all_fields_populated_simultaneously(self):
        bundle = {
            "lab_abnormalities": [{"labItemName": "ALT", "severity": "high"}],
            "symptom_patterns": [{"symptomType": "腹痛", "label": "反覆發作"}],
            "device_escalation": {"escalationLevel": "warning", "reasons": ["睡眠品質異常"]},
            "actions": [{"summary": "飲食調整", "status": "todo"}],
        }
        result = extract_family_evidence_from_bundle(bundle)
        assert len(result["lab_abnormality_summaries"]) == 1
        assert len(result["symptom_pattern_summaries"]) == 1
        assert len(result["escalation_summaries"]) == 1
        assert len(result["action_titles"]) == 1


# ---------------------------------------------------------------------------
# TestLoadFamilyEvidenceDataIntegration  (DB helper)
# ---------------------------------------------------------------------------

class TestLoadFamilyEvidenceDataIntegration:

    def test_no_relationships_returns_empty_dicts(self):
        engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        SLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        Base.metadata.create_all(bind=engine)
        db: Session = SLocal()

        user = User(email="empty_rel@example.com", password_hash="h")
        db.add(user)
        db.commit()
        db.refresh(user)

        result = load_family_evidence_data(db, str(user.id), [])
        assert result["lab_abnormalities_by_profile"] == {}
        assert result["active_actions_by_profile"] == {}
        assert result["recommendations_by_profile"] == {}
        assert result["symptom_patterns_by_profile"] == {}
        assert result["escalations_by_profile"] == {}

    def test_related_profile_lab_data_populates_lab_dict(self):
        engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        SLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        Base.metadata.create_all(bind=engine)
        db: Session = SLocal()

        user = User(email="lab_data@example.com", password_hash="h")
        db.add(user)
        db.commit()
        db.refresh(user)

        child = PersonProfile(
            owner_user_id=user.id,
            display_name="小明",
            relationship="child",
        )
        db.add(child)
        db.commit()
        db.refresh(child)

        _create_lab_report_with_abnormal_item(db, user.id, child.id, "LDL-C", "high")

        relationships: list[dict[str, Any]] = [
            {
                "related_profile_id": str(child.id),
                "relationship_type": "child",
                "permission_level": "manage",
            }
        ]
        result = load_family_evidence_data(db, str(user.id), relationships)
        child_labs = result["lab_abnormalities_by_profile"].get(str(child.id), [])
        assert any("LDL-C" in s for s in child_labs), f"Expected LDL-C in {child_labs}"

    def test_related_profile_active_action_populates_action_dict(self):
        engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        SLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        Base.metadata.create_all(bind=engine)
        db: Session = SLocal()

        user = User(email="action_data@example.com", password_hash="h")
        db.add(user)
        db.commit()
        db.refresh(user)

        child = PersonProfile(
            owner_user_id=user.id,
            display_name="小李",
            relationship="child",
        )
        db.add(child)
        db.commit()
        db.refresh(child)

        _create_active_action(db, user.id, child.id, "每日量血壓")

        relationships: list[dict[str, Any]] = [
            {
                "related_profile_id": str(child.id),
                "relationship_type": "child",
                "permission_level": "manage",
            }
        ]
        result = load_family_evidence_data(db, str(user.id), relationships)
        actions = result["active_actions_by_profile"].get(str(child.id), [])
        assert "每日量血壓" in actions

    def test_unrelated_profile_evidence_not_included(self):
        engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        SLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        Base.metadata.create_all(bind=engine)
        db: Session = SLocal()

        user = User(email="isolation@example.com", password_hash="h")
        db.add(user)
        db.commit()
        db.refresh(user)

        child = PersonProfile(owner_user_id=user.id, display_name="小明", relationship="child")
        unrelated = PersonProfile(owner_user_id=user.id, display_name="陌生人", relationship="self")
        db.add_all([child, unrelated])
        db.commit()
        db.refresh(child)
        db.refresh(unrelated)

        _create_lab_report_with_abnormal_item(db, user.id, unrelated.id, "HBA1C", "high")

        # Only child in relationships — unrelated profile's data must NOT appear
        relationships: list[dict[str, Any]] = [
            {
                "related_profile_id": str(child.id),
                "relationship_type": "child",
                "permission_level": "manage",
            }
        ]
        result = load_family_evidence_data(db, str(user.id), relationships)
        assert str(unrelated.id) not in result["lab_abnormalities_by_profile"]

    def test_duplicate_profile_id_in_relationships_loaded_once(self):
        engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        SLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        Base.metadata.create_all(bind=engine)
        db: Session = SLocal()

        user = User(email="dedup_load@example.com", password_hash="h")
        db.add(user)
        db.commit()
        db.refresh(user)

        child = PersonProfile(owner_user_id=user.id, display_name="小明", relationship="child")
        db.add(child)
        db.commit()
        db.refresh(child)

        _create_lab_report_with_abnormal_item(db, user.id, child.id, "ALT", "warning")

        # Same profile_id appears twice in relationships
        relationships: list[dict[str, Any]] = [
            {"related_profile_id": str(child.id), "relationship_type": "child", "permission_level": "manage"},
            {"related_profile_id": str(child.id), "relationship_type": "caregiver", "permission_level": "full_access"},
        ]
        result = load_family_evidence_data(db, str(user.id), relationships)
        # Profile loaded exactly once — one entry in the dict
        assert str(child.id) in result["lab_abnormalities_by_profile"]
        labs = result["lab_abnormalities_by_profile"][str(child.id)]
        # ALT appears once, not duplicated
        assert labs.count(next(s for s in labs if "ALT" in s)) == 1


# ---------------------------------------------------------------------------
# TestPopulatedFamilyContextAPI  (API endpoint integration)
# ---------------------------------------------------------------------------

class TestPopulatedFamilyContextAPI:

    def test_no_relationships_returns_empty_context(self):
        client, user, person_a, person_b, db = _build_client_with_child()
        # No relationship created — context should be empty
        resp = client.get("/api/v1/health-assistant/family-health-context")
        assert resp.status_code == 200
        ctx = resp.json()["context"]
        assert ctx["relatedProfiles"] == []
        assert ctx["caregiverAlerts"] == []
        assert ctx["childAttentionItems"] == []
        assert ctx["confidence"] == 0.0

    def test_child_with_lab_data_populates_child_attention_items(self):
        client, user, person_a, person_b, db = _build_client_with_child()

        # Create child relationship (child rel_type → surfaces in childAttentionItems)
        _create_child_relationship(db, user.id, person_a.id, person_b.id, permission_level="manage")

        # Seed lab abnormality for child profile
        _create_lab_report_with_abnormal_item(db, user.id, person_b.id, "LDL-C", "high")

        resp = client.get("/api/v1/health-assistant/family-health-context")
        assert resp.status_code == 200
        ctx = resp.json()["context"]

        # childAttentionItems should contain mention of child's lab abnormality
        combined = " ".join(ctx.get("childAttentionItems", []))
        assert "LDL-C" in combined, (
            f"Expected LDL-C in childAttentionItems, got: {ctx.get('childAttentionItems')}"
        )

    def test_evidence_raises_confidence_above_zero(self):
        client, user, person_a, person_b, db = _build_client_with_child()

        _create_child_relationship(db, user.id, person_a.id, person_b.id)
        _create_lab_report_with_abnormal_item(db, user.id, person_b.id, "ALT", "warning")

        resp = client.get("/api/v1/health-assistant/family-health-context")
        assert resp.status_code == 200
        ctx = resp.json()["context"]
        assert ctx["confidence"] > 0.0

    def test_active_action_dedup_suppresses_family_recommendation(self):
        client, user, person_a, person_b, db = _build_client_with_child()

        _create_child_relationship(db, user.id, person_a.id, person_b.id, permission_level="manage")

        # Add active action AND a lab abnormality for the child
        action_title = "定期追蹤LDL-C"
        _create_active_action(db, user.id, person_b.id, action_title)
        _create_lab_report_with_abnormal_item(db, user.id, person_b.id, "LDL-C", "high")

        resp = client.get("/api/v1/health-assistant/family-recommendations")
        assert resp.status_code == 200
        recs = resp.json()["recommendations"]

        # The active action title must NOT appear as a new recommendation (dedup)
        rec_texts = [r["text"] for r in recs]
        assert action_title not in rec_texts, (
            f"Active action '{action_title}' should have been deduped from recommendations"
        )
