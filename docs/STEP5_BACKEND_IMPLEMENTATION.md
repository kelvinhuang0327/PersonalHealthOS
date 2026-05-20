# STEP 5 - Backend Implementation

## 1. 說明
已完成 FastAPI 後端核心模組：
- Auth（註冊、登入、JWT）
- User Profile（查詢/更新）
- Health Metrics（新增/查詢/最新值）
- Symptom Logs（新增/查詢）
- Document Upload（S3-compatible）
- Risk Alerts（查詢/重算）
- Dashboard（overview/trends）

## 2. 產生程式碼（主要）
- `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS/backend/app/main.py`
- `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS/backend/app/api/*.py`
- `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS/backend/app/models/entities.py`
- `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS/backend/app/core/*.py`
- `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS/backend/app/services/storage_service.py`
- `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS/backend/app/services/risk_engine.py`

## 3. 檔案列表
```text
backend/
  app/
    api/
      auth.py
      profile.py
      metrics.py
      symptoms.py
      documents.py
      risk_alerts.py
      dashboard.py
      ai_summary.py
      router.py
    core/
      config.py
      database.py
      security.py
      deps.py
      constants.py
    models/entities.py
    schemas/*.py
    services/
      storage_service.py
      risk_engine.py
      report_parser.py
      ai_service.py
    config/risk_rules.json
    main.py
  requirements.txt
  .env.example
```

## 4. 執行方式
```bash
cd /Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS
docker compose up -d postgres minio

cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env

psql "$DATABASE_URL" -f /Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS/database/schema.sql
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
