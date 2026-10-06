"""Narrative Memory Service — P7 Long-Term Health Context
===========================================================
Builds, persists, and retrieves per-person long-term health narrative
memories over daily / weekly / monthly windows.

Anti-hallucination rules
-------------------------
- improving / worsening items are ONLY emitted when evidence explicitly
  shows directional change (outcome_label OR measured delta).
- repeated risks require ≥ 2 distinct occurrences within the period.
- effective actions require acted notification OR improved outcome.
- ignored items require ignore_count > 0 in notification history.
- If evidence is insufficient the limitations list explains why.
- summary_text never contains medical diagnoses or speculative wording.

Public API
----------
build_narrative_memory()       — pure computation from evidence inputs
persist_narrative_memory()     — upsert record to DB
load_narrative_memory()        — load most-recent record(s) from DB
compare_narrative_periods()    — diff two periods' narrative dicts
"""
from __future__ import annotations

import uuid as _uuid
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
from typing import Any

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.models.entities import (
    ActionOutcome,
    HealthAction,
    NarrativeMemory,
    NotificationLog,
    RiskAlert,
)

# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

NarrativeMemoryResult = dict[str, Any]
"""
{
  periodType: "daily" | "weekly" | "monthly"
  periodStart: str  (ISO date)
  periodEnd: str    (ISO date)
  summaryText: str
  topThemes: list[str]
  improvingItems: list[str]
  worseningItems: list[str]
  repeatedRisks: list[str]
  effectiveActions: list[str]
  ignoredItems: list[str]
  confidence: float
  limitations: list[str]
}
"""

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_MIN_REPEATED_RISK_COUNT = 2  # occurrences needed to call something "repeated"
_MIN_EVIDENCE_FOR_CONFIDENCE = 3  # evidence items needed for non-trivial confidence

_PERIOD_DAYS: dict[str, int] = {
    "daily": 1,
    "weekly": 7,
    "monthly": 30,
}

_SOURCE_TYPE_LABELS: dict[str, str] = {
    "lab_abnormality": "健檢指標異常",
    "device_escalation": "裝置訊號異常",
    "symptom_pattern": "症狀模式",
    "risk_alert": "健康風險警示",
    "recommendation": "健康建議",
    "unknown": "其他提醒",
}

_OUTCOME_LABELS: dict[str, str] = {
    "improved": "已改善",
    "worsened": "持續惡化",
    "no_change": "無明顯變化",
    "insufficient_data": "資料不足",
}

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _to_uuid(val: str | _uuid.UUID) -> _uuid.UUID:
    return val if isinstance(val, _uuid.UUID) else _uuid.UUID(str(val))


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


def _source_label(key: str) -> str:
    return _SOURCE_TYPE_LABELS.get(key, key)


def _period_window(period_type: str, reference_date: date | None = None) -> tuple[date, date]:
    """Return (period_start, period_end) for the given period_type ending today."""
    today = reference_date or date.today()
    days = _PERIOD_DAYS.get(period_type, 7)
    return today - timedelta(days=days - 1), today


# ---------------------------------------------------------------------------
# Core builder — pure function, no DB access
# ---------------------------------------------------------------------------

def build_narrative_memory(
    period_type: str,
    notification_history: list[dict[str, Any]],
    risk_alerts: list[Any],             # RiskAlert ORM rows or dicts
    completed_actions: list[Any],       # HealthAction ORM rows
    action_outcomes: list[Any],         # ActionOutcome ORM rows
    period_start: date | None = None,
    period_end: date | None = None,
) -> NarrativeMemoryResult:
    """Build a NarrativeMemoryResult from evidence inputs.

    All inputs are optional — missing data results in limitations, not errors.
    """
    p_start, p_end = _period_window(period_type, period_end)
    if period_start is not None:
        p_start = period_start
    if period_end is not None:
        p_end = period_end

    limitations: list[str] = []
    evidence_count = 0

    # ── Top themes ──────────────────────────────────────────────────────────
    theme_counter: Counter[str] = Counter()
    for entry in notification_history:
        src = entry.get("source_type", "unknown")
        theme_counter[src] += 1
        evidence_count += 1

    for alert in risk_alerts:
        src = getattr(alert, "source_type", None) or (alert.get("source_type") if isinstance(alert, dict) else "risk_alert")
        theme_counter[src or "risk_alert"] += 1
        evidence_count += 1

    top_themes = [_source_label(k) for k, _ in theme_counter.most_common(3)]

    if not top_themes:
        limitations.append("本期間沒有足夠的提醒記錄來識別健康主題。")

    # ── Improving / Worsening items (from action outcomes only) ─────────────
    improving_items: list[str] = []
    worsening_items: list[str] = []

    for outcome in action_outcomes:
        label = getattr(outcome, "outcome_label", None) or (
            outcome.get("outcome_label") if isinstance(outcome, dict) else None
        )
        metric = getattr(outcome, "metric_type", None) or (
            outcome.get("metric_type") if isinstance(outcome, dict) else None
        )
        if not label or not metric:
            continue
        human = _OUTCOME_LABELS.get(label, label)
        if label == "improved":
            improving_items.append(f"{metric} {human}")
        elif label == "worsened":
            worsening_items.append(f"{metric} {human}")

    if not action_outcomes:
        limitations.append("尚無行動成效資料，無法判斷改善或惡化趨勢。")

    # ── Repeated risks (source_types with ≥ _MIN_REPEATED_RISK_COUNT hits) ──
    risk_type_counter: Counter[str] = Counter()
    for entry in notification_history:
        status = entry.get("status", "")
        src = entry.get("source_type", "unknown")
        if status not in ("suppressed",):  # count non-suppressed signals
            risk_type_counter[src] += 1

    for alert in risk_alerts:
        src = getattr(alert, "source_type", None) or (
            alert.get("source_type") if isinstance(alert, dict) else "risk_alert"
        )
        risk_type_counter[src or "risk_alert"] += 1

    repeated_risks = [
        _source_label(k)
        for k, cnt in risk_type_counter.items()
        if cnt >= _MIN_REPEATED_RISK_COUNT
    ]

    # ── Effective actions (acted notifications + improved outcomes) ──────────
    effective_set: set[str] = set()

    for entry in notification_history:
        if entry.get("status") == "acted":
            src = entry.get("source_type", "unknown")
            effective_set.add(_source_label(src))

    for outcome in action_outcomes:
        label = getattr(outcome, "outcome_label", None) or (
            outcome.get("outcome_label") if isinstance(outcome, dict) else None
        )
        if label == "improved":
            action = getattr(outcome, "action", None)
            if action:
                title = getattr(action, "title", "")
                if title:
                    effective_set.add(title)

    for action in completed_actions:
        status = getattr(action, "status", None) or (
            action.get("status") if isinstance(action, dict) else None
        )
        title = getattr(action, "title", None) or (
            action.get("title") if isinstance(action, dict) else None
        )
        if status == "completed" and title:
            effective_set.add(title)

    effective_actions = sorted(effective_set)[:5]

    if not effective_actions:
        limitations.append("尚未有足夠的行動記錄來識別有效的健康行動。")

    # ── Ignored items (notifications with ignore_count > 0) ─────────────────
    ignored_counter: Counter[str] = Counter()
    for entry in notification_history:
        if (entry.get("ignore_count") or 0) > 0:
            src = entry.get("source_type", "unknown")
            ignored_counter[src] += 1

    ignored_items = [_source_label(k) for k, _ in ignored_counter.most_common(3)]

    # ── Confidence ─────────────────────────────────────────────────────────
    confidence = _compute_confidence(
        evidence_count=evidence_count,
        has_outcomes=len(action_outcomes) > 0,
        has_notifications=len(notification_history) > 0,
        has_risks=len(risk_alerts) > 0,
        limitations_count=len(limitations),
    )

    # ── Summary text ────────────────────────────────────────────────────────
    summary_text = _build_summary_text(
        period_type=period_type,
        top_themes=top_themes,
        improving_items=improving_items,
        worsening_items=worsening_items,
        repeated_risks=repeated_risks,
        effective_actions=effective_actions,
        limitations=limitations,
        confidence=confidence,
    )

    return {
        "periodType": period_type,
        "periodStart": p_start.isoformat(),
        "periodEnd": p_end.isoformat(),
        "summaryText": summary_text,
        "topThemes": top_themes,
        "improvingItems": improving_items,
        "worseningItems": worsening_items,
        "repeatedRisks": repeated_risks,
        "effectiveActions": effective_actions,
        "ignoredItems": ignored_items,
        "confidence": round(confidence, 3),
        "limitations": limitations,
    }


def _compute_confidence(
    evidence_count: int,
    has_outcomes: bool,
    has_notifications: bool,
    has_risks: bool,
    limitations_count: int,
) -> float:
    score = 0.0
    if has_notifications:
        score += 0.25
    if has_risks:
        score += 0.20
    if has_outcomes:
        score += 0.30
    # Evidence volume bonus (up to 0.25)
    volume_bonus = min(evidence_count / 20.0, 1.0) * 0.25
    score += volume_bonus
    # Penalty for limitations
    penalty = min(limitations_count * 0.10, 0.30)
    score = max(score - penalty, 0.0)
    return round(min(score, 1.0), 3)


def _build_summary_text(
    period_type: str,
    top_themes: list[str],
    improving_items: list[str],
    worsening_items: list[str],
    repeated_risks: list[str],
    effective_actions: list[str],
    limitations: list[str],
    confidence: float,
) -> str:
    period_label = {"daily": "今日", "weekly": "本週", "monthly": "本月"}.get(period_type, "本期間")
    parts: list[str] = []

    if top_themes:
        parts.append(f"{period_label}主要健康關注：{'、'.join(top_themes[:2])}。")

    if improving_items:
        parts.append(f"健康助手偵測到改善跡象：{improving_items[0]}。")

    if worsening_items:
        parts.append(f"需要持續留意：{worsening_items[0]}。")

    if repeated_risks:
        parts.append(f"重複出現的風險提醒：{repeated_risks[0]}，建議積極處理。")

    if effective_actions:
        parts.append(f"您已積極採取的行動：{effective_actions[0]}。")

    if not parts:
        parts.append(f"{period_label}尚無足夠的健康資料，請繼續記錄健康數據。")

    if confidence < 0.4:
        parts.append("（資料尚不完整，以上為初步觀察。）")

    return " ".join(parts)


# ---------------------------------------------------------------------------
# DB operations
# ---------------------------------------------------------------------------

def persist_narrative_memory(
    db: Session,
    user_id: str,
    person_id: str,
    memory: NarrativeMemoryResult,
) -> NarrativeMemory:
    """Upsert a NarrativeMemory record for (user, person, period_type, period_start).

    If a record already exists for the same period window, it is overwritten.
    """
    uid = _to_uuid(user_id)
    pid = _to_uuid(person_id)
    p_start = date.fromisoformat(memory["periodStart"])
    p_end = date.fromisoformat(memory["periodEnd"])

    existing = (
        db.query(NarrativeMemory)
        .filter(
            NarrativeMemory.user_id == uid,
            NarrativeMemory.subject_profile_id == pid,
            NarrativeMemory.period_type == memory["periodType"],
            NarrativeMemory.period_start == p_start,
        )
        .first()
    )

    if existing:
        row = existing
    else:
        row = NarrativeMemory(
            user_id=uid,
            subject_profile_id=pid,
            period_type=memory["periodType"],
            period_start=p_start,
        )
        db.add(row)

    row.period_end = p_end
    row.top_themes_json = memory["topThemes"]
    row.improving_items_json = memory["improvingItems"]
    row.worsening_items_json = memory["worseningItems"]
    row.repeated_risks_json = memory["repeatedRisks"]
    row.effective_actions_json = memory["effectiveActions"]
    row.ignored_items_json = memory["ignoredItems"]
    row.limitations_json = memory["limitations"]
    row.summary_text = memory["summaryText"]
    row.confidence = memory["confidence"]
    row.generated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(row)
    return row


def load_narrative_memory(
    db: Session,
    user_id: str,
    person_id: str,
    period_type: str,
    limit: int = 4,
) -> list[NarrativeMemoryResult]:
    """Load the most recent narrative memories for (user, person, period_type).

    Returns a list of NarrativeMemoryResult dicts, newest-first.
    Returns an empty list if none are found.
    """
    uid = _to_uuid(user_id)
    pid = _to_uuid(person_id)

    rows = (
        db.query(NarrativeMemory)
        .filter(
            NarrativeMemory.user_id == uid,
            NarrativeMemory.subject_profile_id == pid,
            NarrativeMemory.period_type == period_type,
        )
        .order_by(desc(NarrativeMemory.period_start))
        .limit(limit)
        .all()
    )

    return [_row_to_dict(r) for r in rows]


def _row_to_dict(row: NarrativeMemory) -> NarrativeMemoryResult:
    return {
        "id": str(row.id),
        "periodType": row.period_type,
        "periodStart": row.period_start.isoformat(),
        "periodEnd": row.period_end.isoformat(),
        "summaryText": row.summary_text,
        "topThemes": row.top_themes_json or [],
        "improvingItems": row.improving_items_json or [],
        "worseningItems": row.worsening_items_json or [],
        "repeatedRisks": row.repeated_risks_json or [],
        "effectiveActions": row.effective_actions_json or [],
        "ignoredItems": row.ignored_items_json or [],
        "limitations": row.limitations_json or [],
        "confidence": float(row.confidence) if row.confidence is not None else 0.0,
        "generatedAt": row.generated_at.isoformat() if row.generated_at else None,
    }


# ---------------------------------------------------------------------------
# Compare periods
# ---------------------------------------------------------------------------

def compare_narrative_periods(
    current: NarrativeMemoryResult,
    previous: NarrativeMemoryResult,
) -> dict[str, Any]:
    """Diff two narrative periods and return a structured comparison.

    Returns which themes / risks appeared, disappeared, or persisted.
    Never infers medical conclusions — only structural differences.
    """
    curr_themes = set(current.get("topThemes", []))
    prev_themes = set(previous.get("topThemes", []))

    curr_risks = set(current.get("repeatedRisks", []))
    prev_risks = set(previous.get("repeatedRisks", []))

    curr_conf = current.get("confidence", 0.0)
    prev_conf = previous.get("confidence", 0.0)

    return {
        "newThemes": sorted(curr_themes - prev_themes),
        "resolvedThemes": sorted(prev_themes - curr_themes),
        "persistingThemes": sorted(curr_themes & prev_themes),
        "newRisks": sorted(curr_risks - prev_risks),
        "resolvedRisks": sorted(prev_risks - curr_risks),
        "persistingRisks": sorted(curr_risks & prev_risks),
        "confidenceDelta": round(curr_conf - prev_conf, 3),
        "newEffectiveActions": sorted(
            set(current.get("effectiveActions", []))
            - set(previous.get("effectiveActions", []))
        ),
        "improvingComparedToPrevious": len(current.get("improvingItems", [])) > len(
            previous.get("improvingItems", [])
        ),
    }


# ---------------------------------------------------------------------------
# Evidence loader (DB) — used by API endpoint
# ---------------------------------------------------------------------------

def _load_evidence_for_period(
    db: Session,
    user_id: str,
    person_id: str,
    period_type: str,
    notification_history: list[dict[str, Any]],
) -> tuple[list[Any], list[Any], list[Any]]:
    """Load risk alerts, completed actions, and action outcomes for the period."""
    uid = _to_uuid(user_id)
    pid = _to_uuid(person_id)
    days = _PERIOD_DAYS.get(period_type, 7)
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    risk_alerts = (
        db.query(RiskAlert)
        .filter(
            RiskAlert.user_id == uid,
            RiskAlert.subject_profile_id == pid,
            RiskAlert.created_at >= cutoff,
        )
        .all()
    )

    completed_actions = (
        db.query(HealthAction)
        .filter(
            HealthAction.user_id == uid,
            HealthAction.person_id == pid,
            HealthAction.status == "completed",
            HealthAction.completed_at >= cutoff,
        )
        .all()
    )

    action_outcomes = (
        db.query(ActionOutcome)
        .filter(
            ActionOutcome.user_id == uid,
            ActionOutcome.person_id == pid,
            ActionOutcome.computed_at >= cutoff,
        )
        .all()
    )

    return risk_alerts, completed_actions, action_outcomes


def generate_and_persist_narrative_memory(
    db: Session,
    user_id: str,
    person_id: str,
    period_type: str,
    notification_history: list[dict[str, Any]],
) -> NarrativeMemoryResult:
    """High-level convenience: load evidence, build memory, persist, return result."""
    risk_alerts, completed_actions, action_outcomes = _load_evidence_for_period(
        db, user_id, person_id, period_type, notification_history
    )
    memory = build_narrative_memory(
        period_type=period_type,
        notification_history=notification_history,
        risk_alerts=risk_alerts,
        completed_actions=completed_actions,
        action_outcomes=action_outcomes,
    )
    persist_narrative_memory(db, user_id, person_id, memory)
    return memory
