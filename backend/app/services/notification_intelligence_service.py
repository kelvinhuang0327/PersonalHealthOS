"""Notification Intelligence Service — P5 Foundation
=====================================================
Pure-function module — no DB access.  All inputs come from
build_evidence_bundle() output plus optional notification history.

Exports
-------
  build_notification_candidates()    — produces NotificationCandidate list
  apply_notification_fatigue_guard() — filters / deduplicates / downgrades

NotificationCandidate keys
--------------------------
  candidate_id     — deterministic 12-char hex (hash of cooldown_key)
  source_type      — "device_escalation" | "lab_abnormality" | "symptom_pattern"
                     | "risk_alert" | "recommendation"
  priority         — "low" | "medium" | "high" | "urgent"
  title            — zh-TW, no diagnosis wording
  message          — zh-TW, no diagnosis wording
  why_now          — explanation of timing
  suggested_action — zh-TW action copy or None
  confidence       — float [0.20, 0.95]
  evidence_sources — list[{"type": str, "id": str | None, "summary": str}]
  cooldown_key     — stable dedup key, safe to use as a DB/cache key
  suppress_reason  — None when active; str when suppressed

NotificationHistory entry keys
------------------------------
  cooldown_key  — str
  priority      — str
  status        — "sent" | "snoozed" | "dismissed" | "ignored" | "acked"
  snooze_count  — int  (default 0)
  ignore_count  — int  (default 0)
  sent_at       — ISO-8601 str | None

Design contracts
----------------
  No hallucination: candidates are only generated from evidence actually present
    in the input bundle.
  No diagnosis wording: copy reviewed against "建議追蹤" framing.
  Low confidence (<0.40) → priority capped at "medium".
  Empty bundle → empty candidate list.
  suppress_reason always populated on suppressed candidates.
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_PRIORITY_RANK: dict[str, int] = {
    "low":    0,
    "medium": 1,
    "high":   2,
    "urgent": 3,
}

# Cooldown durations in seconds per priority level.
# Candidates with the same cooldown_key sent within this window are suppressed.
_COOLDOWN_SECONDS: dict[str, float] = {
    "urgent": 6 * 3600,          # 6 h
    "high":   24 * 3600,         # 24 h
    "medium": 72 * 3600,         # 72 h
    "low":    7 * 24 * 3600,     # 7 days
}

# Device escalation level → notification priority
_ESCALATION_TO_PRIORITY: dict[str, str | None] = {
    "urgent":  "urgent",
    "warning": "high",
    "watch":   "medium",
    "none":    None,  # no candidate
}

# Lab abnormality severity → notification priority
_LAB_SEVERITY_TO_PRIORITY: dict[str, str] = {
    "high":   "high",
    "medium": "medium",
    "low":    "low",
}

# Symptom pattern type → base priority (may be further modified by severity)
_SYMPTOM_PATTERN_PRIORITY: dict[str, str] = {
    "worsening_symptom":                "high",
    "unresolved_high_severity_symptom": "high",
    "symptom_with_lab_risk":            "medium",
    "symptom_with_device_signal":       "medium",
    "recurring_symptom":                "medium",
}

# Risk alert severity → notification priority
_RISK_ALERT_PRIORITY: dict[str, str] = {
    "critical": "urgent",
    "high":     "high",
    "warning":  "high",
    "medium":   "medium",
    "info":     "low",
    "low":      "low",
}

# Minimum confidence to produce any candidate from a source
_MIN_CONFIDENCE = 0.20

# Confidence threshold below which a candidate is capped at "medium"
_HIGH_PRIORITY_CONFIDENCE_THRESHOLD = 0.40

# Max ignore count before permanent suppression
_MAX_IGNORE_COUNT = 3

# Title templates by priority (device escalation)
_ESCALATION_TITLE: dict[str, str] = {
    "urgent": "裝置訊號顯示異常，請盡快確認",
    "high":   "裝置訊號出現警示，建議關注",
    "medium": "裝置訊號建議留意",
    "low":    "裝置訊號更新",
}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _candidate_id(cooldown_key: str) -> str:
    """Return a deterministic 12-char hex ID from a cooldown_key."""
    return hashlib.md5(cooldown_key.encode()).hexdigest()[:12]


def _cap_priority(priority: str, confidence: float) -> str:
    """Cap priority to 'medium' when confidence is below threshold."""
    if (
        confidence < _HIGH_PRIORITY_CONFIDENCE_THRESHOLD
        and _PRIORITY_RANK.get(priority, 0) > _PRIORITY_RANK["medium"]
    ):
        return "medium"
    return priority


def _downgrade_priority(priority: str) -> str:
    """Downgrade priority by one level (urgent→high, high→medium, etc.)."""
    order = ["low", "medium", "high", "urgent"]
    idx = order.index(priority) if priority in order else 0
    return order[max(0, idx - 1)]


def _parse_dt(ts: str | None) -> datetime | None:
    if not ts:
        return None
    try:
        dt = datetime.fromisoformat(ts)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return None


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _sanitise(s: str) -> str:
    """Produce a safe lowercase key fragment (max 40 chars)."""
    return s.lower().replace(" ", "_").replace("/", "_").replace("-", "_")[:40]


def _clamp_confidence(c: float) -> float:
    return min(max(c, _MIN_CONFIDENCE), 0.95)


# ---------------------------------------------------------------------------
# Per-source candidate builders
# ---------------------------------------------------------------------------

def _candidate_from_device_escalation(
    escalation: dict[str, Any],
) -> dict[str, Any] | None:
    """Build a NotificationCandidate from a device escalation dict."""
    level = escalation.get("escalationLevel", "none")
    priority = _ESCALATION_TO_PRIORITY.get(level)
    if not priority:
        return None

    confidence = float(escalation.get("confidence", 0.50))
    if confidence < _MIN_CONFIDENCE:
        return None

    priority = _cap_priority(priority, confidence)
    reasons: list[str] = escalation.get("reasons") or []
    message = "；".join(reasons[:3]) if reasons else "裝置訊號異常"
    recommended_action = escalation.get("recommendedAction")

    cooldown_key = f"device_escalation_{level}"
    evidence_sources = (
        [{"type": "device_escalation", "id": None, "summary": r} for r in reasons[:3]]
        if reasons
        else [{"type": "device_escalation", "id": None, "summary": "裝置訊號偵測"}]
    )

    return {
        "candidate_id": _candidate_id(cooldown_key),
        "source_type": "device_escalation",
        "priority": priority,
        "title": _ESCALATION_TITLE.get(priority, "裝置訊號提醒"),
        "message": message,
        "why_now": f"裝置訊號升級為「{level}」等級",
        "suggested_action": recommended_action,
        "confidence": _clamp_confidence(confidence),
        "evidence_sources": evidence_sources,
        "cooldown_key": cooldown_key,
        "suppress_reason": None,
    }


def _candidate_from_lab_abnormality(abn: dict[str, Any]) -> dict[str, Any] | None:
    """Build a NotificationCandidate from a lab abnormality dict."""
    severity = abn.get("severity", "low")
    priority = _LAB_SEVERITY_TO_PRIORITY.get(severity, "low")
    confidence = float(abn.get("confidence", 0.50))

    if confidence < _MIN_CONFIDENCE:
        return None

    priority = _cap_priority(priority, confidence)

    rule_id = abn.get("rule_id") or _sanitise(abn.get("labItemName", "unknown"))
    cooldown_key = f"lab_abnormality_{_sanitise(rule_id)}"

    return {
        "candidate_id": _candidate_id(cooldown_key),
        "source_type": "lab_abnormality",
        "priority": priority,
        "title": f"健檢指標異常：{abn.get('labItemName', '未知項目')}",
        "message": abn.get("whyDetected") or "指標數值標記為異常",
        "why_now": f"健檢指標「{abn.get('labItemName', '')}」嚴重度：{severity}",
        "suggested_action": abn.get("suggestedAction"),
        "confidence": _clamp_confidence(confidence),
        "evidence_sources": abn.get("evidenceSources") or [],
        "cooldown_key": cooldown_key,
        "suppress_reason": None,
    }


def _candidate_from_symptom_pattern(pattern: dict[str, Any]) -> dict[str, Any] | None:
    """Build a NotificationCandidate from a symptom pattern dict."""
    pattern_type = pattern.get("patternType", "")
    base_priority = _SYMPTOM_PATTERN_PRIORITY.get(pattern_type)
    if not base_priority:
        return None

    severity = pattern.get("severity", "medium")
    confidence = float(pattern.get("confidence", 0.50))

    if confidence < _MIN_CONFIDENCE:
        return None

    # Worsening + medium severity → downgrade to medium
    if pattern_type == "worsening_symptom" and severity == "medium":
        base_priority = "medium"

    priority = _cap_priority(base_priority, confidence)

    symptom_type = pattern.get("symptomType", "未知症狀")
    label = pattern.get("label") or pattern_type
    cooldown_key = f"symptom_pattern_{_sanitise(pattern_type)}_{_sanitise(symptom_type)}"

    return {
        "candidate_id": _candidate_id(cooldown_key),
        "source_type": "symptom_pattern",
        "priority": priority,
        "title": f"症狀提醒：{label}",
        "message": pattern.get("whyDetected") or "症狀模式偵測到",
        "why_now": f"症狀「{symptom_type}」{label}",
        "suggested_action": pattern.get("suggestedAction"),
        "confidence": _clamp_confidence(confidence),
        "evidence_sources": pattern.get("evidenceSources") or [],
        "cooldown_key": cooldown_key,
        "suppress_reason": None,
    }


def _candidate_from_risk_alert(alert: dict[str, Any]) -> dict[str, Any] | None:
    """Build a NotificationCandidate from a risk alert dict."""
    severity = alert.get("severity", "low")
    priority = _RISK_ALERT_PRIORITY.get(severity, "low")
    confidence = 0.85  # risk alerts are pre-validated

    priority = _cap_priority(priority, confidence)

    rule_code = alert.get("rule_code") or _sanitise(alert.get("title", "alert"))
    cooldown_key = f"risk_alert_{_sanitise(rule_code)}"

    return {
        "candidate_id": _candidate_id(cooldown_key),
        "source_type": "risk_alert",
        "priority": priority,
        "title": alert.get("title") or "健康風險提醒",
        "message": alert.get("message") or "",
        "why_now": f"風險警示已觸發（{severity}）",
        "suggested_action": alert.get("recommendation"),
        "confidence": confidence,
        "evidence_sources": [
            {
                "type": "risk_alert",
                "id": alert.get("source_id"),
                "summary": alert.get("title") or "",
            }
        ],
        "cooldown_key": cooldown_key,
        "suppress_reason": None,
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_notification_candidates(
    bundle: dict[str, Any],
    notification_history: list[dict[str, Any]] | None = None,  # reserved, unused by builder
) -> list[dict[str, Any]]:
    """Generate raw notification candidates from an evidence bundle.

    Does NOT apply fatigue guard.  Call apply_notification_fatigue_guard()
    after this function to filter and downgrade.

    Parameters
    ----------
    bundle:
        Output of build_evidence_bundle().
    notification_history:
        Reserved for future enrichment.  Currently unused here; pass it to
        apply_notification_fatigue_guard() instead.

    Returns
    -------
    list[NotificationCandidate] — sorted urgent→high→medium→low, then
    confidence descending within tier.
    """
    candidates: list[dict[str, Any]] = []

    # ── device escalation ──────────────────────────────────────────────────
    escalation = bundle.get("device_escalation") or {}
    if isinstance(escalation, dict):
        level = escalation.get("escalationLevel", "none")
        if level != "none":
            c = _candidate_from_device_escalation(escalation)
            if c:
                candidates.append(c)

    # ── lab abnormalities ──────────────────────────────────────────────────
    for abn in bundle.get("lab_abnormalities") or []:
        c = _candidate_from_lab_abnormality(abn)
        if c:
            candidates.append(c)

    # ── symptom patterns ──────────────────────────────────────────────────
    for pattern in bundle.get("symptom_patterns") or []:
        c = _candidate_from_symptom_pattern(pattern)
        if c:
            candidates.append(c)

    # ── risk alerts ────────────────────────────────────────────────────────
    for alert in bundle.get("risk_alerts") or []:
        c = _candidate_from_risk_alert(alert)
        if c:
            candidates.append(c)

    # ── deduplicate by cooldown_key: keep highest-priority per key ─────────
    seen: dict[str, dict[str, Any]] = {}
    for c in candidates:
        key = c["cooldown_key"]
        if (
            key not in seen
            or _PRIORITY_RANK.get(c["priority"], 0)
            > _PRIORITY_RANK.get(seen[key]["priority"], 0)
        ):
            seen[key] = c

    # ── sort: priority desc, then confidence desc ──────────────────────────
    return sorted(
        seen.values(),
        key=lambda x: (_PRIORITY_RANK.get(x["priority"], 0), x["confidence"]),
        reverse=True,
    )


def apply_notification_fatigue_guard(
    candidates: list[dict[str, Any]],
    notification_history: list[dict[str, Any]] | None = None,
    active_rule_ids: set[str] | None = None,
) -> dict[str, list[dict[str, Any]]]:
    """Apply alert-fatigue guard rules to a candidate list.

    Rules applied in order (first match wins):
    1. ignore_count >= 3 → suppress permanently
    2. Active action rule_id substring match on cooldown_key → suppress (dedup)
    3. Same cooldown_key sent within cooldown window → suppress (throttle)
    4. status == "snoozed" → downgrade priority one level (candidate remains active)

    Parameters
    ----------
    candidates:
        Output of build_notification_candidates().
    notification_history:
        List of past notification records (see module docstring for schema).
    active_rule_ids:
        Set of rule_id strings from currently active health actions.

    Returns
    -------
    {"active": [...], "suppressed": [...]}
    Every suppressed candidate has suppress_reason populated.
    """
    # Build lookup by cooldown_key
    history_map: dict[str, dict[str, Any]] = {}
    for h in (notification_history or []):
        key = h.get("cooldown_key", "")
        if key:
            history_map[key] = h

    active_rule_ids = active_rule_ids or set()
    now = _now()

    active: list[dict[str, Any]] = []
    suppressed: list[dict[str, Any]] = []

    for raw_c in candidates:
        c = dict(raw_c)  # shallow copy — priority may be mutated
        key = c["cooldown_key"]
        hist = history_map.get(key)

        # Rule 1 — ignore count
        if hist and hist.get("ignore_count", 0) >= _MAX_IGNORE_COUNT:
            c["suppress_reason"] = f"已忽略 {hist['ignore_count']} 次，暫停提醒"
            suppressed.append(c)
            continue

        # Rule 2 — active action dedup
        action_match = any(
            bool(rule_id) and rule_id in key
            for rule_id in active_rule_ids
        )
        if action_match:
            c["suppress_reason"] = "相關健康行動正在追蹤中，不重複提醒"
            suppressed.append(c)
            continue

        # Rule 3 — cooldown window
        if hist:
            sent_at_dt = _parse_dt(hist.get("sent_at"))
            if sent_at_dt:
                elapsed_s = (now - sent_at_dt).total_seconds()
                cooldown_s = _COOLDOWN_SECONDS.get(c["priority"], 24 * 3600)
                if elapsed_s < cooldown_s:
                    remaining_h = int((cooldown_s - elapsed_s) // 3600)
                    c["suppress_reason"] = (
                        f"冷卻中（距上次提醒 {int(elapsed_s // 3600)} 小時，"
                        f"剩餘約 {remaining_h} 小時）"
                    )
                    suppressed.append(c)
                    continue

        # Rule 4 — snooze handling (suppress if still in snooze window; downgrade if expired)
        if hist and hist.get("status") == "snoozed":
            snoozed_until_dt = _parse_dt(hist.get("snoozed_until"))
            if snoozed_until_dt and snoozed_until_dt > now:
                c["suppress_reason"] = (
                    f"已暫緩提醒（至 {snoozed_until_dt.strftime('%m/%d %H:%M')}）"
                )
                suppressed.append(c)
                continue
            # Snooze expired or no deadline → downgrade and keep active
            c["priority"] = _downgrade_priority(c["priority"])

        # Rule 5 — clicked/acted: downgrade priority as a positive reward signal
        elif hist and hist.get("status") in ("clicked", "acted"):
            c["priority"] = _downgrade_priority(c["priority"])

        active.append(c)

    return {"active": active, "suppressed": suppressed}


# ---------------------------------------------------------------------------
# P6 — Personalization ranking
# ---------------------------------------------------------------------------

def apply_personalization_ranking(
    candidates: list[dict[str, Any]],
    profile: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Adjust candidate priorities based on the personalization profile.

    Rules (applied in order; first rule that modifies a field wins for that field):
    A. BYPASS — priority=="urgent" or source_type=="device_escalation"
       → returned unchanged; add personalization_reasons=["緊急：不受個人化影響"]
    B. High-response category (act_count >= 2 OR in high_response_categories)
       → confidence +0.10, add reason
    C. Frequently ignored category (ignore_count >= 2)
       → confidence −ignore_count×0.05 (floor 0.20), downgrade priority one level
    D. Low engagement (engagement_score < 0.30) AND priority > "medium"
       → cap priority at "medium", add reason

    Parameters
    ----------
    candidates:
        Output of build_notification_candidates() or after fatigue guard.
    profile:
        Serialized PersonalizationProfile dict (from profile_to_dict()).
        If None the candidates are returned unchanged (safe fallback).

    Returns
    -------
    list[dict] — same length, same order, priorities/confidence adjusted.
    """
    if not profile:
        return list(candidates)

    acted_cats: dict[str, int] = profile.get("acted_categories") or {}
    ignored_cats: dict[str, int] = profile.get("ignored_categories") or {}
    high_response: set[str] = set(profile.get("high_response_categories") or [])
    engagement: float = float(profile.get("engagement_score") or 0.5)

    result: list[dict[str, Any]] = []

    for raw_c in candidates:
        c = dict(raw_c)
        src = c.get("source_type", "")
        reasons: list[str] = list(c.get("personalization_reasons") or [])

        # A — bypass
        if c.get("priority") == "urgent" or src == "device_escalation":
            c["personalization_reasons"] = reasons + ["緊急提醒：不受個人化排序影響"]
            result.append(c)
            continue

        orig_conf = float(c.get("confidence", 0.5))
        adj_conf = orig_conf

        # B — high-response boost
        act_count = acted_cats.get(src, 0)
        if act_count >= 2 or src in high_response:
            adj_conf = min(adj_conf + 0.10, 0.95)
            reasons.append("您常回應此類提醒，已優先排序")

        # C — ignored penalty
        ignore_count = ignored_cats.get(src, 0)
        if ignore_count >= 2:
            penalty = min(ignore_count * 0.05, 0.25)
            adj_conf = max(adj_conf - penalty, 0.20)
            c["priority"] = _downgrade_priority(c["priority"])
            reasons.append(f"此類提醒常被略過（{ignore_count} 次），已降低優先度")

        # D — low engagement cap
        if engagement < 0.30 and _PRIORITY_RANK.get(c["priority"], 0) > _PRIORITY_RANK["medium"]:
            c["priority"] = "medium"
            reasons.append("目前互動較少，已調整提醒強度")

        c["confidence"] = min(max(adj_conf, 0.20), 0.95)
        c["personalization_reasons"] = reasons
        result.append(c)

    return result


# ---------------------------------------------------------------------------
# P6.2 — Adaptive Timing
# ---------------------------------------------------------------------------

def apply_adaptive_notification_timing(
    candidates: list[dict[str, Any]],
    analytics: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Adjust candidate priorities / confidence based on engagement timing analytics.

    Rules (applied in order; urgent / device_escalation always bypass):
    T1. BYPASS — priority=="urgent" or source_type=="device_escalation"
        → returned unchanged; reason appended
    T2. Best window (current time in bestNotificationWindows)
        → confidence +0.08 (cap 0.95), reason appended
    T3. Ignored window (current time in ignoredTimeWindows)
        → confidence −0.10 (floor 0.20), downgrade priority one level, reason
    T4. Declining engagement trend
        → confidence −0.05 (floor 0.20), downgrade priority one level if > medium

    Parameters
    ----------
    candidates:
        Output of apply_personalization_ranking() or build_notification_candidates().
    analytics:
        EngagementAnalytics dict from build_engagement_analytics().
        If None the candidates are returned unchanged (safe fallback).

    Returns
    -------
    list[dict] — same length, same order, adjustments applied in-place copies.
    """
    if not analytics:
        return list(candidates)

    from datetime import datetime, timezone as _tz
    current_hour = datetime.now(_tz.utc).hour
    current_window = _get_time_window_label(current_hour)

    best_windows: set[str] = set(analytics.get("bestNotificationWindows") or [])
    ignored_windows: set[str] = set(analytics.get("ignoredTimeWindows") or [])
    trend: str = analytics.get("engagementTrend") or "stable"

    result: list[dict[str, Any]] = []
    for raw_c in candidates:
        c = dict(raw_c)
        src = c.get("source_type", "")
        reasons: list[str] = list(c.get("personalization_reasons") or [])

        # T1 — bypass
        if c.get("priority") == "urgent" or src == "device_escalation":
            result.append(c)
            continue

        conf = float(c.get("confidence", 0.5))

        # T2 — best window boost
        if current_window in best_windows:
            conf = min(conf + 0.08, 0.95)
            reasons.append("當前為您最佳回應時段，已優先提醒")

        # T3 — ignored window penalty
        if current_window in ignored_windows:
            conf = max(conf - 0.10, 0.20)
            c["priority"] = _downgrade_priority(c.get("priority", "medium"))
            reasons.append("當前為您較少回應的時段，提醒強度已調整")

        # T4 — declining engagement penalty
        if trend == "declining":
            conf = max(conf - 0.05, 0.20)
            if _PRIORITY_RANK.get(c.get("priority", "medium"), 0) > _PRIORITY_RANK["medium"]:
                c["priority"] = _downgrade_priority(c.get("priority", "high"))
            reasons.append("助手偵測到提醒回應減少，已降低頻率以避免疲勞")

        c["confidence"] = min(max(conf, 0.20), 0.95)
        c["personalization_reasons"] = reasons
        result.append(c)

    return result


def _get_time_window_label(hour: int) -> str:
    """Map 0–23 hour to a named window label (matches engagement_analytics_service)."""
    if 6 <= hour < 12:
        return "morning"
    if 12 <= hour < 18:
        return "afternoon"
    if 18 <= hour < 22:
        return "evening"
    return "night"
