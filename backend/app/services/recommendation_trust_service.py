"""Recommendation Trust Service
================================
Scores each health recommendation for confidence and trustworthiness.

Scoring dimensions (max 100 pts total):
  F1  Primary-source quality  (max 30)  — evidence level of triggering source
  F2  Data recency            (max 20)  — how recent the primary evidence is
  F3  Evidence breadth        (max 15)  — distinct health domains available
  F4  Repeated signals        (max 10)  — same risk appearing in multiple records
  F5  Adherence history       (max 10)  — streak / active tracking of related actions
  F6  Outcome validation      (max 15)  — verified by past ActionOutcome records

confidence = total_pts / 100.0  (clamped 0.0–1.0)
level: ≥ 0.65 → "high" | ≥ 0.35 → "medium" | else → "low"

Anti-hallucination rules:
  - "verifiedByOutcome" is True ONLY when an outcome with label="improved" exists.
  - Deteriorated or no_change outcomes do NOT set verifiedByOutcome=True.
  - Missing data is surfaced explicitly in "limitations", never silently hidden.
"""
from __future__ import annotations

from typing import Any

# ---------------------------------------------------------------------------
# Scoring tables
# ---------------------------------------------------------------------------

_QUALITY_SCORE: dict[str, int] = {
    "lab_report_item":  30,   # Level A — objective lab result
    "risk_alert":       22,   # Level B — rule-based clinical trigger
    "insight":          18,   # Level B — system-generated pattern
    "health_metric":    18,   # Level B — objective measurement
    "long_term_symptom": 12,  # Level C — self-reported persistent symptom
    "decision_item":    15,   # Mixed   — decision engine output
    "missing_data":      0,   # No triggering evidence
}

_RECENCY_SCORE: dict[str, int] = {
    "today":      20,
    "this_week":  14,
    "this_month":  8,
    "older":       3,
    "unknown":     0,
}

# Human-readable reason strings (Chinese)
_QUALITY_REASON: dict[str, str] = {
    "lab_report_item":   "健檢報告異常項目（A 級客觀證據）",
    "risk_alert":        "主動風險警示（規則引擎確認）",
    "insight":           "系統健康洞察（B 級模式辨識）",
    "health_metric":     "客觀健康指標（B 級量測資料）",
    "long_term_symptom": "持續症狀記錄（C 級自述證據）",
    "decision_item":     "決策引擎優先推薦",
}

_RECENCY_REASON: dict[str, str] = {
    "today":      "資料為今日最新記錄",
    "this_week":  "資料為本週記錄",
    "this_month": "資料為本月記錄",
}

# Bundle domain key for each source_type
_SRC_TO_BUNDLE_KEY: dict[str, str] = {
    "lab_report_item":   "lab_report_items",
    "risk_alert":        "risk_alerts",
    "insight":           "insights",
    "long_term_symptom": "long_term_symptoms",
    "health_metric":     "health_metrics",
    "symptom":           "symptoms",
}

# Missing-data labels that don't need to surface as limitations (expected absence)
_TRIVIAL_MISSING: frozenset[str] = frozenset({
    "風險警示（目前無主動警示）",
    "健康洞察（建議先執行健康分析）",
})

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def recommendation_confidence_score(
    recommendation: dict[str, Any],
    evidence_bundle: dict[str, Any],
    outcomes: list[dict[str, Any]],
) -> dict[str, Any]:
    """Score a single recommendation for confidence and trust.

    Args:
        recommendation: One recommendation dict from get_action_recommendations().
        evidence_bundle: Full bundle from build_evidence_bundle().
        outcomes: bundle["outcomes"] — past ActionOutcome records for this person.

    Returns:
        dict with keys: confidence, level, reasons, limitations,
                        verifiedByOutcome, nextCheckInSuggestion
    """
    reasons: list[str] = []
    limitations: list[str] = []

    # ── F1: Primary-source quality ─────────────────────────────────────────
    src_type = recommendation.get("source_type", "missing_data")
    q_score = _QUALITY_SCORE.get(src_type, 0)
    q_reason = _QUALITY_REASON.get(src_type)
    if q_reason:
        reasons.append(q_reason)

    # ── F2: Data recency ───────────────────────────────────────────────────
    recency = _primary_source_recency(recommendation, evidence_bundle)
    r_score = _RECENCY_SCORE.get(recency, 0)
    r_reason = _RECENCY_REASON.get(recency)
    if r_reason:
        reasons.append(r_reason)
    elif recency in ("older", "unknown"):
        limitations.append("部分資料時效較舊，建議更新健康記錄")

    # ── F3: Evidence breadth ───────────────────────────────────────────────
    summary = evidence_bundle.get("summary", {})
    filled_domains = _count_filled_domains(summary)
    breadth_score = [0, 3, 6, 10, 13, 15][min(filled_domains, 5)]
    if filled_domains >= 3:
        reasons.append(f"共有 {filled_domains} 種健康資料類型支持此建議")
    elif filled_domains >= 2:
        reasons.append(f"有 {filled_domains} 種健康資料類型可供參考")
    else:
        limitations.append("健康資料類型不足，建議補充更多數據")

    # ── F4: Repeated signals ───────────────────────────────────────────────
    repeat_score = _compute_repeat_score(summary)
    if repeat_score >= 8:
        reasons.append("多筆記錄顯示相同健康風險，訊號一致性高")
    elif repeat_score >= 4:
        reasons.append("多筆資料呈現相似趨勢")

    # ── F5: Adherence history ──────────────────────────────────────────────
    adherence_score, streak, snooze_count = _compute_adherence_score(
        recommendation, evidence_bundle
    )
    if streak >= 7:
        reasons.append(f"已連續執行相關行動 {streak} 天")
    elif streak >= 3:
        reasons.append(f"已持續追蹤 {streak} 天，展現良好依從性")
    elif streak >= 1:
        reasons.append("已開始相關行動追蹤")
    if snooze_count > 0:
        limitations.append(f"此建議已被暫緩 {snooze_count} 次，請確認是否需要調整")

    # ── F6: Outcome validation ─────────────────────────────────────────────
    outcome_score, verified_by_outcome = _compute_outcome_score(outcomes)
    if verified_by_outcome:
        reasons.append("過去相似行動已驗證有改善效果（成效回饋：improved）")
    else:
        limitations.append("尚無成效驗證記錄，建議完成行動後觀察效果")

    # ── Missing data limitations ───────────────────────────────────────────
    for missing in evidence_bundle.get("missing_data", []):
        if missing not in _TRIVIAL_MISSING:
            limitations.append(f"缺少：{missing}")

    # ── Final score ────────────────────────────────────────────────────────
    total = q_score + r_score + breadth_score + repeat_score + adherence_score + outcome_score
    confidence = round(min(1.0, max(0.0, total / 100.0)), 2)
    level = _confidence_to_level(confidence)

    return {
        "confidence": confidence,
        "level": level,
        "reasons": reasons,
        "limitations": limitations,
        "verifiedByOutcome": verified_by_outcome,
        "nextCheckInSuggestion": _next_check_in(level),
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _primary_source_recency(rec: dict[str, Any], bundle: dict[str, Any]) -> str:
    """Look up the recency label of the recommendation's primary source in the bundle.

    Falls back to the most recent health metric recency if source not found.
    """
    src_type = rec.get("source_type", "")
    src_id = rec.get("source_id")

    if src_id:
        bundle_key = _SRC_TO_BUNDLE_KEY.get(src_type)
        if bundle_key:
            for item in bundle.get(bundle_key, []):
                if item.get("source_id") == src_id:
                    return item.get("recency", "unknown")

    # Fallback: use most recent health metric recency
    metrics = bundle.get("health_metrics", [])
    if metrics:
        return metrics[0].get("recency", "unknown")

    return "unknown"


def _count_filled_domains(summary: dict[str, Any]) -> int:
    """Count distinct evidence domains that have at least one record."""
    return sum([
        1 if summary.get("symptom_count", 0) > 0 else 0,
        1 if summary.get("metric_count", 0) > 0 else 0,
        1 if summary.get("abnormal_lab_count", 0) > 0 else 0,
        1 if summary.get("active_alert_count", 0) > 0 else 0,
        1 if summary.get("insight_count", 0) > 0 else 0,
    ])


def _compute_repeat_score(summary: dict[str, Any]) -> int:
    """Award points for multiple records in the same domain (repeated signals)."""
    score = 0
    if summary.get("metric_count", 0) >= 3:
        score += 5
    elif summary.get("metric_count", 0) >= 2:
        score += 3
    if summary.get("abnormal_lab_count", 0) >= 2:
        score += 5
    if summary.get("active_alert_count", 0) >= 2:
        score += 3
    return min(score, 10)


def _compute_adherence_score(
    rec: dict[str, Any],
    bundle: dict[str, Any],
) -> tuple[int, int, int]:
    """Return (score, streak_count, snooze_count) for the tracked action.

    Looks up the tracking action in bundle["actions"] by tracking_action_id.
    """
    tracking_id = rec.get("tracking_action_id")
    if not tracking_id:
        return 0, 0, 0

    for act in bundle.get("actions", []):
        if act.get("source_id") == tracking_id:
            streak = int(act.get("streak_count") or 0)
            snooze = int(act.get("snooze_count") or 0)
            if streak >= 7:
                base = 10
            elif streak >= 3:
                base = 7
            elif streak >= 1:
                base = 5
            else:
                base = 3  # tracking but no streak yet
            penalty = min(5, snooze * 2) if snooze > 0 else 0
            return max(0, base - penalty), streak, snooze

    return 0, 0, 0  # tracking_id set but action not found in bundle


def _compute_outcome_score(outcomes: list[dict[str, Any]]) -> tuple[int, bool]:
    """Return (score, verifiedByOutcome).

    verifiedByOutcome is True ONLY when outcome_label=="improved" exists.
    Deteriorated / no_change outcomes yield score=5 but verifiedByOutcome=False.
    """
    for o in outcomes:
        if o.get("outcome_label") == "improved":
            return 15, True
    if outcomes:
        # Measured but not improved — partial evidence credit, not verified
        return 5, False
    return 0, False


def _confidence_to_level(confidence: float) -> str:
    if confidence >= 0.65:
        return "high"
    if confidence >= 0.35:
        return "medium"
    return "low"


def _next_check_in(level: str) -> str:
    if level == "high":
        return "7 天後重新評估，目前建議可信度高，請持續執行"
    if level == "medium":
        return "3 天後回顧進度，建議補充更多健康資料以提升可信度"
    return "建議今日補充健康資料，待資料完整後再評估建議可信度"
