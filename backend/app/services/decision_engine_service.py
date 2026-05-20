"""
Central Decision Engine Service
================================
Produces a unified, cross-source ranked `decision_items` list that serves as
the SINGLE SOURCE OF TRUTH for:

  Dashboard  → DailyDecisionSurface / DecisionPanel / daily summary
  Notifications → priority grouping (urgent / attention / snoozed / low)
  Insights   → CTA ordering
  Actions    → today's focus

Architecture:
  Rule Engine  → Risk Engine → Insight Engine → Recommendation Engine
                                                         ↓
                             decision_engine_service.build_decision_items()
                                                         ↓
                          dashboard API → { decision_items: [...] }
                                                         ↓
                  Dashboard / Notifications / Insights / Actions
                  (frontend reads only, never re-ranks)

Scoring mirrors the frontend decision-scoring.ts 7-factor model but is
authoritative because the backend already has explicit severity/confidence/
evidence_level fields – no inference needed.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.models.entities import HealthAction

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Severity → base score (mirrors frontend RISK_MAP × 100 × weight 0.25)
_SEVERITY_BASE: dict[str, int] = {
    'critical': 92,
    'high': 80,
    'warning': 72,
    'medium': 55,
    'info': 38,
    'low': 28,
}

# Priority string (actions) → base score
_PRIORITY_STR_BASE: dict[str, int] = {
    'high': 78,
    'medium': 55,
    'low': 30,
}

# Evidence level → score boost
_EVIDENCE_BOOST: dict[str, int] = {'A': 8, 'B': 4, 'C': 0}

# Reminder / overdue status → score boost
_REMINDER_BOOST: dict[str, int] = {
    'overdue': 15,
    'risk_up': 12,
    'streak_break': 8,
    'no_data': 3,
    'none': 0,
}

# Category → related metric columns
_CATEGORY_METRIC_MAP: dict[str, list[str]] = {
    'bp': ['systolic_bp', 'diastolic_bp'],
    'blood_pressure': ['systolic_bp', 'diastolic_bp'],
    'weight': ['weight_kg'],
    'sleep': ['sleep_hours'],
    'blood_glucose': ['blood_glucose'],
    'activity': ['steps'],
    'heart_rate': ['heart_rate'],
    'uric_acid': [],
}

# Keyword → metrics (for title/category text matching)
_KEYWORD_METRIC_MAP: list[tuple[str, list[str]]] = [
    ('血壓', ['systolic_bp', 'diastolic_bp']),
    ('bp', ['systolic_bp', 'diastolic_bp']),
    ('cardio', ['systolic_bp', 'diastolic_bp']),
    ('blood pressure', ['systolic_bp', 'diastolic_bp']),
    ('血糖', ['blood_glucose']),
    ('glucose', ['blood_glucose']),
    ('sugar', ['blood_glucose']),
    ('體重', ['weight_kg']),
    ('weight', ['weight_kg']),
    ('bmi', ['weight_kg']),
    ('睡眠', ['sleep_hours']),
    ('sleep', ['sleep_hours']),
    ('步', ['steps']),
    ('steps', ['steps']),
    ('activity', ['steps']),
]

# Trend detection config
_TREND_CONFIG: dict[str, dict] = {
    'systolic_bp': {'label': '血壓', 'worsening_when': 'up', 'threshold': 5},
    'blood_glucose': {'label': '血糖', 'worsening_when': 'up', 'threshold': 8},
    'weight_kg': {'label': '體重', 'worsening_when': 'up', 'threshold': 1.2},
    'sleep_hours': {'label': '睡眠', 'worsening_when': 'down', 'threshold': 0.7},
}


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

def _days_old(date_val: Any) -> int:
    """Return how many days ago a date_str/datetime is. Returns 7 if unknown."""
    if not date_val:
        return 7
    try:
        if isinstance(date_val, str):
            dt = datetime.fromisoformat(date_val.replace('Z', '+00:00'))
        elif isinstance(date_val, datetime):
            dt = date_val
        else:
            return 7
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return max(0, (datetime.now(timezone.utc) - dt).days)
    except Exception:
        return 7


def _category_to_metrics(category: str) -> list[str]:
    c = str(category).lower()
    if c in _CATEGORY_METRIC_MAP:
        return _CATEGORY_METRIC_MAP[c]
    for keyword, metrics in _KEYWORD_METRIC_MAP:
        if keyword in c:
            return metrics
    return []


def _compute_score(
    severity_or_priority: Any,
    confidence: float,
    evidence_level: str,
    reminder_status: str = 'none',
    days_old: int = 0,
) -> int:
    """
    Compute 0-100 ranking score.

    Base from severity/priority, boosted by confidence, evidence, overdue
    status, and recency.  Thresholds match frontend decision-scoring.ts:
      ≥75 → high priority
      55-74 → medium priority
      <55 → low priority
    """
    if isinstance(severity_or_priority, int):
        # Recommendation priority (5-10 integer)
        base = max(28, min(92, int(severity_or_priority) * 9))
    elif isinstance(severity_or_priority, str):
        sop = severity_or_priority.lower()
        base = _SEVERITY_BASE.get(sop) or _PRIORITY_STR_BASE.get(sop) or 40
    else:
        base = 40

    conf_boost = int(min(1.0, max(0.0, float(confidence or 0))) * 10)
    evid_boost = _EVIDENCE_BOOST.get(str(evidence_level or 'B').upper(), 0)
    reminder_boost = _REMINDER_BOOST.get(str(reminder_status or 'none').lower(), 0)
    recency_boost = 5 if days_old <= 7 else (3 if days_old <= 30 else 0)

    return min(100, base + conf_boost + evid_boost + reminder_boost + recency_boost)


def _score_to_priority(score: int) -> str:
    if score >= 75:
        return 'high'
    if score >= 55:
        return 'medium'
    return 'low'


# ---------------------------------------------------------------------------
# Trend signal detection (mirrors frontend getTrendSignal)
# ---------------------------------------------------------------------------

def _build_trend_signals(trends: dict) -> list[dict]:
    """Detect worsening trends from time-series metric data."""
    signals = []
    for metric, points in (trends or {}).items():
        if not isinstance(points, list) or len(points) < 2:
            continue
        config = _TREND_CONFIG.get(metric)
        if not config:
            continue
        try:
            first_val = float(
                points[0].get('value', 0) if isinstance(points[0], dict)
                else getattr(points[0], 'value', 0)
            )
            last_val = float(
                points[-1].get('value', 0) if isinstance(points[-1], dict)
                else getattr(points[-1], 'value', 0)
            )
        except (TypeError, ValueError):
            continue
        delta = round(last_val - first_val, 1)
        if abs(delta) < config['threshold']:
            continue
        direction = 'up' if delta > 0 else 'down'
        is_worsening = (direction == config['worsening_when'])
        movement = '上升' if direction == 'up' else '下降'
        signals.append({
            'key': metric,
            'label': config['label'],
            'delta': delta,
            'direction': direction,
            'is_worsening': is_worsening,
            'summary': f"{config['label']}在最近一段時間{movement} {abs(delta)}",
        })
    return signals


# ---------------------------------------------------------------------------
# why_now text generators
# ---------------------------------------------------------------------------

def _why_now_alert(alert: dict) -> list[str]:
    severity = str(alert.get('severity', '')).lower()
    title = str(alert.get('title', ''))
    desc = str(alert.get('description', '') or '')
    reasons = []
    if severity in ('critical', 'high', 'warning'):
        reasons.append(f'{title}：風險等級高，需要優先處理。')
    else:
        reasons.append(f'{title}：這項提醒已整理成可執行方向。')
    if desc and len(desc) > 10:
        reasons.append(desc[:80])
    return reasons[:2]


def _why_now_insight(insight: dict) -> list[str]:
    summary = str(insight.get('summary', '') or '')
    title = str(insight.get('title', ''))
    rec = str(insight.get('recommendation', '') or '')
    reasons = [summary[:80]] if summary else [title]
    if rec:
        reasons.append(rec[:80])
    return reasons[:2]


def _why_now_recommendation(rec: dict) -> list[str]:
    title = str(rec.get('title', '') or rec.get('recommendation', '') or '')
    reasons = [title or '系統建議先做這件事。']
    guideline = str(rec.get('guideline_source', '') or '')
    if guideline:
        reasons.append(f'依據：{guideline}')
    return reasons[:2]


def _why_now_action(action: HealthAction) -> list[str]:
    reasons: list[str] = []
    rs = str(action.reminder_status or 'none').lower()
    if rs == 'overdue':
        reasons.append('這項任務已逾期，需要補回節奏。')
    elif rs == 'risk_up':
        reasons.append('這是高風險任務，拖延會讓風險持續累積。')
    elif rs == 'streak_break':
        reasons.append('連續執行紀錄即將中斷，完成一次可保住動力。')
    if str(action.priority or '').lower() == 'high':
        reasons.append('標記為高優先級行動。')
    if not reasons:
        reasons.append('這項行動有助於改善目前的健康指標。')
    return reasons[:2]


def _why_now_trend(signal: dict) -> list[str]:
    return [
        f'{signal["label"]}趨勢正在惡化：{signal["summary"]}。',
        f'建議先把 {signal["label"]} 納入本週追蹤，避免風險繼續累積。',
    ]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_decision_items(
    alerts: list[dict],
    insights: list[dict],
    recommendations: list[dict],
    actions: list[HealthAction],
    trends: dict,
    health_score: dict,
    risk_level: str,
) -> list[dict]:
    """
    Build a unified, cross-source ranked list of decision items.

    Returns up to 15 items sorted by score DESC, deduplicated by title.
    Each item conforms to the UnifiedDecisionItem schema contract.
    """
    items: list[dict] = []

    # ── 1. Alert items ──────────────────────────────────────────────────────
    for alert in (alerts or []):
        severity = str(alert.get('severity', 'medium')).lower()
        confidence = float(alert.get('confidence', 0.65) or 0.65)
        evidence_level = str(alert.get('evidence_level', 'B') or 'B').upper()
        days = _days_old(alert.get('created_at'))
        score = _compute_score(severity, confidence, evidence_level, 'none', days)
        items.append({
            'id': str(alert.get('id', '')),
            'source_type': 'alert',
            'source_id': str(alert.get('rule_id') or alert.get('id', '')),
            'title': str(alert.get('title', '')),
            'description': str(alert.get('description', '') or ''),
            'priority': _score_to_priority(score),
            'why_now': _why_now_alert(alert),
            'next_action': '先開始追蹤這項指標',
            'category': str(alert.get('category', '') or '風險提醒'),
            'status': None,
            'due_date': None,
            'confidence': confidence,
            'evidence_level': evidence_level,
            'guideline_source': alert.get('guideline_source'),
            'related_metric_types': _category_to_metrics(alert.get('category') or ''),
            'outcome_hint': None,
            'feedback_state': 'pending',
            'score': score,
        })

    # ── 2. Insight items ────────────────────────────────────────────────────
    for insight in (insights or []):
        severity = str(insight.get('severity', 'medium')).lower()
        confidence = float(insight.get('confidence', 0.65) or 0.65)
        evidence_level = str(insight.get('evidence_level', 'B') or 'B').upper()
        days = _days_old(insight.get('generated_at'))
        score = _compute_score(severity, confidence, evidence_level, 'none', days)
        items.append({
            'id': str(insight.get('id', '')),
            'source_type': 'insight',
            'source_id': str(insight.get('id', '')),
            'title': str(insight.get('title', '')),
            'description': str(insight.get('summary', '') or ''),
            'priority': _score_to_priority(score),
            'why_now': _why_now_insight(insight),
            'next_action': str(insight.get('recommendation') or '查看詳情'),
            'category': str(insight.get('category', '') or '健康洞察'),
            'status': None,
            'due_date': None,
            'confidence': confidence,
            'evidence_level': evidence_level,
            'guideline_source': insight.get('guideline_source'),
            'related_metric_types': _category_to_metrics(insight.get('category') or ''),
            'outcome_hint': None,
            'feedback_state': 'pending',
            'score': score,
        })

    # ── 3. Recommendation items ─────────────────────────────────────────────
    for i, rec in enumerate(recommendations or []):
        priority_int = int(rec.get('priority', 5) or 5)
        confidence = float(rec.get('confidence', 0.7) or 0.7)
        evidence_level = str(rec.get('evidence_level', 'B') or 'B').upper()
        score = _compute_score(priority_int, confidence, evidence_level, 'none', 0)
        items.append({
            'id': str(rec.get('id') or rec.get('rule_id') or f'rec-{i}'),
            'source_type': 'recommendation',
            'source_id': str(rec.get('rule_id') or f'rec-{i}'),
            'title': str(rec.get('title') or rec.get('recommendation') or '改善建議'),
            'description': str(rec.get('recommendation') or ''),
            'priority': _score_to_priority(score),
            'why_now': _why_now_recommendation(rec),
            'next_action': str(rec.get('title') or rec.get('recommendation') or '開始行動'),
            'category': str(rec.get('category', '') or '改善建議'),
            'status': None,
            'due_date': None,
            'confidence': confidence,
            'evidence_level': evidence_level,
            'guideline_source': rec.get('guideline_source'),
            'related_metric_types': _category_to_metrics(rec.get('category') or ''),
            'outcome_hint': None,
            'feedback_state': 'pending',
            'score': score,
        })

    # ── 4. Action items (overdue / risk_up / streak_break only) ────────────
    for action in (actions or []):
        if str(action.status or '').lower() == 'done':
            continue
        rs = str(action.reminder_status or 'none').lower()
        if rs not in ('overdue', 'risk_up', 'streak_break'):
            continue
        confidence = float(action.confidence or 0.65)
        evidence_level = str(action.evidence_level or 'B').upper()
        days = _days_old(action.created_at)
        score = _compute_score(
            str(action.priority or 'medium'),
            confidence, evidence_level, rs, days
        )
        feedback = str(action.impact_status or 'pending')
        items.append({
            'id': str(action.id),
            'source_type': 'action',
            'source_id': str(action.id),
            'title': str(action.title),
            'description': str(action.description or ''),
            'priority': _score_to_priority(score),
            'why_now': _why_now_action(action),
            'next_action': str(action.title),
            'category': str(action.category or '既有任務'),
            'status': str(action.status),
            'due_date': action.due_date.isoformat() if action.due_date else None,
            'confidence': confidence,
            'evidence_level': evidence_level,
            'guideline_source': action.guideline_source,
            'related_metric_types': _category_to_metrics(action.category or ''),
            'outcome_hint': None,
            'feedback_state': feedback,
            'score': score,
        })

    # ── 5. Worsening trend signals ──────────────────────────────────────────
    for signal in _build_trend_signals(trends or {}):
        if not signal['is_worsening']:
            continue
        score = _compute_score('warning', 0.72, 'B', 'none', 0)
        items.append({
            'id': f'trend-{signal["key"]}',
            'source_type': 'insight',
            'source_id': f'trend_{signal["key"]}',
            'title': f'{signal["label"]}趨勢需要先追蹤',
            'description': signal['summary'],
            'priority': _score_to_priority(score),
            'why_now': _why_now_trend(signal),
            'next_action': f'先把 {signal["label"]} 納入本週追蹤',
            'category': signal['label'],
            'status': None,
            'due_date': None,
            'confidence': 0.72,
            'evidence_level': 'B',
            'guideline_source': 'Trend Monitor',
            'related_metric_types': [signal['key']],
            'outcome_hint': None,
            'feedback_state': 'pending',
            'score': score,
        })

    # ── Dedup by title (keep highest score), sort DESC, limit 15 ──────────
    seen: dict[str, dict] = {}
    for item in items:
        key = str(item.get('title', '')).strip().lower()
        if not key:
            continue
        if key not in seen or item['score'] > seen[key]['score']:
            seen[key] = item

    return sorted(seen.values(), key=lambda x: x['score'], reverse=True)[:15]
