# Planner Task Prompt

## Objective
8-hour product sprint: Cross-page consistency audit — conflicting decisions and broken signals

## Task Draft
8-hour product sprint: Cross-page consistency audit — conflicting decisions and broken signals

User Value: A user who sees a "High Risk" label on the Dashboard but "All Good" on the Insights page loses trust immediately. This task hunts and fixes every inconsistency in how health signals are displayed.

Product Maturity Impact: Consistency is the bedrock of clinical trust. A single contradictory data point can destroy months of earned credibility. Consistent, coherent signals are the mark of a mature health product.

Expected Change: A user can navigate from Dashboard to Insights to Actions and see the same risk score and action count everywhere. Trust in the platform's data integrity increases. Conflicting decisions — the #1 source of user confusion — are eliminated.

Objective: Audit all four core surfaces (Dashboard, Insights, Actions, Notifications) for data inconsistencies, conflicting recommendations, and missing context.

Phase 1: Open each surface and record every piece of health data shown: risk score, action count, notification count, insight summary. Check: do the same numbers appear consistently on every surface? Is the same action recommended on both Insights and Actions pages? Document every discrepancy found.
Phase 2: Trace each discrepancy to its source in the backend. Is it a stale cache? A different API endpoint that uses different logic? A UI component that applies different filtering? Identify the root cause.
Phase 3: Fix the top-3 consistency issues. Prioritize: risk score inconsistency > action count mismatch > notification badge mismatch. For each fix, document which file was changed and what the correct source of truth is.
Phase 4: Run `npm run lint` and `make backend-test`. Add a frontend test (or API contract test) that asserts the same risk score is returned from both the Dashboard API and the Insights API.

Scope: frontend/app/platform/, backend/app/api/, backend/app/services/
Files to inspect: app/platform/dashboard/page.tsx, app/platform/insights/, app/platform/actions/, app/platform/notifications/
Acceptance Criteria: At least 3 consistency issues fixed; source of truth documented per data type; npm run lint and make backend-test pass.
focus_keys: consistency, cross_page, conflicting_decisions, trust, data_integrity
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
| 信心度 | 0.63 |
| Pass Rate | 63% |
| 失敗率 | 37% |
| 近期任務數 | 19 |

> 63% gate pass rate across last 19 tasks.

## Focus Keys
consistency, cross_page, conflicting_decisions, trust, data_integrity

## Expected Duration
480 minutes (8.0h)

## Previous Context
Latest task #154 status=QUEUED objective=8-hour product sprint: Feature usage funnel and retention drop-off analysis
