# Active Task Report — P2-DEVICE-ESCALATION-VERIFIED-AND-SAFEGUARDED

Generated: 2026-05-20  
Classification: **`P2_DEVICE_ESCALATION_VERIFIED_AND_SAFEGUARDED`**

---

## Summary

This sprint verified and safeguarded the P2 Device Escalation Layer completed in
the prior session.  No new features were added.  Focus was on git safety, data
flow verification, automated smoke testing, and honest limitation documentation.

---

## Task 1 — Git Safety

| Item | Result |
|---|---|
| `git status` before init | `fatal: not a git repository` |
| `.gitignore` created | ✅ Excludes `.venv/`, `node_modules/`, `.next/`, `.env`, `runtime/snapshots/`, runtime locks |
| `git init` | ✅ |
| `git add .` — excluded files verified | ✅ No `.env`, `.venv`, `node_modules`, `.next`, `snapshots` committed |
| Initial commit | ✅ `ab977a6 chore: initial commit — P2_DEVICE_ESCALATION_LAYER_READY` |
| Runtime orchestrator locks untracked | ✅ `git rm --cached` + .gitignore update |
| Final `git status` | ✅ `nothing to commit, working tree clean` |
| `git log --oneline` | `0df1cb5 chore: untrack runtime lock files from index` → `2c5d36e` → `ab977a6` |

---

## Task 2 — Device Escalation Data Flow Verification

Verified end-to-end by code inspection + automated smoke tests:

```
external_metrics (HealthMetric rows, source != 'manual')
  → detect_device_signals()            ← device_signals in bundle ✅
  → build_device_signal_history()      ← device_signal_history in bundle ✅
  → evaluate_signal_escalation()       ← device_escalation in bundle ✅
  → build_evidence_bundle()
  → get_action_recommendations()       ← device_escalation in return ✅
  → generate_daily_health_summary()    ← escalation key injected when level != none ✅
  → frontend DeviceSignalCard          ← escalation prop consumed ✅
```

| Check | Result |
|---|---|
| `bundle["device_signals"]` present | ✅ |
| `bundle["device_signal_history"]` present | ✅ computed, NOT persisted to DB |
| `bundle["device_escalation"]` present | ✅ |
| `get_action_recommendations()` returns `device_escalation` | ✅ |
| `generate_daily_health_summary()` uses escalation for topRisk / todayAction | ✅ |
| `EscalationDecision` type in `frontend/lib/api.ts` | ✅ |
| `DeviceSignalCard` receives and renders `escalation` prop | ✅ |
| Medical disclaimer shown when signals or escalation present | ✅ |
| Stale-all cap at "watch" | ✅ |

---

## Task 3 — API Smoke Tests

**New file:** `backend/tests/test_api_escalation_smoke.py` — 12 tests

| Class | Tests | Result |
|---|---|---|
| `TestDeviceSignalsEndpoint` | schema keys, empty=no signals, elevated HR→signal, signal key shapes | **4/4 PASS** |
| `TestEvidenceBundleEndpoint` | device_escalation key, schema, no-signal=none, elevated HR raises level, device_signal_history present | **5/5 PASS** |
| `TestDailySummaryEndpoint` | base keys, no-signal=no escalation key, elevated HR may inject escalation | **3/3 PASS** |

Note: Tests use in-memory SQLite with real FastAPI TestClient.  An `autouse`
fixture clears `app.dependency_overrides` after each test to prevent cross-test
contamination.

---

## Required Validation — Full Results

| Test file | Count | Result |
|---|---|---|
| `test_device_signal_escalation.py` | 24 | **24 PASS** |
| `test_device_signal_detection.py` | 21 | **21 PASS** |
| `test_health_assistant_service.py` | ~40 | **PASS** |
| `test_daily_summary_service.py` | ~20 | **PASS** |
| `test_recommendation_trust_service.py` | ~20 | **PASS** |
| `test_outcome_feedback_service.py` | ~20 | **PASS** |
| **Full backend (excl. orchestrator)** | **222** | **222 PASS** |
| `test_dual_agent_orchestrator.py` | 10 | **PRE-EXISTING FAILURES — excluded** |
| `npx tsc --noEmit` | — | **PASS** |
| `npx next build` | — | **PASS** |
| E2E / Playwright browser smoke | — | **NOT RUN** |

---

## Files Changed This Sprint

| File | Change |
|---|---|
| `.gitignore` | Created — excludes secrets, venv, node_modules, runtime locks |
| `backend/tests/test_api_escalation_smoke.py` | Created — 12 API smoke tests |

(All P2 escalation service + UI files were created in the prior session.)

---

## Known Limitations

| Limitation | Detail |
|---|---|
| **DB persistence NOT implemented** | `device_signal_history` is computed deterministically from `HealthMetric` rows at request time.  There is NO separate history table, no trend DB, no long-term memory store.  "Trend memory" means recurrence is inferred across time-bucketed rows from the same table. |
| **E2E not run** | No Playwright / browser smoke tests executed.  Frontend verified by `tsc --noEmit` + `next build` only. |
| **Orchestrator failures pre-existing** | `test_dual_agent_orchestrator.py` — 10 PLANNER_SKIP_SAFE_RUN failures exist before this sprint and are not caused by escalation changes. |
| **No remote git** | Repo is local only.  No remote configured, no CI/CD triggered. |
| **Escalation is session-scoped** | Each API call recomputes escalation from available metrics.  There is no cross-session escalation state. |

---

## Previous Report — P2-DEVICE-SIGNAL-INTELLIGENCE

# Active Task Report — P2-DEVICE-SIGNAL-INTELLIGENCE

Generated: 2026-05-20  
Classification: **`P2_DEVICE_SIGNAL_INTELLIGENCE_READY`**

---

## Pre-step Results

| Step | Result |
|---|---|
| Snapshot path | `runtime/snapshots/backend.app.20260520-HHMM.tgz` (created before any change) |
| `HealthMetric.source` field confirmed | ✅ String(40), default='manual' |
| `HealthMetric.spo2` column exists | ❌ Not present — handled gracefully (no hallucination) |

---

## Modified / Created Files

| File | Action |
|---|---|
| `backend/app/services/device_signal_detection_service.py` | **CREATED** — pure-function detection: elevated HR, pulse trend, low sleep, reduced activity, SpO₂ placeholder |
| `backend/app/services/health_assistant_service.py` | **MODIFIED** — import + enrich external_metrics with raw values + `detect_device_signals` call + `device_signals` in bundle + `_SOURCE_PRIORITY["device_signal"]=70` + candidate generation + recommendation builder handler + return `device_signals` |
| `backend/app/api/health_assistant.py` | **MODIFIED** — import + new `GET /health-assistant/device-signals` endpoint |
| `backend/tests/test_device_signal_detection.py` | **CREATED** — 21 tests covering all 9 spec scenarios |
| `frontend/lib/api.ts` | **MODIFIED** — `DeviceSignal` type + `getDeviceSignals()` |
| `frontend/app/components/platform/device-signal-card.tsx` | **CREATED** — severity badges, freshness, confidence %, empty state |
| `frontend/app/components/platform/health-assistant-panel.tsx` | **MODIFIED** — import + `device_signals?` in HealthAssistantData + render section |

---

## Acceptance Criteria

| Criterion | Status |
|---|---|
| `detect_device_signals([])` returns `[]` | [Confirmed] |
| elevated_resting_heart_rate detected (HR ≥ 90) | [Confirmed] |
| abnormal_pulse_trend detected (≥ 3 ascending readings) | [Confirmed] |
| low_sleep_duration detected (< 7 h) | [Confirmed] |
| reduced_activity detected (< 5000 steps) | [Confirmed] |
| unstable_spo2 — no hallucination (no column) | [Confirmed] |
| Stale → confidence × 0.70 | [Confirmed] |
| ≥ 3 repeated abnormal → severity escalates to high | [Confirmed] |
| Device signal surfaces in Top-3 recommendations | [Confirmed] |
| `/health-assistant/device-signals` endpoint | [Confirmed] |
| `DeviceSignal` TS type + `getDeviceSignals()` API | [Confirmed] |
| `DeviceSignalCard` + empty state rendered in panel | [Confirmed] |
| `npx tsc --noEmit` PASS | [Confirmed] |
| `npx next build` PASS | [Confirmed] |

---

## Test Results

```
test_device_signal_detection.py  — 21 passed
Full backend regression           — 186 passed, 4 warnings
frontend tsc --noEmit             — PASS
frontend next build               — PASS
```

---

## Risks / Next Steps

| Item | Note |
|---|---|
| SpO₂ signal | No `spo2` column yet. Placeholder comment in service. Implement when schema column added. |
| Pulse trend / elevated HR co-signal | Trend only emits when HR < 90 to avoid double-counting. |
| Frontend empty state | Does NOT claim any device is connected — neutral guidance only. |

---

## Final Classification

`P2_DEVICE_SIGNAL_INTELLIGENCE_READY`

---

# Previous Report — P0-EVIDENCE-EXTERNAL-METRICS-FIRST-CLASS

Generated: 2026-05-20

---

## 前置步驟結果

### Step 1 — Snapshot

```
runtime/snapshots/backend.app.20260520-1218.tgz  (180K)
```
Status: **DONE** [Confirmed]

### Step 2 — source 欄位確認

```
backend/app/models/entities.py:93
class HealthMetric:
    source = Column(String(40), default='manual')
```
Status: **CONFIRMED** — `HealthMetric.source` 欄位存在，型別 `String(40)`，預設值 `'manual'`。

### Step 3 — 原始 external_metrics 邏輯

```python
# 原始 (修改前)
"external_metrics": [],  # populated by external_metrics_service if needed
```
原因：hardcoded 空陣列，從未被填入任何資料。

---

## 修改檔案清單

| 檔案 | 修改內容 |
|---|---|
| `backend/app/services/health_assistant_service.py` | 新增 `_freshness_label()` 函式、`_EXTERNAL_RELIABILITY` 對照表、`_DEFAULT_EXTERNAL_RELIABILITY`；在 `build_evidence_bundle` 的 health_metrics 迴圈後新增 external_metrics 抽取邏輯；將 `"external_metrics": []` 替換為 `"external_metrics": external_metrics` |
| `backend/tests/test_health_assistant_service.py` | 新增 `_make_external_metric()` helper、`test_external_metrics_happy_path`、`test_external_metrics_empty_when_all_manual`、`test_external_metrics_stale_freshness` 三個新測試 |
| `runtime/snapshots/backend.app.20260520-1218.tgz` | 新增 snapshot（唯讀備份） |

**未修改任何其他檔案。** frontend、models、API endpoint 簽名均未動。

---

## 驗收標準逐項對應

| 驗收標準 | 結果 |
|---|---|
| 1. 含 source-tagged metrics 的使用者，`external_metrics` 為非空陣列 | **[Confirmed]** — `test_external_metrics_happy_path` PASS |
| 2. 每筆含 `source`, `timestamp`, `freshness`, `reliability`, `summary` | **[Confirmed]** — `test_external_metrics_happy_path` 驗證所有欄位 |
| 3. 無 source-tagged metrics 時，`external_metrics` 保持 `[]` 且不報錯 | **[Confirmed]** — `test_external_metrics_empty_when_all_manual` PASS |
| 4a. happy path 測試 | **[Confirmed]** — `test_external_metrics_happy_path` PASS |
| 4b. empty path 測試 | **[Confirmed]** — `test_external_metrics_empty_when_all_manual` PASS |
| 4c. stale freshness 測試 | **[Confirmed]** — `test_external_metrics_stale_freshness` PASS |
| 5. 既有 backend tests 全綠（無回歸） | **[Confirmed]** — 165 passed (excluding pre-existing orchestrator failures) |
| 6. `npx tsc --noEmit` PASS | **[Confirmed]** — exit code 0 |

---

## 測試輸出摘要

### test_health_assistant_service.py (18 tests)
```
18 passed in 0.43s
```
新增測試：
- `test_external_metrics_happy_path`        PASS
- `test_external_metrics_empty_when_all_manual`  PASS
- `test_external_metrics_stale_freshness`   PASS

### 全 backend suite（不含 orchestrator）
```
165 passed, 4 warnings in 2.23s
```

### Orchestrator pre-existing failures（與本任務無關）
```
10 failed in test_dual_agent_orchestrator.py
原因: PLANNER_SKIP_SAFE_RUN vs CREATED — 環境問題，非本任務造成
```

### Frontend tsc
```
npx tsc --noEmit → exit 0
```

---

## 實作細節

### `_freshness_label(dt)` 邏輯
- `None` → `"unknown"`
- 距今 ≤ 86400 秒（24 h）→ `"fresh"`
- 距今 > 86400 秒 → `"stale"`

### `_EXTERNAL_RELIABILITY` 對照表
| source | reliability |
|---|---|
| apple_health | 0.90 |
| google_fit | 0.88 |
| omron | 0.88 |
| wearable / fitbit / garmin / samsung / withings | 0.85 |
| 未知來源 | 0.80 (fallback) |

### external_metrics 抽取邏輯
- 從現有 `metric_rows`（30 天查詢）中篩選 `source != 'manual'`
- 不新增額外 DB query
- 每筆回傳：`source`, `timestamp` (ISO8601), `freshness`, `reliability`, `summary`
- `summary` 格式：`[{source}] 血壓 130/85、血糖 95.0、體重 70.5kg、...`

---

## 風險 / Unknown / 後續建議

| 項目 | 說明 |
|---|---|
| 真實資料庫中的 source 值多樣性 | 目前 source 欄位為 free-text String(40)，沒有 ENUM 約束。若真實資料中出現非預期 source 值（如 `"Withings"` 大寫），會走 fallback reliability 0.80。建議未來在資料入口統一 lowercase normalize。 |
| external_metrics 未加入 `missing_data` 提示 | 設計決定：external metrics 是補充資料，非必填，不適合觸發 missing_data 警告。 |
| freshness 邊界 24h | 目前 "fresh" = 24h 內。若 wearable 每小時同步，這個邊界合理。但若使用場景改為「當天」概念，建議改為 calendar day boundary。 |
| orchestrator 10 tests 失敗 | 與本任務完全無關，為 `PLANNER_SKIP_SAFE_RUN` 環境設定問題，不在本任務修改範圍。 |
| E2E / API integration test | 未執行 live API call 驗證，unit tests 覆蓋邏輯層，但真實 DB 回傳的 source 值尚未在 staging 驗證。 |

---

## Final Classification

**`P0_EVIDENCE_EXTERNAL_METRICS_DONE`**
