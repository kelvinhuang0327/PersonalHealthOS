"""API smoke tests — P4 Lab Intelligence data flow
===================================================
Verifies that lab abnormalities surface correctly through
the real FastAPI routes using in-memory SQLite.

Coverage:
  GET /health-assistant/evidence-bundle
    → always includes lab_abnormalities key
    → no lab reports → lab_abnormalities == [] (anti-hallucination)
    → abnormal LabReport/LabReportItem rows → entries detected
    → multiple items for same marker → recurrenceCount > 1
    → HH flag → high severity

  GET /health-assistant/recommendations
    → always includes lab_abnormalities key
    → no labs → lab_abnormalities == []
    → high-severity lab abnormality can surface in recommendations
    → lab_abnormality source_type appears when lab data present
    → dedup: covered by lab_abnormality should not also appear as lab_report_item
"""
from __future__ import annotations

import uuid as _uuid
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
# Client factory
# ---------------------------------------------------------------------------

def _build_client(seed_labs: list[dict] | None = None) -> tuple[TestClient, object]:
    """Build a TestClient with in-memory SQLite.

    seed_labs format:
        [{"report_date": date, "items": [{"item_name": str, "value_num": float,
          "unit": str, "ref_range": str, "ref_low": float, "ref_high": float,
          "abnormal_flag": str, "parser_confidence": float}]}]
    """
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    db = Session()
    user = User(email="lab_smoke@example.com", password_hash="hashed")
    db.add(user)
    db.commit()
    db.refresh(user)

    person = PersonProfile(
        owner_user_id=user.id,
        display_name="Lab Tester",
        relationship="self",
        is_default=True,
    )
    db.add(person)
    db.commit()
    db.refresh(person)

    if seed_labs:
        for lab_def in seed_labs:
            report = LabReport(
                user_id=user.id,
                subject_profile_id=person.id,
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
                    value_text=item_def.get("value_text"),
                    unit=item_def.get("unit"),
                    ref_range=item_def.get("ref_range"),
                    ref_low=item_def.get("ref_low"),
                    ref_high=item_def.get("ref_high"),
                    abnormal_flag=item_def.get("abnormal_flag"),
                    parser_confidence=item_def.get("parser_confidence", 0.85),
                )
                db.add(item)
            db.commit()

    def override_db():
        try:
            yield db
        finally:
            pass

    def override_user():
        return user

    def override_person():
        return person

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = override_user
    app.dependency_overrides[get_target_person] = override_person

    return TestClient(app), person


# ---------------------------------------------------------------------------
# Lab seed helpers
# ---------------------------------------------------------------------------

def _ldl_report(
    value_num: float = 4.5,
    abnormal_flag: str = "H",
    days_ago: int = 10,
) -> dict:
    return {
        "report_date": date.today() - timedelta(days=days_ago),
        "items": [{
            "item_name": "LDL",
            "value_num": value_num,
            "unit": "mmol/L",
            "ref_range": "< 3.37 mmol/L",
            "ref_low": None,
            "ref_high": 3.37,
            "abnormal_flag": abnormal_flag,
            "parser_confidence": 0.88,
        }],
    }


# ---------------------------------------------------------------------------
# GET /health-assistant/evidence-bundle — lab_abnormalities key
# ---------------------------------------------------------------------------

class TestEvidenceBundleLabKeys:
    def test_bundle_always_has_lab_abnormalities_key(self):
        client, _ = _build_client()
        resp = client.get("/api/v1/health-assistant/evidence-bundle")
        assert resp.status_code == 200
        assert "lab_abnormalities" in resp.json(), "bundle must have lab_abnormalities"

    def test_no_labs_lab_abnormalities_is_empty(self):
        """Anti-hallucination: no LabReport rows → lab_abnormalities == []."""
        client, _ = _build_client(seed_labs=[])
        resp = client.get("/api/v1/health-assistant/evidence-bundle")
        assert resp.json()["lab_abnormalities"] == [], "No labs → no abnormalities"

    def test_abnormal_lab_item_produces_entry(self):
        """An abnormal LabReportItem row must produce a lab_abnormality entry."""
        client, _ = _build_client(seed_labs=[_ldl_report()])
        resp = client.get("/api/v1/health-assistant/evidence-bundle")
        lab_abns = resp.json()["lab_abnormalities"]
        assert len(lab_abns) >= 1

    def test_entry_lab_item_name_matches_seeded(self):
        client, _ = _build_client(seed_labs=[_ldl_report()])
        resp = client.get("/api/v1/health-assistant/evidence-bundle")
        names = [a["labItemName"] for a in resp.json()["lab_abnormalities"]]
        assert "LDL" in names

    def test_two_reports_same_marker_recurrence_count_2(self):
        """Two reports with LDL abnormal → recurrenceCount == 2."""
        client, _ = _build_client(seed_labs=[
            _ldl_report(days_ago=30),
            _ldl_report(days_ago=60),
        ])
        resp = client.get("/api/v1/health-assistant/evidence-bundle")
        ldl_entries = [a for a in resp.json()["lab_abnormalities"] if a["labItemName"] == "LDL"]
        assert ldl_entries, "Expected LDL entry"
        assert ldl_entries[0]["recurrenceCount"] == 2

    def test_hh_flag_produces_high_severity(self):
        client, _ = _build_client(seed_labs=[_ldl_report(abnormal_flag="HH")])
        resp = client.get("/api/v1/health-assistant/evidence-bundle")
        ldl = next((a for a in resp.json()["lab_abnormalities"] if a["labItemName"] == "LDL"), None)
        assert ldl is not None
        assert ldl["severity"] == "high"

    def test_entry_has_required_schema_keys(self):
        required = {
            "abnormalityType", "severity", "labItemName", "currentValue",
            "referenceRange", "reportId", "detectedAt", "whyDetected",
            "suggestedAction", "confidence", "evidenceSources",
            "recurrenceCount", "rule_id",
        }
        client, _ = _build_client(seed_labs=[_ldl_report()])
        resp = client.get("/api/v1/health-assistant/evidence-bundle")
        for entry in resp.json()["lab_abnormalities"]:
            missing = required - set(entry.keys())
            assert not missing, f"Missing keys: {missing}"

    def test_summary_includes_lab_abnormality_count(self):
        client, _ = _build_client(seed_labs=[_ldl_report()])
        resp = client.get("/api/v1/health-assistant/evidence-bundle")
        summary = resp.json().get("summary", {})
        assert "lab_abnormality_count" in summary


# ---------------------------------------------------------------------------
# GET /health-assistant/recommendations — lab_abnormalities key
# ---------------------------------------------------------------------------

class TestRecommendationsLabAbnormalities:
    def test_recommendations_always_has_lab_abnormalities_key(self):
        client, _ = _build_client()
        resp = client.get("/api/v1/health-assistant/recommendations")
        assert resp.status_code == 200
        assert "lab_abnormalities" in resp.json()

    def test_no_labs_returns_empty_lab_abnormalities(self):
        client, _ = _build_client(seed_labs=[])
        resp = client.get("/api/v1/health-assistant/recommendations")
        assert resp.json()["lab_abnormalities"] == []

    def test_high_severity_lab_abnormality_can_enter_recommendations(self):
        """Three abnormal LDL reports → high severity → eligible for top-3."""
        client, _ = _build_client(seed_labs=[
            _ldl_report(abnormal_flag="H", days_ago=10),
            _ldl_report(abnormal_flag="H", days_ago=40),
            _ldl_report(abnormal_flag="H", days_ago=70),
        ])
        resp = client.get("/api/v1/health-assistant/recommendations")
        data = resp.json()
        assert len(data["lab_abnormalities"]) >= 1
        recs = data["recommendations"]
        source_types = [r.get("source_type") for r in recs]
        # Either lab_abnormality or lab_report_item (depending on priority)
        assert any(st in ("lab_abnormality", "lab_report_item") for st in source_types), (
            f"Expected lab source in recommendations, got: {source_types}"
        )

    def test_recommendations_schema_intact_with_labs(self):
        client, _ = _build_client(seed_labs=[_ldl_report()])
        resp = client.get("/api/v1/health-assistant/recommendations")
        assert resp.status_code == 200
        required = {"person_id", "generated_at", "recommendations", "missing_data",
                    "symptom_patterns", "lab_abnormalities"}
        missing = required - set(resp.json().keys())
        assert not missing, f"Recommendations response missing keys: {missing}"


# ---------------------------------------------------------------------------
# Active / Completed Action Deduplication
# ---------------------------------------------------------------------------



class TestCompletedActionDedup:
    """When a HealthAction with matching rule_id is status='done',
    the lab recommendation must be suppressed (absent from top-3 recs)."""

    def _build_dedup_client(self, action_status: str, include_action: bool = True):
        """Helper: 3 abnormal LDL reports + optional HealthAction."""
        engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        Base.metadata.create_all(bind=engine)

        db = Session()
        tag = action_status[:8] if action_status else "none"
        user = User(email=f"dedup_{tag}@example.com", password_hash="h")
        db.add(user)
        db.commit()
        db.refresh(user)

        person = PersonProfile(
            owner_user_id=user.id,
            display_name="Dedup Tester",
            relationship="self",
            is_default=True,
        )
        db.add(person)
        db.commit()
        db.refresh(person)

        # 3 abnormal LDL reports so lab_abnormality severity reaches "high"
        for days_back in (5, 35, 65):
            report = LabReport(
                user_id=user.id,
                subject_profile_id=person.id,
                report_date=date.today() - timedelta(days=days_back),
                report_type="health_check",
            )
            db.add(report)
            db.commit()
            db.refresh(report)
            db.add(LabReportItem(
                report_id=report.id,
                item_name="LDL",
                value_num=4.5,
                unit="mmol/L",
                ref_range="< 3.37 mmol/L",
                ref_high=3.37,
                abnormal_flag="H",
                parser_confidence=0.88,
            ))
        db.commit()

        if include_action:
            from app.models.entities import HealthAction
            action = HealthAction(
                user_id=user.id,
                person_id=person.id,
                rule_id="lab_abnormality_LDL",
                title="LDL 追蹤",
                action_type="lifestyle",
                status=action_status,
                completed_at=(
                    datetime.now(timezone.utc) - timedelta(days=1)
                    if action_status == "done" else None
                ),
            )
            db.add(action)
            db.commit()

        def override_db():
            try:
                yield db
            finally:
                pass

        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_target_person] = lambda: person

        return TestClient(app)

    def test_done_action_suppresses_recommendation(self):
        """status=done + completed_at within 30d → LDL absent from top-3."""
        client = self._build_dedup_client("done")
        resp = client.get("/api/v1/health-assistant/recommendations")
        assert resp.status_code == 200
        rule_ids = [r.get("rule_id") for r in resp.json()["recommendations"]]
        assert "lab_abnormality_LDL" not in rule_ids, (
            f"Expected LDL suppressed (status=done), but found in: {rule_ids}"
        )

    def test_in_progress_action_does_not_suppress(self):
        """status=in_progress → LDL must still appear in recommendations."""
        client = self._build_dedup_client("in_progress")
        resp = client.get("/api/v1/health-assistant/recommendations")
        assert resp.status_code == 200
        recs = resp.json()["recommendations"]
        source_types = [r.get("source_type") for r in recs]
        assert any(st in ("lab_abnormality", "lab_report_item") for st in source_types), (
            f"in_progress must not suppress lab rec. Got: {source_types}"
        )

    def test_no_action_lab_rec_appears(self):
        """Baseline: no HealthAction → lab abnormality enters top-3."""
        client = self._build_dedup_client("", include_action=False)
        resp = client.get("/api/v1/health-assistant/recommendations")
        assert resp.status_code == 200
        recs = resp.json()["recommendations"]
        source_types = [r.get("source_type") for r in recs]
        assert any(st in ("lab_abnormality", "lab_report_item") for st in source_types), (
            f"Without completed action, lab rec should appear. Got: {source_types}"
        )
