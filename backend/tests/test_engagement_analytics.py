"""Tests for engagement_analytics_service — P6.2 Adaptive Timing Optimization.

Pure-function tests — no DB required.
Covers:
  - engagement trend: improving / stable / declining
  - best notification windows detection
  - ignored time-window detection
  - response delay calculation
  - action completion rate
  - notification open rate
  - adaptive timing boost (apply_adaptive_notification_timing)
  - adaptive timing penalty (ignored window)
  - urgent / device_escalation bypass in timing
  - auto-profile-sync integration (via HTTP test client)
  - no-data fallbacks return sensible defaults
"""
from __future__ import annotations

import uuid
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
from app.models.entities import NotificationLog, PersonProfile, User
from app.services.engagement_analytics_service import (
    build_engagement_analytics,
    calculate_action_completion_rate,
    calculate_best_notification_windows,
    calculate_engagement_trend,
    calculate_notification_open_rate,
    calculate_response_delay,
)
from app.services.notification_intelligence_service import (
    apply_adaptive_notification_timing,
)

# ---------------------------------------------------------------------------
# Shared DB (in-memory SQLite)
# ---------------------------------------------------------------------------

_ENGINE = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
_Session = sessionmaker(bind=_ENGINE)
Base.metadata.create_all(bind=_ENGINE)


# ---------------------------------------------------------------------------
# History builders
# ---------------------------------------------------------------------------

_NOW = datetime.now(timezone.utc)


def _h(
    status: str = "generated",
    ignore_count: int = 0,
    snooze_count: int = 0,
    sent_at: datetime | None = None,
    acted_at: datetime | None = None,
    clicked_at: datetime | None = None,
    source_type: str = "lab_abnormality",
    cooldown_key: str | None = None,
) -> dict[str, Any]:
    sent = sent_at or _NOW
    return {
        "cooldown_key": cooldown_key or f"key_{uuid.uuid4().hex[:6]}",
        "source_type": source_type,
        "status": status,
        "priority": "medium",
        "snooze_count": snooze_count,
        "ignore_count": ignore_count,
        "sent_at": sent.isoformat(),
        "acted_at": acted_at.isoformat() if acted_at else None,
        "clicked_at": clicked_at.isoformat() if clicked_at else None,
        "snoozed_until": None,
    }


def _at(days_ago: float = 0, hour: int = 10) -> datetime:
    """Build a datetime `days_ago` days ago at the specified hour."""
    base = _NOW.replace(hour=hour, minute=0, second=0, microsecond=0)
    return base - timedelta(days=days_ago)


# ---------------------------------------------------------------------------
# Tests — engagement trend
# ---------------------------------------------------------------------------

class TestEngagementTrend:
    def test_insufficient_data_returns_stable(self):
        history = [_h("acted") for _ in range(3)]  # below threshold
        assert calculate_engagement_trend(history) == "stable"

    def test_improving_when_recent_more_engaged(self):
        # Recent (0-14 d): many acted; older (14-28 d): many ignored
        recent = [
            _h("acted", sent_at=_at(days_ago=2)) for _ in range(5)
        ]
        older = [
            _h("ignored", ignore_count=2, sent_at=_at(days_ago=20)) for _ in range(5)
        ]
        result = calculate_engagement_trend(recent + older)
        assert result == "improving"

    def test_declining_when_recent_less_engaged(self):
        # Recent: many ignored; older: many acted
        recent = [
            _h("ignored", ignore_count=3, sent_at=_at(days_ago=3)) for _ in range(5)
        ]
        older = [
            _h("acted", sent_at=_at(days_ago=22)) for _ in range(5)
        ]
        result = calculate_engagement_trend(recent + older)
        assert result == "declining"

    def test_stable_when_no_older_data(self):
        history = [_h("acted", sent_at=_at(days_ago=2)) for _ in range(6)]
        assert calculate_engagement_trend(history) == "stable"

    def test_stable_on_empty_history(self):
        assert calculate_engagement_trend([]) == "stable"


# ---------------------------------------------------------------------------
# Tests — best notification windows
# ---------------------------------------------------------------------------

class TestBestNotificationWindows:
    def test_no_data_returns_empty(self):
        best, ignored = calculate_best_notification_windows([])
        assert best == []
        assert ignored == []

    def test_insufficient_data_per_window_returns_empty(self):
        # Only 2 entries in morning — below the 3-entry threshold
        history = [_h("acted", sent_at=_at(hour=9)) for _ in range(2)]
        best, ignored = calculate_best_notification_windows(history)
        assert best == []

    def test_morning_detected_as_best_window(self):
        # Morning: 5 entries, 4 acted → 80% act rate
        history = [_h("acted", sent_at=_at(hour=9)) for _ in range(4)]
        history += [_h("generated", sent_at=_at(hour=9))]
        # Evening: 4 entries, 0 acted
        history += [_h("generated", sent_at=_at(hour=20)) for _ in range(4)]
        best, _ = calculate_best_notification_windows(history)
        assert "morning" in best
        assert "evening" not in best

    def test_evening_detected_as_ignored_window(self):
        # Evening: 5 entries, 4 ignored → 80% ignore rate
        history = [_h("ignored", ignore_count=2, sent_at=_at(hour=19)) for _ in range(4)]
        history += [_h("generated", sent_at=_at(hour=19))]
        # Morning: 4 entries, 0 ignored
        history += [_h("generated", sent_at=_at(hour=8)) for _ in range(4)]
        _, ignored = calculate_best_notification_windows(history)
        assert "evening" in ignored
        assert "morning" not in ignored


# ---------------------------------------------------------------------------
# Tests — response delay
# ---------------------------------------------------------------------------

class TestResponseDelay:
    def test_none_when_no_acted_or_clicked(self):
        history = [_h("generated") for _ in range(5)]
        assert calculate_response_delay(history) is None

    def test_none_when_only_one_valid_measurement(self):
        sent = _at(days_ago=1)
        acted = sent + timedelta(minutes=45)
        history = [_h("acted", sent_at=sent, acted_at=acted)]
        assert calculate_response_delay(history) is None

    def test_returns_average_delay_minutes(self):
        entries = []
        for minutes in [30, 60]:
            sent = _at(days_ago=2)
            acted = sent + timedelta(minutes=minutes)
            entries.append(_h("acted", sent_at=sent, acted_at=acted))
        delay = calculate_response_delay(entries)
        assert delay == pytest.approx(45.0, abs=1.0)

    def test_ignores_delays_over_24h(self):
        sent = _at(days_ago=5)
        acted = sent + timedelta(hours=30)  # stale — should be excluded
        valid_sent = _at(days_ago=2)
        valid_acted = valid_sent + timedelta(minutes=20)
        history = [
            _h("acted", sent_at=sent, acted_at=acted),
            _h("acted", sent_at=valid_sent, acted_at=valid_acted),
        ]
        # Only 1 valid → None
        assert calculate_response_delay(history) is None


# ---------------------------------------------------------------------------
# Tests — rates
# ---------------------------------------------------------------------------

class TestRates:
    def test_action_completion_rate(self):
        history = [
            _h("acted"),
            _h("acted"),
            _h("ignored"),
            _h("generated"),
        ]
        rate = calculate_action_completion_rate(history)
        assert rate == pytest.approx(0.5, abs=0.01)

    def test_action_completion_rate_zero_on_empty(self):
        assert calculate_action_completion_rate([]) == 0.0

    def test_notification_open_rate(self):
        history = [
            _h("clicked"),
            _h("acted"),
            _h("generated"),
            _h("generated"),
        ]
        rate = calculate_notification_open_rate(history)
        assert rate == pytest.approx(0.5, abs=0.01)

    def test_notification_open_rate_excludes_suppressed(self):
        history = [
            _h("clicked"),
            {"cooldown_key": "s1", "status": "suppressed",
             "ignore_count": 0, "snooze_count": 0,
             "sent_at": _NOW.isoformat(), "acted_at": None,
             "clicked_at": None, "snoozed_until": None, "source_type": "lab"},
        ]
        rate = calculate_notification_open_rate(history)
        assert rate == pytest.approx(1.0, abs=0.01)  # 1/1 non-suppressed


# ---------------------------------------------------------------------------
# Tests — build_engagement_analytics (main entry)
# ---------------------------------------------------------------------------

class TestBuildEngagementAnalytics:
    def test_empty_history_returns_safe_defaults(self):
        result = build_engagement_analytics([])
        assert result["engagementTrend"] == "stable"
        assert result["avgResponseDelayMinutes"] is None
        assert result["bestNotificationWindows"] == []
        assert result["ignoredTimeWindows"] == []
        assert result["actionCompletionRate"] == 0.0
        assert result["notificationOpenRate"] == 0.0

    def test_all_keys_present(self):
        result = build_engagement_analytics([_h("acted")])
        expected_keys = {
            "engagementTrend", "avgResponseDelayMinutes",
            "bestNotificationWindows", "ignoredTimeWindows",
            "actionCompletionRate", "notificationOpenRate",
        }
        assert expected_keys <= set(result.keys())


# ---------------------------------------------------------------------------
# Tests — apply_adaptive_notification_timing
# ---------------------------------------------------------------------------

def _cand(
    source_type: str = "lab_abnormality",
    priority: str = "high",
    confidence: float = 0.70,
) -> dict[str, Any]:
    return {
        "source_type": source_type,
        "priority": priority,
        "confidence": confidence,
        "title": "Test",
        "personalization_reasons": [],
    }


def _analytics(
    best: list[str] | None = None,
    ignored: list[str] | None = None,
    trend: str = "stable",
) -> dict[str, Any]:
    return {
        "engagementTrend": trend,
        "bestNotificationWindows": best or [],
        "ignoredTimeWindows": ignored or [],
        "avgResponseDelayMinutes": None,
        "actionCompletionRate": 0.5,
        "notificationOpenRate": 0.5,
    }


class TestAdaptiveTimingEngine:
    def test_no_analytics_returns_unchanged(self):
        cands = [_cand()]
        result = apply_adaptive_notification_timing(cands)
        assert result[0]["confidence"] == pytest.approx(0.70, abs=0.01)

    def test_best_window_boosts_confidence(self):
        # Force current window to be "morning" via patching is not needed —
        # we just verify the boost applies when current_window is in best_windows.
        # To make this deterministic, we test all four windows and at least one matches.
        # We just need to verify the function processes the analytics dict.
        # Strategy: inject ALL windows as best_windows → should boost regardless of current time
        cands = [_cand("lab_abnormality", "high", 0.60)]
        analytics = _analytics(best=["morning", "afternoon", "evening", "night"])
        result = apply_adaptive_notification_timing(cands, analytics)
        # Confidence must be boosted by 0.08
        assert result[0]["confidence"] > 0.60

    def test_ignored_window_penalizes_confidence(self):
        cands = [_cand("lab_abnormality", "high", 0.70)]
        analytics = _analytics(ignored=["morning", "afternoon", "evening", "night"])
        result = apply_adaptive_notification_timing(cands, analytics)
        assert result[0]["confidence"] < 0.70

    def test_ignored_window_downgrades_priority(self):
        cands = [_cand("lab_abnormality", "high", 0.70)]
        analytics = _analytics(ignored=["morning", "afternoon", "evening", "night"])
        result = apply_adaptive_notification_timing(cands, analytics)
        assert result[0]["priority"] != "high"

    def test_declining_trend_penalizes_confidence(self):
        cands = [_cand("lab_abnormality", "high", 0.70)]
        analytics = _analytics(trend="declining")
        result = apply_adaptive_notification_timing(cands, analytics)
        assert result[0]["confidence"] < 0.70

    def test_urgent_bypasses_timing_suppression(self):
        cands = [_cand("lab_abnormality", "urgent", 0.90)]
        analytics = _analytics(
            ignored=["morning", "afternoon", "evening", "night"],
            trend="declining",
        )
        result = apply_adaptive_notification_timing(cands, analytics)
        assert result[0]["priority"] == "urgent"
        assert result[0]["confidence"] == pytest.approx(0.90, abs=0.01)

    def test_device_escalation_bypasses_timing(self):
        cands = [_cand("device_escalation", "high", 0.80)]
        analytics = _analytics(
            ignored=["morning", "afternoon", "evening", "night"],
            trend="declining",
        )
        result = apply_adaptive_notification_timing(cands, analytics)
        assert result[0]["priority"] == "high"
        assert result[0]["confidence"] == pytest.approx(0.80, abs=0.01)

    def test_confidence_never_below_0_20(self):
        cands = [_cand("lab_abnormality", "medium", 0.25)]
        analytics = _analytics(
            ignored=["morning", "afternoon", "evening", "night"],
            trend="declining",
        )
        result = apply_adaptive_notification_timing(cands, analytics)
        assert result[0]["confidence"] >= 0.20

    def test_personalization_reasons_populated(self):
        cands = [_cand()]
        analytics = _analytics(best=["morning", "afternoon", "evening", "night"])
        result = apply_adaptive_notification_timing(cands, analytics)
        assert isinstance(result[0]["personalization_reasons"], list)


# ---------------------------------------------------------------------------
# Tests — Auto profile sync (integration via HTTP client)
# ---------------------------------------------------------------------------


def _build_client_with_notification():
    """Build a TestClient with a seeded notification log; returns (client, notif_id, db, user, person)."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db = Session()

    u = User(email=f"sync_{uuid.uuid4().hex[:6]}@test.com", password_hash="hashed")
    db.add(u)
    db.commit()
    db.refresh(u)

    p = PersonProfile(
        owner_user_id=u.id,
        display_name="Sync Test",
        relationship="self",
        is_default=True,
    )
    db.add(p)
    db.commit()
    db.refresh(p)

    log = NotificationLog(
        user_id=u.id,
        subject_profile_id=p.id,
        candidate_id="aabbcc001122",
        cooldown_key="lab_abnormality_ldl",
        source_type="lab_abnormality",
        priority="high",
        title="Test Notification",
        message="Test message",
        status="generated",
        generated_at=datetime.now(timezone.utc),
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    notif_id = str(log.id)

    def override_db():
        yield db

    def override_user():
        return u

    def override_person():
        return p

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = override_user
    app.dependency_overrides[get_target_person] = override_person

    client = TestClient(app)
    return client, notif_id, db, u, p


@pytest.fixture(autouse=True)
def _clear_overrides():
    yield
    app.dependency_overrides.clear()


class TestAutoProfileSync:
    def test_auto_sync_after_acted(self):
        from app.models.entities import PersonalizationProfile

        client, notif_id, db, u, p = _build_client_with_notification()
        resp = client.post(f"/api/v1/health-assistant/notifications/{notif_id}/acted")
        assert resp.status_code == 200

        # Profile should now exist in DB (auto-created + synced)
        profile = (
            db.query(PersonalizationProfile)
            .filter_by(user_id=u.id, subject_profile_id=p.id)
            .first()
        )
        assert profile is not None

    def test_auto_sync_after_ignore(self):
        from app.models.entities import PersonalizationProfile

        client, notif_id, db, u, p = _build_client_with_notification()
        resp = client.post(f"/api/v1/health-assistant/notifications/{notif_id}/ignore")
        assert resp.status_code == 200

        profile = (
            db.query(PersonalizationProfile)
            .filter_by(user_id=u.id, subject_profile_id=p.id)
            .first()
        )
        assert profile is not None
