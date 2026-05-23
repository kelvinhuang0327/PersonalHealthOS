# Active Task — P13 Finalize + Browser Auth Negative Smoke

## 任務名稱

P13-FINALIZE-AND-BROWSER-AUTH-SMOKE

## 背景

P13 Auth E2E + Entrypoint Hardening handoff 與 CTO review 確認:
- `backend/tests/test_real_token_auth_negative.py` (7 tests, real JWT decode path) 已存在於 working tree
- `backend/tests/test_auth_negative_smoke.py` (override-style) 已存在於 working tree
- `Makefile` 新增 `backend-smoke` target, `.gitignore` 加入 runtime artifact 規則
- README/Makefile entrypoint 對齊
- Backend 723/723 PASS, tsc 0 errors, next build PASS, backend-smoke 10/10 PASS (依 active_task_report.md 自報, CTO 未獨立重跑)

關鍵問題: **所有 P13 產出仍未 commit**。HEAD 仍在 P12 `de78305`。`git status` 顯示:
```
 M .gitignore
 M Makefile
 M 00-Plan/roadmap/{CEO-Decision,CTO-Analysis,active_task,active_task_report,roadmap}.md
D  frontend/tsconfig.tsbuildinfo
D  runtime/launchd/pids/backend.pid
D  runtime/launchd/pids/frontend.pid
?? backend/tests/test_auth_negative_smoke.py
?? backend/tests/test_real_token_auth_negative.py
```

CEO 於 2026-05-23 裁決: 今日聚焦兩個依賴序子驗收 — A 必先於 B。

## Branch Governance (MANDATORY)

- Canonical repo: `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS`
- Canonical branch: `main`
- 嚴禁: 新增 repo / 新分支 / 新 worktree / checkout 其他 branch / detached HEAD

Pre-flight 必跑:
```
git rev-parse --show-toplevel
git branch --show-current
git status --short
git diff --cached --stat
```

若非 canonical repo / branch / 出現非預期 dirty 檔 → 停工並回報。

## 目標

按依賴序完成兩個子驗收:
- A. P13 working tree finalize, HEAD 前進, working tree clean
- B. Browser-level auth negative smoke: 1 個 PASS, 或 `BROWSER_AUTH_E2E_NOT_IMPLEMENTED` + 精確 gap report

## 子驗收 A — P13 Working Tree Finalization

### 1. Staging 意圖確認
- `git diff --cached --stat` 確認三個 `D ` 是 `git rm --cached` (僅移出 index, 實體檔保留) 而非 `git rm` (實體刪除)。
- 若三個 pid/tsbuildinfo 實體仍存在於檔案系統, OK。
- 若實體不存在 (被 `rm` 刪了) → **停工回報**, 不繼續。

### 2. 確認 P13 程式碼來源真實
- 讀取 `backend/tests/test_real_token_auth_negative.py` 與 `backend/tests/test_auth_negative_smoke.py` 前 30 行, 確認為 real-token / override-style auth 測試, 不是其他 phase 殘留。
- 若內容與 P13 描述不符 → **停工回報**。

### 3. 邏輯分組 commit (2 或 3 個 commit)
- C1: `feat(auth): P13 real-token JWT negative smoke + override smoke`
  - 包含: `backend/tests/test_real_token_auth_negative.py`, `backend/tests/test_auth_negative_smoke.py`
- C2: `chore(governance): backend-smoke target + artifact ignore rules + entrypoint alignment`
  - 包含: `Makefile`, `.gitignore`, 三個 staged deletion (`frontend/tsconfig.tsbuildinfo`, `runtime/launchd/pids/backend.pid`, `runtime/launchd/pids/frontend.pid`)
- C3: `docs(roadmap): P13 closure — roadmap + CTO + CEO + active task + report`
  - 包含: `00-Plan/roadmap/{roadmap,CTO-Analysis,CEO-Decision,active_task,active_task_report}.md`
- Commit message body 可加 `Co-Authored-By: Claude <noreply@anthropic.com>` (可選)
- 嚴禁 `git push` (除非用戶要求)
- 嚴禁 amend 既有 commits
- 嚴禁 `git add -A`; 必須明確列檔
- 嚴禁 skip pre-commit hooks (若有 hook 失敗, 修復後重新 commit, 不 amend)

### A 驗收
- `git log --oneline -5` 顯示 2 或 3 個新 commit 在 `de78305` 之上
- `git status --short` 為空 (或僅本任務 worker 自己新建的 report 檔)
- 三個 pid/tsbuildinfo 實體檔仍存在於 filesystem

## 子驗收 B — Browser Auth Negative Smoke (Playwright)

### 1. Fixture probe
```
grep -rn "test\.use\|login\|authenticate\|storageState\|access_token" frontend/tests/ 2>/dev/null | head -40
ls frontend/tests/ 2>/dev/null
ls frontend/tests/e2e/ 2>/dev/null
cat frontend/playwright.config.ts 2>/dev/null | head -60
```

### 2. 分支判斷
- **若 login helper / storageState fixture 存在**:
  - 寫 1 個 minimal browser test: `frontend/tests/e2e/auth-negative.spec.ts` (或對應目錄)
  - 場景: user A 登入 → 嘗試訪問 user B 的 family context 頁面 (e.g. `/platform/family?profile=<userB_pid>` 或 API call) → 預期 redirect / 403 / 404 / 無 user B 資料洩漏
  - 跑 `npm run e2e` (限該檔案), 記錄結果
  - 嚴禁啟動全部 e2e suite (避免 scope creep)
- **若 fixture 不存在**:
  - 標記 `BROWSER_AUTH_E2E_NOT_IMPLEMENTED`
  - 在報告中精確列出:
    - 缺哪個 fixture (login helper / token bootstrap / storageState)
    - 對應 Next 路由 (login page path, family page path)
    - 建議測試斷言點 (redirect URL / response status / DOM 不應出現 user B 資料)
  - **嚴禁** 安裝新 npm package
  - **嚴禁** 新建 Playwright config 或大型 framework

### B 驗收
- 1 個 browser smoke PASS, 報告含 trace 或 console summary
- 或 `BROWSER_AUTH_E2E_NOT_IMPLEMENTED` + 完整 gap detail (符合上述列點)

## 允許修改範圍

- `backend/tests/test_real_token_auth_negative.py`, `backend/tests/test_auth_negative_smoke.py` (僅 commit, 不改內容)
- `Makefile`, `.gitignore` (僅 commit, 不改內容)
- `00-Plan/roadmap/*.md` (僅 commit)
- `frontend/tests/e2e/auth-negative.spec.ts` 或同性質單檔 (僅在 fixture 存在時新增)
- `00-Plan/roadmap/active_task_report.md` (新 P13 finalize 區塊置頂, 不刪歷史; 可在 C3 commit 之後做 D4 commit 或併入 C3)

## 禁止修改範圍

- `backend/app/**`
- `frontend/app/**`
- `frontend/lib/**`
- `frontend/playwright.config.ts` 等 config 檔
- `.github/workflows/**` (CI hardening 明日做)
- `backend/app/orchestrator/**`
- `docs/**`
- `00-Plan/roadmap/CEO-Decision.md`, `CTO-Analysis.md`, `roadmap.md` (僅 commit, 不改內容)
- 真實 wearable / Apple Health / Google Fit 接入
- PostgreSQL 環境設置 (P2 plan, 非今日)
- 新 npm / pip dependency
- `git push` / new branch / new worktree / detached HEAD
- `runtime/**` 內任何實體檔案刪除
- `git rm` (僅可 `git rm --cached`, 若必要)

## 測試指令

```
# Pre-flight
git rev-parse --show-toplevel
git branch --show-current
git status --short
git diff --cached --stat

# A. 邏輯切分後做 commit
# (具體指令由 worker 按 C1/C2/C3 分組決定, 嚴格列檔, 不用 git add -A)

# 驗證 A
git log --oneline -5
git status --short

# B. Fixture probe
grep -rn "test\.use\|login\|storageState" frontend/tests/ 2>/dev/null | head -40
cat frontend/playwright.config.ts 2>/dev/null | head -60

# B. 若 fixture 存在, 跑單檔 e2e
cd /Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS/frontend
npx playwright test tests/e2e/auth-negative.spec.ts

# B. 若 fixture 不存在: 不跑, 只輸出 gap report
```

## 輸出報告位置

`00-Plan/roadmap/active_task_report.md` (頂端新增 P13-FINALIZE 區塊 + browser smoke 區塊, 不刪除歷史; 舊內容下移為 appendix)

報告必須包含:
1. Branch governance pre-flight 結果 (repo / branch / status / staged diff stat 摘要)
2. A1. Staging 意圖確認結果 (`D ` 為 `git rm --cached` 還是 `git rm`)
3. A2. P13 test files 內容真實性確認
4. A3. Commit list (C1/C2/C3 commit hash + message + 檔案數)
5. A 驗收: `git log -5`, `git status --short`, pid/tsbuildinfo 實體檔存在性
6. B1. Fixture probe 輸出摘要
7. B2. Branch 判斷 (Implemented or NOT_IMPLEMENTED)
8. B 測試結果或 gap report
9. Known limitations / Unknown / Inferred
10. Final classification

## Final Classification (擇一)

- `P13_FINALIZED_AND_BROWSER_AUTH_VERIFIED` (A PASS + B PASS)
- `P13_FINALIZED_BROWSER_AUTH_NOT_IMPLEMENTED` (A PASS + B 為合法 NOT_IMPLEMENTED with detail)
- `P13_FINALIZE_PARTIAL` (A 部分 commit 或 staging 意圖確認失敗)
- `P13_FINALIZE_BLOCKED` (A1 或 A2 觸發停工; staging 為實體刪除, 或測試檔內容不符)
- `P13_FINALIZE_REJECTED` (worker 發現超出 scope 衝突, 停工回報)

## Anti-Scope-Creep Reminder

- 嚴禁開始新功能 / 新 phase / CI workflow / PostgreSQL setup。
- 嚴禁修改 application code (backend/app, frontend/app, frontend/lib)。
- 嚴禁修改 Playwright config / 既有 fixture。
- 嚴禁安裝新 dependency。
- 嚴禁刪除 `runtime/**` 實體檔案。
- 嚴禁 `git push` / 新分支 / amend / skip hooks。
- 嚴禁全 e2e suite 跑; 僅限新建單檔。
- 若 fixture 不存在, **就只輸出 gap report**, 不建框架。
- 若 staging 顯示實體刪除, **立即停工回報**, 不嘗試恢復。
