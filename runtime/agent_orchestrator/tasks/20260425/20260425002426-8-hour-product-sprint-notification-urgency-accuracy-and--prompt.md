# Planner Task Prompt

## Objective
8-hour product sprint: Notification urgency accuracy and fatigue prevention

## Task Draft
8-hour product sprint: Notification urgency accuracy and fatigue prevention

User Value: Overnotified users disable notifications entirely. Undernotified users miss important health signals. This task makes every notification feel timely, relevant, and worth reading.

Product Maturity Impact: Notification open rate is a direct proxy for how much users trust the platform's judgment. A high open rate means the product has earned the right to speak. Notification fatigue kills engagement silently.

Expected Change: Notification open rate rises as urgency accuracy improves. Users stop disabling notifications because each one feels relevant and timely. The daily cap prevents fatigue; snooze resurfacing prevents important signals from vanishing.

Objective: Audit notification urgency accuracy, snooze/resurfacing behavior, and implement basic fatigue prevention.

Phase 1: Audit the notification pipeline end-to-end. What triggers a notification? Is urgency (LOW/MEDIUM/HIGH) assigned correctly? Is there a daily notification cap? What happens when a user snoozes — does the notification resurface or disappear forever?
Phase 2: Audit the snooze → resurfacing flow. Implement: a snoozed notification must resurface within 24 hours unless the underlying health event is resolved. Add a resurfaced_at timestamp to the notification model.
Phase 3: Implement a daily notification cap (max 3 notifications per day per user). Prioritize HIGH urgency notifications when the cap is reached. Add the cap enforcement in backend/app/services/.
Phase 4: Run `make backend-test`. Add tests for: (a) daily cap enforcement; (b) snooze resurfacing within 24h. Verify notification-related tests pass.

Scope: backend/app/services/, backend/app/api/, backend/app/models/, backend/tests/
Files to inspect: backend/app/services/ (notification services), backend/app/api/ (notification endpoints)
Acceptance Criteria: Daily notification cap enforced; snooze resurfacing implemented; make backend-test passes; urgency assignment documented.
focus_keys: notifications, urgency, fatigue_prevention, snooze, resurfacing, cap
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
notifications, urgency, fatigue_prevention, snooze, resurfacing, cap

## Expected Duration
480 minutes (8.0h)

## Previous Context
Latest task #205 status=QUEUED objective=8-hour product sprint: Daily habit loop design and streak feedback optimization
