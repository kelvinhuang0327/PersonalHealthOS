"""Narrative Intelligence Service — P7.2 Cross-Period Health Reasoning
======================================================================
Higher-level reasoning over multiple stored narrative memories.

Builds on P7 NarrativeMemoryResult dicts from narrative_memory_service.
All functions are pure (no DB access) — fast, deterministic, testable.

Anti-hallucination rules
--------------------------
- overallTrend requires evidence from ≥ 2 distinct period memories
- sustainedImprovements must appear in ≥ 2 period memories
- longTermRisks must appear in ≥ 2 distinct period memories
- repeatedIgnoredRisks must appear in ignoredItems of ≥ 2 memories
- carryOverRecommendations limited to max_carry = 3 per item (prevent loops)
- All limitations explain why a conclusion is absent
- No medical diagnoses — factual observations only

Public API
----------
build_cross_period_health_reasoning()  — aggregate reasoning from multiple period memories
rank_narrative_insights()              — rank insights by severity / impact / evidence
generate_carry_over_recommendations()  — produce actionable carry-over items
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Any

# ---------------------------------------------------------------------------
# Type aliases (documented shapes)
# ---------------------------------------------------------------------------

NarrativeMemoryResult = dict[str, Any]
CrossPeriodReasoning = dict[str, Any]
"""
{
  overallTrend: "improving" | "stable" | "mixed" | "worsening"
  longTermRisks: list[str]
  sustainedImprovements: list[str]
  unstableAreas: list[str]
  repeatedIgnoredRisks: list[str]
  effectiveLongTermActions: list[str]
  carryOverRecommendations: list[str]
  confidence: float
  limitations: list[str]
}
"""

RankedInsight = dict[str, Any]
"""{ item, category, score, reason }"""

CarryOverRecommendation = dict[str, Any]
"""{ text, evidence_source, urgency, carry_over_count }"""

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_MIN_PERIOD_COUNT = 2       # need ≥ 2 periods to assert cross-period trend
_MIN_SUSTAINED = 2          # need ≥ 2 occurrences for "sustained"
_MAX_CARRY_OVER = 3         # prevent infinite carry-over loops
_STALE_THRESHOLD_DAYS = 30  # memory older than this lowers insight confidence

_CATEGORY_BASE_SCORES: dict[str, float] = {
    "long_term_risk": 0.70,
    "repeated_ignored_risk": 0.65,
    "unstable_area": 0.55,
    "carry_over": 0.50,
    "sustained_improvement": 0.45,
    "effective_action": 0.35,
}


# ---------------------------------------------------------------------------
# Task 1 — Cross-Period Health Reasoning
# ---------------------------------------------------------------------------

def build_cross_period_health_reasoning(
    daily_memories: list[NarrativeMemoryResult],
    weekly_memories: list[NarrativeMemoryResult],
    monthly_memories: list[NarrativeMemoryResult],
    recommendations: list[Any] | None = None,
    outcome_feedback: list[Any] | None = None,
    notification_history: list[dict[str, Any]] | None = None,
) -> CrossPeriodReasoning:
    """Aggregate cross-period health reasoning from stored narrative memories.

    All inputs are optional — missing data is explained in limitations.
    Never emits medical diagnoses or speculative health conclusions.

    Trend assessment requires ≥ 2 distinct period memories to avoid
    single-data-point false positives.
    """
    all_memories: list[NarrativeMemoryResult] = (
        daily_memories + weekly_memories + monthly_memories
    )
    limitations: list[str] = []

    if not all_memories:
        return {
            "overallTrend": "stable",
            "longTermRisks": [],
            "sustainedImprovements": [],
            "unstableAreas": [],
            "repeatedIgnoredRisks": [],
            "effectiveLongTermActions": [],
            "carryOverRecommendations": [],
            "confidence": 0.0,
            "limitations": ["尚無跨期間記憶資料，無法進行長期趨勢分析。"],
        }

    # ── Collect evidence across all period memories ──────────────────────────
    improving_counter: Counter[str] = Counter()
    worsening_counter: Counter[str] = Counter()
    risk_counter: Counter[str] = Counter()
    ignored_counter: Counter[str] = Counter()
    effective_counter: Counter[str] = Counter()

    for mem in all_memories:
        for item in mem.get("improvingItems", []):
            improving_counter[item] += 1
        for item in mem.get("worseningItems", []):
            worsening_counter[item] += 1
        for item in mem.get("repeatedRisks", []):
            risk_counter[item] += 1
        for item in mem.get("ignoredItems", []):
            ignored_counter[item] += 1
        for item in mem.get("effectiveActions", []):
            effective_counter[item] += 1

    total_periods = len(all_memories)

    # ── Overall trend ────────────────────────────────────────────────────────
    total_improving = sum(improving_counter.values())
    total_worsening = sum(worsening_counter.values())

    if total_periods < _MIN_PERIOD_COUNT:
        limitations.append(
            f"僅有 {total_periods} 個期間記憶，"
            f"跨期趨勢分析需要至少 {_MIN_PERIOD_COUNT} 個期間。"
        )
        overall_trend = "stable"
    elif total_improving == 0 and total_worsening == 0:
        overall_trend = "stable"
    elif total_improving > 0 and total_worsening == 0:
        overall_trend = "improving"
    elif total_worsening > 0 and total_improving == 0:
        overall_trend = "worsening"
    elif total_improving >= total_worsening * 2:
        overall_trend = "improving"
    elif total_worsening >= total_improving * 2:
        overall_trend = "worsening"
    else:
        overall_trend = "mixed"

    # ── Long-term risks — appear in ≥ 2 distinct memories ───────────────────
    long_term_risks: list[str] = [
        item for item, cnt in risk_counter.items() if cnt >= _MIN_SUSTAINED
    ]
    # Also include items that are worsening in ≥ 2 memories
    for item, cnt in worsening_counter.items():
        if cnt >= _MIN_SUSTAINED and item not in long_term_risks:
            long_term_risks.append(item)

    if not long_term_risks and total_periods >= _MIN_PERIOD_COUNT:
        limitations.append("跨期間未發現持續性長期風險。")

    # ── Sustained improvements — appear in ≥ 2 memories ────────────────────
    sustained_improvements: list[str] = [
        item for item, cnt in improving_counter.items() if cnt >= _MIN_SUSTAINED
    ]

    # ── Unstable areas — appear in BOTH improving and worsening ─────────────
    unstable_areas: list[str] = sorted(
        set(improving_counter.keys()) & set(worsening_counter.keys())
    )

    # ── Repeated ignored risks — appear in ≥ 2 memories ─────────────────────
    repeated_ignored_risks: list[str] = [
        item for item, cnt in ignored_counter.items() if cnt >= _MIN_SUSTAINED
    ]

    # ── Effective long-term actions — appear in ≥ 2 memories ────────────────
    effective_long_term_actions: list[str] = [
        item for item, cnt in effective_counter.items() if cnt >= _MIN_SUSTAINED
    ]

    if not effective_long_term_actions:
        limitations.append("尚未發現跨期間持續有效的行動。")

    # ── Carry-over recommendations ───────────────────────────────────────────
    # Items in long_term_risks or repeated_ignored_risks not already sustained-improved
    improved_set = set(sustained_improvements)
    carry_over_candidates = set(long_term_risks) | set(repeated_ignored_risks)
    carry_over_raw = [c for c in carry_over_candidates if c not in improved_set]
    carry_over_recommendations = sorted(carry_over_raw)[:5]

    # ── Confidence ───────────────────────────────────────────────────────────
    avg_confidence = (
        sum(m.get("confidence", 0.0) for m in all_memories) / total_periods
    )
    period_volume_bonus = min(total_periods / 6.0, 1.0) * 0.20
    raw_confidence = (avg_confidence * 0.80) + period_volume_bonus - len(limitations) * 0.05
    confidence = round(max(min(raw_confidence, 1.0), 0.0), 3)

    return {
        "overallTrend": overall_trend,
        "longTermRisks": sorted(long_term_risks),
        "sustainedImprovements": sorted(sustained_improvements),
        "unstableAreas": unstable_areas,
        "repeatedIgnoredRisks": sorted(repeated_ignored_risks),
        "effectiveLongTermActions": sorted(effective_long_term_actions),
        "carryOverRecommendations": carry_over_recommendations,
        "confidence": confidence,
        "limitations": limitations,
    }


# ---------------------------------------------------------------------------
# Task 2 — Narrative Insight Ranking
# ---------------------------------------------------------------------------

def rank_narrative_insights(
    reasoning: CrossPeriodReasoning,
    memories: list[NarrativeMemoryResult],
    stale_threshold_days: int = _STALE_THRESHOLD_DAYS,
) -> list[RankedInsight]:
    """Rank narrative insights by severity, long-term impact, and evidence strength.

    Returns RankedInsight dicts sorted by score descending.

    Scoring rules:
    - repeated worsening risk: base 0.70, +0.05 per extra occurrence (max +0.20)
    - repeated ignored risk: base 0.65, capped at 0.75 to prevent spam
    - sustained improvement: base 0.45, +0.03 per extra occurrence
    - stale memory (older than stale_threshold_days): penalty up to 0.30
    - deduped by item — highest score wins
    """
    now = datetime.now(timezone.utc)
    stale_cutoff = now - timedelta(days=stale_threshold_days)

    # ── Determine staleness penalty from most recent memory ─────────────────
    latest_gen: datetime | None = None
    for mem in memories:
        gen_at_str = mem.get("generatedAt")
        if gen_at_str:
            try:
                gen_at = datetime.fromisoformat(gen_at_str)
                if gen_at.tzinfo is None:
                    gen_at = gen_at.replace(tzinfo=timezone.utc)
                if latest_gen is None or gen_at > latest_gen:
                    latest_gen = gen_at
            except ValueError:
                pass

    staleness_penalty = 0.0
    if latest_gen is not None and latest_gen < stale_cutoff:
        days_stale = (now - latest_gen).days
        staleness_penalty = min(days_stale / 90.0, 0.30)

    # ── Occurrence counts ────────────────────────────────────────────────────
    risk_occurrence: Counter[str] = Counter()
    improving_occurrence: Counter[str] = Counter()
    ignored_occurrence: Counter[str] = Counter()

    for mem in memories:
        for item in mem.get("repeatedRisks", []):
            risk_occurrence[item] += 1
        for item in mem.get("improvingItems", []):
            improving_occurrence[item] += 1
        for item in mem.get("ignoredItems", []):
            ignored_occurrence[item] += 1

    insights: list[RankedInsight] = []

    def _add(item: str, category: str, reason: str, extra_boost: float = 0.0) -> None:
        base = _CATEGORY_BASE_SCORES.get(category, 0.40)
        score = round(max(min(base + extra_boost - staleness_penalty, 1.0), 0.0), 3)
        insights.append({"item": item, "category": category, "score": score, "reason": reason})

    # Long-term risks
    for item in reasoning.get("longTermRisks", []):
        occ = risk_occurrence.get(item, 1)
        boost = min((occ - 1) * 0.05, 0.20)
        _add(item, "long_term_risk", f"跨期間重複出現 {occ} 次", boost)

    # Repeated ignored risks — urgency capped at 0.75 to avoid spam
    for item in reasoning.get("repeatedIgnoredRisks", []):
        occ = ignored_occurrence.get(item, 1)
        raw = _CATEGORY_BASE_SCORES["repeated_ignored_risk"] + min(occ * 0.03, 0.10) - staleness_penalty
        score = round(max(min(raw, 0.75), 0.0), 3)
        insights.append({
            "item": item,
            "category": "repeated_ignored_risk",
            "score": score,
            "reason": f"已被忽略 {occ} 次，持續存在風險",
        })

    # Sustained improvements
    for item in reasoning.get("sustainedImprovements", []):
        occ = improving_occurrence.get(item, 1)
        boost = min((occ - 1) * 0.03, 0.10)
        _add(item, "sustained_improvement", f"跨 {occ} 個期間持續改善", boost)

    # Unstable areas
    for item in reasoning.get("unstableAreas", []):
        _add(item, "unstable_area", "指標在不同期間波動，需持續觀察")

    # Carry-over recommendations
    for item in reasoning.get("carryOverRecommendations", []):
        _add(item, "carry_over", "未解決的持續性風險，建議優先處理")

    # Effective long-term actions (positive reinforcement)
    for item in reasoning.get("effectiveLongTermActions", []):
        _add(item, "effective_action", "跨期間持續有效的健康行動")

    # Dedup by item — keep highest score
    seen: dict[str, RankedInsight] = {}
    for ins in insights:
        key = ins["item"]
        if key not in seen or ins["score"] > seen[key]["score"]:
            seen[key] = ins

    return sorted(seen.values(), key=lambda x: x["score"], reverse=True)


# ---------------------------------------------------------------------------
# Task 3 — Long-Term Recommendation Carry-Over
# ---------------------------------------------------------------------------

def generate_carry_over_recommendations(
    reasoning: CrossPeriodReasoning,
    active_action_titles: list[str] | None = None,
    previous_carry_overs: list[dict[str, Any]] | None = None,
    max_carry: int = _MAX_CARRY_OVER,
) -> list[CarryOverRecommendation]:
    """Generate carry-over recommendations from unresolved long-term risks.

    Rules:
    - Sources: longTermRisks (urgency=high) + repeatedIgnoredRisks (urgency=medium)
    - Exclude items already in active_action_titles (no duplicates)
    - Exclude items already in sustainedImprovements or effectiveLongTermActions
    - Increment carry_over_count if item appeared in previous_carry_overs
    - Reject items with carry_over_count >= max_carry (prevent infinite loops)
    - Carry-over items preserve their evidence_source
    - Returns empty list when evidence is insufficient
    """
    active_titles = {t.lower().strip() for t in (active_action_titles or [])}
    improved_set = {s.lower().strip() for s in reasoning.get("sustainedImprovements", [])}
    effective_set = {s.lower().strip() for s in reasoning.get("effectiveLongTermActions", [])}

    # Build previous carry-over lookup: item_lower → carry_over_count
    prev_counts: dict[str, int] = {}
    if previous_carry_overs:
        for co in previous_carry_overs:
            key = co.get("text", "").lower().strip()
            if key:
                prev_counts[key] = co.get("carry_over_count", 0)

    # Build deduplicated candidate map: item_lower → (item_original, source, urgency)
    candidate_map: dict[str, tuple[str, str, str]] = {}

    for item in reasoning.get("longTermRisks", []):
        k = item.lower().strip()
        if k not in candidate_map:
            candidate_map[k] = (item, "long_term_risk", "high")

    for item in reasoning.get("repeatedIgnoredRisks", []):
        k = item.lower().strip()
        if k not in candidate_map:
            candidate_map[k] = (item, "repeated_ignored_risk", "medium")

    results: list[CarryOverRecommendation] = []

    for item_key, (item, source, urgency) in candidate_map.items():
        # Skip already resolved
        if item_key in improved_set or item_key in effective_set:
            continue
        # Skip already active
        if item_key in active_titles:
            continue
        # Carry-over count check
        count = prev_counts.get(item_key, 0)
        if count >= max_carry:
            continue

        results.append({
            "text": item,
            "evidence_source": source,
            "urgency": urgency,
            "carry_over_count": count + 1,
        })

    # Sort: urgency desc (high → medium → low), then carry_over_count desc
    _urgency_order = {"high": 0, "medium": 1, "low": 2}
    results.sort(
        key=lambda x: (_urgency_order.get(x["urgency"], 9), -x["carry_over_count"])
    )
    return results
