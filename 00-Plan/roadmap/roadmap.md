# PersonalHealthOS Roadmap

Updated: 2026-05-23
Owner: CTO review

## Product Positioning

[Confirmed] PersonalHealthOS is an AI personal health assistant. It should integrate symptoms, long-term symptom changes, health history, checkup reports, medical/lab data, daily health metrics, actions, outcomes, family context, and future device data, then provide daily trustworthy, actionable, and trackable health recommendations.

## Current Input Sources

- [Confirmed] User-provided handoff: `P13 Auth E2E + Entrypoint Hardening`.
- [Confirmed] `00-Plan/roadmap/active_task_report.md`: top P13 block reports `P13_AUTH_E2E_ENTRYPOINT_HARDENED`.
- [Confirmed] `00-Plan/roadmap/active_task.md`: prior P12 post-closure verification task, now superseded by P13 report.
- [Confirmed] Current repo path: `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS`.
- [Confirmed] Current branch: `main`.
- [Confirmed] Current working tree has existing dirty/uncommitted P13-related changes, including `.gitignore`, `Makefile`, `active_task_report.md`, `test_auth_negative_smoke.py`, `test_real_token_auth_negative.py`, and staged artifact removals.
- [Confirmed] `frontend/package.json` has Playwright support through `npm run e2e`.
- [Confirmed] `.github/workflows/ci-cd.yml` still runs backend tests with bare `PYTHONPATH=. pytest -q`.

## Latest Phase Status

### P0 - Personal Health Assistant Core Closure

Status: [Aligned] core loop completed enough for production-trust verification.

- [Confirmed] Symptom input surfaces exist: `/platform/symptoms`, quick check-in symptom entry, and `/symptoms` API.
- [Confirmed] Health Assistant Evidence Bundle exists.
- [Confirmed] Top 3 Health Recommendations exist.
- [Confirmed] Dashboard daily assistant surfaces exist.
- [Confirmed] Actions Page uses the recommendation layer before dashboard fallbacks.
- [Confirmed] External/source-tagged metrics are first-class evidence in `external_metrics`.
- [Confirmed] Recommendation trust layer exists and is shared across relevant UI.
- [Confirmed] P13 added real-token JWT auth negative/sanity tests for family context/recommendations.
- [Blocked] Browser-level login/token/session auth flow remains unverified.
- [Blocked] CI backend workflow still uses bare `pytest`, so entrypoint governance is not fully hardened in CI.

### P1 - Daily Behavior Loop And Outcome Learning

Status: [Aligned] partially completed, but browser regression remains open.

- [Confirmed] Daily Health Summary exists.
- [Confirmed] Outcome Feedback exists and avoids claiming improvement when data is insufficient.
- [Confirmed] Recommendation Trust Layer exists.
- [Missing] Browser-level regression coverage is still not run for login/auth, Daily Assistant, Trust, Outcome Feedback, and Family Health Card.
- [Missing] Real login page -> token/cookie/session -> protected API flow remains unverified.

### P2 - Device Data Readiness

Status: [Aligned] device signal intelligence exists; connector work remains paused.

- [Confirmed] Existing source-tagged metrics feed `external_metrics`.
- [Confirmed] Device signal detection exists and is surfaced in the health assistant panel.
- [Confirmed] `/health-assistant/device-signals` endpoint exists.
- [Missing] SpO2 schema/column and PostgreSQL-backed integration lane are not complete.
- [Outdated] Any roadmap item that starts Apple Health, Google Fit, or wearable connector work before browser auth/CI governance is downgraded.

### P3 - Symptom Intelligence Upgrade

Status: [Aligned] partially completed.

- [Confirmed] Symptom page, symptom API, temporal symptom parsing, symptom patterns, and symptom insight UI exist.
- [Inferred] More advanced symptom-to-reminder behavior remains future work.

### P4 - Report-To-Action Closure

Status: [Aligned] substantially implemented.

- [Confirmed] Lab abnormalities can enter recommendations and report-to-action flow.
- [Confirmed] Stale report handling and lab insight UI have been reported as verified in prior active task report sections.
- [Missing] Browser/E2E coverage for the report-to-action journey is still not proven.

### P5 - Notification And Reminder Intelligence

Status: [Outdated] keep downgraded until P0/P1 verification is complete.

- [Confirmed] Snooze/reminder data structures exist.
- [Blocked] Notification expansion should not compete with browser auth smoke and CI entrypoint hardening.

### P6 - Personalization And Learning

Status: [Aligned] future work.

Use completion history, outcome changes, snooze reasons, and preferred check-in timing after P0/P1 verification is stable.

### P7 - Narrative Memory

Status: [Aligned] partially implemented and future-expandable.

Narrative memory and cross-period reasoning appear in tests/reports, but should not take P0/P1 resources today.

### P8 - Family / Multi-Person Health Assistant

Status: [Aligned] implemented and API-auth hardened, but browser auth still missing.

- [Confirmed] Family relationships and family health context exist.
- [Confirmed] Cross-profile isolation tests exist.
- [Confirmed] P12 family permission enforcement and source granularity exist.
- [Confirmed] P13 added real-token JWT negative tests for cross-user family context/recommendations.
- [Blocked] Real browser auth flow for family context remains unverified.

### P9 - Product Analytics And Orchestrator Governance

Status: [Aligned] ongoing governance track.

- [Confirmed] P12 fixed `_open_db(profile_path=None)` so `ORCHESTRATOR_PROFILE_PATH` env fallback is respected.
- [Confirmed] P13 hardened backend test entrypoint in README/Makefile.
- [Drift] GitHub Actions backend workflow still uses bare pytest, so CI governance is incomplete.
- [Drift] Current working tree still contains uncommitted/staged P13 changes and artifact removals; roadmap should not treat the repo as clean.

### P10 - Production Trust, Compliance, And Ecosystem

Status: [Aligned] active production-trust track.

- [Confirmed] P13 reports backend regression 723/723 PASS.
- [Confirmed] P13 reports frontend TypeScript PASS.
- [Confirmed] P13 reports Next build PASS with 20 static routes.
- [Confirmed] P13 reports `backend-smoke` PASS 10/10.
- [Missing] Playwright browser JWT login flow and real browser E2E remain NOT RUN.
- [Missing] PostgreSQL-backed integration lane remains future work.

### P11/P12/P13 - Production Trust Extension Track

Status: [Aligned] P13 closure reached with remaining browser/CI risks.

- [Confirmed] P12 permission/source trust closure exists.
- [Confirmed] P12 orchestrator env/path issue was fixed.
- [Confirmed] P13 introduced `backend/tests/test_real_token_auth_negative.py` with real JWT decode path tests.
- [Confirmed] P13 confirms `get_target_person` ownership check stays production code and is not overridden.
- [Confirmed] P13 test shim only coerces SQLite UUID string to `uuid.UUID`; production app code was not changed.
- [Blocked] SQLite UUID behavior differs from PostgreSQL and still needs a PostgreSQL integration lane before stronger production claims.

## Roadmap Alignment Assessment

- [Aligned] P13 directly addresses the prior P0 auth trust gap by moving from dependency override smoke to real-token JWT tests.
- [Aligned] P13 entrypoint hardening supports roadmap governance and reduces false backend regression reports.
- [Aligned] P13 did not expand into new product features, which matches the current instruction to stabilize production trust first.
- [Drift] The previous roadmap still listed API auth E2E as an unclosed P0 blocker. It should now be narrowed to browser-level auth flow and PostgreSQL integration.
- [Drift] README/Makefile entrypoint hardening exists, but CI workflow still uses bare pytest; "CI governance complete" would be overstated.
- [Missing] Browser-level login/session E2E is not implemented/run.
- [Missing] PostgreSQL-backed auth integration is not implemented/run.
- [Outdated] Any next feature phase before browser auth smoke and CI workflow entrypoint hardening is downgraded.
- [Blocked] Production deployment readiness remains blocked by browser auth flow, CI workflow hardening, and DB parity coverage.

## Completed Items Since Prior CTO Review

- [Confirmed] P13 real-token JWT auth negative tests added.
- [Confirmed] No-token, expired-token, and garbage-token paths are covered as 401.
- [Confirmed] User A token cannot read user B family context/recommendations at API level.
- [Confirmed] Own-profile and default-profile sanity paths return 200.
- [Confirmed] `get_target_person` production ownership check remains un-overridden.
- [Confirmed] `backend-smoke` target exists in `Makefile`.
- [Confirmed] `.gitignore` contains runtime artifact rules for `frontend/tsconfig.tsbuildinfo` and launchd pid files.
- [Confirmed from active report] Backend regression: 723/723 PASS.
- [Confirmed from active report] Frontend TypeScript and Next build PASS.

## Reprioritized Roadmap

### P0 - Browser Auth Smoke + CI Entrypoint Governance

Goal: Convert API-level auth confidence into browser/session confidence and make test entrypoints consistent for agents/CI.

1. [Blocked] Browser-level auth smoke.
   - Required flow: login or token bootstrap in browser, access own protected family context, reject cross-user family context/recommendations.
   - Acceptance: Playwright/browser smoke PASS, or a precise `BROWSER_AUTH_E2E_NOT_IMPLEMENTED` report with missing fixtures listed.

2. [Blocked] CI backend entrypoint hardening.
   - Current issue: `.github/workflows/ci-cd.yml` still uses `PYTHONPATH=. pytest -q`.
   - Acceptance: CI backend test command uses the canonical venv/module entrypoint or an equivalent reproducible environment command.

3. [Blocked] PostgreSQL integration lane decision.
   - Current issue: P13 needs a SQLite UUID coercion shim, while production uses PostgreSQL.
   - Acceptance: at least one PostgreSQL-backed auth smoke exists, or the lane is explicitly planned with owner/scope.

4. [Drift] Working tree / artifact finalization.
   - Current issue: P13 changes are still dirty/untracked/staged in the current workspace.
   - Acceptance: changes are committed or explicitly reported as pending; no unrelated dirty files block the next sprint.

5. [Missing] Report archive strategy.
   - Current issue: `active_task_report.md` is prepend/append heavy and growing.
   - Acceptance: define an archive/appendix strategy without deleting historical evidence.

### P1 - Browser Regression And Trust UX

1. Playwright regression for Daily Assistant, Actions recommendations, Recommendation Trust, Outcome Feedback, and Family Health Card.
2. Unknown/missing trust fallback rendered explicitly.
3. Browser-level health assistant smoke after login.
4. Product signal reliability for completion, snooze, conversion, and recommendation acceptance.

### P2 - Device Data Readiness Without Connector Overreach

1. Provider-neutral external metrics contract for heart rate, pulse, sleep, steps, activity, and SpO2.
2. SpO2/pulse schema decision and migration planning.
3. Mock/manual import with source metadata, freshness, reliability, and source normalization.
4. No real wearable connector until P0/P1 verification is clean.

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
5. Document-to-action conversion tracking and E2E smoke.

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

Harden task/report quality gates, CI/test entrypoints, report archive strategy, and orchestrator issue prioritization.

### P10 - Production Trust, Compliance, And Ecosystem

Audit logs, privacy boundaries, health recommendation safety guardrails, auth/deployment smoke, compliance documentation, and production monitoring.

## Items To Downgrade, Merge, Pause, Or Retire

- [Retire] API-level real-token auth negative smoke as a blocker; P13 completed it.
- [Downgrade] New product feature phases until browser auth smoke and CI entrypoint governance are closed.
- [Downgrade] Real wearable connector work until P2 schema/readiness and P0/P1 verification are clean.
- [Merge] CI entrypoint hardening into P0 because false regression signals block verifiability.
- [Merge] Report archive strategy into P9 governance, with P0 urgency due active handoff size.
- [Pause] New worker task prompt generation by CTO because the current instruction explicitly forbids producing new worker prompts.

## Today Recommended Focus

[Confirmed] The next most valuable optimization is:

> Browser Auth Smoke + CI Test Governance Hardening.

Do not start a new product feature phase. P13 proved API-level JWT negative auth behavior; now prove the browser/session path and make CI use the same canonical backend entrypoint so agents and CI stop disagreeing about regression status.

## Active Task Prompt Status

[Blocked] No new worker task prompt is written by this CTO review.

Reasons:

- [Confirmed] The instruction says CTO can update only `00-Plan/roadmap/roadmap.md` and `00-Plan/roadmap/CTO-Analysis.md`.
- [Confirmed] The instruction says "嚴禁產出新的 worker task prompt."
- [Confirmed] `00-Plan/roadmap/active_task.md` already exists but is not modified by CTO in this review.
