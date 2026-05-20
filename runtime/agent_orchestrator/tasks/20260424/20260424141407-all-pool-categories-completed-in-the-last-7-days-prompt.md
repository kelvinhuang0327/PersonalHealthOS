# Planner Task Prompt

## Objective
產品問題衝刺: All pool categories completed in the last 7 days

## Task Draft
產品問題衝刺: All pool categories completed in the last 7 days

User Value: Every pool template was completed within the last 7 days. The planner should generate a problem-specific task based on actual product signals rather than cycling through static templates again.

Product Maturity Impact: Addressing this systemic issue unblocks forward product progress and prevents the orchestrator from cycling through exhausted work.

Expected Change: The detected issue is resolved and the orchestrator generates meaningful new work in subsequent cycles.

Objective: Investigate and resolve: Every pool template was completed within the last 7 days. The planner should generate a problem-specific task based on actual product signals rather than cycling through static templates again.

Phase 1: Analyse the signal data: {'on_cooldown_count': 12}.
Phase 2: Determine root cause and design a targeted fix.
Phase 3: Implement the fix with the smallest safe change set.
Phase 4: Verify with make backend-test.

Scope: backend/app/orchestrator/
Acceptance Criteria: Issue resolved; make backend-test passes.
focus_keys: orchestrator, product_health, signal_detection
expected_duration_minutes: 240

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

## Previous Context
Latest task #163 status=COMPLETED objective=8-hour product sprint: Action → Outcome → Feedback closed-loop optimization
Latest gate verdict=PASS reason=
