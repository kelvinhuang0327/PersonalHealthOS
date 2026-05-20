# STEP 8 - AI Health Summary

## 1. 說明
已實作 AI 健康摘要：
- 聚合 profile + metrics + risk alerts
- 呼叫 LLM API（OpenAI）
- 若無 API Key，走 rule-based fallback
- 每次回應附帶醫療免責聲明
- 儲存到 `ai_summaries`

## 2. 產生程式碼（主要）
- `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS/backend/app/services/ai_service.py`
- `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS/backend/app/api/ai_summary.py`
- `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS/ai/prompts/health_summary_system_prompt.md`

## 3. 檔案列表
```text
backend/app/services/ai_service.py
backend/app/api/ai_summary.py
ai/prompts/health_summary_system_prompt.md
```

## 4. 執行方式
1. 設定 `OPENAI_API_KEY`（可選）
2. 產生摘要：`POST /api/v1/ai-summary/generate`
3. 查詢歷史：`GET /api/v1/ai-summary`
