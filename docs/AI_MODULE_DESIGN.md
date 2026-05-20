# Personal Health Platform - AI 模組設計

## 1. AI 模型設計

### 1.1 系統 A：健檢報告解讀 AI
- 目標：解讀健檢/檢驗結果並輸出風險、生活建議、追蹤項目。
- 輸入：`lab_report_items + health_metrics + user_profile + risk_alerts`
- 核心流程：
  1. Context Builder 聚合最近 N 天資料
  2. LLM 生成結構化 JSON
  3. Guardrail 驗證 evidence grounding
  4. 回傳結構化建議與免責聲明

### 1.2 系統 B：症狀分析 AI
- 目標：分析症狀與健康紀錄關聯，提供風險分層與追蹤建議。
- 輸入：`symptom_logs + health_metrics + user_profile + lab_report_items`
- 核心流程同上，重點在症狀嚴重度/持續時間解讀。

### 1.3 系統 C：健康風險預測
- 目標：預測短期風險趨勢（非醫療診斷）。
- 輸入：`health_metrics 趨勢 + symptom_logs + lab_report_items + risk_alerts`
- 核心流程同上，著重趨勢與追蹤優先順序。

### 1.4 共用輸出格式
- `health_risks[]`
- `lifestyle_recommendations[]`
- `follow_up_items[]`
- `confidence`
- `guardrail_report`
- `disclaimer`

---

## 2. Prompt Template

已落地檔案：
- `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS/ai/prompts/health_check_interpreter_prompt.md`
- `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS/ai/prompts/symptom_analysis_prompt.md`
- `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS/ai/prompts/health_risk_prediction_prompt.md`

共通要求：
- 僅使用輸入資料 evidence_ids
- 嚴格 JSON 輸出
- 不可做診斷/處方
- 資料不足時輸出追蹤建議

---

## 3. Hallucination Guardrail

已落地：`backend/app/services/ai_guardrail_service.py`

Guardrail 規則：
1. 無 evidence_ids 的項目直接丟棄
2. evidence_ids 不在 allowed set 的項目丟棄
3. 風險等級/建議優先級正規化為 `low|medium|high`
4. 掃描禁用詞（診斷/處方/劑量）
5. 計算 `grounded_ratio` 與 `dropped_items`

輸出：
- `guardrail_report`（dropped_items, grounded_ratio, safety_flags）

---

## 4. Evaluation 方法

已落地：`evaluate_guarded_output()` in `ai_guardrail_service.py`

指標：
1. `format_valid`：輸出 JSON 結構完整性
2. `grounded_ratio`：有證據支持項目比例
3. `safety_pass`：是否觸發禁用醫療語句
4. `actionability_score`：可執行建議密度
5. `overall_score`：加權總分（0-1）

建議離線評估集：
- 30 筆健檢案例
- 30 筆症狀案例
- 30 筆趨勢案例
每筆標註：關鍵風險、可接受建議、必須追蹤項目。

---

## 5. API

### 5.1 AI 模組 API
- `POST /api/v1/ai-modules/health-check-interpretation`
- `POST /api/v1/ai-modules/symptom-analysis`
- `POST /api/v1/ai-modules/risk-prediction`

Request body:
```json
{
  "days": 90,
  "focus": "最近血糖偏高",
  "max_items": 5
}
```

Response body（摘要）:
```json
{
  "module": "health_check_interpreter",
  "model_name": "gpt-4.1-mini",
  "health_risks": [],
  "lifestyle_recommendations": [],
  "follow_up_items": [],
  "confidence": 0.78,
  "guardrail_report": {
    "dropped_items": 1,
    "grounded_ratio": 0.86,
    "safety_flags": []
  },
  "disclaimer": "本平台提供健康資訊整理與一般建議，非醫療診斷；若有不適請諮詢專業醫療人員。"
}
```

### 5.2 評估 API
- `POST /api/v1/ai-modules/evaluate/{module_name}`
  - module_name: `health_check_interpreter | symptom_analysis | health_risk_prediction`

---

## 實作檔案
- `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS/backend/app/api/ai_modules.py`
- `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS/backend/app/services/ai_modules_service.py`
- `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS/backend/app/services/ai_guardrail_service.py`
- `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS/backend/app/schemas/ai_modules.py`
