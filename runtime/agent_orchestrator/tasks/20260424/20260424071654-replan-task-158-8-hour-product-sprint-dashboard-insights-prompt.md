# Planner Task Prompt

## Objective
Replan task #158: 8-hour product sprint: Dashboard → Insights → Action flow friction reduction (reason: Delivery has placeholder or insufficient content in: "User Value Delivered", "Product Maturity Impact Achieved", "Expected Change Evidence". Each dimension section must contain ≥80 chars of real evidence, not template scaffolding. Worker must describe specific, observable outcomes.)

## Task Draft
Replan task #158: 8-hour product sprint: Dashboard → Insights → Action flow friction reduction (reason: Delivery has placeholder or insufficient content in: "User Value Delivered", "Product Maturity Impact Achieved", "Expected Change Evidence". Each dimension section must contain ≥80 chars of real evidence, not template scaffolding. Worker must describe specific, observable outcomes.)

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
| 信心度 | 0.45 |
| Pass Rate | 45% |
| 失敗率 | 55% |
| 近期任務數 | 20 |

> 45% gate pass rate across last 20 tasks.

## Previous Context
Latest task #158 status=REPLAN_REQUIRED objective=8-hour product sprint: Dashboard → Insights → Action flow friction reduction
Latest gate verdict=RESULT_SHALLOW reason=Delivery has placeholder or insufficient content in: "User Value Delivered", "Product Maturity Impact Achieved", "Expected Change Evidence". Each dimension section must contain ≥80 chars of real evidence, not template scaffolding. Worker must describe specific, observable outcomes.
