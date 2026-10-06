from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from typing import Any
import uuid

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.entities import AISummary, HealthInsight, HealthMetric, LabReport, LabReportItem, RiskAlert, SymptomLog
from app.services.health_ai_engine.anomaly_engine import detect_anomalies
from app.services.health_ai_engine.clinical_score_engine import calculate_clinical_scores
from app.services.health_ai_engine.confidence_engine import calibrate_confidence, combine_confidence
from app.services.health_ai_engine.guideline_engine import derive_clinical_labels
from app.services.health_ai_engine.guideline_registry import enrich_explainability
from app.services.health_ai_engine.personalization_engine import build_personalized_context
from app.services.health_ai_engine.prediction_engine import generate_predictive_insights
from app.services.health_ai_engine.recommendation_engine import generate_recommendations
from app.services.health_ai_engine.reasoning_engine import generate_reasoning_summary
from app.services.health_ai_engine.risk_stratification_engine import stratify_risk_level
from app.services.health_ai_engine.rule_engine import evaluate_rules, load_rules
from app.services.health_ai_engine.safety_guardrail import MEDICAL_DISCLAIMER, apply_safety_guardrail


def generate_health_narrative(context: dict[str, Any]) -> dict[str, Any]:
    health_score = context.get('health_score') or {}
    alerts = context.get('alerts') or []
    insights = context.get('insights') or []
    trends = context.get('trends') or {}
    symptoms = context.get('symptoms') or []
    labs = context.get('labs') or []
    metrics = context.get('metrics') or []
    actions = context.get('actions') or []
    risk_level = str(context.get('risk_level') or 'low').lower()

    summary = _build_narrative_summary(risk_level, alerts, trends, symptoms, labs, health_score)
    risks = _build_narrative_risks(alerts, labs, insights)
    trend_lines = _build_narrative_trends(trends, symptoms, metrics)
    reasons = _build_narrative_reasons(symptoms, metrics, alerts, labs, actions)
    action_lines = _build_narrative_actions(alerts, trends, symptoms, labs, actions)

    return {
        'summary': summary,
        'risks': risks[:3],
        'trends': trend_lines[:3],
        'reasons': reasons[:3],
        'actions': action_lines[:3],
    }


def generate_health_narrative_v2(context: dict[str, Any], previous_narrative: dict[str, Any] | str | None = None) -> dict[str, Any]:
    current_score = _to_int((context.get('health_score') or {}).get('overall_score'))
    previous_score = _extract_previous_score(previous_narrative)
    score_delta = current_score - previous_score if previous_score is not None else None
    score_window = _time_window_phrase(previous_narrative, context)

    current = generate_health_narrative(context)
    trend_summary = current['trends']
    action_lines = current['actions']
    reasons = current['reasons']

    delta_summary = _build_delta_summary(score_delta, current, score_window, previous_narrative, context)
    improvements = _build_improvements(context, previous_narrative, score_delta)
    deteriorations = _build_deteriorations(context, previous_narrative, score_delta)
    adherence = _build_adherence(context)
    missed_risks = _build_missed_risks(context)

    return {
        **current,
        'delta_summary': delta_summary,
        'improvements': improvements[:3],
        'deteriorations': deteriorations[:3],
        'adherence': adherence[:3],
        'missed_risks': missed_risks[:3],
    }


def generate_health_narrative_v3(
    context: dict[str, Any],
    previous_narrative: dict[str, Any] | str | None = None,
    completed_actions: list[Any] | None = None,
) -> dict[str, Any]:
    """Narrative v3 – Causal narrative: WHY did things change?

    Upgrades v2's "change description" into "change explanation" by linking
    completed actions to observed metric deltas.

    Output shape::

        {
          summary, improvements, deteriorations,
          causes: ["你血壓下降，主要原因是…"],
          missed_opportunities: ["尿酸偏高，但尚未開始任何對應行動"],
          next_actions: ["…"]
        }
    """
    v2 = generate_health_narrative_v2(context, previous_narrative)
    actions = completed_actions or context.get('actions') or []
    trends = context.get('trends') or {}
    alerts = context.get('alerts') or []

    causes = _build_causes(actions, trends, context)
    missed_opportunities = _build_missed_opportunities(alerts, actions, context)
    next_actions = _build_next_actions_v3(actions, alerts, trends, context)

    return {
        **v2,
        'causes': causes[:4],
        'missed_opportunities': missed_opportunities[:3],
        'next_actions': next_actions[:3],
        'narrative_version': 'v3',
    }


def _build_causes(actions: list[Any], trends: dict[str, Any], context: dict[str, Any]) -> list[str]:
    """Link completed/ongoing actions to observed metric improvements."""
    causes: list[str] = []
    done_actions = [a for a in actions if str(getattr(a, 'status', '')).lower() == 'done']
    in_progress = [a for a in actions if str(getattr(a, 'status', '')).lower() == 'in_progress']
    streak_actions = [
        a for a in (done_actions + in_progress)
        if (_to_int(getattr(a, 'streak_count', None), 0) or _to_int(getattr(a, 'streak', None), 0) or 0) >= 3
    ]

    # BP improvement cause
    if 'systolic_bp' in trends:
        first = _point_value(trends['systolic_bp'][0]) if trends['systolic_bp'] else 0
        last = _point_value(trends['systolic_bp'][-1]) if trends['systolic_bp'] else 0
        if last < first - 1:
            bp_actions = [a for a in streak_actions if _action_matches_category(a, ['bp', 'blood_pressure', 'cardiovascular', 'salt', 'exercise'])]
            if bp_actions:
                titles = '、'.join(str(getattr(a, 'title', '行動')) for a in bp_actions[:2])
                causes.append(f'你的血壓有下降趨勢，很可能是因為你持續執行了「{titles}」，這些行動都與控制血壓直接相關。')
            else:
                causes.append('你的血壓有下降趨勢，但目前尚未找到明確的對應行動。持續追蹤有助於找出原因。')

    # Weight improvement cause
    if 'weight_kg' in trends:
        first = _point_value(trends['weight_kg'][0]) if trends['weight_kg'] else 0
        last = _point_value(trends['weight_kg'][-1]) if trends['weight_kg'] else 0
        if last < first - 0.2:
            weight_actions = [a for a in streak_actions if _action_matches_category(a, ['weight', 'diet', 'exercise', 'lifestyle', 'activity'])]
            if weight_actions:
                titles = '、'.join(str(getattr(a, 'title', '行動')) for a in weight_actions[:2])
                causes.append(f'體重有下降趨勢（減少約 {abs(last - first):.1f} kg），這與你持續執行的「{titles}」有關。')

    # Sleep improvement cause
    if 'sleep_hours' in trends:
        first = _point_value(trends['sleep_hours'][0]) if trends['sleep_hours'] else 0
        last = _point_value(trends['sleep_hours'][-1]) if trends['sleep_hours'] else 0
        if last > first + 0.2:
            sleep_actions = [a for a in streak_actions if _action_matches_category(a, ['sleep', 'rest', 'habit'])]
            if sleep_actions:
                titles = '、'.join(str(getattr(a, 'title', '行動')) for a in sleep_actions[:2])
                causes.append(f'睡眠時間有改善（增加約 {abs(last - first):.1f} 小時），這與你執行的「{titles}」有直接關聯。')

    # Streak cause (general adherence)
    if streak_actions and not causes:
        titles = '、'.join(str(getattr(a, 'title', '行動')) for a in streak_actions[:2])
        streak = max(
            _to_int(getattr(a, 'streak_count', None), 0) or _to_int(getattr(a, 'streak', None), 0) or 0
            for a in streak_actions
        )
        causes.append(f'你在「{titles}」上已連續堅持 {streak} 天，這種持續性本身就是改善的最大來源。')

    # No-action but worsening
    alerts_titles = [str(getattr(a, 'title', '')) for a in (context.get('alerts') or [])]
    if not done_actions and alerts_titles:
        top_alert = alerts_titles[0]
        causes.append(f'「{top_alert}」仍在提醒中，因為目前還沒有對應的完成行動來改變這個方向。')

    if not causes:
        causes.append('目前資料尚不足以找出明確的因果關係，建議繼續記錄並執行行動，7 天後將有更清楚的回饋。')

    return causes


def _build_missed_opportunities(alerts: list[Any], actions: list[Any], context: dict[str, Any]) -> list[str]:
    """Highlight risks that have no matching active action."""
    missed: list[str] = []
    action_text = ' '.join(
        str(getattr(a, 'title', '')) + ' ' + str(getattr(a, 'category', '') or '')
        for a in actions
    ).lower()

    category_keywords = {
        '尿酸': ['uric_acid', '尿酸', 'gout', '痛風'],
        '血壓': ['bp', 'blood_pressure', '血壓', 'hypertension'],
        '血糖': ['glucose', '血糖', 'diabetes'],
        '體重': ['weight', '體重', '肥胖'],
        '睡眠': ['sleep', '睡眠'],
        '肝功能': ['liver', 'alt', 'ast', '肝'],
    }

    for alert in alerts:
        title = str(getattr(alert, 'title', '') or getattr(alert, 'risk_type', '') or '')
        matched = False
        for label, keywords in category_keywords.items():
            if any(kw in title.lower() for kw in keywords):
                if not any(kw in action_text for kw in keywords):
                    missed.append(f'「{label}」相關指標偏高，但目前還沒有開始任何針對此類別的行動，錯過了改善的機會窗口。')
                    matched = True
                    break
        if not matched and title and title not in action_text[:200]:
            missed.append(f'「{title}」已出現提醒，但尚未有對應的追蹤行動，建議盡快建立一個。')

    # Check trends for worsening metrics with no action
    trends = context.get('trends') or {}
    for metric_key, points in trends.items():
        if not isinstance(points, list) or len(points) < 2:
            continue
        first = _point_value(points[0])
        last = _point_value(points[-1])
        lower_is_better = metric_key != 'sleep_hours'
        worsening = (last > first + 1) if lower_is_better else (last < first - 0.3)
        if worsening and _metric_name(metric_key) not in action_text:
            label = _metric_name(metric_key)
            missed.append(f'{label} 數值在持續往不好的方向走，但目前沒有任何對應行動在追蹤它。')

    return missed or ['目前看起來沒有明顯被遺漏的風險，繼續保持！']


def _build_next_actions_v3(
    actions: list[Any],
    alerts: list[Any],
    trends: dict[str, Any],
    context: dict[str, Any],
) -> list[str]:
    """Concrete next step recommendations based on causal analysis."""
    nexts: list[str] = []

    # Overdue actions first
    overdue = [a for a in actions if str(getattr(a, 'reminder_status', '')).lower() in ('overdue', 'risk_up')]
    if overdue:
        title = str(getattr(overdue[0], 'title', '某項行動'))
        nexts.append(f'「{title}」已逾期或風險上升，今天最重要的事是先完成它。')

    # Streak break
    streak_break = [a for a in actions if str(getattr(a, 'reminder_status', '')).lower() == 'streak_break']
    if streak_break:
        title = str(getattr(streak_break[0], 'title', '連續行動'))
        streak = _to_int(getattr(streak_break[0], 'streak_count', None), 0) or _to_int(getattr(streak_break[0], 'streak', None), 0) or 0
        nexts.append(f'「{title}」的連續記錄（{streak} 天）快中斷了，今天補做一次可以保住這個成果。')

    # No action for top alert
    alert_titles = [str(getattr(a, 'title', '')) for a in alerts]
    action_text = ' '.join(str(getattr(a, 'title', '')) for a in actions).lower()
    for alert_title in alert_titles[:2]:
        if alert_title.lower() not in action_text:
            nexts.append(f'針對「{alert_title}」，建議今天新增一個追蹤行動，讓系統在 7 天後可以判斷是否有改善。')

    # Worsening metric suggestion
    for metric_key, points in trends.items():
        if not isinstance(points, list) or len(points) < 2:
            continue
        first = _point_value(points[0])
        last = _point_value(points[-1])
        lower_better = metric_key != 'sleep_hours'
        worsening = (last > first + 2) if lower_better else (last < first - 0.3)
        if worsening:
            label = _metric_name(metric_key)
            suggestions = {
                'systolic_bp': '減少鹽分攝取或增加有氧運動',
                'weight_kg': '調整飲食份量並增加步行',
                'sleep_hours': '固定就寢時間並減少睡前螢幕時間',
                'blood_glucose': '減少精緻澱粉並在飯後步行 10 分鐘',
            }
            suggestion = suggestions.get(metric_key, '持續追蹤並考慮就醫諮詢')
            nexts.append(f'{label} 數值仍在惡化，下一步建議：{suggestion}。')
            break

    if not nexts:
        nexts.append('整體狀況尚穩定，今天的任務是繼續記錄一筆健康數據，讓系統累積更多判斷依據。')

    return nexts


def _action_matches_category(action: Any, keywords: list[str]) -> bool:
    text = (
        str(getattr(action, 'category', '') or '').lower()
        + ' '
        + str(getattr(action, 'title', '') or '').lower()
        + ' '
        + str(getattr(action, 'description', '') or '').lower()
    )
    return any(kw.lower() in text for kw in keywords)


def get_latest_narrative(
    db: Session,
    user_id: str,
    person_id: str,
    include_legacy: bool = False,
    summary_type: str | None = None,
) -> dict[str, Any] | None:
    row = _fetch_narrative_row(db, user_id, person_id, include_legacy=include_legacy, summary_type=summary_type, offset=0)
    return _serialize_narrative_row(row) if row else None


def get_previous_narrative(
    db: Session,
    user_id: str,
    person_id: str,
    include_legacy: bool = False,
    summary_type: str | None = None,
) -> dict[str, Any] | None:
    row = _fetch_narrative_row(db, user_id, person_id, include_legacy=include_legacy, summary_type=summary_type, offset=1)
    return _serialize_narrative_row(row) if row else None


def get_narrative_history(
    db: Session,
    user_id: str,
    person_id: str,
    limit: int = 10,
    include_legacy: bool = False,
    summary_type: str | None = None,
) -> list[dict[str, Any]]:
    user_key = _uuid_or_raw(user_id)
    person_key = _uuid_or_raw(person_id)
    query = db.query(AISummary).filter(AISummary.user_id == user_key)
    summary_filter = AISummary.subject_profile_id == person_key
    if include_legacy:
        summary_filter = or_(summary_filter, AISummary.subject_profile_id.is_(None))
    query = query.filter(summary_filter)
    if summary_type:
        query = query.filter(AISummary.summary_type == summary_type)
    rows = query.order_by(AISummary.generated_at.desc(), AISummary.created_at.desc()).limit(limit).all()
    return [ _serialize_narrative_row(row) for row in rows if row is not None ]


def should_persist_narrative(current: dict[str, Any], previous: dict[str, Any] | None, threshold_hours: int = 24) -> bool:
    if previous is None:
        return True

    current_time = _parse_datetime(current.get('generated_at'))
    previous_time = _parse_datetime(previous.get('generated_at'))
    if current_time and previous_time and current_time - previous_time >= timedelta(hours=threshold_hours):
        return True

    current_v2 = current.get('health_narrative_v2') or {}
    previous_v2 = previous.get('health_narrative_v2') or {}
    current_v1 = current.get('health_narrative') or {}
    previous_v1 = previous.get('health_narrative') or {}

    comparable_pairs = [
        (current_v2.get('summary'), previous_v2.get('summary')),
        (current_v2.get('delta_summary'), previous_v2.get('delta_summary')),
        (current.get('risk_level'), previous.get('risk_level')),
        (current.get('summary_type'), previous.get('summary_type')),
        (current.get('narrative_version'), previous.get('narrative_version')),
        (current_v1.get('summary'), previous_v1.get('summary')),
        (current.get('overall_score') or (current.get('health_score') or {}).get('overall_score'), previous.get('overall_score') or (previous.get('health_score') or {}).get('overall_score')),
    ]
    for left, right in comparable_pairs:
        if _normalize_text(left) != _normalize_text(right):
            return True

    for key in ('improvements', 'deteriorations', 'adherence', 'missed_risks', 'actions', 'risks', 'trends', 'reasons'):
        if _normalize_list(current_v2.get(key) or current_v1.get(key)) != _normalize_list(previous_v2.get(key) or previous_v1.get(key)):
            return True

    if _normalize_text(current.get('based_on_alert_snapshot')) != _normalize_text(previous.get('based_on_alert_snapshot')):
        return True

    return False


def persist_narrative_history(
    db: Session,
    user_id: str,
    person_id: str,
    current: dict[str, Any],
    summary_type: str = 'daily',
    based_on_score_id: str | None = None,
    based_on_alert_snapshot: str | None = None,
    include_legacy: bool = False,
) -> AISummary | None:
    previous = get_latest_narrative(db, user_id, person_id, include_legacy=include_legacy, summary_type=summary_type)
    if not should_persist_narrative(current, previous):
        return None

    user_key = _uuid_or_raw(user_id)
    person_key = _uuid_or_raw(person_id)
    now = _parse_datetime(current.get('generated_at')) or datetime.now(timezone.utc)
    narrative_v1 = current.get('health_narrative') or {}
    narrative_v2 = current.get('health_narrative_v2') or {}
    summary_text = narrative_v2.get('delta_summary') or narrative_v1.get('summary') or current.get('summary') or '健康敘事已生成。'
    action_texts = narrative_v2.get('actions') or narrative_v1.get('actions') or []
    recommendations = '\n'.join(str(item) for item in action_texts[:3]) if action_texts else summary_text
    alert_snapshot = based_on_alert_snapshot or current.get('based_on_alert_snapshot') or _snapshot_hash(current.get('alerts') or [])
    score_id = based_on_score_id or current.get('based_on_score_id')

    row = AISummary(
        user_id=user_key,
        subject_profile_id=person_key,
        period_start=None,
        period_end=None,
        summary_text=summary_text,
        abnormal_explanation=narrative_v2.get('delta_summary') or narrative_v1.get('summary'),
        recommendations=recommendations,
        disclaimer=MEDICAL_DISCLAIMER,
        model_name='narrative_engine_v2',
        narrative_json=current,
        narrative_version=str(current.get('narrative_version') or 'v2'),
        summary_type=summary_type,
        generated_at=now,
        based_on_score_id=_uuid_or_raw(score_id) if score_id else None,
        based_on_alert_snapshot=alert_snapshot,
        created_at=now,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def generate_health_insights(db: Session, user_id: str, person_id: str, include_legacy: bool) -> list[HealthInsight]:
    user_key = _uuid_or_raw(user_id)
    person_key = _uuid_or_raw(person_id)
    metric_filter = HealthMetric.subject_profile_id == person_key
    symptom_filter = SymptomLog.subject_profile_id == person_key
    alert_filter = RiskAlert.subject_profile_id == person_key
    report_filter = LabReport.subject_profile_id == person_key
    insight_filter = HealthInsight.subject_profile_id == person_key
    if include_legacy:
        metric_filter = or_(metric_filter, HealthMetric.subject_profile_id.is_(None))
        symptom_filter = or_(symptom_filter, SymptomLog.subject_profile_id.is_(None))
        alert_filter = or_(alert_filter, RiskAlert.subject_profile_id.is_(None))
        report_filter = or_(report_filter, LabReport.subject_profile_id.is_(None))
        insight_filter = or_(insight_filter, HealthInsight.subject_profile_id.is_(None))

    now = datetime.now(timezone.utc)
    metrics = (
        db.query(HealthMetric).filter(HealthMetric.user_id == user_key, metric_filter).order_by(HealthMetric.recorded_at.desc()).limit(30).all()
    )
    symptoms = (
        db.query(SymptomLog).filter(SymptomLog.user_id == user_key, symptom_filter).order_by(SymptomLog.occurred_at.desc()).limit(20).all()
    )
    alerts = (
        db.query(RiskAlert)
        .filter(RiskAlert.user_id == user_key, RiskAlert.status == 'active', alert_filter)
        .order_by(RiskAlert.created_at.desc())
        .limit(20)
        .all()
    )
    lab_items = (
        db.query(LabReportItem)
        .join(LabReport, LabReportItem.report_id == LabReport.id)
        .filter(LabReport.user_id == user_key, report_filter)
        .order_by(LabReportItem.captured_at.desc())
        .limit(40)
        .all()
    )
    existing = (
        db.query(HealthInsight)
        .filter(HealthInsight.user_id == user_key, HealthInsight.is_active.is_(True), insight_filter)
        .all()
    )
    existing_keys = {(row.insight_type, row.title) for row in existing}
    context = _build_context(metrics, symptoms, alerts)
    matched_rules = evaluate_rules(load_rules('insight_rules.yaml'), context)
    rule_coverage = (len(matched_rules) / max(1, len(load_rules('insight_rules.yaml'))))
    calibrated_confidence = calibrate_confidence(
        metrics_count=len(metrics),
        labs_count=len(lab_items),
        timeline_length=len(metrics) + len(symptoms) + len(alerts),
        rule_coverage=rule_coverage,
    )
    personalized = build_personalized_context(metrics)
    anomaly_items = detect_anomalies(metrics, lab_items)
    predictive_items = generate_predictive_insights(metrics, alerts)
    clinical_labels = derive_clinical_labels(metrics, lab_items)
    risk_level = stratify_risk_level(metrics, lab_items, context['chronic_count'], len(alerts))
    clinical_scores = calculate_clinical_scores(metrics, lab_items)
    recommendations = generate_recommendations(clinical_labels, risk_level['risk_level'], alerts, calibrated_confidence)
    reasoning = generate_reasoning_summary([], alerts, {'overall_score': context.get('overall_score')}, [], metrics)
    guarded_reasoning = apply_safety_guardrail(reasoning['summary'])
    generated: list[HealthInsight] = []
    for rule in matched_rules:
        payload = rule.get('output', {})
        key = (payload.get('insight_type', 'follow_up'), payload.get('title', rule.get('id', '洞察')))
        if key in existing_keys:
            continue
        summary_template = payload.get('summary_template', '偵測到健康洞察。')
        generated.append(
            HealthInsight(
                user_id=user_key,
                subject_profile_id=person_key,
                insight_type=payload.get('insight_type', 'follow_up'),
                severity=payload.get('severity', 'info'),
                title=payload.get('title', '健康洞察'),
                summary=_mock_llm_summary(summary_template, payload.get('insight_type', 'follow_up')),
                recommendation=payload.get('recommendation', '建議持續追蹤。'),
                evidence_json=enrich_explainability(
                    {
                    'context': context,
                    'rule_id': rule.get('id'),
                    'category': rule.get('category'),
                    'priority': rule.get('priority', 0),
                    'confidence': combine_confidence(calibrated_confidence, rule.get('confidence', 0)),
                    'evidence_level': rule.get('evidence_level', 'B'),
                    'guideline_source': rule.get('guideline_source', 'Rule Library'),
                    }
                ),
                generated_at=now,
                expires_at=now + timedelta(days=30),
                is_active=True,
            )
        )
    for anomaly in anomaly_items:
        key = ('follow_up', anomaly['title'])
        if key in existing_keys:
            continue
        generated.append(
            HealthInsight(
                user_id=user_key,
                subject_profile_id=person_key,
                insight_type='follow_up',
                severity='warning',
                title=anomaly['title'],
                summary=_mock_llm_summary(anomaly['summary'], 'follow_up'),
                recommendation='建議持續監測並與專業人員討論。',
                evidence_json=enrich_explainability(
                    {
                        **anomaly,
                        'confidence': combine_confidence(calibrated_confidence, anomaly.get('confidence')),
                        'evidence_level': anomaly.get('evidence_level', 'B'),
                    }
                ),
                generated_at=now,
                expires_at=now + timedelta(days=14),
                is_active=True,
            )
        )
    for pred in predictive_items:
        key = ('trend', pred['title'])
        if key in existing_keys:
            continue
        generated.append(
            HealthInsight(
                user_id=user_key,
                subject_profile_id=person_key,
                insight_type='trend',
                severity='info',
                title=pred['title'],
                summary=_mock_llm_summary(pred['summary'], 'trend'),
                recommendation='建議持續追蹤趨勢變化。',
                evidence_json=enrich_explainability(
                    {
                        **pred,
                        'confidence': combine_confidence(calibrated_confidence, pred.get('confidence')),
                        'evidence_level': pred.get('evidence_level', 'C'),
                    }
                ),
                generated_at=now,
                expires_at=now + timedelta(days=21),
                is_active=True,
            )
        )
    key = ('follow_up', 'AI 推理摘要')
    if key not in existing_keys:
        generated.append(
            HealthInsight(
                user_id=user_key,
                subject_profile_id=person_key,
                insight_type='follow_up',
                severity='info',
                title='AI 推理摘要',
                summary=guarded_reasoning['safe_response'],
                recommendation='建議依照風險與趨勢優先處理高風險項目。',
                evidence_json=enrich_explainability(
                    {
                    'reasoning': reasoning,
                    'safe_response': guarded_reasoning['safe_response'],
                    'confidence': calibrated_confidence,
                    'evidence_level': 'B',
                    'guideline_source': reasoning.get('guideline_source', 'Clinical Safety Reasoning'),
                    'personalized_context': personalized,
                    'clinical_labels': clinical_labels,
                    'risk_level': risk_level,
                    'clinical_scores': clinical_scores,
                    'recommendations': recommendations,
                    }
                ),
                generated_at=now,
                expires_at=now + timedelta(days=7),
                is_active=True,
            )
        )
    for row in generated:
        db.add(row)
    db.commit()
    for row in generated:
        db.refresh(row)
    return generated


def list_active_insights(db: Session, user_id: str, person_id: str, include_legacy: bool, limit: int = 50) -> list[HealthInsight]:
    user_key = _uuid_or_raw(user_id)
    person_key = _uuid_or_raw(person_id)
    insight_filter = HealthInsight.subject_profile_id == person_key
    if include_legacy:
        insight_filter = or_(insight_filter, HealthInsight.subject_profile_id.is_(None))
    rows = (
        db.query(HealthInsight)
        .filter(HealthInsight.user_id == user_key, HealthInsight.is_active.is_(True), insight_filter)
        .all()
    )
    ranked_rows = sorted(rows, key=_health_insight_rank_key, reverse=True)
    return ranked_rows[:limit]


def _health_insight_rank_key(row: HealthInsight) -> tuple[float, float, float]:
    severity_rank = {
        'critical': 4.0,
        'high': 3.0,
        'warning': 2.0,
        'medium': 1.0,
        'info': 0.0,
    }.get(str(getattr(row, 'severity', '')).lower(), 0.0)
    evidence = row.evidence_json or {}
    confidence = _to_float(evidence.get('confidence'), 0.65)
    evidence_level = str(evidence.get('evidence_level', '')).upper()
    evidence_rank = {'A': 1.0, 'B': 0.75, 'C': 0.5}.get(evidence_level, 0.6)
    age_days = 0.0
    generated_at = _parse_datetime(getattr(row, 'generated_at', None))
    if generated_at:
        age_days = max(0.0, (datetime.now(timezone.utc) - generated_at).total_seconds() / 86400.0)
    recency_rank = 1.0 if age_days <= 7 else 0.6 if age_days <= 30 else 0.3
    score = (severity_rank * 0.5) + (confidence * 0.2) + (evidence_rank * 0.15) + (recency_rank * 0.15)
    return score, confidence, -age_days


def _build_context(metrics: list[Any], symptoms: list[Any], alerts: list[Any]) -> dict[str, Any]:
    systolic = [m.systolic_bp for m in metrics if m.systolic_bp is not None][:3]
    chronic = [s for s in symptoms if getattr(s, 'estimated_duration_days', 0) and s.estimated_duration_days >= 180]
    return {
        'has_three_bp': len(systolic) == 3,
        'avg_systolic': (sum(systolic) / len(systolic)) if systolic else None,
        'chronic_count': len(chronic),
        'alert_count': len(alerts),
        'overall_score': max(0, 100 - len(alerts) * 5),
    }


def _mock_llm_summary(text: str, insight_type: str) -> str:
    return f"[LLM-mock:{insight_type}] {text}"


def _uuid_or_raw(value: str):
    try:
        return uuid.UUID(value)
    except ValueError:
        return value


def _to_int(value: Any, fallback: int | None = None) -> int | None:
    try:
        if value is None:
            return fallback
        return int(float(value))
    except (TypeError, ValueError):
        return fallback


def _to_float(value: Any, fallback: float = 0.0) -> float:
    try:
        if value is None:
            return fallback
        return float(value)
    except (TypeError, ValueError):
        return fallback


def _extract_previous_score(previous_narrative: dict[str, Any] | str | None) -> int | None:
    if isinstance(previous_narrative, dict):
        candidate = previous_narrative.get('health_score') or previous_narrative.get('overall_score') or previous_narrative.get('score')
        return _to_int(candidate)
    return None


def _time_window_phrase(previous_narrative: dict[str, Any] | str | None, context: dict[str, Any]) -> str:
    if isinstance(previous_narrative, dict):
        prev_time = previous_narrative.get('created_at') or previous_narrative.get('generated_at')
        if prev_time:
            try:
                prev_dt = datetime.fromisoformat(str(prev_time).replace('Z', '+00:00'))
                days = max(1, int((datetime.now(timezone.utc) - prev_dt).days))
                if days <= 7:
                    return '上週'
                if days <= 30:
                    return f'過去 {days} 天'
                return f'過去 {days // 30} 個月'
            except ValueError:
                pass
    trends = context.get('trends') or {}
    max_points = max((len(points) for points in trends.values() if isinstance(points, list)), default=0)
    if max_points >= 2:
        return '過去 7 天'
    return '最近'


def _metric_direction_label(metric_key: str, delta: float) -> str:
    if metric_key == 'sleep_hours':
        if delta > 0:
            return '變好'
        if delta < 0:
            return '變差'
        return '穩定'
    if delta < 0:
        return '變好'
    if delta > 0:
        return '變差'
    return '穩定'


def _build_delta_summary(
    score_delta: int | None,
    current: dict[str, Any],
    score_window: str,
    previous_narrative: dict[str, Any] | str | None,
    context: dict[str, Any],
) -> str:
    trend_hint = _top_metric_change(context.get('trends') or {})
    risk_level = _risk_level_label(str(context.get('risk_level') or 'low'))

    if score_delta is None:
        base = f'{score_window} 的健康狀況看起來大致穩定'
    elif score_delta >= 5:
        base = f'與{score_window}相比，你的健康狀況略有改善'
    elif score_delta <= -5:
        base = f'與{score_window}相比，你的健康狀況有些變差'
    else:
        base = f'與{score_window}相比，你的健康狀況沒有明顯變化'

    if trend_hint:
        base = f'{base}，{trend_hint}'

    if current.get('actions'):
        base = f'{base}，目前的行動已開始帶來一些回饋'

    if isinstance(previous_narrative, dict):
        return f'{base}。'
    return f'{base}，目前仍屬於{risk_level}。'


def _top_metric_change(trends: dict[str, Any]) -> str | None:
    candidates: list[tuple[float, str]] = []
    for metric_key, points in trends.items():
        if not isinstance(points, list) or len(points) < 2:
            continue
        first = _point_value(points[0])
        last = _point_value(points[-1])
        delta = last - first
        if abs(delta) < 0.1:
            continue
        label = _metric_name(metric_key)
        if metric_key == 'sleep_hours':
            if delta > 0:
                candidates.append((abs(delta), f'{label}比之前更充足'))
            else:
                candidates.append((abs(delta), f'{label}比之前更不足'))
        else:
            if delta < 0:
                candidates.append((abs(delta), f'{label}有下降，方向比較好'))
            else:
                candidates.append((abs(delta), f'{label}有上升，需要持續留意'))
    if not candidates:
        return None
    return max(candidates, key=lambda item: item[0])[1]


def _build_improvements(context: dict[str, Any], previous_narrative: dict[str, Any] | str | None, score_delta: int | None) -> list[str]:
    items: list[str] = []
    trends = context.get('trends') or {}
    if 'weight_kg' in trends:
        trend = _trend_change_text('體重', trends['weight_kg'], direction_hint='下降')
        if trend:
            items.append(trend)
    if 'systolic_bp' in trends:
        trend = _trend_change_text('血壓', trends['systolic_bp'], direction_hint='下降')
        if trend:
            items.append(trend)
    if score_delta is not None and score_delta > 0:
        items.append('整體健康分數比上次高了一些。')
    for action in context.get('actions') or []:
        if str(getattr(action, 'status', '')).lower() == 'done':
            items.append(f'已完成「{getattr(action, "title", "一項行動")}」，代表你開始把追蹤做起來了。')
        elif (getattr(action, 'streak', 0) or 0) >= 3:
            items.append(f'「{getattr(action, "title", "一項行動")}」已連續執行 {getattr(action, "streak", 0)} 天。')
    if not items and isinstance(previous_narrative, dict) and previous_narrative.get('summary_text'):
        items.append('和上次相比，至少有些指標沒有繼續惡化。')
    return items or ['目前沒有明顯改善訊號，但也沒有看到大幅惡化。']


def _build_deteriorations(context: dict[str, Any], previous_narrative: dict[str, Any] | str | None, score_delta: int | None) -> list[str]:
    items: list[str] = []
    trends = context.get('trends') or {}
    if 'systolic_bp' in trends:
        trend = _trend_change_text('血壓', trends['systolic_bp'], direction_hint='上升')
        if trend:
            items.append(trend)
    if 'sleep_hours' in trends:
        trend = _trend_change_text('睡眠', trends['sleep_hours'], direction_hint='下降', reverse_for_sleep=True)
        if trend:
            items.append(trend)
    if score_delta is not None and score_delta < 0:
        items.append('整體健康分數比上次低了一些。')
    for risk in context.get('alerts') or []:
        title = str(getattr(risk, 'title', '風險提醒'))
        if title:
            items.append(f'{title} 仍在提醒範圍內，表示這件事還沒有真正穩住。')
    return items or ['目前沒有明確惡化，但風險也還沒完全解除。']


def _build_adherence(context: dict[str, Any]) -> list[str]:
    items: list[str] = []
    for action in context.get('actions') or []:
        title = str(getattr(action, 'title', '行動'))
        streak = _to_int(getattr(action, 'streak', None), 0) or 0
        status = str(getattr(action, 'status', '')).lower()
        if status == 'done' and streak > 0:
            items.append(f'已持續完成「{title}」{streak} 天。')
        elif status == 'done':
            items.append(f'已完成「{title}」。')
        elif status == 'in_progress' and streak > 0:
            items.append(f'「{title}」已連續執行 {streak} 天，節奏還算穩定。')
        elif status in {'todo', 'snoozed'}:
            items.append(f'「{title}」還沒開始或還在暫停中。')
    if not items:
        items.append('目前還沒有足夠的行動資料可判斷執行狀況。')
    return items


def _build_missed_risks(context: dict[str, Any]) -> list[str]:
    items: list[str] = []
    actions = context.get('actions') or []
    alerts = context.get('alerts') or []
    symptoms = context.get('symptoms') or []
    action_text = ' '.join(str(getattr(action, 'title', '')) for action in actions)

    for alert in alerts:
        title = str(getattr(alert, 'title', '風險提醒'))
        if title and title not in action_text:
            items.append(f'{title} 已經出現提醒，但還沒有對應的追蹤行動。')

    for symptom in symptoms:
        duration = _to_int(getattr(symptom, 'estimated_duration_days', None))
        if duration and duration >= 365:
            symptom_name = str(getattr(symptom, 'symptom', '症狀'))
            items.append(f'{symptom_name} 已持續約 {_format_duration_days(duration)}，但看起來還沒有被當成主要追蹤重點。')

    if not items:
        items.append('目前沒有看到明顯被忽略的風險。')
    return items


def _trend_change_text(metric_label: str, points: list[Any], direction_hint: str, reverse_for_sleep: bool = False) -> str | None:
    if not isinstance(points, list) or len(points) < 2:
        return None
    first = _point_value(points[0])
    last = _point_value(points[-1])
    delta = last - first
    if abs(delta) < 0.1:
        return None
    if reverse_for_sleep:
        if delta < 0:
            return f'{metric_label}在過去 {max(1, len(points))} 筆資料中有下降，這會讓整體狀態更不容易穩定。'
        return f'{metric_label}在過去 {max(1, len(points))} 筆資料中有上升，算是比較好的方向。'
    if direction_hint == '下降' and delta < 0:
        return f'{metric_label}在過去 {max(1, len(points))} 筆資料中有下降，方向比之前好一些。'
    if direction_hint == '上升' and delta > 0:
        return f'{metric_label}在過去 {max(1, len(points))} 筆資料中有上升，這代表風險還沒完全穩住。'
    return None


def _point_value(point: Any) -> float:
    if isinstance(point, dict):
        return float(point.get('value', 0) or 0)
    return float(getattr(point, 'value', 0) or 0)


def _parse_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _normalize_text(value: Any) -> str:
    if value is None:
        return ''
    if isinstance(value, (list, tuple, set)):
        return ' | '.join(_normalize_text(item) for item in value)
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return str(value).strip()


def _normalize_list(value: Any) -> list[str]:
    if not value:
        return []
    if isinstance(value, list):
        return [_normalize_text(item) for item in value]
    return [_normalize_text(value)]


def _snapshot_hash(alerts: list[Any]) -> str | None:
    if not alerts:
        return None
    normalized = []
    for alert in alerts:
        if isinstance(alert, dict):
            getter = alert.get
        else:
            getter = lambda key, default=None, _alert=alert: getattr(_alert, key, default)
        normalized.append(
            {
                'id': getter('id') and str(getter('id')),
                'title': _normalize_text(getter('title')),
                'severity': _normalize_text(getter('severity')),
                'rule_id': _normalize_text(getter('rule_id')),
            }
        )
    digest = json.dumps(sorted(normalized, key=lambda item: (item['severity'], item['title'])), ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(digest.encode('utf-8')).hexdigest()


def build_alert_snapshot_hash(alerts: list[Any]) -> str | None:
    return _snapshot_hash(alerts)


def _narrative_filter_query(db: Session, user_id: str, person_id: str, include_legacy: bool, summary_type: str | None = None):
    user_key = _uuid_or_raw(user_id)
    person_key = _uuid_or_raw(person_id)
    query = db.query(AISummary).filter(AISummary.user_id == user_key)
    summary_filter = AISummary.subject_profile_id == person_key
    if include_legacy:
        summary_filter = or_(summary_filter, AISummary.subject_profile_id.is_(None))
    query = query.filter(summary_filter)
    if summary_type:
        query = query.filter(AISummary.summary_type == summary_type)
    return query


def _fetch_narrative_row(
    db: Session,
    user_id: str,
    person_id: str,
    include_legacy: bool,
    summary_type: str | None = None,
    offset: int = 0,
):
    query = _narrative_filter_query(db, user_id, person_id, include_legacy, summary_type=summary_type)
    return (
        query.order_by(AISummary.generated_at.desc(), AISummary.created_at.desc())
        .offset(offset)
        .limit(1)
        .first()
    )


def _serialize_narrative_row(row: AISummary | None) -> dict[str, Any] | None:
    if row is None:
        return None
    payload = dict(row.narrative_json or {})
    generated_at = row.generated_at or row.created_at
    generated_at_iso = generated_at.isoformat() if generated_at else None
    created_at_iso = row.created_at.isoformat() if row.created_at else generated_at_iso
    if not payload:
        payload = {
            'summary': row.summary_text,
            'risks': [row.abnormal_explanation] if row.abnormal_explanation else [],
            'trends': [],
            'reasons': [],
            'actions': [row.recommendations] if row.recommendations else [],
            'delta_summary': row.summary_text,
            'improvements': [],
            'deteriorations': [],
            'adherence': [],
            'missed_risks': [],
        }
    payload.setdefault('summary', payload.get('health_narrative_v2', {}).get('summary') if isinstance(payload.get('health_narrative_v2'), dict) else row.summary_text)
    payload.setdefault('summary_text', row.summary_text)
    payload.setdefault('generated_at', generated_at_iso)
    payload.setdefault('created_at', created_at_iso)
    payload.setdefault('narrative_version', row.narrative_version or ('v2' if payload.get('health_narrative_v2') else 'v1'))
    payload.setdefault('summary_type', row.summary_type or 'daily')
    payload.setdefault('risk_level', payload.get('risk_level'))
    payload.setdefault('based_on_score_id', str(row.based_on_score_id) if row.based_on_score_id else payload.get('based_on_score_id'))
    payload.setdefault('based_on_alert_snapshot', row.based_on_alert_snapshot or payload.get('based_on_alert_snapshot'))
    if 'health_narrative' not in payload:
        payload['health_narrative'] = {
            'summary': payload.get('summary') or row.summary_text,
            'risks': payload.get('risks', []),
            'trends': payload.get('trends', []),
            'reasons': payload.get('reasons', []),
            'actions': payload.get('actions', []),
        }
    if 'health_narrative_v2' not in payload:
        payload['health_narrative_v2'] = {
            'summary': payload.get('summary') or row.summary_text,
            'risks': payload.get('risks', []),
            'trends': payload.get('trends', []),
            'reasons': payload.get('reasons', []),
            'actions': payload.get('actions', []),
            'delta_summary': payload.get('delta_summary') or row.summary_text,
            'improvements': payload.get('improvements', []),
            'deteriorations': payload.get('deteriorations', []),
            'adherence': payload.get('adherence', []),
            'missed_risks': payload.get('missed_risks', []),
        }
    return payload


def _risk_level_label(risk_level: str) -> str:
    normalized = str(risk_level or 'low').lower()
    if normalized in {'high', 'elevated'}:
        return '高風險'
    if normalized in {'moderate', 'medium'}:
        return '中度風險'
    return '低風險'


def _metric_name(metric_key: str) -> str:
    mapping = {
        'systolic_bp': '血壓',
        'blood_glucose': '血糖',
        'weight_kg': '體重',
        'sleep_hours': '睡眠',
    }
    return mapping.get(metric_key, metric_key)


def _format_duration_days(days: int | None) -> str | None:
    if not days or days <= 0:
        return None
    if days >= 365 * 20:
        return f'{days // 365}年'
    if days >= 365:
        return f'{days // 365}年'
    if days >= 30:
        return f'{days // 30}個月'
    if days >= 14:
        return f'{days // 7}週'
    return f'{days}天'


def _build_narrative_summary(
    risk_level: str,
    alerts: list[Any],
    trends: dict[str, Any],
    symptoms: list[Any],
    labs: list[Any],
    health_score: dict[str, Any],
) -> str:
    problems: list[str] = []
    if any('血壓' in str(getattr(alert, 'title', '')) or 'blood pressure' in str(getattr(alert, 'title', '')).lower() for alert in alerts):
        problems.append('近期血壓偏高')
    if any('尿酸' in str(getattr(lab, 'item_name', '')) for lab in labs):
        problems.append('尿酸長期偏高')
    if any('alt' in str(getattr(lab, 'item_name', '')).lower() or '肝' in str(getattr(lab, 'item_name', '')) for lab in labs):
        problems.append('肝功能指標偏高')
    if not problems:
        for metric_key, points in list((trends or {}).items())[:4]:
            trend_summary = _summarize_trend(metric_key, points)
            if trend_summary and '變差' in trend_summary:
                problems.append(f'{_metric_name(metric_key)}最近有變化')
    if not problems:
        long_term = next((symptom for symptom in symptoms if getattr(symptom, 'estimated_duration_days', 0) and symptom.estimated_duration_days >= 365), None)
        if long_term:
            problems.append(f'{getattr(long_term, "symptom", "長期症狀")}持續很久')
    if not problems:
        score = health_score.get('overall_score')
        if isinstance(score, (int, float)):
            problems.append(f'健康分數目前約 {int(score)} 分')
        else:
            problems.append('目前需要持續追蹤關鍵指標')
    return f"你的健康目前處於「{_risk_level_label(risk_level)}」，主要問題來自" + '、'.join(problems[:3]) + '。'


def _build_narrative_risks(alerts: list[Any], labs: list[Any], insights: list[Any]) -> list[str]:
    risks: list[str] = []
    if any('血壓' in str(getattr(alert, 'title', '')) or 'blood pressure' in str(getattr(alert, 'title', '')).lower() for alert in alerts):
        risks.append('心血管風險增加，因為最近血壓持續偏高。')
    uric_item = next((lab for lab in labs if '尿酸' in str(getattr(lab, 'item_name', ''))), None)
    if uric_item:
        risks.append('痛風發作的可能增加，因為尿酸已經偏高一段時間。')
    liver_item = next((lab for lab in labs if 'alt' in str(getattr(lab, 'item_name', '')).lower() or 'ast' in str(getattr(lab, 'item_name', '')).lower()), None)
    if liver_item:
        risks.append('肝臟負擔可能增加，因為肝功能指標沒有回到穩定區間。')
    if not risks and insights:
        risks.extend([f"{getattr(insight, 'title', '健康風險')}，建議持續追蹤。" for insight in insights[:2]])
    if not risks:
        risks.append('目前沒有看到非常明確的高風險訊號，但仍建議持續追蹤血壓、血糖與體重。')
    return risks


def _summarize_trend(metric_key: str, points: list[Any]) -> str | None:
    if not points or len(points) < 2:
        return None
    def _point_value(point: Any) -> float:
        if isinstance(point, dict):
            return float(point.get('value', 0) or 0)
        return float(getattr(point, 'value', 0) or 0)

    first = _point_value(points[0])
    last = _point_value(points[-1])
    delta = last - first
    if abs(delta) < 0.5:
        return f'{_metric_name(metric_key)}最近維持穩定'
    days = 14 if len(points) >= 2 else 7
    if metric_key == 'sleep_hours':
        if delta < 0:
            return f'{_metric_name(metric_key)}在過去 {days // 7} 週變差'
        return f'{_metric_name(metric_key)}在過去 {days // 7} 週有變好'
    if delta > 0:
        return f'{_metric_name(metric_key)}在過去 {days // 7} 週變差'
    return f'{_metric_name(metric_key)}在過去 {days // 7} 週有變好'


def _build_narrative_trends(trends: dict[str, Any], symptoms: list[Any], metrics: list[Any]) -> list[str]:
    trend_lines: list[str] = []
    for metric_key, points in (trends or {}).items():
        summary = _summarize_trend(metric_key, points)
        if not summary:
            continue
        if '穩定' in summary:
            trend_lines.append(summary + '。')
        elif '變差' in summary:
            trend_lines.append(summary.replace('變差', '呈變差趨勢') + '。')
        else:
            trend_lines.append(summary.replace('有變好', '呈改善趨勢') + '。')

    long_term_symptom = next((symptom for symptom in symptoms if getattr(symptom, 'estimated_duration_days', 0) and symptom.estimated_duration_days >= 14), None)
    if long_term_symptom:
        duration = _format_duration_days(getattr(long_term_symptom, 'estimated_duration_days', None))
        trend_lines.append(f"{getattr(long_term_symptom, 'symptom', '症狀')}已持續 {duration}，代表這不是短期波動。")

    if not trend_lines and metrics:
        trend_lines.append('最近的量測資料還不夠多，暫時只能先當作基線觀察。')
    return trend_lines


def _build_narrative_reasons(
    symptoms: list[Any],
    metrics: list[Any],
    alerts: list[Any],
    labs: list[Any],
    actions: list[Any],
) -> list[str]:
    reasons: list[str] = []
    long_term_symptom = next((symptom for symptom in symptoms if getattr(symptom, 'estimated_duration_days', 0)), None)
    if long_term_symptom:
        duration = _format_duration_days(getattr(long_term_symptom, 'estimated_duration_days', None))
        if duration:
            reasons.append(f"{getattr(long_term_symptom, 'symptom', '這個症狀')}已持續約 {duration}。")

    latest_metric = metrics[0] if metrics else None
    if latest_metric and getattr(latest_metric, 'sleep_hours', None) is not None and float(latest_metric.sleep_hours) < 6:
        reasons.append('最近睡眠偏少，可能讓血壓、體重或疲勞感更不容易穩定。')
    if alerts:
        reasons.append('最近已有風險提醒出現，表示這不是單次量測偏差。')
    if any((getattr(action, 'status', '') in {'todo', 'in_progress'}) for action in actions):
        reasons.append('目前有追蹤項目還沒完成，所以系統還看不到改善是否真正發生。')
    if not reasons and labs:
        reasons.append('最近的健檢與量測資料顯示部分指標還沒有完全回到穩定區間。')
    if not reasons:
        reasons.append('目前資料還有限，但已經看到值得提早處理的訊號。')
    return reasons


def _build_narrative_actions(
    alerts: list[Any],
    trends: dict[str, Any],
    symptoms: list[Any],
    labs: list[Any],
    actions: list[Any],
) -> list[str]:
    action_lines: list[str] = []
    if any('血壓' in str(getattr(alert, 'title', '')) or 'blood pressure' in str(getattr(alert, 'title', '')).lower() for alert in alerts):
        action_lines.append('每天固定量血壓並連續記錄 7 天，先確認是否持續偏高。')
    if any('尿酸' in str(getattr(lab, 'item_name', '')) for lab in labs):
        action_lines.append('這週先減少高普林食物，例如內臟、濃湯與部分海鮮。')
    if any('腰' in str(getattr(symptom, 'symptom', '')) or '腰' in str(getattr(symptom, 'note', '')) for symptom in symptoms):
        action_lines.append('每天安排 10 分鐘腰背伸展，並記錄症狀有沒有變輕。')
    if 'sleep_hours' in (trends or {}):
        action_lines.append('這週把睡眠時間拉回 7 小時左右，連續觀察 7 天。')
    if any(getattr(action, 'status', '') in {'todo', 'in_progress'} for action in actions):
        action_lines.append('先完成目前最上面的待辦任務，讓系統能判斷你是在變好還是停滯。')
    if len(action_lines) < 3:
        action_lines.extend(
            [
                '每天記錄一次體重或血糖，先把近期變化補齊。',
                '把最近讓你不舒服的症狀寫下來，包含多久一次、持續多久。',
                '若同一項風險連續幾週沒有下降，安排回診或進一步追蹤。',
            ]
        )
    deduped: list[str] = []
    for line in action_lines:
        if line not in deduped:
            deduped.append(line)
    return deduped
