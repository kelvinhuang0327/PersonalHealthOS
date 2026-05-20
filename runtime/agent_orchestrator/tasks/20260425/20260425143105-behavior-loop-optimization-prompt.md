# Planner Task Prompt

## Objective
產品問題衝刺: 補強長期未覆蓋的產品領域: behavior_loop_optimization

## Task Draft
產品問題衝刺: 補強長期未覆蓋的產品領域: behavior_loop_optimization

User Value: 4 product areas have had no sprint in 30+ days: behavior_loop_optimization, health_narrative_deepening, user_journey_analysis, retention_habit_loop. These areas have accumulated unaddressed product debt that affects user experience.

Product Maturity Impact: Unbalanced product development creates gaps in user experience quality. The neglected area "behavior_loop_optimization" likely has the highest opportunity for improvement relative to effort.

Expected Change: The behavior_loop_optimization area receives at least one concrete improvement that measurably advances user value in that domain.

Objective: Focus this sprint entirely on "behavior_loop_optimization". Make the highest-impact change possible in that area.

Phase 1: Audit the current state of "behavior_loop_optimization" in the codebase. What exists? What is broken or missing? What do users encounter?
Phase 2: Identify the single highest-impact change. Think: what is the one thing a user in this area needs most?
Phase 3: Implement that change. Keep scope tight — one real improvement is better than five half-finished ideas.
Phase 4: Run make backend-test and npm run build. Document what changed and why it matters to the user.

Scope: backend/app/, frontend/app/platform/behavior-loop-optimization/
Acceptance Criteria: At least one concrete, tested change in the behavior_loop_optimization area; make backend-test passes; npm run build passes.
focus_keys: behavior_loop_optimization, health_narrative_deepening, user_journey_analysis, retention_habit_loop, product_debt
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
| 信心度 | 0.95 |
| Pass Rate | 95% |
| 失敗率 | 0% |
| 近期任務數 | 20 |

> 95% gate pass rate across last 20 tasks.

## Previous Context
Latest task #305 status=QUEUED objective=8-hour product sprint: Health Narrative v3 causal chain and human-readable rewrite
