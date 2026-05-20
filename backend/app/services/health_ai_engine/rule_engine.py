from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from app.services.health_ai_engine.guideline_registry import enrich_explainability


RULES_DIR = Path(__file__).resolve().parent / 'rules'


def load_rules(rule_file: str) -> list[dict[str, Any]]:
    path = RULES_DIR / rule_file
    if not path.exists():
        return []
    with path.open('r', encoding='utf-8') as fp:
        data = yaml.safe_load(fp) or {}
    if isinstance(data, list):
        return data
    return data.get('rules', [])


def evaluate_rule(rule: dict[str, Any], context: dict[str, Any]) -> bool:
    if not rule.get('enabled', True):
        return False
    return _eval_conditions(rule.get('conditions') or {}, context)


def evaluate_rules(rule_set: list[dict[str, Any]], context: dict[str, Any]) -> list[dict[str, Any]]:
    matched = [rule for rule in rule_set if evaluate_rule(rule, context)]
    matched.sort(key=lambda r: int(r.get('priority', 0)), reverse=True)
    for rule in matched:
        rule['_explainability'] = enrich_explainability(
            {
            'rule_id': rule.get('id'),
            'category': rule.get('category'),
            'priority': int(rule.get('priority', 0)),
            'confidence': float(rule.get('confidence', 0)),
            'evidence_level': rule.get('evidence_level', 'B'),
            'guideline_source': rule.get('guideline_source', 'Rule Library'),
            }
        )
    return matched


def _eval_conditions(conditions: dict[str, Any], context: dict[str, Any]) -> bool:
    if not conditions:
        return True
    if 'all' in conditions:
        return all(_eval_condition_item(item, context) for item in conditions['all'])
    if 'any' in conditions:
        return any(_eval_condition_item(item, context) for item in conditions['any'])
    return _eval_condition_item(conditions, context)


def _eval_condition_item(item: dict[str, Any], context: dict[str, Any]) -> bool:
    if 'all' in item or 'any' in item:
        return _eval_conditions(item, context)
    field = item.get('field')
    value = context.get(field)
    if 'eq' in item:
        return value == item['eq']
    if 'gt' in item:
        return value is not None and value > item['gt']
    if 'gte' in item:
        return value is not None and value >= item['gte']
    if 'lt' in item:
        return value is not None and value < item['lt']
    if 'lte' in item:
        return value is not None and value <= item['lte']
    if 'in' in item:
        return value in item['in']
    if 'contains' in item:
        if value is None:
            return False
        return str(item['contains']) in str(value)
    return False
