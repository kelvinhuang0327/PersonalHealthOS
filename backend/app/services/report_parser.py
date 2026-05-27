from __future__ import annotations

import io
import json
import re
from pathlib import Path
from typing import Any

from pypdf import PdfReader
from PIL import Image
import pytesseract
from pdf2image import convert_from_bytes

from app.core.config import get_settings

settings = get_settings()

RANGE_FILE = Path(__file__).resolve().parent.parent / 'config' / 'lab_reference_ranges.json'

ALIAS_MAP = {
    'Glu': 'Glucose',
    'Glucose': 'Glucose',
    '血糖': 'Glucose',
    'ALT': 'ALT',
    'GPT': 'ALT',
    'AST': 'AST',
    'GOT': 'AST',
    '尿酸': 'Uric Acid',
    'Uric Acid': 'Uric Acid',
    '膽固醇': 'Total Cholesterol',
    'Total Cholesterol': 'Total Cholesterol',
    'LDL': 'LDL',
    'HDL': 'HDL',
    'Triglycerides': 'Triglycerides',
    '三酸甘油脂': 'Triglycerides',
    'Hemoglobin': 'Hemoglobin',
    '血紅素': 'Hemoglobin',
}

GENERIC_LINE_PATTERN = re.compile(
    r'^\s*([A-Za-z\u4e00-\u9fff][A-Za-z0-9\u4e00-\u9fff ()/_%+\-]{1,90}?)\s*[:：]?\s+'
    r'(-?\d+(?:\.\d+)?)\s*([A-Za-z/%\.μµ]+)?\s*'
    r'(?:\(?\s*(?:Ref(?:erence)?|Normal|Range|參考值|參考範圍)?\s*[:：]?\s*'
    r'((?:-?\d+(?:\.\d+)?\s*-\s*-?\d+(?:\.\d+)?)|(?:[<>]=?\s*-?\d+(?:\.\d+)?)|(?:-?\d+(?:\.\d+)?))\s*\)?)?\s*$',
    flags=re.IGNORECASE,
)

settings = get_settings()


def _load_default_ranges() -> dict[str, Any]:
    with RANGE_FILE.open('r', encoding='utf-8') as fp:
        return json.load(fp)


def extract_text_from_pdf(file_bytes: bytes) -> str:
    reader = PdfReader(io.BytesIO(file_bytes))
    text = '\n'.join(page.extract_text() or '' for page in reader.pages)
    return text.strip()


def extract_text_with_ocr(file_bytes: bytes, mime_type: str) -> str:
    if mime_type == 'application/pdf':
        images = convert_from_bytes(file_bytes)
    else:
        images = [Image.open(io.BytesIO(file_bytes))]

    chunks = [pytesseract.image_to_string(img, lang=settings.ocr_language) for img in images]
    return '\n'.join(chunks).strip()


def extract_text(file_bytes: bytes, mime_type: str) -> str:
    text = ''
    if mime_type == 'application/pdf':
        try:
            text = extract_text_from_pdf(file_bytes)
        except Exception:
            text = ''
    if not text:
        text = extract_text_with_ocr(file_bytes, mime_type)
    return text


def normalize_unit(unit: str | None) -> str | None:
    if not unit:
        return None
    stripped = unit.strip()
    if not stripped:
        return None
    lower = stripped.lower()
    # IU/L → U/L (case-insensitive)
    if lower == 'iu/l':
        return 'U/L'
    # Replace Unicode mu/micro-sign prefix with ASCII u
    normalized = stripped
    if normalized[0] in ('μ', 'µ'):
        normalized = 'u' + normalized[1:]
    return normalized


def normalize_item_name(raw_name: str) -> str:
    text = raw_name.strip()
    for alias, canonical in ALIAS_MAP.items():
        if alias.lower() in text.lower():
            return canonical
    return text


def parse_reference_range(range_text: str | None) -> tuple[float | None, float | None, str | None]:
    if not range_text:
        return None, None, None

    clean = range_text.replace(' ', '')
    match_range = re.match(r'^(-?\d+(?:\.\d+)?)-(-?\d+(?:\.\d+)?)$', clean)
    if match_range:
        low = float(match_range.group(1))
        high = float(match_range.group(2))
        return low, high, f'{low}-{high}'

    match_lt = re.match(r'^<=?(-?\d+(?:\.\d+)?)$', clean)
    if match_lt:
        high = float(match_lt.group(1))
        return None, high, f'<={high}'

    match_gt = re.match(r'^>=?(-?\d+(?:\.\d+)?)$', clean)
    if match_gt:
        low = float(match_gt.group(1))
        return low, None, f'>={low}'

    match_single = re.match(r'^(-?\d+(?:\.\d+)?)$', clean)
    if match_single:
        high = float(match_single.group(1))
        return None, high, f'<={high}'

    return None, None, None


def infer_reference_range(item_name: str, gender: str | None, unit: str | None) -> tuple[float | None, float | None, str | None, str]:
    ranges = _load_default_ranges()
    rule = ranges.get(item_name)
    if not rule:
        return None, None, None, 'unknown'

    if isinstance(rule.get('male'), dict) or isinstance(rule.get('female'), dict):
        gender_key = (gender or '').lower()
        if gender_key in {'male', 'm', '男'}:
            rule = rule.get('male')
        elif gender_key in {'female', 'f', '女'}:
            rule = rule.get('female')
        else:
            rule = rule.get('male') or rule.get('female')

    low = float(rule.get('low')) if rule.get('low') is not None else None
    high = float(rule.get('high')) if rule.get('high') is not None else None
    ref_unit = rule.get('unit') or unit

    if low is not None and high is not None:
        return low, high, f'{low}-{high} {ref_unit}'.strip(), 'default_rule'
    if low is not None:
        return low, None, f'>={low} {ref_unit}'.strip(), 'default_rule'
    if high is not None:
        return None, high, f'<={high} {ref_unit}'.strip(), 'default_rule'
    return None, None, None, 'default_rule'


def compute_abnormal_flag(value: float, low: float | None, high: float | None) -> str:
    if low is not None and value < low:
        return 'L'
    if high is not None and value > high:
        return 'H'
    return 'N'


def parse_lab_items(raw_text: str, gender: str | None = None) -> list[dict[str, Any]]:
    seen: dict[str, dict[str, Any]] = {}

    for line in raw_text.splitlines():
        clean = re.sub(r'\s+', ' ', line).strip()
        if not clean or len(clean) < 3:
            continue

        match = GENERIC_LINE_PATTERN.match(clean)
        if not match:
            continue

        raw_name = match.group(1)
        value_num = float(match.group(2))
        unit = (match.group(3) or '').strip() or None
        raw_ref = match.group(4)

        item_name = normalize_item_name(raw_name)

        ref_low, ref_high, ref_range = parse_reference_range(raw_ref)
        range_source = 'extracted' if ref_range else 'unknown'

        if ref_range is None:
            ref_low, ref_high, ref_range, range_source = infer_reference_range(item_name, gender, unit)

        abnormal_flag = compute_abnormal_flag(value_num, ref_low, ref_high) if (ref_low is not None or ref_high is not None) else None

        confidence = 0.55
        if unit:
            confidence += 0.15
        if raw_ref:
            confidence += 0.2
        if item_name in ALIAS_MAP.values():
            confidence += 0.1
        confidence = min(confidence, 0.99)

        candidate = {
            'item_name': item_name,
            'item_code': re.sub(r'[^A-Za-z0-9]+', '_', item_name).upper()[:40],
            'value_num': value_num,
            'value_text': None,
            'unit': unit,
            'normalized_unit': normalize_unit(unit),
            'ref_range': ref_range,
            'ref_low': ref_low,
            'ref_high': ref_high,
            'range_source': range_source,
            'abnormal_flag': abnormal_flag,
            'parser_confidence': confidence,
        }

        current = seen.get(item_name)
        if current is None or float(current['parser_confidence']) < confidence:
            seen[item_name] = candidate

    return list(seen.values())
