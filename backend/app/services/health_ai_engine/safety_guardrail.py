from __future__ import annotations

import re

MEDICAL_DISCLAIMER = '本系統為健康建議工具，非醫療診斷，請諮詢專業醫療人員。'
_UNSAFE_PATTERNS = [
    r'你.*患有',
    r'確診',
    r'請立即服用',
    r'處方',
]


def apply_safety_guardrail(content: str) -> dict[str, str]:
    sanitized = content
    for pattern in _UNSAFE_PATTERNS:
        sanitized = re.sub(pattern, '建議就醫評估', sanitized)
    if MEDICAL_DISCLAIMER not in sanitized:
        sanitized = f'{sanitized}\n\n{MEDICAL_DISCLAIMER}'
    return {'safe_response': sanitized}
