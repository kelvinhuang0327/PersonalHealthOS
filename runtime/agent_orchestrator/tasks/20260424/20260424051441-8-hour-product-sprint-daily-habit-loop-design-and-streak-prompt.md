# Planner Task Prompt

## Objective
8-hour product sprint: Daily habit loop design and streak feedback optimization

## Task Draft
8-hour product sprint: Daily habit loop design and streak feedback optimization

User Value: Users who do not return daily forget the product exists. This task designs a daily hook that makes returning to the platform a habit, not a chore — using streaks, feedback loops, and return triggers.

Product Maturity Impact: D30 retention is the vanity-free measure of product-market fit. A well-designed habit loop (cue → routine → reward) is the primary driver of D30 retention.

Expected Change: D7 and D30 retention improve as streak milestones create emotional investment. Users who reach day-7 streak are 3× more likely to reach day 30. Milestone celebrations make progress visible and reinforce the daily return habit.

Objective: Design and implement a daily habit loop: daily check-in cue, streak tracking, and completion reward signal.

Phase 1: Audit the current streak implementation in backend/app/services/ and backend/tests/test_action_streak.py. Does the streak reset correctly at midnight? Is it surfaced prominently in the UI? Is there any reward signal when a streak milestone is hit?
Phase 2: Design the daily cue: what triggers a user to open the app each day? Sketch: a daily summary notification (Today's health snapshot), a streak reminder (Day 4 streak — don't break it!), or a fresh action recommendation (Your #1 action for today is...).
Phase 3: Implement the streak milestone reward signal in the frontend. When a user hits day 3, 7, 14, or 30, show a celebratory moment (a banner, animation, or summary card). Update the backend streak endpoint to return milestone_reached: bool alongside the count.
Phase 4: Run `make backend-test` and `npm run lint`. Add a test for streak milestone detection. Document the habit loop design with the cue/routine/reward labels.

Scope: backend/app/services/, backend/app/api/, frontend/app/platform/, frontend/components/
Files to inspect: backend/tests/test_action_streak.py, backend/app/services/ (streak-related), frontend/app/platform/
Acceptance Criteria: Streak milestone field returned by API; frontend shows milestone celebration at day 3/7/14/30; make backend-test passes; habit loop documented.
focus_keys: retention, habit_loop, streak, daily_hook, milestone, d30
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
| 信心度 | 0.89 |
| Pass Rate | 89% |
| 失敗率 | 11% |
| 近期任務數 | 19 |

> 89% gate pass rate across last 19 tasks.

## Focus Keys
retention, habit_loop, streak, daily_hook, milestone, d30

## Expected Duration
480 minutes (8.0h)

## Previous Context
Latest task #147 status=QUEUED objective=8-hour product sprint: Full user journey friction audit — Report upload to Action complete
