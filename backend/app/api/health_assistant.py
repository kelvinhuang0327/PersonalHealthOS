"""Health Assistant API
========================
Exposes the evidence bundle and Top-3 action recommendations
to the frontend and the orchestrator product-signal layer.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Annotated, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, get_target_person
from app.models.entities import PersonProfile, User
from app.services.device_signal_detection_service import detect_device_signals
from app.services.health_assistant_service import (
    build_evidence_bundle,
    build_product_signals,
    generate_daily_health_summary,
    get_action_recommendations,
)
from app.services.adaptive_recommendation_service import adaptive_recommendation_score
from app.services.notification_intelligence_service import (
    apply_notification_fatigue_guard,
    apply_personalization_ranking,
    build_notification_candidates,
)
from app.services.notification_history_service import (
    get_notification_by_id,
    load_notification_history,
    persist_notification_candidates,
    update_notification_status,
)
from app.services.outcome_feedback_service import compare_expected_vs_actual_outcome
from app.services.personalization_service import (
    get_or_create_profile,
    profile_to_dict,
    sync_profile_from_history,
)

router = APIRouter(prefix='/health-assistant', tags=['health-assistant'])


@router.get('/evidence-bundle')
def get_evidence_bundle(
    target_person: Annotated[PersonProfile, Depends(get_target_person)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    """Return the unified health evidence bundle for the target person.

    Each evidence item carries source_type, source_id, recency, confidence,
    evidence_level, and summary.  Missing data is explicit in `missing_data`.
    """
    return build_evidence_bundle(db, str(current_user.id), str(target_person.id))


@router.get('/recommendations')
def get_recommendations(
    target_person: Annotated[PersonProfile, Depends(get_target_person)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    """Return Top-3 health action recommendations for the target person.

    Recommendations are deduplicated against active/completed actions.
    User-created actions always remain visible.
    Completed actions are hidden unless recurrence/resurface applies.
    """
    return get_action_recommendations(
        db,
        str(current_user.id),
        str(target_person.id),
    )


@router.get('/device-signals')
def get_device_signals(
    target_person: Annotated[PersonProfile, Depends(get_target_person)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    """Return device-sourced health signals detected from external metrics.

    Signals are derived from HealthMetric rows where source != 'manual'.
    Stale readings (> 24 h) carry reduced confidence.
    Returns an empty list when no external device data is available.
    """
    from app.services.health_assistant_service import build_evidence_bundle  # local to avoid circular
    from datetime import datetime, timezone

    bundle = build_evidence_bundle(db, str(current_user.id), str(target_person.id))
    signals = bundle.get("device_signals", [])
    return {
        "person_id": str(target_person.id),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "signals": signals,
        "signal_count": len(signals),
    }


@router.get('/product-signals')
def get_product_signals_endpoint(
    target_person: Annotated[PersonProfile, Depends(get_target_person)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    days: Annotated[int, Query(ge=7, le=90)] = 30,
) -> dict[str, Any]:
    """Return product engagement signals for the orchestrator.

    Used by detect_product_issues() to generate problem-driven sprint tasks.
    """
    return build_product_signals(db, str(current_user.id), str(target_person.id), days=days)


@router.get('/outcome-feedback')
def get_outcome_feedback(
    target_person: Annotated[PersonProfile, Depends(get_target_person)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    window_days: Annotated[int, Query(ge=7, le=30)] = 7,
) -> dict[str, Any]:
    """Return outcome feedback comparing expected vs actual health impact.

    window_days must be 7, 14, or 30. Values outside those are clamped to 7.
    Completed actions enter full comparison; active actions show as 'tracking'.
    Insufficient metric data is always surfaced explicitly — never hallucinated.
    """
    if window_days not in (7, 14, 30):
        window_days = 7
    return compare_expected_vs_actual_outcome(
        db, str(current_user.id), str(target_person.id), window_days
    )


@router.get('/daily-summary')
def get_daily_summary(
    target_person: Annotated[PersonProfile, Depends(get_target_person)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    """Return today's health summary narrative for the daily companion card.

    Derives topRisk, biggestChange, todayAction, whyNow, confidence,
    missingData, and encouragement without any LLM call — all logic is
    deterministic and grounded in the evidence bundle.
    """
    return generate_daily_health_summary(db, str(current_user.id), str(target_person.id))


@router.get('/notifications/intelligent')
def get_intelligent_notifications(
    target_person: Annotated[PersonProfile, Depends(get_target_person)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    """Return intelligent notification candidates for the target person.

    Builds the evidence bundle, generates candidates, loads DB history to
    apply the stateful fatigue guard, then persists results.

    Response keys
    -------------
    items        — active candidates with notification_id for status updates
    suppressed   — suppressed candidates with suppress_reason + notification_id
    generated_at — ISO-8601 timestamp
    total_candidates — total before guard
    """
    uid = str(current_user.id)
    pid = str(target_person.id)

    bundle = build_evidence_bundle(db, uid, pid)
    history = load_notification_history(db, uid, pid)
    active_rule_ids: set[str] = {
        act.get("rule_id", "") for act in bundle.get("actions", [])
        if act.get("rule_id")
    }
    candidates = build_notification_candidates(bundle)
    result = apply_notification_fatigue_guard(candidates, history, active_rule_ids)

    # P6 — apply personalization ranking to active candidates
    profile = get_or_create_profile(db, uid, pid)
    profile_dict = profile_to_dict(profile)
    ranked_active = apply_personalization_ranking(result["active"], profile_dict)

    # Persist and get DB notification_ids
    id_map = persist_notification_candidates(
        db, uid, pid, ranked_active, result["suppressed"]
    )

    def _attach_id(c: dict) -> dict:
        out = dict(c)
        out["notification_id"] = id_map.get(c.get("candidate_id", ""))
        return out

    return {
        "person_id": pid,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "items": [_attach_id(c) for c in ranked_active],
        "suppressed": [_attach_id(c) for c in result["suppressed"]],
        "total_candidates": len(candidates),
    }


# ---------------------------------------------------------------------------
# Notification status update endpoints (P5 Learning Loop)
# ---------------------------------------------------------------------------

class _SnoozeBody(BaseModel):
    hours: Optional[int] = 24
    snoozed_until: Optional[str] = None  # ISO-8601; overrides hours when set


def _get_log_or_404(
    notification_id: str,
    current_user: User,
    target_person: PersonProfile,
    db: Session,
):
    """Shared helper — raises 404 if notification not found for this person."""
    record = get_notification_by_id(
        db, notification_id, str(current_user.id), str(target_person.id)
    )
    if record is None:
        raise HTTPException(status_code=404, detail="Notification not found")
    return record


@router.post('/notifications/{notification_id}/snooze')
def snooze_notification(
    notification_id: str,
    target_person: Annotated[PersonProfile, Depends(get_target_person)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    body: Optional[_SnoozeBody] = None,
) -> dict[str, Any]:
    """Snooze a notification for a specified number of hours (default 24)."""
    _get_log_or_404(notification_id, current_user, target_person, db)
    body = body or _SnoozeBody()

    # Resolve snoozed_until
    if body.snoozed_until:
        try:
            snoozed_until_dt = datetime.fromisoformat(body.snoozed_until)
            if snoozed_until_dt.tzinfo is None:
                snoozed_until_dt = snoozed_until_dt.replace(tzinfo=timezone.utc)
        except ValueError:
            snoozed_until_dt = None
    else:
        hours = max(1, body.hours or 24)
        snoozed_until_dt = datetime.now(timezone.utc) + timedelta(hours=hours)

    updated = update_notification_status(
        db, notification_id, str(current_user.id), str(target_person.id),
        status="snoozed", snoozed_until=snoozed_until_dt,
    )
    return updated


@router.post('/notifications/{notification_id}/ignore')
def ignore_notification(
    notification_id: str,
    target_person: Annotated[PersonProfile, Depends(get_target_person)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    """Mark notification as ignored (increments ignore_count)."""
    _get_log_or_404(notification_id, current_user, target_person, db)
    updated = update_notification_status(
        db, notification_id, str(current_user.id), str(target_person.id),
        status="ignored",
    )
    return updated


@router.post('/notifications/{notification_id}/click')
def click_notification(
    notification_id: str,
    target_person: Annotated[PersonProfile, Depends(get_target_person)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    """Mark notification as clicked."""
    _get_log_or_404(notification_id, current_user, target_person, db)
    updated = update_notification_status(
        db, notification_id, str(current_user.id), str(target_person.id),
        status="clicked",
    )
    return updated


@router.post('/notifications/{notification_id}/acted')
def acted_notification(
    notification_id: str,
    target_person: Annotated[PersonProfile, Depends(get_target_person)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    """Mark notification as acted upon (strongest positive signal)."""
    _get_log_or_404(notification_id, current_user, target_person, db)
    updated = update_notification_status(
        db, notification_id, str(current_user.id), str(target_person.id),
        status="acted",
    )
    return updated


# ---------------------------------------------------------------------------
# P6 — Personalization profile endpoints
# ---------------------------------------------------------------------------

@router.get('/personalization-profile')
def get_personalization_profile(
    target_person: Annotated[PersonProfile, Depends(get_target_person)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    """Return the personalization profile for the target person.

    Creates a neutral default profile if none exists yet.
    """
    profile = get_or_create_profile(db, str(current_user.id), str(target_person.id))
    return profile_to_dict(profile)


@router.post('/personalization-profile/sync')
def sync_personalization_profile(
    target_person: Annotated[PersonProfile, Depends(get_target_person)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    days: Annotated[int, Query(ge=7, le=90)] = 30,
) -> dict[str, Any]:
    """Recompute the personalization profile from recent notification history.

    Reads the last `days` days of notification history and updates:
    acted_categories, ignored_categories, high_response_categories,
    engagement_score, response_style, preferred_notification_types.

    Returns the updated profile dict.
    """
    uid = str(current_user.id)
    pid = str(target_person.id)
    history = load_notification_history(db, uid, pid, days=days)
    profile = sync_profile_from_history(db, uid, pid, history)
    return profile_to_dict(profile)

