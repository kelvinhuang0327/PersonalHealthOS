"""Device Signal Detection Service
====================================
Pure-function analysis layer that converts raw external_metrics items
(from the evidence bundle) into structured DeviceSignal objects.

No database access — operates only on pre-fetched data, ensuring
the detection logic is fully testable without a live DB.

Signals supported
-----------------
  elevated_resting_heart_rate
      heart_rate ≥ 90 bpm from an external device source.
  abnormal_pulse_trend
      Heart rate values across ≥ 3 readings showing a consistent
      ascending pattern.
  low_sleep_duration
      sleep_hours < 7.0 h from an external device source.
  reduced_activity
      steps < 5 000 from an external device source.
  unstable_spo2
      Placeholder — no spo2 column exists in HealthMetric yet.
      Always returns no signal; will never hallucinate data.

Staleness rule
--------------
  Any reading with ``freshness == "stale"`` has its confidence
  multiplied by ``_STALE_CONFIDENCE_FACTOR`` (0.70).

Repeated-abnormal escalation
-----------------------------
  If the same signal type is backed by ≥ 3 abnormal readings,
  severity is escalated to "high".
"""
from __future__ import annotations

from typing import Any

# ---------------------------------------------------------------------------
# Thresholds
# ---------------------------------------------------------------------------

_HR_CRITICAL  = 110   # bpm — high severity
_HR_HIGH      = 100   # bpm — medium severity
_HR_ELEVATED  =  90   # bpm — low severity (notable)

_SLEEP_CRITICAL = 6.0  # hours — high severity
_SLEEP_SHORT    = 7.0  # hours — medium severity

_STEPS_CRITICAL = 2_000   # steps — high severity (very sedentary)
_STEPS_LOW      = 5_000   # steps — medium severity

# Confidence penalty applied to stale readings (> 24 h old)
_STALE_CONFIDENCE_FACTOR = 0.70

# Base confidence for device-sourced signals before staleness adjustment
_BASE_CONFIDENCE = 0.82


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _severity_from_hr(hr: float) -> str:
    if hr >= _HR_CRITICAL:
        return "high"
    if hr >= _HR_HIGH:
        return "medium"
    return "low"


def _severity_from_sleep(h: float) -> str:
    if h < _SLEEP_CRITICAL:
        return "high"
    if h < _SLEEP_SHORT:
        return "medium"
    return "low"


def _severity_from_steps(s: int) -> str:
    if s < _STEPS_CRITICAL:
        return "high"
    if s < _STEPS_LOW:
        return "medium"
    return "low"


def _confidence(freshness: str, base: float = _BASE_CONFIDENCE) -> float:
    """Return confidence score, reduced for stale readings."""
    raw = base * _STALE_CONFIDENCE_FACTOR if freshness == "stale" else base
    return round(raw, 3)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def detect_device_signals(
    external_metrics: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Analyse ``external_metrics`` and return detected DeviceSignal dicts.

    If ``external_metrics`` is empty or contains no relevant values,
    returns ``[]`` — never hallucinating a signal with no data.

    Parameters
    ----------
    external_metrics:
        The list of enriched external-metric items from the evidence bundle.
        Each item must include the raw numeric fields added by
        ``build_evidence_bundle``:
        ``heart_rate``, ``sleep_hours``, ``steps``,
        ``systolic_bp``, ``diastolic_bp``, ``freshness``.

    Returns
    -------
    list[dict]
        Each element matches the DeviceSignal shape::

            {
              "signal_type":      str,
              "severity":         "low" | "medium" | "high",
              "metric_type":      str,
              "current_value":    float,
              "baseline_value":   float | None,
              "trend":            str | None,
              "why_detected":     str,
              "suggested_action": str | None,
              "confidence":       float,
              "freshness":        "fresh" | "stale" | "unknown",
            }
    """
    if not external_metrics:
        return []

    signals: list[dict[str, Any]] = []

    # ── Collect per-metric time-ordered readings ──────────────────────────
    # external_metrics is already ordered desc(recorded_at) from the bundle.
    hr_readings:    list[tuple[float, str]] = []   # (value, freshness)
    sleep_readings: list[tuple[float, str]] = []
    step_readings:  list[tuple[int,   str]] = []

    for em in external_metrics:
        fr = em.get("freshness", "stale")
        hr = em.get("heart_rate")
        if hr is not None:
            hr_readings.append((float(hr), fr))
        sl = em.get("sleep_hours")
        if sl is not None:
            sleep_readings.append((float(sl), fr))
        st = em.get("steps")
        if st is not None:
            step_readings.append((int(st), fr))

    # ── elevated_resting_heart_rate ───────────────────────────────────────
    elevated_hr = [(v, f) for v, f in hr_readings if v >= _HR_ELEVATED]
    if elevated_hr:
        latest_hr, latest_fr = elevated_hr[0]
        severity = _severity_from_hr(latest_hr)
        # Repeated abnormal readings → escalate
        if len(elevated_hr) >= 3 and severity != "high":
            severity = "high"

        trend = "elevated" if len(elevated_hr) == 1 else "persistently_elevated"
        signals.append({
            "signal_type":      "elevated_resting_heart_rate",
            "severity":         severity,
            "metric_type":      "heart_rate",
            "current_value":    latest_hr,
            "baseline_value":   None,
            "trend":            trend,
            "why_detected": (
                f"靜息心率 {latest_hr:.0f} bpm 超過正常範圍（< 90 bpm），"
                f"共 {len(elevated_hr)} 筆外部裝置記錄異常。"
            ),
            "suggested_action": (
                "減少咖啡因攝取，增加有氧運動，並密切監測心率趨勢；若持續偏高請就醫。"
            ),
            "confidence": _confidence(latest_fr),
            "freshness":  latest_fr,
        })

    # ── abnormal_pulse_trend ──────────────────────────────────────────────
    if len(hr_readings) >= 3:
        # Readings are most-recent-first; ascending trend means values are
        # decreasing as we iterate (index 0 = newest = highest).
        window = [v for v, _ in hr_readings[:5]]
        # Check that each successive value is lower (desc order → ascending trend)
        ascending = all(window[i] >= window[i + 1] for i in range(len(window) - 1))
        oldest_val = window[-1]
        if ascending and oldest_val > 60:  # non-trivial baseline, not already 0 bpm
            latest_hr2, latest_fr2 = hr_readings[0]
            # Only emit if not already captured by elevated_resting_hr signal
            already_elevated = any(
                s["signal_type"] == "elevated_resting_heart_rate" for s in signals
            )
            if not already_elevated or latest_hr2 < _HR_ELEVATED:
                signals.append({
                    "signal_type":      "abnormal_pulse_trend",
                    "severity":         "medium",
                    "metric_type":      "heart_rate",
                    "current_value":    latest_hr2,
                    "baseline_value":   float(oldest_val),
                    "trend":            "increasing",
                    "why_detected": (
                        f"過去 {len(window)} 筆心率記錄呈持續上升趨勢，"
                        f"從 {oldest_val:.0f} 升至 {latest_hr2:.0f} bpm。"
                    ),
                    "suggested_action": (
                        "觀察心率趨勢，避免過度勞累或壓力，必要時諮詢醫師。"
                    ),
                    "confidence": _confidence(latest_fr2, 0.75),
                    "freshness":  latest_fr2,
                })

    # ── low_sleep_duration ────────────────────────────────────────────────
    short_sleep = [(v, f) for v, f in sleep_readings if v < _SLEEP_SHORT]
    if short_sleep:
        latest_sl, latest_fr_sl = short_sleep[0]
        severity = _severity_from_sleep(latest_sl)
        if len(short_sleep) >= 3 and severity != "high":
            severity = "high"

        trend = "below_target" if len(short_sleep) == 1 else "chronically_short"
        signals.append({
            "signal_type":      "low_sleep_duration",
            "severity":         severity,
            "metric_type":      "sleep_hours",
            "current_value":    latest_sl,
            "baseline_value":   None,
            "trend":            trend,
            "why_detected": (
                f"裝置記錄睡眠 {latest_sl:.1f} 小時（建議 ≥ 7 小時），"
                f"共 {len(short_sleep)} 筆記錄低於閾值。"
            ),
            "suggested_action": (
                "建立規律睡眠時間，睡前減少螢幕使用，並評估睡眠環境。"
            ),
            "confidence": _confidence(latest_fr_sl),
            "freshness":  latest_fr_sl,
        })

    # ── reduced_activity ──────────────────────────────────────────────────
    low_steps = [(v, f) for v, f in step_readings if v < _STEPS_LOW]
    if low_steps:
        latest_st, latest_fr_st = low_steps[0]
        severity = _severity_from_steps(latest_st)
        if len(low_steps) >= 3 and severity != "high":
            severity = "high"

        trend = "below_target" if len(low_steps) == 1 else "chronically_low"
        signals.append({
            "signal_type":      "reduced_activity",
            "severity":         severity,
            "metric_type":      "steps",
            "current_value":    float(latest_st),
            "baseline_value":   None,
            "trend":            trend,
            "why_detected": (
                f"裝置記錄步數 {latest_st:,} 步（建議 ≥ 5000 步），"
                f"共 {len(low_steps)} 筆記錄低於閾值。"
            ),
            "suggested_action": (
                "嘗試每天至少步行 30 分鐘，或使用樓梯代替電梯。"
            ),
            "confidence": _confidence(latest_fr_st),
            "freshness":  latest_fr_st,
        })

    # ── unstable_spo2 ─────────────────────────────────────────────────────
    # SpO₂ is not available in the current HealthMetric schema.
    # This block intentionally returns nothing rather than hallucinating data.
    # When the spo2 column is added to the model, implement detection here.

    return signals
