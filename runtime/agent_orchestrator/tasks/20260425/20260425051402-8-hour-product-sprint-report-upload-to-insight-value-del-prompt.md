# Planner Task Prompt

## Objective
8-hour product sprint: Report upload to Insight value delivery audit

## Task Draft
8-hour product sprint: Report upload to Insight value delivery audit

User Value: A user who uploads a blood test report expects to understand what it means for their health within minutes, not days. This task audits whether that value is actually delivered and fixes the gaps.

Product Maturity Impact: The report upload flow is the moment of highest intent. If the user gets a clear, actionable insight immediately, they become a power user. If the result is generic or delayed, they churn.

Expected Change: Users who upload a report immediately see a specific insight referencing their own values, not a generic health summary. The CTA from report to first action reduces post-upload abandonment. Report upload becomes the product's highest-value moment.

Objective: Audit the report upload → parsing → insight → action pipeline for value leakage. Fix the top-3 value-delivery failures.

Phase 1: Upload a sample report (or trace the code with a mocked file). Record: How long does parsing take? Does the user see a progress indicator? Is the resulting insight specific to the report content or generic? Does the insight lead directly to a recommended action?
Phase 2: Inspect backend/app/services/ for report parsing logic. What data is extracted? What is discarded? Is there a validation step that tells the user "your report was parsed successfully, here is what we found"?
Phase 3: Fix the top-3 value gaps. Examples: add a parsing success confirmation with key extracted values; ensure insights reference specific report values (e.g. "Your LDL of 145 mg/dL..."); add a "Report processed — here is your #1 action" CTA.
Phase 4: Run `make backend-test`. Add a test that asserts the insight generated from a report references at least one extracted metric value. Document value delivery before/after.

Scope: backend/app/services/, backend/app/api/, frontend/app/platform/reports/, uploads/, ai/prompts/
Files to inspect: backend/app/services/ (parsing services), ai/prompts/health_check_interpreter_prompt.md, frontend/app/platform/reports/
Acceptance Criteria: Insight references specific report metric; parsing success confirmation shown to user; CTA from report to first action exists; make backend-test passes.
focus_keys: reports, parsing, insight_value, cta, report_to_action, specific_metrics
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
reports, parsing, insight_value, cta, report_to_action, specific_metrics

## Expected Duration
480 minutes (8.0h)

## Previous Context
Latest task #235 status=QUEUED objective=8-hour product sprint: Notification urgency accuracy and fatigue prevention
