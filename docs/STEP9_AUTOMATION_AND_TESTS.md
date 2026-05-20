# STEP 9 - Automation and Basic Tests

## 1. 說明
為提升可交付性，補上：
- 一鍵容器化啟動（frontend + backend + postgres + minio）
- Backend 最小單元測試（risk engine / ai fallback）

## 2. 產生程式碼
- `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS/docker-compose.yml`
- `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS/backend/Dockerfile`
- `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS/frontend/Dockerfile`
- `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS/backend/tests/test_risk_engine.py`
- `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS/backend/tests/test_ai_service.py`
- `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS/Makefile`

## 3. 檔案列表
```text
docker-compose.yml
backend/Dockerfile
frontend/Dockerfile
backend/requirements-dev.txt
backend/tests/test_risk_engine.py
backend/tests/test_ai_service.py
Makefile
```

## 4. 執行方式
```bash
cd /Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS
make up
make logs
make backend-test
make down
```
