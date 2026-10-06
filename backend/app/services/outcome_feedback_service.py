"""Outcome Feedback Service
============================
Compares expected health impact of completed HealthActions against actual
metric changes, producing per-action outcome assessments.

Anti-hallucination rules
-------------------------
- "improved" is ONLY emitted when:
    (a) an ActionOutcome row with outcome_label='improved' exists, OR
    (b) both before AND after HealthMetric values exist and the delta moves
        in the improvement direction for that metric type.
- Active actions are shown only as "tracking"; no outcome is inferred.
- Missing metrics surface as "insufficient_data", never as a positive result.
- Partial metric data (only before OR only after) → "insufficient_data".
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.entities import ActionOutcome, HealthAction, HealthMetric

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_METRIC_LABEL: dict[str, str] = {
    "systolic_bp": "收縮壓",
    "diastolic_bp": "舒張壓",
    "blood_glucose": "血糖",
    "weight_kg": "體重",
    "heart_rate": "心率",
    "sleep_hours": "睡眠",
    "steps": "步數",
}

# Category keyword → HealthMetric field name
_CATEGORY_METRIC: dict[str, str] = {
    "bp": "systolic_bp",
    "blood_pressure": "systolic_bp",
    "cardiovascular": "systolic_bp",
    "heart": "systolic_bp",
    "glucose": "blood_glucose",
    "diabetes": "blood_glucose",
    "metabolic": "blood_glucose",
    "weight": "weight_kg",
    "lifestyle": "weight_kg",
    "fitness": "weight_kg",
    "sleep": "sleep_hours",
    "activity": "steps",
    "steps": "steps",
    "movement": "steps",
    "exercise": "steps",
}

# Lower value = healthier (decrease → improvement)
_LOWER_IS_BETTER: frozenset[str] = frozenset(
    {"systolic_bp", "diastolic_bp", "blood_glucose", "weight_kg"}
)
# Higher value = healthier (increase → improvement)
_HIGHER_IS_BETTER: frozenset[str] = frozenset({"sleep_hours", "steps"})

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _aware(dt: datetime) -> datetime:
    """Return dt as timezone-aware UTC."""
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


def _derive_expected_impact(action: Any) -> str:
    """Derive a human-readable expected health impact from action category."""
    cat = (action.category or "").lower()
    if any(k in cat for k in ("bp", "blood_pressure", "cardiovascular", "heart")):
        return "預期有助於降低血壓"
    if any(k in cat for k in ("glucose", "diabetes", "metabolic")):
        return "預期有助於穩定血糖"
    if "weight" in cat:
        return "預期有助於體重管理"
    if "sleep" in cat:
        return "預期有助於改善睡眠品質"
    if any(k in cat for k in ("activity", "steps", "exercise", "fitness", "movement")):
        return "預期有助於增加活動量"
    return "預期改善整體健康狀態"


def _direction_from_delta(metric_type: str, delta: float) -> str:
    """Map a numeric delta to 'improved' | 'worsened' | 'stable'."""
    if abs(delta) < 0.001:
        return "stable"
    if metric_type in _LOWER_IS_BETTER:
        return "improved" if delta < 0 else "worsened"
    if metric_type in _HIGHER_IS_BETTER:
        return "improved" if delta > 0 else "worsened"
    return "stable"


def _outcome_status_from_direction(direction: str) -> str:
    mapping = {"improved": "improved", "worsened": "deteriorated", "stable": "unchanged"}
    return mapping.get(direction, "unchanged")


def _make_explanation(outcome_status: str, metric_type: str | None, action_title: str) -> str:
    label = _METRIC_LABEL.get(metric_type or "", "健康指標")
    if outcome_status == "improved":
        return f"「{action_title}」執行後，{label} 出現改善趨勢。"
    if outcome_status == "deteriorated":
        return f"「{action_title}」執行後，{label} 有所波動，建議持續觀察。"
    if outcome_status == "unchanged":
        return f"「{action_title}」執行後，{label} 維持穩定，請繼續堅持。"
    if outcome_status == "tracking":
        return f"正在追蹤中，完成「{action_title}」後將評估實際健康效果。"
    # insufficient_data
    return f"尚未有足夠的 {label} 數據來評估效果，請繼續記錄。"


_FEEDBACK_SAFE_COPY: dict[str, str] = {
    "not_useful": (
        "回饋已記錄：您標記此建議「沒有用」。"
        "我們會將此回饋用於改善未來建議，但這不代表任何健康效果的判斷。"
    ),
    "not_applicable": (
        "回饋已記錄：您標記此建議「不適合我」。"
        "我們會將此回饋用於改善未來建議，但這不代表任何健康效果的判斷。"
    ),
    "snoozed": (
        "您已延後此建議。尚未評估效果，系統會在到期後重新評估是否提醒您。"
    ),
}


def _process_dismissed_action(action: Any) -> dict[str, Any]:
    """Return a safe, non-overclaiming record for not_useful/not_applicable actions.

    Guarantees
    ----------
    - outcome_status never claims effectiveness or improvement.
    - confidence is always 0.0 — no metric evidence, just user feedback.
    - explanation is user-feedback acknowledgement only.
    """
    status = action.status  # 'not_useful' or 'not_applicable'
    return {
        "action_id": str(action.id),
        "action_title": action.title,
        "status": status,
        "completed_at": None,
        "expected_health_impact": _derive_expected_impact(action),
        "outcome_status": status,
        "actual_metric_change": None,
        "adherence_status": "dismissed",
        "evidence_sources": [],
        "confidence": 0.0,
        "explanation": _FEEDBACK_SAFE_COPY.get(status, "回饋已記錄。"),
        "next_check_in": None,
    }


def _process_snoozed_action(action: Any, now: datetime) -> dict[str, Any]:
    """Return a safe record for snoozed actions.

    Guarantees
    ----------
    - outcome_status is 'snoozed' — no effectiveness claim.
    - confidence is always 0.0.
    - snoozed_until is passed through for UI display.
    """
    raw_snooze = getattr(action, "snoozed_until", None)
    snoozed_until_iso: str | None = (
        _aware(raw_snooze).isoformat() if raw_snooze is not None else None
    )
    return {
        "action_id": str(action.id),
        "action_title": action.title,
        "status": "snoozed",
        "completed_at": None,
        "expected_health_impact": _derive_expected_impact(action),
        "outcome_status": "snoozed",
        "actual_metric_change": None,
        "adherence_status": "snoozed",
        "evidence_sources": [],
        "confidence": 0.0,
        "explanation": _FEEDBACK_SAFE_COPY["snoozed"],
        "next_check_in": snoozed_until_iso,
    }


def _next_check_in(completed_at: datetime, window_days: int, now: datetime) -> str:
    """Return the ISO date for the next evaluation checkpoint."""
    check = completed_at + timedelta(days=window_days)
    return (now if check < now else check).date().isoformat()


def _process_completed_action(
    action: Any,
    outcomes_by_action: dict,
    relevant_metrics: list,
    now: datetime,
    window_days: int,
) -> dict[str, Any]:
    action_id = action.id
    raw_completed = action.completed_at or action.updated_at or now
    completed_at = _aware(raw_completed)
    expected_impact = _derive_expected_impact(action)
    cat = (action.category or "").lower()
    metric_type: str | None = _CATEGORY_METRIC.get(cat)

    # ── Priority 1: use an existing ActionOutcome record (most authoritative) ──
    action_outcomes = outcomes_by_action.get(action_id, [])
    if action_outcomes:
        best = max(
            action_outcomes,
            key=lambda o: _aware(o.computed_at) if o.computed_at else now,
        )
        raw_label = best.outcome_label or "no_change"
        # Normalise persisted labels to the public outcome-feedback vocabulary.
        if raw_label == "no_change":
            outcome_status = "unchanged"
        elif raw_label == "worse":
            outcome_status = "deteriorated"
        elif raw_label in ("improved", "deteriorated", "unchanged"):
            outcome_status = raw_label
        else:
            outcome_status = "unchanged"

        mt = best.metric_type or metric_type or "unknown"
        before_val = float(best.before_value) if best.before_value is not None else None
        after_val = float(best.after_value) if best.after_value is not None else None
        delta = float(best.delta) if best.delta is not None else None
        direction = _direction_from_delta(mt, delta) if delta is not None else "stable"

        return {
            "action_id": str(action_id),
            "action_title": action.title,
            "status": "completed",
            "completed_at": completed_at.isoformat(),
            "expected_health_impact": expected_impact,
            "outcome_status": outcome_status,
            "actual_metric_change": {
                "metric_type": mt,
                "before_value": before_val,
                "after_value": after_val,
                "delta": delta,
                "direction": direction,
            },
            "adherence_status": "completed",
            "evidence_sources": ["action_outcome"],
            "confidence": 0.80,
            "explanation": _make_explanation(outcome_status, mt, action.title),
            "next_check_in": _next_check_in(completed_at, window_days, now),
        }

    # ── Priority 2: derive from raw HealthMetric before/after split ────────
    if metric_type:
        before_metrics = [
            m for m in relevant_metrics
            if _aware(m.recorded_at) <= completed_at
            and getattr(m, metric_type, None) is not None
        ]
        after_metrics = [
            m for m in relevant_metrics
            if _aware(m.recorded_at) > completed_at
            and getattr(m, metric_type, None) is not None
        ]

        if before_metrics and after_metrics:
            before_avg = (
                sum(float(getattr(m, metric_type)) for m in before_metrics)
                / len(before_metrics)
            )
            after_avg = (
                sum(float(getattr(m, metric_type)) for m in after_metrics)
                / len(after_metrics)
            )
            delta = after_avg - before_avg
            direction = _direction_from_delta(metric_type, delta)
            outcome_status = _outcome_status_from_direction(direction)

            return {
                "action_id": str(action_id),
                "action_title": action.title,
                "status": "completed",
                "completed_at": completed_at.isoformat(),
                "expected_health_impact": expected_impact,
                "outcome_status": outcome_status,
                "actual_metric_change": {
                    "metric_type": metric_type,
                    "before_value": round(before_avg, 2),
                    "after_value": round(after_avg, 2),
                    "delta": round(delta, 2),
                    "direction": direction,
                },
                "adherence_status": "completed",
                "evidence_sources": ["health_metric"],
                "confidence": 0.60,
                "explanation": _make_explanation(outcome_status, metric_type, action.title),
                "next_check_in": _next_check_in(completed_at, window_days, now),
            }

        # Partial data — only one side of the split available
        has_before = bool(before_metrics)
        has_after = bool(after_metrics)
        if has_before or has_after:
            source = before_metrics if has_before else after_metrics
            vals = [float(getattr(m, metric_type)) for m in source]
            partial_avg = round(sum(vals) / len(vals), 2)
            return {
                "action_id": str(action_id),
                "action_title": action.title,
                "status": "completed",
                "completed_at": completed_at.isoformat(),
                "expected_health_impact": expected_impact,
                "outcome_status": "insufficient_data",
                "actual_metric_change": {
                    "metric_type": metric_type,
                    "before_value": partial_avg if has_before else None,
                    "after_value": partial_avg if has_after else None,
                    "delta": None,
                    "direction": None,
                },
                "adherence_status": "completed",
                "evidence_sources": ["health_metric"],
                "confidence": 0.35,
                "explanation": _make_explanation(
                    "insufficient_data", metric_type, action.title
                ),
                "next_check_in": _next_check_in(completed_at, window_days, now),
            }

    # ── No data at all ─────────────────────────────────────────────────────
    return {
        "action_id": str(action_id),
        "action_title": action.title,
        "status": "completed",
        "completed_at": completed_at.isoformat(),
        "expected_health_impact": expected_impact,
        "outcome_status": "insufficient_data",
        "actual_metric_change": None,
        "adherence_status": "completed",
        "evidence_sources": [],
        "confidence": 0.20,
        "explanation": _make_explanation("insufficient_data", metric_type, action.title),
        "next_check_in": _next_check_in(completed_at, window_days, now),
    }


def _process_active_action(action: Any, now: datetime, window_days: int) -> dict[str, Any]:
    expected_impact = _derive_expected_impact(action)
    next_ci = (now + timedelta(days=window_days)).date().isoformat()
    return {
        "action_id": str(action.id),
        "action_title": action.title,
        "status": "tracking",
        "completed_at": None,
        "expected_health_impact": expected_impact,
        "outcome_status": "tracking",
        "actual_metric_change": None,
        "adherence_status": "tracking",
        "evidence_sources": [],
        "confidence": 0.0,
        "explanation": f"正在追蹤中，完成「{action.title}」後將評估實際健康效果。",
        "next_check_in": next_ci,
    }


def _compute_summary(outcome_items: list[dict[str, Any]]) -> dict[str, Any]:
    def _count(status: str) -> int:
        return sum(1 for o in outcome_items if o["outcome_status"] == status)

    return {
        "improved_count": _count("improved"),
        "unchanged_count": _count("unchanged"),
        "deteriorated_count": _count("deteriorated"),
        "insufficient_data_count": _count("insufficient_data"),
        "tracking_count": _count("tracking"),
        "not_useful_count": _count("not_useful"),
        "not_applicable_count": _count("not_applicable"),
        "snoozed_count": _count("snoozed"),
        "total_count": len(outcome_items),
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def compare_expected_vs_actual_outcome(
    db: Session,
    user_id: str,
    person_id: str,
    window_days: int = 7,
) -> dict[str, Any]:
    """Compare expected vs actual health outcomes for completed actions.

    Parameters
    ----------
    window_days : 7 | 14 | 30
        How far back to look for completed actions.

    Guarantees
    ----------
    - "improved" is never returned without hard metric or ActionOutcome evidence.
    - Active (todo/in_progress) actions are shown as "tracking" only.
    - Insufficient metric data is always surfaced explicitly.
    """
    uid = UUID(user_id)
    pid = UUID(person_id)
    now = _now()
    cutoff = now - timedelta(days=window_days)
    metric_cutoff = now - timedelta(days=window_days * 2)

    # Single query per model; Python-side filtering keeps mock simple in tests.
    all_actions: list = db.query(HealthAction).filter(
        HealthAction.user_id == uid,
        HealthAction.person_id == pid,
    ).all()

    completed_actions = [
        a for a in all_actions
        if a.status == "done"
        and a.completed_at is not None
        and _aware(a.completed_at) >= cutoff
    ]
    active_actions = [
        a for a in all_actions
        if a.status in ("todo", "in_progress")
    ]
    dismissed_actions = [
        a for a in all_actions
        if a.status in ("not_useful", "not_applicable")
    ]
    snoozed_actions = [
        a for a in all_actions
        if a.status == "snoozed"
    ]

    all_outcomes: list = db.query(ActionOutcome).filter(
        ActionOutcome.user_id == uid,
        ActionOutcome.person_id == pid,
    ).all()
    outcomes_by_action: dict = {}
    for o in all_outcomes:
        outcomes_by_action.setdefault(o.action_id, []).append(o)

    all_metrics: list = db.query(HealthMetric).filter(
        HealthMetric.user_id == uid,
        HealthMetric.subject_profile_id == pid,
    ).all()
    relevant_metrics = [
        m for m in all_metrics
        if _aware(m.recorded_at) >= metric_cutoff
    ]

    outcome_items: list[dict[str, Any]] = []
    for action in completed_actions:
        outcome_items.append(
            _process_completed_action(
                action, outcomes_by_action, relevant_metrics, now, window_days
            )
        )
    for action in active_actions:
        outcome_items.append(_process_active_action(action, now, window_days))
    for action in dismissed_actions:
        outcome_items.append(_process_dismissed_action(action))
    for action in snoozed_actions:
        outcome_items.append(_process_snoozed_action(action, now))

    return {
        "person_id": person_id,
        "generated_at": now.isoformat(),
        "window_days": window_days,
        "outcomes": outcome_items,
        "summary": _compute_summary(outcome_items),
    }
