# Active Task — Evidence Bundle `external_metrics` 第一級化

## 任務名稱

P0-EVIDENCE-EXTERNAL-METRICS-FIRST-CLASS

## 背景

PersonalHealthOS 產品定位是「整合所有個人健康資料」並產生今日健康建議。當前 `/health-assistant/evidence-bundle` 對 `external_metrics` 永遠回傳 `[]`, 即使資料庫 `health_metrics.source` 已有外部來源標記資料。這是產品定位與實作之間最直接的落差。

CEO 於 2026-05-20 裁決: 今日聚焦此單一方向。其他 P0 候選 (runtime smoke / unknown trust fallback) 排下一輪。

無 git repo, 嚴禁新增 repo。動工前必須建立 snapshot tarball 以提供 rollback 能力。

## 目標

讓 `/health-assistant/evidence-bundle` 對含有 source-tagged metrics 的使用者回傳非空 `external_metrics`, 每筆 evidence 含: `source`, `timestamp`, `freshness`, `reliability`, `summary`。

不引入新的資料欄位; 僅使用 `health_metrics` 表既有欄位 (`source`, 量測時間, 數值, 單位等) 計算 freshness/reliability。

## 強制前置步驟 (worker 必須完成才能動 code)

1. 建立 snapshot:
   ```
   mkdir -p runtime/snapshots
   tar -czf runtime/snapshots/backend.app.$(date +%Y%m%d-%H%M).tgz backend/app
   ```
2. 確認 `health_metrics` model 含 `source` 欄位:
   ```
   grep -nR "source" backend/app/models/ | head -50
   ```
   若 `source` 欄位不存在 → 停工, 在 `00-Plan/roadmap/active_task_report.md` 回報並退出, 不做任何修改。
3. 讀取 `backend/app/services/health_assistant_service.py` 中 evidence bundle 組裝邏輯, 確認 `external_metrics` 當前如何被設為 `[]`。

## 允許修改範圍

- `backend/app/services/health_assistant_service.py` (evidence bundle 組裝)
- `backend/app/schemas/` 中 evidence bundle 對應 schema (僅在 `external_metrics` item shape 必須擴充時)
- `backend/tests/` 新增或擴充 `test_health_assistant_service.py` 對 external_metrics 的覆蓋
- `runtime/snapshots/` (僅新增 tarball)

## 禁止修改範圍

- `frontend/**` (今日不動前端)
- `backend/app/models/**` (不改 schema migration)
- `backend/app/api/health_assistant.py` 的 endpoint 簽名 (回傳結構可擴充但路徑/方法/auth 不動)
- `runtime/agent_orchestrator/**`
- `docs/**`
- 任何 git 初始化或 repo 建立操作
- 真實 wearable / Apple Health / Google Fit 接入

## 驗收標準

1. `/health-assistant/evidence-bundle` 對於至少一個含 source-tagged metrics 的測試使用者, `external_metrics` 為非空陣列。
2. `external_metrics` 每筆含: `source` (string), `timestamp` (ISO8601), `freshness` (e.g. "fresh" / "stale" / 秒數), `reliability` (0–1 或分級), `summary` (一行人類可讀文字)。
3. 對於完全沒有 source-tagged metrics 的使用者, `external_metrics` 保持 `[]` 且不報錯。
4. 新增 backend unit tests 覆蓋:
   - 有 external metrics 的 happy path
   - 完全無 external metrics 的 empty path
   - 過期/stale metrics 的 freshness 標記
5. Backend 既有 tests 全綠 (不可回歸): `cd backend && pytest`
6. `npx tsc --noEmit` 仍為 PASS (理論上不變動, 但需驗證)。

## 測試指令

```
cd /Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS/backend
pytest tests/test_health_assistant_service.py -v
pytest

cd /Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS/frontend
npx tsc --noEmit
```

## 輸出報告位置

`00-Plan/roadmap/active_task_report.md`

報告必須包含:
- 前置步驟結果 (snapshot 路徑 / `source` 欄位確認)
- 修改檔案清單
- 驗收標準逐項對應 [Confirmed] / [Failed]
- 測試輸出摘要
- 風險 / unknown / 後續建議
- Final classification

## Final Classification (worker 完成時擇一)

- `P0_EVIDENCE_EXTERNAL_METRICS_DONE`
- `P0_EVIDENCE_EXTERNAL_METRICS_PARTIAL`
- `P0_EVIDENCE_EXTERNAL_METRICS_BLOCKED`
- `P0_EVIDENCE_EXTERNAL_METRICS_REJECTED_BY_SCHEMA` (若步驟 2 退出)
