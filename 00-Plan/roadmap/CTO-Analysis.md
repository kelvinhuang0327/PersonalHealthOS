# CTO Roadmap Alignment And System Optimization Analysis

## 1. CTO Review Date

2026-05-23 Asia/Taipei

## 2. Input Sources

- [Confirmed] User-provided handoff: `P13 Auth E2E + Entrypoint Hardening`.
- [Confirmed] `00-Plan/roadmap/roadmap.md`: prior CTO roadmap.
- [Confirmed] `00-Plan/roadmap/active_task.md`: prior P12 post-closure verification task.
- [Confirmed] `00-Plan/roadmap/active_task_report.md`: top P13 report block and P12 appendix.
- [Confirmed] Git repo state: canonical repo path `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS`, branch `main`.
- [Confirmed] Current `git status --short`: P13-related dirty/untracked/staged files remain in the workspace.
- [Confirmed] `backend/tests/test_real_token_auth_negative.py`: real-token JWT auth negative/sanity tests.
- [Confirmed] `backend/tests/test_auth_negative_smoke.py`: P12 override-style auth negative smoke.
- [Confirmed] `Makefile`: `backend-smoke` target exists.
- [Confirmed] `backend/README.md`: canonical venv pytest guidance exists.
- [Confirmed] `.github/workflows/ci-cd.yml`: backend CI still runs bare `PYTHONPATH=. pytest -q`.
- [Confirmed] `frontend/package.json`: Playwright is available through `npm run e2e`.
- [Unknown] CTO did not rerun backend, frontend build, Playwright, or smoke tests during this analysis.

## 3. Roadmap Alignment Assessment

- [Aligned] P13 work matches the prior P0 direction: close auth trust gaps and harden test entrypoints before new product work.
- [Aligned] P13 real-token tests are a meaningful upgrade over dependency-override-only auth smoke.
- [Aligned] Keeping `get_target_person` un-overridden preserves the production ownership enforcement path in tests.
- [Aligned] Not changing production `get_current_user` for SQLite-only UUID behavior is appropriately conservative.
- [Drift] The previous roadmap still treated API auth E2E as broadly open; it should now be narrowed to browser/session auth and PostgreSQL parity.
- [Drift] Entry-point hardening is only partially complete: README/Makefile are aligned, but GitHub Actions still uses bare pytest.
- [Missing] Browser login -> token/cookie/session -> protected API flow is still NOT RUN.
- [Missing] PostgreSQL-backed auth integration lane is not present; SQLite UUID shim remains a test-environment compromise.
- [Outdated] Starting notification intelligence, wearable connectors, or another product feature phase before browser auth/CI governance is premature.
- [Blocked] Production readiness is still blocked by browser-level auth smoke, CI entrypoint hardening, and DB parity verification, not by API-level JWT tests.

## 4. Completed Work Assessment

| Work item | Assessment |
| --- | --- |
| Real-token JWT auth negative tests | [Confirmed] `test_real_token_auth_negative.py` exists with 7 tests. |
| No/expired/garbage token rejection | [Confirmed] Covered as 401 cases. |
| Cross-user family context isolation | [Confirmed] User A token against user B person returns 404 at API level. |
| Cross-user family recommendations isolation | [Confirmed] Covered as 404 at API level. |
| Own/default person sanity | [Confirmed] Covered as 200 cases. |
| Production ownership dependency | [Confirmed] `get_target_person` is not overridden in P13 real-token tests. |
| SQLite UUID coercion | [Confirmed] Test-local shim only; production app code unchanged. |
| Backend regression | [Confirmed from active report] 723/723 PASS. |
| Frontend TypeScript | [Confirmed from active report] PASS. |
| Frontend Next build | [Confirmed from active report] PASS, 20 static routes. |
| Backend smoke target | [Confirmed] `backend-smoke` target exists and active report says 10/10 PASS. |
| Runtime artifact ignore rules | [Confirmed] `.gitignore` includes tsbuildinfo and launchd pid artifacts. |

## 5. Unfinished Work Assessment

| Work item | Assessment |
| --- | --- |
| Browser-level auth E2E | [Blocked] Playwright exists, but real browser JWT/login flow is NOT RUN. |
| Real login page/session/cookie/refresh flow | [Missing] API token tests do not cover browser session behavior. |
| PostgreSQL integration lane | [Missing] SQLite UUID shim means DB parity remains unproven. |
| CI workflow test entrypoint | [Drift] `.github/workflows/ci-cd.yml` still uses bare `pytest -q`. |
| P13 changes finalization | [Drift] Current working tree has dirty/untracked/staged P13 changes. |
| Report archive strategy | [Missing] `active_task_report.md` continues prepend/append growth; appendix exists but long-term strategy is not defined. |
| New worker task prompt | [Blocked] Current CTO instruction forbids producing one. |

## 6. P0 / P1 / P2 / P3-P10 Reprioritization

### P0

1. [Blocked] Browser-level auth smoke.
   - Upgrade reason: API-level JWT tests do not prove browser login/token/session behavior.

2. [Blocked] CI backend entrypoint hardening.
   - Upgrade reason: `.github/workflows/ci-cd.yml` can still produce false regression signals by using bare pytest.

3. [Missing] PostgreSQL auth integration lane.
   - Upgrade reason: current real-token tests require SQLite UUID coercion shim; production DB parity remains unverified.

4. [Drift] P13 change finalization / clean working tree.
   - Upgrade reason: P13 outputs are dirty/untracked/staged and should be committed or explicitly handed off before further work.

5. [Missing] Active report archive strategy.
   - Upgrade reason: handoff report is now coherent at top, but long-term prepend/append growth remains a governance risk.

### P1

1. Playwright regression for Daily Assistant, Actions, Trust, Outcome Feedback, and Family Health Card.
2. Unknown/missing trust fallback UI and regression coverage.
3. Browser-level health assistant smoke after login.
4. Product signal reliability for completion, snooze, conversion, and recommendation acceptance.

### P2

1. Provider-neutral device schema for heart rate, pulse, sleep, steps, activity, and SpO2.
2. SpO2/pulse migration planning.
3. Mock/manual import reliability and source normalization.
4. Keep real wearable connectors paused.

### P3-P10

- P3 Symptom intelligence: timeline, trend, pattern, recommendation, reminder.
- P4 Report-to-action: conversion tracking and E2E smoke.
- P5 Notification intelligence: downgraded until P0/P1 verified.
- P6 Personalization and learning: future iteration.
- P7 Narrative memory: future iteration.
- P8 Family/multi-person assistant: maintain and harden permission/isolation boundaries.
- P9 Product analytics and orchestrator governance: CI/test entrypoints, report archive strategy, gate quality.
- P10 Production trust/compliance: auth, DB parity, deployment smoke, audit, privacy, monitoring.

### Upgrades, Downgrades, Merges, Pauses

- [Upgrade to P0] Browser auth smoke.
- [Upgrade to P0] GitHub Actions backend entrypoint hardening.
- [Upgrade to P0] PostgreSQL auth smoke planning/lane.
- [Retire] API-level real-token auth negative test as blocker; P13 completed it.
- [Downgrade] Notification intelligence and real wearable connectors until P0/P1 verification is clean.
- [Merge] CI entrypoint governance into P0 and P9.
- [Pause] CTO-generated worker prompt due explicit instruction conflict.

## 7. Critical Blockers

### Blocker 1 - Browser Auth Flow Unverified

- Impact scope: login/session behavior, protected health assistant/family pages, browser auth storage.
- Why blocker: [Confirmed] P13 tests real JWT at API/TestClient level, but [Missing] Playwright/browser login flow is not run.
- Risk if untreated: API tests pass while browser token storage, login redirects, cookie/session handling, or protected API calls fail.
- Priority: P0.
- Acceptance standard: browser smoke demonstrates login or token bootstrap, own protected context access, and cross-user protected context rejection; otherwise produce explicit `BROWSER_AUTH_E2E_NOT_IMPLEMENTED` with missing fixtures.

### Blocker 2 - CI Backend Entrypoint Still Uses Bare Pytest

- Impact scope: CI reliability, agent regression interpretation, release gates.
- Why blocker: [Confirmed] README/Makefile use `.venv`, but `.github/workflows/ci-cd.yml` still runs `PYTHONPATH=. pytest -q`.
- Risk if untreated: CI/agents can still hit dependency/collection errors and misclassify backend health.
- Priority: P0.
- Acceptance standard: CI backend test step uses canonical `.venv/bin/python -m pytest` or an equivalent reproducible environment command, and `backend-smoke` is documented/runnable.

### Blocker 3 - SQLite/PostgreSQL Auth Parity Gap

- Impact scope: auth tests, UUID handling, production DB confidence.
- Why blocker: [Confirmed] P13 needs a SQLite-only UUID coercion shim; [Unknown] PostgreSQL integration smoke is absent.
- Risk if untreated: SQLite-only behavior may hide or invent UUID/auth issues relative to production.
- Priority: P0/P2 boundary; P0 if claiming production readiness.
- Acceptance standard: at least one PostgreSQL-backed auth smoke validates real JWT subject handling and cross-user rejection, or a scoped plan is accepted.

### Blocker 4 - P13 Working Tree Not Finalized

- Impact scope: branch governance, next sprint safety, reviewability.
- Why blocker: [Confirmed] P13 changes remain dirty/untracked/staged in current workspace.
- Risk if untreated: next agents may overwrite, duplicate, or misclassify pending P13 changes.
- Priority: P0 governance.
- Acceptance standard: P13 changes are committed, or a handoff explicitly lists pending files and expected owner.

### Blocker 5 - Report Growth / Archive Strategy

- Impact scope: roadmap governance, handoff readability, context load.
- Why blocker: [Confirmed] `active_task_report.md` is prepend/append based and already large.
- Risk if untreated: future agents may miss the active section or over-read stale appendix content.
- Priority: P1/P9; P0-adjacent for handoff reliability.
- Acceptance standard: current report keeps top active section, while older reports move to a clear archive strategy without deleting evidence.

## 8. Recommended System Optimization Directions

### Direction 1 - Browser Auth Smoke

- Roadmap phase: P0 / P10.
- Why important: closest remaining auth path to production user behavior.
- Maturity push: moves from API-level trust to browser/session trust.
- Expected benefit: catches login, token persistence, protected-route, and cross-user browser failures.
- Risk: Playwright fixtures may need careful minimal setup; avoid building a large framework.
- Acceptance: browser login/token bootstrap -> own family context allowed -> cross-user context rejected.
- Priority: P0.

### Direction 2 - CI Test Entrypoint Governance

- Roadmap phase: P0 / P9.
- Why important: backend health must be evaluated through one canonical entrypoint.
- Maturity push: prevents false regression reports from missing dependencies or wrong Python environment.
- Expected benefit: CI and agents agree on backend status.
- Risk: CI environment differs from local venv assumptions; use reproducible setup.
- Acceptance: `.github/workflows/ci-cd.yml`, README, Makefile, and smoke target are aligned.
- Priority: P0.

### Direction 3 - PostgreSQL Auth Parity Lane

- Roadmap phase: P0/P2/P10.
- Why important: SQLite UUID shim is a known test/prod difference.
- Maturity push: validates production DB behavior for JWT subject and ownership checks.
- Expected benefit: lower false-positive/false-negative auth risk.
- Risk: local DB setup may increase task cost; keep to one smoke first.
- Acceptance: one PostgreSQL-backed auth smoke or an explicit, owner-scoped lane plan.
- Priority: P0 if release-bound, otherwise P2.

### Direction 4 - Handoff Report Lifecycle Governance

- Roadmap phase: P1/P9.
- Why important: reports are now long and appendix-heavy.
- Maturity push: preserves evidence while keeping active state readable.
- Expected benefit: less agent confusion and lower context overhead.
- Risk: over-cleaning can destroy useful history; archive, do not delete.
- Acceptance: active report top section remains current; older sections are linked/archived with clear boundaries.
- Priority: P1.

### Direction 5 - Product Work Resume Gate

- Roadmap phase: P1/P3+.
- Why important: product work should resume only after trust gates are stable.
- Maturity push: keeps feature velocity from outrunning safety/verifiability.
- Expected benefit: safer return to symptom/report/notification/product loops.
- Risk: too much governance can stall user value; keep gates minimal.
- Acceptance: browser auth + CI entrypoint + pending P13 changes finalized.
- Priority: P1.

## 9. Roadmap Changes Applied

- [Confirmed] Updated `roadmap.md` to 2026-05-23 P13 state.
- [Confirmed] Marked API-level real-token auth negative testing as completed.
- [Confirmed] Replaced prior P0 auth blocker with browser auth smoke and DB parity blockers.
- [Confirmed] Added CI workflow entrypoint gap as P0.
- [Confirmed] Added PostgreSQL auth parity lane to P0/P2 boundary.
- [Confirmed] Marked P13 working tree finalization as governance blocker.
- [Confirmed] Kept notification intelligence and real wearable connectors downgraded.
- [Confirmed] Did not write `CEO-Decision.md`, `active_task.md`, `active_task_report.md`, production, registry, data, or any new repo.

## 10. Risks / Unknowns

- [Confirmed] Current working tree has P13-related dirty/untracked/staged files.
- [Confirmed] `.github/workflows/ci-cd.yml` still uses bare pytest.
- [Confirmed] Playwright/browser auth flow is NOT RUN.
- [Confirmed] PostgreSQL auth integration is not present.
- [Confirmed] P13 uses SQLite UUID coercion shim in test-local dependency.
- [Unknown] CTO did not independently rerun 723 backend tests, `tsc`, `next build`, or `backend-smoke`.
- [Unknown] Whether current uncommitted P13 changes are intended to be committed as one batch or handed off.
- [Inferred] P13 materially improves API-level auth trust, but is still not browser/production DB proof.
- [Confirmed] New worker prompt generation is prohibited by this CTO instruction set.

## 11. CTO Final Recommendation

Do not start a new product feature phase today. P13 closed the API-level auth gap well enough to retire it as a blocker. The next highest-value system optimization is to close the remaining production-trust gap: browser-level auth smoke, GitHub Actions backend entrypoint alignment, and a PostgreSQL auth parity lane or explicit plan. Finalize the current dirty P13 working tree before any new feature work.

## 12. CTO Summary In 10 Lines

1. [Confirmed] P13 added 7 real-token JWT auth tests.
2. [Confirmed] Cross-user family context/recommendation access is rejected at API level.
3. [Confirmed] `get_target_person` production ownership check remains un-overridden.
4. [Confirmed] Backend 723/723 PASS is reported in `active_task_report.md`.
5. [Confirmed] TypeScript, Next build, and `backend-smoke` PASS are reported.
6. [Drift] GitHub Actions still uses bare pytest.
7. [Missing] Browser login/token/session auth flow is not run.
8. [Missing] PostgreSQL auth integration lane is absent.
9. [P0] Next focus: browser auth smoke + CI entrypoint governance.
10. [Blocked] No new worker task prompt is emitted because CTO is forbidden to generate one.

## Active Task Prompt Decision

[Blocked] No "今日第一個可直接交給 Planner / Worker 執行的任務 prompt" is produced or written by this CTO review.

Reason:

- [Confirmed] The instruction says CTO can update only `00-Plan/roadmap/roadmap.md` and `00-Plan/roadmap/CTO-Analysis.md`.
- [Confirmed] The instruction explicitly says "嚴禁產出新的 worker task prompt."
- [Confirmed] `00-Plan/roadmap/active_task.md` already exists but is not modified.

Final classification for this analysis: `CTO_ROADMAP_UPDATED_WITH_RISKS`
