# CEO Decision — PersonalHealthOS Daily Direction

## 1. CEO Review Date

2026-05-20 Asia/Taipei

## 2. Reviewed Inputs

- [Confirmed] `00-Plan/roadmap/current_state.md` — P1 Daily Assistant UI Recovery handoff.
- [Confirmed] `00-Plan/roadmap/CTO-Analysis.md` — CTO 2026-05-20 review.
- [Confirmed] `00-Plan/roadmap/roadmap.md` — CTO-consolidated roadmap.
- [Confirmed] Product positioning补充: AI 個人健康小助手, integrates symptoms/history/reports/metrics/actions/outcomes/future devices.

## 3. Yesterday Work Value Assessment

| Item | Value | Note |
| --- | --- | --- |
| Shared `RecommendationTrustBlock` consolidated | [Confirmed] Real value | 消除 trust UI drift, 統一 backend-driven 契約 |
| Dashboard/Actions trust 同源 | [Confirmed] Real value | 防止未來 divergence |
| Backend 101 tests PASS | [Confirmed] Real value | 但僅 unit-level |
| `tsc --noEmit` / `next build` PASS | [Confirmed] Real value | type/build 層級 |
| Runtime / E2E / Docker / smoke | [Risk] 未跑 | 不能宣稱 UI 成熟 |
| 整體 sprint | [Inferred] 推進 "safe to iterate"，非新用戶價值 | verification sprint by design |

結論: 昨日推進的是「可迭代性」而非「產品成熟度」。仍需 P0 用戶價值推進。

## 4. CTO Judgment Review

**判斷: 部分採納 (Partially Approved)**

### 採納
- [Confirmed] Runtime verification 為 P0 缺口。
- [Confirmed] `external_metrics: []` 為產品定位最直接落差，列 P0。
- [Confirmed] Unknown trust fallback 列 P0/P1 邊界, CEO 同意納入 P0。
- [Confirmed] 真實 wearable connector 降為 P2。
- [Confirmed] Notification intelligence 降級。

### 不採納
- [Rejected] CTO 把「change-control / git baseline」列 P0 Blocker 並要求 CEO 裁決。
  - CEO 裁決: 嚴禁新增 repo (本日明確指示)。
  - 替代方案: 採用 snapshot tarball 備份至 `runtime/snapshots/`, 排程後續任務處理, 不阻塞今日交付。
- [Rejected as P0] Orchestrator gate credibility 阻塞用戶價值推進。
  - CEO 裁決: 移至 P9 governance 子軌道, 與用戶交付並行, 不阻塞 P0。

### 過度悲觀 / 樂觀
- [Risk] CTO 把 5 個項目同列 P0, 過寬, 今日無法全做; CEO 收斂為「最高優先單一方向」+ 2 個並行小項。
- [Inferred] CTO 對 evidence bundle external_metrics 的判斷貼近產品定位, 採納。

## 5. Roadmap Gap Assessment

| Gap | 行動 |
| --- | --- |
| P0 列入 change-control | [Retire-for-now], 改 snapshot 策略 |
| P0 列入 orchestrator gate | 降為 P9 子軌, 不阻塞 P0 |
| external_metrics 為空 | 維持 P0, 今日聚焦 |
| Unknown trust fallback | 維持 P0 |
| Runtime smoke | 維持 P0 但用輕量 curl/手動而非 Playwright |
| Playwright | 移至 P1 |

## 6. CEO Priority Decision

### P0 (今日 / 本週)
1. **Evidence Bundle external_metrics 第一級化** (今日焦點)
2. Unknown trust fallback UX + regression test
3. Health Assistant runtime smoke (curl + 手動瀏覽器)

### P1
1. Playwright 對 Dashboard/Actions/Trust/Outcome Feedback 的瀏覽器級回歸
2. Outcome feedback 7/14/30 日窗口精修
3. Product signal 可靠性 (completion / snooze / conversion / acceptance)
4. Report/insight-to-action UX (限 P0 完成後)

### P2
1. Provider-neutral external metrics schema (heart rate / pulse / sleep / steps / activity / SpO2)
2. Mock / manual import layer with source / freshness / reliability
3. Device signal detection
4. 不接 Apple Health / Google Fit / 真實 wearable API

### P3–P10
- P3 症狀智慧 (timeline, severity, pattern, → recommendation, → reminder)
- P4 報告到行動閉環
- P5 通知智慧化 (降級, 等 P0/P1 verified)
- P6 個人化與學習
- P7 敘事記憶
- P8 家庭 / 多人健康助手
- P9 產品分析 + orchestrator gate 硬化 (合併自原 P0)
- P10 生產合規與生態

### Retired / Paused
- [Retired-for-now] 新增 git repo (CEO 否決)
- [Paused] 真實 wearable 連接器
- [Paused] Notification intelligence

## 7. Today Focus Direction

**單一焦點: Evidence Bundle `external_metrics` 第一級化**

- Roadmap phase: P0
- 為什麼重要: 產品定位是「整合所有個人健康資料」, 但目前 evidence bundle 對 `external_metrics` 回傳 `[]`, 等於對使用者承諾的「整合所有資料」未兌現。
- 對系統成熟度的實質推進: 把已存在的 source-tagged metrics 從隱性資料升為顯性 evidence, recommendation/trust 取得更多輸入, 為 P2 wearable schema 鋪路。
- 預期收益:
  - Recommendation 信號來源更完整
  - Trust score 計算輸入更豐富
  - 為 P2 device readiness 預留契約
- 風險:
  - 過度設計 schema → 限制只暴露現有 `health_metrics.source` 欄位
  - 無 git rollback → worker 動工前必須建 snapshot tarball
- 驗收:
  - `/health-assistant/evidence-bundle` 對有 source-tagged metrics 的 user 回傳非空 `external_metrics`
  - 每筆含 source / timestamp / freshness / reliability / summary
  - Backend unit tests 全綠 (含新增測試)
  - `npx tsc --noEmit` 全綠
- 是否採納 CTO 建議: 採納 (對應 CTO Direction 2 / Blocker 3)

## 8. Risks / Blind Spots

- [Risk] 無 git → worker 任何動作前必須 `cp -r backend/app /tmp/backend.app.snapshot.YYYYMMDD-HHMM`。
- [Risk] `health_metrics.source` 欄位實際存在性未經本輪驗證; worker 第一步須 grep 驗證, 缺失即停工回報。
- [Unknown] `external_metrics` 是否已有 service 骨架; worker 須先讀 `backend/app/services/health_assistant_service.py` 確認。
- [Risk] 任務 scope 蔓延; 今日只動 backend evidence bundle, frontend 不改, 若 worker 擴大 scope 須立即停止。
- [Inferred] Runtime smoke / unknown trust fallback 今日不啟動, 等 external_metrics 落地後排下一輪。

## 9. CEO Final Decision

**CEO_DECISION_PARTIALLY_APPROVED**

採納 CTO 對 evidence completeness / runtime verification / unknown trust / wearable downgrade 的判斷。
否決 CTO 對 change-control 與 orchestrator gate 列 P0 阻塞的判斷; 改以 snapshot 策略與 P9 子軌處理。
今日單一可執行任務: Evidence Bundle external_metrics 第一級化, 寫入 `00-Plan/roadmap/active_task.md`。

## 10. CEO 摘要 (10 行內)

1. 昨日為 verification sprint, 推進「可迭代性」非新用戶價值。
2. CTO 分析方向正確, 但 P0 過寬, 需收斂。
3. CEO 否決新增 git repo, 以 snapshot tarball 替代。
4. Orchestrator gate 降為 P9 子軌, 不阻塞用戶交付。
5. 今日 P0 焦點: Evidence Bundle `external_metrics` 第一級化。
6. 對應產品定位「整合所有個人健康資料」最直接落差。
7. Scope 限制: 只暴露現有 `health_metrics.source`, 不引入新欄位。
8. Worker 動工前必須建 snapshot, 第一步驗證 schema 存在。
9. Runtime smoke / unknown trust fallback 排下一輪。
10. Final: CEO_DECISION_PARTIALLY_APPROVED。
