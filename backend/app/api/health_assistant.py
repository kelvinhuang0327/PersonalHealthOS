"""Health Assistant API
========================
Exposes the evidence bundle and Top-3 action recommendations
to the frontend and the orchestrator product-signal layer.
"""
from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
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
from app.services.outcome_feedback_service import compare_expected_vs_actual_outcome

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
