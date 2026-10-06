"""Symptom Intelligence Service
================================
Pure-function module — no DB access.  All inputs come from
build_evidence_bundle() output.

Exports
-------
  build_symptom_timeline()    — groups symptom entries by type, computes
                                trend, and links to device signals / labs
  detect_symptom_patterns()   — identifies clinically meaningful patterns

Design contracts
----------------
  - No hallucination: relatedDeviceSignals / relatedLabItems only include
    items actually present in the input arguments.
  - severityTrend == "unknown" when < 2 data points.
  - No pattern is emitted when there is no supporting data.
  - All confidence values are bounded [0.20, 0.90].
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


# ---------------------------------------------------------------------------
# Correlation maps
# ---------------------------------------------------------------------------

# Symptom name keyword → device signal types that may co-occur.
# Matching is substring-based (keyword in symptom_name).
_SYMPTOM_TO_SIGNALS: dict[str, list[str]] = {
    "頭痛":  ["elevated_resting_heart_rate", "abnormal_pulse_trend"],
    "頭暈":  ["elevated_resting_heart_rate", "low_activity_level"],
    "暈眩":  ["elevated_resting_heart_rate", "low_activity_level"],
    "心悸":  ["elevated_resting_heart_rate", "abnormal_pulse_trend"],
    "胸悶":  ["elevated_resting_heart_rate", "abnormal_pulse_trend"],
    "胸痛":  ["elevated_resting_heart_rate", "abnormal_pulse_trend"],
    "疲勞":  ["insufficient_sleep", "low_activity_level"],
    "疲倦":  ["insufficient_sleep", "low_activity_level"],
    "乏力":  ["insufficient_sleep", "low_activity_level"],
    "失眠":  ["insufficient_sleep"],
    "睡眠":  ["insufficient_sleep"],
    "呼吸":  ["low_activity_level"],
    "血壓":  ["elevated_resting_heart_rate"],
    "心跳":  ["elevated_resting_heart_rate", "abnormal_pulse_trend"],
    "心率":  ["elevated_resting_heart_rate", "abnormal_pulse_trend"],
    "活動":  ["low_activity_level"],
}

# Symptom name keyword → lab item_name keywords (for abnormal-flag correlation).
_SYMPTOM_TO_LAB: dict[str, list[str]] = {
    "血壓":   ["血壓", "BP", "Systolic", "Diastolic", "收縮壓", "舒張壓"],
    "高血壓":  ["血壓", "BP", "Systolic", "Diastolic"],
    "血糖":   ["血糖", "glucose", "Glucose", "HbA1c", "糖化"],
    "糖尿":   ["血糖", "glucose", "HbA1c"],
    "貧血":   ["Hb", "血紅素", "Hemoglobin", "CBC", "RBC"],
    "疲勞":   ["Hb", "血紅素", "TSH", "甲狀腺"],
    "疲倦":   ["Hb", "血紅素", "TSH", "甲狀腺"],
    "膽固醇":  ["LDL", "HDL", "Cholesterol", "膽固醇", "三酸甘油酯"],
    "肝":    ["ALT", "AST", "GOT", "GPT", "肝功能"],
    "腎":    ["creatinine", "GFR", "eGFR", "肌酸酐", "腎功能", "BUN"],
    "頭痛":   ["血壓", "BP"],
    "心悸":   ["ECG", "EKG", "心電"],
}

# Human-readable label per pattern type (zh-TW).
_PATTERN_LABEL: dict[str, str] = {
    "recurring_symptom":                "症狀反覆出現",
    "worsening_symptom":                "症狀持續惡化",
    "symptom_with_device_signal":       "症狀與裝置訊號同時發生",
    "symptom_with_lab_risk":            "症狀伴隨異常檢驗指標",
    "unresolved_high_severity_symptom": "高嚴重度症狀尚未緩解",
}

# Default suggested action per pattern type (zh-TW).
_PATTERN_ACTION: dict[str, str] = {
    "recurring_symptom":                "建議追蹤症狀模式，並在下次就醫時向醫師說明。",
    "worsening_symptom":                "建議密切觀察症狀變化，如持續惡化請諮詢醫師。",
    "symptom_with_device_signal":       "建議結合裝置數據一同評估，必要時諮詢醫師。",
    "symptom_with_lab_risk":            "建議將症狀與相關檢驗結果一同向醫師說明。",
    "unresolved_high_severity_symptom": "症狀嚴重度偏高且尚未緩解，建議儘快諮詢醫師。",
}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _parse_ts(ts: str | None) -> datetime | None:
    if not ts:
        return None
    try:
        dt = datetime.fromisoformat(ts)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return None


def _severity_trend(sorted_severities: list[int]) -> str:
    """Compute trend from list of severity ints ordered oldest → newest.

    Returns "worsening" / "improving" / "stable" / "unknown".
    Threshold: a mean difference > 1.5 points triggers a directional verdict.
    """
    n = len(sorted_severities)
    if n < 2:
        return "unknown"
    mid = n // 2
    older_avg = sum(sorted_severities[:mid]) / mid
    newer_avg = sum(sorted_severities[mid:]) / (n - mid)
    diff = newer_avg - older_avg
    if diff > 1.5:
        return "worsening"
    if diff < -1.5:
        return "improving"
    return "stable"


def _find_related_signals(
    symptom_name: str,
    device_signals: list[dict[str, Any]],
) -> list[str]:
    """Return signal_types from device_signals that correlate with symptom_name.

    Only returns signal types actually present in device_signals.  No
    hallucination — if a signal_type is not in the input it is never returned.
    """
    present_types: set[str] = {
        s["signal_type"] for s in device_signals if s.get("signal_type")
    }
    expected: set[str] = set()
    for keyword, signal_types in _SYMPTOM_TO_SIGNALS.items():
        if keyword in symptom_name:
            expected.update(signal_types)
    return sorted(expected & present_types)


def _find_related_labs(
    symptom_name: str,
    lab_report_items: list[dict[str, Any]],
) -> list[str]:
    """Return item_names from lab_report_items that correlate with symptom_name.

    Only includes items that have abnormal_flag set.  No hallucination.
    """
    expected_keywords: list[str] = []
    for keyword, lab_keys in _SYMPTOM_TO_LAB.items():
        if keyword in symptom_name:
            expected_keywords.extend(lab_keys)

    if not expected_keywords:
        return []

    result: list[str] = []
    for lab in lab_report_items:
        if not lab.get("abnormal_flag"):
            continue
        item_name: str = lab.get("item_name", "")
        for kw in expected_keywords:
            if kw.lower() in item_name.lower():
                if item_name not in result:
                    result.append(item_name)
                break
    return result


def _clamp(value: float, lo: float = 0.20, hi: float = 0.90) -> float:
    return max(lo, min(hi, value))


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_symptom_timeline(
    symptoms: list[dict[str, Any]],
    long_term_symptoms: list[dict[str, Any]],
    external_metrics: list[dict[str, Any]],  # accepted for interface contract; not used directly
    device_signals: list[dict[str, Any]],
    lab_report_items: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Group symptom entries by type and build per-symptom timeline items.

    Returns [] when no symptom data is available.

    Output shape per item::

        {
            "symptomType":          str,
            "firstSeenAt":          str | None,   # ISO timestamp
            "lastSeenAt":           str | None,
            "recurrenceCount":      int,
            "severityTrend":        "improving" | "stable" | "worsening" | "unknown",
            "recentSeverity":       int | None,   # 1-10
            "relatedDeviceSignals": list[str],    # signal_types actually present in input
            "relatedLabItems":      list[str],    # item_names actually present in input
            "evidenceSources":      list[EvidenceSource],
        }
    """
    all_symptoms = symptoms + long_term_symptoms
    if not all_symptoms:
        return []

    # Group by normalized symptom name
    groups: dict[str, list[dict[str, Any]]] = {}
    for sym in all_symptoms:
        name: str = (sym.get("symptom") or "").strip()
        if not name:
            continue
        groups.setdefault(name, []).append(sym)

    _epoch = datetime.min.replace(tzinfo=timezone.utc)

    timeline: list[dict[str, Any]] = []
    for symptom_name, entries in groups.items():
        # Sort oldest → newest for correct trend direction
        entries.sort(
            key=lambda e: _parse_ts(e.get("occurred_at")) or _epoch
        )

        severities: list[int] = [
            int(e["severity"]) for e in entries if e.get("severity") is not None
        ]
        valid_ts: list[datetime] = [
            t for t in (_parse_ts(e.get("occurred_at")) for e in entries) if t is not None
        ]

        first_seen = valid_ts[0].isoformat() if valid_ts else None
        last_seen  = valid_ts[-1].isoformat() if valid_ts else None
        recent_severity = (
            int(entries[-1]["severity"]) if entries[-1].get("severity") is not None else None
        )

        related_signals = _find_related_signals(symptom_name, device_signals)
        related_labs    = _find_related_labs(symptom_name, lab_report_items)

        evidence: list[dict[str, Any]] = [
            {
                "type":    "symptom",
                "id":      e.get("source_id", ""),
                "summary": e.get("summary", symptom_name),
            }
            for e in entries
        ]

        timeline.append({
            "symptomType":          symptom_name,
            "firstSeenAt":          first_seen,
            "lastSeenAt":           last_seen,
            "recurrenceCount":      len(entries),
            "severityTrend":        _severity_trend(severities),
            "recentSeverity":       recent_severity,
            "relatedDeviceSignals": related_signals,
            "relatedLabItems":      related_labs,
            "evidenceSources":      evidence,
        })

    # Surface most-recurring / highest-severity first
    timeline.sort(
        key=lambda t: (t["recurrenceCount"], t["recentSeverity"] or 0),
        reverse=True,
    )
    return timeline


def detect_symptom_patterns(
    symptom_timeline: list[dict[str, Any]],
    symptoms: list[dict[str, Any]],
    long_term_symptoms: list[dict[str, Any]],
    device_signals: list[dict[str, Any]],
    lab_report_items: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Detect clinically meaningful symptom patterns from the timeline.

    Returns [] when no data is available.  No pattern is emitted without
    supporting evidence in the inputs.

    Pattern types
    -------------
    recurring_symptom               recurrenceCount ≥ 3
    worsening_symptom               severityTrend == "worsening"
    symptom_with_device_signal      relatedDeviceSignals non-empty
    symptom_with_lab_risk           relatedLabItems non-empty
    unresolved_high_severity_symptom recentSeverity ≥ 8

    Output shape per pattern::

        {
            "patternType":          str,
            "severity":             "low" | "medium" | "high",
            "symptomType":          str,
            "label":                str,          # zh-TW human label
            "whyDetected":          str,
            "confidence":           float,        # [0.20, 0.90]
            "suggestedAction":      str | None,
            "evidenceSources":      list[EvidenceSource],
            "relatedDeviceSignals": list[str],
            "relatedLabItems":      list[str],
        }
    """
    if not symptom_timeline:
        return []

    patterns: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()  # (pattern_type, symptom_type)

    for item in symptom_timeline:
        stype      = item["symptomType"]
        recurrence = item["recurrenceCount"]
        trend      = item["severityTrend"]
        sev_val    = item.get("recentSeverity") or 0
        r_signals  = item.get("relatedDeviceSignals", [])
        r_labs     = item.get("relatedLabItems", [])
        evidence   = item.get("evidenceSources", [])

        # ── recurring_symptom ────────────────────────────────────────────
        if recurrence >= 3 and ("recurring_symptom", stype) not in seen:
            seen.add(("recurring_symptom", stype))
            sev = "high" if sev_val >= 7 else "medium"
            conf = _clamp(0.60 + recurrence * 0.05)
            patterns.append(_make_pattern(
                pattern_type="recurring_symptom",
                severity=sev,
                symptom_type=stype,
                why=f"症狀「{stype}」在追蹤期間出現 {recurrence} 次",
                confidence=conf,
                evidence=evidence,
                related_signals=r_signals,
                related_labs=r_labs,
            ))

        # ── worsening_symptom ────────────────────────────────────────────
        if trend == "worsening" and ("worsening_symptom", stype) not in seen:
            seen.add(("worsening_symptom", stype))
            sev = "high" if sev_val >= 7 else "medium"
            patterns.append(_make_pattern(
                pattern_type="worsening_symptom",
                severity=sev,
                symptom_type=stype,
                why=f"症狀「{stype}」嚴重度呈上升趨勢",
                confidence=0.75,
                evidence=evidence,
                related_signals=r_signals,
                related_labs=r_labs,
            ))

        # ── symptom_with_device_signal ───────────────────────────────────
        if r_signals and ("symptom_with_device_signal", stype) not in seen:
            seen.add(("symptom_with_device_signal", stype))
            sig_label = "、".join(r_signals[:2])
            conf = _clamp(0.65 + len(r_signals) * 0.05)
            sev = "high" if sev_val >= 7 else "medium"
            patterns.append(_make_pattern(
                pattern_type="symptom_with_device_signal",
                severity=sev,
                symptom_type=stype,
                why=f"症狀「{stype}」與裝置訊號（{sig_label}）同時存在",
                confidence=conf,
                evidence=evidence,
                related_signals=r_signals,
                related_labs=r_labs,
            ))

        # ── symptom_with_lab_risk ────────────────────────────────────────
        if r_labs and ("symptom_with_lab_risk", stype) not in seen:
            seen.add(("symptom_with_lab_risk", stype))
            lab_label = "、".join(r_labs[:2])
            patterns.append(_make_pattern(
                pattern_type="symptom_with_lab_risk",
                severity="high",
                symptom_type=stype,
                why=f"症狀「{stype}」伴隨異常檢驗指標（{lab_label}）",
                confidence=0.80,
                evidence=evidence,
                related_signals=r_signals,
                related_labs=r_labs,
            ))

        # ── unresolved_high_severity_symptom ─────────────────────────────
        if sev_val >= 8 and ("unresolved_high_severity_symptom", stype) not in seen:
            seen.add(("unresolved_high_severity_symptom", stype))
            patterns.append(_make_pattern(
                pattern_type="unresolved_high_severity_symptom",
                severity="high",
                symptom_type=stype,
                why=f"症狀「{stype}」近期嚴重度 {sev_val}/10，尚未緩解",
                confidence=0.85,
                evidence=evidence,
                related_signals=r_signals,
                related_labs=r_labs,
            ))

    # Sort: high > medium > low, then confidence desc
    _sev_rank = {"high": 2, "medium": 1, "low": 0}
    patterns.sort(
        key=lambda p: (_sev_rank.get(p["severity"], 0), p["confidence"]),
        reverse=True,
    )
    return patterns


# ---------------------------------------------------------------------------
# Private builder
# ---------------------------------------------------------------------------

def _make_pattern(
    *,
    pattern_type: str,
    severity: str,
    symptom_type: str,
    why: str,
    confidence: float,
    evidence: list[dict[str, Any]],
    related_signals: list[str],
    related_labs: list[str],
) -> dict[str, Any]:
    """Assemble a SymptomPattern dict."""
    # Cross-source evidence boosts confidence slightly
    if related_signals and related_labs:
        confidence = _clamp(confidence + 0.05)
    return {
        "patternType":          pattern_type,
        "severity":             severity,
        "symptomType":          symptom_type,
        "label":                _PATTERN_LABEL.get(pattern_type, pattern_type),
        "whyDetected":          why,
        "confidence":           round(_clamp(confidence), 3),
        "suggestedAction":      _PATTERN_ACTION.get(pattern_type),
        "evidenceSources":      evidence,
        "relatedDeviceSignals": related_signals,
        "relatedLabItems":      related_labs,
    }
