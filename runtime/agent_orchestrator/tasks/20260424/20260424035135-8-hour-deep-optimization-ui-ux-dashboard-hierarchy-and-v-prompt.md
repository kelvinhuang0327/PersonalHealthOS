# Planner Task Prompt

## Objective
8-hour deep optimization: UI/UX Dashboard hierarchy and visual-feedback consistency

## Task Draft
8-hour deep optimization: UI/UX Dashboard hierarchy and visual-feedback consistency

Objective: Audit and fix layout hierarchy, spacing inconsistencies, visual-feedback states, and component style drift across all platform pages.

Phase 1: Audit frontend/app/platform/ pages. List the top 8 hierarchy / spacing / colour issues found (with file + line references).
Phase 2: Inspect frontend/components/ for shared components that render differently across pages. Document each inconsistency.
Phase 3: Fix identified issues. Run `npm run lint` to verify no regressions. Record a before/after summary for each fix.
Phase 4: Smoke-test key user flows (dashboard → insights → actions → reports) and confirm visual hierarchy is correct.

Scope: frontend/app/platform/, frontend/components/, frontend/styles/
Files to inspect: tailwind.config.ts, app/platform/dashboard/page.tsx, components/dashboard/, components/shared/
Recommended commands: npm run lint, npm run build
Acceptance Criteria: npm run lint passes with 0 errors; at least 5 visual issues resolved with evidence; no new TypeScript errors introduced.
focus_keys: ui_ux, dashboard, visual_feedback, component_consistency
expected_duration_minutes: 480

## Scope
- Read backlog and project references listed in project profile.
- Implement only what is required to satisfy this task objective.
- Produce both human-readable and machine-readable delivery artifacts.

## Constraints
- Do not modify protected paths from project profile.
- Do not leave the task in RUNNING when blocked by runtime/permission issues.
- Keep changes focused and production-safe.

## Acceptance Criteria
- Pass required check: make backend-test
- Pass required check: backend:pytest
- Pass required check: frontend:npm run build
- No forbidden path modifications.

## Handoff Notes
- Record changed files in task_result.json.
- Attach evidence for each acceptance check.
- Keep next_action clear for the next planner tick.

## System State
| 項目 | 値 |
|------|----|
| Regime | `ACTIVE` |
| 信心度 | 1.00 |
| Pass Rate | 100% |
| 失敗率 | 0% |
| 近期任務數 | 20 |

> 100% gate pass rate across last 20 tasks.

## Focus Keys
ui_ux, dashboard, visual_feedback, component_consistency

## Expected Duration
480 minutes (8.0h)

## Previous Context
Latest task #140 status=COMPLETED objective=建立關鍵 API 與資料流程的 8 小時回歸研究任務，驗證核心健康事件管線在真實資料分布下的穩定性
Latest gate verdict=PASS reason=
