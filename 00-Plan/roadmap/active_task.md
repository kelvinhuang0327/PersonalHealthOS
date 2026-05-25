# Active Task — P62 Recommendation Feedback Timeline View

## 任務名稱

P62-RECOMMENDATION-FEEDBACK-TIMELINE

## 背景

P50–P60 已完成 recommendation → feedback → persistence → snooze → safe outcome → smoke readiness 完整鏈路。
HEAD 在 `6ea326b`。`make runtime-smoke` 全 PASS（含 56 outcome tests）。

目前產品缺口：
- 使用者可標記行動（done/snoozed/not_useful/not_applicable）
- 系統可計算並回傳 safe outcome status
- 但 **無 UI 顯示過去建議的歷史記錄**：使用者無法看到「我這 30 天被推薦了什麼 → 我怎麼回應 → 結果如何」

P62 目標：新增一個 **recommendation feedback timeline** 前端元件，利用現有的
`GET /api/v1/health-assistant/outcome-feedback?window_days=30` API，
將過去 30 天的行動依時序顯示，含使用者回應與 safe outcome status。

## Branch Governance (MANDATORY)

- Canonical repo: `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS`
- Canonical branch: `main`
- 嚴禁: 新增 repo / 新分支 / 新 worktree / checkout 其他 branch / detached HEAD / force push

Pre-flight 必跑：
```
git rev-parse --show-toplevel
git branch --show-current
git status --short
git log --oneline -5
```

STOP conditions:
- repo 非 canonical → STOP
- branch 非 main → STOP
- detached HEAD → STOP
- 00-Plan/roadmap/*.md 以外有 unrelated dirty files → STOP 回報

## 目標

在 bounded scope 內新增 `recommendation-history-card.tsx` 前端元件，使用現有後端 API：
1. 呼叫 `GET /api/v1/health-assistant/outcome-feedback?window_days=30`
2. 依陣列順序，以時序方式顯示每個行動
3. 每筆顯示：行動標題、使用者回應狀態、safe outcome status、說明文字
4. 不需要後端改動（API 已存在、型別已在 P59 更新）
5. 使用現有 STATUS_CONFIG 與 Tailwind 元件樣式（參考 outcome-feedback-card.tsx）

## 範圍

### 允許
- 新建 `frontend/app/components/platform/recommendation-history-card.tsx`
- 在現有平台頁面（如 `/platform/actions`）加入此元件（選擇已有 outcome-feedback-card 的頁面）
- 更新 `frontend/lib/api.ts` 如需新增 helper function（應不需要，型別已在 P59 更新）
- 新增 backend API 測試（沿用 P59 的 TestClient + dependency override 模式）
- 更新 `active_task_report.md`（prepend P62 區塊）

### 禁止
- Do NOT create a new backend endpoint（使用現有 `/outcome-feedback?window_days=30`）
- Do NOT add wearable connectors
- Do NOT modify auth flow
- Do NOT change CI workflows
- Do NOT add new PostgreSQL tables
- Do NOT redesign dashboard or rewrite existing components
- Do NOT claim medical effectiveness from outcome data
- Do NOT create new branches
- Do NOT force push
- Do NOT stage `00-Plan/roadmap/*.md` dirty files unless part of P62 report

## 必要調查

```bash
# 1. 確認現有 outcome-feedback-card 位置
ls frontend/app/components/platform/

# 2. 確認 outcome-feedback 型別
grep -n "OutcomeFeedback\|OutcomeFeedbackItem\|STATUS_CONFIG" \
  frontend/lib/api.ts \
  frontend/app/components/platform/outcome-feedback-card.tsx | head -30

# 3. 確認現有平台頁面使用 outcome-feedback-card 的位置
grep -rn "outcome-feedback-card\|OutcomeFeedbackCard" frontend/ | head -20

# 4. 確認 API endpoint 結構
grep -n "outcome-feedback\|window_days" backend/app/api/health_assistant.py | head -10
```

## 實作規則

### 元件設計
`recommendation-history-card.tsx` 應：
1. Props: `outcomes: OutcomeFeedbackItem[]`（直接接收 API response 的 outcomes 陣列）
2. 依陣列順序顯示每個行動（reverse chronological 或 grouped by status）
3. 每列顯示：
   - 行動標題（`action_title`）
   - 使用者回應（`status`：completed/tracking/not_useful/not_applicable/snoozed）
   - Outcome status（`outcome_status`）：使用現有 STATUS_CONFIG label/color
   - 說明（`explanation`，截短至 2 行）
4. Safe display：不顯示任何醫療效果聲稱；說明直接 pass through（P58/P59 保證 safe copy）
5. 無 data 時顯示 empty state：「過去 30 天尚無建議記錄」

### 整合
- 在已有 `outcome-feedback-card` 的頁面（如 `/platform/actions`）的適當位置加入
- 或以獨立 section 呈現，傳入同一 API response 的 `outcomes`

### 型別
- 使用 `frontend/lib/api.ts` 現有的 `OutcomeFeedbackItem`（P59 已擴充）
- 使用現有 `OutcomeFeedback` response 型別
- 不需新增型別

## 必要驗證

```bash
# 1. TypeScript
cd frontend && npx tsc --noEmit

# 2. Backend outcome tests（確認無回歸）
source backend/.venv/bin/activate && \
  python -m pytest backend/tests/test_outcome_feedback_service.py \
    backend/tests/test_api_outcome_feedback_p59.py -q

# 3. Playwright regression
cd frontend && npx playwright test \
  tests/e2e/p55-action-feedback-loop.spec.ts \
  tests/e2e/p56-recommendation-feedback-persistence.spec.ts \
  tests/e2e/p57-snooze-persistence.spec.ts \
  --reporter=line

# 4. runtime-smoke
make runtime-smoke
```

若任何命令失敗：
- 判斷是否由 P62 引入
- 若是 → 修復後重跑
- 若否（pre-existing）→ STOP 回報，不掩蓋

## Commit 規範

```
feat(frontend): add recommendation feedback timeline card (P62)
```

若有後端測試：
```
test: add P62 recommendation history card API coverage
```

報告 commit：
```
docs(report): P62 recommendation feedback timeline closure
```

嚴禁 stage `00-Plan/roadmap/*.md` dirty files（CEO/CTO 輸出）除非明確是 P62 report。

## 預期最終報告

回傳：
1. 本輪目標
2. 已完成事項
3. 修改或產出的檔案
4. 驗證結果 / 測試結果
5. 目前結論
6. 尚未完成事項
7. 風險與不確定點
8. 建議今天優先處理的方向
9. 下一輪可直接執行的 task prompt
10. CTO agent 10 行內摘要

## Final Classification（擇一）

- `P62_RECOMMENDATION_HISTORY_READY` — 元件存在、TypeScript PASS、Playwright 不回歸
- `P62_RECOMMENDATION_HISTORY_PARTIAL` — 元件存在但有已知限制（記錄）
- `P62_BLOCKED_BY_GOVERNANCE_PREFLIGHT` — pre-flight 失敗
- `P62_REJECTED_SCOPE_CONFLICT` — 發現必要改動超出 scope，停工回報

