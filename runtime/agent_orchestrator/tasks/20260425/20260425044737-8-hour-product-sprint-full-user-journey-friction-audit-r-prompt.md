# Planner Task Prompt

## Objective
8-hour product sprint: Full user journey friction audit — Report upload to Action complete

## Task Draft
8-hour product sprint: Full user journey friction audit — Report upload to Action complete

User Value: A new user who uploads a health report should be able to read an AI insight and complete their first recommended action in under 5 minutes. This task maps and fixes the biggest blockers in that journey.

Product Maturity Impact: The "time to first meaningful outcome" metric defines whether a user becomes a retained user or churns. Shortening TTFMO from 30 minutes to 5 minutes is a step-change in product maturity.

Expected Change: TTFMO drops visibly after fixing the top-3 friction points. Fewer users abandon between report upload and first action. The friction audit becomes a repeatable quarterly product-quality process.

Objective: End-to-end audit of the journey from Report Upload → AI Insight → Action completion. Find and fix the top-3 friction points.

Phase 1: Trace the full journey in the codebase and UI. Report Upload: what happens after the file is accepted? How long before an Insight appears? What if parsing fails? Insight: is the connection from insight to action explicit? Action: how many taps to mark complete? Document each step with file references.
Phase 2: Score each step on: latency (does the user wait?), clarity (does the user know what to do?), confidence (does the user trust the result?). Identify the 3 steps with the lowest scores.
Phase 3: Fix the top-3 friction steps. Examples: add a progress indicator during report parsing; add an explicit "This insight suggests → [Action]" link; reduce action completion to a single tap from the Insight card.
Phase 4: Run `npm run lint` and `make backend-test`. Document the before/after step count and estimated TTFMO improvement.

Scope: frontend/app/platform/, backend/app/api/, backend/app/services/
Files to inspect: app/platform/reports/, app/platform/insights/, app/platform/actions/, backend/app/api/ (report endpoints)
Acceptance Criteria: At least 3 friction steps fixed with evidence; before/after journey step count documented; npm run lint and make backend-test pass.
focus_keys: user_journey, friction_audit, ttfmo, onboarding, report_to_action
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
| 信心度 | 1.00 |
| Pass Rate | 100% |
| 失敗率 | 0% |
| 近期任務數 | 20 |

> 100% gate pass rate across last 20 tasks.

## Focus Keys
user_journey, friction_audit, ttfmo, onboarding, report_to_action

## Expected Duration
480 minutes (8.0h)

## Previous Context
Latest task #230 status=QUEUED objective=8-hour product sprint: Health Narrative v3 causal chain and human-readable rewrite
