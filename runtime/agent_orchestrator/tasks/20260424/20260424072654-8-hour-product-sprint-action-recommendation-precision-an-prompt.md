# Planner Task Prompt

## Objective
8-hour product sprint: Action recommendation precision and deduplication

## Task Draft
8-hour product sprint: Action recommendation precision and deduplication

User Value: Users currently see duplicated or irrelevant action recommendations, which erodes trust and reduces completion rates. This task makes every recommended action feel personally relevant and achievable.

Product Maturity Impact: Precision of action recommendations is a core differentiator. A recommendation engine that learns from outcomes creates a moat that generic apps cannot copy.

Expected Change: Users receive a deduplicated, personalized action list every session. Actions with positive past outcomes rise to the top. Over 4 weeks the recommendation engine becomes measurably self-improving.

Objective: Audit the action recommendation pipeline. Remove duplicates. Improve relevance scoring. Correlate recommended action priority with actual completion rate.

Phase 1: Audit the current action recommendation logic in backend/app/services/. Find where duplicates arise (same action recommended multiple times, same category repeatedly). Document the deduplication gap.
Phase 2: Inspect how prioritized_actions are scored. What signals feed into the priority? Is there any personalization based on past completions or outcomes? Document missing signals.
Phase 3: Implement deduplication: within a single recommendation batch, no action title or category should appear more than once. Add at least one personalization signal (e.g. past completion rate for that action type).
Phase 4: Run `make backend-test`. Add tests that assert: (a) no duplicate action titles in a recommendation batch; (b) actions with higher past completion rates score higher. Document priority vs completion correlation before/after.

Scope: backend/app/services/, backend/app/api/, backend/tests/
Files to inspect: backend/app/services/ (action recommendation services), backend/app/api/ (action endpoints)
Acceptance Criteria: make backend-test passes; no duplicate actions in a recommendation batch (asserted by test); at least one personalization signal implemented; priority vs completion correlation documented.
focus_keys: action_recommendation, deduplication, personalization, completion_rate, precision
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
| 信心度 | 0.42 |
| Pass Rate | 42% |
| 失敗率 | 58% |
| 近期任務數 | 19 |

> 42% gate pass rate across last 19 tasks.

## Focus Keys
action_recommendation, deduplication, personalization, completion_rate, precision

## Expected Duration
480 minutes (8.0h)

## Previous Context
Latest task #159 status=QUEUED objective=Replan task #158: 8-hour product sprint: Dashboard → Insights → Action flow friction reduction (reason: Delivery has placeholder or insufficient content in: "User Value Delivered", "Product Maturity Impact Achieved", "Expected Change Evidence". Each dimension section must contain ≥80 chars of real evidence, not template scaffolding. Worker must describe specific, observable outcomes.)
