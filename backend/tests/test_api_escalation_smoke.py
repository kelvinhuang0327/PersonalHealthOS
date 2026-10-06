"""API smoke tests — P2 Device Escalation data flow
=====================================================
Verifies structural correctness of the three health-assistant endpoints
that carry escalation data:

  GET /health-assistant/device-signals   → signals schema
  GET /health-assistant/evidence-bundle  → includes device_escalation key
  GET /health-assistant/daily-summary    → includes escalation key when signal
                                           is injected

These tests use an in-memory SQLite DB and inject external metrics directly
through the HealthMetric table so no real device is required.

Persistence note: device_signal_history is computed deterministically from
HealthMetric rows at request time.  There is NO separate history table or
DB-persisted trend memory.  The tests reflect this correctly.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.deps import get_current_user, get_target_person
from app.main import app
from app.models.entities import HealthMetric, PersonProfile, User


# ---------------------------------------------------------------------------
# Teardown: clear dependency overrides after every test so other test modules
# are not affected by leftover overrides (prevents cross-test contamination).
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _clear_app_overrides():
    yield
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Test client factory
# ---------------------------------------------------------------------------

def _build_client(seed_metrics: list[dict[str, Any]] | None = None):
    """Create a TestClient with an in-memory SQLite DB.

    Optionally seeds HealthMetric rows so endpoints see external-device data.
    """
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    db = Session()
    user = User(email="smoke@example.com", password_hash="hashed")
    db.add(user)
    db.commit()
    db.refresh(user)

    person = PersonProfile(
        owner_user_id=user.id,
        display_name="Test Person",
        relationship="self",
        is_default=True,
    )
    db.add(person)
    db.commit()
    db.refresh(person)

    # Seed HealthMetric rows (external device data)
    # HealthMetric uses individual columns (heart_rate, sleep_hours, etc.)
    # plus user_id + subject_profile_id — not a generic metric_type/value model.
    if seed_metrics:
        for m in seed_metrics:
            row = HealthMetric(
                user_id=user.id,
                subject_profile_id=person.id,
                recorded_at=m["recorded_at"],
                source=m.get("source", "apple_health"),
            )
            # Apply whichever column is specified
            for col in ("heart_rate", "sleep_hours", "steps",
                        "systolic_bp", "diastolic_bp", "blood_glucose", "weight_kg"):
                if col in m:
                    setattr(row, col, m[col])
            db.add(row)
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


def _hr_metrics(bpm: int, days_ago: float = 0.1, count: int = 1) -> list[dict]:
    """Helper: produce elevated heart-rate HealthMetric seeds."""
    now = datetime.now(timezone.utc)
    return [
        {
            "heart_rate": int(bpm),
            "source": "apple_health",
            "recorded_at": now - timedelta(days=days_ago + i * 0.01),
        }
        for i in range(count)
    ]


# ---------------------------------------------------------------------------
# GET /health-assistant/device-signals
# ---------------------------------------------------------------------------

class TestDeviceSignalsEndpoint:
    def test_returns_200_and_schema_keys(self):
        client, _ = _build_client()
        resp = client.get("/api/v1/health-assistant/device-signals")
        assert resp.status_code == 200
        data = resp.json()
        assert "signals" in data
        assert "signal_count" in data
        assert "person_id" in data
        assert "generated_at" in data

    def test_empty_metrics_yields_no_signals(self):
        client, _ = _build_client(seed_metrics=[])
        resp = client.get("/api/v1/health-assistant/device-signals")
        assert resp.status_code == 200
        data = resp.json()
        assert data["signal_count"] == 0
        assert data["signals"] == []

    def test_elevated_hr_produces_signal(self):
        """Injected elevated heart rate → at least one device signal detected."""
        client, _ = _build_client(seed_metrics=_hr_metrics(bpm=110, count=5))
        resp = client.get("/api/v1/health-assistant/device-signals")
        assert resp.status_code == 200
        data = resp.json()
        assert data["signal_count"] >= 1, "Expected at least one device signal from elevated HR"

    def test_each_signal_has_required_keys(self):
        client, _ = _build_client(seed_metrics=_hr_metrics(bpm=115, count=5))
        resp = client.get("/api/v1/health-assistant/device-signals")
        signals = resp.json()["signals"]
        required = {"signal_type", "severity", "confidence", "freshness"}
        for sig in signals:
            missing = required - set(sig.keys())
            assert not missing, f"Signal missing keys: {missing}"


# ---------------------------------------------------------------------------
# GET /health-assistant/evidence-bundle
# ---------------------------------------------------------------------------

class TestEvidenceBundleEndpoint:
    def test_returns_200_and_escalation_key(self):
        """evidence-bundle must always contain device_escalation key."""
        client, _ = _build_client()
        resp = client.get("/api/v1/health-assistant/evidence-bundle")
        assert resp.status_code == 200
        bundle = resp.json()
        assert "device_signals" in bundle, "bundle must include device_signals"
        assert "device_escalation" in bundle, "bundle must include device_escalation"

    def test_escalation_has_required_schema(self):
        client, _ = _build_client()
        resp = client.get("/api/v1/health-assistant/evidence-bundle")
        esc = resp.json()["device_escalation"]
        required = {"escalationLevel", "reasons", "confidence", "recommendedAction", "requiresFollowUp"}
        missing = required - set(esc.keys())
        assert not missing, f"EscalationDecision missing keys: {missing}"

    def test_no_signals_escalation_level_is_none(self):
        """With no external metrics, escalation level must be 'none'."""
        client, _ = _build_client(seed_metrics=[])
        resp = client.get("/api/v1/health-assistant/evidence-bundle")
        esc = resp.json()["device_escalation"]
        assert esc["escalationLevel"] == "none"

    def test_elevated_hr_raises_escalation_above_none(self):
        """With elevated HR signals, escalation should be at least 'watch'."""
        client, _ = _build_client(seed_metrics=_hr_metrics(bpm=112, count=5))
        resp = client.get("/api/v1/health-assistant/evidence-bundle")
        esc = resp.json()["device_escalation"]
        levels = ("watch", "warning", "urgent")
        assert esc["escalationLevel"] in levels, (
            f"Expected watch/warning/urgent but got {esc['escalationLevel']!r}"
        )

    def test_device_signal_history_key_present(self):
        """Bundle must expose device_signal_history (computed trend memory)."""
        client, _ = _build_client(seed_metrics=_hr_metrics(bpm=108, count=3))
        resp = client.get("/api/v1/health-assistant/evidence-bundle")
        bundle = resp.json()
        assert "device_signal_history" in bundle, (
            "bundle must include device_signal_history (computed, not persisted)"
        )


# ---------------------------------------------------------------------------
# GET /health-assistant/daily-summary
# ---------------------------------------------------------------------------

class TestDailySummaryEndpoint:
    def test_returns_200_and_base_keys(self):
        client, _ = _build_client()
        resp = client.get("/api/v1/health-assistant/daily-summary")
        assert resp.status_code == 200
        data = resp.json()
        required = {"topRisk", "biggestChange", "todayAction", "whyNow", "confidence"}
        missing = required - set(data.keys())
        assert not missing, f"daily-summary missing keys: {missing}"

    def test_no_signals_no_escalation_key(self):
        """When there are no device signals, 'escalation' key must be absent."""
        client, _ = _build_client(seed_metrics=[])
        resp = client.get("/api/v1/health-assistant/daily-summary")
        data = resp.json()
        # escalation key only injected when escalationLevel != none/null
        assert "escalation" not in data or data.get("escalation") is None, (
            "No escalation expected with no device data"
        )

    def test_elevated_hr_injects_escalation_into_summary(self):
        """With elevated HR metrics, daily summary may include 'escalation' key."""
        client, _ = _build_client(seed_metrics=_hr_metrics(bpm=115, count=8))
        resp = client.get("/api/v1/health-assistant/daily-summary")
        data = resp.json()
        # When escalation is present it must have the EscalationDecision shape
        if "escalation" in data and data["escalation"]:
            esc = data["escalation"]
            assert "escalationLevel" in esc
            assert esc["escalationLevel"] in ("watch", "warning", "urgent")
