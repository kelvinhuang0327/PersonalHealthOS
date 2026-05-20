# STEP 3 - API Design (REST)

## 1. 說明
採用 `/api/v1` 版本化 REST API。所有非 auth 端點需 Bearer JWT。回應統一包含安全錯誤碼與驗證訊息。

## 2. 產生程式碼
- API 路由程式碼：`/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS/backend/app/api/*.py`
- API 匯總路由：`/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS/backend/app/api/router.py`

## 3. Endpoint 設計
### Auth
- `POST /api/v1/auth/register`
  - req: `{ "email": "", "password": "" }`
  - res: `{ "id": "", "email": "" }`
- `POST /api/v1/auth/login`
  - req: `{ "email": "", "password": "" }`
  - res: `{ "access_token": "", "token_type": "bearer" }`

### Profile
- `GET /api/v1/profile/me`
- `PUT /api/v1/profile/me`

### Health Metrics
- `POST /api/v1/metrics`
- `GET /api/v1/metrics?limit=50`
- `GET /api/v1/metrics/latest`

### Symptom Logs
- `POST /api/v1/symptoms`
- `GET /api/v1/symptoms?limit=50`

### Documents
- `POST /api/v1/documents/upload` (multipart/form-data)
- `GET /api/v1/documents`
- `POST /api/v1/documents/{document_id}/parse`

### Risk Alerts
- `GET /api/v1/risk-alerts`
- `POST /api/v1/risk-alerts/recalculate`

### Dashboard
- `GET /api/v1/dashboard`
- `GET /api/v1/dashboard/overview`
- `GET /api/v1/dashboard/trends?days=30`

### Health Insights
- `GET /api/v1/insights`
- `POST /api/v1/insights/generate`
- `POST /api/v1/insights/{id}/dismiss`

### AI Summary
- `POST /api/v1/ai-summary/generate`
- `GET /api/v1/ai-summary`

## 4. 檔案列表
```text
backend/app/api/auth.py
backend/app/api/profile.py
backend/app/api/metrics.py
backend/app/api/symptoms.py
backend/app/api/documents.py
backend/app/api/risk_alerts.py
backend/app/api/dashboard.py
backend/app/api/insights.py
backend/app/api/ai_summary.py
backend/app/api/router.py
```

## 5. 執行方式
```bash
cd /Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS/backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
啟動後可用 Swagger 測試：`http://localhost:8000/docs`
