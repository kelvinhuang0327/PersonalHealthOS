# Planner Task Prompt

## Objective
Replan task #155: 8-hour product sprint: Cross-page consistency audit — conflicting decisions and broken signals (reason: Delivery has placeholder or insufficient content in: "User Value Delivered", "Product Maturity Impact Achieved", "Expected Change Evidence". Each dimension section must contain ≥80 chars of real evidence, not template scaffolding. Worker must describe specific, observable outcomes.)

## Task Draft
Replan task #155: 8-hour product sprint: Cross-page consistency audit — conflicting decisions and broken signals (reason: Delivery has placeholder or insufficient content in: "User Value Delivered", "Product Maturity Impact Achieved", "Expected Change Evidence". Each dimension section must contain ≥80 chars of real evidence, not template scaffolding. Worker must describe specific, observable outcomes.)

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
| 信心度 | 0.55 |
| Pass Rate | 55% |
| 失敗率 | 45% |
| 近期任務數 | 20 |

> 55% gate pass rate across last 20 tasks.

## Previous Context
Latest task #155 status=REPLAN_REQUIRED objective=8-hour product sprint: Cross-page consistency audit — conflicting decisions and broken signals
Latest gate verdict=RESULT_SHALLOW reason=Delivery has placeholder or insufficient content in: "User Value Delivered", "Product Maturity Impact Achieved", "Expected Change Evidence". Each dimension section must contain ≥80 chars of real evidence, not template scaffolding. Worker must describe specific, observable outcomes.
