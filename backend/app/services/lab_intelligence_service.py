"""Lab Intelligence Service — P4 Report-to-Action Bridge
=========================================================
Pure-function module — no DB access.  All inputs come from
build_evidence_bundle() output.

Exports
-------
  detect_lab_abnormalities()  — groups lab_report_item evidence by marker,
                                 classifies severity, enriches with risk-alert
                                 corroboration, and produces actionable output.

Design contracts
----------------
  No hallucination — only processes items actually present in inputs.
  No medical diagnosis wording — all copy reviewed against non-clinical
    framing ("數值標記為異常" not "您罹患…").
  Confidence bounded [0.30, 0.88].
  Severity = "low" | "medium" | "high" only.
  rule_id format: "lab_abnormality_{sanitised_item_name}" — stable across
    requests for the same marker, used by the dedup layer in
    health_assistant_service.py.
  Sorting: high → medium → low, then recurrenceCount descending within tier.
"""
from __future__ import annotations

from typing import Any


# ---------------------------------------------------------------------------
# Abnormality classification
# ---------------------------------------------------------------------------

# Maps a substring of item_name → abnormality type code.
# First match wins (ordered by specificity preference).
_ITEM_TO_ABNORMALITY_TYPE: list[tuple[str, str]] = [
    # Fatty liver markers
    ("脂肪肝",       "fatty_liver_marker"),
    ("fatty_liver",  "fatty_liver_marker"),
    ("Fatty Liver",  "fatty_liver_marker"),
    # Kidney stone-related markers
    ("草酸",         "kidney_stone_related_marker"),
    ("Oxalate",      "kidney_stone_related_marker"),
    ("oxalate",      "kidney_stone_related_marker"),
    ("Calcium",      "kidney_stone_related_marker"),
    ("calcium",      "kidney_stone_related_marker"),
    ("腎結石",       "kidney_stone_related_marker"),
    ("Phosphate",    "kidney_stone_related_marker"),
    # Uric acid / gout (before generic lipid fallback)
    ("尿酸",         "uric_acid"),
    ("Uric",         "uric_acid"),
    # Lipids
    ("LDL",          "lipid_abnormality"),
    ("HDL",          "lipid_abnormality"),
    ("VLDL",         "lipid_abnormality"),
    ("膽固醇",        "lipid_abnormality"),
    ("三酸甘油酯",    "lipid_abnormality"),
    ("Cholesterol",  "lipid_abnormality"),
    ("TG",           "lipid_abnormality"),
    ("脂",           "lipid_abnormality"),
    ("HbA1c",       "glucose_abnormality"),
    ("A1c",         "glucose_abnormality"),
    ("糖化",        "glucose_abnormality"),
    ("血糖",        "glucose_abnormality"),
    ("Glucose",     "glucose_abnormality"),
    ("glucose",     "glucose_abnormality"),
    ("Insulin",     "glucose_abnormality"),
    # Blood pressure
    ("血壓",        "blood_pressure"),
    ("Systolic",    "blood_pressure"),
    ("Diastolic",   "blood_pressure"),
    ("BP",          "blood_pressure"),
    # Kidney
    ("creatinine",  "kidney_function"),
    ("Creatinine",  "kidney_function"),
    ("eGFR",        "kidney_function"),
    ("GFR",         "kidney_function"),
    ("肌酸酐",      "kidney_function"),
    ("BUN",         "kidney_function"),
    ("腎",          "kidney_function"),
    # Liver
    ("ALT",         "liver_function"),
    ("AST",         "liver_function"),
    ("GOT",         "liver_function"),
    ("GPT",         "liver_function"),
    ("ALP",         "liver_function"),
    ("γ-GT",        "liver_function"),
    ("GGT",         "liver_function"),
    ("肝",          "liver_function"),
    ("膽紅素",      "liver_function"),
    ("Bilirubin",   "liver_function"),
    # Thyroid
    ("TSH",         "thyroid_function"),
    ("甲狀腺",      "thyroid_function"),
    ("T3",          "thyroid_function"),
    ("T4",          "thyroid_function"),
    # Blood / CBC
    ("Hemoglobin",  "anemia_marker"),
    ("Haemoglobin", "anemia_marker"),
    ("血紅素",      "anemia_marker"),
    ("Hb",          "anemia_marker"),
    ("RBC",         "anemia_marker"),
    ("CBC",         "anemia_marker"),
    ("Ferritin",    "anemia_marker"),
    ("鐵",          "anemia_marker"),
    ("貧血",        "anemia_marker"),
    # Uric acid is listed earlier (above lipids) to prevent
    # "uric" being caught by a broader kidney keyword.
    # Inflammatory markers
    ("CRP",          "inflammation_marker"),
    ("ESR",          "inflammation_marker"),
    ("發炎",         "inflammation_marker"),
]


def _classify_abnormality_type(item_name: str) -> str:
    """Return the abnormality type code for an item_name string."""
    for keyword, abn_type in _ITEM_TO_ABNORMALITY_TYPE:
        if keyword in item_name:
            return abn_type
    return "lab_abnormality"


# ---------------------------------------------------------------------------
# Suggested actions (zh-TW, non-diagnosis)
# ---------------------------------------------------------------------------

_TYPE_TO_ACTION: dict[str, str] = {
    "lipid_abnormality":           "建議與醫師討論血脂管理，並評估飲食調整與運動計畫。",
    "glucose_abnormality":         "建議追蹤血糖或糖化數值，與醫師討論是否需要進一步評估。",
    "blood_pressure":              "建議監測血壓趨勢，並與醫師討論生活型態調整方向。",
    "kidney_function":             "建議增加飲水量並定期追蹤腎功能指標，必要時諮詢醫師。",
    "liver_function":              "建議定期追蹤肝功能指標，並避免對肝臟有負擔的習慣。",
    "fatty_liver_marker":          "建議與醫師討論肝臟指標，評估是否需要超音波追蹤，並調整飲食習慣。",
    "thyroid_function":            "建議與醫師討論甲狀腺指標，評估是否需要安排追蹤檢查。",
    "anemia_marker":               "建議與醫師討論血液指標，並評估是否需要進一步追蹤。",
    "uric_acid":                   "建議減少高普林食物攝取，並定期追蹤尿酸數值。",
    "kidney_stone_related_marker": "建議增加飲水量，並與醫師討論是否需要進一步泌尿系統評估。",
    "inflammation_marker":         "建議與醫師討論發炎指標，並評估是否需要進一步檢查。",
    "lab_abnormality":             "建議與醫師討論此項目異常，並安排複查以確認趨勢。",
}

# ---------------------------------------------------------------------------
# Abnormal flag → severity mapping
# ---------------------------------------------------------------------------

# Critical: independent of recurrence, immediately "high".
_CRITICAL_FLAGS: frozenset[str] = frozenset({
    "HH", "LL", "!!", "C", "CRITICAL", "PANIC",
    "critical", "panic", "CRISIS",
})

# Clearly abnormal — "medium" baseline.
_HIGH_FLAGS: frozenset[str] = frozenset({
    "H", "L", "A", "!", "ABNORMAL", "HIGH", "LOW",
    "high", "low", "abnormal",
})


def _flag_severity(flag: str | None) -> str:
    """Map a parser abnormal_flag string to 'low' | 'medium' | 'high'."""
    if not flag:
        return "low"
    normalised = flag.strip()
    if normalised in _CRITICAL_FLAGS or normalised.upper() in {f.upper() for f in _CRITICAL_FLAGS}:
        return "high"
    if normalised in _HIGH_FLAGS or normalised.upper() in {f.upper() for f in _HIGH_FLAGS}:
        return "medium"
    return "low"


# ---------------------------------------------------------------------------
# Severity ordering for sort
# ---------------------------------------------------------------------------

_SEV_ORDER: dict[str, int] = {"high": 0, "medium": 1, "low": 2}


def _max_severity(*severities: str) -> str:
    """Return the most severe among the given severity strings."""
    return min(severities, key=lambda s: _SEV_ORDER.get(s, 99))


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def detect_lab_abnormalities(
    lab_report_items: list[dict[str, Any]],
    risk_alerts: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Detect clinically meaningful lab abnormalities from evidence-bundle data.

    Parameters
    ----------
    lab_report_items:
        The ``lab_report_items`` list from build_evidence_bundle().
        Only rows with ``abnormal_flag`` set are included here (the service
        already filters in the DB query).
    risk_alerts:
        The ``risk_alerts`` list from build_evidence_bundle().
        Used to corroborate lab abnormalities and boost severity / confidence.

    Returns
    -------
    list[dict]  — one entry per unique ``item_name``, sorted high → low
                   severity then by recurrenceCount descending.

    Anti-hallucination contract
    ---------------------------
    Only items present in ``lab_report_items`` are ever returned.
    risk_alerts are used only for corroboration; they cannot introduce
    new lab item names.
    """
    if not lab_report_items:
        return []

    # ── Group by item_name ─────────────────────────────────────────────────
    from collections import defaultdict
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in lab_report_items:
        name = (item.get("item_name") or "").strip()
        if name:
            groups[name].append(item)

    # ── Build risk-alert lookup (rule_code prefix or item_name keyword) ────
    # We treat a risk_alert as corroborating a lab item if the alert's
    # rule_code or message contains the item_name keyword.
    def _alert_matches(item_name: str, alert: dict[str, Any]) -> bool:
        rule = (alert.get("rule_code") or "").lower()
        msg = (alert.get("message") or "").lower()
        name_lower = item_name.lower()
        return name_lower in rule or name_lower in msg

    # ── Process each unique marker ─────────────────────────────────────────
    results: list[dict[str, Any]] = []

    for item_name, occurrences in groups.items():
        recurrence_count = len(occurrences)

        # Most-recent occurrence first
        occurrences_sorted = sorted(
            occurrences,
            key=lambda o: (o.get("recency") or "older"),
        )
        # Use simple recency order: today < this_week < this_month < older
        _recency_rank = {"today": 0, "this_week": 1, "this_month": 2, "older": 3, "unknown": 4}
        occurrences_sorted = sorted(
            occurrences,
            key=lambda o: _recency_rank.get(o.get("recency") or "unknown", 4),
        )
        most_recent = occurrences_sorted[0]

        # ── Severity ───────────────────────────────────────────────────────
        # Base from abnormal_flag of most-recent occurrence
        flag_sev = _flag_severity(most_recent.get("abnormal_flag"))
        # Recurrence boost: ≥ 2 occurrences → at least medium
        if recurrence_count >= 2:
            recurrence_sev = "high" if recurrence_count >= 3 else "medium"
        else:
            recurrence_sev = "low"

        # Corroborating risk_alerts
        matched_alerts = [a for a in risk_alerts if _alert_matches(item_name, a)]
        if matched_alerts:
            alert_severities = [a.get("severity", "low") for a in matched_alerts]
            alert_sev = min(alert_severities, key=lambda s: _SEV_ORDER.get(s, 99))
        else:
            alert_sev = "low"

        severity = _max_severity(flag_sev, recurrence_sev, alert_sev)

        # ── Abnormality type & action ──────────────────────────────────────
        abnormality_type = _classify_abnormality_type(item_name)
        suggested_action = _TYPE_TO_ACTION.get(abnormality_type, _TYPE_TO_ACTION["lab_abnormality"])

        # ── Current value ──────────────────────────────────────────────────
        raw_num = most_recent.get("value_num")
        raw_text = most_recent.get("value_text")
        if raw_num is not None:
            current_value: float | str | None = float(raw_num)
        elif raw_text:
            current_value = raw_text
        else:
            current_value = None

        # ── whyDetected ────────────────────────────────────────────────────
        flag_str = most_recent.get("abnormal_flag") or "異常"
        unit_str = most_recent.get("unit") or ""
        ref_range_str = most_recent.get("ref_range") or ""

        val_display = ""
        if current_value is not None:
            val_display = f"，當前值 {current_value} {unit_str}".rstrip()

        ref_display = f"，參考範圍 {ref_range_str}" if ref_range_str else ""

        why_parts = [
            f"健檢報告顯示 {item_name} 數值標記為異常（{flag_str}）{val_display}{ref_display}"
        ]
        if recurrence_count > 1:
            why_parts.append(f"此項目在 {recurrence_count} 份報告中均出現異常")
        if matched_alerts:
            why_parts.append("同時有系統風險警示提醒此項目需要關注")

        why_detected = "；".join(why_parts) + "。"

        # Stale data warning appended to whyDetected when most-recent is old
        if most_recent.get("recency") == "older":
            why_detected = why_detected.rstrip("。") + "；此資料來自較早期的報告，建議與醫師確認是否需要重新檢測。"

        # ── Confidence ─────────────────────────────────────────────────────
        # Average parser_confidence from all occurrences, then apply boosts.
        raw_confidences = [
            float(o["confidence"])
            for o in occurrences
            if o.get("confidence") is not None
        ]
        base_conf = sum(raw_confidences) / len(raw_confidences) if raw_confidences else 0.70
        # Corroboration from risk_alert → +0.08
        if matched_alerts:
            base_conf = min(base_conf + 0.08, 0.88)
        # Recurrence → +0.05 per additional occurrence beyond first, max +0.10
        recurrence_boost = min((recurrence_count - 1) * 0.05, 0.10)
        # Stale report penalty: when the most-recent occurrence is "older",
        # data currency is low — reduce confidence to signal this.
        _RECENCY_PENALTY = {"today": 0.0, "this_week": 0.0, "this_month": 0.0, "older": -0.10}
        stale_penalty = _RECENCY_PENALTY.get(most_recent.get("recency") or "unknown", -0.05)
        confidence = min(max(base_conf + recurrence_boost + stale_penalty, 0.30), 0.88)

        # ── Evidence sources ───────────────────────────────────────────────
        evidence_sources: list[dict[str, Any]] = []
        for occ in occurrences_sorted:
            evidence_sources.append({
                "type": "lab_report_item",
                "id": occ.get("source_id"),
                "reportId": occ.get("report_id"),
                "summary": occ.get("summary", f"{item_name} 異常"),
                "recency": occ.get("recency"),
            })
        for alert in matched_alerts:
            evidence_sources.append({
                "type": "risk_alert",
                "id": alert.get("source_id"),
                "summary": alert.get("summary") or alert.get("title", ""),
                "recency": alert.get("recency"),
            })

        # ── rule_id (stable dedup key) ─────────────────────────────────────
        # Sanitise item_name: keep alphanumeric + CJK, replace rest with _
        safe_name = "".join(
            c if (c.isalnum() or "\u4e00" <= c <= "\u9fff") else "_"
            for c in item_name
        ).strip("_")
        rule_id = f"lab_abnormality_{safe_name}"

        results.append({
            "abnormalityType": abnormality_type,
            "severity": severity,
            "labItemName": item_name,
            "currentValue": current_value,
            "referenceRange": ref_range_str or None,
            "reportId": most_recent.get("report_id"),
            "detectedAt": most_recent.get("report_date"),
            "whyDetected": why_detected,
            "suggestedAction": suggested_action,
            "confidence": round(confidence, 3),
            "evidenceSources": evidence_sources,
            "recurrenceCount": recurrence_count,
            "rule_id": rule_id,
        })

    # ── Sort: high → medium → low, then recurrenceCount desc ──────────────
    results.sort(
        key=lambda r: (_SEV_ORDER.get(r["severity"], 99), -r["recurrenceCount"])
    )

    return results
