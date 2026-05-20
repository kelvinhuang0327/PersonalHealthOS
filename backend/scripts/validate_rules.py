from __future__ import annotations

from collections import defaultdict
from pathlib import Path
import sys
from typing import Any

import yaml

RULES_DIR = Path(__file__).resolve().parents[1] / 'app' / 'services' / 'health_ai_engine' / 'rules'


def normalize_conditions(conditions: dict[str, Any] | None) -> tuple:
    if not conditions:
        return ()
    all_conditions = conditions.get('all') or []
    normalized = []
    for condition in all_conditions:
        field = condition.get('field')
        operator = next((key for key in condition.keys() if key != 'field'), 'eq')
        value = condition.get(operator)
        normalized.append((field, operator, str(value)))
    return tuple(sorted(normalized))


def find_line_number(file_path: Path, rule_id: str) -> int:
    for index, line in enumerate(file_path.read_text(encoding='utf-8').splitlines(), start=1):
        if f'id: {rule_id}' in line:
            return index
    return 1


def load_rules() -> list[dict[str, Any]]:
    loaded: list[dict[str, Any]] = []
    for file_path in sorted(RULES_DIR.glob('*.yaml')):
        data = yaml.safe_load(file_path.read_text(encoding='utf-8')) or {}
        for rule in data.get('rules') or []:
            loaded.append(
                {
                    'file': file_path.name,
                    'line': find_line_number(file_path, str(rule.get('id', 'unknown'))),
                    'id': rule.get('id', 'unknown'),
                    'role': rule.get('role') or rule.get('type') or 'unknown',
                    'enabled': bool(rule.get('enabled', True)),
                    'conditions': normalize_conditions(rule.get('conditions')),
                    'severity': (rule.get('output') or {}).get('severity') or rule.get('severity'),
                    'insight_type': (rule.get('output') or {}).get('insight_type') or rule.get('type'),
                }
            )
    return loaded


def main() -> int:
    rules = load_rules()
    grouped: dict[tuple, list[dict[str, Any]]] = defaultdict(list)
    for rule in rules:
        grouped[rule['conditions']].append(rule)

    conflicts = 0
    overlaps = 0
    for fingerprint, group in grouped.items():
        if len(group) < 2 or not fingerprint:
            continue
        for index, left in enumerate(group):
            for right in group[index + 1 :]:
                if left['role'] != right['role']:
                    overlaps += 1
                    continue
                left_output = (left['severity'], left['insight_type'])
                right_output = (right['severity'], right['insight_type'])
                if left_output != right_output:
                    conflicts += 1
                    print(f"CONFLICT: {left['id']} vs {right['id']}")
                    print(f"  Condition: {' AND '.join(f'{field} {operator} {value}' for field, operator, value in fingerprint)}")
                    print(f"  Rule A output: severity={left['severity']}, type={left['insight_type']}")
                    print(f"  Rule B output: severity={right['severity']}, type={right['insight_type']}")
                    print(f"  Files: {left['file']}:{left['line']}, {right['file']}:{right['line']}")
                if left['enabled'] != right['enabled']:
                    disabled = left if not left['enabled'] else right
                    enabled = right if left is disabled else left
                    print(f"SHADOWED: {disabled['id']} is disabled but matches enabled rule {enabled['id']}")
                    print(f"  Condition: {' AND '.join(f'{field} {operator} {value}' for field, operator, value in fingerprint)}")
                    print(f"  Files: {disabled['file']}:{disabled['line']}, {enabled['file']}:{enabled['line']}")

    print(f'{overlaps} cross-layer overlaps found (expected, not errors)')
    print(f'{conflicts} true conflicts found')
    return 0 if conflicts == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
