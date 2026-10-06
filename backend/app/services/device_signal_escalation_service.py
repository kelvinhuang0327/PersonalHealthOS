"""Device Signal Escalation Service
=====================================
Pure-function module providing:

  build_device_signal_history(external_metrics, ...) -> dict[str, SignalHistory]
  evaluate_signal_escalation(current_signals, signal_history,
                              symptom_history, outcomes) -> EscalationDecision

Both functions are side-effect-free (no DB access) for full testability.

SignalHistory dict keys:
    signal_type, first_detected_at, last_detected_at, resolved_at,
    recurrence_count, escalation_state ("active"|"resolved"|"escalating"),
    severity_progression (list[str], oldest→newest),
    trend_direction ("worsening"|"stable"|"improving"),
    metric_snapshots (list[{value, timestamp, freshness}])

EscalationDecision dict keys:
    escalationLevel ("none"|"watch"|"warning"|"urgent"),
    reasons (list[str]), confidence (float),
    recommendedAction (str|None), requiresFollowUp (bool)
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from app.services.device_signal_detection_service import detect_device_signals

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_SEVERITY_INT: dict[str, int] = {"low": 1, "medium": 2, "high": 3}

_ESCALATION_LEVELS = ("none", "watch", "warning", "urgent")
_ESCALATION_RANK: dict[str, int] = {lv: i for i, lv in enumerate(_ESCALATION_LEVELS)}

# Human-readable labels for signal types (zh-TW)
_SIGNAL_LABEL: dict[str, str] = {
    "elevated_resting_heart_rate": "靜息心率偏高",
    "abnormal_pulse_trend":        "心率趨勢異常",
    "low_sleep_duration":          "睡眠不足",
    "reduced_activity":            "活動量不足",
    "unstable_spo2":               "血氧不穩定",
}

# Symptom keywords correlated with each signal type for cross-signal escalation
_SYMPTOM_SIGNAL_CORRELATION: dict[str, list[str]] = {
    "elevated_resting_heart_rate": [
        "心悸", "胸痛", "胸悶", "呼吸困難", "palpitation", "chest", "tachycardia",
    ],
    "abnormal_pulse_trend": [
        "心悸", "胸痛", "palpitation", "chest",
    ],
    "low_sleep_duration": [
        "失眠", "疲勞", "疲倦", "睡眠", "insomnia", "fatigue", "tired", "exhausted",
    ],
    "reduced_activity": [
        "疲勞", "無力", "虛弱", "fatigue", "weakness", "tired", "lethargic",
    ],
    "unstable_spo2": [
        "呼吸困難", "胸悶", "dyspnea", "shortness of breath",
    ],
}

# Which raw metric key to include in metric_snapshots per signal type
_SIGNAL_METRIC_KEY: dict[str, str | None] = {
    "elevated_resting_heart_rate": "heart_rate",
    "abnormal_pulse_trend":        "heart_rate",
    "low_sleep_duration":          "sleep_hours",
    "reduced_activity":            "steps",
    "unstable_spo2":               None,
}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _parse_ts(ts_str: str | None) -> datetime | None:
    """Parse ISO timestamp string to UTC-aware datetime, or None on failure."""
    if not ts_str:
        return None
    try:
        dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, TypeError):
        return None


# ---------------------------------------------------------------------------
# Task 1 — Signal Trend Memory
# ---------------------------------------------------------------------------

def build_device_signal_history(
    external_metrics: list[dict],
    reference_dt: datetime | None = None,
    window_days: int = 7,
    num_windows: int = 4,
) -> dict[str, dict]:
    """Derive per-signal-type trend history from the external_metrics time series.

    Splits the lookback period into ``num_windows`` windows of ``window_days``
    each (window 0 = most recent, window N-1 = oldest).  Detects device
    signals in each window bucket, then builds a SignalHistory record for
    every signal type that appeared in at least one window.

    No DB access — pure computation over the already-fetched metrics list.

    Args:
        external_metrics:  List of metric dicts (from build_evidence_bundle).
                           Must include a "timestamp" key (ISO string) and the
                           raw metric fields used by detect_device_signals.
        reference_dt:      Anchor point for window calculation.  Defaults to
                           datetime.now(UTC).  Pass a fixed value in tests.
        window_days:       Width of each time bucket in days.  Default: 7.
        num_windows:       Number of buckets.  Default: 4  (≈ 28 days lookback).

    Returns:
        {signal_type: SignalHistory}  — empty dict when external_metrics is empty.
    """
    if not external_metrics:
        return {}

    ref = reference_dt or datetime.now(timezone.utc)

    # ── Bucket metrics into weekly windows ─────────────────────────────────
    # Window w covers:  ref − (w+1)*window_days  ≤ ts  <  ref − w*window_days
    # Window 0 = most recent, window (num_windows−1) = oldest.
    windowed: list[list[dict]] = [[] for _ in range(num_windows)]
    for m in external_metrics:
        ts = _parse_ts(m.get("timestamp"))
        if ts is None:
            windowed[0].append(m)  # no timestamp → treat as recent
            continue
        age_days = (ref - ts).total_seconds() / 86400.0
        w = int(age_days // window_days)
        if 0 <= w < num_windows:
            windowed[w].append(m)
        # Older than total coverage → ignore

    # ── Detect signals in each window ──────────────────────────────────────
    window_detections: list[dict[str, str]] = []   # [{signal_type: severity}]
    for w in range(num_windows):
        if not windowed[w]:
            window_detections.append({})
            continue
        sigs = detect_device_signals(windowed[w])
        window_detections.append({s["signal_type"]: s["severity"] for s in sigs})

    # ── Gather all signal types seen across any window ──────────────────────
    all_signal_types: set[str] = set()
    for det in window_detections:
        all_signal_types.update(det.keys())

    if not all_signal_types:
        return {}

    # ── Build SignalHistory per signal type ─────────────────────────────────
    history: dict[str, dict] = {}

    for sig_type in all_signal_types:
        # Windows where this signal was detected (0 = most recent)
        detecting_windows = [w for w in range(num_windows) if sig_type in window_detections[w]]
        if not detecting_windows:
            continue

        recurrence_count = len(detecting_windows)
        in_most_recent = (0 in detecting_windows)
        oldest_window_idx = max(detecting_windows)   # largest index = oldest window

        # severity_progression: build oldest → newest
        sev_prog: list[str] = []
        for w in range(num_windows - 1, -1, -1):  # num_windows-1 down to 0
            if sig_type in window_detections[w]:
                sev_prog.append(window_detections[w][sig_type])

        # Trend direction from first to last detection
        if len(sev_prog) >= 2:
            start_int = _SEVERITY_INT.get(sev_prog[0], 1)
            end_int   = _SEVERITY_INT.get(sev_prog[-1], 1)
            if end_int > start_int:
                trend = "worsening"
            elif end_int < start_int:
                trend = "improving"
            else:
                trend = "stable"
        else:
            trend = "stable"

        # Escalation state
        if not in_most_recent:
            escalation_state = "resolved"
        elif trend == "worsening" and recurrence_count >= 2:
            escalation_state = "escalating"
        else:
            escalation_state = "active"

        # ── Timestamps ─────────────────────────────────────────────────────
        # first_detected_at: oldest actual metric timestamp in oldest detecting window
        oldest_metrics = windowed[oldest_window_idx]
        oldest_ts_dts  = [_parse_ts(m.get("timestamp")) for m in oldest_metrics]
        oldest_ts_dts  = [dt for dt in oldest_ts_dts if dt is not None]
        first_detected_at: str | None = min(oldest_ts_dts).isoformat() if oldest_ts_dts else None

        if in_most_recent:
            # last_detected_at: newest metric timestamp in window 0
            newest_metrics = windowed[0]
            newest_ts_dts  = [_parse_ts(m.get("timestamp")) for m in newest_metrics]
            newest_ts_dts  = [dt for dt in newest_ts_dts if dt is not None]
            last_detected_at: str | None = max(newest_ts_dts).isoformat() if newest_ts_dts else None
            resolved_at: str | None = None
        else:
            # last_detected_at: newest metric timestamp in the most-recent detecting window
            last_window_idx = min(detecting_windows)  # smallest index = most recent
            last_metrics   = windowed[last_window_idx]
            last_ts_dts    = [_parse_ts(m.get("timestamp")) for m in last_metrics]
            last_ts_dts    = [dt for dt in last_ts_dts if dt is not None]
            last_detected_at = max(last_ts_dts).isoformat() if last_ts_dts else None
            # resolved_at: approximate boundary of the last detecting window
            resolved_at = (ref - timedelta(days=last_window_idx * window_days)).isoformat()

        # ── Metric snapshots (up to 10 most recent readings) ───────────────
        metric_key = _SIGNAL_METRIC_KEY.get(sig_type)
        metric_snapshots: list[dict] = []
        if metric_key:
            for m in external_metrics[:10]:
                val = m.get(metric_key)
                if val is not None:
                    metric_snapshots.append({
                        "value":     float(val),
                        "timestamp": m.get("timestamp"),
                        "freshness": m.get("freshness", "unknown"),
                    })

        history[sig_type] = {
            "signal_type":         sig_type,
            "first_detected_at":   first_detected_at,
            "last_detected_at":    last_detected_at,
            "resolved_at":         resolved_at,
            "recurrence_count":    recurrence_count,
            "escalation_state":    escalation_state,
            "severity_progression": sev_prog,
            "trend_direction":     trend,
            "metric_snapshots":    metric_snapshots,
        }

    return history


# ---------------------------------------------------------------------------
# Task 2 — Escalation Engine
# ---------------------------------------------------------------------------

def evaluate_signal_escalation(
    current_signals: list[dict],
    signal_history: dict[str, dict],
    symptom_history: list[dict],
    outcomes: list[dict],
) -> dict[str, Any]:
    """Evaluate overall escalation level from current device signals + trend history.

    Escalation rules (applied in priority order — highest level wins):
      urgent:   high-severity signal with recurrence ≥ 3
                OR ≥ 2 distinct signal types all worsening simultaneously
                OR symptom severity ≥ 8 AND matching wearable signal (med/high)
      warning:  any current signal with recurrence ≥ 2 (persistent)
                OR any signal in "escalating" state
                OR any high-severity current signal
                OR symptom severity ≥ 6 AND matching wearable signal
      watch:    any current signal exists (but none of the above)
      none:     no current signals

    Stale guard:
      • All signals stale  → cap at "watch", confidence − 0.25
      • Any signal stale   → confidence − 0.10
      • No device data     → always "none" (no escalation hallucination)

    Args:
        current_signals:   Output of detect_device_signals (current window).
        signal_history:    Output of build_device_signal_history.
        symptom_history:   List of symptom dicts (from bundle["symptoms"] +
                           bundle["long_term_symptoms"]).  Each may have keys:
                           "symptom" (str) and "severity" (int 0-10).
        outcomes:          List of outcome dicts from bundle["outcomes"].
                           Currently not used in scoring but included for
                           future extension.

    Returns:
        EscalationDecision dict with keys:
            escalationLevel, reasons, confidence, recommendedAction, requiresFollowUp
    """
    if not current_signals:
        return {
            "escalationLevel": "none",
            "reasons": [],
            "confidence": 0.80,
            "recommendedAction": None,
            "requiresFollowUp": False,
        }

    reasons: list[str] = []
    level = "none"
    confidence = 0.85
    recommended_action: str | None = None

    # ── Stale guard ─────────────────────────────────────────────────────────
    all_stale = all(s.get("freshness") == "stale" for s in current_signals)
    any_stale = any(s.get("freshness") == "stale" for s in current_signals)
    if all_stale:
        confidence -= 0.25
    elif any_stale:
        confidence -= 0.10

    # ── Helper: promote escalation level ────────────────────────────────────
    def _promote(new_level: str) -> None:
        nonlocal level
        if _ESCALATION_RANK[new_level] > _ESCALATION_RANK[level]:
            level = new_level

    # ── Helper: symptom keyword correlation ─────────────────────────────────
    def _has_symptom_correlation(sig_type: str, min_severity: int) -> bool:
        keywords = _SYMPTOM_SIGNAL_CORRELATION.get(sig_type, [])
        if not keywords:
            return False
        for sym in symptom_history:
            sev = sym.get("severity") or 0
            if sev >= min_severity:
                sym_text = (sym.get("symptom") or "").lower()
                if any(kw.lower() in sym_text for kw in keywords):
                    return True
        return False

    # ── Per-signal evaluation ────────────────────────────────────────────────
    worsening_types: list[str] = []

    for sig in current_signals:
        sig_type   = sig.get("signal_type", "")
        severity   = sig.get("severity", "low")
        hist       = signal_history.get(sig_type, {})
        recurrence = hist.get("recurrence_count", 1)
        esc_state  = hist.get("escalation_state", "active")
        trend      = hist.get("trend_direction", "stable")
        label      = _SIGNAL_LABEL.get(sig_type, sig_type)

        # Any signal → at least watch
        _promote("watch")

        # High severity
        if severity == "high":
            _promote("warning")
            reasons.append(f"{label} 嚴重度高")

        # Persistent (≥ 2 weekly windows)
        if recurrence >= 2:
            _promote("warning")
            reasons.append(f"{label} 已持續 {recurrence} 週")

        # Escalating trend
        if esc_state == "escalating":
            _promote("warning")
            reasons.append(f"{label} 呈惡化趨勢")

        # Mild symptom correlation (sev ≥ 6)
        if _has_symptom_correlation(sig_type, min_severity=6):
            _promote("warning")
            reasons.append(f"{label} 與症狀同步出現")

        # Track worsening signals for multi-signal urgent check
        if trend == "worsening":
            worsening_types.append(sig_type)

        # Urgent: high severity + recurrence ≥ 3
        if severity == "high" and recurrence >= 3:
            _promote("urgent")
            reasons.append(f"{label} 高風險且連續 {recurrence} 週異常")

        # Urgent: severe symptom correlation (sev ≥ 8) + medium/high signal
        if severity in ("high", "medium") and _has_symptom_correlation(sig_type, min_severity=8):
            _promote("urgent")
            reasons.append(f"{label} 與嚴重症狀同時惡化")

    # Urgent: ≥ 2 distinct signal types simultaneously worsening
    if len(worsening_types) >= 2:
        _promote("urgent")
        multi_label = " + ".join(
            _SIGNAL_LABEL.get(t, t) for t in worsening_types[:2]
        )
        reasons.append(f"多項裝置訊號同時惡化：{multi_label}")

    # ── Stale cap ───────────────────────────────────────────────────────────
    if all_stale and _ESCALATION_RANK[level] > _ESCALATION_RANK["watch"]:
        level = "watch"
        reasons.append("數據時效較舊，升級判斷受限")

    # ── Deduplicate reasons (preserve insertion order) ───────────────────────
    seen: set[str] = set()
    deduped: list[str] = []
    for r in reasons:
        if r not in seen:
            seen.add(r)
            deduped.append(r)

    # ── Recommended action ───────────────────────────────────────────────────
    if level == "urgent":
        recommended_action = "建議儘快諮詢醫師或回診評估目前健康狀況"
    elif level == "warning":
        recommended_action = "建議密切觀察，並於下次回診時與醫師討論"

    requires_follow_up = level in ("warning", "urgent")
    confidence = round(min(max(confidence, 0.20), 0.90), 2)

    return {
        "escalationLevel":    level,
        "reasons":            deduped[:5],
        "confidence":         confidence,
        "recommendedAction":  recommended_action,
        "requiresFollowUp":   requires_follow_up,
    }
