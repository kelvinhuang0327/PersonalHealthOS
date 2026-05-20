# Hallucination Guardrail Policy

1. 所有輸出必須可追溯到輸入 evidence_ids。
2. 無 evidence 的敘述要被降級或移除。
3. 禁止診斷、處方、藥物劑量建議。
4. 輸出必須是 JSON 且欄位完整。
5. 若資料不足，優先回覆追蹤建議與補件項目。
