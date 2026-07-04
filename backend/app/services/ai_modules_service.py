from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import logging
import re
from pathlib import Path
from typing import Any

from openai import OpenAI
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.constants import MEDICAL_DISCLAIMER
from app.models.entities import HealthMetric, LabReport, LabReportItem, PersonProfile, RiskAlert, SymptomLog
from app.orchestrator.execution_policy import evaluate_llm_execution, record_llm_call
from app.services.ai_guardrail_service import apply_guardrails, evaluate_guarded_output

settings = get_settings()

logger = logging.getLogger(__name__)

PROMPT_DIR = Path(__file__).resolve().parents[3] / 'ai' / 'prompts'
PROMPT_FILES = {
    'health_check_interpreter': 'health_check_interpreter_prompt.md',
    'symptom_analysis': 'symptom_analysis_prompt.md',
    'health_risk_prediction': 'health_risk_prediction_prompt.md',
}


def run_ai_module(
    db: Session,
    user_id: str,
    person: PersonProfile,
    module: str,
    days: int = 90,
    focus: str | None = None,
    max_items: int = 5,
) -> tuple[dict[str, Any], dict[str, Any]]:
    context = _build_context(db, user_id, person, days)
    prompt = _build_prompt(module, context, focus, max_items)

    raw_output, model_name = _call_model(module, prompt, context, max_items)

    guarded_output, guardrail_report = apply_guardrails(
        module=module,
        output=raw_output,
        allowed_evidence_ids=set(context['evidence_ids']),
        max_items=max_items,
    )

    if not guarded_output['health_risks']:
        guarded_output['health_risks'] = [
            {
                'title': '資料不足需追蹤',
                'level': 'medium',
                'reason': '可用證據不足，建議補充近期健康紀錄與健檢。',
                'evidence_ids': context['evidence_ids'][:1],
            }
        ]

    response = {
        'module': module,
        'model_name': model_name,
        'generated_at': datetime.now(timezone.utc),
        'health_risks': guarded_output['health_risks'],
        'lifestyle_recommendations': guarded_output['lifestyle_recommendations'],
        'follow_up_items': guarded_output['follow_up_items'],
        'confidence': float(guarded_output.get('confidence', 0.5)),
        'guardrail_report': guardrail_report,
        'disclaimer': MEDICAL_DISCLAIMER,
    }

    evaluation = evaluate_guarded_output(guarded_output, guardrail_report)
    evaluation['module'] = module
    return response, evaluation


def _build_context(db: Session, user_id: str, person: PersonProfile, days: int) -> dict[str, Any]:
    start = datetime.now(timezone.utc) - timedelta(days=days)

    metric_filter = HealthMetric.subject_profile_id == person.id
    symptom_filter = SymptomLog.subject_profile_id == person.id
    alert_filter = RiskAlert.subject_profile_id == person.id
    report_filter = LabReport.subject_profile_id == person.id
    if person.is_default:
        metric_filter = or_(metric_filter, HealthMetric.subject_profile_id.is_(None))
        symptom_filter = or_(symptom_filter, SymptomLog.subject_profile_id.is_(None))
        alert_filter = or_(alert_filter, RiskAlert.subject_profile_id.is_(None))
        report_filter = or_(report_filter, LabReport.subject_profile_id.is_(None))
    metrics = (
        db.query(HealthMetric)
        .filter(HealthMetric.user_id == user_id, HealthMetric.recorded_at >= start, metric_filter)
        .order_by(HealthMetric.recorded_at.desc())
        .limit(50)
        .all()
    )
    symptoms = (
        db.query(SymptomLog)
        .filter(SymptomLog.user_id == user_id, SymptomLog.occurred_at >= start, symptom_filter)
        .order_by(SymptomLog.occurred_at.desc())
        .limit(50)
        .all()
    )
    alerts = (
        db.query(RiskAlert)
        .filter(RiskAlert.user_id == user_id, alert_filter)
        .order_by(RiskAlert.created_at.desc())
        .limit(30)
        .all()
    )
    lab_items = (
        db.query(LabReportItem)
        .join(LabReport, LabReportItem.report_id == LabReport.id)
        .filter(LabReport.user_id == user_id, LabReport.created_at >= start, report_filter)
        .order_by(LabReportItem.captured_at.desc())
        .limit(80)
        .all()
    )

    evidence_ids: list[str] = []

    metric_payload = []
    for m in metrics:
        evidence_id = f'METRIC:{m.id}'
        evidence_ids.append(evidence_id)
        metric_payload.append(
            {
                'evidence_id': evidence_id,
                'recorded_at': m.recorded_at.isoformat(),
                'systolic_bp': m.systolic_bp,
                'diastolic_bp': m.diastolic_bp,
                'heart_rate': m.heart_rate,
                'blood_glucose': float(m.blood_glucose) if m.blood_glucose is not None else None,
                'weight_kg': float(m.weight_kg) if m.weight_kg is not None else None,
                'sleep_hours': float(m.sleep_hours) if m.sleep_hours is not None else None,
            }
        )

    symptom_payload = []
    for s in symptoms:
        evidence_id = f'SYMPTOM:{s.id}'
        evidence_ids.append(evidence_id)
        symptom_payload.append(
            {
                'evidence_id': evidence_id,
                'symptom': s.symptom,
                'occurred_at': s.occurred_at.isoformat(),
                'duration_minutes': s.duration_minutes,
                'severity': s.severity,
                'note': s.note,
            }
        )

    lab_payload = []
    for item in lab_items:
        evidence_id = f'LAB_ITEM:{item.id}'
        evidence_ids.append(evidence_id)
        lab_payload.append(
            {
                'evidence_id': evidence_id,
                'item_name': item.item_name,
                'value_num': float(item.value_num) if item.value_num is not None else None,
                'unit': item.unit,
                'ref_range': item.ref_range,
                'abnormal_flag': item.abnormal_flag,
            }
        )

    alert_payload = []
    for alert in alerts:
        evidence_id = f'ALERT:{alert.id}'
        evidence_ids.append(evidence_id)
        alert_payload.append(
            {
                'evidence_id': evidence_id,
                'severity': alert.severity,
                'title': alert.title,
                'message': alert.message,
                'created_at': alert.created_at.isoformat(),
            }
        )

    profile_payload = {
        'evidence_id': f'PROFILE:{person.id}',
        'full_name': person.display_name,
        'gender': person.gender,
        'height_cm': float(person.height_cm) if person.height_cm is not None else None,
        'weight_kg': float(person.weight_kg) if person.weight_kg is not None else None,
        'allergies': person.allergies,
        'family_history': person.family_history,
        'chronic_conditions': person.chronic_conditions,
    }
    evidence_ids.append(profile_payload['evidence_id'])

    return {
        'profile': profile_payload,
        'metrics': metric_payload,
        'symptoms': symptom_payload,
        'lab_items': lab_payload,
        'alerts': alert_payload,
        'evidence_ids': evidence_ids,
    }


def _build_prompt(module: str, context: dict[str, Any], focus: str | None, max_items: int) -> str:
    template = _load_prompt_template(module)
    context_text = json.dumps(context, ensure_ascii=False)
    focus_text = focus or '無特定焦點，請綜合分析。'

    return (
        f'{template}\n\n'
        f'分析焦點: {focus_text}\n'
        f'最多輸出項目: {max_items}\n'
        f'可用資料(JSON): {context_text}\n'
        f'請務必僅使用資料中的 evidence_ids。\n'
        f'最後請附帶免責聲明概念，但不得輸出醫療診斷。'
    )


def _load_prompt_template(module: str) -> str:
    filename = PROMPT_FILES.get(module)
    if not filename:
        return '你是健康分析助手，請輸出結構化 JSON。'

    path = PROMPT_DIR / filename
    if path.exists():
        return path.read_text(encoding='utf-8')

    return '你是健康分析助手，請輸出結構化 JSON。'


def _call_model(module: str, prompt: str, context: dict[str, Any], max_items: int) -> tuple[dict[str, Any], str]:
    policy = evaluate_llm_execution(source='api-direct')
    if settings.openai_api_key and policy.allowed:
        try:
            record_llm_call(source='api-direct', provider='openai', model=settings.openai_model)
            client = OpenAI(api_key=settings.openai_api_key)
            completion = client.responses.create(
                model=settings.openai_model,
                input=prompt,
                temperature=0.2,
            )
            parsed = _safe_json_load(completion.output_text)
            if parsed is None:
                parsed = _fallback_output(module, context, max_items)
            return parsed, settings.openai_model
        except Exception as exc:
            logger.error("OpenAI call failed in _call_model: %s", exc)
            return _fallback_output(module, context, max_items), "rule-based-fallback"

    if settings.openai_api_key and not policy.allowed:
        return _fallback_output(module, context, max_items), f'policy-fallback:{policy.code.lower()}'

    return _fallback_output(module, context, max_items), 'rule-based-fallback'


def _safe_json_load(text: str) -> dict[str, Any] | None:
    content = text.strip()
    content = re.sub(r'^```json\s*', '', content)
    content = re.sub(r'```$', '', content)

    try:
        return json.loads(content)
    except Exception:
        pass

    match = re.search(r'\{[\s\S]*\}', content)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except Exception:
        return None


def _fallback_output(module: str, context: dict[str, Any], max_items: int) -> dict[str, Any]:
    risks: list[dict[str, Any]] = []
    recommendations: list[dict[str, Any]] = []
    follow_ups: list[dict[str, Any]] = []

    for alert in context['alerts'][:max_items]:
        risks.append(
            {
                'title': alert['title'],
                'level': str(alert['severity']).lower() if alert.get('severity') else 'medium',
                'reason': alert['message'],
                'evidence_ids': [alert['evidence_id']],
            }
        )

    abnormal_lab = [item for item in context['lab_items'] if item.get('abnormal_flag') in {'H', 'L'}]
    for item in abnormal_lab[:max_items]:
        follow_ups.append(
            {
                'item': f"追蹤檢驗：{item['item_name']}",
                'timeline': '2-4 週內複檢',
                'why': f"近期數值異常 ({item.get('abnormal_flag')})。",
                'evidence_ids': [item['evidence_id']],
            }
        )

    if module == 'symptom_analysis':
        top_symptoms = sorted(context['symptoms'], key=lambda x: x.get('severity') or 0, reverse=True)[:max_items]
        for symptom in top_symptoms:
            risks.append(
                {
                    'title': f"症狀風險：{symptom['symptom']}",
                    'level': 'high' if (symptom.get('severity') or 0) >= 4 else 'medium',
                    'reason': '症狀嚴重度較高，建議持續觀察。',
                    'evidence_ids': [symptom['evidence_id']],
                }
            )

    recommendations.append(
        {
            'title': '規律生活作息',
            'action': '保持每週至少 150 分鐘中強度運動，並維持規律睡眠。',
            'priority': 'high',
            'evidence_ids': [context['profile']['evidence_id']],
        }
    )

    return {
        'health_risks': risks[:max_items],
        'lifestyle_recommendations': recommendations[:max_items],
        'follow_up_items': follow_ups[:max_items],
        'confidence': 0.65,
    }
