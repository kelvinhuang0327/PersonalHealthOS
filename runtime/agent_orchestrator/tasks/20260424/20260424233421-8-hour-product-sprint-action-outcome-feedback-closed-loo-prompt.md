# Planner Task Prompt

## Objective
8-hour product sprint: Action → Outcome → Feedback closed-loop optimization

## Task Draft
8-hour product sprint: Action → Outcome → Feedback closed-loop optimization

User Value: Users who complete a health action today get no meaningful feedback on whether it worked. This task closes that loop — making every action feel worth doing again.

Product Maturity Impact: Transforms the platform from a task-tracker into a genuine behavior-change engine. Completion rate and 7-day retention are the north-star metrics.

Expected Change: Action completion rate rises as users see that their actions produce measurable outcomes. AI recommendation quality improves progressively as outcome data accumulates — the engine becomes self-improving.

Objective: Design and implement the full behavior loop: Action completion triggers an Outcome check-in prompt; the check-in result feeds back into the AI narrative and the next Action recommendation. Track completion rate before and after.

Phase 1: Map the current behavior loop gap. Find where action completion data exists in the backend (backend/app/api/, backend/app/models/) and where it does NOT feed back into insights or the next recommendation cycle. Document the exact missing links.
Phase 2: Design the Outcome check-in model. Sketch the data schema (action_id, outcome_rating, outcome_note, checked_at). Implement the API endpoint POST /actions/{id}/outcome with proper validation and idempotency.
Phase 3: Wire the outcome into the AI recommendation pipeline. When generating the next prioritized_actions list, weight actions whose previous outcomes were positive higher. Update ai/prompts/health_summary_system_prompt.md to reference recent outcomes.
Phase 4: Add the outcome check-in UI prompt to the frontend action completion flow. Show a simple 1-5 star or thumbs-up/down after marking an action done. Run `npm run lint` and `make backend-test` to confirm no regressions.

Scope: backend/app/api/, backend/app/models/, backend/app/services/, ai/prompts/, frontend/app/platform/, frontend/components/
Acceptance Criteria: POST /actions/{id}/outcome endpoint exists and returns 200; outcome data influences the next AI recommendation cycle; frontend shows outcome prompt after action completion; make backend-test passes; npm run lint passes.
focus_keys: behavior_loop, outcome_tracking, feedback, action_completion, retention
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
| 信心度 | 0.85 |
| Pass Rate | 85% |
| 失敗率 | 15% |
| 近期任務數 | 20 |

> 85% gate pass rate across last 20 tasks.

## Focus Keys
behavior_loop, outcome_tracking, feedback, action_completion, retention

## Expected Duration
480 minutes (8.0h)

## Previous Context
Latest task #200 status=QUEUED objective=8-hour product sprint: Decision Engine scoring weights and explainability
