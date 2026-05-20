# Planner Task Prompt

## Objective
Replan task #160: 8-hour product sprint: Action recommendation precision and deduplication (reason: Delivery has placeholder or insufficient content in: "User Value Delivered", "Product Maturity Impact Achieved", "Expected Change Evidence". Each dimension section must contain ≥80 chars of real evidence, not template scaffolding. Worker must describe specific, observable outcomes.)

## Task Draft
Replan task #160: 8-hour product sprint: Action recommendation precision and deduplication (reason: Delivery has placeholder or insufficient content in: "User Value Delivered", "Product Maturity Impact Achieved", "Expected Change Evidence". Each dimension section must contain ≥80 chars of real evidence, not template scaffolding. Worker must describe specific, observable outcomes.)

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
| Regime | `COLD` |
| 信心度 | 0.60 |
| Pass Rate | 40% |
| 失敗率 | 60% |
| 近期任務數 | 20 |

> 60% of recent tasks failed or required replanning.

## Previous Context
Latest task #160 status=REPLAN_REQUIRED objective=8-hour product sprint: Action recommendation precision and deduplication
Latest gate verdict=RESULT_SHALLOW reason=Delivery has placeholder or insufficient content in: "User Value Delivered", "Product Maturity Impact Achieved", "Expected Change Evidence". Each dimension section must contain ≥80 chars of real evidence, not template scaffolding. Worker must describe specific, observable outcomes.
