"""Personalization Service — P6 Adaptive Health Assistant
==========================================================
Manages the PersonalizationProfile per user+person.
Learns from notification history (snooze / ignore / click / acted) to
produce an ever-improving profile that feeds the adaptive ranking pipeline.

Public API
----------
get_or_create_profile(db, user_id, person_id) -> PersonalizationProfile
    Return existing profile or create a default one.

sync_profile_from_history(db, user_id, person_id, notification_history)
    Recompute the profile from raw notification history records and persist.

profile_to_dict(profile) -> dict
    Serialize profile to a JSON-safe dict for API responses.

_DEFAULT_PROFILE
    Fallback dict used when no profile exists (pure-function consumers).
"""
from __future__ import annotations

import uuid as _uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.models.entities import PersonalizationProfile

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Minimum acted count for a category to be "high-response"
_HIGH_RESPONSE_THRESHOLD = 2

# Engagement scoring
_ENGAGEMENT_ACT_WEIGHT = 0.60
_ENGAGEMENT_CLICK_WEIGHT = 0.30
_ENGAGEMENT_SNOOZE_WEIGHT = -0.10
_ENGAGEMENT_IGNORE_WEIGHT = -0.20

# Default profile when no history is available
_DEFAULT_PROFILE: dict[str, Any] = {
    "engagement_score": 0.5,
    "response_style": "balanced",
    "preferred_notification_timing": {},
    "preferred_notification_types": [],
    "ignored_categories": {},
    "acted_categories": {},
    "high_response_categories": [],
    "avg_response_delay_minutes": None,
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _to_uuid(val: str | _uuid.UUID) -> _uuid.UUID:
    return val if isinstance(val, _uuid.UUID) else _uuid.UUID(str(val))


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


# ---------------------------------------------------------------------------
# Public functions
# ---------------------------------------------------------------------------


def get_or_create_profile(
    db: Session,
    user_id: str,
    person_id: str,
) -> PersonalizationProfile:
    """Return the existing PersonalizationProfile or create a neutral default."""
    uid = _to_uuid(user_id)
    pid = _to_uuid(person_id)

    profile = (
        db.query(PersonalizationProfile)
        .filter_by(user_id=uid, subject_profile_id=pid)
        .first()
    )
    if profile:
        return profile

    profile = PersonalizationProfile(
        user_id=uid,
        subject_profile_id=pid,
        engagement_score=Decimal("0.5"),
        response_style="balanced",
        preferred_notification_timing={},
        preferred_notification_types=[],
        ignored_categories={},
        acted_categories={},
        high_response_categories=[],
        avg_response_delay_minutes=None,
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


def sync_profile_from_history(
    db: Session,
    user_id: str,
    person_id: str,
    notification_history: list[dict[str, Any]],
) -> PersonalizationProfile:
    """Recompute personalization profile from notification history and persist.

    notification_history is the list returned by load_notification_history():
        cooldown_key, priority, status, snooze_count, ignore_count,
        sent_at, snoozed_until
    Plus optional fields from the full NotificationLog:
        source_type, clicked_at, acted_at

    Computed fields
    ---------------
    acted_categories   — {source_type: total acted signals}
    ignored_categories — {source_type: total ignore_count sum}
    high_response_categories — source_types with act_count >= 2
    engagement_score   — weighted signal ratio 0.0–1.0
    response_style     — derived from engagement_score
    """
    profile = get_or_create_profile(db, user_id, person_id)

    acted_cats: dict[str, int] = {}
    ignored_cats: dict[str, int] = {}
    total_acted = 0
    total_clicked = 0
    total_snoozed = 0
    total_ignored = 0
    total_records = len(notification_history)

    for h in notification_history:
        src = h.get("source_type") or _infer_source_from_key(h.get("cooldown_key", ""))
        status = h.get("status", "")
        ig_count = int(h.get("ignore_count", 0))
        sn_count = int(h.get("snooze_count", 0))

        if status == "acted":
            acted_cats[src] = acted_cats.get(src, 0) + 1
            total_acted += 1
        if status == "clicked":
            total_clicked += 1
        if ig_count > 0:
            ignored_cats[src] = ignored_cats.get(src, 0) + ig_count
            total_ignored += ig_count
        if sn_count > 0:
            total_snoozed += sn_count

    # High-response categories
    high_response = [k for k, v in acted_cats.items() if v >= _HIGH_RESPONSE_THRESHOLD]

    # Preferred notification types (top acted categories, desc)
    preferred_types = sorted(acted_cats, key=lambda k: acted_cats[k], reverse=True)[:3]

    # Engagement score: ratio of positive signals minus negative signals
    if total_records == 0:
        eng = 0.5
    else:
        positive = total_acted * _ENGAGEMENT_ACT_WEIGHT + total_clicked * _ENGAGEMENT_CLICK_WEIGHT
        negative = total_ignored * abs(_ENGAGEMENT_IGNORE_WEIGHT) + total_snoozed * abs(_ENGAGEMENT_SNOOZE_WEIGHT)
        raw = (positive - negative) / max(total_records, 1)
        eng = _clamp(0.5 + raw, 0.05, 0.95)

    # Response style
    if eng >= 0.65:
        style = "proactive"
    elif eng <= 0.30:
        style = "minimal"
    else:
        style = "balanced"

    # Persist
    profile.acted_categories = acted_cats
    profile.ignored_categories = ignored_cats
    profile.high_response_categories = high_response
    profile.preferred_notification_types = preferred_types
    profile.engagement_score = Decimal(str(round(eng, 3)))
    profile.response_style = style

    db.commit()
    db.refresh(profile)
    return profile


def profile_to_dict(profile: PersonalizationProfile | None) -> dict[str, Any]:
    """Serialize PersonalizationProfile to a JSON-safe dict.

    Returns _DEFAULT_PROFILE values when profile is None (fallback).
    """
    if profile is None:
        return dict(_DEFAULT_PROFILE)

    def _dec(v: Any) -> float | None:
        if v is None:
            return None
        return float(v)

    return {
        "id": str(profile.id),
        "engagement_score": _dec(profile.engagement_score),
        "response_style": profile.response_style or "balanced",
        "preferred_notification_timing": profile.preferred_notification_timing or {},
        "preferred_notification_types": profile.preferred_notification_types or [],
        "ignored_categories": profile.ignored_categories or {},
        "acted_categories": profile.acted_categories or {},
        "high_response_categories": profile.high_response_categories or [],
        "avg_response_delay_minutes": _dec(profile.avg_response_delay_minutes),
        "last_updated_at": (
            profile.last_updated_at.isoformat()
            if profile.last_updated_at
            else None
        ),
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _infer_source_from_key(cooldown_key: str) -> str:
    """Guess source_type from cooldown_key prefix."""
    if cooldown_key.startswith("lab_"):
        return "lab_abnormality"
    if cooldown_key.startswith("device_"):
        return "device_escalation"
    if cooldown_key.startswith("symptom_"):
        return "symptom_pattern"
    if cooldown_key.startswith("risk_"):
        return "risk_alert"
    return "unknown"
