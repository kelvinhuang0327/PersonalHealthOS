from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

from app.models.entities import HealthMetric, LabReportItem, PersonProfile, RiskAlert

RULE_FILE = Path(__file__).resolve().parent.parent / 'config' / 'risk_rules.json'


def load_rules() -> dict[str, Any]:
    with RULE_FILE.open('r', encoding='utf-8') as fp:
        return json.load(fp)


def evaluate_metric_risks(user_id: uuid.UUID | str, profile: PersonProfile | None, metric: HealthMetric) -> list[RiskAlert]:
    rules = load_rules()
    alerts: list[RiskAlert] = []

    if profile and profile.height_cm and metric.weight_kg:
        height_m = float(profile.height_cm) / 100
        bmi = float(metric.weight_kg) / (height_m * height_m)
        bmi_rules = rules.get('bmi', {})
        if bmi < bmi_rules['underweight']['lt']:
            alerts.append(_make_alert(user_id, 'health_metric', metric.id, 'BMI_UNDER', bmi_rules['underweight']))
        elif bmi >= bmi_rules['obese']['gte']:
            alerts.append(_make_alert(user_id, 'health_metric', metric.id, 'BMI_OBESE', bmi_rules['obese']))
        elif bmi >= bmi_rules['overweight']['gte']:
            alerts.append(_make_alert(user_id, 'health_metric', metric.id, 'BMI_OVER', bmi_rules['overweight']))

    bp_rule = rules.get('blood_pressure', {}).get('elevated')
    if bp_rule and (
        (metric.systolic_bp is not None and metric.systolic_bp >= bp_rule['systolic_gte'])
        or (metric.diastolic_bp is not None and metric.diastolic_bp >= bp_rule['or_diastolic_gte'])
    ):
        alerts.append(_make_alert(user_id, 'health_metric', metric.id, 'BP_HIGH', bp_rule))

    glucose_rule = rules.get('blood_glucose', {}).get('elevated')
    if glucose_rule and metric.blood_glucose is not None and float(metric.blood_glucose) >= glucose_rule['gte']:
        alerts.append(_make_alert(user_id, 'health_metric', metric.id, 'GLUCOSE_HIGH', glucose_rule))

    return alerts


def evaluate_lab_item_risks(user_id: uuid.UUID | str, item: LabReportItem) -> list[RiskAlert]:
    rules = load_rules()
    alerts: list[RiskAlert] = []

    def check_block(block: dict[str, Any], prefix: str):
        for code, rule in block.items():
            if rule.get('item_name', '').lower() != item.item_name.lower():
                continue
            value = float(item.value_num or 0)
            if ('gte' in rule and value >= rule['gte']) or ('lt' in rule and value < rule['lt']):
                alerts.append(_make_alert(user_id, 'lab_report', item.report_id, f'{prefix}_{code}'.upper(), rule))

    check_block(rules.get('liver_function', {}), 'LIVER')
    check_block(rules.get('uric_acid', {}), 'UA')
    check_block(rules.get('lipids', {}), 'LIPID')
    return alerts


def _make_alert(user_id: uuid.UUID | str, source_type: str, source_id: Any, rule_code: str, rule: dict[str, Any]) -> RiskAlert:
    if isinstance(user_id, str):
        user_id = uuid.UUID(user_id)
    return RiskAlert(
        user_id=user_id,
        risk_type=rule_code.lower(),
        source_type=source_type,
        source_id=source_id,
        rule_code=rule_code,
        severity=rule['severity'],
        title=rule['title'],
        message=rule['message'],
        description=rule.get('description') or rule['message'],
        recommendation=rule.get('recommendation') or '建議持續追蹤並視情況就醫。',
        status='active',
    )
