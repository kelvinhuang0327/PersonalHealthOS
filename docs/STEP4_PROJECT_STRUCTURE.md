# STEP 4 - Project Structure

## 1. 說明
MVP 以單一 repository 管理前後端與資料庫腳本，目錄切分如下。

## 2. 產生程式碼
- 結構建立與初始檔案：`frontend/`, `backend/`, `database/`, `ai/`, `docs/`

## 3. Project Structure
```text
PersonalHealthOS/
  frontend/
  backend/
  database/
  ai/
  docs/
```

## 4. 檔案列表（主要）
```text
README.md
docker-compose.yml
frontend/package.json
backend/requirements.txt
database/schema.sql
ai/prompts/health_summary_system_prompt.md
docs/STEP1_PRODUCT_PLAN.md ... STEP8_AI_SUMMARY.md
```

## 5. 執行方式
```bash
cd /Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS
find . -maxdepth 3 -type d | sort
```
