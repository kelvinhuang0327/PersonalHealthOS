from __future__ import annotations

from typing import Any

BANNED_TERMS = ['確診', '診斷為', '處方', '藥物劑量', 'prescription', 'diagnose', 'dosage']
ALLOWED_LEVELS = {'low', 'medium', 'high'}
ALLOWED_PRIORITIES = {'low', 'medium', 'high'}


def apply_guardrails(module: str, output: dict[str, Any], allowed_evidence_ids: set[str], max_items: int = 5) -> tuple[dict[str, Any], dict[str, Any]]:
    health_risks = _sanitize_risks(output.get('health_risks', []), allowed_evidence_ids, max_items)
    recommendations = _sanitize_recommendations(output.get('lifestyle_recommendations', []), allowed_evidence_ids, max_items)
    follow_ups = _sanitize_follow_ups(output.get('follow_up_items', []), allowed_evidence_ids, max_items)

    safety_flags: list[str] = []
    _scan_safety_terms(health_risks, safety_flags)
    _scan_safety_terms(recommendations, safety_flags)
    _scan_safety_terms(follow_ups, safety_flags)

    total_items = len(output.get('health_risks', [])) + len(output.get('lifestyle_recommendations', [])) + len(output.get('follow_up_items', []))
    grounded_items = len(health_risks) + len(recommendations) + len(follow_ups)
    dropped_items = max(0, total_items - grounded_items)
    grounded_ratio = round(grounded_items / total_items, 3) if total_items > 0 else 1.0

    guarded = {
        'module': module,
        'health_risks': health_risks,
        'lifestyle_recommendations': recommendations,
        'follow_up_items': follow_ups,
        'confidence': float(output.get('confidence', 0.5)),
    }
    report = {
        'dropped_items': dropped_items,
        'grounded_items': grounded_items,
        'total_items': total_items,
        'grounded_ratio': grounded_ratio,
        'safety_flags': safety_flags,
    }
    return guarded, report


def evaluate_guarded_output(guarded_output: dict[str, Any], report: dict[str, Any]) -> dict[str, Any]:
    format_valid = all(
        key in guarded_output
        for key in ['health_risks', 'lifestyle_recommendations', 'follow_up_items', 'confidence']
    )
    safety_pass = len(report.get('safety_flags', [])) == 0
    actionable_count = len(guarded_output.get('lifestyle_recommendations', [])) + len(guarded_output.get('follow_up_items', []))
    actionability_score = min(1.0, actionable_count / 6)

    overall = (
        0.35 * (1.0 if format_valid else 0.0)
        + 0.35 * float(report.get('grounded_ratio', 0.0))
        + 0.2 * (1.0 if safety_pass else 0.0)
        + 0.1 * actionability_score
    )

    return {
        'format_valid': format_valid,
        'grounded_ratio': float(report.get('grounded_ratio', 0.0)),
        'safety_pass': safety_pass,
        'actionability_score': round(actionability_score, 3),
        'overall_score': round(overall, 3),
    }


def _sanitize_risks(items: list[dict[str, Any]], allowed_ids: set[str], max_items: int) -> list[dict[str, Any]]:
    cleaned: list[dict[str, Any]] = []
    for item in items[:max_items]:
        evidence = _valid_evidence(item.get('evidence_ids', []), allowed_ids)
        if not evidence:
            continue
        level = str(item.get('level', 'medium')).lower()
        if level not in ALLOWED_LEVELS:
            level = 'medium'
        cleaned.append(
            {
                'title': _safe_text(item.get('title', '未命名風險')),
                'level': level,
                'reason': _safe_text(item.get('reason', '資料支持不足。')),
                'evidence_ids': evidence,
            }
        )
    return cleaned


def _sanitize_recommendations(items: list[dict[str, Any]], allowed_ids: set[str], max_items: int) -> list[dict[str, Any]]:
    cleaned: list[dict[str, Any]] = []
    for item in items[:max_items]:
        evidence = _valid_evidence(item.get('evidence_ids', []), allowed_ids)
        if not evidence:
            continue
        priority = str(item.get('priority', 'medium')).lower()
        if priority not in ALLOWED_PRIORITIES:
            priority = 'medium'
        cleaned.append(
            {
                'title': _safe_text(item.get('title', '生活建議')),
                'action': _safe_text(item.get('action', '請持續追蹤。')),
                'priority': priority,
                'evidence_ids': evidence,
            }
        )
    return cleaned


def _sanitize_follow_ups(items: list[dict[str, Any]], allowed_ids: set[str], max_items: int) -> list[dict[str, Any]]:
    cleaned: list[dict[str, Any]] = []
    for item in items[:max_items]:
        evidence = _valid_evidence(item.get('evidence_ids', []), allowed_ids)
        if not evidence:
            continue
        cleaned.append(
            {
                'item': _safe_text(item.get('item', '追蹤項目')),
                'timeline': _safe_text(item.get('timeline', '2-4 週')),
                'why': _safe_text(item.get('why', '依近期紀錄建議追蹤。')),
                'evidence_ids': evidence,
            }
        )
    return cleaned


def _valid_evidence(evidence_ids: list[Any], allowed_ids: set[str]) -> list[str]:
    normalized = [str(e).strip() for e in evidence_ids if str(e).strip()]
    return [e for e in normalized if e in allowed_ids]


def _safe_text(text: Any) -> str:
    value = str(text).strip()
    return value[:240] if value else 'N/A'


def _scan_safety_terms(items: list[dict[str, Any]], safety_flags: list[str]) -> None:
    for item in items:
        joined = ' '.join(str(v) for v in item.values()).lower()
        for term in BANNED_TERMS:
            if term.lower() in joined:
                safety_flags.append(f'contains_banned_term:{term}')
                break
