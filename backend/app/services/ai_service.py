from __future__ import annotations

from datetime import date
import logging
from typing import Any

from openai import OpenAI

from app.core.config import get_settings
from app.core.constants import MEDICAL_DISCLAIMER
from app.orchestrator.execution_policy import evaluate_llm_execution, record_llm_call

settings = get_settings()

logger = logging.getLogger(__name__)


def build_summary_payload(profile: dict[str, Any], metrics: list[dict[str, Any]], alerts: list[dict[str, Any]]) -> str:
    return (
        '你是健康資訊整理助手。請輸出：1)健康摘要 2)異常值說明 3)生活建議。'
        '不要做醫療診斷，不要給藥物處方。\n'
        f'個人資料: {profile}\n近期指標: {metrics}\n近期提醒: {alerts}\n'
        f'最後必須加上免責聲明: {MEDICAL_DISCLAIMER}'
    )


def generate_health_summary(
    profile: dict[str, Any],
    metrics: list[dict[str, Any]],
    alerts: list[dict[str, Any]],
    period_start: date | None,
    period_end: date | None,
) -> dict[str, Any]:
    prompt = build_summary_payload(profile, metrics, alerts)
    policy = evaluate_llm_execution(source='api-direct')

    if settings.openai_api_key and policy.allowed:
        try:
            record_llm_call(source='api-direct', provider='openai', model=settings.openai_model)
            client = OpenAI(api_key=settings.openai_api_key)
            completion = client.responses.create(
                model=settings.openai_model,
                input=prompt,
                temperature=0.3,
            )
            text = completion.output_text
            model_name = settings.openai_model
        except Exception as exc:
            logger.error("OpenAI summary generation failed: %s", exc)
            text = (
                '近期健康數據已整理完成。請持續追蹤血壓、血糖與體重變化，若異常持續請儘速就醫。\n'
                '異常值：請參考系統提示卡片。\n'
                '建議：規律作息、均衡飲食、每週至少 150 分鐘中強度運動。\n'
                f'免責聲明：{MEDICAL_DISCLAIMER}'
            )
            model_name = 'rule-based-fallback'
    else:
        text = (
            '近期健康數據已整理完成。請持續追蹤血壓、血糖與體重變化，若異常持續請儘速就醫。\n'
            '異常值：請參考系統提示卡片。\n'
            '建議：規律作息、均衡飲食、每週至少 150 分鐘中強度運動。\n'
            f'免責聲明：{MEDICAL_DISCLAIMER}'
        )
        if settings.openai_api_key and not policy.allowed:
            model_name = f'policy-fallback:{policy.code.lower()}'
        else:
            model_name = 'rule-based-fallback'

    return {
        'period_start': period_start,
        'period_end': period_end,
        'summary_text': text,
        'abnormal_explanation': '請參考摘要中的異常值段落。',
        'recommendations': '請依摘要建議執行並定期追蹤。',
        'disclaimer': MEDICAL_DISCLAIMER,
        'model_name': model_name,
    }
