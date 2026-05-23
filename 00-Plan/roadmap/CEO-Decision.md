# CEO Decision — PersonalHealthOS Daily Direction

## 1. CEO Review Date

2026-05-23 Asia/Taipei

## 2. Reviewed Inputs

- [Confirmed] `00-Plan/roadmap/roadmap.md` updated 2026-05-23 by CTO.
- [Confirmed] `00-Plan/roadmap/CTO-Analysis.md` 2026-05-23 by CTO.
- [Confirmed] User-provided handoff "工程交接報告 — P13 Auth E2E + Entrypoint Hardening" (referenced inside CTO docs).
- [Confirmed] Git state: canonical repo `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS` on `main`, HEAD `de78305`.
- [Confirmed] Working tree dirty: `.gitignore`, `Makefile`, 5 roadmap docs, 3 staged deletions (`frontend/tsconfig.tsbuildinfo`, `runtime/launchd/pids/backend.pid`, `runtime/launchd/pids/frontend.pid`), 2 untracked test files (`test_auth_negative_smoke.py`, `test_real_token_auth_negative.py`).
- [Confirmed] Product positioning: AI personal health assistant integrating symptoms / history / reports / metrics / actions / outcomes / family / future devices.

## 3. Yesterday Work Value Assessment

| Item | Value | Note |
| --- | --- | --- |
| `test_real_token_auth_negative.py` (7 tests, real JWT decode path) | [Confirmed] Real value | API-level cross-user rejection now evidence-based |
| `get_target_person` ownership 未在測試中 override | [Confirmed] Real value | production enforcement path preserved |
| `test_auth_negative_smoke.py` (override-style) | [Confirmed] Real value | fallback coverage |
| `Makefile` `backend-smoke` target | [Confirmed] Real value | canonical reproducible entrypoint |
| `.gitignore` rules for runtime artifacts | [Confirmed] Real value | pre-flight cleanup foundation |
| Backend 723/723 PASS / tsc / next build / backend-smoke | [Inferred] Real value | reported in active_task_report.md, not independently rerun |
| **All P13 changes NOT YET COMMITTED** | [Risk] Critical governance gap | HEAD still at P12 `de78305`, dirty tree blocks next agent |
| SQLite UUID coercion shim | [Risk] Test-local only | PostgreSQL behavior unverified |
| Browser auth flow | [Risk] Never run | API trust ≠ browser session trust |
| CI workflow `.github/workflows/ci-cd.yml` | [Risk] Still bare `pytest -q` | CI/agent regression interpretation divergent |

結論: P13 內容是實質推進, 但「未 commit」使這份推進對下一輪 agent 不可見。最高優先必須是 **將 P13 變更轉為 git history evidence**, 之後才能在乾淨基礎上做 browser auth smoke。

## 4. CTO Judgment Review

**判斷: 部分採納 (Partially Approved)**

### 採納
- [Confirmed] API-level real-token auth smoke 退役為 blocker (P13 已完成)。
- [Confirmed] Browser auth smoke 為下一個信任缺口。
- [Confirmed] CI entrypoint hardening 為 governance debt。
- [Confirmed] PostgreSQL parity 為真實 gap。
- [Confirmed] 不啟新 feature phase。
- [Confirmed] Wearable / notification 維持降級。

### 修正
- [Rejected as 5 parallel P0s] CTO 再次列 5 個 P0, 過寬。CEO 收斂為「single sprint with 2 sub-acceptance」。
- [Reordered] **P13 commit finalization 必須先於 browser smoke**, 否則 dirty tree 阻塞 pre-flight。
- [Downgrade] CI workflow hardening 推至明日 P0, 今日不擠。
- [Downgrade] PostgreSQL parity 改為 **P2 plan**, 非 P0 (需 Postgres 環境, 非 1 day scope)。
- [Move] Report archive strategy 至 P1 governance, 加註「保留歷史, 切 archive 目錄」。

### 過度樂觀 / 遺漏
- [Risk] CTO 未獨立重跑 backend 723 PASS / next build / backend-smoke, 完全依賴 active_task_report.md 自報。CEO 不要求今日重跑 (避免 scope creep), 但 worker 報告須明示「依賴上一輪自報」。
- [Risk] CTO 未檢查 `D ` 是 `git rm` 還是 `git rm --cached`; 若為前者則 daemon pid 檔被刪可能影響本機。Worker pre-flight 必須確認。

## 5. Roadmap Gap Assessment

| Gap | 行動 |
| --- | --- |
| 5 並列 P0 過寬 | 收斂為「single sprint, 2 sub-acceptance」 |
| P13 未 commit | 列為 sprint 第一項 (governance unblock) |
| Browser auth smoke | 列為 sprint 第二項 |
| CI workflow | 明日 P0 候選, 今日不動 |
| PostgreSQL parity | 降為 P2 plan, 非 P0 |
| Report archive | 移 P1 |
| `D ` staging 意圖未明 | Worker pre-flight 用 `git diff --cached --stat` 確認 |
| Backend 723 自報 | 不要求今日重跑, 報告須註明來源 |

## 6. CEO Priority Decision

### P0 (今日 single sprint, 名稱: `P13-FINALIZE-AND-BROWSER-AUTH-SMOKE`)

依賴序 (A 必先於 B):

**A. P13 Working Tree Finalization (governance unblock)**
- 確認 dirty/staged/untracked 清單與 P13 邏輯吻合
- 按邏輯分組做 2–3 個 commit:
  - C1: `feat(auth): P13 real-token JWT negative smoke + override smoke` (兩個測試檔)
  - C2: `chore(governance): backend-smoke target, .gitignore artifact rules, README/Makefile entrypoint`
  - C3: `docs(roadmap): P13 closure — roadmap.md, CTO-Analysis.md, CEO-Decision.md, active_task.md, active_task_report.md`
- 驗收: HEAD 前進至少 1 步, `git status --short` clean (或剩 CEO 本次新增的 docs)

**B. Browser Auth Negative Smoke (Playwright minimal)**
- 利用 frontend 既有 `npm run e2e` (Playwright)
- 第一步: grep 確認是否已有 login helper / auth fixture
- 若 fixture 存在: 寫 1 個 minimal browser test, user A 登入後嘗試讀 user B family page → 預期 redirect / 403 / 404 / 無資料洩漏
- 若 fixture 不存在: 輸出 `BROWSER_AUTH_E2E_NOT_IMPLEMENTED` + 缺哪個 helper + 對應 Next route, **不強推新測試 framework**
- 驗收: 1 個 PASS, 或 NOT_IMPLEMENTED + 詳細 gap report

### P0 (明日候選, 不擠今日)
- CI workflow `.github/workflows/ci-cd.yml` 改用 `.venv/bin/python -m pytest` 或等價 reproducible 指令

### P1
1. Playwright regression for Daily Assistant / Actions / Trust / Outcome / Family Health Card
2. Unknown / missing trust fallback UI + regression
3. Report archive strategy (`active_task_report.md` 切 archive 目錄, 保留歷史)
4. Product signal reliability (completion / snooze / conversion / acceptance)

### P2
1. PostgreSQL auth parity lane plan (owner / scope / test target / 環境設置)
2. Provider-neutral device schema (HR / pulse / sleep / steps / activity / SpO2)
3. SpO2/pulse migration planning
4. Mock/manual import reliability + source normalization
5. 真實 wearable connectors 維持 paused

### P3–P10
- P3 症狀智慧 (timeline / severity / pattern / → recommendation / → reminder)
- P4 報告到行動閉環 + conversion tracking + E2E smoke
- P5 通知智慧化 (降級)
- P6 個人化與學習
- P7 敘事記憶
- P8 家庭 / 多人健康助手 (permission/isolation 持續硬化)
- P9 Orchestrator governance + CI entrypoint + report archive
- P10 生產合規 (auth / DB parity / deployment smoke / audit / privacy / monitoring)

### Retired / Paused
- [Retired] API-level real-token auth negative smoke (P13 已完成)
- [Retired] "No git repo" 阻塞
- [Paused] 真實 wearable 連接器
- [Paused] Notification intelligence
- [Paused] CTO 自行產出 worker prompt (instruction 禁止)

## 7. Today Focus Direction

**單一焦點: P13 Finalize + Browser Auth Negative Smoke**

- Roadmap phase: P0 / P10 extension
- 為什麼重要:
  - P13 程式碼未 commit, dirty tree 阻塞下一輪 agent
  - Browser auth 是真實用戶面對的層, API auth trust 不等於 session trust
- 系統成熟度推進:
  - 把 P13 從「working tree evidence」升為「git history evidence」
  - 把 "claimed API auth trust" 升為 "evidenced browser auth boundary"
- 預期收益:
  - HEAD 移至 P13 closure commit, 下輪 agent 不需處理 dirty
  - 一個 browser-level negative test 證明真實 session/JWT flow, 或精確列出缺失 fixture
- 風險:
  - Playwright 啟動本地 dev server 可能因 port 衝突失敗 → 允許 NOT_IMPLEMENTED partial
  - Commit 包山包海會難 review → 強制 2–3 commit 邏輯切分
- 驗收: 子驗收 A `clean tree + HEAD 前進`, 子驗收 B `PASS 或 NOT_IMPLEMENTED + gap detail`
- 是否採納 CTO: 部分採納; 採納 Direction 1 (browser auth smoke); 推遲 Direction 2 (CI) 至明日; 降級 Direction 3 (PostgreSQL) 至 P2 plan

## 8. Risks / Blind Spots

- [Risk] Working tree 內 `D ` staging 意圖未明; worker pre-flight 必須用 `git diff --cached --stat` 確認是 `git rm --cached` 而非 `git rm` 實體刪除。
- [Risk] 若 `runtime/launchd/pids/*.pid` 實體被刪, 本機 daemon 狀態可能受影響; 嚴禁 worker 主動刪除任何 `runtime/**` 實體檔案。
- [Risk] CTO 未獨立重跑 backend 723 PASS; 今日 sprint 不要求重跑, 但報告須註明「依賴 active_task_report.md 自報, 未本輪 rerun」。
- [Risk] Playwright `npm run e2e` 需要 dev server 啟動; 若 port 衝突或環境不足, NOT_IMPLEMENTED 為合法 partial 結果。
- [Unknown] Playwright fixture 是否已有 login helper / token bootstrap; worker 第一步 grep, 不存在則只輸出 gap, 不建框架。
- [Risk] Commit message 若一次包山包海, 未來 revert / cherry-pick 困難; 強制邏輯切分。
- [Inferred] CEO/CTO/Roadmap 三檔的 modification 是 P13 governance 一部分, 應與 P13 一起 commit (C3 docs commit)。
- [Risk] 本輪 CEO 新增的 CEO-Decision.md + active_task.md modification 若在 worker 動工後寫入, 會再次造成 dirty; 因此 CEO 必須先寫完 docs, 再讓 worker 動。
- [Unknown] PostgreSQL parity 真實成本未估; 列 P2 plan 不視為承諾。
- [Risk] Report archive 移 P1 後若一直推遲, `active_task_report.md` 持續膨脹; 下次 CTO review 應 escalate。

## 9. CEO Final Decision

**CEO_DECISION_PARTIALLY_APPROVED**

採納 CTO 對 P13 已關 API-level auth blocker、browser auth 為下一缺口、PostgreSQL parity 真實存在的判斷。
否決「5 並列 P0」結構, 改為「single sprint with 2 sub-acceptance, 依賴序」。
今日單一 task 寫入 `00-Plan/roadmap/active_task.md`。
CI hardening 推至明日 P0; PostgreSQL parity 降至 P2 plan; Report archive 移至 P1。

## 10. CEO 摘要 (10 行內)

1. P13 真實推進 API auth 信任邊界, 但所有產出未 commit。
2. HEAD 仍在 P12 `de78305`, dirty tree 是當前最大 governance 阻塞。
3. CTO 方向正確但 5 並列 P0 過寬, CEO 收斂為單一 sprint。
4. 今日聚焦: P13 finalize → browser auth negative smoke。
5. Commit 分 2–3 個邏輯組 (tests / governance / docs)。
6. Browser smoke 允許 NOT_IMPLEMENTED partial; 不強推新 framework。
7. CI workflow hardening 明日 P0, 今日不擠。
8. PostgreSQL parity 降為 P2 plan, 非 P0 阻塞。
9. Report archive 移 P1, 不今日動。
10. Final: **CEO_DECISION_PARTIALLY_APPROVED**。
