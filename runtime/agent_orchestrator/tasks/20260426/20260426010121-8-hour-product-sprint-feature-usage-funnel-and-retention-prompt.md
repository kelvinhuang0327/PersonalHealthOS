# Planner Task Prompt

## Objective
8-hour product sprint: Feature usage funnel and retention drop-off analysis

## Task Draft
8-hour product sprint: Feature usage funnel and retention drop-off analysis

User Value: Users who do not use certain features are losing value they paid for. This task finds which features are not being used and why, so we can either fix them or retire them.

Product Maturity Impact: Knowing the usage funnel (how many users reach each step) is the foundation of product-led growth. Without it, every design decision is a guess.

Expected Change: The team can see exactly where users drop off. Features with <20% usage are surfaced for redesign or removal. Product decisions shift from intuition to data. The funnel endpoint becomes the primary weekly health metric for the product.

Objective: Build a usage funnel analysis across the core product surfaces and identify the highest-drop-off steps.

Phase 1: Define the funnel steps for the core journey: (1) Login, (2) View Dashboard, (3) View an Insight, (4) Click an Action, (5) Complete an Action, (6) Return next day. Determine which backend events currently exist to measure each step.
Phase 2: Inspect the backend for existing event logging or analytics hooks. What user events are recorded in the database? Is there a concept of "session" or "daily active user"? Document what exists and what is missing.
Phase 3: Implement at least 3 missing funnel event logs. Examples: log when a user views an insight (GET /insights/:id → append to insight_views); log when an action is clicked but not completed; log when a user opens the app on consecutive days.
Phase 4: Build a simple admin API endpoint GET /analytics/funnel that returns per-step counts for the last 7 days. Run `make backend-test`. Document the current funnel drop-off percentages.

Scope: backend/app/api/, backend/app/models/, backend/app/services/
Files to inspect: backend/app/api/ (analytics/admin endpoints), backend/app/models/ (event models)
Acceptance Criteria: 3 funnel event logs implemented; GET /analytics/funnel endpoint returns per-step counts; make backend-test passes; drop-off percentages documented.
focus_keys: analytics, funnel, retention, dau, feature_usage, drop_off
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
analytics, funnel, retention, dau, feature_usage, drop_off

## Expected Duration
480 minutes (8.0h)

## Previous Context
Latest task #359 status=QUEUED objective=產品問題衝刺: 全類別輪替完成 — 選擇下一個最高價值優化領域
