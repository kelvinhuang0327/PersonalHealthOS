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
from app.services.engagement_analytics_service import build_engagement_analytics
from app.services.notification_intelligence_service import (
    apply_adaptive_notification_timing,
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

    # P6.2 — apply adaptive timing adjustments
    analytics = build_engagement_analytics(history)
    ranked_active = apply_adaptive_notification_timing(ranked_active, analytics)

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
    _trigger_profile_sync(db, str(current_user.id), str(target_person.id))
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
    _trigger_profile_sync(db, str(current_user.id), str(target_person.id))
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
    _trigger_profile_sync(db, str(current_user.id), str(target_person.id))
    return updated


def _trigger_profile_sync(db: Session, user_id: str, person_id: str) -> None:
    """Non-blocking profile sync after any status update (Task 4 auto-sync).

    Never raises — any failure here must not break the primary response.
    """
    try:
        hist = load_notification_history(db, user_id, person_id, days=30)
        sync_profile_from_history(db, user_id, person_id, hist)
    except Exception:  # noqa: BLE001
        pass


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


@router.get('/engagement-analytics')
def get_engagement_analytics(
    target_person: Annotated[PersonProfile, Depends(get_target_person)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    days: Annotated[int, Query(ge=7, le=90)] = 30,
) -> dict[str, Any]:
    """Return engagement analytics for the target person.

    Computes engagement trend, best notification windows, avg response delay,
    action completion rate, and open rate from notification history.

    Returns safe empty/neutral defaults when history is insufficient
    (no hallucination guarantee).
    """
    uid = str(current_user.id)
    pid = str(target_person.id)
    history = load_notification_history(db, uid, pid, days=days)
    return build_engagement_analytics(history)


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


# ---------------------------------------------------------------------------
# Narrative Memory — P7
# ---------------------------------------------------------------------------

from app.services.narrative_memory_service import (  # noqa: E402
    generate_and_persist_narrative_memory,
    load_narrative_memory,
    compare_narrative_periods,
)
from app.services.narrative_intelligence_service import (  # noqa: E402
    build_cross_period_health_reasoning,
)


@router.get('/narrative-memory')
def get_narrative_memory(
    target_person: Annotated[PersonProfile, Depends(get_target_person)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    period_type: Annotated[str, Query(pattern='^(daily|weekly|monthly)$')] = 'weekly',
    days: Annotated[int, Query(ge=7, le=90)] = 30,
) -> dict[str, Any]:
    """Return the most recent stored narrative memory for the target person.

    If no memory has been generated yet, returns an explainable empty result.
    Never returns medical diagnoses — factual observations only.
    """
    uid = str(current_user.id)
    pid = str(target_person.id)

    memories = load_narrative_memory(db, uid, pid, period_type=period_type, limit=1)
    if memories:
        return {
            "person_id": pid,
            "found": True,
            "memory": memories[0],
        }
    return {
        "person_id": pid,
        "found": False,
        "memory": None,
        "message": "尚未生成記憶，請呼叫 POST /narrative-memory/generate 以建立記憶。",
    }


@router.post('/narrative-memory/generate')
def generate_narrative_memory(
    target_person: Annotated[PersonProfile, Depends(get_target_person)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    period_type: Annotated[str, Query(pattern='^(daily|weekly|monthly)$')] = 'weekly',
    days: Annotated[int, Query(ge=7, le=90)] = 30,
) -> dict[str, Any]:
    """Generate and persist a narrative memory for the target person.

    Reads notification history, risk alerts, completed actions, and
    action outcomes for the specified period; builds and stores the memory.

    Returns the generated NarrativeMemoryResult dict.
    """
    uid = str(current_user.id)
    pid = str(target_person.id)
    history = load_notification_history(db, uid, pid, days=days)
    memory = generate_and_persist_narrative_memory(db, uid, pid, period_type, history)
    return {
        "person_id": pid,
        "generated": True,
        "memory": memory,
    }


@router.get('/narrative-memory/cross-period')
def get_cross_period_reasoning(
    target_person: Annotated[PersonProfile, Depends(get_target_person)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    """Return cross-period health reasoning aggregated from all stored narrative memories.

    Loads the most recent daily, weekly, and monthly narrative memories and
    computes trend direction, sustained improvements, long-term risks, and
    carry-over recommendations.

    Never returns medical diagnoses — factual observations only.
    Returns limitations when evidence is insufficient.
    """
    uid = str(current_user.id)
    pid = str(target_person.id)

    daily = load_narrative_memory(db, uid, pid, period_type="daily", limit=7)
    weekly = load_narrative_memory(db, uid, pid, period_type="weekly", limit=4)
    monthly = load_narrative_memory(db, uid, pid, period_type="monthly", limit=3)

    reasoning = build_cross_period_health_reasoning(
        daily_memories=daily,
        weekly_memories=weekly,
        monthly_memories=monthly,
    )

    return {
        "person_id": pid,
        "reasoning": reasoning,
    }


# ---------------------------------------------------------------------------
# Family Health Context — P8
# ---------------------------------------------------------------------------

from pydantic import field_validator  # noqa: E402
from app.models.entities import FamilyRelationship  # noqa: E402
from app.services.family_health_context_service import (  # noqa: E402
    build_family_health_context,
    generate_family_recommendations,
    load_family_evidence_data,
    load_family_relationships,
)


class _FamilyRelationshipBody(BaseModel):
    related_profile_id: str
    relationship_type: str
    permission_level: str = "read_only"

    @field_validator("relationship_type")
    @classmethod
    def _validate_rel_type(cls, v: str) -> str:
        allowed = {"self", "child", "parent", "spouse", "caregiver"}
        if v not in allowed:
            raise ValueError(f"relationship_type must be one of {sorted(allowed)}")
        return v

    @field_validator("permission_level")
    @classmethod
    def _validate_perm(cls, v: str) -> str:
        allowed = {"read_only", "manage", "full_access"}
        if v not in allowed:
            raise ValueError(f"permission_level must be one of {sorted(allowed)}")
        return v


@router.post('/family-relationships', status_code=201)
def create_family_relationship(
    body: _FamilyRelationshipBody,
    target_person: Annotated[PersonProfile, Depends(get_target_person)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    """Create a family relationship between the target person and a related profile.

    relationship_type: self | child | parent | spouse | caregiver
    permission_level:  read_only | manage | full_access

    Returns 201 with the created relationship dict.
    Idempotent — returns existing record if relationship already exists.
    """
    import uuid as _uuid

    uid = current_user.id      # UUID object for DB queries
    pid = target_person.id     # UUID object for DB queries

    # Parse body.related_profile_id to UUID for DB queries
    try:
        related_pid = _uuid.UUID(body.related_profile_id)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=422, detail="related_profile_id is not a valid UUID")

    # Idempotency check
    existing = (
        db.query(FamilyRelationship)
        .filter(
            FamilyRelationship.owner_user_id == uid,
            FamilyRelationship.subject_profile_id == pid,
            FamilyRelationship.related_profile_id == related_pid,
        )
        .first()
    )
    if existing:
        return {
            "id": str(existing.id),
            "owner_user_id": str(uid),
            "subject_profile_id": str(pid),
            "related_profile_id": str(existing.related_profile_id),
            "relationship_type": existing.relationship_type,
            "permission_level": existing.permission_level,
            "created": False,
        }

    # Verify related_profile exists and belongs to this user
    related = db.query(PersonProfile).filter(
        PersonProfile.id == related_pid,
        PersonProfile.owner_user_id == uid,
    ).first()
    if not related:
        raise HTTPException(status_code=404, detail="Related profile not found")

    rel = FamilyRelationship(
        id=_uuid.uuid4(),
        owner_user_id=uid,
        subject_profile_id=pid,
        related_profile_id=related_pid,
        relationship_type=body.relationship_type,
        permission_level=body.permission_level,
    )
    db.add(rel)
    db.commit()
    db.refresh(rel)

    return {
        "id": str(rel.id),
        "owner_user_id": str(uid),
        "subject_profile_id": str(pid),
        "related_profile_id": str(rel.related_profile_id),
        "relationship_type": rel.relationship_type,
        "permission_level": rel.permission_level,
        "created": True,
    }


@router.get('/family-relationships')
def list_family_relationships(
    target_person: Annotated[PersonProfile, Depends(get_target_person)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    """Return all family relationships for the target person."""
    uid = str(current_user.id)
    pid = str(target_person.id)
    relationships = load_family_relationships(db, uid, pid)
    return {
        "person_id": pid,
        "relationships": relationships,
        "total": len(relationships),
    }


@router.get('/family-health-context')
def get_family_health_context_endpoint(
    target_person: Annotated[PersonProfile, Depends(get_target_person)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    """Return the family health context for the target person.

    Aggregates relationships, shared risks, caregiver alerts, child attention
    items, and family action suggestions.

    Returns an explainable empty context when no family relationships exist.
    Never emits medical diagnoses — factual observations only.
    """
    uid = str(current_user.id)
    pid = str(target_person.id)

    relationships = load_family_relationships(db, uid, pid)
    evidence = load_family_evidence_data(db, uid, relationships)
    context = build_family_health_context(
        relationships,
        recommendations_by_profile=evidence["recommendations_by_profile"],
        lab_abnormalities_by_profile=evidence["lab_abnormalities_by_profile"],
        symptom_patterns_by_profile=evidence["symptom_patterns_by_profile"],
        escalations_by_profile=evidence["escalations_by_profile"],
        load_errors_by_profile=evidence["load_errors_by_profile"],
    )
    # Merge permission limitations (Task 1)
    if evidence.get("permission_limitations"):
        context["limitations"].extend(evidence["permission_limitations"])

    return {
        "person_id": pid,
        "context": context,
    }


@router.get('/family-recommendations')
def get_family_recommendations_endpoint(
    target_person: Annotated[PersonProfile, Depends(get_target_person)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    """Return family-level recommendations derived from the family health context.

    Sources child attention items (urgency=high), caregiver alerts (medium),
    shared risks (medium), and family action suggestions (low).

    Deduplicates against active actions.
    Never emits medical diagnoses — factual observations only.
    """
    uid = str(current_user.id)
    pid = str(target_person.id)

    relationships = load_family_relationships(db, uid, pid)
    evidence = load_family_evidence_data(db, uid, relationships)
    context = build_family_health_context(
        relationships,
        recommendations_by_profile=evidence["recommendations_by_profile"],
        lab_abnormalities_by_profile=evidence["lab_abnormalities_by_profile"],
        symptom_patterns_by_profile=evidence["symptom_patterns_by_profile"],
        escalations_by_profile=evidence["escalations_by_profile"],
        load_errors_by_profile=evidence["load_errors_by_profile"],
    )
    # Merge permission limitations (Task 1)
    if evidence.get("permission_limitations"):
        context["limitations"].extend(evidence["permission_limitations"])
    recommendations = generate_family_recommendations(
        context,
        active_actions_by_profile=evidence["active_actions_by_profile"],
    )

    return {
        "person_id": pid,
        "recommendations": recommendations,
        "total": len(recommendations),
    }

