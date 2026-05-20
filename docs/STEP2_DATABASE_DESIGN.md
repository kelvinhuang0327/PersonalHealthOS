# STEP 2 - Database Design

## 說明
MVP 使用 PostgreSQL，主表對應需求指定的 9 張資料表，採用 UUID 主鍵、`created_at` 時間欄位、使用者資料隔離（所有業務資料表都含 `user_id` 並建立索引）。

## Schema 重點
- `users` + `user_profiles`：帳號與個人健康背景
- `health_metrics`：時序健康指標
- `symptom_logs`：症狀紀錄
- `medical_documents`：文件 metadata + 解析狀態
- `lab_reports` / `lab_report_items`：報告與結構化檢驗值
- `risk_alerts`：規則引擎提醒
- `ai_summaries`：AI 產生摘要（含免責聲明）

## Index 策略
- 查詢主路徑：`(user_id, 時間 DESC)`
- 關聯路徑：`report_id`
- 身分驗證：`users.email`

## SQL
- 主要 SQL：`/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS/database/schema.sql`

## 執行方式
```bash
psql "$DATABASE_URL" -f /Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS/database/schema.sql
```
