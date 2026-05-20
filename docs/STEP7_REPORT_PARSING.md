# STEP 7 - Report Parsing

## 1. 說明
已實作報告解析流程：
- PDF text extraction（`pypdf`）
- OCR（`pytesseract` + `pdf2image`）
- 檢驗數據抽取（regex rules）
- 結構化儲存到 `lab_reports` / `lab_report_items`
- 解析後觸發 `risk_alerts`

## 2. 產生程式碼（主要）
- `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS/backend/app/services/report_parser.py`
- `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS/backend/app/api/documents.py`

## 3. 檔案列表
```text
backend/app/services/report_parser.py
backend/app/api/documents.py
```

## 4. 執行方式
1. 上傳文件：`POST /api/v1/documents/upload`
2. 呼叫解析：`POST /api/v1/documents/{document_id}/parse`
3. 查詢結果：資料會落在 `lab_reports`, `lab_report_items`, `risk_alerts`
