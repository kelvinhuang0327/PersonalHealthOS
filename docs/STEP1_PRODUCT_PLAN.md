# Personal Health Platform MVP - STEP 1 Product Plan

## 1) MVP 功能列表

### A. Account System
- 註冊（Email + Password）
- 登入（Email + Password）
- JWT 驗證（Access Token）
- Token 過期與未授權錯誤處理

### B. User Profile
- 基本資料（姓名、性別、生日）
- 身高、體重
- 過敏史
- 家族病史
- 慢性病史

### C. Health Records
- 血壓（收縮壓、舒張壓）
- 心率
- 血糖
- 體重
- 睡眠時數
- 備註
- 支援時間戳記

### D. Symptom Logs
- 症狀名稱
- 發生時間
- 持續時間
- 嚴重程度（1-5）
- 備註

### E. Medical Documents
- 上傳 PDF / 圖片（JPG/PNG）
- 文件分類（健檢、化驗、影像、處方、其他）
- 文件列表與查詢
- 檔案儲存至 S3-compatible storage

### F. Report Parsing
- PDF text extraction
- OCR（圖片與掃描 PDF）
- 抽取檢驗數據（檢驗項目、結果值、單位、參考範圍）
- 儲存為結構化資料

### G. Risk Alerts（Rule-based）
- BMI
- 血壓
- 血糖
- 肝功能（ALT/AST）
- 尿酸
- 血脂（TC/LDL/HDL/TG）
- 規則可配置（非硬編碼於商業邏輯）

### H. AI Health Summary
- 健康摘要
- 異常值說明
- 健康建議（生活方式建議）
- 醫療免責聲明（固定欄位 + 每次回應附帶）

### I. Dashboard
- 健康概覽（最新指標）
- 異常提示（來自 risk_alerts）
- 趨勢圖（血壓、血糖、體重、睡眠）

---

## 2) 系統架構（MVP）

## 2.1 Logical Architecture
- Frontend：Next.js（React）
- Backend API：FastAPI
- DB：PostgreSQL
- Object Storage：S3-compatible
- OCR + Parsing Service：FastAPI internal service layer（Tesseract adapter）
- AI Service Layer：LLM API adapter

## 2.2 Request Flow
1. 使用者在 Frontend 操作
2. Frontend 透過 HTTPS 呼叫 FastAPI
3. FastAPI 驗證 JWT，存取 PostgreSQL
4. 文件上傳流程：
   - API 簽發 pre-signed URL（或 server-side upload）
   - 檔案寫入 S3-compatible
   - metadata 寫入 medical_documents
5. 報告解析流程：
   - 讀取 S3 檔案
   - PDF 抽字 / OCR
   - 解析結構化檢驗值
   - 落地 lab_reports + lab_report_items
   - 觸發風險規則與提示
6. AI 摘要流程：
   - 聚合 profile + metrics + recent alerts
   - 呼叫 LLM（模板化提示詞）
   - 寫入 ai_summaries（含 disclaimer）

## 2.3 Security & Compliance Baseline
- Password 使用 bcrypt 雜湊
- JWT 短時效 + 驗證中介層
- 檔案上傳白名單（副檔名、MIME、大小）
- 輸入驗證（Pydantic）
- 每個 user 僅可讀寫自己的資料
- 統一錯誤碼與審計日誌（最小可行）
- AI 輸出必附免責聲明：
  - 「本平台提供健康資訊整理與一般建議，非醫療診斷；若有不適請諮詢專業醫療人員。」

---

## 3) 模組拆分（Backend / Frontend / Shared）

## 3.1 Backend Modules（FastAPI）
- `auth`：註冊、登入、JWT
- `users`：使用者資料、個人檔案
- `health_metrics`：健康指標 CRUD
- `symptoms`：症狀紀錄 CRUD
- `documents`：上傳、列表、下載 metadata
- `report_parsing`：PDF/OCR/結構化抽取
- `risk_engine`：規則評估、產生 alerts
- `ai_summary`：摘要生成與儲存
- `dashboard`：概覽與趨勢 API
- `core`：設定、資料庫、錯誤處理、權限

## 3.2 Frontend Modules（Next.js）
- `auth`：登入/註冊頁 + token 管理
- `dashboard`：概覽卡片、異常提示、趨勢圖
- `profile`：個資編輯
- `records`：健康指標列表/新增
- `symptoms`：症狀紀錄列表/新增
- `documents`：上傳、文件清單、解析狀態
- `ai-summary`：摘要顯示與歷史查詢
- `api-client`：對 FastAPI 的 typed client

## 3.3 Cross-Cutting
- `config`：環境變數、密鑰、外部服務端點
- `observability`：logging、錯誤追蹤（MVP 先 logging）
- `validation`：欄位與業務規則校驗
- `disclaimer`：醫療免責聲明常數與回應注入

---

## 4) MVP 邊界（不在本階段）
- 不做醫療診斷或處方建議
- 不做保險理賠流程
- 不做穿戴裝置即時串流
- 不做多租戶醫療院所管理
- 不做進階權限系統（MVP 先 user-scope）

---

## 5) 驗收標準（Step 1）
- 功能清單完整涵蓋需求
- 架構可支持 Step 2~8 逐步開發
- 模組切分可直接對應程式碼目錄
- 有明確的安全與免責聲明基線

---

## 6) 產出檔案
- `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS/docs/STEP1_PRODUCT_PLAN.md`
- `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS/docs/step1_architecture.yaml`

## 7) 執行方式
```bash
cat /Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS/docs/STEP1_PRODUCT_PLAN.md
cat /Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS/docs/step1_architecture.yaml
```
