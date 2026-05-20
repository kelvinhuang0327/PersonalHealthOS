# PersonalHealthOS Roadmap

Updated: 2026-05-20
Owner: CTO review

## Product Positioning

[Confirmed] PersonalHealthOS is an AI personal health assistant. It must integrate symptoms, long-term symptom changes, health history, checkup reports, medical/lab data, daily health metrics, actions, outcomes, and future device data, then provide daily trustworthy, actionable, and trackable health recommendations.

## Input Sources

- [Confirmed] Historical roadmap source: `docs/NEXT_STAGE_ROADMAP.md` (updated 2026-05-19).
- [Confirmed] Current handoff source: `00-Plan/roadmap/current_state.md`.
- [Confirmed] Current code and tests: `backend/app/services/health_assistant_service.py`, `backend/app/api/health_assistant.py`, `frontend/app/platform/dashboard/page.tsx`, `frontend/app/platform/actions/page.tsx`, related tests.
- [Confirmed] Runtime/orchestrator state: `runtime/agent_orchestrator/orchestrator.db`, `runtime/agent_orchestrator/tasks/`, `runtime/agent_orchestrator/cto_reports/`.
- [Confirmed] `00-Plan/roadmap/roadmap.md` did not exist before this review; this file consolidates the roadmap without creating any new repo.

## Latest Phase Status

### Phase 0 - Personal Health Assistant Core Loop

Status: [Aligned] mostly implemented, but [Blocked] by verification and governance gaps.

- [Confirmed] Health Assistant Evidence Bundle service/API exists at `/health-assistant/evidence-bundle`.
- [Confirmed] Top 3 health recommendations exist at `/health-assistant/recommendations`.
- [Confirmed] Dashboard contains `DailyAssistantEntry` and `HealthAssistantPanel` for daily assistant surfaces.
- [Confirmed] Actions Page uses the health-assistant recommendation source before dashboard fallbacks.
- [Confirmed] Recommendation trust calculation exists in backend and shared trust UI exists in frontend.
- [Confirmed] Daily summary and outcome feedback APIs exist.
- [Drift] The evidence bundle currently returns `external_metrics: []`; source-tagged external metrics are stored through health metrics but are not a first-class evidence group.
- [Blocked] Runtime API/browser validation, Docker integration, production smoke, and Playwright trust UI tests were not run in the handoff.
- [Blocked] Workspace has no git repository/change-control baseline, while CTO is prohibited from creating a new repo.
- [Blocked] Orchestrator gates have accepted placeholder/no-change tasks as PASS, reducing trust in runtime maturity signals.

### Phase 1 - Daily Behavior Loop and Trust

Status: [Aligned] partially complete; remaining work is verification and learning-loop depth.

- [Confirmed] Daily Health Summary exists.
- [Confirmed] Outcome Feedback exists and explicitly represents insufficient data.
- [Confirmed] Recommendation Trust Layer exists and is backend-driven.
- [Missing] Browser-level regression coverage for Dashboard/Actions trust UI is not present.
- [Missing] Unknown/missing trust fallback behavior is not fully productized.
- [Inferred] 7/14/30-day behavior learning is started, but not yet proven as a closed daily retention loop.

### Phase 2 - External Device Data Readiness

Status: [Drift] partially started but should remain behind P0/P1 closure.

- [Confirmed] Existing health metrics support heart rate, sleep, steps, blood pressure, blood glucose, weight, and source tags.
- [Confirmed] External metrics are mock/manual sync only.
- [Missing] Pulse, SpO2, activity-session metadata, provider-neutral import contract, freshness scoring, and reliability scoring are not first-class.
- [Outdated] Any roadmap item that prioritizes real wearable connector work before the evidence contract is stable is downgraded.

### Phase 3 - Symptom Intelligence Upgrade

Status: [Aligned] keep as medium-term direction.

- [Confirmed] Temporal symptom fields and tests exist.
- [Inferred] Long-term symptoms are included in the evidence bundle.
- [Missing] Full symptom pattern detection and symptom-to-reminder flow remain future work.

### Phase 4 - Report-to-Action Closure

Status: [Aligned] important, but not ahead of P0/P1 verification.

- [Confirmed] Lab report items can feed recommendations.
- [Missing] Report detail UX for one-click action adoption is not proven.
- [Inferred] Report-to-action conversion should be tracked by product signals before broad UX expansion.

### Phase 5 - Notification and Reminder Intelligence

Status: [Outdated] downgraded until P0/P1 loops are verified.

- [Confirmed] Snooze/reminder fields exist.
- [Blocked] Notification optimization should not proceed before recommendation trust, action suppression, and outcome feedback are runtime-verified.

### Phase 6 - Personalization and Learning

Status: [Aligned] future work.

Keep after outcome feedback and product signal quality are stable.

### Phase 7 - Narrative Memory

Status: [Aligned] future work.

Keep after daily recommendation evidence and outcome tracking are reliable.

### Phase 8 - Family / Multi-Person Health Assistant

Status: [Aligned] future work.

Person-scoped data exists, but family expansion should not consume P0/P1 resources.

### Phase 9 - Product Analytics to Orchestrator

Status: [Drift] split into two tracks.

- [P0 merge] Quality gate credibility, anti-shallow delivery checks, and repeated problem-signal cooldown belong in P0 now.
- [P9 remain] Advanced product analytics expansion remains long-term.

### Phase 10 - Production Trust, Compliance, and Ecosystem

Status: [Aligned] future work.

Compliance and production hardening remain important, but should follow verified assistant core behavior.

## Roadmap Alignment Assessment

- [Aligned] Today/yesterday work on shared trust UI, Dashboard/Actions consistency, Daily Summary, Outcome Feedback, and backend-driven recommendations matches the health assistant roadmap.
- [Drift] The previous roadmap treated P0 as unimplemented; current code shows P0 core pieces are implemented, so the next P0 must shift to verification, data completeness, and governance.
- [Missing] `roadmap.md` was absent; this consolidated file is now the working roadmap.
- [Missing] External/source-tagged metrics are not first-class in the evidence bundle despite existing mock external metrics.
- [Outdated] "Build the entire P0 core loop" is no longer precise; update to "verify and harden the P0 core loop."
- [Outdated] Immediate wearable connector work is downgraded behind evidence contract completeness.
- [Blocked] No git/change-control baseline blocks safe iteration, but CTO cannot create a repo under the current restriction.
- [Blocked] Runtime API/E2E validation and shallow delivery gates block system maturity claims.

## Completed Items

- [Confirmed] P0 Evidence Bundle implemented and tested for symptoms-only, reports-only, metrics-only, and mixed-data cases.
- [Confirmed] P0 Top 3 Recommendations implemented and tested.
- [Confirmed] P0 completed-action suppression / tracking behavior exists in backend recommendation logic.
- [Confirmed] P0 Dashboard daily assistant surfaces exist.
- [Confirmed] P0/P1 Actions Page recommendation layer uses backend health-assistant recommendations.
- [Confirmed] P1 Daily Health Summary exists.
- [Confirmed] P1 Outcome Feedback exists and avoids hallucinating improvement when data is insufficient.
- [Confirmed] P1 Recommendation Trust Layer exists and is shared across Dashboard/Actions.
- [Confirmed] Focused backend tests passed: 101 passed.
- [Confirmed] Frontend TypeScript validation passed: `npx tsc --noEmit`.

## Reprioritized Roadmap

### P0 - Verification, Data Completeness, and Governance Closure

Goal: Make the already-built health assistant core verifiable, rollback-safe, and evidence-complete.

1. [Blocked] Change-control / rollback baseline.
   - [Confirmed] No `.git` repository exists in the workspace.
   - [Blocked] CTO cannot create a new repo; CEO decision is required for whether in-place version control is allowed.
   - Acceptance: CEO-approved change-control approach exists; protected paths remain protected; current stable state can be diffed and recovered.

2. [Blocked] Health Assistant runtime verification gate.
   - [Confirmed] Unit tests pass, but browser/E2E, Docker integration, production smoke, and real backend-to-frontend runtime validation are not confirmed.
   - Acceptance: Dashboard and Actions load real `/health-assistant/*` responses; trust UI appears for high/low/unknown states; completed actions are not duplicated.

3. [Drift] Evidence bundle source completeness.
   - [Confirmed] `external_metrics` is an empty placeholder in the evidence bundle.
   - Acceptance: existing source-tagged external metrics are represented with source, timestamp, freshness, reliability/confidence, and missing-data behavior.

4. [Blocked] Orchestrator quality gate credibility.
   - [Confirmed] Runtime has 390 PASS tasks, 3 INVALID_DELIVERY, 2 RATE_LIMIT, and recent `problem_signal` tasks with no changed files.
   - Acceptance: placeholder acceptance evidence cannot pass; empty changed-file tasks require explicit analysis-only classification; repeated problem-signal tasks are rate-limited/cooldowned.

5. [Missing] Unknown trust fallback.
   - [Confirmed] Trust is an optional frontend field.
   - Acceptance: missing trust data renders a clear "unknown/insufficient evidence" state instead of silently disappearing.

### P1 - Daily Behavior Loop and Outcome Learning

Goal: Make the assistant worth opening daily and turn actions into learning signals.

1. Browser regression coverage for Daily Assistant, Recommendations, Trust, and Outcome Feedback.
2. Daily check-in and outcome feedback refinement for 7/14/30-day windows.
3. Product signal reliability for completion rate, snooze rate, insight-to-action conversion, document-to-action conversion, and recommendation acceptance.
4. Report/insight-to-action adoption UX only after P0 verification gates are in place.

### P2 - External Device Data Readiness

Goal: Prepare device data architecture without real connector overreach.

1. Provider-neutral external metrics schema for heart rate, pulse, sleep, steps, activity, and SpO2.
2. Mock/manual import layer with source metadata, freshness, and reliability scoring.
3. Device signal detection for abnormal heart rate, low sleep, activity decline, and long-term trend changes.
4. Evidence bundle integration before Apple Health, Google Fit, or wearable API connector work.

### P3 - Symptom Intelligence Upgrade

1. Symptom timeline.
2. Severity trend.
3. Pattern detection.
4. Symptom-to-recommendation.
5. Symptom-to-reminder.

### P4 - Report-to-Action Closure

1. Report parsing and lab normalization.
2. Risk mapping.
3. Report-to-decision item.
4. Report-to-action recommendation.
5. Document-to-action conversion tracking.

### P5 - Notification and Reminder Intelligence

1. Notification priority.
2. Snooze learning.
3. Reminder timing.
4. Risk escalation.
5. Daily check-in notifications.

### P6 - Personalization and Learning

Learn from completion history, outcome changes, snooze reasons, and preferred check-in timing.

### P7 - Narrative Memory

Persist narrative history and compare current state to unresolved prior health themes.

### P8 - Family / Multi-Person Health Assistant

Strengthen person-scoped evidence bundles, context labels, permission boundaries, and role guardrails.

### P9 - Product Analytics to Orchestrator

Persist richer product events and use them to drive planner priorities after P0 gate credibility is fixed.

### P10 - Production Trust, Compliance, and Ecosystem

Audit logs, privacy boundaries, health recommendation safety guardrails, device-provider governance, compliance documentation, and production monitoring.

## Items To Downgrade, Merge, Pause, Or Retire

- [Downgrade] Real wearable connector implementation: move behind P2 schema/manual import readiness.
- [Downgrade] Notification intelligence: keep behind verified recommendation/action/outcome loop.
- [Merge] P9 quality-gate credibility into P0; advanced analytics remain P9.
- [Merge] Report/insight conversion metrics into P1 product signal reliability; expanded UX remains P4.
- [Pause] New worker task prompt generation until CEO final decision exists and CTO constraints are reconciled.
- [Retire] Repeated task-pool rotation as a source of truth when runtime backlog/task history is stale or shallow.

## Today Recommended Focus

[Confirmed] The product core exists; the highest-value next focus is not another feature surface. It is:

> P0 verification and governance closure for the existing Health Assistant loop.

Work should prove that Dashboard and Actions consume the same backend recommendation/evidence/trust source at runtime, that unknown trust and external/source-tagged metrics are explicit, and that orchestrator gates stop accepting shallow placeholder delivery.

## Active Task Prompt Status

[Blocked] No active worker task prompt is written by this CTO review.

Reasons:

- [Confirmed] CTO is explicitly restricted to updating only `00-Plan/roadmap/roadmap.md` and `00-Plan/roadmap/CTO-Analysis.md`.
- [Confirmed] The request also says "嚴禁產出新的 worker task prompt."
- [Unknown] CEO final裁決 is not present in the allowed roadmap files.
- [Blocked] Therefore `00-Plan/roadmap/active_task.md` is not created in this review.
