# Stage 2 - Health Intelligence Features

## 1) Schema 修改

### 1.1 `lab_report_items` 新增欄位
- `ref_low NUMERIC(10,3)`
- `ref_high NUMERIC(10,3)`
- `range_source VARCHAR(30) DEFAULT 'extracted'`
- `parser_confidence NUMERIC(4,3)`

### 1.2 新增 `health_scores`
- `overall_score`（0-100）
- 分項：`cardiovascular_score`, `metabolic_score`, `weight_score`, `sleep_score`
- `score_detail JSONB`
- `source_period_days`

### 1.3 SQL 檔案
- `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS/database/schema.sql`
- `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS/database/migrations/002_stage2_features.sql`

---

## 2) API 新增

### Report parsing
- `POST /api/v1/documents/{document_id}/parse`
  - 回傳新增 `abnormal_items`

### Timeline
- `GET /api/v1/timeline?days=180&limit=200`

### Trend analysis
- `GET /api/v1/analytics/trends?days=90`

### Health score
- `POST /api/v1/health-score/calculate`（body: `{ "days": 30 }`）
- `GET /api/v1/health-score/latest`
- `GET /api/v1/health-score/history?limit=20`

---

## 3) 前端頁面

- `/timeline`：健康時間軸（健檢 / 症狀 / 健康數據）
- `/trends`：健康趨勢分析（血壓 / 體重 / 血糖）
- `/health-score`：健康分數（總分 + 分項）
- `/stage2`：Stage 2 功能入口

主要檔案：
- `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS/frontend/pages/timeline.tsx`
- `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS/frontend/pages/trends.tsx`
- `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS/frontend/pages/health-score.tsx`
- `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS/frontend/lib/api.ts`

---

## 4) Backend Service

- `report_parser.py`
  - 自動欄位抽取
  - reference range 推斷（extracted + default rule）
  - abnormal flag（H/L/N）
- `timeline_service.py`
  - 聚合健檢、症狀、健康數據為時間軸
- `trend_analysis_service.py`
  - 計算趨勢方向、變化率、斜率
- `health_score_service.py`
  - 計算 0-100 健康分數與分項分數

---

## 5) AI 計算邏輯

### 5.1 健檢解析（AI/規則混合）
- OCR/PDF 抽字後，使用通用 pattern 抽取檢驗值
- alias normalization（例：GOT -> AST, GPT -> ALT）
- 優先用文件中 reference range；缺失時套用預設 reference rules
- 依 `value` vs `ref_low/ref_high` 標記 `abnormal_flag`

### 5.2 Health Score（0-100）
- Cardio（35%）：血壓/心率
- Metabolic（30%）：血糖與血脂
- Weight（20%）：BMI
- Sleep（15%）：平均睡眠時數
- 依高風險 alerts 額外扣分（最高 15 分）

---

## 執行方式

```bash
cd /Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS

# 套用 Stage 2 migration
psql "postgresql://postgres:postgres@localhost:5432/personal_health" \
  -f /Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS/database/migrations/002_stage2_features.sql

# 啟動服務
make up

# 後端測試
make backend-test
```
