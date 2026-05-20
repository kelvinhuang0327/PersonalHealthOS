"""Adaptive Recommendation Scoring — P6 Personalization
=========================================================
Pure-function module (no DB access) that adjusts recommendation priorities
and confidence scores based on:

  - PersonalizationProfile (acted / ignored / engagement)
  - Notification history (snooze / ignore frequency)
  - Outcome feedback (historical improvement evidence)

Public API
----------
adaptive_recommendation_score(
    recommendations, notification_history, outcome_summaries, profile
) -> list[dict]
    Returns the same recommendation list with adjusted fields:
      adjusted_confidence   — personalized confidence score
      personalization_reasons — list[str] explaining each adjustment
    Original dict is NOT mutated; a new dict is returned per item.

Design contracts
----------------
- "urgent" source or device_escalation → bypass all personalization suppression
- Ignored category (ignore_count >= 4) → hard floor at "low" priority, confidence 0.20
- No personalization data → recommendations returned unchanged (safe fallback)
- All confidence values clamped to [0.20, 0.95]
- All priority downgrades use the same _PRIORITY_ORDER as notification_intelligence_service
"""
from __future__ import annotations

from typing import Any

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_PRIORITY_ORDER = ["low", "medium", "high", "urgent"]
_PRIORITY_RANK: dict[str, int] = {p: i for i, p in enumerate(_PRIORITY_ORDER)}

_MIN_CONFIDENCE = 0.20
_MAX_CONFIDENCE = 0.95

# Confidence adjustments per signal
_ACT_BOOST_PER_COUNT = 0.07          # +7% per act, max 3 acts counted
_MAX_ACT_BOOST = 0.15                # cap total act boost
_IGNORE_PENALTY_PER_COUNT = 0.05     # -5% per ignore
_MAX_IGNORE_PENALTY = 0.25           # cap total ignore penalty
_OUTCOME_SUCCESS_BOOST = 0.10        # +10% for verified improved outcome

# Ignore count that triggers a priority downgrade (in addition to confidence penalty)
_IGNORE_DOWNGRADE_THRESHOLD = 2

# Ignore count that triggers hard-floor to "low" priority
_IGNORE_HARD_FLOOR_THRESHOLD = 5

# Engagement score below which priority is capped at "medium"
_LOW_ENGAGEMENT_THRESHOLD = 0.30

# Source types that always bypass personalization suppression
_BYPASS_SOURCE_TYPES: frozenset[str] = frozenset({"device_escalation"})


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _downgrade_priority(priority: str) -> str:
    idx = _PRIORITY_RANK.get(priority, 0)
    return _PRIORITY_ORDER[max(0, idx - 1)]


def _clamp_conf(v: float) -> float:
    return max(_MIN_CONFIDENCE, min(_MAX_CONFIDENCE, v))


def _infer_category(rec: dict[str, Any]) -> str:
    """Extract a stable category key from a recommendation dict."""
    return (
        rec.get("source_type")
        or rec.get("action_type")
        or rec.get("category")
        or "unknown"
    )


def _outcome_improved(category: str, outcome_summaries: list[dict[str, Any]]) -> bool:
    """Return True if any outcome in the list shows 'improved' for this category."""
    for o in outcome_summaries:
        if o.get("outcome_status") == "improved" or o.get("outcome_label") == "improved":
            action_cat = (
                o.get("source_type")
                or o.get("action_type")
                or o.get("category")
                or ""
            )
            if not action_cat or action_cat == category:
                return True
    return False


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def adaptive_recommendation_score(
    recommendations: list[dict[str, Any]],
    notification_history: list[dict[str, Any]] | None = None,
    outcome_summaries: list[dict[str, Any]] | None = None,
    profile: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Adjust recommendation priority + confidence using personalization signals.

    Parameters
    ----------
    recommendations:
        List of recommendation dicts (any schema with at least 'priority' and
        'confidence' keys).
    notification_history:
        List of notification history entries (from load_notification_history()).
        Used as fallback signal source when profile is sparse.
    outcome_summaries:
        List of outcome feedback dicts (from compare_expected_vs_actual_outcome()).
    profile:
        Serialized PersonalizationProfile dict (from profile_to_dict()).
        If None, a safe neutral fallback is used.

    Returns
    -------
    list[dict] — new dicts (originals are not mutated) with:
      adjusted_confidence      float
      personalization_reasons  list[str]
      priority                 may be adjusted
    """
    notification_history = notification_history or []
    outcome_summaries = outcome_summaries or []
    profile = profile or {}

    acted_cats: dict[str, int] = profile.get("acted_categories") or {}
    ignored_cats: dict[str, int] = profile.get("ignored_categories") or {}
    high_response: set[str] = set(profile.get("high_response_categories") or [])
    engagement: float = float(profile.get("engagement_score") or 0.5)

    result: list[dict[str, Any]] = []

    for raw_rec in recommendations:
        rec = dict(raw_rec)
        reasons: list[str] = []
        category = _infer_category(rec)
        orig_conf = float(rec.get("confidence") or 0.5)
        orig_priority = str(rec.get("priority") or "medium")
        adj_conf = orig_conf

        # ── BYPASS: urgent or critical source type ────────────────────────
        is_bypass = (
            orig_priority == "urgent"
            or category in _BYPASS_SOURCE_TYPES
        )
        if is_bypass:
            rec["adjusted_confidence"] = _clamp_conf(adj_conf)
            rec["personalization_reasons"] = ["緊急提醒：不受個人化調整影響"]
            result.append(rec)
            continue

        # ── Boost: acted category ─────────────────────────────────────────
        act_count = acted_cats.get(category, 0)
        if act_count > 0:
            boost = min(act_count * _ACT_BOOST_PER_COUNT, _MAX_ACT_BOOST)
            adj_conf += boost
            reasons.append(f"您曾採取此類建議行動（{act_count} 次），信心度提升")

        # ── Boost: high-response category ────────────────────────────────
        if category in high_response and act_count == 0:
            adj_conf += 0.08
            reasons.append("此類提醒您持續有正面回應")

        # ── Boost: verified outcome improvement ──────────────────────────
        if _outcome_improved(category, outcome_summaries):
            adj_conf += _OUTCOME_SUCCESS_BOOST
            reasons.append("過去類似建議已確認改善健康指標")

        # ── Penalty: ignored category ─────────────────────────────────────
        ignore_count = ignored_cats.get(category, 0)
        if ignore_count >= _IGNORE_DOWNGRADE_THRESHOLD:
            penalty = min(ignore_count * _IGNORE_PENALTY_PER_COUNT, _MAX_IGNORE_PENALTY)
            adj_conf -= penalty
            reasons.append(f"此類提醒您曾多次略過（{ignore_count} 次），信心度調降")

            # Hard-floor: too many ignores → cap at "low"
            if ignore_count >= _IGNORE_HARD_FLOOR_THRESHOLD:
                rec["priority"] = "low"
                reasons.append("忽略次數過多，已降至最低優先度")
            else:
                rec["priority"] = _downgrade_priority(orig_priority)

        # ── Penalty: low engagement → cap priority at medium ──────────────
        if engagement < _LOW_ENGAGEMENT_THRESHOLD:
            curr_rank = _PRIORITY_RANK.get(rec.get("priority", orig_priority), 0)
            if curr_rank > _PRIORITY_RANK["medium"]:
                rec["priority"] = "medium"
                reasons.append("目前提醒互動較少，已調整為中等提醒強度")

        rec["adjusted_confidence"] = _clamp_conf(adj_conf)
        rec["personalization_reasons"] = reasons
        result.append(rec)

    # Re-sort: priority desc, then adjusted_confidence desc
    return sorted(
        result,
        key=lambda x: (
            _PRIORITY_RANK.get(x.get("priority", "medium"), 1),
            x.get("adjusted_confidence", x.get("confidence", 0.5)),
        ),
        reverse=True,
    )
