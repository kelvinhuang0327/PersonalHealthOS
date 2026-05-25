# PersonalHealthOS Roadmap

Updated: 2026-05-25 (P61 refocus)
Owner: CTO review

## Product Positioning

[Confirmed] PersonalHealthOS is an AI personal health assistant. It should integrate daily symptoms, long-term symptom changes, health history, checkup reports, medical/lab data, daily health metrics, actions, outcomes, family context, and future device data, then provide daily trustworthy, actionable, and trackable health recommendations.

## Current Input Sources

- [Confirmed] User-provided handoff: `P49 Frontend Auth E2E CI Readiness`.
- [Confirmed] `00-Plan/roadmap/active_task_report.md`: top P49 block reports `P49_FRONTEND_AUTH_E2E_LOCAL_GATE_DOCUMENTED`.
- [Confirmed] `docs/security/P49_FRONTEND_AUTH_E2E_CI_READINESS.md`: documents frontend auth E2E CI readiness audit and local gate decision.
- [Confirmed] `docs/security/P48_CI_RUNTIME_SMOKE_ALIGNMENT.md`: documents CI/runtime-smoke alignment after adding frontend TypeScript CI gate.
- [Confirmed] `docs/security/P40_POSTGRESQL_PARITY_SMOKE.md`: documents one-off PostgreSQL parity smoke with 11/11 PASS.
- [Confirmed] Current repo path: `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS`.
- [Confirmed] Current branch: `main`.
- [Confirmed] Current working tree is clean at review time.
- [Confirmed] Current HEAD includes P49 commits `5776e35` and `62b791f`.
- [Outdated] `00-Plan/roadmap/active_task.md` still describes a P13 finalize/browser-auth task and does not match current P49 state.
- [Outdated] `00-Plan/roadmap/current_state.md` is an older P1 verification handoff and contains claims contradicted by the current canonical git repo state.

## Latest Phase Status

### P50–P60 Closure Summary (2026-05-25)

- [Closed] P50 — Frontend auth smoke local stability diagnosed and stabilized (commit `0191e59`).
- [Closed] P51 — Recommendation explanation safety (safe Chinese copy, no medical overclaiming).
- [Closed] P52 — Prioritized action safety (evidence-grounded, safe copy).
- [Closed] P53 — Action confidence labels (UI trust layer).
- [Closed] P54 — Daily summary context (topRisk / biggestChange / todayAction / whyNow / confidence / missingData).
- [Closed] P55 — Action feedback loop (mark done/snoozed/not_useful/not_applicable at API level).
- [Closed] P56 — Recommendation feedback persistence (commit `9624f04`).
- [Closed] P57 — Snooze persistence + dismissed filter in prioritized actions (commit `07b15d0`).
- [Closed] P58 — Recommendation outcome readiness safeguards (safe copy, confidence=0.0, actual_metric_change=null for dismissed/snoozed; commit `5dea27e`).
- [Closed] P59 — Outcome visibility verification: frontend type unions fixed, outcome-feedback-card.tsx updated, 18 API tests added (commit `4e5dd81`).
- [Closed] P60 — Outcome feedback route smoke readiness: `outcome-smoke` Makefile target added, 56 tests now in `make runtime-smoke` (commit `6ea326b`).

### P0 - Personal Health Assistant Core Closure

Status: [Aligned] Core recommendation / feedback / outcome chain now closed end-to-end.

- [Confirmed] Symptom input surfaces exist: `/platform/symptoms`, quick check-in symptom entry, and `/symptoms` API.
- [Confirmed] Health Assistant Evidence Bundle exists.
- [Confirmed] Top 3 Health Recommendations exist.
- [Confirmed] Dashboard daily assistant surfaces exist.
- [Confirmed] Actions Page uses the recommendation layer before dashboard fallbacks.
- [Confirmed] Recommendation trust layer exists and is shared across relevant UI.
- [Confirmed] Backend auth/security coverage is now included in `backend-auth-audit` and propagates through `runtime-smoke`.
- [Confirmed] `make frontend-auth-smoke` stabilized (P50): requires `npm run build` before running.
- [Confirmed] P51–P53 added safe copy and confidence labels to recommendations.
- [Confirmed] P54 hardened daily summary with topRisk / biggestChange / todayAction / whyNow / confidence / missingData.
- [Confirmed] P55–P57 closed the action feedback + snooze persistence loop.
- [Confirmed] P58–P59 closed the safe outcome visibility loop (no overclaiming, dismissed/snoozed surfaced in UI).
- [Confirmed] P60 added `outcome-smoke` to `make runtime-smoke` (56 service+API tests).
- [Missing] Recommendation feedback timeline/history view: users cannot see a chronological record of past recommendations with user responses and outcomes.

### P1 - Daily Behavior Loop And Outcome Learning

Status: [Partially complete] Recommendation → feedback → outcome chain is closed. History/timeline view is the next product slice.

- [Confirmed] Daily Health Summary exists with all required fields.
- [Confirmed] Outcome Feedback exists and avoids claiming improvement when data is insufficient.
- [Confirmed] Recommendation Trust Layer exists.
- [Confirmed] P48 added frontend TypeScript CI coverage, reducing UI regression risk.
- [Confirmed] Action feedback (mark done/snoozed/dismissed) persists at API level (P55-P57).
- [Confirmed] Outcome feedback card renders safe outcome statuses (P59).
- [Missing] A simple chronological recommendation history: recommended action → user response → safe outcome status.
- [Next] P62 should add a recommendation feedback timeline view using existing backend data.

### P2 - Device Data Readiness

Status: [Aligned] important, but not today's blocker.

- [Confirmed] Symptom input surfaces exist: `/platform/symptoms`, quick check-in symptom entry, and `/symptoms` API.
- [Confirmed] Health Assistant Evidence Bundle exists.
- [Confirmed] Top 3 Health Recommendations exist.
- [Confirmed] Dashboard daily assistant surfaces exist.
- [Confirmed] Actions Page uses the recommendation layer before dashboard fallbacks.
- [Confirmed] Recommendation trust layer exists and is shared across relevant UI.
- [Confirmed] Backend auth/security coverage is now included in `backend-auth-audit` and propagates through `runtime-smoke`.
- [Blocked] `make frontend-auth-smoke` fails locally with Playwright webServer 120s timeout, so browser auth smoke is not a reliable local gate.
- [Blocked] `active_task.md` is stale at P13 and can mislead the next Planner/Worker if used as the current source of truth.

### P1 - Daily Behavior Loop And Outcome Learning

Status: [Aligned] partially complete; product work should resume after the P50 local gate diagnosis is bounded.

- [Confirmed] Daily Health Summary exists.
- [Confirmed] Outcome Feedback exists and avoids claiming improvement when data is insufficient.
- [Confirmed] Recommendation Trust Layer exists.
- [Confirmed] P48 added frontend TypeScript CI coverage, reducing UI regression risk.
- [Missing] Browser-level regression coverage for Daily Assistant, Actions, Trust, Outcome Feedback, and Family Health Card is still limited to mocked CI E2E plus local/manual flows.
- [Inferred] Product value work should focus on making the daily assistant more useful with existing data, not on expanding device connectors.

### P2 - Device Data Readiness

Status: [Aligned] important, but not today's blocker.

- [Confirmed] Existing source-tagged metrics feed `external_metrics`.
- [Confirmed] Device signal detection exists and is surfaced in the health assistant panel.
- [Confirmed] `/health-assistant/device-signals` endpoint exists.
- [Missing] SpO2/pulse schema and stable provider-neutral import policy remain future work.
- [Outdated] Apple Health, Google Fit, or real wearable connector work remains downgraded until core recommendation and gate reliability are stable.

### P3 - Symptom Intelligence Upgrade

Status: [Aligned] partially implemented and future-expandable.

- [Confirmed] Symptom page, symptom API, temporal symptom parsing, symptom patterns, and symptom insight UI exist.
- [Inferred] More advanced symptom-to-reminder behavior remains future work.

### P4 - Report-To-Action Closure

Status: [Aligned] substantially implemented and security-hardened.

- [Confirmed] Lab abnormalities can enter recommendations and report-to-action flow.
- [Confirmed] Report download token policy was audited in P44 and hardened in P45.
- [Confirmed] P47 added report download token policy tests to `backend-auth-audit`, bringing them into `runtime-smoke`.
- [Missing] Browser/E2E coverage for the complete report-to-action journey is still not proven as a stable gate.

### P5 - Notification And Reminder Intelligence

Status: [Outdated] keep downgraded until P0/P1 verification is stable.

- [Confirmed] Snooze/reminder data structures exist.
- [Blocked] Notification expansion should not compete with local auth smoke stability and core daily assistant usefulness.

### P6 - Personalization And Learning

Status: [Aligned] future work.

Use completion history, outcome changes, snooze reasons, and preferred check-in timing after P0/P1 verification is stable.

### P7 - Narrative Memory

Status: [Aligned] partially implemented and future-expandable.

Narrative memory and cross-period reasoning appear in tests/reports, but should not take P0/P1 resources today.

### P8 - Family / Multi-Person Health Assistant

Status: [Aligned] backend/API trust hardened; frontend auth UI gate remains local-only and currently unstable.

- [Confirmed] Family relationships and family health context exist.
- [Confirmed] P12 family permission enforcement and source granularity exist.
- [Confirmed] P13 real-token JWT negative tests cover cross-user family context/recommendations at API level.
- [Confirmed] P49 concludes auth contract logic is meaningfully covered by backend CI/auth audit.
- [Blocked] Full browser auth UI flow is not a reliable gate because `frontend-auth-smoke` fails locally.

### P9 - Product Analytics And Orchestrator Governance

Status: [Aligned] active governance track.

- [Confirmed] P48 aligned CI with runtime-smoke for frontend TypeScript.
- [Confirmed] CI backend uses `PYTHONPATH=. python -m pytest -q`, not bare `pytest`.
- [Confirmed] CI frontend runs `npm run e2e:ci`, limited to three mocked specs with no live backend dependency.
- [Confirmed] P49 documents frontend auth E2E as local/manual, not CI.
- [Drift] `active_task.md` is stale and does not reflect P49/P50.
- [Missing] `active_task_report.md` archive/lifecycle policy remains undefined.

### P10 - Production Trust, Compliance, And Ecosystem

Status: [Aligned] production-trust track has progressed; remaining gaps are local frontend-auth smoke stability, live-service E2E design, and periodic DB parity.

- [Confirmed] P47 runtime-smoke: 130 passed, 2 skipped.
- [Confirmed] P48 reports CI backend full suite: 983 passed, 2 skipped.
- [Confirmed] P48 reports CI frontend TypeScript gate added.
- [Confirmed] P49 reports `make runtime-smoke`: 130 passed, 2 skipped.
- [Confirmed] P49 reports `make frontend-auth-smoke`: FAIL due Playwright webServer 120s timeout.
- [Confirmed] P40 PostgreSQL parity smoke exists with 11/11 PASS.
- [Missing] PostgreSQL parity is not part of `runtime-smoke` or CI.

### P40-P49 - Production Trust Extension Track

Status: [Aligned] most backend/security gates are closed or accepted; frontend auth E2E CI is explicitly deferred.

- [Confirmed] P40 verified PostgreSQL parity for UUID, TIMESTAMPTZ, JSONB, and FK cascade at one-off smoke level.
- [Confirmed] P41 hardened risk-engine UUID hygiene after P40.
- [Confirmed] P44/P45 audited and hardened report download token policy.
- [Confirmed] P47 added report download token policy tests to `backend-auth-audit` and `runtime-smoke`.
- [Confirmed] P48 added `npx tsc --noEmit` to CI frontend job.
- [Confirmed] P49 documented `frontend-auth-smoke` as local/manual gate and rejected direct CI inclusion.
- [Blocked] P50-level work is needed to diagnose local `frontend-auth-smoke` stability before reconsidering CI.

## Roadmap Alignment Assessment

- [Aligned] P49 follows roadmap priority by auditing verification gates before adding CI complexity.
- [Aligned] The choice not to add `frontend-auth-smoke` to CI is consistent with production-trust governance because local failure proves CI would be flaky.
- [Aligned] Backend security/auth coverage is now stronger than the P13 roadmap state: `backend-auth-audit`, `runtime-smoke`, and CI full backend suite cover the core authorization logic.
- [Drift] The prior roadmap's P0 "CI backend bare pytest" blocker is now outdated; CI backend uses `python -m pytest`.
- [Drift] The prior roadmap's broad "browser auth smoke + CI hardening" should be narrowed to "local frontend-auth-smoke stability diagnosis"; direct CI inclusion is paused.
- [Missing] Roadmap had not yet recorded P48/P49 decisions.
- [Missing] `active_task.md` still points to P13 and is not aligned with the current P49/P50 decision state.
- [Outdated] Treating frontend auth E2E CI inclusion as the next default step is no longer valid after P49.
- [Blocked] System maturity is blocked by an unstable local browser auth gate and stale task-source governance, not by backend auth contract coverage.

## Completed Items Since Prior CTO Review

- [Confirmed] P40 PostgreSQL parity smoke documented 11/11 PASS.
- [Confirmed] P41 risk-engine UUID hygiene was completed after P40.
- [Confirmed] P44/P45 report download token risk was audited and hardened.
- [Confirmed] P47 moved token policy tests into `backend-auth-audit` and `runtime-smoke`.
- [Confirmed] P48 added frontend TypeScript check to CI and aligned CI/runtime-smoke coverage.
- [Confirmed] P49 audited frontend auth E2E CI readiness.
- [Confirmed] P49 executed `make frontend-auth-smoke` and found local webServer 120s timeout.
- [Confirmed] P49 executed `make runtime-smoke` with 130 passed, 2 skipped.
- [Confirmed] P49 created `docs/security/P49_FRONTEND_AUTH_E2E_CI_READINESS.md`.
- [Confirmed] P49 committed `5776e35` and `62b791f`.

## Reprioritized Roadmap

### P0 - Frontend Auth Local Gate Stability And Governance Alignment

Goal: make the remaining browser auth gate diagnosable and keep agents from using stale task sources.

1. [Blocked] Diagnose `make frontend-auth-smoke` local failure.
   - Current issue: Playwright webServer times out after 120s while starting `next start` at `127.0.0.1:3010`.
   - Acceptance: `make frontend-auth-smoke` becomes a reliable local PASS, or a root-cause blocker report identifies the exact failing prerequisite.

2. [Blocked] Keep frontend auth E2E out of CI until local gate is stable.
   - Current issue: CI would require live backend, env, database, fresh Next build, `next start`, ports, and CORS bridge.
   - Acceptance: CI continues to run mocked E2E plus backend auth/security gates; no direct auth E2E CI addition before local stability.

3. [Blocked] Align current task-source governance.
   - Current issue: `active_task.md` is stale at P13 while active reports and HEAD are at P49.
   - Acceptance: CEO/Planner-owned active task source is updated outside this CTO-only review, or explicitly ignored in favor of the P49 handoff.

4. [Missing] Define report lifecycle/archive policy.
   - Current issue: `active_task_report.md` is long and prepend-heavy.
   - Acceptance: active top block remains concise while historical reports are clearly archived or indexed without deleting evidence.

### P1 - Product Core Resume Gate

1. Resume daily assistant product-value work only after P50 local-gate diagnosis is bounded.
2. Improve user-facing daily assistant usefulness with existing data: today's risk, biggest change, next action, and data-insufficiency clarity.
3. Add stable browser regression coverage for Daily Assistant, Actions, Trust, Outcome Feedback, and Family Health Card without requiring live backend orchestration.
4. Strengthen product signals for completion, snooze, conversion, recommendation acceptance, and outcome feedback.

### P2 - Periodic Production-Parity And Device Readiness

1. Convert P40 PostgreSQL parity evidence into a periodic/local smoke lane if cost is acceptable.
2. Keep PostgreSQL parity out of P0 unless release claims require DB-level proof.
3. Define provider-neutral external metrics contract for heart rate, pulse, sleep, steps, activity, and SpO2.
4. Keep real wearable connectors paused until schema, source quality, and core recommendation usefulness are stable.

### P3 - Symptom Intelligence Upgrade

1. Symptom timeline.
2. Severity trend.
3. Pattern detection.
4. Symptom-to-recommendation.
5. Symptom-to-reminder.

### P4 - Report-To-Action Closure

1. Report parsing and lab normalization.
2. Risk mapping.
3. Report-to-decision item.
4. Report-to-action recommendation.
5. Browser smoke for report-to-action journey after gate reliability improves.

### P5 - Notification And Reminder Intelligence

1. Notification priority.
2. Snooze learning.
3. Reminder timing.
4. Risk escalation.
5. Daily check-in notifications.

### P6 - Personalization And Learning

Learn from completion history, outcome changes, snooze reasons, and preferred check-in timing.

### P7 - Narrative Memory

Persist narrative history and compare current state to unresolved prior health themes.

### P8 - Family / Multi-Person Health Assistant

Maintain family context, permission clarity, source badges, cross-profile isolation, and caregiver/member boundaries.

### P9 - Product Analytics And Orchestrator Governance

Harden task/report quality gates, CI/test entrypoints, report archive strategy, smoke target clarity, and orchestrator issue prioritization.

### P10 - Production Trust, Compliance, And Ecosystem

Audit logs, privacy boundaries, health recommendation safety guardrails, auth/deployment smoke, periodic DB parity, compliance documentation, and production monitoring.

## Items To Downgrade, Merge, Pause, Or Retire

- [Retire] CI backend bare-pytest blocker; current CI uses `python -m pytest`.
- [Retire] API-level real-token auth negative smoke as a blocker; backend auth coverage is now gated through CI/backend-auth-audit.
- [Downgrade] Direct frontend auth E2E CI inclusion; P49 proves it is not safe until local gate stability is fixed.
- [Downgrade] PostgreSQL parity from P0 blocker to P2/periodic gate, because P40 one-off parity exists but it is not part of CI/runtime-smoke.
- [Downgrade] Notification intelligence and real wearable connectors until P0/P1 verification and product core usefulness are stable.
- [Merge] P47/P48/P49 smoke/CI governance into P9/P10.
- [Pause] Full frontend E2E CI redesign until local `frontend-auth-smoke` is stable and service orchestration is specified.
- [Pause] New worker task prompt generation by CTO because the current instruction explicitly forbids producing new worker prompts.

## Today Recommended Focus

[Confirmed] The next most valuable optimization is:

> P50 - Frontend Auth Smoke Local Stability Diagnosis.

Do not add frontend auth E2E to CI today. First determine why local `make frontend-auth-smoke` times out, and either stabilize it or produce a precise blocker report. In parallel, treat `active_task.md` as stale until CEO/Planner refreshes it outside this CTO-only review.

## Active Task Prompt Status

[Blocked] No new worker task prompt is written or emitted by this CTO review.

Reason:

- [Confirmed] The instruction says CTO can update only `00-Plan/roadmap/roadmap.md` and `00-Plan/roadmap/CTO-Analysis.md`.
- [Confirmed] The instruction explicitly says "嚴禁產出新的 worker task prompt."
