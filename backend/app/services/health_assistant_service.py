"""Health Assistant Service
===========================
Builds a unified evidence bundle from all available health data sources
and generates top-3 action recommendations grounded in that evidence.

The evidence bundle is the single input to the recommendation layer —
it must be explicit about missing data so the frontend can show the user
exactly why certain recommendations cannot be made.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.models.entities import (
    ActionOutcome,
    HealthAction,
    HealthInsight,
    HealthMetric,
    LabReport,
    LabReportItem,
    PersonProfile,
    RiskAlert,
    SymptomLog,
    UserProfile,
)
from app.services.device_signal_detection_service import detect_device_signals
from app.services.device_signal_escalation_service import (
    build_device_signal_history,
    evaluate_signal_escalation,
)
from app.services.recommendation_trust_service import recommendation_confidence_score

# ---------------------------------------------------------------------------
# Recency helpers
# ---------------------------------------------------------------------------

_NOW = lambda: datetime.now(timezone.utc)  # noqa: E731


def _recency_label(dt: datetime | None) -> str:
    if dt is None:
        return "unknown"
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    delta = _NOW() - dt
    if delta < timedelta(days=1):
        return "today"
    if delta < timedelta(days=7):
        return "this_week"
    if delta < timedelta(days=30):
        return "this_month"
    return "older"


def _days_ago(dt: datetime | None) -> int | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return (_NOW() - dt).days


def _freshness_label(dt: datetime | None) -> str:
    """Return 'fresh' if recorded within 24 h, 'stale' otherwise."""
    if dt is None:
        return "unknown"
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return "fresh" if (_NOW() - dt).total_seconds() <= 86400 else "stale"


# Source → reliability score for known external providers.
# Any unrecognised source falls back to _DEFAULT_EXTERNAL_RELIABILITY.
_EXTERNAL_RELIABILITY: dict[str, float] = {
    "apple_health": 0.90,
    "google_fit":   0.88,
    "wearable":     0.85,
    "fitbit":       0.85,
    "garmin":       0.85,
    "samsung":      0.85,
    "withings":     0.85,
    "omron":        0.88,
}
_DEFAULT_EXTERNAL_RELIABILITY = 0.80


# ---------------------------------------------------------------------------
# Task 1 — Evidence Bundle
# ---------------------------------------------------------------------------

def build_evidence_bundle(
    db: Session,
    user_id: str,
    person_id: str,
) -> dict[str, Any]:
    """Collect all health evidence for a person into a unified bundle.

    Every evidence item carries:
      source_type  — type of data source
      source_id    — UUID string of the originating row
      recency      — "today" | "this_week" | "this_month" | "older"
      confidence   — float 0–1 (best available)
      evidence_level — "A" | "B" | "C" | None
      summary      — human-readable one-liner

    Missing data is explicit in `missing_data` so callers can surface it.
    """
    uid = UUID(user_id)
    pid = UUID(person_id)

    # ── profile ────────────────────────────────────────────────────────────
    profile_row = (
        db.query(UserProfile).filter(UserProfile.user_id == uid).first()
    )
    person_row = db.query(PersonProfile).filter(PersonProfile.id == pid).first()

    profile_summary: dict[str, Any] | None = None
    if person_row:
        profile_summary = {
            "display_name": person_row.display_name,
            "relationship": person_row.relationship,
            "birth_date": str(person_row.birth_date) if person_row.birth_date else None,
            "gender": person_row.gender,
            "height_cm": float(person_row.height_cm) if person_row.height_cm else None,
            "weight_kg": float(person_row.weight_kg) if person_row.weight_kg else None,
            "chronic_conditions": person_row.chronic_conditions,
            "allergies": person_row.allergies,
            "family_history": person_row.family_history,
        }
    elif profile_row:
        profile_summary = {
            "display_name": None,
            "relationship": "self",
            "birth_date": str(profile_row.birth_date) if profile_row.birth_date else None,
            "gender": profile_row.gender,
            "height_cm": float(profile_row.height_cm) if profile_row.height_cm else None,
            "weight_kg": float(profile_row.weight_kg) if profile_row.weight_kg else None,
            "chronic_conditions": profile_row.chronic_conditions,
            "allergies": profile_row.allergies,
            "family_history": profile_row.family_history,
        }

    # ── symptoms (last 90 days) ────────────────────────────────────────────
    cutoff_90d = _NOW() - timedelta(days=90)
    symptom_rows = (
        db.query(SymptomLog)
        .filter(
            SymptomLog.user_id == uid,
            SymptomLog.subject_profile_id == pid,
            SymptomLog.occurred_at >= cutoff_90d,
        )
        .order_by(desc(SymptomLog.occurred_at))
        .limit(50)
        .all()
    )

    symptoms: list[dict[str, Any]] = []
    long_term_symptoms: list[dict[str, Any]] = []
    for s in symptom_rows:
        item = {
            "source_type": "symptom",
            "source_id": str(s.id),
            "recency": _recency_label(s.occurred_at),
            "confidence": float(s.confidence_score) if s.confidence_score else 0.7,
            "evidence_level": "C",
            "summary": f"{s.symptom}（嚴重度 {s.severity}/10）",
            "symptom": s.symptom,
            "severity": s.severity,
            "occurred_at": s.occurred_at.isoformat() if s.occurred_at else None,
            "estimated_duration_days": s.estimated_duration_days,
        }
        # Long-term: estimated duration > 30 days or older occurrence
        days = _days_ago(s.occurred_at)
        if (s.estimated_duration_days and s.estimated_duration_days > 30) or (days and days > 30):
            long_term_symptoms.append(item)
        else:
            symptoms.append(item)

    # ── health metrics (last 30 days) ──────────────────────────────────────
    cutoff_30d = _NOW() - timedelta(days=30)
    metric_rows = (
        db.query(HealthMetric)
        .filter(
            HealthMetric.user_id == uid,
            HealthMetric.subject_profile_id == pid,
            HealthMetric.recorded_at >= cutoff_30d,
        )
        .order_by(desc(HealthMetric.recorded_at))
        .limit(30)
        .all()
    )

    health_metrics: list[dict[str, Any]] = []
    for m in metric_rows:
        parts = []
        if m.systolic_bp and m.diastolic_bp:
            parts.append(f"血壓 {m.systolic_bp}/{m.diastolic_bp}")
        if m.blood_glucose:
            parts.append(f"血糖 {float(m.blood_glucose):.1f}")
        if m.weight_kg:
            parts.append(f"體重 {float(m.weight_kg):.1f}kg")
        if m.sleep_hours:
            parts.append(f"睡眠 {float(m.sleep_hours):.1f}h")
        if m.steps:
            parts.append(f"步數 {m.steps}")
        health_metrics.append({
            "source_type": "health_metric",
            "source_id": str(m.id),
            "recency": _recency_label(m.recorded_at),
            "confidence": 0.9,
            "evidence_level": "B",
            "summary": "、".join(parts) if parts else "（無數值）",
            "recorded_at": m.recorded_at.isoformat() if m.recorded_at else None,
            "systolic_bp": m.systolic_bp,
            "diastolic_bp": m.diastolic_bp,
            "heart_rate": m.heart_rate,
            "blood_glucose": float(m.blood_glucose) if m.blood_glucose else None,
            "weight_kg": float(m.weight_kg) if m.weight_kg else None,
            "sleep_hours": float(m.sleep_hours) if m.sleep_hours else None,
            "steps": m.steps,
            "source": m.source,
        })

    # ── external metrics (source-tagged, last 30 days) ────────────────────
    # Any HealthMetric row where source != 'manual' is treated as external
    # evidence from a device or third-party integration.
    external_metrics: list[dict[str, Any]] = []
    for m in metric_rows:
        src = (m.source or "manual").strip().lower()
        if src == "manual":
            continue
        parts: list[str] = []
        if m.systolic_bp and m.diastolic_bp:
            parts.append(f"血壓 {m.systolic_bp}/{m.diastolic_bp}")
        if m.blood_glucose:
            parts.append(f"血糖 {float(m.blood_glucose):.1f}")
        if m.weight_kg:
            parts.append(f"體重 {float(m.weight_kg):.1f}kg")
        if m.sleep_hours:
            parts.append(f"睡眠 {float(m.sleep_hours):.1f}h")
        if m.steps:
            parts.append(f"步數 {m.steps}")
        value_summary = "、".join(parts) if parts else "（無數值）"
        reliability = _EXTERNAL_RELIABILITY.get(src, _DEFAULT_EXTERNAL_RELIABILITY)
        external_metrics.append({
            "source":        m.source,
            "timestamp":     m.recorded_at.isoformat() if m.recorded_at else None,
            "freshness":     _freshness_label(m.recorded_at),
            "reliability":   reliability,
            "summary":       f"[{m.source}] {value_summary}",
            # Raw values for device signal detection
            "heart_rate":    m.heart_rate,
            "sleep_hours":   float(m.sleep_hours) if m.sleep_hours else None,
            "steps":         m.steps,
            "systolic_bp":   m.systolic_bp,
            "diastolic_bp":  m.diastolic_bp,
            "blood_glucose": float(m.blood_glucose) if m.blood_glucose else None,
            "weight_kg":     float(m.weight_kg) if m.weight_kg else None,
        })

    # ── lab report items (last 365 days, abnormal only) ────────────────────
    cutoff_1y = _NOW() - timedelta(days=365)
    recent_reports = (
        db.query(LabReport)
        .filter(
            LabReport.user_id == uid,
            LabReport.subject_profile_id == pid,
            LabReport.created_at >= cutoff_1y,
        )
        .order_by(desc(LabReport.created_at))
        .limit(10)
        .all()
    )

    lab_report_items: list[dict[str, Any]] = []
    for report in recent_reports:
        items = (
            db.query(LabReportItem)
            .filter(
                LabReportItem.report_id == report.id,
                LabReportItem.abnormal_flag.isnot(None),
            )
            .all()
        )
        for item in items:
            val_str = (
                f"{float(item.value_num):.2f} {item.unit or ''}"
                if item.value_num is not None
                else (item.value_text or "N/A")
            )
            lab_report_items.append({
                "source_type": "lab_report_item",
                "source_id": str(item.id),
                "report_id": str(report.id),
                "recency": _recency_label(report.created_at),
                "confidence": float(item.parser_confidence) if item.parser_confidence else 0.75,
                "evidence_level": "A",
                "summary": f"{item.item_name} {val_str}（{item.abnormal_flag}）",
                "item_name": item.item_name,
                "item_code": item.item_code,
                "value_num": float(item.value_num) if item.value_num is not None else None,
                "value_text": item.value_text,
                "unit": item.unit,
                "ref_range": item.ref_range,
                "abnormal_flag": item.abnormal_flag,
                "report_date": str(report.report_date) if report.report_date else None,
            })

    # ── risk alerts (active) ───────────────────────────────────────────────
    alert_rows = (
        db.query(RiskAlert)
        .filter(
            RiskAlert.user_id == uid,
            RiskAlert.subject_profile_id == pid,
            RiskAlert.status == "active",
        )
        .order_by(desc(RiskAlert.created_at))
        .limit(20)
        .all()
    )

    risk_alerts: list[dict[str, Any]] = []
    for a in alert_rows:
        risk_alerts.append({
            "source_type": "risk_alert",
            "source_id": str(a.id),
            "recency": _recency_label(a.created_at),
            "confidence": 0.85,
            "evidence_level": "B",
            "title": a.title,
            "summary": a.title,
            "severity": a.severity,
            "risk_type": a.risk_type,
            "rule_code": a.rule_code,
            "message": a.message,
            "recommendation": a.recommendation,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        })

    # ── insights (active, not expired) ────────────────────────────────────
    now = _NOW()
    insight_rows = (
        db.query(HealthInsight)
        .filter(
            HealthInsight.user_id == uid,
            HealthInsight.subject_profile_id == pid,
            HealthInsight.is_active.is_(True),
        )
        .filter(
            (HealthInsight.expires_at.is_(None)) | (HealthInsight.expires_at > now)
        )
        .order_by(desc(HealthInsight.generated_at))
        .limit(10)
        .all()
    )

    insights: list[dict[str, Any]] = []
    for ins in insight_rows:
        insights.append({
            "source_type": "insight",
            "source_id": str(ins.id),
            "recency": _recency_label(ins.generated_at),
            "confidence": 0.8,
            "evidence_level": "B",
            "summary": ins.title,
            "insight_type": ins.insight_type,
            "severity": ins.severity,
            "recommendation": ins.recommendation,
            "generated_at": ins.generated_at.isoformat() if ins.generated_at else None,
        })

    # ── actions (active/todo/in_progress) ─────────────────────────────────
    action_rows = (
        db.query(HealthAction)
        .filter(
            HealthAction.user_id == uid,
            HealthAction.person_id == pid,
            HealthAction.status.in_(["todo", "in_progress", "snoozed"]),
        )
        .order_by(desc(HealthAction.created_at))
        .all()
    )

    actions: list[dict[str, Any]] = []
    for act in action_rows:
        actions.append({
            "source_type": "action",
            "source_id": str(act.id),
            "recency": _recency_label(act.created_at),
            "confidence": float(act.confidence) if act.confidence else 0.7,
            "evidence_level": act.evidence_level,
            "summary": act.title,
            "status": act.status,
            "priority": act.priority,
            "category": act.category,
            "action_type": act.action_type,
            "source_type_origin": act.source_type,
            "snooze_count": act.resurface_count,
            "streak_count": act.streak_count,
            "due_date": act.due_date.isoformat() if act.due_date else None,
            "snoozed_until": act.snoozed_until.isoformat() if act.snoozed_until else None,
            "rule_id": act.rule_id,
        })

    # ── completed actions (last 30 days) ───────────────────────────────────
    completed_rows = (
        db.query(HealthAction)
        .filter(
            HealthAction.user_id == uid,
            HealthAction.person_id == pid,
            HealthAction.status == "done",
            HealthAction.completed_at >= cutoff_30d,
        )
        .order_by(desc(HealthAction.completed_at))
        .limit(20)
        .all()
    )

    completed_actions: list[dict[str, Any]] = []
    completed_rule_ids: set[str] = set()
    for act in completed_rows:
        if act.rule_id:
            completed_rule_ids.add(act.rule_id)
        completed_actions.append({
            "source_type": "completed_action",
            "source_id": str(act.id),
            "recency": _recency_label(act.completed_at),
            "confidence": float(act.confidence) if act.confidence else 0.7,
            "evidence_level": act.evidence_level,
            "summary": f"已完成：{act.title}",
            "title": act.title,
            "category": act.category,
            "completed_at": act.completed_at.isoformat() if act.completed_at else None,
            "rule_id": act.rule_id,
            "streak_count": act.streak_count,
        })

    # ── outcomes (last 30 days) ────────────────────────────────────────────
    completed_ids = [UUID(a["source_id"]) for a in completed_actions]
    outcomes: list[dict[str, Any]] = []
    if completed_ids:
        outcome_rows = (
            db.query(ActionOutcome)
            .filter(ActionOutcome.action_id.in_(completed_ids))
            .order_by(desc(ActionOutcome.computed_at))
            .limit(30)
            .all()
        )
        for o in outcome_rows:
            outcomes.append({
                "source_type": "outcome",
                "source_id": str(o.id),
                "action_id": str(o.action_id),
                "recency": _recency_label(o.computed_at),
                "confidence": 0.85,
                "evidence_level": "B",
                "summary": f"{o.metric_type} {o.outcome_label} ({o.time_window_days}天)",
                "metric_type": o.metric_type,
                "before_value": float(o.before_value) if o.before_value is not None else None,
                "after_value": float(o.after_value) if o.after_value is not None else None,
                "delta": float(o.delta) if o.delta is not None else None,
                "outcome_label": o.outcome_label,
                "time_window_days": o.time_window_days,
            })

    # ── missing data flags ─────────────────────────────────────────────────
    missing_data: list[str] = []
    if not symptom_rows:
        missing_data.append("症狀記錄")
    if not metric_rows:
        missing_data.append("健康指標（血壓、血糖、體重等）")
    if not lab_report_items:
        missing_data.append("健檢報告（或無異常項目）")
    if not risk_alerts:
        missing_data.append("風險警示（目前無主動警示）")
    if not insights:
        missing_data.append("健康洞察（建議先執行健康分析）")
    if profile_summary is None:
        missing_data.append("個人健康檔案")

    # ── device signals (derived from external_metrics) ─────────────────────
    device_signals: list[dict[str, Any]] = detect_device_signals(external_metrics)

    # ── signal trend history + escalation ─────────────────────────────────
    _all_symptoms = symptoms + long_term_symptoms
    signal_history: dict[str, Any] = build_device_signal_history(external_metrics)
    device_escalation: dict[str, Any] = evaluate_signal_escalation(
        device_signals, signal_history, _all_symptoms, outcomes,
    )

    # ── bundle ─────────────────────────────────────────────────────────────
    return {
        "person_id": person_id,
        "generated_at": _NOW().isoformat(),
        "profile": profile_summary,
        "symptoms": symptoms,
        "long_term_symptoms": long_term_symptoms,
        "health_metrics": health_metrics,
        "external_metrics": external_metrics,
        "device_signals": device_signals,
        "device_signal_history": signal_history,
        "device_escalation": device_escalation,
        "lab_report_items": lab_report_items,
        "risk_alerts": risk_alerts,
        "insights": insights,
        "actions": actions,
        "completed_actions": completed_actions,
        "outcomes": outcomes,
        "missing_data": missing_data,
        "_completed_rule_ids": list(completed_rule_ids),
        "summary": {
            "symptom_count": len(symptoms) + len(long_term_symptoms),
            "metric_count": len(metric_rows),
            "abnormal_lab_count": len(lab_report_items),
            "active_alert_count": len(risk_alerts),
            "insight_count": len(insights),
            "active_action_count": len(actions),
            "completed_action_count": len(completed_actions),
            "outcome_count": len(outcomes),
            "missing_data_count": len(missing_data),
        },
    }


# ---------------------------------------------------------------------------
# Task 2 — Action Recommendations
# ---------------------------------------------------------------------------

# Priority score mapping for sources
_SOURCE_PRIORITY: dict[str, int] = {
    "risk_alert": 100,
    "lab_report_item": 80,
    "device_signal": 70,
    "insight": 60,
    "symptom": 50,
    "health_metric": 40,
    "long_term_symptom": 45,
}

_SEVERITY_SCORE: dict[str, int] = {
    "critical": 40,
    "high": 30,
    "warning": 20,
    "medium": 10,
    "info": 5,
    "low": 2,
}


def get_action_recommendations(
    db: Session,
    user_id: str,
    person_id: str,
    decision_items: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Generate Top-3 health action recommendations.

    Logic:
    1. Build the evidence bundle.
    2. Score each active risk alert / insight / lab abnormality.
    3. For each candidate, check if an active/snoozed action already covers it
       → mark as 'tracking', suppress duplicate.
    4. Check if a completed action covers it recently
       → suppress unless recurrence applies (resurface_count > 0).
    5. User-created actions always remain visible.
    6. Return top-3 ranked recommendations.
    """
    bundle = build_evidence_bundle(db, user_id, person_id)
    completed_rule_ids: set[str] = set(bundle.get("_completed_rule_ids", []))

    # Build lookup: rule_id / source_id → active action
    active_action_by_rule: dict[str, dict] = {}
    active_action_by_source: dict[str, dict] = {}
    for act in bundle["actions"]:
        if act.get("rule_id"):
            active_action_by_rule[act["rule_id"]] = act
        active_action_by_source[act["source_id"]] = act

    # ── Candidate generation ────────────────────────────────────────────────
    candidates: list[dict[str, Any]] = []

    # From risk alerts
    for alert in bundle["risk_alerts"]:
        score = _SOURCE_PRIORITY["risk_alert"] + _SEVERITY_SCORE.get(alert.get("severity", "info"), 5)
        candidates.append({
            "_score": score,
            "_source": alert,
            "_source_type": "risk_alert",
            "rule_id": alert.get("rule_code"),
        })

    # From lab abnormalities
    for lab in bundle["lab_report_items"]:
        score = _SOURCE_PRIORITY["lab_report_item"]
        if lab.get("recency") in ("today", "this_week"):
            score += 20
        elif lab.get("recency") == "this_month":
            score += 10
        candidates.append({
            "_score": score,
            "_source": lab,
            "_source_type": "lab_report_item",
            "rule_id": f"lab_{lab.get('item_code') or lab.get('item_name', '')}",
        })

    # From active insights (high/warning severity)
    for ins in bundle["insights"]:
        if ins.get("severity") in ("high", "warning", "critical"):
            score = _SOURCE_PRIORITY["insight"] + _SEVERITY_SCORE.get(ins.get("severity", "info"), 5)
            candidates.append({
                "_score": score,
                "_source": ins,
                "_source_type": "insight",
                "rule_id": None,
            })

    # From long-term symptoms (persistent, high severity)
    for sym in bundle["long_term_symptoms"]:
        if sym.get("severity", 0) >= 6:
            score = _SOURCE_PRIORITY["long_term_symptom"] + sym.get("severity", 0) * 2
            candidates.append({
                "_score": score,
                "_source": sym,
                "_source_type": "long_term_symptom",
                "rule_id": None,
            })

    # From device signals (medium/high severity only)
    for sig in bundle.get("device_signals", []):
        if sig.get("severity") in ("medium", "high"):
            sev = sig.get("severity", "medium")
            score = _SOURCE_PRIORITY["device_signal"] + _SEVERITY_SCORE.get(sev, 10)
            candidates.append({
                "_score":      score,
                "_source":     sig,
                "_source_type": "device_signal",
                "rule_id":     f"device_{sig.get('signal_type', '')}",
            })

    # From decision_items if provided (backend authoritative)
    if decision_items:
        for di in decision_items[:5]:
            score = _SEVERITY_SCORE.get(di.get("priority", "medium"), 10) + 30
            candidates.append({
                "_score": score,
                "_source": di,
                "_source_type": "decision_item",
                "rule_id": di.get("rule_id"),
            })

    # Sort by score descending
    candidates.sort(key=lambda c: c["_score"], reverse=True)

    # ── Deduplication and suppression ──────────────────────────────────────
    recommendations: list[dict[str, Any]] = []
    seen_rule_ids: set[str] = set()

    for cand in candidates:
        if len(recommendations) >= 3:
            break

        src = cand["_source"]
        src_type = cand["_source_type"]
        rule_id = cand.get("rule_id") or ""
        source_id = src.get("source_id", "")

        # Skip duplicate rule_ids
        if rule_id and rule_id in seen_rule_ids:
            continue

        # Check if active action already tracks this
        tracking_action = active_action_by_rule.get(rule_id) or active_action_by_source.get(source_id)
        suppression_reason: str | None = None

        if tracking_action:
            if tracking_action["status"] == "snoozed":
                suppression_reason = "已暫緩（使用者已設定稍後提醒）"
            # Active tracking — still surface it but mark as tracking
            is_tracking = True
        else:
            is_tracking = False

        # Check if recently completed action covers this and no recurrence
        if rule_id and rule_id in completed_rule_ids:
            if not tracking_action or tracking_action.get("snooze_count", 0) == 0:
                suppression_reason = "近期已完成，無需重複建議"
                # Don't add to recommendations
                continue

        # Build the recommendation
        rec = _build_recommendation_from_candidate(
            cand, tracking_action, is_tracking, suppression_reason, bundle
        )
        recommendations.append(rec)
        if rule_id:
            seen_rule_ids.add(rule_id)

    # Pad with generic recommendations if < 3
    if len(recommendations) < 3:
        recommendations.extend(_build_fallback_recommendations(
            bundle, seen_rule_ids, 3 - len(recommendations)
        ))

    final_recs = recommendations[:3]
    for rec in final_recs:
        rec["trust"] = recommendation_confidence_score(rec, bundle, bundle["outcomes"])

    return {
        "person_id": person_id,
        "generated_at": _NOW().isoformat(),
        "recommendations": final_recs,
        "device_signals": bundle.get("device_signals", []),
        "device_escalation": bundle.get("device_escalation", {}),
        "evidence_bundle_summary": bundle["summary"],
        "missing_data": bundle["missing_data"],
    }


def _build_recommendation_from_candidate(
    cand: dict[str, Any],
    tracking_action: dict | None,
    is_tracking: bool,
    suppression_reason: str | None,
    bundle: dict[str, Any],
) -> dict[str, Any]:
    src = cand["_source"]
    src_type = cand["_source_type"]

    if src_type == "risk_alert":
        title = src.get("title", "健康風險需關注")
        why_now = f"目前有主動風險警示：{src.get('message', '')}，嚴重度 {src.get('severity', '未知')}"
        impact = src.get("recommendation") or "降低健康風險，防止病況惡化"
        next_action = src.get("recommendation") or "請查看完整風險說明"
        priority = _map_severity_to_priority(src.get("severity", "medium"))
        evidence = [{"type": "risk_alert", "id": src.get("source_id"), "summary": src.get("summary", title)}]

    elif src_type == "lab_report_item":
        title = f"異常檢驗項目需追蹤：{src.get('item_name', '')}"
        why_now = (
            f"健檢報告顯示 {src.get('item_name')} = {src.get('value_num') or src.get('value_text')} "
            f"（{src.get('abnormal_flag', '異常')}），"
            f"報告日期 {src.get('report_date', '最近')}"
        )
        impact = "及早追蹤異常指標，避免演變為慢性疾病風險"
        next_action = f"與醫師討論 {src.get('item_name')} 異常並安排複查"
        priority = "high" if src.get("recency") in ("today", "this_week") else "medium"
        evidence = [{"type": "lab_report_item", "id": src.get("source_id"), "summary": src.get("summary", title)}]

    elif src_type == "insight":
        title = src.get("title", "健康洞察需注意")
        why_now = f"系統偵測到健康洞察：{src.get('summary', '')}，嚴重度 {src.get('severity', '未知')}"
        impact = src.get("recommendation") or "改善健康狀態，提升整體健康評分"
        next_action = src.get("recommendation") or "依據洞察採取對應行動"
        priority = _map_severity_to_priority(src.get("severity", "info"))
        evidence = [{"type": "insight", "id": src.get("source_id"), "summary": src.get("summary", title)}]

    elif src_type == "long_term_symptom":
        title = f"持續症狀需關注：{src.get('symptom', '')}"
        why_now = (
            f"症狀 {src.get('symptom')} 已持續估計 {src.get('estimated_duration_days', '多')} 天，"
            f"嚴重度 {src.get('severity', 0)}/10"
        )
        impact = "長期症狀若不處理可能發展為慢性問題"
        next_action = "就醫評估持續症狀的原因"
        priority = "high" if (src.get("severity") or 0) >= 8 else "medium"
        evidence = [{"type": "symptom", "id": src.get("source_id"), "summary": src.get("summary", title)}]

    elif src_type == "device_signal":
        signal_type = src.get("signal_type", "device_signal")
        current_val = src.get("current_value")
        metric_type = src.get("metric_type", "")
        title = f"裝置訊號異常：{signal_type.replace('_', ' ')}"
        why_now = src.get("why_detected", "裝置偵測到健康指標異常")
        if current_val is not None:
            why_now = f"{why_now}（當前值：{current_val}）"
        impact = src.get("suggested_action") or "及早關注裝置偵測的健康訊號，避免惡化"
        next_action = src.get("suggested_action") or "查看裝置健康訊號詳情"
        priority = _map_severity_to_priority(src.get("severity", "medium"))
        evidence = [{"type": "device_signal", "id": signal_type, "summary": src.get("why_detected", title)}]

    elif src_type == "decision_item":
        title = src.get("title", "健康優先事項")
        why_now = src.get("reason") or "系統健康決策引擎優先推薦"
        impact = src.get("recommendation") or "改善關鍵健康指標"
        next_action = src.get("recommendation") or "執行此健康行動"
        priority = src.get("priority", "medium")
        evidence = [{"type": "decision_item", "id": src.get("id"), "summary": src.get("summary", title)}]

    else:
        title = "健康建議"
        why_now = "基於目前可用的健康資料"
        impact = "改善整體健康狀態"
        next_action = "查看詳細健康資料"
        priority = "low"
        evidence = []

    # Enrich evidence with related health metrics
    if bundle.get("health_metrics"):
        latest_metric = bundle["health_metrics"][0]
        evidence.append({
            "type": "health_metric",
            "id": latest_metric.get("source_id"),
            "summary": latest_metric.get("summary", "最新健康指標"),
        })

    return {
        "title": title,
        "why_now": why_now,
        "priority": priority,
        "related_decision_item": src.get("id") if src_type == "decision_item" else None,
        "expected_health_impact": impact,
        "evidence_sources": evidence,
        "next_action": next_action,
        "is_tracking": is_tracking,
        "tracking_action_id": tracking_action["source_id"] if tracking_action else None,
        "suppression_reason": suppression_reason,
        "source_type": src_type,
        "source_id": src.get("source_id"),
    }


def _build_fallback_recommendations(
    bundle: dict[str, Any],
    seen_rule_ids: set[str],
    count: int,
) -> list[dict[str, Any]]:
    """Fallback recommendations when evidence is sparse."""
    fallbacks = []
    missing = bundle.get("missing_data", [])

    if "健康指標（血壓、血糖、體重等）" in missing and len(fallbacks) < count:
        fallbacks.append({
            "title": "記錄今日健康指標",
            "why_now": "目前沒有近期健康指標記錄，無法進行精準健康評估",
            "priority": "medium",
            "related_decision_item": None,
            "expected_health_impact": "提供健康指標後，系統可產生個人化建議",
            "evidence_sources": [],
            "next_action": "前往記錄血壓、血糖或體重",
            "is_tracking": False,
            "tracking_action_id": None,
            "suppression_reason": None,
            "source_type": "missing_data",
            "source_id": None,
        })

    if "症狀記錄" in missing and len(fallbacks) < count:
        fallbacks.append({
            "title": "記錄近期症狀",
            "why_now": "目前沒有症狀記錄，建議記錄身體狀況以利追蹤",
            "priority": "low",
            "related_decision_item": None,
            "expected_health_impact": "症狀記錄有助於偵測潛在健康問題",
            "evidence_sources": [],
            "next_action": "前往症狀記錄頁面",
            "is_tracking": False,
            "tracking_action_id": None,
            "suppression_reason": None,
            "source_type": "missing_data",
            "source_id": None,
        })

    if "健檢報告（或無異常項目）" in missing and len(fallbacks) < count:
        fallbacks.append({
            "title": "上傳健檢報告",
            "why_now": "缺少健檢報告資料，系統無法評估血液指標異常",
            "priority": "low",
            "related_decision_item": None,
            "expected_health_impact": "健檢報告可提供血液指標的客觀依據",
            "evidence_sources": [],
            "next_action": "前往文件頁面上傳健檢報告",
            "is_tracking": False,
            "tracking_action_id": None,
            "suppression_reason": None,
            "source_type": "missing_data",
            "source_id": None,
        })

    return fallbacks[:count]


def _map_severity_to_priority(severity: str) -> str:
    mapping = {"critical": "high", "high": "high", "warning": "high",
               "medium": "medium", "info": "low", "low": "low"}
    return mapping.get(severity, "medium")


# ---------------------------------------------------------------------------
# Task 4 — Product Signal computation from main DB
# ---------------------------------------------------------------------------

def build_product_signals(
    db: Session,
    user_id: str,
    person_id: str,
    days: int = 30,
) -> dict[str, Any]:
    """Compute real product engagement signals from the main PostgreSQL database.

    Returns a dict of signal_name → value for use by detect_product_issues().
    """
    uid = UUID(user_id)
    pid = UUID(person_id)
    cutoff = _NOW() - timedelta(days=days)

    # action completion rate
    all_actions = (
        db.query(HealthAction)
        .filter(
            HealthAction.user_id == uid,
            HealthAction.person_id == pid,
            HealthAction.created_at >= cutoff,
        )
        .all()
    )
    total = len(all_actions)
    done = sum(1 for a in all_actions if a.status == "done")
    completion_rate = done / total if total > 0 else None

    # snooze count
    snooze_count = sum(a.resurface_count or 0 for a in all_actions)
    snoozed_actions = [a for a in all_actions if a.status == "snoozed"]
    snooze_rate = len(snoozed_actions) / total if total > 0 else None

    # insight-to-action conversion: actions sourced from insights / total insights
    insight_sourced_actions = sum(1 for a in all_actions if a.source_type == "insight")
    insight_count = (
        db.query(HealthInsight)
        .filter(
            HealthInsight.user_id == uid,
            HealthInsight.subject_profile_id == pid,
            HealthInsight.generated_at >= cutoff,
        )
        .count()
    )
    insight_action_conversion = (
        insight_sourced_actions / insight_count if insight_count > 0 else None
    )

    # document-to-action conversion: actions sourced from reports / total reports
    report_sourced_actions = sum(1 for a in all_actions if a.source_type in ("report", "lab_report"))
    report_count = (
        db.query(LabReport)
        .filter(
            LabReport.user_id == uid,
            LabReport.subject_profile_id == pid,
            LabReport.created_at >= cutoff,
        )
        .count()
    )
    doc_action_conversion = (
        report_sourced_actions / report_count if report_count > 0 else None
    )

    # outcome improvement rate
    improved_outcomes = (
        db.query(ActionOutcome)
        .filter(
            ActionOutcome.user_id == uid,
            ActionOutcome.person_id == pid,
            ActionOutcome.outcome_label == "improved",
            ActionOutcome.computed_at >= cutoff,
        )
        .count()
    )
    total_outcomes = (
        db.query(ActionOutcome)
        .filter(
            ActionOutcome.user_id == uid,
            ActionOutcome.person_id == pid,
            ActionOutcome.computed_at >= cutoff,
        )
        .count()
    )
    outcome_improvement_rate = (
        improved_outcomes / total_outcomes if total_outcomes > 0 else None
    )

    return {
        "period_days": days,
        "total_actions": total,
        "completed_actions": done,
        "completion_rate": round(completion_rate, 3) if completion_rate is not None else None,
        "snooze_count": snooze_count,
        "snooze_rate": round(snooze_rate, 3) if snooze_rate is not None else None,
        "insight_action_conversion": (
            round(insight_action_conversion, 3) if insight_action_conversion is not None else None
        ),
        "doc_action_conversion": (
            round(doc_action_conversion, 3) if doc_action_conversion is not None else None
        ),
        "outcome_improvement_rate": (
            round(outcome_improvement_rate, 3) if outcome_improvement_rate is not None else None
        ),
        "insight_count": insight_count,
        "report_count": report_count,
        "total_outcomes": total_outcomes,
        "improved_outcomes": improved_outcomes,
    }


# ---------------------------------------------------------------------------
# Task 5 (P1) — Daily Health Summary
# ---------------------------------------------------------------------------

# Severity ordering used by _derive_top_risk
_SEVERITY_ORDER: dict[str, int] = {
    "critical": 5, "high": 4, "warning": 3, "medium": 2, "low": 1, "info": 0,
}

# Human-readable metric names for change descriptions
_METRIC_LABEL: dict[str, str] = {
    "systolic_bp": "收縮壓",
    "diastolic_bp": "舒張壓",
    "blood_glucose": "血糖",
    "weight_kg": "體重",
    "heart_rate": "心率",
    "sleep_hours": "睡眠",
    "steps": "步數",
}


def generate_daily_health_summary(
    db: Session,
    user_id: str,
    person_id: str,
) -> dict[str, Any]:
    """Generate the daily health summary narrative card.

    Pulls from the existing evidence bundle + recommendations layer so that
    all derivation is deterministic and testable without LLM calls.

    Outputs (snake_case keys reflect camelCase TypeScript type):
      topRisk         — most pressing risk or concern today
      biggestChange   — largest measurable health change recently
      todayAction     — single most important action to take today
      whyNow          — reason this action matters right now
      confidence      — float 0.0–1.0, reflects evidence completeness
      missingData     — list of missing categories (absent when empty)
      encouragement   — positive reinforcement string (absent when no trigger)
    """
    bundle = build_evidence_bundle(db, user_id, person_id)
    rec_result = get_action_recommendations(db, user_id, person_id)

    recommendations: list[dict[str, Any]] = rec_result.get("recommendations", [])
    missing_data: list[str] = bundle.get("missing_data", [])
    risk_alerts: list[dict[str, Any]] = bundle.get("risk_alerts", [])
    outcomes: list[dict[str, Any]] = bundle.get("outcomes", [])
    health_metrics: list[dict[str, Any]] = bundle.get("health_metrics", [])
    actions: list[dict[str, Any]] = bundle.get("actions", [])
    completed_actions: list[dict[str, Any]] = bundle.get("completed_actions", [])
    long_term_symptoms: list[dict[str, Any]] = bundle.get("long_term_symptoms", [])
    bundle_summary: dict[str, Any] = bundle.get("summary", {})
    device_escalation: dict[str, Any] = bundle.get("device_escalation", {})

    top_risk = _derive_top_risk(
        risk_alerts, recommendations, long_term_symptoms, missing_data,
        escalation=device_escalation,
    )
    biggest_change = _derive_biggest_change(outcomes, health_metrics)
    today_action, why_now = _derive_today_action_and_why(
        recommendations, escalation=device_escalation,
    )
    confidence = _compute_confidence(bundle_summary, missing_data)
    encouragement = _derive_encouragement(actions, completed_actions, outcomes)

    result: dict[str, Any] = {
        "person_id": person_id,
        "generated_at": _NOW().isoformat(),
        "topRisk": top_risk,
        "biggestChange": biggest_change,
        "todayAction": today_action,
        "whyNow": why_now,
        "confidence": confidence,
    }
    if missing_data:
        result["missingData"] = missing_data
    if encouragement:
        result["encouragement"] = encouragement
    if device_escalation and device_escalation.get("escalationLevel") not in (None, "none"):
        result["escalation"] = device_escalation
    return result


# ── Private helpers ─────────────────────────────────────────────────────────

def _derive_top_risk(
    risk_alerts: list[dict[str, Any]],
    recommendations: list[dict[str, Any]],
    long_term_symptoms: list[dict[str, Any]],
    missing_data: list[str],
    escalation: dict[str, Any] | None = None,
) -> str:
    """Pick the single most urgent risk description."""
    if risk_alerts:
        best = max(
            risk_alerts,
            key=lambda a: _SEVERITY_ORDER.get(a.get("severity", "info"), 0),
        )
        sev_label = {
            "critical": "嚴重", "high": "高風險", "warning": "警示",
        }.get(best.get("severity", ""), best.get("severity", ""))
        return f"{best.get('title', '健康風險')}（{sev_label}）"

    # No explicit risk alert — check device escalation
    if escalation:
        esc_level = escalation.get("escalationLevel", "none")
        esc_reasons = escalation.get("reasons", [])
        if esc_level == "urgent" and esc_reasons:
            return f"裝置健康訊號緊急：{esc_reasons[0]}"
        if esc_level == "warning" and esc_reasons:
            return f"裝置健康訊號警示：{esc_reasons[0]}"

    for rec in recommendations:
        if rec.get("priority") == "high" and rec.get("source_type") not in ("missing_data", None):
            return rec.get("title", "健康問題需關注")

    for sym in long_term_symptoms:
        if (sym.get("severity") or 0) >= 6:
            return f"持續症狀需關注：{sym.get('symptom', '')}（已追蹤中）"

    for rec in recommendations:
        if rec.get("source_type") not in ("missing_data", None):
            return rec.get("title", "建議主動追蹤健康狀況")

    if len(missing_data) >= 3:
        return "資料不足，建議補充健康資料以完整評估風險"

    return "目前未偵測到顯著風險"


def _derive_biggest_change(
    outcomes: list[dict[str, Any]],
    health_metrics: list[dict[str, Any]],
) -> str:
    """Return a one-liner describing the largest measurable health change."""
    if outcomes:
        best = max(outcomes, key=lambda o: abs(o.get("delta") or 0))
        delta = best.get("delta") or 0
        if delta != 0:
            metric = best.get("metric_type", "")
            label = _METRIC_LABEL.get(metric, metric or "健康指標")
            # For metrics where lower is better (BP, glucose) negative delta is improvement
            lower_is_better = metric in ("systolic_bp", "diastolic_bp", "blood_glucose")
            if lower_is_better:
                direction = "改善" if delta < 0 else "上升"
            else:
                direction = "上升" if delta > 0 else "下降"
            window = best.get("time_window_days", "")
            outcome_tag = best.get("outcome_label", "")
            suffix = f"（{outcome_tag}，{window}天）" if outcome_tag and window else ""
            return f"{label}{direction} {abs(delta):.1f}{suffix}"

    # Derive trend from raw metric readings (ordered newest → oldest)
    for extractor, label, lower_is_better, threshold, unit in [
        (lambda m: m.get("systolic_bp"), "收縮壓", True, 5.0, "mmHg"),
        (lambda m: m.get("blood_glucose"), "血糖", True, 0.5, ""),
        (lambda m: m.get("weight_kg"), "體重", False, 0.5, "kg"),
        (lambda m: m.get("sleep_hours"), "睡眠時數", False, 0.5, "h"),
    ]:
        values = [extractor(m) for m in health_metrics if extractor(m) is not None]
        if len(values) >= 2:
            delta = float(values[0]) - float(values[-1])  # newest - oldest
            if abs(delta) >= threshold:
                if lower_is_better:
                    direction = "改善" if delta < 0 else "上升"
                else:
                    direction = "上升" if delta > 0 else "下降"
                return f"{label}{direction} {abs(delta):.1f}{unit}（近期趨勢）"

    return "近期無明顯數據變化"


def _derive_today_action_and_why(
    recommendations: list[dict[str, Any]],
    escalation: dict[str, Any] | None = None,
) -> tuple[str, str]:
    """Return (todayAction, whyNow) from the top available recommendation."""
    # Urgent escalation overrides fallback but never overrides explicit recs
    if escalation and escalation.get("escalationLevel") == "urgent":
        urgent_action = escalation.get("recommendedAction")
        if urgent_action:
            # Only use escalation action if no explicit actionable rec exists
            has_actionable = any(
                not r.get("is_tracking") and r.get("source_type") not in ("missing_data",)
                for r in recommendations
            )
            if not has_actionable:
                reasons = escalation.get("reasons", [])
                why = reasons[0] if reasons else "裝置訊號顯示健康異常需監測"
                return urgent_action, why
    default_action = "記錄今日健康狀況"
    default_why = "建立每日健康追蹤習慣，讓系統更了解您的健康趨勢"

    # Prefer actionable (non-tracking, non-missing_data) recs
    for rec in recommendations:
        if not rec.get("is_tracking") and rec.get("source_type") not in ("missing_data",):
            return rec.get("title", default_action), rec.get("why_now", default_why)

    # Accept tracking recs (still meaningful — user is already on it)
    for rec in recommendations:
        if rec.get("source_type") not in ("missing_data",):
            return rec.get("title", default_action), rec.get("why_now", default_why)

    # Fallback to first (may be missing_data type)
    if recommendations:
        return recommendations[0].get("title", default_action), recommendations[0].get("why_now", default_why)

    return default_action, default_why


def _compute_confidence(
    summary: dict[str, Any],
    missing_data: list[str],
) -> float:
    """Compute evidence confidence 0.20–0.95 from data completeness."""
    score = 0.0
    if summary.get("symptom_count", 0) > 0:
        score += 0.15
    if summary.get("metric_count", 0) > 0:
        score += 0.20
    if summary.get("abnormal_lab_count", 0) > 0:
        score += 0.20
    if summary.get("insight_count", 0) > 0:
        score += 0.15
    if summary.get("active_alert_count", 0) > 0:
        score += 0.15
    if summary.get("outcome_count", 0) > 0:
        score += 0.10
    if "個人健康檔案" not in missing_data:
        score += 0.05
    return round(min(max(score, 0.20), 0.95), 2)


def _derive_encouragement(
    actions: list[dict[str, Any]],
    completed_actions: list[dict[str, Any]],
    outcomes: list[dict[str, Any]],
) -> str | None:
    """Return a positive reinforcement string, or None if no trigger applies."""
    best_streak = max((a.get("streak_count") or 0 for a in actions), default=0)
    if best_streak >= 7:
        return f"連續 {best_streak} 天保持健康習慣，表現非常亮眼！繼續維持！"
    if best_streak >= 3:
        return f"已連續 {best_streak} 天執行健康計畫，習慣正在建立中！"

    positive = [
        o for o in outcomes
        if o.get("outcome_label") in ("improved", "positive")
    ]
    if positive:
        metric = positive[0].get("metric_type", "")
        label = _METRIC_LABEL.get(metric, "健康指標")
        return f"你的努力正在發揮效果：{label} 已有改善！繼續保持！"

    count = len(completed_actions)
    if count >= 5:
        return f"本月已完成 {count} 項健康行動，每一步都讓身體更健康！"
    if count >= 1:
        title = completed_actions[0].get("title", "健康行動")
        return f"你已完成了「{title}」，繼續保持！"

    if not actions and not completed_actions:
        return "每天記錄一件健康小事，讓系統更了解你的身體。"

    return None
