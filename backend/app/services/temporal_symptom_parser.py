from __future__ import annotations

import re
from datetime import date, timedelta
from typing import Any
from typing import Optional


def parse_temporal_symptom(text: str) -> dict[str, Any]:
    normalized = (text or '').strip()
    today = date.today()
    days: Optional[int] = None
    confidence = 0.45

    if not normalized:
        return {
            'symptom': '',
            'estimated_start_date': None,
            'estimated_duration_days': None,
            'temporal_source': 'user_narrative',
            'confidence_score': confidence,
        }

    year_match = re.search(r'(?:大約|約|大概|近)?\s*(\d+)\s*年', normalized)
    if year_match:
        days = int(year_match.group(1)) * 365
        confidence = 0.9
    elif re.search(r'最近半年|近半年|半年', normalized):
        days = 182
        confidence = 0.82
    else:
        month_match = re.search(r'最近?\s*(\d+)\s*個?月', normalized)
        if month_match:
            days = int(month_match.group(1)) * 30
            confidence = 0.8
        else:
            week_match = re.search(r'最近?\s*(\d+)\s*(?:週|星期)', normalized)
            if week_match:
                days = int(week_match.group(1)) * 7
                confidence = 0.75
            else:
                day_match = re.search(r'最近?\s*(\d+)\s*(?:天|日)', normalized)
                if day_match:
                    days = int(day_match.group(1))
                    confidence = 0.74

    symptom = _extract_symptom(normalized)
    start_date = today - timedelta(days=days) if days else None
    return {
        'symptom': symptom or normalized[:120],
        'estimated_start_date': start_date,
        'estimated_duration_days': days,
        'temporal_source': 'user_narrative',
        'confidence_score': round(confidence, 3),
    }


def _extract_symptom(text: str) -> str:
    cleaned = text
    patterns = [
        r'(?:大約|約|大概|近|最近)\s*\d+\s*年(?:的)?',
        r'(?:大約|約|大概|近|最近)\s*\d+\s*個?月(?:的)?',
        r'(?:大約|約|大概|近|最近)\s*\d+\s*(?:週|星期)(?:的)?',
        r'(?:大約|約|大概|近|最近)\s*\d+\s*(?:天|日)(?:的)?',
        r'(?:最近|近)?半年(?:的)?',
        r'(?:大約|約|大概)?\s*\d+\s*年$',
        r'(?:大約|約|大概)?\s*\d+\s*個?月$',
    ]
    for pattern in patterns:
        cleaned = re.sub(pattern, '', cleaned)

    cleaned = cleaned.strip().lstrip('的').strip()
    return cleaned[:120]
