# Planner Task Prompt

## Objective
8-hour product sprint: Dashboard → Insights → Action flow friction reduction

## Task Draft
8-hour product sprint: Dashboard → Insights → Action flow friction reduction

User Value: New users arrive at the Dashboard and do not know what to do next. This task audits and removes every step of unnecessary friction so the "Dashboard → read an Insight → take an Action" journey takes under 60 seconds.

Product Maturity Impact: A frictionless core flow is the single biggest lever for first-week retention. Removing 3 friction points can double D7 retention.

Expected Change: Time-to-first-action drops from 3+ clicks to under 60 seconds. Empty states become guided onboarding moments instead of dead ends. D7 retention improves as fewer users abandon before taking their first action.

Objective: Audit the core user flow from Dashboard to Insights to Action completion. Identify the top 5 friction points. Fix at least 3 of them.

Phase 1: Walk through the full flow as a first-time user. Document every click, load, blank state, confusing label, and missing CTA. Use frontend/app/platform/ as your map. Rate each step: Does it move the user forward or create hesitation?
Phase 2: Inspect the Dashboard page (app/platform/dashboard/page.tsx). Is the most important health signal visible above the fold? Is there a clear next-action CTA? Are empty states helpful or discouraging?
Phase 3: Fix the top-3 friction points. Concrete examples: add a "Start here" CTA to empty Dashboard; improve Insight card CTAs to link directly to the relevant Action; reduce loading states with skeleton placeholders; clarify confusing copy.
Phase 4: Run `npm run lint` to confirm no regressions. Write a brief before/after friction audit report (what changed and why).

Scope: frontend/app/platform/dashboard/, frontend/app/platform/insights/, frontend/app/platform/actions/, frontend/components/
Files to inspect: app/platform/dashboard/page.tsx, app/platform/insights/, app/platform/actions/, components/shared/
Acceptance Criteria: At least 3 friction points fixed with evidence; Dashboard has a visible primary CTA in empty state; npm run lint passes; before/after audit documented.
focus_keys: ux_flow, dashboard, insights, friction, cta, onboarding
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
ux_flow, dashboard, insights, friction, cta, onboarding

## Expected Duration
480 minutes (8.0h)

## Previous Context
Latest task #281 status=QUEUED objective=產品問題衝刺: 補強長期未覆蓋的產品領域: behavior_loop_optimization
